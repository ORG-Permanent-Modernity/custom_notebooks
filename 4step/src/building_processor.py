"""Building processing functions for OSM data."""

import osmnx as ox
import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path
from .config import CityConfig


def load_buildings(place_name, cache_path=None, use_cache=True, verbose=True):
    """
    Load buildings from OSM or cache.

    Parameters:
    -----------
    place_name : str
        Name of place to download buildings for (e.g., "Brooklyn, New York, USA")
    cache_path : Path or str, optional
        Path to cache file (GeoJSON)
    use_cache : bool, default True
        Whether to use cached data if available
    verbose : bool
        If True, print detailed progress messages

    Returns:
    --------
    GeoDataFrame
        Buildings with polygon geometries
    """
    if use_cache and cache_path and Path(cache_path).exists():
        if verbose:
            print(f"Loading buildings from cache: {cache_path}")
        gdf = gpd.read_file(cache_path)
        print(f"Loaded {len(gdf):,} buildings")
    else:
        if verbose:
            print("Downloading buildings from OSM...")
        tags = {"building": True}

        # Add error handling for OSM download failures
        try:
            gdf = ox.features_from_place(place_name, tags)
        except Exception as e:
            print(f"ERROR: Failed to download buildings from OSM: {e}")
            if cache_path and Path(cache_path).exists():
                print("Falling back to cache...")
                gdf = gpd.read_file(cache_path)
                print(f"Loaded {len(gdf):,} buildings from fallback cache")
            else:
                raise RuntimeError(f"Could not download buildings from OSM and no cache available: {e}")

        # Save to cache if path provided
        if cache_path:
            Path(cache_path).parent.mkdir(exist_ok=True, parents=True)
            gdf.to_file(cache_path, driver="GeoJSON")
            print(f"Downloaded {len(gdf):,} buildings")
            if verbose:
                print(f"Saved to cache: {cache_path}")

    # Keep polygonal footprints (Polygon or MultiPolygon) and drop empties
    gdf = gdf[gdf.geometry.notna()]
    gdf = gdf[gdf.geometry.geom_type.isin(['Polygon', 'MultiPolygon'])].copy()

    return gdf


def process_buildings(gdf: gpd.GeoDataFrame, config: CityConfig, verbose=True):
    """
    Process buildings to calculate square footage and estimate floors.

    Parameters:
    -----------
    gdf : GeoDataFrame
        Buildings data
    config : CityConfig
        Configuration object with city-specific parameters
    verbose : bool
        If True, print detailed progress messages

    Returns:
    --------
    GeoDataFrame
        Processed buildings with footprint_sqft, estimated_floors, total_sqft
    """
    # Project to meters (UTM)
    gdf_proj = gdf.to_crs(gdf.estimate_utm_crs())

    # Calculate Footprint Area
    gdf_proj["footprint_m2"] = gdf_proj.geometry.area
    gdf_proj["footprint_sqft"] = gdf_proj["footprint_m2"] * config.m2_to_sqft

    # Clean 'building:levels'
    if 'building:levels' in gdf_proj.columns:
        gdf_proj['levels_clean'] = pd.to_numeric(gdf_proj['building:levels'], errors='coerce')
    else:
        gdf_proj['levels_clean'] = np.nan

    # Clean 'height' to estimate levels
    if 'height' in gdf_proj.columns:
        gdf_proj['height_clean'] = pd.to_numeric(
            gdf_proj['height'].astype(str).str.replace('m', '', regex=False),
            errors='coerce'
        )
    else:
        gdf_proj['height_clean'] = np.nan

    # Vectorized estimation of number of floors
    conditions = [
        (gdf_proj['levels_clean'].notna()) & (gdf_proj['levels_clean'] > 0),
        (gdf_proj['height_clean'].notna()) & (gdf_proj['height_clean'] > 0)
    ]
    choices = [
        gdf_proj['levels_clean'],
        (gdf_proj['height_clean'] / config.avg_floor_height_m).round().clip(lower=1)
    ]
    
    gdf_proj['estimated_floors'] = np.select(conditions, choices, default=config.default_floors).astype(int)

    # Calculate Total Square Footage
    gdf_proj["total_sqft"] = gdf_proj["footprint_sqft"] * gdf_proj["estimated_floors"]

    # Add validation for unrealistic building sizes
    large_buildings = gdf_proj['total_sqft'] > 1_000_000
    if large_buildings.any():
        print(f"WARNING: {large_buildings.sum():,} buildings exceed 1M sqft")
        if verbose:
            # Show statistics of large buildings
            large_bldg_stats = gdf_proj.loc[large_buildings, 'total_sqft'].describe()
            print(f"  Large buildings stats: max={large_bldg_stats['max']:,.0f} sqft, mean={large_bldg_stats['mean']:,.0f} sqft")

    very_large_buildings = gdf_proj['total_sqft'] > 5_000_000
    if very_large_buildings.any():
        print(f"WARNING: {very_large_buildings.sum():,} buildings exceed 5M sqft (likely data errors)")

    # Check for unrealistic floor counts
    high_floors = gdf_proj['estimated_floors'] > 100
    if high_floors.any():
        print(f"WARNING: {high_floors.sum():,} buildings have >100 floors (likely data errors)")
        if verbose:
            max_floors = gdf_proj.loc[high_floors, 'estimated_floors'].max()
            print(f"  Maximum floor count: {max_floors}")

    # Prepare final building data
    useful_columns = ["building", "footprint_sqft", "estimated_floors", "total_sqft", "geometry"]
    buildings_gdf = gdf_proj[[c for c in useful_columns if c in gdf_proj.columns]].copy()
    buildings_gdf = buildings_gdf.to_crs("EPSG:4326")

    # Create unique building ID
    buildings_gdf = buildings_gdf.reset_index()
    buildings_gdf['building_id'] = range(len(buildings_gdf))

    print(f"Buildings processed: {len(buildings_gdf):,}")

    return buildings_gdf


def save_buildings(buildings_gdf, output_path, verbose=True):
    """
    Save processed buildings to file.

    Parameters:
    -----------
    buildings_gdf : GeoDataFrame
        Processed buildings data
    output_path : Path or str
        Output file path (supports GeoJSON)
    verbose : bool
        If True, print save confirmation
    """
    buildings_gdf.to_file(output_path, driver="GeoJSON")
    if verbose:
        print(f"Saved buildings to: {output_path}")
