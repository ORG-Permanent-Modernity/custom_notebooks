"""Optimized functions for creating trip generator dataset with proper units."""

import geopandas as gpd
import pandas as pd
import numpy as np
import yaml
from pathlib import Path
from .heuristics import BUILDING_TYPE_MAP
from .config import AreaConfig, CityConfig  # CityConfig kept for backward compatibility


def load_poi_mapping(settings_path=None):
    """
    Load POI to trip generation category mapping from settings file.

    Parameters:
    -----------
    settings_path : Path or str, optional
        Path to the settings YAML file. If None, uses brooklyn_settings.yaml.

    Returns:
    --------
    dict
        Dictionary with 'land_use_map', 'default_category', and 'units' keys
    """
    if settings_path is None:
        module_dir = Path(__file__).parent
        settings_path = module_dir.parent / 'settings' / 'brooklyn_settings.yaml'

    settings_path = Path(settings_path)
    if not settings_path.exists():
        raise FileNotFoundError(f"Settings file not found: {settings_path}")

    with open(settings_path, 'r') as f:
        settings = yaml.safe_load(f)

    return {
        'land_use_map': settings['trip_gen_land_use_map'],
        'default_category': settings['default_trip_gen_category'],
        'units': settings.get('trip_gen_units', {})
    }


# Load the mapping at module level for backward compatibility
_POI_MAPPING = load_poi_mapping()
TRIP_GEN_LAND_USE_MAP = _POI_MAPPING['land_use_map']
TRIP_GEN_DEFAULT_CATEGORY = _POI_MAPPING['default_category']


def create_trip_generators(processed_pois_df, buildings_gdf, config: AreaConfig, verbose=True):
    """
    Create unified trip generator dataset using vectorized operations.

    Parameters:
    -----------
    processed_pois_df : DataFrame
        Processed POIs with square footage allocations
    buildings_gdf : GeoDataFrame
        Buildings data with building_id and total_sqft
    config : AreaConfig
        Configuration object with area-specific parameters
    verbose : bool
        If True, print detailed progress messages

    Returns:
    --------
    GeoDataFrame
        Unified trip generator dataset with proper units
    """
    if verbose:
        print("Creating trip generators using optimized processing...")

    # Process POIs data using vectorized operations
    pois_data = processed_pois_df.copy()
    remaining_series = pois_data.get('is_remaining')
    if isinstance(remaining_series, pd.Series):
        # Fix for FutureWarning: use infer_objects to handle downcasting
        is_remaining = remaining_series.fillna(False).infer_objects(copy=False).astype(bool)
    else:
        is_remaining = pd.Series(False, index=pois_data.index)
    pois_data['source'] = np.where(is_remaining, 'inferred_remaining', 'osm_poi')
    pois_data['land_use_type'] = pois_data['poi_type']
    pois_data['land_use_category'] = pois_data['poi_category']
    pois_data['sqft'] = pois_data['poi_sqft']

    # Keep only needed columns
    pois_generators = pois_data[['source', 'building_id', 'land_use_type',
                                 'land_use_category', 'name', 'sqft', 'geometry']].copy()

    # Handle buildings without POIs using vectorized operations
    buildings_with_poi = set(processed_pois_df['building_id'].unique())
    buildings_without_poi = buildings_gdf[~buildings_gdf['building_id'].isin(buildings_with_poi)].copy()

    if verbose:
        print(f"Buildings with POIs: {len(buildings_with_poi):,}")
        print(f"Buildings without POI: {len(buildings_without_poi):,}")

    if len(buildings_without_poi) > 0:
        # Project to UTM for accurate centroid calculation (vectorized)
        buildings_utm = buildings_without_poi.to_crs(buildings_without_poi.estimate_utm_crs())
        buildings_without_poi['geometry'] = buildings_utm.geometry.centroid.to_crs("EPSG:4326")

        # Vectorized building tag processing; fall back to 'yes' even if column is missing
        if 'building' in buildings_without_poi.columns:
            building_series = buildings_without_poi['building'].fillna('yes')
        else:
            building_series = pd.Series('yes', index=buildings_without_poi.index)

        buildings_without_poi['building_tag'] = building_series.astype(str).str.lower()
        buildings_without_poi['land_use_type'] = buildings_without_poi['building_tag'].map(BUILDING_TYPE_MAP).fillna('residential')

        # Create generator records for buildings without POIs
        building_generators = pd.DataFrame({
            'source': 'building_inferred',
            'building_id': buildings_without_poi['building_id'],
            'land_use_type': buildings_without_poi['land_use_type'],
            'land_use_category': 'building',
            'name': buildings_without_poi['land_use_type'].str.replace('_', ' ').str.title(),
            'sqft': buildings_without_poi['total_sqft'],
            'geometry': buildings_without_poi['geometry']
        })

        # Combine POI generators and building generators
        all_generators = pd.concat([pois_generators, building_generators], ignore_index=True)
    else:
        all_generators = pois_generators

    # Create GeoDataFrame
    generators_gdf = gpd.GeoDataFrame(all_generators, crs="EPSG:4326")
    generators_gdf['generator_id'] = range(len(generators_gdf))

    # Add trip generation units using vectorized operations
    if verbose:
        print("Converting to trip generation units...")

    # Initialize columns
    generators_gdf['trip_gen_value'] = 0.0
    generators_gdf['trip_gen_unit'] = '1000_sf'
    generators_gdf['trip_gen_category'] = generators_gdf['land_use_type'].map(TRIP_GEN_LAND_USE_MAP).fillna(TRIP_GEN_DEFAULT_CATEGORY)

    # Vectorized unit conversions by category
    # Residential
    residential_mask = generators_gdf['trip_gen_category'].str.contains('Residential', na=False)
    generators_gdf.loc[residential_mask, 'trip_gen_value'] = generators_gdf.loc[residential_mask, 'sqft'] / config.sqft_per_du
    generators_gdf.loc[residential_mask, 'trip_gen_unit'] = 'DU'

    # Hotel
    hotel_mask = generators_gdf['trip_gen_category'] == 'Hotel'
    generators_gdf.loc[hotel_mask, 'trip_gen_value'] = generators_gdf.loc[hotel_mask, 'sqft'] / config.sqft_per_hotel_room
    generators_gdf.loc[hotel_mask, 'trip_gen_unit'] = 'rooms'

    # Parks
    park_mask = generators_gdf['trip_gen_category'].str.contains('Park Space', na=False)
    generators_gdf.loc[park_mask, 'trip_gen_value'] = generators_gdf.loc[park_mask, 'sqft'] * config.sqft_to_acres
    generators_gdf.loc[park_mask, 'trip_gen_unit'] = 'acres'

    # Schools
    school_mask = generators_gdf['trip_gen_category'].str.contains('School', na=False)
    generators_gdf.loc[school_mask, 'trip_gen_value'] = generators_gdf.loc[school_mask, 'sqft'] / config.sqft_per_student
    generators_gdf.loc[school_mask, 'trip_gen_unit'] = 'students'

    # Daycare
    daycare_mask = generators_gdf['trip_gen_category'].str.contains('Daycare', na=False)
    generators_gdf.loc[daycare_mask, 'trip_gen_value'] = generators_gdf.loc[daycare_mask, 'sqft'] / 1000
    generators_gdf.loc[daycare_mask, 'trip_gen_unit'] = '1000_sf'

    # Cineplex
    cinema_mask = generators_gdf['trip_gen_category'] == 'Cineplex'
    generators_gdf.loc[cinema_mask, 'trip_gen_value'] = generators_gdf.loc[cinema_mask, 'sqft'] / config.sqft_per_cinema_seat
    generators_gdf.loc[cinema_mask, 'trip_gen_unit'] = 'seats'

    # Default (per 1000 sf) - everything else
    other_mask = ~(residential_mask | hotel_mask | park_mask | school_mask | daycare_mask | cinema_mask)
    generators_gdf.loc[other_mask, 'trip_gen_value'] = generators_gdf.loc[other_mask, 'sqft'] / 1000

    # Always print high-level summary
    print(f"Trip Generators Created: {len(generators_gdf):,} generators, {generators_gdf['sqft'].sum():,.0f} total sqft")

    if verbose:
        print(f"\n=== Detailed Trip Generator Dataset ===")
        print(f"Total generators: {len(generators_gdf):,}")
        print(f"Total sqft: {generators_gdf['sqft'].sum():,.0f}")

        # Breakdown by source
        print(f"\nBy Source:")
        source_summary = generators_gdf.groupby('source')['sqft'].agg(['count', 'sum'])
        for source, row in source_summary.iterrows():
            print(f"  {source}: {row['count']:,} generators, {row['sum']:,.0f} sqft")

    return generators_gdf


def save_trip_generators(generators_gdf, geojson_path=None, csv_path=None, verbose=True):
    """
    Save trip generator dataset to files.

    Parameters:
    -----------
    generators_gdf : GeoDataFrame
        Trip generator dataset
    geojson_path : str, optional
        Path to save GeoJSON file
    csv_path : str, optional
        Path to save CSV file
    verbose : bool
        If True, print save confirmations
    """
    if geojson_path:
        generators_gdf.to_file(geojson_path, driver="GeoJSON")
        if verbose:
            print(f"Saved: {geojson_path}")

    if csv_path:
        generators_csv = generators_gdf.drop(columns=['geometry']).copy()
        generators_csv['lat'] = generators_gdf.geometry.y
        generators_csv['lon'] = generators_gdf.geometry.x
        generators_csv.to_csv(csv_path, index=False)
        if verbose:
            print(f"Saved: {csv_path}")


def print_trip_gen_summary(generators_gdf):
    """
    Print summary statistics for the trip generator dataset.

    Parameters:
    -----------
    generators_gdf : GeoDataFrame
        Trip generator dataset
    """
    # Summary by trip generation category
    print(f"\nTop 15 Trip Generation Categories:")
    cat_summary = generators_gdf.groupby('trip_gen_category').agg({
        'generator_id': 'count',
        'trip_gen_value': 'sum'
    }).sort_values('trip_gen_value', ascending=False)
    cat_summary.columns = ['count', 'total_units']

    # Add unit type to display
    unit_types = generators_gdf.groupby('trip_gen_category')['trip_gen_unit'].first()
    cat_summary['unit_type'] = unit_types

    print(cat_summary.head(15))

    # Show conversion examples
    print(f"\n=== Unit Conversion Examples ===")
    examples = generators_gdf.groupby('trip_gen_unit').first()
    for unit, row in examples.iterrows():
        print(f"{row['land_use_type']}: {row['sqft']:,.0f} sqft → {row['trip_gen_value']:.1f} {unit}")
