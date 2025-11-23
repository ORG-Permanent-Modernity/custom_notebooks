"""Optimized functions for creating trip generator dataset with proper units."""

import geopandas as gpd
import pandas as pd
import numpy as np
from .heuristics import BUILDING_TYPE_MAP
from .config import get_city_config
from .trip_generator import TRIP_GEN_LAND_USE_MAP, convert_to_trip_gen_units


def create_trip_generators_optimized(processed_pois_df, buildings_gdf, city_name='brooklyn'):
    """
    Create unified trip generator dataset using vectorized operations.

    Parameters:
    -----------
    processed_pois_df : DataFrame
        Processed POIs with square footage allocations
    buildings_gdf : GeoDataFrame
        Buildings data with building_id and total_sqft
    city_name : str
        City name for configuration

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

        # Vectorized building tag processing
        buildings_without_poi['building_tag'] = buildings_without_poi.get('building', 'yes').fillna('yes').str.lower()
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
    config = get_city_config(city_name)

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
