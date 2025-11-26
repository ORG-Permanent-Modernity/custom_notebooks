"""
Trip Generation Module

Step 1 of the 4-step model: Calculate trip productions and attractions by zone.
"""

from dataclasses import dataclass, field
from typing import Optional, Literal
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import yaml
from collections import defaultdict


@dataclass
class TripRates:
    """
    Trip generation rates by land use category.

    Rates are from NYC CEQR Technical Manual and ITE Trip Generation Manual.
    Units vary by category (trips per DU, per 1000 sqft, per student, etc.)
    """

    # Daily trip rates by category: (production_rate, attraction_rate)
    # For residential: most trips are produced, few attracted
    # For employment: most trips are attracted, few produced
    daily_rates: dict = field(default_factory=lambda: {
        # Residential - trips per dwelling unit
        "Residential (1-2 floors)": (9.5, 0.5),
        "Residential (2 floors or less)": (9.5, 0.5),
        "Residential (3 or more floors)": (4.2, 0.3),

        # Office - trips per 1000 sqft
        "Office (multi-tenant type building)": (1.5, 11.0),
        "Office (single-tenant type building)": (1.5, 11.0),

        # Retail - trips per 1000 sqft
        "Local Retail": (1.0, 42.0),
        "Regional Retail": (1.0, 45.0),
        "Destination Retail": (0.8, 40.0),
        "Supermarket": (1.0, 102.0),
        "Home Improvement Store": (0.8, 35.0),

        # Restaurant - trips per 1000 sqft
        "Sit Down/High Turnover Restaurant": (0.5, 127.0),
        "Fast Food Restaurant without Drive Through Window": (0.5, 496.0),
        "Fast Food Restaurant with Drive Through Window": (0.5, 534.0),

        # Hotel - trips per room
        "Hotel": (0.5, 8.2),

        # Medical - trips per 1000 sqft
        "Medical Office": (1.0, 36.0),
        "Hospital": (1.0, 17.0),

        # Education - trips per student (schools) or per 1000 sqft (daycare)
        "Public School (Students)": (0.0, 1.02),
        "Private School (Students)": (0.0, 1.15),
        "Daycare": (0.0, 80.0),  # Per 1000 sqft - high trip rate
        "Daycare (Children)": (0.0, 80.0),
        "Academic University": (0.0, 2.5),  # Per student

        # Entertainment - trips per seat (cinema) or per 1000 sqft
        "Cineplex": (0.0, 0.08),  # Per seat
        "Museum": (0.5, 15.0),  # Per 1000 sqft

        # Recreation - trips per 1000 sqft or acre
        "Health Club": (0.5, 32.0),  # Per 1000 sqft
        "Passive Park Space": (0.0, 1.5),  # Per acre
        "Active Park Space": (0.0, 3.5),  # Per acre
        "Park": (0.0, 2.0),

        # Default for unknown categories
        "default": (0.5, 5.0),
    })

    # Peak hour factors (fraction of daily trips in peak hour)
    peak_hour_factors: dict = field(default_factory=lambda: {
        "AM": {"production": 0.10, "attraction": 0.12},
        "PM": {"production": 0.12, "attraction": 0.10},
        "midday": {"production": 0.08, "attraction": 0.08},
    })

    # Trip purpose splits (fraction of trips by purpose)
    purpose_splits: dict = field(default_factory=lambda: {
        "Residential (1-2 floors)": {"HBW": 0.25, "HBO": 0.50, "NHB": 0.25},
        "Residential (2 floors or less)": {"HBW": 0.25, "HBO": 0.50, "NHB": 0.25},
        "Residential (3 or more floors)": {"HBW": 0.30, "HBO": 0.45, "NHB": 0.25},
        "Office (multi-tenant type building)": {"HBW": 0.80, "HBO": 0.10, "NHB": 0.10},
        "Local Retail": {"HBW": 0.05, "HBO": 0.60, "NHB": 0.35},
        "default": {"HBW": 0.33, "HBO": 0.34, "NHB": 0.33},
    })

    # Track unknown categories encountered
    _unknown_categories: set = field(default_factory=set)

    def get_rates(self, category: str) -> tuple[float, float]:
        """Get (production_rate, attraction_rate) for a category."""
        if category in self.daily_rates:
            return self.daily_rates[category]
        else:
            self._unknown_categories.add(category)
            return self.daily_rates["default"]

    def get_purpose_split(self, category: str) -> dict:
        """Get trip purpose split for a category."""
        return self.purpose_splits.get(category, self.purpose_splits["default"])

    def get_unknown_categories(self) -> set:
        """Return set of categories that were not found in rates table."""
        return self._unknown_categories

    def clear_unknown_categories(self):
        """Clear the unknown categories tracker."""
        self._unknown_categories = set()

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "TripRates":
        """
        Load trip rates from a YAML settings file.

        Expected YAML structure:
        ```yaml
        trip_gen_rates:
          "Category Name": [production_rate, attraction_rate]
        ```

        If trip_gen_rates is not present, attempts to build from
        trip_gen_land_use_map with default rates.

        Args:
            yaml_path: Path to YAML settings file

        Returns:
            TripRates instance
        """
        with open(yaml_path, 'r') as f:
            settings = yaml.safe_load(f)

        # Check for explicit rates
        if 'trip_gen_rates' in settings:
            daily_rates = {
                k: tuple(v) for k, v in settings['trip_gen_rates'].items()
            }
            daily_rates['default'] = daily_rates.get('default', (0.5, 5.0))
            return cls(daily_rates=daily_rates)

        # Otherwise, start with defaults and return
        # The YAML may have category mappings but not rates
        instance = cls()

        # Load peak hour factors if present
        if 'peak_hour_factors' in settings:
            instance.peak_hour_factors = settings['peak_hour_factors']

        return instance

    def to_dataframe(self) -> pd.DataFrame:
        """Convert rates to DataFrame for vectorized operations."""
        records = []
        for category, (prod, attr) in self.daily_rates.items():
            if category != 'default':
                records.append({
                    'trip_gen_category': category,
                    'production_rate': prod,
                    'attraction_rate': attr
                })
        return pd.DataFrame(records)


def assign_generators_to_zones(
    generators: gpd.GeoDataFrame,
    zones: gpd.GeoDataFrame,
    zone_id_col: str = "zone_id",
    verbose: bool = False
) -> gpd.GeoDataFrame:
    """
    Spatially assign trip generators to zones.

    Args:
        generators: GeoDataFrame of trip generators with point geometry
        zones: GeoDataFrame of zones with polygon geometry
        zone_id_col: Name of zone ID column in zones GeoDataFrame
        verbose: Print progress messages

    Returns:
        GeoDataFrame of generators with zone_id column added
    """
    # Ensure both have the same CRS
    if generators.crs != zones.crs:
        if verbose:
            print(f"  Converting generators CRS from {generators.crs} to {zones.crs}")
        generators = generators.to_crs(zones.crs)

    # Ensure generators have point geometry
    if not generators.empty and generators.geometry.iloc[0].geom_type != "Point":
        if verbose:
            print("  Converting generator geometries to centroids...")
        generators = generators.copy()
        generators["geometry"] = generators.geometry.centroid

    # Spatial join: assign each generator to its containing zone
    if verbose:
        print(f"  Assigning {len(generators):,} generators to {len(zones):,} zones...")

    generators_with_zones = gpd.sjoin(
        generators,
        zones[[zone_id_col, "geometry"]],
        how="left",
        predicate="within"
    )

    # Handle generators outside all zones (assign to nearest zone)
    unassigned_mask = generators_with_zones[zone_id_col].isna()
    n_unassigned = unassigned_mask.sum()

    if n_unassigned > 0:
        if verbose:
            print(f"  WARNING: {n_unassigned:,} generators outside zone boundaries")
            print(f"           Assigning to nearest zone centroid...")

        # Vectorized nearest neighbor assignment using spatial index
        zone_centroids = zones.copy()
        zone_centroids["geometry"] = zones.geometry.centroid

        unassigned_generators = generators_with_zones.loc[unassigned_mask].copy()

        # Use sjoin_nearest for efficiency (requires geopandas >= 0.10)
        try:
            nearest = gpd.sjoin_nearest(
                unassigned_generators[["geometry"]],
                zone_centroids[[zone_id_col, "geometry"]],
                how="left"
            )
            generators_with_zones.loc[unassigned_mask, zone_id_col] = nearest[zone_id_col].values
        except AttributeError:
            # Fallback for older geopandas
            for idx in unassigned_generators.index:
                gen_point = unassigned_generators.loc[idx, "geometry"]
                distances = zone_centroids.geometry.distance(gen_point)
                nearest_zone_idx = distances.idxmin()
                generators_with_zones.loc[idx, zone_id_col] = zones.loc[nearest_zone_idx, zone_id_col]

    # Clean up join artifacts
    if "index_right" in generators_with_zones.columns:
        generators_with_zones = generators_with_zones.drop(columns=["index_right"])

    # Summary statistics
    zones_with_generators = generators_with_zones[zone_id_col].nunique()
    zones_without_generators = len(zones) - zones_with_generators

    if verbose:
        print(f"  Assigned generators to {zones_with_generators:,} zones")
        if zones_without_generators > 0:
            print(f"  WARNING: {zones_without_generators:,} zones have no generators")

    return generators_with_zones


def calculate_zone_trips(
    generators: pd.DataFrame,
    zone_id_col: str = "zone_id",
    trip_gen_category_col: str = "trip_gen_category",
    trip_gen_value_col: str = "trip_gen_value",
    trip_rates: Optional[TripRates] = None,
    trip_purpose: Literal["all", "HBW", "HBO", "NHB"] = "all",
    time_period: Literal["daily", "AM", "PM", "midday"] = "daily",
    verbose: bool = False
) -> pd.DataFrame:
    """
    Calculate trip productions and attractions by zone (VECTORIZED).

    Args:
        generators: DataFrame with trip generators and zone assignments
        zone_id_col: Column name for zone ID
        trip_gen_category_col: Column with trip generation category
        trip_gen_value_col: Column with trip generation value (DU, sqft, students, etc.)
        trip_rates: TripRates object with rate tables (uses defaults if None)
        trip_purpose: Trip purpose to calculate ('all', 'HBW', 'HBO', 'NHB')
        time_period: Time period for rates ('daily', 'AM', 'PM', 'midday')
        verbose: Print progress messages

    Returns:
        DataFrame with columns: zone_id, production, attraction
    """
    if trip_rates is None:
        trip_rates = TripRates()

    trip_rates.clear_unknown_categories()

    if verbose:
        print(f"  Calculating {time_period} trips for purpose: {trip_purpose}")

    # Data quality checks
    generators = generators.copy()

    missing_category = generators[trip_gen_category_col].isna().sum()
    missing_value = generators[trip_gen_value_col].isna().sum()
    zero_value = (generators[trip_gen_value_col] == 0).sum()

    if verbose and (missing_category > 0 or missing_value > 0):
        print(f"  WARNING: Data quality issues found:")
        if missing_category > 0:
            print(f"           - {missing_category:,} generators with missing category")
        if missing_value > 0:
            print(f"           - {missing_value:,} generators with missing trip_gen_value")
        if zero_value > 0:
            print(f"           - {zero_value:,} generators with zero trip_gen_value")

    # Fill missing values
    generators[trip_gen_category_col] = generators[trip_gen_category_col].fillna("default")
    generators[trip_gen_value_col] = generators[trip_gen_value_col].fillna(0)

    # VECTORIZED: Create rates lookup DataFrame
    rates_df = trip_rates.to_dataframe()

    # Merge rates with generators
    generators_with_rates = generators.merge(
        rates_df,
        on=trip_gen_category_col,
        how='left'
    )

    # Fill missing rates with default
    default_prod, default_attr = trip_rates.daily_rates.get("default", (0.5, 5.0))
    generators_with_rates['production_rate'] = generators_with_rates['production_rate'].fillna(default_prod)
    generators_with_rates['attraction_rate'] = generators_with_rates['attraction_rate'].fillna(default_attr)

    # Track categories that didn't match
    unmatched_mask = generators.merge(
        rates_df[[trip_gen_category_col]],
        on=trip_gen_category_col,
        how='left',
        indicator=True
    )['_merge'] == 'left_only'

    unmatched_categories = generators.loc[unmatched_mask, trip_gen_category_col].unique()
    for cat in unmatched_categories:
        trip_rates._unknown_categories.add(cat)

    # Apply time period factor (vectorized)
    if time_period != "daily":
        peak_factors = trip_rates.peak_hour_factors.get(
            time_period, {"production": 0.1, "attraction": 0.1}
        )
        generators_with_rates['production_rate'] *= peak_factors["production"]
        generators_with_rates['attraction_rate'] *= peak_factors["attraction"]

    # Apply trip purpose factor (vectorized)
    if trip_purpose != "all":
        # Create purpose factor lookup
        purpose_factors = []
        for cat in generators_with_rates[trip_gen_category_col]:
            split = trip_rates.get_purpose_split(cat)
            purpose_factors.append(split.get(trip_purpose, 0.33))
        generators_with_rates['purpose_factor'] = purpose_factors
        generators_with_rates['production_rate'] *= generators_with_rates['purpose_factor']
        generators_with_rates['attraction_rate'] *= generators_with_rates['purpose_factor']

    # VECTORIZED: Calculate trips
    generators_with_rates['_production'] = (
        generators_with_rates['production_rate'] * generators_with_rates[trip_gen_value_col]
    )
    generators_with_rates['_attraction'] = (
        generators_with_rates['attraction_rate'] * generators_with_rates[trip_gen_value_col]
    )

    # Aggregate by zone
    zone_trips = generators_with_rates.groupby(zone_id_col).agg(
        production=("_production", "sum"),
        attraction=("_attraction", "sum")
    ).reset_index()

    # Print category breakdown
    if verbose:
        unknown_cats = trip_rates.get_unknown_categories()
        if unknown_cats:
            print(f"  WARNING: {len(unknown_cats)} unknown categories used default rates:")
            for cat in sorted(unknown_cats)[:10]:  # Show first 10
                count = (generators[trip_gen_category_col] == cat).sum()
                print(f"           - '{cat}' ({count:,} generators)")
            if len(unknown_cats) > 10:
                print(f"           ... and {len(unknown_cats) - 10} more")

        # Category breakdown
        print(f"\n  Trip Generation by Category:")
        cat_summary = generators_with_rates.groupby(trip_gen_category_col).agg(
            count=('_production', 'size'),
            production=('_production', 'sum'),
            attraction=('_attraction', 'sum')
        ).sort_values('attraction', ascending=False)

        total_attr = cat_summary['attraction'].sum()
        for cat, row in cat_summary.head(10).iterrows():
            pct = row['attraction'] / total_attr * 100 if total_attr > 0 else 0
            print(f"    {cat[:40]:<40} {row['attraction']:>12,.0f} ({pct:>5.1f}%)")
        if len(cat_summary) > 10:
            other_attr = cat_summary.iloc[10:]['attraction'].sum()
            other_pct = other_attr / total_attr * 100 if total_attr > 0 else 0
            print(f"    {'(other categories)':<40} {other_attr:>12,.0f} ({other_pct:>5.1f}%)")

    # Summary statistics
    total_prod = zone_trips["production"].sum()
    total_attr = zone_trips["attraction"].sum()
    pa_ratio = total_prod / total_attr if total_attr > 0 else float('inf')

    if verbose:
        print(f"\n  Total productions: {total_prod:,.0f}")
        print(f"  Total attractions: {total_attr:,.0f}")
        print(f"  P/A ratio: {pa_ratio:.3f}", end="")
        if pa_ratio > 2.0 or pa_ratio < 0.5:
            print(f" (WARNING: significant imbalance)")
        elif pa_ratio > 1.2 or pa_ratio < 0.8:
            print(f" (note: >20% imbalance)")
        else:
            print()

    return zone_trips


def balance_trip_ends(
    zone_trips: pd.DataFrame,
    method: Literal["attraction", "production", "average"] = "attraction",
    verbose: bool = False
) -> pd.DataFrame:
    """
    Balance total productions to equal total attractions.

    Args:
        zone_trips: DataFrame with zone_id, production, attraction columns
        method: Balancing method
            - 'attraction': Scale productions to match total attractions
            - 'production': Scale attractions to match total productions
            - 'average': Scale both to match average of totals
        verbose: Print progress messages

    Returns:
        DataFrame with balanced production and attraction columns
    """
    zone_trips = zone_trips.copy()

    total_prod = zone_trips["production"].sum()
    total_attr = zone_trips["attraction"].sum()

    if verbose:
        print(f"\n  Before balancing: P={total_prod:,.0f}, A={total_attr:,.0f}")

    if method == "attraction":
        # Scale productions to match attractions
        factor = total_attr / total_prod if total_prod > 0 else 1.0
        zone_trips["production"] *= factor
        if verbose and abs(factor - 1.0) > 0.01:
            print(f"  Scaling productions by {factor:.4f}")

    elif method == "production":
        # Scale attractions to match productions
        factor = total_prod / total_attr if total_attr > 0 else 1.0
        zone_trips["attraction"] *= factor
        if verbose and abs(factor - 1.0) > 0.01:
            print(f"  Scaling attractions by {factor:.4f}")

    elif method == "average":
        # Scale both to average
        target = (total_prod + total_attr) / 2
        prod_factor = target / total_prod if total_prod > 0 else 1.0
        attr_factor = target / total_attr if total_attr > 0 else 1.0
        zone_trips["production"] *= prod_factor
        zone_trips["attraction"] *= attr_factor

    if verbose:
        new_prod = zone_trips["production"].sum()
        new_attr = zone_trips["attraction"].sum()
        print(f"  After balancing ({method}): P={new_prod:,.0f}, A={new_attr:,.0f}")

    return zone_trips


def create_zone_arrays(
    zone_trips: pd.DataFrame,
    zone_id_col: str = "zone_id"
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Convert zone trips DataFrame to numpy arrays for gravity model.

    Args:
        zone_trips: DataFrame with zone_id, production, attraction
        zone_id_col: Column name for zone ID

    Returns:
        Tuple of (zone_ids, productions, attractions) as numpy arrays
    """
    zone_ids = zone_trips[zone_id_col].values
    productions = zone_trips["production"].values.astype(np.float64)
    attractions = zone_trips["attraction"].values.astype(np.float64)

    return zone_ids, productions, attractions
