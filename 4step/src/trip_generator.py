"""Functions for creating trip generator dataset with proper units for trip generation."""

import geopandas as gpd
import pandas as pd
from .heuristics import BUILDING_TYPE_MAP
from .config import get_city_config


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

def convert_to_trip_gen_units(row, city_name='brooklyn'):
    """
    Convert square footage to appropriate units for trip generation.

    Parameters:
    -----------
    row : dict-like
        Must contain 'land_use_type' and 'sqft' keys
    city_name : str
        City name for configuration (default: 'brooklyn')

    Returns:
    --------
    tuple
        (value, unit_type, trip_gen_category)
    """
    # Get city-specific configuration
    config = get_city_config(city_name)

    land_use_type = row['land_use_type']
    sqft = row['sqft']

    # Get the trip gen category
    trip_gen_category = TRIP_GEN_LAND_USE_MAP.get(land_use_type, 'Local Retail')

    # Convert based on category using config values
    if 'Residential' in trip_gen_category:
        # Convert to dwelling units
        value = sqft / config.sqft_per_du
        unit = 'DU'
    elif trip_gen_category == 'Hotel':
        # Convert to rooms
        value = sqft / config.sqft_per_hotel_room
        unit = 'rooms'
    elif 'Park Space' in trip_gen_category:
        # Convert to acres
        value = sqft * config.sqft_to_acres
        unit = 'acres'
    elif 'School' in trip_gen_category or 'Daycare' in trip_gen_category:
        # For schools/daycare, keep as 1000 sf (rates are per 1000 sf for daycare)
        if 'School' in trip_gen_category:
            value = sqft / config.sqft_per_student  # Convert to students
            unit = 'students'
        else:
            value = sqft / 1000
            unit = '1000_sf'
    elif trip_gen_category == 'Cineplex':
        # Convert to seats
        value = sqft / config.sqft_per_cinema_seat
        unit = 'seats'
    else:
        # Most categories use per 1000 sf
        value = sqft / 1000
        unit = '1000_sf'

    return value, unit, trip_gen_category


def create_trip_generators(processed_pois_df, buildings_gdf, city_name='brooklyn'):
    """
    Create unified trip generator dataset with proper naming.

    Parameters:
    -----------
    processed_pois_df : DataFrame
        Processed POIs with square footage allocations
    buildings_gdf : GeoDataFrame
        Buildings data with building_id and total_sqft

    Returns:
    --------
    GeoDataFrame
        Unified trip generator dataset with proper units
    """
    trip_generators = []

    # Add POIs from processed_df (includes both actual POIs and inferred remaining)
    for idx, row in processed_pois_df.iterrows():
        remaining_flag = row.get('is_remaining', False)
        is_remaining = bool(remaining_flag) if pd.notna(remaining_flag) else False

        trip_generators.append({
            'source': 'inferred_remaining' if is_remaining else 'osm_poi',
            'building_id': row['building_id'],
            'land_use_type': row['poi_type'],  # Renamed from poi_type
            'land_use_category': row['poi_category'],
            'name': row['name'],
            'sqft': row['poi_sqft'],
            'geometry': row['geometry']
        })

    # Handle buildings without any matched POI
    buildings_with_poi = set(processed_pois_df['building_id'].unique())
    buildings_without_poi = buildings_gdf[~buildings_gdf['building_id'].isin(buildings_with_poi)]

    print(f"Buildings with POIs: {len(buildings_with_poi):,}")
    print(f"Buildings without POI: {len(buildings_without_poi):,}")

    # For buildings without POIs, use building=* tag to infer use
    # Project to UTM for accurate centroid calculation if not empty
    if len(buildings_without_poi) > 0:
        buildings_utm = buildings_without_poi.to_crs(buildings_without_poi.estimate_utm_crs())
        centroids_utm = buildings_utm.geometry.centroid
        centroids_4326 = gpd.GeoSeries(centroids_utm, crs=buildings_utm.crs).to_crs("EPSG:4326")

        for idx, (bldg_idx, bldg) in enumerate(buildings_without_poi.iterrows()):
            centroid = centroids_4326.iloc[idx]
            building_tag = str(bldg.get('building', 'yes')).lower()
            land_use_type = BUILDING_TYPE_MAP.get(building_tag, 'residential')

            trip_generators.append({
                'source': 'building_inferred',
                'building_id': bldg['building_id'],
                'land_use_type': land_use_type,  # Renamed from poi_type
                'land_use_category': 'building',
                'name': f"{land_use_type.replace('_', ' ').title()}",
                'sqft': bldg['total_sqft'],
                'geometry': centroid
            })

    # Create GeoDataFrame
    generators_gdf = gpd.GeoDataFrame(trip_generators, crs="EPSG:4326")
    generators_gdf['generator_id'] = range(len(generators_gdf))  # Renamed from unified_poi_id

    # Add trip generation units
    units_data = generators_gdf.apply(
        lambda r: convert_to_trip_gen_units(r, city_name=city_name),
        axis=1
    )
    generators_gdf['trip_gen_value'] = units_data.apply(lambda x: x[0])
    generators_gdf['trip_gen_unit'] = units_data.apply(lambda x: x[1])
    generators_gdf['trip_gen_category'] = units_data.apply(lambda x: x[2])

    print(f"\n=== Unified Trip Generator Dataset ===")
    print(f"Total generators: {len(generators_gdf):,}")
    print(f"Total sqft: {generators_gdf['sqft'].sum():,.0f}")

    # Breakdown by source
    print(f"\nBy Source:")
    for source, group in generators_gdf.groupby('source'):
        print(f"  {source}: {len(group):,} generators, {group['sqft'].sum():,.0f} sqft")

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
