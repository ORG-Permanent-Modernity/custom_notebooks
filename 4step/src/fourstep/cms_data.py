"""
NYC Citywide Mobility Survey (CMS) Data Processing Module

Helper functions for extracting mode share statistics from CMS survey data
to calibrate mode choice models.

Data source: NYC DOT Citywide Mobility Survey (2019)
Available at: https://data.cityofnewyork.us

The CMS provides observed travel behavior data for NYC residents including:
- Trip-level data with modes, distances, durations
- Person-level demographics and vehicle/bike access
- Household-level characteristics
- Survey zone geographies
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Union

import numpy as np
import pandas as pd


# CMS 2019 mode_type codes (inferred from data patterns)
# Based on analysis of trip_distance, trip_duration, and sustainable_mode flag
MODE_TYPE_CODES = {
    1: "taxi",              # Taxi/hired car (not sustainable, ~5 mi, 27 min)
    2: "tnc",               # TNC/ride-hail (not sustainable, ~10 mi, 29 min)
    3: "commuter_rail",     # Commuter rail/ferry (sustainable, ~10 mi, 36 min)
    4: "bus",               # Bus transit (sustainable, ~4 mi, 28 min)
    5: "ferry",             # Ferry (sustainable, ~8 mi, 42 min)
    6: "subway",            # Subway/rail (sustainable, ~4 mi, 39 min)
    7: "auto",              # Auto/private vehicle (not sustainable, ~6 mi, 26 min)
    8: "bike",              # Bicycle (sustainable, ~3 mi, 25 min)
    9: "walk",              # Walk (sustainable, ~0.6 mi, 12 min)
    10: "airplane",         # Airplane/long distance (~86 mi)
    995: "missing",         # Missing/excluded (no weight)
}

# Grouped mode type codes for r_mode_type_nyc (from 2022 codebook)
GROUPED_MODE_CODES = {
    1: "vehicle",
    2: "bus",
    3: "rail",
    4: "walk",
    5: "bike",
    6: "other",
    995: "missing",
}

# Mapping from detailed mode codes to our model modes
# Note: "auto" mode requires checking the 'driver' column for driver/passenger split
MODE_MODEL_MAPPING = {
    # Auto modes - "auto" is special, needs driver column check
    "auto": "auto",  # Will be split into auto_driver/auto_passenger using driver column
    "taxi": "taxi_tnc",
    "tnc": "taxi_tnc",
    # Transit modes
    "subway": "transit",
    "bus": "transit",
    "commuter_rail": "transit",
    "ferry": "transit",
    # Active modes
    "walk": "walk",
    "bike": "bike",
    # Excluded
    "airplane": None,
    "missing": None,
}

# Driver column values (CMS coding)
DRIVER_CODES = {
    1: "driver",      # Person was driving
    2: "passenger",   # Person was a passenger
    3: "both",        # Switched during trip (treat as driver)
    995: "missing",   # Missing response
}

# CMS Survey Zones
CMS_ZONES = {
    "Inner Brooklyn": ["Inner Brooklyn"],
    "Outer Brooklyn": ["Outer Brooklyn"],
    "Manhattan Core": ["Manhattan Core"],
    "Upper Manhattan": ["Upper Manhattan"],
    "Inner Queens": ["Inner Queens"],
    "Middle Queens": ["Middle Queens"],
    "Outer Queens": ["Outer Queens"],
    "Southern Bronx": ["Southern Bronx"],
    "Northern Bronx": ["Northern Bronx"],
    "Staten Island": ["Staten Island"],
    "JFK": ["JFK"],
    "LGA": ["LGA"],
}

# Brooklyn zones for filtering
BROOKLYN_ZONES = ["Inner Brooklyn", "Outer Brooklyn"]


@dataclass
class CMSModeShares:
    """Container for CMS mode share statistics."""
    auto_driver: float
    auto_passenger: float  # Includes private vehicle passengers + taxi/TNC
    transit: float
    walk: float
    bike: float
    total_trips: float
    total_weighted_trips: float
    source_zones: List[str]

    def to_dict(self) -> Dict[str, float]:
        """Return mode shares as a dictionary."""
        return {
            "auto_driver": self.auto_driver,
            "auto_passenger": self.auto_passenger,
            "transit": self.transit,
            "walk": self.walk,
            "bike": self.bike,
        }

    def combined_auto(self) -> float:
        """Total auto share (driver + passenger including taxi/TNC)."""
        return self.auto_driver + self.auto_passenger

    def combined_bike_personal_share(self, personal_share_of_bike: float = 0.5) -> float:
        """Estimate personal bike share from total bike share."""
        return self.bike * personal_share_of_bike

    def combined_bike_share_share(self, bikeshare_share_of_bike: float = 0.5) -> float:
        """Estimate bike share from total bike share."""
        return self.bike * bikeshare_share_of_bike


@dataclass
class CMSOwnershipStats:
    """Container for vehicle and bike ownership statistics."""
    auto_ownership_rate: float  # Fraction of households with 1+ vehicles
    avg_vehicles_per_hh: float
    bike_ownership_rate: float  # Fraction of households with 1+ bikes
    avg_bikes_per_hh: float
    sample_size: int


def load_cms_trips(
    data_dir: Union[str, Path] = "input_data/cms",
    year: int = 2019
) -> pd.DataFrame:
    """
    Load CMS trip data.

    Args:
        data_dir: Directory containing CMS data files
        year: Survey year (default 2019)

    Returns:
        DataFrame with trip records
    """
    data_dir = Path(data_dir)
    trip_file = data_dir / f"Citywide_Mobility_Survey_-_Trip_{year}.csv"

    if not trip_file.exists():
        raise FileNotFoundError(f"CMS trip file not found: {trip_file}")

    return pd.read_csv(trip_file)


def load_cms_persons(
    data_dir: Union[str, Path] = "input_data/cms",
    year: int = 2019
) -> pd.DataFrame:
    """
    Load CMS person data.

    Args:
        data_dir: Directory containing CMS data files
        year: Survey year (default 2019)

    Returns:
        DataFrame with person records
    """
    data_dir = Path(data_dir)
    person_file = data_dir / f"Citywide_Mobility_Survey_-_Person_{year}.csv"

    if not person_file.exists():
        raise FileNotFoundError(f"CMS person file not found: {person_file}")

    return pd.read_csv(person_file)


def load_cms_households(
    data_dir: Union[str, Path] = "input_data/cms",
    year: int = 2019
) -> pd.DataFrame:
    """
    Load CMS household data.

    Args:
        data_dir: Directory containing CMS data files
        year: Survey year (default 2019)

    Returns:
        DataFrame with household records
    """
    data_dir = Path(data_dir)
    hh_file = data_dir / f"Citywide_Mobility_Survey_-_Household_{year}.csv"

    if not hh_file.exists():
        raise FileNotFoundError(f"CMS household file not found: {hh_file}")

    return pd.read_csv(hh_file)


def filter_brooklyn_trips(
    trips: pd.DataFrame,
    origin_col: str = "o_cms_zone",
    dest_col: str = "d_cms_zone",
    home_zone_col: str = "home_cms_zone",
    filter_type: str = "home_based"
) -> pd.DataFrame:
    """
    Filter trips to Brooklyn-related records.

    Args:
        trips: CMS trip DataFrame
        origin_col: Column name for origin zone
        dest_col: Column name for destination zone
        home_zone_col: Column name for person's home zone (trip data uses 'home_cms_zone')
        filter_type: How to filter:
            - "home_based": Trips where home zone is Brooklyn (recommended)
            - "origin": Trips originating in Brooklyn
            - "destination": Trips ending in Brooklyn
            - "either": Trips with either end in Brooklyn
            - "both": Trips with both ends in Brooklyn

    Returns:
        Filtered DataFrame
    """
    # Map zone names to check for Brooklyn
    brooklyn_mask_origin = trips[origin_col].isin(BROOKLYN_ZONES)
    brooklyn_mask_dest = trips[dest_col].isin(BROOKLYN_ZONES)
    brooklyn_mask_home = trips[home_zone_col].isin(BROOKLYN_ZONES)

    if filter_type == "home_based":
        return trips[brooklyn_mask_home].copy()
    elif filter_type == "origin":
        return trips[brooklyn_mask_origin].copy()
    elif filter_type == "destination":
        return trips[brooklyn_mask_dest].copy()
    elif filter_type == "either":
        return trips[brooklyn_mask_origin | brooklyn_mask_dest].copy()
    elif filter_type == "both":
        return trips[brooklyn_mask_origin & brooklyn_mask_dest].copy()
    else:
        raise ValueError(f"Unknown filter_type: {filter_type}")


def map_mode_to_model(mode_type: int) -> Optional[str]:
    """
    Map CMS mode_type code to our mode choice model categories.

    Args:
        mode_type: CMS mode_type code

    Returns:
        Model mode name or None if excluded
    """
    mode_name = MODE_TYPE_CODES.get(mode_type, "missing")
    return MODE_MODEL_MAPPING.get(mode_name)


def calculate_mode_shares(
    trips: pd.DataFrame,
    weight_col: str = "trip_weight",
    mode_col: str = "mode_type",
    driver_col: str = "driver",
    exclude_missing: bool = True
) -> CMSModeShares:
    """
    Calculate weighted mode shares from CMS trip data.

    Properly handles the driver/passenger split for private vehicle trips
    using the 'driver' column.

    Args:
        trips: DataFrame with trip records
        weight_col: Column name for survey weights
        mode_col: Column name for mode type
        driver_col: Column name for driver/passenger indicator
        exclude_missing: Whether to exclude missing/invalid modes

    Returns:
        CMSModeShares with calculated statistics
    """
    # Filter to valid weights
    valid_trips = trips[trips[weight_col] > 0].copy()

    # Map mode codes to intermediate categories
    valid_trips["model_mode"] = valid_trips[mode_col].apply(map_mode_to_model)

    if exclude_missing:
        valid_trips = valid_trips[valid_trips["model_mode"].notna()]

    total_weighted = valid_trips[weight_col].sum()

    # Calculate shares for each mode category
    shares = {}

    # Walk
    walk_mask = valid_trips["model_mode"] == "walk"
    shares["walk"] = valid_trips.loc[walk_mask, weight_col].sum() / total_weighted

    # Transit
    transit_mask = valid_trips["model_mode"] == "transit"
    shares["transit"] = valid_trips.loc[transit_mask, weight_col].sum() / total_weighted

    # Bike
    bike_mask = valid_trips["model_mode"] == "bike"
    shares["bike"] = valid_trips.loc[bike_mask, weight_col].sum() / total_weighted

    # Taxi/TNC (for-hire vehicles) - will be added to auto_passenger
    taxi_mask = valid_trips["model_mode"] == "taxi_tnc"
    taxi_tnc_weight = valid_trips.loc[taxi_mask, weight_col].sum()

    # Private vehicle - split by driver column
    # driver=1 means person was driving, driver=2 means passenger
    auto_mask = valid_trips["model_mode"] == "auto"
    auto_trips = valid_trips[auto_mask]

    if driver_col in auto_trips.columns:
        # Driver (code 1) or both (code 3, treat as driver)
        driver_mask = auto_trips[driver_col].isin([1, 3])
        shares["auto_driver"] = auto_trips.loc[driver_mask, weight_col].sum() / total_weighted

        # Passenger (code 2) + taxi/TNC
        passenger_mask = auto_trips[driver_col] == 2
        private_passenger_weight = auto_trips.loc[passenger_mask, weight_col].sum()
        shares["auto_passenger"] = (private_passenger_weight + taxi_tnc_weight) / total_weighted
    else:
        # Fallback if no driver column - assume all are drivers, taxi/tnc are passengers
        shares["auto_driver"] = auto_trips[weight_col].sum() / total_weighted
        shares["auto_passenger"] = taxi_tnc_weight / total_weighted

    # Get unique source zones (trip data uses home_cms_zone)
    zone_col = "home_cms_zone" if "home_cms_zone" in valid_trips.columns else "cms_zone"
    source_zones = valid_trips[zone_col].unique().tolist() if zone_col in valid_trips.columns else []

    return CMSModeShares(
        auto_driver=shares.get("auto_driver", 0.0),
        auto_passenger=shares.get("auto_passenger", 0.0),
        transit=shares.get("transit", 0.0),
        walk=shares.get("walk", 0.0),
        bike=shares.get("bike", 0.0),
        total_trips=len(valid_trips),
        total_weighted_trips=total_weighted,
        source_zones=source_zones,
    )


def get_brooklyn_mode_shares(
    data_dir: Union[str, Path] = "input_data/cms",
    year: int = 2019,
    filter_type: str = "home_based",
    verbose: bool = True
) -> CMSModeShares:
    """
    Calculate mode shares for Brooklyn trips from CMS data.

    This is the main function to use for getting calibration targets.

    Args:
        data_dir: Directory containing CMS data files
        year: Survey year
        filter_type: How to filter Brooklyn trips (see filter_brooklyn_trips)
        verbose: Whether to print summary statistics

    Returns:
        CMSModeShares with Brooklyn mode share statistics
    """
    # Load data
    trips = load_cms_trips(data_dir, year)

    # Filter to Brooklyn
    brooklyn_trips = filter_brooklyn_trips(trips, filter_type=filter_type)

    # Calculate shares
    shares = calculate_mode_shares(brooklyn_trips)

    if verbose:
        print(f"\n=== Brooklyn Mode Shares (CMS {year}) ===")
        print(f"Filter type: {filter_type}")
        print(f"Sample size: {shares.total_trips:,.0f} trips")
        print(f"Weighted trips: {shares.total_weighted_trips:,.0f}")
        print(f"\nMode Shares:")
        print(f"  Auto Driver:    {shares.auto_driver:.1%}")
        print(f"  Auto Passenger: {shares.auto_passenger:.1%}  (includes taxi/TNC)")
        print(f"  Transit:        {shares.transit:.1%}")
        print(f"  Walk:           {shares.walk:.1%}")
        print(f"  Bike:           {shares.bike:.1%}")
        print(f"\nCombined:")
        print(f"  Total Auto:     {shares.combined_auto():.1%}")

    return shares


def get_ownership_statistics(
    data_dir: Union[str, Path] = "input_data/cms",
    year: int = 2019,
    zone_filter: Optional[List[str]] = None,
    verbose: bool = True
) -> CMSOwnershipStats:
    """
    Calculate vehicle and bike ownership statistics from CMS household data.

    Args:
        data_dir: Directory containing CMS data files
        year: Survey year
        zone_filter: List of CMS zones to include (None = all)
        verbose: Whether to print summary statistics

    Returns:
        CMSOwnershipStats with ownership rates
    """
    households = load_cms_households(data_dir, year)

    # Determine zone column name (varies by year)
    zone_col = "reported_home_cms_zone" if "reported_home_cms_zone" in households.columns else "cms_zone"

    # Filter by zone if specified
    if zone_filter:
        households = households[households[zone_col].isin(zone_filter)]

    # Vehicle ownership
    valid_vehicles = households[households["num_vehicles"] >= 0]
    has_vehicle = (valid_vehicles["num_vehicles"] > 0).mean()
    avg_vehicles = valid_vehicles["num_vehicles"].mean()

    # Bike ownership
    valid_bikes = households[households["num_bicycles"] >= 0]
    has_bike = (valid_bikes["num_bicycles"] > 0).mean()
    avg_bikes = valid_bikes["num_bicycles"].mean()

    stats = CMSOwnershipStats(
        auto_ownership_rate=has_vehicle,
        avg_vehicles_per_hh=avg_vehicles,
        bike_ownership_rate=has_bike,
        avg_bikes_per_hh=avg_bikes,
        sample_size=len(households),
    )

    if verbose:
        zones_desc = ", ".join(zone_filter) if zone_filter else "All NYC"
        print(f"\n=== Ownership Statistics (CMS {year}) ===")
        print(f"Zones: {zones_desc}")
        print(f"Sample size: {stats.sample_size:,} households")
        print(f"\nVehicle Ownership:")
        print(f"  Has 1+ vehicles: {stats.auto_ownership_rate:.1%}")
        print(f"  Avg vehicles/HH: {stats.avg_vehicles_per_hh:.2f}")
        print(f"\nBike Ownership:")
        print(f"  Has 1+ bikes:    {stats.bike_ownership_rate:.1%}")
        print(f"  Avg bikes/HH:    {stats.avg_bikes_per_hh:.2f}")

    return stats


def get_brooklyn_ownership(
    data_dir: Union[str, Path] = "input_data/cms",
    year: int = 2019,
    verbose: bool = True
) -> CMSOwnershipStats:
    """
    Get vehicle and bike ownership statistics for Brooklyn.

    Args:
        data_dir: Directory containing CMS data files
        year: Survey year
        verbose: Whether to print summary statistics

    Returns:
        CMSOwnershipStats for Brooklyn households
    """
    return get_ownership_statistics(
        data_dir=data_dir,
        year=year,
        zone_filter=BROOKLYN_ZONES,
        verbose=verbose,
    )


def get_trip_length_distribution(
    trips: pd.DataFrame,
    mode_col: str = "mode_type",
    distance_col: str = "trip_distance",
    weight_col: str = "trip_weight",
    bins: List[float] = None
) -> Dict[str, pd.DataFrame]:
    """
    Calculate trip length frequency distribution by mode.

    Useful for calibrating friction factors in gravity model.

    Args:
        trips: DataFrame with trip records
        mode_col: Column name for mode type
        distance_col: Column name for trip distance (miles)
        weight_col: Column name for survey weights
        bins: Distance bins (default: 0-0.5, 0.5-1, 1-2, 2-5, 5-10, 10-20, 20+)

    Returns:
        Dict mapping mode names to DataFrames with TLFD
    """
    if bins is None:
        bins = [0, 0.5, 1, 2, 5, 10, 20, 100]

    # Filter valid trips
    valid_trips = trips[(trips[weight_col] > 0) & (trips[distance_col] >= 0)].copy()

    # Map modes to model categories
    valid_trips["model_mode"] = valid_trips[mode_col].apply(map_mode_to_model)
    valid_trips = valid_trips[valid_trips["model_mode"].notna()]

    # Bin distances
    valid_trips["distance_bin"] = pd.cut(valid_trips[distance_col], bins=bins)

    results = {}
    for mode in valid_trips["model_mode"].unique():
        mode_trips = valid_trips[valid_trips["model_mode"] == mode]

        # Weighted histogram
        tlfd = mode_trips.groupby("distance_bin")[weight_col].sum()
        tlfd = tlfd / tlfd.sum()  # Normalize to shares

        results[mode] = tlfd.reset_index()
        results[mode].columns = ["distance_bin", "share"]

    return results


def get_person_bike_usage(
    data_dir: Union[str, Path] = "input_data/cms",
    year: int = 2019,
    zone_filter: Optional[List[str]] = None,
    verbose: bool = True
) -> Dict[str, float]:
    """
    Get bike usage statistics from person-level CMS data.

    Args:
        data_dir: Directory containing CMS data files
        year: Survey year
        zone_filter: List of CMS zones to include (None = all)
        verbose: Whether to print summary statistics

    Returns:
        Dict with bike usage rates
    """
    persons = load_cms_persons(data_dir, year)

    # Determine zone column name
    zone_col = "cms_zone" if "cms_zone" in persons.columns else "reported_home_cms_zone"

    if zone_filter:
        persons = persons[persons[zone_col].isin(zone_filter)]

    # Check for bike-related columns
    bike_cols = [c for c in persons.columns if 'bike' in c.lower()]

    results = {}

    # Bike frequency (if available)
    # CMS coding: 1=5+/wk, 2=4/wk, 3=2-3/wk, 4=1/wk, 5=1-3/mo, 6=<monthly, 995=missing, 996=never
    if "bike_freq" in persons.columns:
        # Exclude missing (995) and never (996) and system missing (-9998)
        valid_bikers = persons[
            (persons["bike_freq"] >= 1) &
            (persons["bike_freq"] <= 6)
        ]
        # Anyone who bikes at all (codes 1-6)
        results["bike_user_rate"] = len(valid_bikers) / len(persons)

        # Regular bikers (at least weekly = codes 1-4)
        regular_bikers = persons[
            (persons["bike_freq"] >= 1) &
            (persons["bike_freq"] <= 4)
        ]
        results["regular_bike_user_rate"] = len(regular_bikers) / len(persons)

    # Citi Bike usage (if available)
    # Same coding scheme
    if "bike_share_citi_bike" in persons.columns:
        # Anyone who uses Citi Bike at all
        citibike_users = persons[
            (persons["bike_share_citi_bike"] >= 1) &
            (persons["bike_share_citi_bike"] <= 6)
        ]
        results["citibike_user_rate"] = len(citibike_users) / len(persons)

        # Regular Citi Bike users (at least weekly)
        regular_citibike = persons[
            (persons["bike_share_citi_bike"] >= 1) &
            (persons["bike_share_citi_bike"] <= 4)
        ]
        results["regular_citibike_user_rate"] = len(regular_citibike) / len(persons)

    if verbose:
        zones_desc = ", ".join(zone_filter) if zone_filter else "All NYC"
        print(f"\n=== Bike Usage Statistics (CMS {year}) ===")
        print(f"Zones: {zones_desc}")
        print(f"Sample size: {len(persons):,} persons")
        for key, val in results.items():
            print(f"  {key}: {val:.1%}")

    return results


def get_mode_choice_calibration_targets(
    data_dir: Union[str, Path] = "input_data/cms",
    year: int = 2019,
    verbose: bool = True
) -> Dict[str, float]:
    """
    Get all relevant statistics for mode choice model calibration.

    This is a convenience function that extracts all the key statistics
    needed for calibrating a mode choice model for Brooklyn.

    Args:
        data_dir: Directory containing CMS data files
        year: Survey year
        verbose: Whether to print summary statistics

    Returns:
        Dict with all calibration targets
    """
    results = {}

    # Mode shares
    shares = get_brooklyn_mode_shares(data_dir, year, verbose=verbose)
    results["mode_shares"] = shares.to_dict()
    results["auto_driver_share"] = shares.auto_driver
    results["auto_passenger_share"] = shares.auto_passenger  # includes taxi/TNC
    results["auto_share"] = shares.combined_auto()  # driver + passenger
    results["transit_share"] = shares.transit
    results["walk_share"] = shares.walk
    results["bike_share"] = shares.bike

    # Ownership statistics
    ownership = get_brooklyn_ownership(data_dir, year, verbose=verbose)
    results["auto_ownership_rate"] = ownership.auto_ownership_rate
    results["bike_ownership_rate"] = ownership.bike_ownership_rate

    # Bike usage
    bike_usage = get_person_bike_usage(data_dir, year, BROOKLYN_ZONES, verbose=verbose)
    results.update(bike_usage)

    if verbose:
        print("\n=== Summary: Mode Choice Calibration Targets ===")
        print(f"Auto driver share:    {results['auto_driver_share']:.1%}")
        print(f"Auto passenger share: {results['auto_passenger_share']:.1%}  (includes taxi/TNC)")
        print(f"Total auto share:     {results['auto_share']:.1%}")
        print(f"Transit share:        {results['transit_share']:.1%}")
        print(f"Walk share:           {results['walk_share']:.1%}")
        print(f"Bike share:           {results['bike_share']:.1%}")
        print(f"Auto ownership rate:  {results['auto_ownership_rate']:.1%}")
        print(f"Bike ownership rate:  {results['bike_ownership_rate']:.1%}")

    return results


# Convenience function for quick analysis
def analyze_cms_data(
    data_dir: Union[str, Path] = "input_data/cms",
    year: int = 2019
) -> Dict:
    """
    Run complete CMS data analysis for Brooklyn.

    Args:
        data_dir: Directory containing CMS data files
        year: Survey year

    Returns:
        Dict with all analysis results
    """
    print("=" * 60)
    print(f"NYC Citywide Mobility Survey Analysis - {year}")
    print("=" * 60)

    results = get_mode_choice_calibration_targets(data_dir, year, verbose=True)

    # Add trip length distributions
    trips = load_cms_trips(data_dir, year)
    brooklyn_trips = filter_brooklyn_trips(trips)
    results["trip_length_dist"] = get_trip_length_distribution(brooklyn_trips)

    return results
