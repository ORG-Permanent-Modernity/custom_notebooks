"""Optimized functions for creating trip generator dataset with proper units."""

import geopandas as gpd
import pandas as pd
import numpy as np
from .heuristics import BUILDING_TYPE_MAP
from .config import CityConfig

# Land use type mapping from our categories to trip generation table
TRIP_GEN_LAND_USE_MAP = {
    # Residential types
    'residential': 'Residential (3 or more floors)',  # Default for Brooklyn
    'apartments': 'Residential (3 or more floors)',
    'house': 'Residential (2 floors or less)',
    'detached': 'Residential (2 floors or less)',
    'dormitory': 'Residential (3 or more floors)',

    # Office
    'office': 'Office (multi-tenant type building)',
    'company': 'Office (multi-tenant type building)',
    'government': 'Office (multi-tenant type building)',
    'insurance': 'Office (multi-tenant type building)',
    'lawyer': 'Office (multi-tenant type building)',
    'estate_agent': 'Office (multi-tenant type building)',

    # Retail
    'supermarket': 'Supermarket',
    'convenience': 'Local Retail',
    'clothes': 'Local Retail',
    'shoes': 'Local Retail',
    'hardware': 'Home Improvement Store',
    'doityourself': 'Home Improvement Store',
    'department_store': 'Destination Retail',
    'mall': 'Destination Retail',
    'electronics': 'Destination Retail',

    # Food service
    'restaurant': 'Sit Down/High Turnover Restaurant',
    'cafe': 'Sit Down/High Turnover Restaurant',
    'fast_food': 'Fast Food Restaurant without Drive Through Window',
    'bar': 'Sit Down/High Turnover Restaurant',

    # Education
    'school': 'Public School (Students)',
    'kindergarten': 'Daycare (Children)',
    'college': 'Academic University',
    'university': 'Academic University',

    # Medical
    'hospital': 'Medical Office',
    'clinic': 'Medical Office',
    'doctors': 'Medical Office',
    'dentist': 'Medical Office',

    # Recreation
    'fitness_centre': 'Health Club',
    'sports_centre': 'Health Club',
    'park': 'Passive Park Space',
    'playground': 'Active Park Space',
    'pitch': 'Active Park Space',

    # Hospitality
    'hotel': 'Hotel',
    'hostel': 'Hotel',

    # Entertainment
    'cinema': 'Cineplex',
    'theatre': 'Cineplex',
    'museum': 'Museum',
}


def create_trip_generators(processed_pois_df, buildings_gdf, config: CityConfig):
    """
    Create unified trip generator dataset using vectorized operations.

    Parameters:
    -----------
    processed_pois_df : DataFrame
        Processed POIs with square footage allocations
    buildings_gdf : GeoDataFrame
        Buildings data with building_id and total_sqft
    config : CityConfig
        Configuration object with city-specific parameters

    Returns:
    --------
    GeoDataFrame
        Unified trip generator dataset with proper units
    """
    print("Creating trip generators using optimized processing...")

    # Process POIs data using vectorized operations
    pois_data = processed_pois_df.copy()
    remaining_series = pois_data.get('is_remaining')
    if isinstance(remaining_series, pd.Series):
        is_remaining = remaining_series.fillna(False).astype(bool)
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
    print("Converting to trip generation units...")

    # Initialize columns
    generators_gdf['trip_gen_value'] = 0.0
    generators_gdf['trip_gen_unit'] = '1000_sf'
    generators_gdf['trip_gen_category'] = generators_gdf['land_use_type'].map(TRIP_GEN_LAND_USE_MAP).fillna('Local Retail')

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

    print(f"\n=== Unified Trip Generator Dataset ===")
    print(f"Total generators: {len(generators_gdf):,}")
    print(f"Total sqft: {generators_gdf['sqft'].sum():,.0f}")

    # Breakdown by source
    print(f"\nBy Source:")
    source_summary = generators_gdf.groupby('source')['sqft'].agg(['count', 'sum'])
    for source, row in source_summary.iterrows():
        print(f"  {source}: {row['count']:,} generators, {row['sum']:,.0f} sqft")

    return generators_gdf


def save_trip_generators(generators_gdf, geojson_path=None, csv_path=None):
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
    """
    if geojson_path:
        generators_gdf.to_file(geojson_path, driver="GeoJSON")
        print(f"Saved: {geojson_path}")

    if csv_path:
        generators_csv = generators_gdf.drop(columns=['geometry']).copy()
        generators_csv['lat'] = generators_gdf.geometry.y
        generators_csv['lon'] = generators_gdf.geometry.x
        generators_csv.to_csv(csv_path, index=False)
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
