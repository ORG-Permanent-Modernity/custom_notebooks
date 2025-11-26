"""
Validation Module

Functions for validating 4-step model results against observed data:
- Trip length frequency distribution (TLFD) comparison
- Mode share validation against ACS data
- Production/attraction validation
- Model diagnostics summary
"""

from typing import Optional, Tuple
import numpy as np
import pandas as pd
from pathlib import Path


def compare_tlfd(
    modeled_trips: np.ndarray,
    modeled_impedance: np.ndarray,
    observed_tlfd: np.ndarray,
    observed_bins: np.ndarray,
    verbose: bool = False
) -> dict:
    """
    Compare modeled trip length frequency distribution to observed.

    Args:
        modeled_trips: OD trip matrix from model
        modeled_impedance: Distance/time matrix
        observed_tlfd: Observed trip counts or percentages by bin
        observed_bins: Bin edges for observed TLFD
        verbose: Print comparison results

    Returns:
        Dictionary with comparison metrics:
        - coincidence_ratio: Overlap measure (0-1, higher is better)
        - rmse: Root mean square error
        - r_squared: Coefficient of determination
        - avg_trip_length_model: Model average trip length
        - avg_trip_length_observed: Observed average trip length (if calculable)
    """
    # Calculate modeled TLFD using same bins
    trips_flat = modeled_trips.ravel()
    impedance_flat = modeled_impedance.ravel()

    mask = trips_flat > 0
    trips_flat = trips_flat[mask]
    impedance_flat = impedance_flat[mask]

    modeled_counts, _ = np.histogram(impedance_flat, bins=observed_bins, weights=trips_flat)

    # Normalize to percentages
    modeled_pct = modeled_counts / modeled_counts.sum() * 100 if modeled_counts.sum() > 0 else modeled_counts

    # Ensure observed is also percentages
    if observed_tlfd.sum() > 1.5:  # Likely counts, not percentages
        observed_pct = observed_tlfd / observed_tlfd.sum() * 100
    else:
        observed_pct = observed_tlfd * 100 if observed_tlfd.max() <= 1 else observed_tlfd

    # Calculate coincidence ratio
    # CR = sum(min(modeled_pct, observed_pct)) / sum(observed_pct)
    coincidence_ratio = np.minimum(modeled_pct, observed_pct).sum() / observed_pct.sum()

    # Calculate RMSE
    rmse = np.sqrt(np.mean((modeled_pct - observed_pct) ** 2))

    # Calculate R-squared
    ss_res = np.sum((modeled_pct - observed_pct) ** 2)
    ss_tot = np.sum((observed_pct - observed_pct.mean()) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    # Calculate average trip lengths
    bin_centers = (observed_bins[:-1] + observed_bins[1:]) / 2
    avg_trip_length_model = (modeled_pct * bin_centers).sum() / modeled_pct.sum() if modeled_pct.sum() > 0 else 0
    avg_trip_length_observed = (observed_pct * bin_centers).sum() / observed_pct.sum() if observed_pct.sum() > 0 else 0

    results = {
        "coincidence_ratio": float(coincidence_ratio),
        "rmse": float(rmse),
        "r_squared": float(r_squared),
        "avg_trip_length_model": float(avg_trip_length_model),
        "avg_trip_length_observed": float(avg_trip_length_observed),
        "modeled_pct": modeled_pct,
        "observed_pct": observed_pct,
        "bins": observed_bins,
    }

    if verbose:
        print("Trip Length Frequency Distribution Comparison")
        print("=" * 50)
        print(f"  Coincidence Ratio: {coincidence_ratio:.3f} (1.0 = perfect match)")
        print(f"  RMSE: {rmse:.2f}%")
        print(f"  R-squared: {r_squared:.3f}")
        print(f"  Avg Trip Length (model): {avg_trip_length_model:.2f}")
        print(f"  Avg Trip Length (observed): {avg_trip_length_observed:.2f}")

    return results


def validate_mode_shares(
    model_mode_shares: dict,
    acs_mode_shares: Optional[dict] = None,
    acs_file: Optional[str] = None,
    verbose: bool = False
) -> dict:
    """
    Compare modeled mode shares to ACS (American Community Survey) data.

    Args:
        model_mode_shares: Dictionary of mode -> share (0-1) from model
        acs_mode_shares: Dictionary of mode -> share from ACS (optional)
        acs_file: Path to ACS commute mode JSON file (optional)
        verbose: Print comparison

    Returns:
        Dictionary with comparison results
    """
    # Default ACS mode shares for NYC (2019 ACS 5-year estimates for Brooklyn)
    default_acs_shares = {
        "auto_driver": 0.22,
        "auto_passenger": 0.04,
        "transit": 0.57,
        "walk": 0.10,
        "bike": 0.02,
        "other": 0.05,
    }

    if acs_mode_shares is not None:
        observed = acs_mode_shares
    elif acs_file is not None:
        import json
        with open(acs_file, 'r') as f:
            observed = json.load(f)
    else:
        observed = default_acs_shares

    # Map model modes to observed modes if needed
    mode_mapping = {
        "auto_driver": ["auto_driver", "drove_alone", "car_truck_van_alone"],
        "auto_passenger": ["auto_passenger", "carpooled", "car_truck_van_carpooled"],
        "transit": ["transit", "public_transit", "public_transportation"],
        "walk": ["walk", "walked"],
        "bike": ["bike", "bicycle"],
    }

    # Calculate comparison metrics
    comparison = []
    total_abs_diff = 0

    for model_mode, model_share in model_mode_shares.items():
        # Find matching observed mode
        obs_share = None
        for obs_mode in mode_mapping.get(model_mode, [model_mode]):
            if obs_mode in observed:
                obs_share = observed[obs_mode]
                break

        if obs_share is None:
            obs_share = 0

        diff = model_share - obs_share
        pct_diff = (diff / obs_share * 100) if obs_share > 0 else float('inf')

        comparison.append({
            "mode": model_mode,
            "model_share": model_share,
            "observed_share": obs_share,
            "difference": diff,
            "pct_difference": pct_diff,
        })

        total_abs_diff += abs(diff)

    results = {
        "comparison": comparison,
        "total_absolute_difference": total_abs_diff,
        "model_shares": model_mode_shares,
        "observed_shares": observed,
    }

    if verbose:
        print("Mode Share Validation")
        print("=" * 60)
        print(f"{'Mode':<20} {'Model':>10} {'Observed':>10} {'Diff':>10}")
        print("-" * 60)
        for c in comparison:
            print(f"{c['mode']:<20} {c['model_share']*100:>9.1f}% {c['observed_share']*100:>9.1f}% {c['difference']*100:>+9.1f}%")
        print("-" * 60)
        print(f"Total absolute difference: {total_abs_diff*100:.1f}%")

    return results


def validate_productions(
    zone_productions: pd.DataFrame,
    acs_workers_file: Optional[str] = None,
    zone_id_col: str = "zone_id",
    verbose: bool = False
) -> dict:
    """
    Compare modeled productions to ACS workers by residence.

    Args:
        zone_productions: DataFrame with zone_id and production columns
        acs_workers_file: Path to ACS workers by residence data
        zone_id_col: Zone ID column name
        verbose: Print comparison

    Returns:
        Comparison results dictionary
    """
    results = {
        "total_model_productions": float(zone_productions["production"].sum()),
        "zones_with_production": int((zone_productions["production"] > 0).sum()),
        "validation_available": False,
    }

    if acs_workers_file is not None and Path(acs_workers_file).exists():
        acs_data = pd.read_csv(acs_workers_file)
        results["validation_available"] = True
        # Add comparison logic here when ACS data format is known

    if verbose:
        print("Production Validation")
        print("=" * 50)
        print(f"  Total model productions: {results['total_model_productions']:,.0f}")
        print(f"  Zones with production: {results['zones_with_production']}")
        if not results["validation_available"]:
            print("  (No ACS data available for comparison)")

    return results


def model_diagnostics(
    result,  # FourStepModelResult object
    verbose: bool = True
) -> dict:
    """
    Generate comprehensive model diagnostics.

    Args:
        result: FourStepModelResult object from pipeline
        verbose: Print diagnostics

    Returns:
        Dictionary with all diagnostic metrics
    """
    diagnostics = {}

    # Trip Generation diagnostics
    diagnostics["trip_generation"] = {
        "n_zones": len(result.zone_ids),
        "total_productions": float(result.productions.sum()),
        "total_attractions": float(result.attractions.sum()),
        "pa_ratio": float(result.productions.sum() / result.attractions.sum())
        if result.attractions.sum() > 0 else float('inf'),
        "zones_with_zero_production": int((result.productions == 0).sum()),
        "zones_with_zero_attraction": int((result.attractions == 0).sum()),
        "max_production": float(result.productions.max()),
        "max_attraction": float(result.attractions.max()),
    }

    # Trip Distribution diagnostics
    diagnostics["trip_distribution"] = {
        "total_trips": float(result.trip_matrix.sum()),
        "avg_trip_length": result.distribution_diagnostics.get("avg_trip_length", 0),
        "intrazonal_pct": result.distribution_diagnostics.get("intrazonal_pct", 0),
        "friction_function": result.distribution_diagnostics.get("friction_function", "N/A"),
        "constraint_type": result.distribution_diagnostics.get("constraint_type", "N/A"),
        "max_od_flow": float(result.trip_matrix.max()),
        "nonzero_od_pairs": int((result.trip_matrix > 0).sum()),
        "sparsity_pct": float((result.trip_matrix == 0).sum() / result.trip_matrix.size * 100),
    }

    # Check for Furness convergence
    if "furness" in result.distribution_diagnostics:
        furness = result.distribution_diagnostics["furness"]
        diagnostics["trip_distribution"]["furness_converged"] = furness.get("converged", False)
        diagnostics["trip_distribution"]["furness_iterations"] = furness.get("iterations", 0)

    # Mode Choice diagnostics (if available)
    if result.mode_trips is not None:
        total_person_trips = sum(m.sum() for m in result.mode_trips.values())
        diagnostics["mode_choice"] = {
            "total_person_trips": float(total_person_trips),
            "mode_shares": {
                mode: float(trips.sum() / total_person_trips)
                for mode, trips in result.mode_trips.items()
            },
        }
        if result.vehicle_trips is not None:
            diagnostics["mode_choice"]["total_vehicle_trips"] = float(result.vehicle_trips.sum())
            diagnostics["mode_choice"]["avg_occupancy"] = (
                total_person_trips / result.vehicle_trips.sum()
                if result.vehicle_trips.sum() > 0 else 0
            )

    # Traffic Assignment diagnostics (if available)
    if result.assignment_result is not None:
        vc_ratios = result.assignment_result.get_vc_ratios()
        diagnostics["traffic_assignment"] = {
            "total_vmt": float((result.assignment_result.link_volumes *
                               result.assignment_result.network.links["length"].values).sum()),
            "total_vht": float((result.assignment_result.link_volumes *
                               result.assignment_result.link_times).sum() / 60),  # Convert to hours
            "avg_vc_ratio": float(vc_ratios.mean()),
            "max_vc_ratio": float(vc_ratios.max()),
            "links_over_capacity": int((vc_ratios > 1.0).sum()),
            "links_congested": int((vc_ratios > 0.8).sum()),
        }

    if verbose:
        _print_diagnostics(diagnostics)

    return diagnostics


def _print_diagnostics(diagnostics: dict):
    """Print formatted diagnostics."""
    print("\n" + "=" * 70)
    print("MODEL DIAGNOSTICS SUMMARY")
    print("=" * 70)

    # Trip Generation
    tg = diagnostics.get("trip_generation", {})
    print("\nTRIP GENERATION")
    print("-" * 50)
    print(f"  Zones: {tg.get('n_zones', 'N/A')}")
    print(f"  Total productions: {tg.get('total_productions', 0):,.0f}")
    print(f"  Total attractions: {tg.get('total_attractions', 0):,.0f}")
    print(f"  P/A ratio: {tg.get('pa_ratio', 0):.3f}")
    if tg.get('zones_with_zero_production', 0) > 0:
        print(f"  WARNING: {tg['zones_with_zero_production']} zones with zero production")
    if tg.get('zones_with_zero_attraction', 0) > 0:
        print(f"  WARNING: {tg['zones_with_zero_attraction']} zones with zero attraction")

    # Trip Distribution
    td = diagnostics.get("trip_distribution", {})
    print("\nTRIP DISTRIBUTION")
    print("-" * 50)
    print(f"  Total trips: {td.get('total_trips', 0):,.0f}")
    print(f"  Average trip length: {td.get('avg_trip_length', 0):.2f} miles")
    print(f"  Intrazonal trips: {td.get('intrazonal_pct', 0):.1f}%")
    print(f"  Friction function: {td.get('friction_function', 'N/A')}")
    print(f"  OD matrix sparsity: {td.get('sparsity_pct', 0):.1f}%")
    if not td.get("furness_converged", True):
        print(f"  WARNING: Furness balancing did not converge")

    # Mode Choice
    mc = diagnostics.get("mode_choice")
    if mc:
        print("\nMODE CHOICE")
        print("-" * 50)
        print(f"  Total person trips: {mc.get('total_person_trips', 0):,.0f}")
        if mc.get("total_vehicle_trips"):
            print(f"  Total vehicle trips: {mc['total_vehicle_trips']:,.0f}")
            print(f"  Average occupancy: {mc.get('avg_occupancy', 0):.2f}")
        print("  Mode shares:")
        for mode, share in mc.get("mode_shares", {}).items():
            print(f"    {mode}: {share*100:.1f}%")

    # Traffic Assignment
    ta = diagnostics.get("traffic_assignment")
    if ta:
        print("\nTRAFFIC ASSIGNMENT")
        print("-" * 50)
        print(f"  Total VMT: {ta.get('total_vmt', 0):,.0f} miles")
        print(f"  Total VHT: {ta.get('total_vht', 0):,.0f} hours")
        print(f"  Average V/C ratio: {ta.get('avg_vc_ratio', 0):.2f}")
        print(f"  Max V/C ratio: {ta.get('max_vc_ratio', 0):.2f}")
        if ta.get("links_over_capacity", 0) > 0:
            print(f"  WARNING: {ta['links_over_capacity']} links over capacity (V/C > 1.0)")

    print("\n" + "=" * 70)


def reasonableness_checks(
    result,  # FourStepModelResult
    verbose: bool = True
) -> dict:
    """
    Perform reasonableness checks on model results.

    Args:
        result: FourStepModelResult object
        verbose: Print warnings and checks

    Returns:
        Dictionary with check results and warnings
    """
    checks = {
        "passed": [],
        "warnings": [],
        "errors": [],
    }

    # Check 1: Total trips should be reasonable
    total_trips = result.trip_matrix.sum()
    n_zones = len(result.zone_ids)
    trips_per_zone = total_trips / n_zones if n_zones > 0 else 0

    if trips_per_zone < 10:
        checks["warnings"].append(f"Very low trips per zone ({trips_per_zone:.1f})")
    elif trips_per_zone > 100000:
        checks["warnings"].append(f"Very high trips per zone ({trips_per_zone:.1f})")
    else:
        checks["passed"].append("Trips per zone within reasonable range")

    # Check 2: Average trip length should be reasonable (1-20 miles for urban)
    avg_length = result.distribution_diagnostics.get("avg_trip_length", 0)
    if avg_length < 0.5:
        checks["warnings"].append(f"Average trip length very short ({avg_length:.2f} mi)")
    elif avg_length > 30:
        checks["warnings"].append(f"Average trip length very long ({avg_length:.2f} mi)")
    else:
        checks["passed"].append(f"Average trip length reasonable ({avg_length:.2f} mi)")

    # Check 3: Intrazonal percentage should be 5-25% typically
    intrazonal_pct = result.distribution_diagnostics.get("intrazonal_pct", 0)
    if intrazonal_pct < 2:
        checks["warnings"].append(f"Intrazonal trips very low ({intrazonal_pct:.1f}%)")
    elif intrazonal_pct > 40:
        checks["warnings"].append(f"Intrazonal trips very high ({intrazonal_pct:.1f}%)")
    else:
        checks["passed"].append(f"Intrazonal percentage reasonable ({intrazonal_pct:.1f}%)")

    # Check 4: Mode shares should be plausible (if mode choice was run)
    if result.mode_shares:
        auto_share = result.mode_shares.get("auto_driver", 0) + result.mode_shares.get("auto_passenger", 0)
        transit_share = result.mode_shares.get("transit", 0)

        if auto_share > 0.95:
            checks["warnings"].append(f"Auto mode share very high ({auto_share*100:.1f}%)")
        if transit_share > 0.8:
            checks["warnings"].append(f"Transit mode share very high ({transit_share*100:.1f}%)")

        checks["passed"].append("Mode shares calculated")

    # Check 5: P/A balance
    pa_ratio = result.productions.sum() / result.attractions.sum() if result.attractions.sum() > 0 else float('inf')
    if abs(pa_ratio - 1.0) > 0.01:
        checks["warnings"].append(f"Productions and attractions not balanced (ratio: {pa_ratio:.4f})")
    else:
        checks["passed"].append("Productions and attractions balanced")

    if verbose:
        print("\nREASONABLENESS CHECKS")
        print("=" * 50)
        print(f"\nPassed ({len(checks['passed'])}):")
        for item in checks["passed"]:
            print(f"  [OK] {item}")

        if checks["warnings"]:
            print(f"\nWarnings ({len(checks['warnings'])}):")
            for item in checks["warnings"]:
                print(f"  [!] {item}")

        if checks["errors"]:
            print(f"\nErrors ({len(checks['errors'])}):")
            for item in checks["errors"]:
                print(f"  [X] {item}")

    return checks
