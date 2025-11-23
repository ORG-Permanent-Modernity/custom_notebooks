"""POI processing functions for OSM data."""

import osmnx as ox
import geopandas as gpd
import pandas as pd
from pathlib import Path


# Exclude these amenity types (not trip generators)
EXCLUDE_AMENITY = {
    # Street furniture
    'bench', 'waste_basket', 'waste_disposal', 'recycling', 'drinking_water',
    'telephone', 'post_box', 'letter_box', 'vending_machine',
    # Parking
    'parking', 'parking_space', 'parking_entrance', 'bicycle_parking',
    'motorcycle_parking', 'bicycle_rental',
    # Other infrastructure
    'shelter', 'toilets', 'shower', 'hunting_stand', 'fountain',
    'clock', 'photo_booth', 'atm',
    # Construction/temporary
    'construction',
}

# Exclude these leisure types
EXCLUDE_LEISURE = {
    'swimming_pool', 'picnic_table', 'firepit', 'outdoor_seating',
    'garden', 'slipway', 'marina',
}

# Keep these transit-related amenities
KEEP_TRANSIT = {'bus_station', 'ferry_terminal', 'taxi'}

# Keep these leisure types
KEEP_LEISURE = {
    'park', 'playground', 'pitch', 'track', 'sports_centre',
    'fitness_centre', 'stadium', 'ice_rink', 'swimming_area',
    'dog_park', 'nature_reserve', 'golf_course'
}


def load_pois(place_name, cache_path=None, use_cache=True):
    """
    Load POIs from OSM or cache.

    Parameters:
    -----------
    place_name : str
        Name of place to download POIs for
    cache_path : Path or str, optional
        Path to cache file (GeoJSON)
    use_cache : bool, default True
        Whether to use cached data if available

    Returns:
    --------
    GeoDataFrame
        Raw POIs data
    """
    if use_cache and cache_path and Path(cache_path).exists():
        print(f"Loading POIs from cache: {cache_path}")
        pois_raw = gpd.read_file(cache_path)
        print(f"Loaded {len(pois_raw):,} POIs from cache")
    else:
        print("Downloading POIs from OSM...")
        poi_tags = {
            'amenity': True,
            'shop': True,
            'office': True,
            'leisure': True,
            'tourism': True,
            'healthcare': True,
            'public_transport': True,
        }
        pois_raw = ox.features_from_place(place_name, poi_tags)

        # Save to cache if path provided
        if cache_path:
            Path(cache_path).parent.mkdir(exist_ok=True, parents=True)
            pois_raw.to_file(cache_path, driver="GeoJSON")
            print(f"Downloaded {len(pois_raw):,} POIs, saved to: {cache_path}")

    return pois_raw


def should_keep_poi(row):
    """Determine if POI should be kept based on type."""
    # Check amenity
    if 'amenity' in row.index and pd.notna(row['amenity']):
        amenity = row['amenity']
        if amenity in EXCLUDE_AMENITY:
            return False
        if amenity in KEEP_TRANSIT:
            return True
        return True

    # Check leisure - only keep specific types
    if 'leisure' in row.index and pd.notna(row['leisure']):
        leisure = row['leisure']
        if leisure in EXCLUDE_LEISURE:
            return False
        if leisure in KEEP_LEISURE:
            return True
        return False

    # Check public_transport - keep all
    if 'public_transport' in row.index and pd.notna(row['public_transport']):
        return True

    # Keep all shops, offices, tourism, healthcare
    for col in ['shop', 'office', 'tourism', 'healthcare']:
        if col in row.index and pd.notna(row[col]):
            return True

    return False


def process_pois(pois_raw, filter_non_trip_generators=True):
    """
    Process POIs: filter and get centroids.

    Parameters:
    -----------
    pois_raw : GeoDataFrame
        Raw POI data
    filter_non_trip_generators : bool, default True
        Whether to filter out non-trip-generating POIs

    Returns:
    --------
    GeoDataFrame
        Processed POIs with centroids
    """
    # Filter POIs if requested
    if filter_non_trip_generators:
        print(f"POIs before filtering: {len(pois_raw):,}")
        pois_filtered = pois_raw[pois_raw.apply(should_keep_poi, axis=1)].copy()
        print(f"POIs after filtering: {len(pois_filtered):,}")
    else:
        pois_filtered = pois_raw.copy()

    # Calculate centroid in projected CRS
    pois_utm = pois_filtered.to_crs(pois_filtered.estimate_utm_crs())
    pois_gdf = pois_filtered.copy()

    # Calculate centroid in projected CRS, then convert back
    centroids_utm = pois_utm.geometry.centroid
    pois_gdf['geometry'] = centroids_utm.to_crs("EPSG:4326")

    # Keep useful columns
    poi_type_cols = ['amenity', 'shop', 'office', 'leisure', 'tourism', 'healthcare',
                     'public_transport', 'name']
    available_cols = [c for c in poi_type_cols if c in pois_gdf.columns]
    pois_gdf = pois_gdf[available_cols + ['geometry']].copy()
    pois_gdf = pois_gdf.reset_index()
    pois_gdf['poi_id'] = range(len(pois_gdf))

    print(f"\nPOIs ready: {len(pois_gdf):,}")

    return pois_gdf


def save_pois(pois_gdf, output_path):
    """
    Save processed POIs to file.

    Parameters:
    -----------
    pois_gdf : GeoDataFrame
        Processed POIs data
    output_path : Path or str
        Output file path
    """
    pois_gdf.to_file(output_path, driver="GeoJSON")
    print(f"Saved POIs to: {output_path}")