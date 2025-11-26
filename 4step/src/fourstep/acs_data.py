"""
ACS Data Module

Functions for fetching American Community Survey data from the Census API
for use in transportation modeling, including:
- Vehicle availability by census tract
- Commute mode shares
- Worker flows

No API key required for basic access (limited to 500 queries/day).
"""

import requests
from typing import Optional, Union
import numpy as np
import pandas as pd


# Census API base URLs
ACS_5YR_BASE = "https://api.census.gov/data/{year}/acs/acs5"


def get_auto_ownership_by_tract(
    state_fips: str,
    county_fips: Optional[str] = None,
    year: int = 2022,
    api_key: Optional[str] = None,
    verbose: bool = False
) -> pd.DataFrame:
    """
    Fetch vehicle availability by census tract from ACS Table B25044.

    Args:
        state_fips: 2-digit state FIPS code (e.g., "36" for NY, "06" for CA)
        county_fips: 3-digit county FIPS code (e.g., "047" for Kings/Brooklyn).
            If None, fetches all tracts in the state.
        year: ACS 5-year estimate year (2022 = 2018-2022 estimates)
        api_key: Census API key (optional, increases rate limits)
        verbose: Print progress

    Returns:
        DataFrame with columns:
        - tract_id: Full GEOID (state + county + tract)
        - total_households: Total households in tract
        - zero_vehicle_hh: Households with no vehicle
        - auto_ownership_rate: Fraction of households with 1+ vehicles
    """
    # Table B25044: Tenure by Vehicles Available
    # B25044_001E: Total households
    # B25044_003E: Owner occupied - No vehicle available
    # B25044_010E: Renter occupied - No vehicle available
    variables = "B25044_001E,B25044_003E,B25044_010E"

    base_url = ACS_5YR_BASE.format(year=year)

    if county_fips:
        geography = f"&for=tract:*&in=state:{state_fips}&in=county:{county_fips}"
    else:
        geography = f"&for=tract:*&in=state:{state_fips}"

    url = f"{base_url}?get=NAME,{variables}{geography}"

    if api_key:
        url += f"&key={api_key}"

    if verbose:
        print(f"Fetching ACS vehicle data for state {state_fips}" +
              (f", county {county_fips}" if county_fips else "") + "...")

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to fetch Census data: {e}")

    if len(data) < 2:
        raise ValueError(f"No data returned for state {state_fips}, county {county_fips}")

    # Parse response
    records = []
    for row in data[1:]:  # Skip header row
        if county_fips:
            name, total, owner_no_car, renter_no_car, state, county, tract = row
        else:
            name, total, owner_no_car, renter_no_car, state, county, tract = row

        # Handle null/missing values
        total = int(total) if total and total != "null" else 0
        owner_no_car = int(owner_no_car) if owner_no_car and owner_no_car != "null" else 0
        renter_no_car = int(renter_no_car) if renter_no_car and renter_no_car != "null" else 0

        zero_vehicle = owner_no_car + renter_no_car

        # Calculate ownership rate
        if total > 0:
            ownership_rate = 1 - (zero_vehicle / total)
        else:
            ownership_rate = np.nan

        tract_id = f"{state}{county}{tract}"

        records.append({
            "tract_id": tract_id,
            "total_households": total,
            "zero_vehicle_hh": zero_vehicle,
            "auto_ownership_rate": ownership_rate
        })

    df = pd.DataFrame(records)

    if verbose:
        valid = df["auto_ownership_rate"].notna()
        print(f"  Retrieved {len(df):,} tracts")
        print(f"  Average auto ownership: {df.loc[valid, 'auto_ownership_rate'].mean():.1%}")
        print(f"  Range: {df.loc[valid, 'auto_ownership_rate'].min():.1%} - {df.loc[valid, 'auto_ownership_rate'].max():.1%}")

    return df


def get_commute_mode_shares_by_tract(
    state_fips: str,
    county_fips: Optional[str] = None,
    year: int = 2022,
    api_key: Optional[str] = None,
    verbose: bool = False
) -> pd.DataFrame:
    """
    Fetch commute mode shares by census tract from ACS Table B08301.

    Args:
        state_fips: 2-digit state FIPS code
        county_fips: 3-digit county FIPS code (optional)
        year: ACS 5-year estimate year
        api_key: Census API key (optional)
        verbose: Print progress

    Returns:
        DataFrame with columns:
        - tract_id: Full GEOID
        - total_workers: Total workers 16+
        - drove_alone, carpooled, transit, walked, bike, other, wfh: Mode counts
        - share_*: Mode shares (0-1)
    """
    # Table B08301: Means of Transportation to Work
    variables = ",".join([
        "B08301_001E",  # Total workers 16+
        "B08301_003E",  # Car, truck, van - drove alone
        "B08301_004E",  # Car, truck, van - carpooled
        "B08301_010E",  # Public transportation
        "B08301_019E",  # Walked
        "B08301_018E",  # Bicycle
        "B08301_020E",  # Other means
        "B08301_021E",  # Worked from home
    ])

    base_url = ACS_5YR_BASE.format(year=year)

    if county_fips:
        geography = f"&for=tract:*&in=state:{state_fips}&in=county:{county_fips}"
    else:
        geography = f"&for=tract:*&in=state:{state_fips}"

    url = f"{base_url}?get=NAME,{variables}{geography}"

    if api_key:
        url += f"&key={api_key}"

    if verbose:
        print(f"Fetching ACS commute mode data...")

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to fetch Census data: {e}")

    records = []
    for row in data[1:]:
        # Parse values (handle nulls)
        values = []
        for v in row[1:8]:  # Skip name, get 7 numeric columns
            values.append(int(v) if v and v != "null" else 0)

        state = row[-3]
        county = row[-2]
        tract = row[-1]

        total, drove, carpool, transit, walk, bike, other, wfh = values[0], values[1], values[2], values[3], values[4], values[5], values[6], 0

        # Recalculate - the indexing might be off
        # Let's be more careful
        total = int(row[1]) if row[1] and row[1] != "null" else 0
        drove = int(row[2]) if row[2] and row[2] != "null" else 0
        carpool = int(row[3]) if row[3] and row[3] != "null" else 0
        transit = int(row[4]) if row[4] and row[4] != "null" else 0
        walk = int(row[5]) if row[5] and row[5] != "null" else 0
        bike = int(row[6]) if row[6] and row[6] != "null" else 0
        other = int(row[7]) if row[7] and row[7] != "null" else 0
        wfh = int(row[8]) if len(row) > 8 and row[8] and row[8] != "null" else 0

        tract_id = f"{state}{county}{tract}"

        record = {
            "tract_id": tract_id,
            "total_workers": total,
            "drove_alone": drove,
            "carpooled": carpool,
            "transit": transit,
            "walked": walk,
            "bike": bike,
            "other": other,
            "wfh": wfh,
        }

        # Calculate shares
        if total > 0:
            record["share_auto_driver"] = drove / total
            record["share_auto_passenger"] = carpool / total
            record["share_transit"] = transit / total
            record["share_walk"] = walk / total
            record["share_bike"] = bike / total
        else:
            record["share_auto_driver"] = np.nan
            record["share_auto_passenger"] = np.nan
            record["share_transit"] = np.nan
            record["share_walk"] = np.nan
            record["share_bike"] = np.nan

        records.append(record)

    df = pd.DataFrame(records)

    if verbose:
        valid = df["total_workers"] > 0
        print(f"  Retrieved {len(df):,} tracts")
        if valid.sum() > 0:
            print(f"  Average mode shares:")
            print(f"    Auto (driver): {df.loc[valid, 'share_auto_driver'].mean():.1%}")
            print(f"    Auto (passenger): {df.loc[valid, 'share_auto_passenger'].mean():.1%}")
            print(f"    Transit: {df.loc[valid, 'share_transit'].mean():.1%}")
            print(f"    Walk: {df.loc[valid, 'share_walk'].mean():.1%}")
            print(f"    Bike: {df.loc[valid, 'share_bike'].mean():.1%}")

    return df


def join_acs_to_zones(
    zones: pd.DataFrame,
    acs_data: pd.DataFrame,
    zone_id_col: str = "zone_id",
    acs_join_col: str = "tract_id",
    verbose: bool = False
) -> pd.DataFrame:
    """
    Join ACS tract-level data to zones.

    For census block zones, extracts tract ID from the block GEOID.
    Census block GEOIDs are 15 digits: state(2) + county(3) + tract(6) + block(4)
    Census tract GEOIDs are 11 digits: state(2) + county(3) + tract(6)

    Args:
        zones: DataFrame with zone_id column
        acs_data: DataFrame from get_auto_ownership_by_tract or similar
        zone_id_col: Column name for zone IDs in zones DataFrame
        acs_join_col: Column name for tract IDs in ACS data
        verbose: Print progress

    Returns:
        zones DataFrame with ACS columns joined
    """
    zones = zones.copy()

    # Convert zone_id to string for matching
    zones["_zone_str"] = zones[zone_id_col].astype(str)

    # Extract tract ID from zone ID (first 11 digits for census blocks)
    # Census block GEOID: SSCCCTTTTTTBBBB (15 digits)
    # Census tract GEOID: SSCCCTTTTTT (11 digits)
    zones["_tract_id"] = zones["_zone_str"].str[:11]

    # Ensure ACS tract_id is string
    acs_data = acs_data.copy()
    acs_data[acs_join_col] = acs_data[acs_join_col].astype(str)

    # Join
    n_before = len(zones)
    zones = zones.merge(
        acs_data,
        left_on="_tract_id",
        right_on=acs_join_col,
        how="left"
    )

    # Clean up temp columns
    zones = zones.drop(columns=["_zone_str", "_tract_id"], errors="ignore")
    if acs_join_col in zones.columns and acs_join_col != zone_id_col:
        zones = zones.drop(columns=[acs_join_col], errors="ignore")

    if verbose:
        matched = zones["auto_ownership_rate"].notna().sum() if "auto_ownership_rate" in zones.columns else 0
        print(f"  Joined ACS data to {matched:,} of {n_before:,} zones ({matched/n_before:.1%})")

    return zones


def get_zone_auto_ownership(
    zones: pd.DataFrame,
    zone_id_col: str = "zone_id",
    state_fips: Optional[str] = None,
    county_fips: Optional[str] = None,
    year: int = 2022,
    api_key: Optional[str] = None,
    verbose: bool = False
) -> np.ndarray:
    """
    Get auto ownership rates for zones by fetching ACS data and joining.

    Convenience function that combines fetching and joining.

    Args:
        zones: DataFrame with zone_id column (census block GEOIDs)
        zone_id_col: Column name for zone IDs
        state_fips: 2-digit state FIPS. If None, inferred from zone IDs.
        county_fips: 3-digit county FIPS. If None, inferred from zone IDs.
        year: ACS year
        api_key: Census API key
        verbose: Print progress

    Returns:
        Array of auto ownership rates aligned with zones index.
        NaN for zones without ACS data.
    """
    zones = zones.copy()

    # Infer state/county from zone IDs if not provided
    zone_str = zones[zone_id_col].astype(str).iloc[0]

    if state_fips is None:
        state_fips = zone_str[:2]
        if verbose:
            print(f"  Inferred state FIPS: {state_fips}")

    if county_fips is None:
        # Get unique counties from zone IDs
        counties = zones[zone_id_col].astype(str).str[2:5].unique()
        if len(counties) == 1:
            county_fips = counties[0]
            if verbose:
                print(f"  Inferred county FIPS: {county_fips}")
        else:
            if verbose:
                print(f"  Multiple counties detected: {list(counties)}")
                print(f"  Fetching data for all counties in state {state_fips}")

    # Fetch ACS data
    acs_data = get_auto_ownership_by_tract(
        state_fips=state_fips,
        county_fips=county_fips,
        year=year,
        api_key=api_key,
        verbose=verbose
    )

    # Join to zones
    zones_with_acs = join_acs_to_zones(
        zones,
        acs_data,
        zone_id_col=zone_id_col,
        verbose=verbose
    )

    # Extract ownership rates
    ownership = zones_with_acs["auto_ownership_rate"].values

    if verbose:
        valid = ~np.isnan(ownership)
        print(f"  Zone auto ownership: mean={np.nanmean(ownership):.1%}, "
              f"range={np.nanmin(ownership):.1%}-{np.nanmax(ownership):.1%}")

    return ownership


# FIPS code lookup for convenience
STATE_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06",
    "CO": "08", "CT": "09", "DE": "10", "DC": "11", "FL": "12",
    "GA": "13", "HI": "15", "ID": "16", "IL": "17", "IN": "18",
    "IA": "19", "KS": "20", "KY": "21", "LA": "22", "ME": "23",
    "MD": "24", "MA": "25", "MI": "26", "MN": "27", "MS": "28",
    "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33",
    "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38",
    "OH": "39", "OK": "40", "OR": "41", "PA": "42", "RI": "44",
    "SC": "45", "SD": "46", "TN": "47", "TX": "48", "UT": "49",
    "VT": "50", "VA": "51", "WA": "53", "WV": "54", "WI": "55",
    "WY": "56"
}

# NYC county FIPS for convenience
NYC_COUNTIES = {
    "Manhattan": "061",
    "Bronx": "005",
    "Brooklyn": "047",
    "Queens": "081",
    "Staten Island": "085"
}


# Bike availability estimates by area type
# Based on bike ownership surveys, bike share coverage, and ability/willingness to bike
BIKE_AVAILABILITY_RATES = {
    "urban_core_bikeshare": 0.15,  # Dense urban with bike share (Manhattan, downtown SF)
    "urban_bikeshare": 0.12,       # Urban with bike share coverage (Brooklyn, Chicago)
    "urban_no_bikeshare": 0.08,    # Urban without bike share
    "suburban": 0.05,              # Suburban - mostly recreational cyclists
    "rural": 0.03,                 # Rural - very low bike mode share
}


def estimate_bike_availability(
    area_type: str = "urban_bikeshare",
    has_bikeshare: bool = True,
    bikeshare_coverage: float = 0.5
) -> float:
    """
    Estimate bike availability rate for mode choice model.

    Bike availability reflects the fraction of trips where biking is a
    practical option, considering:
    - Bike ownership (~25-35% of US households own a bike, but only ~5-10%
      regularly use it for transportation)
    - Bike share coverage (stations within reasonable walk distance)
    - Physical ability and willingness to bike
    - Trip characteristics (carrying cargo, weather, etc.)

    Args:
        area_type: One of "urban_core", "urban", "suburban", "rural"
        has_bikeshare: Whether area has bike share program
        bikeshare_coverage: Fraction of zones with bike share access (0-1)

    Returns:
        Estimated fraction of trips with practical bike access (0-1)

    Example:
        >>> # Brooklyn with Citi Bike covering ~60% of study area
        >>> rate = estimate_bike_availability("urban", has_bikeshare=True, bikeshare_coverage=0.6)
        >>> print(f"Bike availability: {rate:.0%}")
        Bike availability: 12%
    """
    # Base rates from bike ownership and usage surveys
    base_rates = {
        "urban_core": 0.08,
        "urban": 0.06,
        "suburban": 0.04,
        "rural": 0.02,
    }

    base = base_rates.get(area_type, 0.05)

    # Bike share adds availability for people without personal bikes
    # but only in covered areas
    if has_bikeshare:
        bikeshare_boost = 0.08 * bikeshare_coverage  # Up to 8% more if fully covered
        if area_type in ["urban_core", "urban"]:
            bikeshare_boost *= 1.2  # Higher uptake in urban areas
        base += bikeshare_boost

    return min(base, 0.25)  # Cap at 25% - even in best conditions


def estimate_bike_availability_from_acs(
    commute_mode_df: pd.DataFrame,
    multiplier: float = 5.0
) -> float:
    """
    Estimate bike availability from ACS commute mode share data.

    The bike commute share represents people who actually bike to work,
    but more people have the *capability* to bike. We apply a multiplier
    to estimate the pool of potential cyclists.

    Rationale: If 2% bike to work, perhaps 10% could bike if they chose to
    (good weather, short trip, etc.). The multiplier accounts for:
    - Trip purpose (commute vs. other trips)
    - Weather variability
    - Non-regular bike owners who occasionally bike

    Args:
        commute_mode_df: DataFrame from get_commute_mode_shares_by_tract()
        multiplier: Factor to convert observed bike share to availability.
            Default 5.0 means if 2% bike to work, we estimate 10% could bike.
            Range typically 3-7 depending on assumptions.

    Returns:
        Estimated bike availability rate (0-1), weighted by workers.

    Example:
        >>> commute_df = get_commute_mode_shares_by_tract("36", "047")  # Brooklyn
        >>> bike_avail = estimate_bike_availability_from_acs(commute_df)
        >>> print(f"Bike availability: {bike_avail:.1%}")
        Bike availability: 8.5%
    """
    # Weight by total workers
    valid = commute_mode_df["total_workers"] > 0
    if not valid.any():
        return 0.10  # Default fallback

    weighted_bike_share = (
        commute_mode_df.loc[valid, "share_bike"] *
        commute_mode_df.loc[valid, "total_workers"]
    ).sum() / commute_mode_df.loc[valid, "total_workers"].sum()

    # Apply multiplier and cap
    availability = weighted_bike_share * multiplier
    return min(availability, 0.25)  # Cap at 25%


def get_bike_availability_for_zones(
    zones: pd.DataFrame,
    zone_id_col: str = "zone_id",
    state_fips: Optional[str] = None,
    county_fips: Optional[str] = None,
    year: int = 2022,
    multiplier: float = 5.0,
    api_key: Optional[str] = None,
    verbose: bool = False
) -> float:
    """
    Get estimated bike availability for zones using ACS commute data.

    Convenience function that fetches ACS data and estimates bike availability.

    Args:
        zones: DataFrame with zone_id column
        zone_id_col: Column name for zone IDs
        state_fips: 2-digit state FIPS (inferred from zones if None)
        county_fips: 3-digit county FIPS (inferred from zones if None)
        year: ACS year
        multiplier: Factor to convert bike commute share to availability
        api_key: Census API key
        verbose: Print progress

    Returns:
        Estimated bike availability rate for the study area.
    """
    zones = zones.copy()

    # Infer state/county from zone IDs
    zone_str = zones[zone_id_col].astype(str).iloc[0]

    if state_fips is None:
        state_fips = zone_str[:2]
        if verbose:
            print(f"  Inferred state FIPS: {state_fips}")

    if county_fips is None:
        counties = zones[zone_id_col].astype(str).str[2:5].unique()
        if len(counties) == 1:
            county_fips = counties[0]
            if verbose:
                print(f"  Inferred county FIPS: {county_fips}")

    # Fetch commute mode data
    commute_df = get_commute_mode_shares_by_tract(
        state_fips=state_fips,
        county_fips=county_fips,
        year=year,
        api_key=api_key,
        verbose=verbose
    )

    # Estimate availability
    availability = estimate_bike_availability_from_acs(commute_df, multiplier)

    if verbose:
        valid = commute_df["total_workers"] > 0
        observed_share = (
            commute_df.loc[valid, "share_bike"] *
            commute_df.loc[valid, "total_workers"]
        ).sum() / commute_df.loc[valid, "total_workers"].sum()
        print(f"  Observed bike commute share: {observed_share:.1%}")
        print(f"  Estimated bike availability (x{multiplier}): {availability:.1%}")

    return availability
