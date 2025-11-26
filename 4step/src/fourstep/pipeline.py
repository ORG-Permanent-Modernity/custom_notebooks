"""
4-Step Model Pipeline

Main entry point for running the complete 4-step transportation demand model.
"""

from dataclasses import dataclass, field
from typing import Optional, Literal
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd

from .trip_generation import (
    assign_generators_to_zones,
    calculate_zone_trips,
    balance_trip_ends,
    create_zone_arrays,
    TripRates
)
from .trip_distribution import (
    calculate_impedance_matrix,
    gravity_model,
    calibrate_friction_parameter,
    FrictionFunction,
    GravityModelResult
)
from .mode_choice import (
    run_mode_choice,
    ModeChoiceModel,
    ModeChoiceResult
)
from .traffic_assignment import (
    run_assignment,
    Network,
    NetworkAssignment
)


@dataclass
class FourStepModelConfig:
    """Configuration for 4-step model run."""

    # Trip generation settings
    trip_rates: Optional[TripRates] = None
    trip_purpose: Literal["all", "HBW", "HBO", "NHB"] = "all"
    time_period: Literal["daily", "AM", "PM", "midday"] = "daily"
    balance_method: Literal["attraction", "production", "average"] = "attraction"

    # Trip distribution settings
    friction_function: FrictionFunction = FrictionFunction.GAMMA
    friction_params: Optional[dict] = None
    constraint_type: Literal["singly_production", "singly_attraction", "doubly"] = "doubly"
    k_factors: Optional[np.ndarray] = None
    intrazonal_method: Literal["half_nearest", "area_based", "fixed"] = "half_nearest"
    calibrate_to_length: Optional[float] = None

    # Mode choice settings
    run_mode_choice: bool = True
    mode_choice_model: Optional[ModeChoiceModel] = None
    area_type: Optional[str] = "urban"  # "urban_core", "urban", "suburban", "rural"
    auto_ownership_rate: Optional[float] = 0.46  # Brooklyn default from ACS
    bike_ownership_rate: Optional[float] = 0.30  # ~30% own bikes
    bikeshare_coverage: Optional[float] = 0.60   # Citi Bike coverage in Brooklyn

    # Traffic assignment settings
    run_assignment: bool = False  # Requires network
    assignment_method: Literal["aon", "ue"] = "ue"
    vdf_type: str = "bpr"
    vdf_params: Optional[dict] = None

    # Output settings
    output_dir: Optional[str] = None
    verbose: bool = True


@dataclass
class FourStepModelResult:
    """Results from 4-step model run."""

    # Step 1: Trip Generation
    generators_with_zones: gpd.GeoDataFrame
    zone_trips: pd.DataFrame
    productions: np.ndarray
    attractions: np.ndarray
    zone_ids: np.ndarray

    # Step 2: Trip Distribution
    trip_matrix: np.ndarray
    impedance_matrix: np.ndarray
    distribution_diagnostics: dict

    # Step 3: Mode Choice (optional)
    mode_trips: Optional[dict] = None
    vehicle_trips: Optional[np.ndarray] = None
    mode_shares: Optional[dict] = None

    # Step 4: Traffic Assignment (optional)
    assignment_result: Optional[NetworkAssignment] = None

    # Config used
    config: Optional[FourStepModelConfig] = None

    def summary(self) -> str:
        """Generate summary report."""
        lines = [
            "=" * 60,
            "4-STEP MODEL RESULTS SUMMARY",
            "=" * 60,
            "",
            "STEP 1: TRIP GENERATION",
            "-" * 40,
            f"  Zones: {len(self.zone_ids)}",
            f"  Total productions: {self.productions.sum():,.0f}",
            f"  Total attractions: {self.attractions.sum():,.0f}",
            "",
            "STEP 2: TRIP DISTRIBUTION",
            "-" * 40,
            f"  Total trips: {self.trip_matrix.sum():,.0f}",
            f"  Average trip length: {self.distribution_diagnostics.get('avg_trip_length', 0):.2f} miles",
            f"  Intrazonal trips: {self.distribution_diagnostics.get('intrazonal_pct', 0):.1f}%",
            f"  Friction function: {self.distribution_diagnostics.get('friction_function', 'N/A')}",
        ]

        if self.mode_trips is not None:
            lines.extend([
                "",
                "STEP 3: MODE CHOICE",
                "-" * 40,
            ])
            total_person_trips = sum(m.sum() for m in self.mode_trips.values())
            for mode, trips in self.mode_trips.items():
                share = trips.sum() / total_person_trips * 100
                lines.append(f"  {mode}: {trips.sum():,.0f} ({share:.1f}%)")

            if self.vehicle_trips is not None:
                lines.append(f"  Total vehicle trips: {self.vehicle_trips.sum():,.0f}")

        if self.assignment_result is not None:
            lines.extend([
                "",
                "STEP 4: TRAFFIC ASSIGNMENT",
                "-" * 40,
                f"  Total assigned volume: {self.assignment_result.link_volumes.sum():,.0f}",
            ])
            vc = self.assignment_result.get_vc_ratios()
            lines.append(f"  Links with V/C > 1.0: {(vc > 1.0).sum()}")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)

    def to_od_dataframe(self) -> pd.DataFrame:
        """Convert trip matrix to long-form DataFrame using vectorized operations."""
        # Vectorized approach using np.where to find non-zero entries
        i_idx, j_idx = np.where(self.trip_matrix > 0)

        return pd.DataFrame({
            "origin_zone": self.zone_ids[i_idx],
            "dest_zone": self.zone_ids[j_idx],
            "trips": self.trip_matrix[i_idx, j_idx],
            "distance": self.impedance_matrix[i_idx, j_idx],
        })

    def save_results(self, output_dir: str):
        """Save results to files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save OD matrix
        od_df = self.to_od_dataframe()
        od_df.to_csv(output_path / "od_trips.csv", index=False)

        # Save zone trips
        self.zone_trips.to_csv(output_path / "zone_trips.csv", index=False)

        # Save trip matrix as numpy
        np.save(output_path / "trip_matrix.npy", self.trip_matrix)

        # Save mode trips if available
        if self.mode_trips is not None:
            for mode, matrix in self.mode_trips.items():
                np.save(output_path / f"trips_{mode}.npy", matrix)

        # Save vehicle trips if available
        if self.vehicle_trips is not None:
            np.save(output_path / "vehicle_trips.npy", self.vehicle_trips)

        # Save link volumes if available
        if self.assignment_result is not None:
            link_df = self.assignment_result.to_dataframe()
            link_df.to_csv(output_path / "link_volumes.csv", index=False)

        # Save summary
        with open(output_path / "summary.txt", "w") as f:
            f.write(self.summary())

        print(f"Results saved to {output_path}")


def run_4step_model(
    trip_generators_file: str,
    zones_file: str,
    config: Optional[FourStepModelConfig] = None,
    network_node_file: Optional[str] = None,
    network_link_file: Optional[str] = None,
    network_skim_file: Optional[str] = None,
) -> FourStepModelResult:
    """
    Run complete 4-step transportation demand model.

    Args:
        trip_generators_file: Path to trip generators CSV/GeoJSON
        zones_file: Path to zones CSV/GeoJSON with polygons
        config: Model configuration (uses defaults if None)
        network_node_file: Path to network node.csv (for assignment)
        network_link_file: Path to network link.csv (for assignment)
        network_skim_file: Path to network skim CSV (for distribution)

    Returns:
        FourStepModelResult with all outputs
    """
    if config is None:
        config = FourStepModelConfig()

    verbose = config.verbose

    # Check required input files exist
    if not Path(trip_generators_file).exists():
        raise FileNotFoundError(
            f"Trip generators file not found: {trip_generators_file}\n"
            f"Expected a CSV or GeoJSON file with columns: lat, lon, trip_gen_category, trip_gen_value"
        )
    if not Path(zones_file).exists():
        raise FileNotFoundError(
            f"Zones file not found: {zones_file}\n"
            f"Expected a CSV or GeoJSON file with columns: zone_id, geometry (WKT or native)"
        )

    # Check optional files if assignment is enabled
    if config.run_assignment:
        if network_node_file and not Path(network_node_file).exists():
            raise FileNotFoundError(
                f"Network node file not found: {network_node_file}\n"
                f"Expected GMNS format CSV with columns: node_id, x_coord, y_coord"
            )
        if network_link_file and not Path(network_link_file).exists():
            raise FileNotFoundError(
                f"Network link file not found: {network_link_file}\n"
                f"Expected GMNS format CSV with columns: link_id, from_node_id, to_node_id, length, capacity"
            )
    if network_skim_file and not Path(network_skim_file).exists():
        raise FileNotFoundError(
            f"Network skim file not found: {network_skim_file}\n"
            f"Expected CSV with columns: origin_zone, dest_zone, impedance (or distance/time)"
        )

    # =========================================================================
    # LOAD INPUT DATA
    # =========================================================================
    if verbose:
        print("=" * 60)
        print("4-STEP TRANSPORTATION DEMAND MODEL")
        print("=" * 60)
        print("\nLoading input data...")

    # Load trip generators
    if trip_generators_file.endswith(".geojson"):
        generators = gpd.read_file(trip_generators_file)
    else:
        generators = pd.read_csv(trip_generators_file)
        # Convert to GeoDataFrame if lat/lon columns exist
        if "lat" in generators.columns and "lon" in generators.columns:
            from shapely.geometry import Point
            geometry = [Point(xy) for xy in zip(generators["lon"], generators["lat"])]
            generators = gpd.GeoDataFrame(generators, geometry=geometry, crs="EPSG:4326")

    if verbose:
        print(f"  Loaded {len(generators):,} trip generators")

    # Load zones
    if zones_file.endswith(".geojson"):
        zones = gpd.read_file(zones_file)
    else:
        zones = pd.read_csv(zones_file)
        # Parse WKT geometry if present
        if "geometry" in zones.columns and isinstance(zones["geometry"].iloc[0], str):
            from shapely import wkt
            zones["geometry"] = zones["geometry"].apply(wkt.loads)

            # Auto-detect CRS from coordinate magnitudes
            sample_geom = zones["geometry"].iloc[0]
            sample_x = sample_geom.centroid.x
            sample_y = sample_geom.centroid.y

            if abs(sample_x) < 360 and abs(sample_y) < 90:
                # Looks like lat/lon (EPSG:4326)
                detected_crs = "EPSG:4326"
            elif 800000 < sample_x < 1200000 and 100000 < sample_y < 400000:
                # Looks like NY State Plane Long Island (feet) - EPSG:2263
                detected_crs = "EPSG:2263"
            elif 100000 < sample_x < 900000 and 100000 < sample_y < 900000:
                # Likely a UTM or State Plane projection (meters)
                detected_crs = "EPSG:2263"  # Default to NY State Plane for this project
            else:
                # Unknown - assume EPSG:4326 and warn
                detected_crs = "EPSG:4326"
                if verbose:
                    print(f"  WARNING: Could not auto-detect CRS from coordinates ({sample_x:.1f}, {sample_y:.1f})")
                    print(f"           Assuming EPSG:4326 - set CRS explicitly if incorrect")

            zones = gpd.GeoDataFrame(zones, geometry="geometry", crs=detected_crs)
            if verbose and detected_crs != "EPSG:4326":
                print(f"  Auto-detected zones CRS: {detected_crs}")

    if verbose:
        print(f"  Loaded {len(zones):,} zones")

    # =========================================================================
    # STEP 1: TRIP GENERATION
    # =========================================================================
    if verbose:
        print("\n" + "=" * 60)
        print("STEP 1: TRIP GENERATION")
        print("=" * 60)

    # Assign generators to zones
    generators_with_zones = assign_generators_to_zones(
        generators, zones,
        zone_id_col="zone_id",
        verbose=verbose
    )

    # Calculate zone productions and attractions
    zone_trips = calculate_zone_trips(
        generators_with_zones,
        zone_id_col="zone_id",
        trip_gen_category_col="trip_gen_category",
        trip_gen_value_col="trip_gen_value",
        trip_rates=config.trip_rates,
        trip_purpose=config.trip_purpose,
        time_period=config.time_period,
        verbose=verbose
    )

    # Balance trip ends
    zone_trips = balance_trip_ends(
        zone_trips,
        method=config.balance_method,
        verbose=verbose
    )

    # Convert to arrays
    zone_ids, productions, attractions = create_zone_arrays(zone_trips, "zone_id")

    # =========================================================================
    # STEP 2: TRIP DISTRIBUTION
    # =========================================================================
    if verbose:
        print("\n" + "=" * 60)
        print("STEP 2: TRIP DISTRIBUTION")
        print("=" * 60)

    # Load network skim if provided
    network_skim = None
    if network_skim_file is not None:
        network_skim = pd.read_csv(network_skim_file)

    # Filter zones to only those with trips
    zones_with_trips = zones[zones["zone_id"].isin(zone_ids)]

    # Calculate impedance matrix
    zone_ids_imp, impedance = calculate_impedance_matrix(
        zones_with_trips,
        zone_id_col="zone_id",
        network_skim=network_skim,
        intrazonal_method=config.intrazonal_method,
        verbose=verbose
    )

    # Reorder to match zone_ids from trip generation
    # (impedance calculation may have different order)
    zone_order = {zid: i for i, zid in enumerate(zone_ids_imp)}
    reorder_idx = [zone_order[zid] for zid in zone_ids if zid in zone_order]

    if len(reorder_idx) < len(zone_ids):
        # Some zones don't have impedance - filter
        valid_zones = [zid for zid in zone_ids if zid in zone_order]
        dropped_zones = [zid for zid in zone_ids if zid not in zone_order]
        zone_mask = np.isin(zone_ids, valid_zones)

        dropped_productions = productions[~zone_mask].sum()
        dropped_attractions = attractions[~zone_mask].sum()

        if verbose:
            print(f"  WARNING: {len(dropped_zones):,} zones dropped - missing from impedance matrix")
            print(f"           Lost {dropped_productions:,.0f} productions and {dropped_attractions:,.0f} attractions")
            print(f"           This may indicate zones outside the study area or missing centroid data")

        zone_ids = zone_ids[zone_mask]
        productions = productions[zone_mask]
        attractions = attractions[zone_mask]
        reorder_idx = [zone_order[zid] for zid in zone_ids]

    impedance = impedance[np.ix_(reorder_idx, reorder_idx)]

    # Calibrate friction parameter if target trip length specified
    if config.calibrate_to_length is not None:
        if verbose:
            print(f"\n  Calibrating to target trip length: {config.calibrate_to_length} miles")

        param_name = "beta" if config.friction_function in [
            FrictionFunction.EXPONENTIAL, FrictionFunction.GAMMA
        ] else "gamma"

        calibrated_param, trip_matrix, calib_diag = calibrate_friction_parameter(
            productions, attractions, impedance,
            target_avg_trip_length=config.calibrate_to_length,
            friction_function=config.friction_function,
            parameter_name=param_name,
            verbose=verbose
        )

        # Update friction params with calibrated value
        if config.friction_params is None:
            config.friction_params = {}
        config.friction_params[param_name] = calibrated_param

        distribution_diagnostics = calib_diag
        distribution_diagnostics["calibrated"] = True

    else:
        # Run gravity model
        trip_matrix, distribution_diagnostics = gravity_model(
            productions, attractions, impedance,
            friction_function=config.friction_function,
            friction_params=config.friction_params,
            constraint_type=config.constraint_type,
            k_factors=config.k_factors,
            verbose=verbose
        )

    # =========================================================================
    # STEP 3: MODE CHOICE
    # =========================================================================
    mode_trips = None
    vehicle_trips = None
    mode_shares = None

    if config.run_mode_choice:
        if verbose:
            print("\n" + "=" * 60)
            print("STEP 3: MODE CHOICE")
            print("=" * 60)

        mode_trips, vehicle_trips = run_mode_choice(
            trip_matrix, impedance,
            model=config.mode_choice_model,
            area_type=config.area_type,
            auto_ownership_rate=config.auto_ownership_rate,
            bike_ownership_rate=config.bike_ownership_rate,
            bikeshare_coverage=config.bikeshare_coverage,
            verbose=verbose
        )

        total_person_trips = sum(m.sum() for m in mode_trips.values())
        mode_shares = {
            mode: trips.sum() / total_person_trips
            for mode, trips in mode_trips.items()
        }

    # =========================================================================
    # STEP 4: TRAFFIC ASSIGNMENT
    # =========================================================================
    assignment_result = None

    if config.run_assignment and network_node_file and network_link_file:
        if verbose:
            print("\n" + "=" * 60)
            print("STEP 4: TRAFFIC ASSIGNMENT")
            print("=" * 60)

        # Use vehicle trips if available, otherwise person trips
        assign_matrix = vehicle_trips if vehicle_trips is not None else trip_matrix

        assignment_result = run_assignment(
            od_matrix=assign_matrix,
            zone_ids=zone_ids,
            node_file=network_node_file,
            link_file=network_link_file,
            method=config.assignment_method,
            vdf_type=config.vdf_type,
            vdf_params=config.vdf_params,
            verbose=verbose
        )

    # =========================================================================
    # COMPILE RESULTS
    # =========================================================================
    result = FourStepModelResult(
        generators_with_zones=generators_with_zones,
        zone_trips=zone_trips,
        productions=productions,
        attractions=attractions,
        zone_ids=zone_ids,
        trip_matrix=trip_matrix,
        impedance_matrix=impedance,
        distribution_diagnostics=distribution_diagnostics,
        mode_trips=mode_trips,
        vehicle_trips=vehicle_trips,
        mode_shares=mode_shares,
        assignment_result=assignment_result,
        config=config
    )

    if verbose:
        print("\n" + result.summary())

    # Save results if output directory specified
    if config.output_dir:
        result.save_results(config.output_dir)

    return result
