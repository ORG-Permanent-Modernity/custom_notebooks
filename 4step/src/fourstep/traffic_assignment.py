"""
Traffic Assignment Module

Step 4 of the 4-step model: Assign vehicle trips to network links.

Implements:
- All-or-nothing (AON) assignment
- User equilibrium (UE) assignment via Frank-Wolfe algorithm
- Volume-delay functions (BPR, conical)
"""

from dataclasses import dataclass, field
from typing import Optional, Literal
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import shortest_path
import warnings


@dataclass
class Link:
    """Network link representation."""
    link_id: int
    from_node: int
    to_node: int
    length: float        # miles
    free_flow_time: float  # minutes
    capacity: float      # vehicles per hour
    lanes: int = 1
    link_type: str = "road"


@dataclass
class Network:
    """
    Simple network representation for traffic assignment.

    For production use, integrate with path4gmns or similar.
    """
    nodes: pd.DataFrame          # node_id, x, y, zone_id (if centroid)
    links: pd.DataFrame          # link_id, from_node, to_node, length, fft, capacity
    zone_centroids: dict = field(default_factory=dict)  # zone_id -> node_id

    def __post_init__(self):
        """Build network data structures."""
        self._build_graph()

    def _build_graph(self):
        """Build adjacency matrix for shortest path."""
        node_ids = self.nodes["node_id"].values
        self.node_to_idx = {nid: i for i, nid in enumerate(node_ids)}
        self.idx_to_node = {i: nid for nid, i in self.node_to_idx.items()}
        self.n_nodes = len(node_ids)
        self.n_links = len(self.links)

        # Build sparse adjacency matrix with free-flow times
        rows = []
        cols = []
        data = []

        for _, link in self.links.iterrows():
            from_idx = self.node_to_idx[link["from_node"]]
            to_idx = self.node_to_idx[link["to_node"]]
            rows.append(from_idx)
            cols.append(to_idx)
            data.append(link["free_flow_time"])

        self.adj_matrix = csr_matrix(
            (data, (rows, cols)),
            shape=(self.n_nodes, self.n_nodes)
        )

        # Link index mapping
        self.link_idx = {
            (row["from_node"], row["to_node"]): i
            for i, row in self.links.iterrows()
        }

    def get_zone_node(self, zone_id) -> int:
        """Get centroid node ID for a zone."""
        return self.zone_centroids.get(zone_id, zone_id)


def bpr_function(
    volume: np.ndarray,
    capacity: np.ndarray,
    free_flow_time: np.ndarray,
    alpha: float = 0.15,
    beta: float = 4.0
) -> np.ndarray:
    """
    BPR (Bureau of Public Roads) volume-delay function.

    t = t0 * (1 + alpha * (v/c)^beta)

    Args:
        volume: Link volumes
        capacity: Link capacities
        free_flow_time: Free-flow travel times
        alpha: BPR alpha parameter (default 0.15)
        beta: BPR beta parameter (default 4.0)

    Returns:
        Congested travel times
    """
    vc_ratio = volume / np.maximum(capacity, 1)
    return free_flow_time * (1 + alpha * np.power(vc_ratio, beta))


def conical_function(
    volume: np.ndarray,
    capacity: np.ndarray,
    free_flow_time: np.ndarray,
    alpha: float = 2.0
) -> np.ndarray:
    """
    Conical volume-delay function.

    More realistic than BPR at high V/C ratios.

    Args:
        volume: Link volumes
        capacity: Link capacities
        free_flow_time: Free-flow travel times
        alpha: Conical parameter

    Returns:
        Congested travel times
    """
    x = volume / np.maximum(capacity, 1)
    beta = (2 * alpha - 1) / (2 * alpha - 2)
    term = np.sqrt(beta**2 + (alpha**2) * (x - 1)**2 + alpha**2)
    return free_flow_time * (2 + term - beta - alpha * (x - 1))


@dataclass
class NetworkAssignment:
    """
    Traffic assignment results and methods.
    """
    network: Network
    link_volumes: np.ndarray
    link_times: np.ndarray
    vdf_type: str = "bpr"
    vdf_params: dict = field(default_factory=lambda: {"alpha": 0.15, "beta": 4.0})

    def get_vc_ratios(self) -> np.ndarray:
        """Calculate volume/capacity ratios."""
        capacities = self.network.links["capacity"].values
        return self.link_volumes / np.maximum(capacities, 1)

    def summary(self) -> str:
        """Return summary statistics."""
        vc = self.get_vc_ratios()
        lines = [
            "Traffic Assignment Results",
            "=" * 40,
            f"Total link volume: {self.link_volumes.sum():,.0f} veh",
            f"V/C ratio range: {vc.min():.2f} - {vc.max():.2f}",
            f"Links with V/C > 1.0: {(vc > 1.0).sum()}",
            f"Links with V/C > 0.8: {(vc > 0.8).sum()}",
            f"Average link time: {self.link_times.mean():.1f} min",
        ]
        return "\n".join(lines)

    def to_dataframe(self) -> pd.DataFrame:
        """Return results as DataFrame."""
        df = self.network.links.copy()
        df["volume"] = self.link_volumes
        df["congested_time"] = self.link_times
        df["vc_ratio"] = self.get_vc_ratios()
        return df


def all_or_nothing(
    network: Network,
    od_matrix: np.ndarray,
    zone_ids: np.ndarray,
    verbose: bool = False
) -> np.ndarray:
    """
    All-or-nothing (AON) traffic assignment.

    Assigns all trips between OD pair to shortest path.
    Used as subroutine in equilibrium assignment.

    Args:
        network: Network object
        od_matrix: OD trip matrix (n_zones, n_zones)
        zone_ids: Zone IDs corresponding to matrix indices
        verbose: Print progress

    Returns:
        Link volume array
    """
    n_zones = len(zone_ids)
    link_volumes = np.zeros(network.n_links)
    disconnected_pairs = 0
    disconnected_trips = 0.0

    # Get centroid node indices
    zone_node_indices = []
    for zid in zone_ids:
        node_id = network.get_zone_node(zid)
        if node_id in network.node_to_idx:
            zone_node_indices.append(network.node_to_idx[node_id])
        else:
            zone_node_indices.append(None)

    # Calculate shortest paths from each origin zone
    if verbose:
        print("  Computing shortest paths...")

    # Use scipy shortest path
    dist_matrix, predecessors = shortest_path(
        network.adj_matrix,
        directed=True,
        return_predecessors=True,
        indices=[idx for idx in zone_node_indices if idx is not None]
    )

    # Trace paths and accumulate volumes
    if verbose:
        print("  Tracing paths and accumulating volumes...")

    valid_origins = [i for i, idx in enumerate(zone_node_indices) if idx is not None]

    for orig_matrix_idx, orig_zone_idx in enumerate(valid_origins):
        orig_node_idx = zone_node_indices[orig_zone_idx]

        for dest_zone_idx in range(n_zones):
            dest_node_idx = zone_node_indices[dest_zone_idx]

            if dest_node_idx is None:
                continue

            trips = od_matrix[orig_zone_idx, dest_zone_idx]
            if trips <= 0:
                continue

            # Trace path from destination back to origin
            current = dest_node_idx
            path_links = []

            max_steps = network.n_nodes  # Prevent infinite loop
            steps = 0

            while current != orig_node_idx and steps < max_steps:
                pred = predecessors[orig_matrix_idx, current]
                if pred < 0:
                    # No path exists - track for warning
                    disconnected_pairs += 1
                    disconnected_trips += trips
                    break

                # Find link from pred to current
                pred_node = network.idx_to_node[pred]
                curr_node = network.idx_to_node[current]

                link_key = (pred_node, curr_node)
                if link_key in network.link_idx:
                    link_volumes[network.link_idx[link_key]] += trips

                current = pred
                steps += 1

    if verbose and disconnected_pairs > 0:
        print(f"  WARNING: {disconnected_pairs:,} OD pairs have no path ({disconnected_trips:,.0f} trips unassigned)")

    return link_volumes


def user_equilibrium(
    network: Network,
    od_matrix: np.ndarray,
    zone_ids: np.ndarray,
    vdf_type: Literal["bpr", "conical"] = "bpr",
    vdf_params: Optional[dict] = None,
    max_iterations: int = 100,
    convergence: float = 0.01,
    verbose: bool = False
) -> NetworkAssignment:
    """
    User equilibrium traffic assignment using Frank-Wolfe algorithm.

    Finds equilibrium where no traveler can reduce their travel time
    by unilaterally changing routes.

    Args:
        network: Network object
        od_matrix: OD trip matrix
        zone_ids: Zone IDs
        vdf_type: Volume-delay function type ('bpr' or 'conical')
        vdf_params: VDF parameters
        max_iterations: Maximum iterations
        convergence: Convergence threshold (relative gap)
        verbose: Print progress

    Returns:
        NetworkAssignment with equilibrium volumes
    """
    if vdf_params is None:
        vdf_params = {"alpha": 0.15, "beta": 4.0}

    # Get link attributes
    capacities = network.links["capacity"].values
    fft = network.links["free_flow_time"].values

    # Select VDF
    if vdf_type == "bpr":
        vdf = lambda v: bpr_function(v, capacities, fft, **vdf_params)
    else:
        vdf = lambda v: conical_function(v, capacities, fft, vdf_params.get("alpha", 2.0))

    # Initialize with AON assignment
    if verbose:
        print("  Initializing with AON assignment...")

    link_volumes = all_or_nothing(network, od_matrix, zone_ids, verbose=False)

    # Frank-Wolfe iterations
    if verbose:
        print("  Running Frank-Wolfe equilibrium iterations...")

    for iteration in range(max_iterations):
        # Update link times based on current volumes
        link_times = vdf(link_volumes)

        # Update network adjacency with current times
        for i, (_, link) in enumerate(network.links.iterrows()):
            from_idx = network.node_to_idx[link["from_node"]]
            to_idx = network.node_to_idx[link["to_node"]]
            network.adj_matrix[from_idx, to_idx] = link_times[i]

        # AON assignment with current times
        aon_volumes = all_or_nothing(network, od_matrix, zone_ids, verbose=False)

        # Calculate optimal step size (line search)
        # Using MSA (Method of Successive Averages) step size
        step = 2.0 / (iteration + 2)

        # Calculate relative gap for convergence check
        # Proper formula: gap = sum(t_a * (x_a - y_a)) / sum(t_a * x_a)
        # where t_a = current link time, x_a = current volume, y_a = AON volume
        # This measures the relative difference in total system travel time
        current_system_time = (link_times * link_volumes).sum()
        if current_system_time > 0:
            # Relative gap: excess travel time compared to AON
            gap = (link_times * (link_volumes - aon_volumes)).sum() / current_system_time
            gap = abs(gap)  # Take absolute value
        else:
            gap = 1.0

        if verbose and iteration % 10 == 0:
            print(f"    Iteration {iteration}: gap = {gap:.6f}")

        # Update volumes
        link_volumes = link_volumes + step * (aon_volumes - link_volumes)

        # Check convergence
        if gap < convergence:
            if verbose:
                print(f"  Converged at iteration {iteration} with gap {gap:.6f}")
            break

    # Final time calculation
    link_times = vdf(link_volumes)

    return NetworkAssignment(
        network=network,
        link_volumes=link_volumes,
        link_times=link_times,
        vdf_type=vdf_type,
        vdf_params=vdf_params
    )


def create_network_from_gmns(
    node_file: str,
    link_file: str,
    zone_file: Optional[str] = None
) -> Network:
    """
    Create Network from GMNS format CSV files.

    Args:
        node_file: Path to node.csv
        link_file: Path to link.csv
        zone_file: Optional path to zone.csv

    Returns:
        Network object
    """
    nodes = pd.read_csv(node_file)
    links = pd.read_csv(link_file)

    # Standardize column names
    node_col_map = {
        "node_id": "node_id",
        "x_coord": "x",
        "y_coord": "y",
        "zone_id": "zone_id",
    }

    link_col_map = {
        "link_id": "link_id",
        "from_node_id": "from_node",
        "to_node_id": "to_node",
        "length": "length",
        "free_speed": "free_speed",
        "capacity": "capacity",
        "lanes": "lanes",
    }

    # Rename columns if needed
    for old, new in node_col_map.items():
        if old in nodes.columns and new not in nodes.columns:
            nodes = nodes.rename(columns={old: new})

    for old, new in link_col_map.items():
        if old in links.columns and new not in links.columns:
            links = links.rename(columns={old: new})

    # Calculate free-flow time if not present
    if "free_flow_time" not in links.columns:
        if "free_speed" in links.columns:
            # time = length / speed * 60 (convert to minutes)
            links["free_flow_time"] = links["length"] / links["free_speed"] * 60
        else:
            # Assume 30 mph default
            links["free_flow_time"] = links["length"] / 30 * 60

    # Set default capacity if missing
    if "capacity" not in links.columns:
        links["capacity"] = 1800  # Default capacity per lane per hour

    # Build zone centroid mapping
    zone_centroids = {}
    if "zone_id" in nodes.columns:
        centroid_nodes = nodes[nodes["zone_id"].notna()]
        for _, row in centroid_nodes.iterrows():
            zone_centroids[row["zone_id"]] = row["node_id"]

    return Network(
        nodes=nodes,
        links=links,
        zone_centroids=zone_centroids
    )


def run_assignment(
    od_matrix: np.ndarray,
    zone_ids: np.ndarray,
    network: Optional[Network] = None,
    node_file: Optional[str] = None,
    link_file: Optional[str] = None,
    method: Literal["aon", "ue"] = "ue",
    vdf_type: str = "bpr",
    vdf_params: Optional[dict] = None,
    max_iterations: int = 100,
    convergence: float = 0.01,
    verbose: bool = False
) -> NetworkAssignment:
    """
    Run traffic assignment.

    Args:
        od_matrix: Vehicle trip matrix
        zone_ids: Zone IDs
        network: Network object (or provide node_file and link_file)
        node_file: Path to node.csv (GMNS format)
        link_file: Path to link.csv (GMNS format)
        method: Assignment method ('aon' or 'ue')
        vdf_type: Volume-delay function type
        vdf_params: VDF parameters
        max_iterations: Max iterations for UE
        convergence: Convergence threshold
        verbose: Print progress

    Returns:
        NetworkAssignment results
    """
    # Load network if not provided
    if network is None:
        if node_file is None or link_file is None:
            raise ValueError("Must provide either network or node_file and link_file")
        network = create_network_from_gmns(node_file, link_file)

    if method == "aon":
        if verbose:
            print("Running all-or-nothing assignment...")
        link_volumes = all_or_nothing(network, od_matrix, zone_ids, verbose)

        # Calculate times at assigned volumes
        capacities = network.links["capacity"].values
        fft = network.links["free_flow_time"].values
        link_times = bpr_function(link_volumes, capacities, fft)

        return NetworkAssignment(
            network=network,
            link_volumes=link_volumes,
            link_times=link_times,
            vdf_type="bpr",
            vdf_params={"alpha": 0.15, "beta": 4.0}
        )

    else:  # UE
        if verbose:
            print("Running user equilibrium assignment...")
        return user_equilibrium(
            network=network,
            od_matrix=od_matrix,
            zone_ids=zone_ids,
            vdf_type=vdf_type,
            vdf_params=vdf_params,
            max_iterations=max_iterations,
            convergence=convergence,
            verbose=verbose
        )
