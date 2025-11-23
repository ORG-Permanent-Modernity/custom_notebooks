"""Functions for generating unified POI dataset."""

import geopandas as gpd
import pandas as pd
from .heuristics import BUILDING_TYPE_MAP


def create_unified_pois(processed_pois_df, buildings_gdf):
    """
    Create unified POI dataset for trip generation.

    Parameters:
    -----------
    processed_pois_df : DataFrame
        Processed POIs with square footage allocations
    buildings_gdf : GeoDataFrame
        Buildings data with building_id and total_sqft

    Returns:
    --------
    GeoDataFrame
        Unified POI dataset with all POIs and inferred building uses
    """
    unified_pois = []

    # Add POIs from processed_df (includes both actual POIs and inferred remaining)
    for idx, row in processed_pois_df.iterrows():
        is_remaining = row.get('is_remaining', False)

        unified_pois.append({
            'source': 'inferred_remaining' if is_remaining else 'osm_poi',
            'building_id': row['building_id'],
            'poi_type': row['poi_type'],
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
            poi_type = BUILDING_TYPE_MAP.get(building_tag, 'residential')

            unified_pois.append({
                'source': 'building_inferred',
                'building_id': bldg['building_id'],
                'poi_type': poi_type,
                'land_use_category': 'building',
                'name': f"{poi_type.replace('_', ' ').title()}",
                'sqft': bldg['total_sqft'],
                'geometry': centroid
            })

    # Create GeoDataFrame
    unified_gdf = gpd.GeoDataFrame(unified_pois, crs="EPSG:4326")
    unified_gdf['unified_poi_id'] = range(len(unified_gdf))

    print(f"\n=== Unified POI Dataset for Trip Generation ===")
    print(f"Total POIs: {len(unified_gdf):,}")
    print(f"Total sqft: {unified_gdf['sqft'].sum():,.0f}")

    # Breakdown by source
    print(f"\nBy Source:")
    for source, group in unified_gdf.groupby('source'):
        print(f"  {source}: {len(group):,} POIs, {group['sqft'].sum():,.0f} sqft")

    return unified_gdf


def save_unified_pois(unified_gdf, geojson_path=None, csv_path=None):
    """
    Save unified POI dataset to files.

    Parameters:
    -----------
    unified_gdf : GeoDataFrame
        Unified POI dataset
    geojson_path : str, optional
        Path to save GeoJSON file
    csv_path : str, optional
        Path to save CSV file
    """
    if geojson_path:
        unified_gdf.to_file(geojson_path, driver="GeoJSON")
        print(f"Saved: {geojson_path}")

    if csv_path:
        unified_csv = unified_gdf.drop(columns=['geometry']).copy()
        unified_csv['lat'] = unified_gdf.geometry.y
        unified_csv['lon'] = unified_gdf.geometry.x
        unified_csv.to_csv(csv_path, index=False)
        print(f"Saved: {csv_path}")


def print_summary_statistics(unified_gdf):
    """
    Print summary statistics for the unified POI dataset.

    Parameters:
    -----------
    unified_gdf : GeoDataFrame
        Unified POI dataset
    """
    # Top POI types by square footage
    print(f"\nTop 15 POI Types (by sqft):")
    type_summary = unified_gdf.groupby('poi_type')['sqft'].agg(['count', 'sum']).sort_values('sum', ascending=False)
    type_summary.columns = ['count', 'total_sqft']
    print(type_summary.head(15))