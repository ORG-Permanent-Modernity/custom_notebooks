"""Spatial matching functions for POIs to buildings."""

import geopandas as gpd
import pandas as pd


def match_pois_to_buildings(buildings_gdf, pois_gdf, verbose=True):
    """
    Match POIs to buildings using vectorized spatial join.

    Parameters:
    -----------
    buildings_gdf : GeoDataFrame
        Buildings with polygon geometries and building_id column
    pois_gdf : GeoDataFrame
        POIs with point geometries and poi_id column
    verbose : bool
        If True, print detailed progress messages

    Returns:
    --------
    DataFrame
        Matches with poi_id and building_id columns
    """
    if verbose:
        print("Matching POIs to buildings using spatial join...")

    # Ensure we have the required columns
    if 'building_id' not in buildings_gdf.columns:
        raise ValueError("buildings_gdf must have 'building_id' column")
    if 'poi_id' not in pois_gdf.columns:
        raise ValueError("pois_gdf must have 'poi_id' column")

    if buildings_gdf.crs is None or pois_gdf.crs is None:
        raise ValueError("Both GeoDataFrames must have a defined CRS before matching")

    # Align CRS to avoid silent mismatch issues
    if buildings_gdf.crs != pois_gdf.crs:
        pois_gdf = pois_gdf.to_crs(buildings_gdf.crs)

    # Keep only necessary columns for the join to minimize memory
    buildings_subset = buildings_gdf[['building_id', 'geometry']].copy()
    pois_subset = pois_gdf[['poi_id', 'geometry']].copy()

    # Create spatial index for performance (triggers automatic index creation)
    if verbose and len(buildings_subset) > 10000:
        print("  Building spatial index for faster matching...")
    _ = buildings_subset.sindex  # This creates and caches the spatial index

    # Perform spatial join (points in polygons)
    # Using 'within' predicate for point-in-polygon test
    joined = gpd.sjoin(
        pois_subset,
        buildings_subset,
        how='left',  # Keep all POIs, even if not matched
        predicate='within'  # POI point within building polygon
    )

    # Create matches dataframe
    matches_df = pd.DataFrame({
        'poi_id': joined['poi_id'],
        'building_id': joined.get('building_id', None)
    })

    # Remove duplicates if any (shouldn't happen with point-in-polygon)
    matches_df = matches_df.drop_duplicates(subset=['poi_id'])

    # Calculate statistics
    matched_count = matches_df['building_id'].notna().sum()
    total_pois = len(pois_gdf)
    match_rate = (matched_count / total_pois * 100) if total_pois > 0 else 0

    print(f"Matched {matched_count:,} POIs to buildings ({match_rate:.1f}%)")

    return matches_df


def join_matches_to_pois(pois_gdf, matches_df, verbose=True):
    """
    Join match information back to POIs.

    Parameters:
    -----------
    pois_gdf : GeoDataFrame
        Original POIs data
    matches_df : DataFrame
        POI to building matches
    verbose : bool
        If True, print detailed progress messages

    Returns:
    --------
    GeoDataFrame
        POIs with building_id, filtered to only matched POIs
    """
    pois_matched = pois_gdf.merge(matches_df, on='poi_id', how='left')
    pois_matched = pois_matched[pois_matched['building_id'].notna()].copy()
    if verbose:
        print(f"POIs with building matches: {len(pois_matched):,}")
    return pois_matched


def match_pois_to_buildings_batch(buildings_gdf, pois_gdf, batch_size=50000, verbose=True):
    """
    Match POIs to buildings in batches for very large datasets.

    Parameters:
    -----------
    buildings_gdf : GeoDataFrame
        Buildings with polygon geometries and building_id column
    pois_gdf : GeoDataFrame
        POIs with point geometries and poi_id column
    batch_size : int
        Number of POIs to process at once
    verbose : bool
        If True, print detailed progress messages

    Returns:
    --------
    DataFrame
        Matches with poi_id and building_id columns
    """
    if len(pois_gdf) <= batch_size:
        # Small enough to process at once
        return match_pois_to_buildings(buildings_gdf, pois_gdf, verbose=verbose)

    if verbose:
        print(f"Processing {len(pois_gdf):,} POIs in batches of {batch_size:,}...")

    all_matches = []
    n_batches = (len(pois_gdf) + batch_size - 1) // batch_size

    for i in range(n_batches):
        start_idx = i * batch_size
        end_idx = min((i + 1) * batch_size, len(pois_gdf))
        batch = pois_gdf.iloc[start_idx:end_idx]

        if verbose:
            print(f"  Batch {i+1}/{n_batches}: POIs {start_idx:,} to {end_idx:,}")
        batch_matches = match_pois_to_buildings(buildings_gdf, batch, verbose=False)  # Avoid nested verbose output
        all_matches.append(batch_matches)

    # Combine all batches
    matches_df = pd.concat(all_matches, ignore_index=True)

    # Final statistics - always print this summary
    matched_count = matches_df['building_id'].notna().sum()
    total_pois = len(pois_gdf)
    match_rate = (matched_count / total_pois * 100) if total_pois > 0 else 0

    print(f"Total: Matched {matched_count:,} POIs to buildings ({match_rate:.1f}%)")

    return matches_df
