"""
Network-Based Distance Calculator using Path4GMNS

This module replaces straight-line (Haversine) distance calculations with
actual network-based shortest path distances for different travel modes.

Uses path4gmns library to calculate mode-specific shortest paths:
- Auto: Uses link free-flow speeds with congestion effects
- Walk: Pedestrian network with walking speed
- Bike: Bicycle network with cycling speed
- Transit: Transit network proxy (street network with transit speeds)

**IMPORTANT**: This module requires path4gmns to be installed in your environment.
If path4gmns is not available, the functions will gracefully fall back to
Haversine (straight-line) distance calculations.

Installation:
    pip install path4gmns

Or from source (in conda environment):
    cd 4step/src/path4gmns
    pip install -e .

Author: Brooklyn 4-step model enhancement
Date: 2025-11-20
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

# Try to import path4gmns, but don't fail if not available
try:
    import path4gmns as pg
    PATH4GMNS_AVAILABLE = True
except ImportError:
    PATH4GMNS_AVAILABLE = False
    print("Warning: path4gmns not available. Network distance calculations will use Haversine fallback.")
    print("To enable network-based distances, install path4gmns:")


def find_nearest_node(zone_centroid_coords: Tuple[float, float],
                     network,
                     max_distance_km: float = 2.0) -> int:
    """
    Find the nearest network node to a zone centroid

    Parameters
    ----------
    zone_centroid_coords : tuple
        (longitude, latitude) of zone centroid
    network : path4gmns.Network
        The network object
    max_distance_km : float
        Maximum search distance in km

    Returns
    -------
    int : Node ID of nearest node, or None if not found
    """
    lon, lat = zone_centroid_coords

    # Simple brute force search for nearest node
    # For production, could use spatial indexing
    min_dist = float('inf')
    nearest_node = None

    for node_id, node in network.node_dict.items():
        # Calculate Euclidean distance (approximate for small distances)
        node_lon = node.x_coord
        node_lat = node.y_coord

        # Haversine formula for more accurate distance
        dlat = np.radians(node_lat - lat)
        dlon = np.radians(node_lon - lon)
        a = (np.sin(dlat/2)**2 +
             np.cos(np.radians(lat)) * np.cos(np.radians(node_lat)) *
             np.sin(dlon/2)**2)
        c = 2 * np.arcsin(np.sqrt(a))
        dist_km = 6371 * c  # Earth radius in km

        if dist_km < min_dist:
            min_dist = dist_km
            nearest_node = node_id

    if min_dist > max_distance_km:
        print(f"Warning: Nearest node is {min_dist:.2f}km away (> {max_distance_km}km threshold)")

    return nearest_node


def calculate_haversine_distance(lon1, lat1, lon2, lat2):
    """
    Calculate Haversine distance between two points in km

    Parameters
    ----------
    lon1, lat1 : float
        Origin coordinates
    lon2, lat2 : float
        Destination coordinates

    Returns
    -------
    float : Distance in kilometers
    """
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (np.sin(dlat/2)**2 +
         np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) *
         np.sin(dlon/2)**2)
    c = 2 * np.arcsin(np.sqrt(a))
    return 6371 * c  # Earth radius in km


def calculate_haversine_od_matrix(zone_dict: Dict) -> pd.DataFrame:
    """
    Fallback: Calculate zone-to-zone straight-line distances using Haversine

    Parameters
    ----------
    zone_dict : dict
        Dictionary of Zone objects from grid2demand

    Returns
    -------
    pd.DataFrame : OD distance matrix with columns [o_zone_id, d_zone_id, distance]
    """
    print("Using Haversine (straight-line) distance calculation...")

    od_distances = []

    for o_zone_id, o_zone in zone_dict.items():
        for d_zone_id, d_zone in zone_dict.items():
            distance_km = calculate_haversine_distance(
                o_zone.x_coord, o_zone.y_coord,
                d_zone.x_coord, d_zone.y_coord
            )

            od_distances.append({
                'o_zone_id': o_zone_id,
                'd_zone_id': d_zone_id,
                'distance': distance_km
            })

    df_od = pd.DataFrame(od_distances)

    print(f"  ✓ Calculated {len(df_od):,} OD distances")
    print(f"  Average distance: {df_od['distance'].mean():.2f} km")

    return df_od


def calculate_network_od_matrix_by_mode(
    zone_dict: Dict,
    network_dir: str,
    mode: str = 'auto',
    output_file: str = None
) -> pd.DataFrame:
    """
    Calculate zone-to-zone network distances using path4gmns shortest paths

    Parameters
    ----------
    zone_dict : dict
        Dictionary of Zone objects from grid2demand (zone_id -> Zone)
    network_dir : str
        Directory containing node.csv and link.csv (GMNS format)
    mode : str
        Travel mode: 'auto', 'walk', 'bike', or 'transit'
    output_file : str, optional
        Path to save OD distance matrix CSV

    Returns
    -------
    pd.DataFrame : OD distance matrix with columns [o_zone_id, d_zone_id, distance]
    """

    print(f"\n{'='*70}")
    print(f"NETWORK-BASED DISTANCE CALCULATION - MODE: {mode.upper()}")
    print(f"{'='*70}")

    # Check if path4gmns is available
    if not PATH4GMNS_AVAILABLE:
        print("\npath4gmns not available - using Haversine fallback")
        print("For network-based distances, install path4gmns:")
        print("  pip install path4gmns")
        print("")
        df_haversine = calculate_haversine_od_matrix(zone_dict)
        if output_file:
            df_haversine.to_csv(output_file, index=False)
            print(f"✓ Haversine distances saved to: {output_file}")
        return df_haversine

    # Mode-specific parameters
    mode_configs = {
        'auto': {
            'agent_type': 'v',  # vehicle
            'name': 'auto',
            'vot': 10.0,  # Value of time ($/hour)
            'flow_type': 0,  # Passenger car
            'pce': 1.0,  # Passenger car equivalent
            'free_speed': 60.0,  # mph (will use link-specific speeds)
            'use_link_ffs': True,  # Use link free-flow speed
            'allowed_uses': 'auto',
        },
        'walk': {
            'agent_type': 'w',
            'name': 'walk',
            'vot': 5.0,
            'flow_type': 0,
            'pce': 0.0,  # Not applicable
            'free_speed': 3.0,  # mph (~5 km/h)
            'use_link_ffs': False,  # Use mode speed
            'allowed_uses': 'walk',
        },
        'bike': {
            'agent_type': 'b',
            'name': 'bike',
            'vot': 7.0,
            'flow_type': 0,
            'pce': 0.0,
            'free_speed': 12.0,  # mph (~19 km/h)
            'use_link_ffs': False,
            'allowed_uses': 'bike',
        },
        'transit': {
            'agent_type': 't',
            'name': 'transit',
            'vot': 8.0,
            'flow_type': 0,
            'pce': 0.0,
            'free_speed': 15.0,  # mph (average transit speed in urban areas)
            'use_link_ffs': False,
            'allowed_uses': 'all',  # Transit can use all links
        }
    }

    if mode not in mode_configs:
        raise ValueError(f"Mode '{mode}' not supported. Choose from: {list(mode_configs.keys())}")

    config = mode_configs[mode]

    # Load network using path4gmns
    print(f"Loading network from {network_dir}...")
    try:
        # Read network - path4gmns will look for node.csv and link.csv
        network = pg.read_network(input_dir=network_dir)

        print(f"  ✓ Network loaded: {network.get_number_of_nodes()} nodes, {network.get_number_of_links()} links")

    except Exception as e:
        print(f"Error loading network: {e}")
        print("Note: path4gmns requires node.csv and link.csv in GMNS format")
        raise

    # Map zones to network nodes
    print(f"\nMapping {len(zone_dict)} zones to network nodes...")
    zone_to_node = {}

    for zone_id, zone in zone_dict.items():
        # Get zone centroid coordinates
        centroid_lon = zone.x_coord
        centroid_lat = zone.y_coord

        # Find nearest network node
        nearest_node = find_nearest_node(
            (centroid_lon, centroid_lat),
            network,
            max_distance_km=2.0
        )

        if nearest_node is not None:
            zone_to_node[zone_id] = nearest_node
        else:
            print(f"  Warning: Could not find network node for zone {zone_id}")

    print(f"  ✓ Mapped {len(zone_to_node)} zones to network nodes")

    # Calculate shortest paths
    print(f"\nCalculating shortest paths (mode={mode})...")
    od_distances = []

    total_pairs = len(zone_to_node) ** 2
    processed = 0

    # Use single-source shortest path for efficiency
    for o_zone_id, o_node_id in zone_to_node.items():
        # Calculate shortest path tree from this origin
        try:
            # Build shortest path tree for this origin
            sp_tree = network.get_shortest_path(
                from_node_id=o_node_id,
                to_node_id=None,  # To all destinations
                mode=config['agent_type'],
                seq_type='node'
            )

            # Extract distances to each destination
            for d_zone_id, d_node_id in zone_to_node.items():
                if d_node_id in sp_tree:
                    # Get distance from shortest path
                    path_info = sp_tree[d_node_id]
                    distance_miles = path_info['distance']
                    distance_km = distance_miles * 1.60934  # Convert to km
                else:
                    # Destination unreachable - use large impedance
                    distance_km = 9999.0

                od_distances.append({
                    'o_zone_id': o_zone_id,
                    'd_zone_id': d_zone_id,
                    'distance': distance_km
                })

                processed += 1

        except Exception as e:
            # If shortest path calculation fails, fall back to straight-line
            print(f"  Warning: Shortest path failed for origin zone {o_zone_id}: {e}")

            # Use straight-line distance as fallback
            o_zone = zone_dict[o_zone_id]
            for d_zone_id in zone_to_node.keys():
                d_zone = zone_dict[d_zone_id]

                # Haversine distance
                dlat = np.radians(d_zone.y_coord - o_zone.y_coord)
                dlon = np.radians(d_zone.x_coord - o_zone.x_coord)
                a = (np.sin(dlat/2)**2 +
                     np.cos(np.radians(o_zone.y_coord)) *
                     np.cos(np.radians(d_zone.y_coord)) *
                     np.sin(dlon/2)**2)
                c = 2 * np.arcsin(np.sqrt(a))
                distance_km = 6371 * c

                od_distances.append({
                    'o_zone_id': o_zone_id,
                    'd_zone_id': d_zone_id,
                    'distance': distance_km
                })

                processed += 1

        # Progress update
        if (processed % 1000) == 0 or processed == total_pairs:
            pct = processed / total_pairs * 100
            print(f"  Progress: {processed}/{total_pairs} OD pairs ({pct:.1f}%)")

    # Create DataFrame
    df_od = pd.DataFrame(od_distances)

    # Summary statistics
    print(f"\n{'='*70}")
    print(f"DISTANCE CALCULATION COMPLETE")
    print(f"{'='*70}")
    print(f"Mode: {mode.upper()}")
    print(f"Total OD pairs: {len(df_od):,}")
    print(f"Average distance: {df_od['distance'].mean():.2f} km")
    print(f"Min distance: {df_od['distance'].min():.2f} km")
    print(f"Max distance: {df_od['distance'].max():.2f} km")
    print(f"Unreachable OD pairs: {(df_od['distance'] >= 9999).sum():,}")

    # Save if output file specified
    if output_file:
        df_od.to_csv(output_file, index=False)
        print(f"\n✓ OD distance matrix saved to: {output_file}")

    return df_od


def calculate_all_mode_distances(
    zone_dict: Dict,
    network_dir: str,
    output_dir: str = None,
    modes: List[str] = ['auto', 'walk', 'bike']
) -> Dict[str, pd.DataFrame]:
    """
    Calculate network distances for all specified modes

    Parameters
    ----------
    zone_dict : dict
        Zone dictionary from grid2demand
    network_dir : str
        Network directory with GMNS files
    output_dir : str, optional
        Directory to save output files
    modes : list
        List of modes to process

    Returns
    -------
    dict : Dictionary mapping mode -> OD distance DataFrame
    """

    all_distances = {}

    for mode in modes:
        print(f"\n{'#'*70}")
        print(f"Processing mode: {mode.upper()}")
        print(f"{'#'*70}")

        # Output file path
        if output_dir:
            output_file = os.path.join(output_dir, f'zone_od_dist_matrix_{mode}.csv')
        else:
            output_file = None

        # Calculate distances
        df_dist = calculate_network_od_matrix_by_mode(
            zone_dict=zone_dict,
            network_dir=network_dir,
            mode=mode,
            output_file=output_file
        )

        all_distances[mode] = df_dist

    return all_distances


if __name__ == '__main__':
    print("This module provides network-based distance calculation utilities.")
    print("Import and use calculate_network_od_matrix_by_mode() or calculate_all_mode_distances()")
