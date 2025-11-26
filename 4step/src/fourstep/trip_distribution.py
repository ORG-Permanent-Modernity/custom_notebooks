"""
Trip Distribution Module

Step 2 of the 4-step model: Distribute trips between zones using gravity model.

Includes multiple friction function options and model improvements:
- Singly and doubly constrained models
- K-factors for zone-pair adjustments
- Intrazonal trip handling
- Calibration to target trip length
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable, Literal
import numpy as np
import pandas as pd
import geopandas as gpd
from scipy.spatial.distance import cdist


class FrictionFunction(Enum):
    """Available friction function types for gravity model."""
    EXPONENTIAL = "exponential"   # exp(-beta * c)
    POWER = "power"               # c^(-gamma)
    GAMMA = "gamma"               # c^alpha * exp(-beta * c)
    TANNER = "tanner"             # c^a * exp(-b * c)
    INVERSE_POWER = "inverse_power"  # 1 / (1 + c)^gamma


def exponential_friction(impedance: np.ndarray, beta: float = 0.1) -> np.ndarray:
    """
    Exponential friction function: f(c) = exp(-beta * c)

    Best for short urban trips where distance has strong deterrent effect.

    Args:
        impedance: Distance/time matrix (n_zones, n_zones)
        beta: Decay parameter (higher = steeper decay)

    Returns:
        Friction matrix (n_zones, n_zones)
    """
    return np.exp(-beta * impedance)


def power_friction(impedance: np.ndarray, gamma: float = 2.0) -> np.ndarray:
    """
    Power friction function: f(c) = c^(-gamma)

    Better for longer trips with gentler distance decay.

    Args:
        impedance: Distance/time matrix (n_zones, n_zones)
        gamma: Power parameter (higher = steeper decay)

    Returns:
        Friction matrix (n_zones, n_zones)
    """
    # Avoid division by zero for intrazonal (c=0)
    safe_impedance = np.maximum(impedance, 1e-6)
    return np.power(safe_impedance, -gamma)


def gamma_friction(
    impedance: np.ndarray,
    alpha: float = -0.5,
    beta: float = 0.1
) -> np.ndarray:
    """
    Gamma friction function: f(c) = c^alpha * exp(-beta * c)

    Most flexible form - combines power and exponential decay.
    Standard in many MPO models.

    Args:
        impedance: Distance/time matrix (n_zones, n_zones)
        alpha: Power parameter (typically negative)
        beta: Exponential decay parameter

    Returns:
        Friction matrix (n_zones, n_zones)
    """
    safe_impedance = np.maximum(impedance, 1e-6)
    return np.power(safe_impedance, alpha) * np.exp(-beta * impedance)


def tanner_friction(
    impedance: np.ndarray,
    a: float = -1.0,
    b: float = 0.05
) -> np.ndarray:
    """
    Tanner friction function: f(c) = c^a * exp(-b * c)

    Traditional 4-step model form (equivalent to gamma).

    Args:
        impedance: Distance/time matrix
        a: Power parameter
        b: Exponential parameter

    Returns:
        Friction matrix
    """
    return gamma_friction(impedance, alpha=a, beta=b)


def inverse_power_friction(
    impedance: np.ndarray,
    gamma: float = 2.0
) -> np.ndarray:
    """
    Inverse power friction: f(c) = 1 / (1 + c)^gamma

    Handles zero distances gracefully.

    Args:
        impedance: Distance/time matrix
        gamma: Power parameter

    Returns:
        Friction matrix
    """
    return np.power(1.0 + impedance, -gamma)


def get_friction_function(
    friction_type: FrictionFunction
) -> Callable:
    """Get the friction function for a given type."""
    mapping = {
        FrictionFunction.EXPONENTIAL: exponential_friction,
        FrictionFunction.POWER: power_friction,
        FrictionFunction.GAMMA: gamma_friction,
        FrictionFunction.TANNER: tanner_friction,
        FrictionFunction.INVERSE_POWER: inverse_power_friction,
    }
    return mapping[friction_type]


def calculate_impedance_matrix(
    zones: gpd.GeoDataFrame,
    zone_id_col: str = "zone_id",
    network_skim: Optional[pd.DataFrame] = None,
    intrazonal_method: Literal["half_nearest", "area_based", "fixed"] = "half_nearest",
    intrazonal_value: float = 5.0,
    verbose: bool = False
) -> tuple[np.ndarray, np.ndarray]:
    """
    Calculate zone-to-zone impedance (distance or time) matrix.

    Args:
        zones: GeoDataFrame with zone polygons
        zone_id_col: Column name for zone ID
        network_skim: Optional pre-computed skim matrix as DataFrame
                      with columns: origin_zone, dest_zone, impedance
        intrazonal_method: Method for intrazonal impedance
            - 'half_nearest': Half the distance to nearest zone
            - 'area_based': Based on zone area (0.5 * sqrt(area/pi))
            - 'fixed': Use fixed intrazonal_value
        intrazonal_value: Fixed value for 'fixed' method (in same units as impedance)
        verbose: Print progress messages

    Returns:
        Tuple of (zone_ids array, impedance matrix)
    """
    zone_ids = zones[zone_id_col].values
    n_zones = len(zone_ids)

    if network_skim is not None:
        # VECTORIZED: Use pivot to create impedance matrix from skim
        if verbose:
            print("  Using network skim matrix...")

        # Check required columns
        required_cols = ['origin_zone', 'dest_zone', 'impedance']
        if not all(col in network_skim.columns for col in required_cols):
            alt_cols = {'o_zone_id': 'origin_zone', 'd_zone_id': 'dest_zone',
                       'distance': 'impedance', 'time': 'impedance'}
            for old, new in alt_cols.items():
                if old in network_skim.columns:
                    network_skim = network_skim.rename(columns={old: new})

        # Filter to zones we care about
        skim_filtered = network_skim[
            network_skim['origin_zone'].isin(zone_ids) &
            network_skim['dest_zone'].isin(zone_ids)
        ]

        # Pivot to matrix form (VECTORIZED - no loop)
        skim_pivot = skim_filtered.pivot(
            index='origin_zone',
            columns='dest_zone',
            values='impedance'
        )

        # Reindex to match zone_ids order
        skim_pivot = skim_pivot.reindex(index=zone_ids, columns=zone_ids)
        impedance = skim_pivot.values.astype(np.float64)

        # Fill any NaN with large value (no connection)
        impedance = np.nan_to_num(impedance, nan=999.0)

    else:
        # Calculate centroid-to-centroid Euclidean distance
        if verbose:
            print("  Calculating centroid-to-centroid distances...")

        # Get centroids
        centroids = zones.geometry.centroid

        # Determine units for distance conversion
        crs_units = "meters"  # Default assumption

        # Project to a suitable CRS for distance calculation if in lat/lon
        if zones.crs and zones.crs.is_geographic:
            # Use UTM zone for the centroid of the study area
            avg_lon = centroids.x.mean()
            utm_zone = int((avg_lon + 180) / 6) + 1
            utm_crs = f"EPSG:{32600 + utm_zone}" if centroids.y.mean() >= 0 else f"EPSG:{32700 + utm_zone}"
            if verbose:
                print(f"  Projecting to {utm_crs} for distance calculation...")
            centroids = centroids.to_crs(utm_crs)
            crs_units = "meters"
        elif zones.crs:
            # Check if CRS uses feet (common for US State Plane)
            crs_str = str(zones.crs).lower()
            # EPSG:2263 and similar US State Plane systems use feet
            if "2263" in crs_str or "foot" in crs_str or "feet" in crs_str or "ft" in crs_str:
                crs_units = "feet"
            elif zones.crs.axis_info and any("foot" in str(ax.unit_name).lower() for ax in zones.crs.axis_info):
                crs_units = "feet"

        # Extract coordinates
        coords = np.column_stack([centroids.x, centroids.y])

        # Calculate pairwise distances - VECTORIZED
        impedance = cdist(coords, coords, metric="euclidean")

        # Convert to miles based on CRS units
        if crs_units == "feet":
            impedance = impedance / 5280.0  # feet per mile
        else:
            impedance = impedance / 1609.34  # meters per mile

    # VECTORIZED: Handle intrazonal impedance
    if verbose:
        print(f"  Setting intrazonal impedance using '{intrazonal_method}' method...")

    if intrazonal_method == "half_nearest":
        # VECTORIZED: Set diagonal to inf, find min per row, then set diagonal
        impedance_temp = impedance.copy()
        np.fill_diagonal(impedance_temp, np.inf)
        min_distances = impedance_temp.min(axis=1)
        # Handle case where a zone has no neighbors (all inf)
        min_distances = np.where(np.isinf(min_distances), intrazonal_value * 2, min_distances)
        np.fill_diagonal(impedance, 0.5 * min_distances)

    elif intrazonal_method == "area_based":
        # Calculate from zone areas - VECTORIZED
        if zones.crs and zones.crs.is_geographic:
            # Project for area calculation
            avg_lon = zones.geometry.centroid.x.mean()
            utm_zone = int((avg_lon + 180) / 6) + 1
            utm_crs = f"EPSG:{32600 + utm_zone}"
            areas = zones.to_crs(utm_crs).geometry.area.values
        else:
            areas = zones.geometry.area.values

        # Intrazonal = 0.5 * sqrt(area / pi), converted to miles - VECTORIZED
        radii_m = np.sqrt(areas / np.pi)
        intrazonal_values = 0.5 * radii_m / 1609.34
        np.fill_diagonal(impedance, intrazonal_values)

    elif intrazonal_method == "fixed":
        np.fill_diagonal(impedance, intrazonal_value)

    if verbose:
        print(f"  Impedance matrix: {n_zones}x{n_zones}")
        print(f"  Distance range: {impedance.min():.2f} - {impedance.max():.2f} miles")
        print(f"  Mean intrazonal: {np.diag(impedance).mean():.2f} miles")

    return zone_ids, impedance


def furness_balance(
    trip_matrix: np.ndarray,
    productions: np.ndarray,
    attractions: np.ndarray,
    max_iterations: int = 100,
    tolerance: float = 0.001,
    verbose: bool = False
) -> tuple[np.ndarray, dict]:
    """
    Furness (IPF) balancing for doubly-constrained gravity model.

    Iteratively adjusts trip matrix until row sums match productions
    and column sums match attractions.

    Args:
        trip_matrix: Initial trip matrix from singly-constrained model
        productions: Target production totals by zone
        attractions: Target attraction totals by zone
        max_iterations: Maximum iterations
        tolerance: Convergence threshold (relative error)
        verbose: Print progress messages

    Returns:
        Tuple of (balanced trip matrix, convergence diagnostics dict)
    """
    T = trip_matrix.copy()
    n_zones = len(productions)

    # Avoid division by zero
    productions = np.maximum(productions, 1e-10)
    attractions = np.maximum(attractions, 1e-10)

    diagnostics = {
        "converged": False,
        "iterations": 0,
        "row_errors": [],
        "col_errors": [],
    }

    for iteration in range(max_iterations):
        # Balance rows (productions) - VECTORIZED
        row_sums = T.sum(axis=1)
        row_sums = np.maximum(row_sums, 1e-10)
        row_factors = productions / row_sums
        T = T * row_factors[:, np.newaxis]

        # Balance columns (attractions) - VECTORIZED
        col_sums = T.sum(axis=0)
        col_sums = np.maximum(col_sums, 1e-10)
        col_factors = attractions / col_sums
        T = T * col_factors[np.newaxis, :]

        # Check convergence
        row_error = np.abs(T.sum(axis=1) - productions).max() / productions.mean()
        col_error = np.abs(T.sum(axis=0) - attractions).max() / attractions.mean()

        diagnostics["row_errors"].append(float(row_error))
        diagnostics["col_errors"].append(float(col_error))
        diagnostics["iterations"] = iteration + 1

        if row_error < tolerance and col_error < tolerance:
            diagnostics["converged"] = True
            if verbose:
                print(f"  Furness converged in {iteration + 1} iterations")
            break

    if verbose and not diagnostics["converged"]:
        print(f"  WARNING: Furness did not converge after {max_iterations} iterations")
        print(f"           Final row error: {row_error:.6f}, col error: {col_error:.6f}")

    return T, diagnostics


def gravity_model(
    productions: np.ndarray,
    attractions: np.ndarray,
    impedance: np.ndarray,

    # Friction function parameters
    friction_function: FrictionFunction = FrictionFunction.GAMMA,
    friction_params: Optional[dict] = None,

    # Constraint type
    constraint_type: Literal["singly_production", "singly_attraction", "doubly"] = "doubly",
    max_iterations: int = 100,
    convergence_threshold: float = 0.001,

    # K-factors (socioeconomic adjustment)
    k_factors: Optional[np.ndarray] = None,

    # Accessibility weighting
    accessibility_weight: float = 0.0,

    verbose: bool = False
) -> tuple[np.ndarray, dict]:
    """
    Gravity model for trip distribution.

    Standard formula (production-constrained):
        T_ij = P_i * (A_j * f(c_ij)) / sum_k(A_k * f(c_ik))

    Args:
        productions: Production totals by zone (n_zones,)
        attractions: Attraction totals by zone (n_zones,)
        impedance: Distance/time matrix (n_zones, n_zones)

        friction_function: Type of friction function to use
        friction_params: Parameters for friction function
            - exponential: {'beta': 0.1}
            - power: {'gamma': 2.0}
            - gamma: {'alpha': -0.5, 'beta': 0.1}
            - tanner: {'a': -1.0, 'b': 0.05}

        constraint_type: Type of constraint
            - 'singly_production': Match production totals only
            - 'singly_attraction': Match attraction totals only
            - 'doubly': Match both (Furness balancing)

        max_iterations: Max iterations for doubly-constrained
        convergence_threshold: Convergence tolerance

        k_factors: Optional zone-pair adjustment factors (n_zones, n_zones)
                   Values > 1 increase trips, < 1 decrease trips

        accessibility_weight: Weight for accessibility adjustment (0 = none)
                              Modifies attractions based on zone accessibility

        verbose: Print progress messages

    Returns:
        Tuple of (trip_matrix, diagnostics_dict)
    """
    n_zones = len(productions)

    # Set default friction parameters
    if friction_params is None:
        friction_params = {
            FrictionFunction.EXPONENTIAL: {"beta": 0.1},
            FrictionFunction.POWER: {"gamma": 2.0},
            FrictionFunction.GAMMA: {"alpha": -0.5, "beta": 0.1},
            FrictionFunction.TANNER: {"a": -1.0, "b": 0.05},
            FrictionFunction.INVERSE_POWER: {"gamma": 2.0},
        }.get(friction_function, {"beta": 0.1})

    if verbose:
        print(f"  Running gravity model:")
        print(f"    Friction function: {friction_function.value}")
        print(f"    Parameters: {friction_params}")
        print(f"    Constraint type: {constraint_type}")

    # Calculate friction matrix
    friction_func = get_friction_function(friction_function)
    F = friction_func(impedance, **friction_params)

    # Apply K-factors if provided
    if k_factors is not None:
        if verbose:
            print(f"    Applying K-factors (range: {k_factors.min():.2f} - {k_factors.max():.2f})")
        F = F * k_factors

    # Apply accessibility weighting if specified
    # FIXED: Hansen accessibility - sum of attractions reachable from zone i
    # A_i = sum_j(A_j * f(c_ij)) - this measures how much attraction zone i can reach
    effective_attractions = attractions.copy()
    if accessibility_weight > 0:
        # Hansen accessibility: for each origin i, sum attractions weighted by friction
        # accessibility[i] = sum_j(A_j * F[i,j])
        accessibility = (attractions[np.newaxis, :] * F).sum(axis=1)  # FIXED: sum across destinations (axis=1)
        accessibility = accessibility / accessibility.mean()  # Normalize
        # Zones with better accessibility get boosted attractions when they are destinations
        effective_attractions = attractions * np.power(accessibility, accessibility_weight)
        if verbose:
            print(f"    Applied accessibility weighting (weight={accessibility_weight})")
            print(f"    Accessibility range: {accessibility.min():.2f} - {accessibility.max():.2f}")

    # Initialize diagnostics
    diagnostics = {
        "friction_function": friction_function.value,
        "friction_params": friction_params,
        "constraint_type": constraint_type,
        "n_zones": n_zones,
        "total_productions": float(productions.sum()),
        "total_attractions": float(attractions.sum()),
    }

    # Calculate base gravity model (production-constrained)
    # T_ij = P_i * (A_j * F_ij) / sum_k(A_k * F_ik)
    numerator = effective_attractions[np.newaxis, :] * F
    denominator = numerator.sum(axis=1, keepdims=True)
    denominator = np.maximum(denominator, 1e-10)  # Avoid division by zero

    T = productions[:, np.newaxis] * numerator / denominator

    if constraint_type == "singly_attraction":
        # Swap: attraction-constrained instead
        # T_ij = A_j * (P_i * F_ij) / sum_k(P_k * F_kj)
        numerator = productions[:, np.newaxis] * F
        denominator = numerator.sum(axis=0, keepdims=True)
        denominator = np.maximum(denominator, 1e-10)
        T = effective_attractions[np.newaxis, :] * numerator / denominator

    elif constraint_type == "doubly":
        # Apply Furness balancing
        T, furness_diag = furness_balance(
            T, productions, effective_attractions,
            max_iterations=max_iterations,
            tolerance=convergence_threshold,
            verbose=verbose
        )
        diagnostics["furness"] = furness_diag

    # Calculate summary statistics
    total_trips = T.sum()
    diagnostics["total_trips"] = float(total_trips)
    diagnostics["avg_trip_length"] = float((T * impedance).sum() / total_trips) if total_trips > 0 else 0
    diagnostics["intrazonal_pct"] = float(np.diag(T).sum() / total_trips * 100) if total_trips > 0 else 0

    if verbose:
        print(f"  Results:")
        print(f"    Total trips: {diagnostics['total_trips']:,.0f}")
        print(f"    Average trip length: {diagnostics['avg_trip_length']:.2f} miles")
        print(f"    Intrazonal trips: {diagnostics['intrazonal_pct']:.1f}%")

    return T, diagnostics


def calibrate_friction_parameter(
    productions: np.ndarray,
    attractions: np.ndarray,
    impedance: np.ndarray,
    target_avg_trip_length: float,
    friction_function: FrictionFunction = FrictionFunction.EXPONENTIAL,
    parameter_name: str = "beta",
    initial_value: float = 0.1,
    max_iterations: int = 50,
    tolerance: float = 0.01,
    verbose: bool = False
) -> tuple[float, np.ndarray, dict]:
    """
    Calibrate friction parameter to match target average trip length.

    Uses iterative adjustment to find parameter value that produces
    the target average trip length.

    Args:
        productions: Production totals by zone
        attractions: Attraction totals by zone
        impedance: Distance/time matrix
        target_avg_trip_length: Target average trip length to match
        friction_function: Friction function type
        parameter_name: Name of parameter to calibrate ('beta', 'gamma', etc.)
        initial_value: Starting value for parameter
        max_iterations: Maximum calibration iterations
        tolerance: Acceptable relative error in trip length
        verbose: Print progress messages

    Returns:
        Tuple of (calibrated_parameter, trip_matrix, calibration_diagnostics)
    """
    param_value = initial_value

    # Adjustment rate - controls convergence speed
    # Higher values = faster but less stable
    alpha = 1.5

    diagnostics = {
        "target_avg_length": target_avg_trip_length,
        "iterations": [],
        "converged": False,
    }

    if verbose:
        print(f"  Calibrating {parameter_name} to target trip length: {target_avg_trip_length:.2f} miles")

    model_avg_length = 0  # Initialize

    for iteration in range(max_iterations):
        # Run gravity model with current parameter
        friction_params = {parameter_name: param_value}
        T, model_diag = gravity_model(
            productions, attractions, impedance,
            friction_function=friction_function,
            friction_params=friction_params,
            constraint_type="singly_production",
            verbose=False
        )

        model_avg_length = model_diag["avg_trip_length"]

        # Record iteration
        iter_record = {
            "iteration": iteration,
            "parameter": float(param_value),
            "model_avg_length": float(model_avg_length),
            "error": float(abs(model_avg_length - target_avg_trip_length) / target_avg_trip_length),
        }
        diagnostics["iterations"].append(iter_record)

        if verbose:
            print(f"    Iter {iteration}: {parameter_name}={param_value:.6f}, "
                  f"avg_length={model_avg_length:.2f} mi")

        # Check convergence
        relative_error = abs(model_avg_length - target_avg_trip_length) / target_avg_trip_length
        if relative_error < tolerance:
            diagnostics["converged"] = True
            if verbose:
                print(f"  Converged after {iteration + 1} iterations")
            break

        # Adjust parameter based on direction needed
        # For decay parameters (beta, gamma): higher value = shorter trips
        # If model trips are too long, increase parameter
        # If model trips are too short, decrease parameter
        adjustment_ratio = model_avg_length / target_avg_trip_length
        param_value = param_value * (adjustment_ratio ** alpha)

        # Bound the parameter to reasonable range
        param_value = max(0.001, min(param_value, 10.0))

    diagnostics["final_parameter"] = float(param_value)
    diagnostics["final_avg_length"] = float(model_avg_length)

    if not diagnostics["converged"] and verbose:
        print(f"  WARNING: Calibration did not converge after {max_iterations} iterations")
        print(f"           Final avg length: {model_avg_length:.2f} (target: {target_avg_trip_length:.2f})")

    # Run final model with doubly-constrained
    friction_params = {parameter_name: param_value}
    T, _ = gravity_model(
        productions, attractions, impedance,
        friction_function=friction_function,
        friction_params=friction_params,
        constraint_type="doubly",
        verbose=False
    )

    return param_value, T, diagnostics


def calculate_trip_length_distribution(
    trip_matrix: np.ndarray,
    impedance: np.ndarray,
    bins: Optional[np.ndarray] = None,
    n_bins: int = 20
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calculate trip length frequency distribution (TLFD).

    Args:
        trip_matrix: OD trip matrix
        impedance: Distance/time matrix
        bins: Optional bin edges for histogram
        n_bins: Number of bins if bins not provided

    Returns:
        Tuple of (bin_edges, trip_counts, trip_percentages)
    """
    # Flatten matrices - VECTORIZED
    trips_flat = trip_matrix.ravel()
    impedance_flat = impedance.ravel()

    # Filter to trips > 0
    mask = trips_flat > 0
    trips_flat = trips_flat[mask]
    impedance_flat = impedance_flat[mask]

    if len(trips_flat) == 0:
        if bins is None:
            bins = np.linspace(0, 10, n_bins + 1)
        return bins, np.zeros(n_bins), np.zeros(n_bins)

    if bins is None:
        bins = np.linspace(0, np.percentile(impedance_flat, 99), n_bins + 1)

    # Calculate weighted histogram
    counts, bin_edges = np.histogram(impedance_flat, bins=bins, weights=trips_flat)
    total = counts.sum()
    percentages = counts / total * 100 if total > 0 else np.zeros_like(counts)

    return bin_edges, counts, percentages


@dataclass
class GravityModelResult:
    """Container for gravity model results."""
    trip_matrix: np.ndarray
    zone_ids: np.ndarray
    productions: np.ndarray
    attractions: np.ndarray
    impedance: np.ndarray
    diagnostics: dict

    def to_dataframe(self) -> pd.DataFrame:
        """Convert trip matrix to long-form DataFrame (VECTORIZED)."""
        # VECTORIZED: Use numpy indexing instead of nested loops
        i_idx, j_idx = np.where(self.trip_matrix > 0)

        return pd.DataFrame({
            "origin_zone": self.zone_ids[i_idx],
            "dest_zone": self.zone_ids[j_idx],
            "trips": self.trip_matrix[i_idx, j_idx],
            "distance": self.impedance[i_idx, j_idx],
        })

    def summary(self) -> str:
        """Return summary statistics as string."""
        lines = [
            "Gravity Model Results",
            "=" * 40,
            f"Zones: {len(self.zone_ids)}",
            f"Total trips: {self.trip_matrix.sum():,.0f}",
            f"Average trip length: {self.diagnostics.get('avg_trip_length', 0):.2f}",
            f"Intrazonal trips: {self.diagnostics.get('intrazonal_pct', 0):.1f}%",
            f"Friction function: {self.diagnostics.get('friction_function', 'N/A')}",
            f"Constraint: {self.diagnostics.get('constraint_type', 'N/A')}",
        ]
        return "\n".join(lines)
