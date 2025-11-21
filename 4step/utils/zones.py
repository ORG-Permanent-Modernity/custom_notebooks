"""
Zone processing utilities for the 4-step travel demand model.
"""
import geopandas as gpd
import pandas as pd

def shapefile_to_zone_csv(shapefile_path: str, output_path: str, zone_id_col: str, county_fp: str):
    """
    Converts a census shapefile to a zone.csv file compatible with grid2demand.

    This function will:
    1. Read a shapefile.
    2. Filter it to the specified county.
    3. Calculate the centroid for each zone.
    4. Reproject the geometries to a projected CRS (EPSG:2263 for NYC).
    5. Create a DataFrame with zone_id, x_coord, y_coord, and geometry (WKT).
    6. Save the DataFrame to a CSV file.

    Args:
        shapefile_path (str): Path to the input shapefile.
        output_path (str): Path to save the output zone.csv file.
        zone_id_col (str): The column name in the shapefile to use for the zone_id.
        county_fp (str): The FIPS code for the county to filter by (e.g., '047' for Kings County/Brooklyn).
    """
    print(f"Reading shapefile from {shapefile_path}...")
    gdf = gpd.read_file(shapefile_path)
    print(f"  Initial shapefile has {len(gdf)} features.")

    # Filter to the specified county (Brooklyn)
    gdf = gdf[gdf['COUNTYFP20'] == county_fp]
    print(f"  Filtered to {len(gdf)} features for county {county_fp}.")

    if gdf.empty:
        raise ValueError(f"No features found for county FIPS code {county_fp}. Please check the shapefile and FIPS code.")

    # Reproject to a projected CRS suitable for NYC (NAD83 / New York Long Island)
    # This is important for accurate centroid calculation and distance measurements.
    projected_crs = "EPSG:2263"
    print(f"Reprojecting to {projected_crs}...")
    gdf = gdf.to_crs(projected_crs)

    # Calculate centroids
    gdf['centroid'] = gdf.geometry.centroid

    # Create the final DataFrame in the required format
    zone_df = pd.DataFrame({
        'zone_id': gdf[zone_id_col],
        'x_coord': gdf.centroid.x,
        'y_coord': gdf.centroid.y,
        'geometry': gdf.geometry.to_wkt()
    })

    # Ensure zone_id is integer
    zone_df['zone_id'] = zone_df['zone_id'].astype(int)

    # Save to CSV
    print(f"Saving zone.csv to {output_path}...")
    zone_df.to_csv(output_path, index=False)
    print("  Done.")

    return zone_df

if __name__ == '__main__':
    # Example usage:
    # This assumes the script is run from the 'utils' directory.
    # Adjust paths as necessary if run from elsewhere.
    
    # Path to the census blocks shapefile
    shp_path = '../input_data/census/ny_state_blocks/tl_2022_36_tabblock20.shp'
    
    # Output path for the new zone.csv
    out_path = '../data/zone_brooklyn_census_blocks.csv'
    
    # The column in the shapefile that will become our 'zone_id'
    # 'TABBLOCK20' is a good unique identifier for each block.
    zone_column = 'GEOID20'
    
    # FIPS code for Kings County (Brooklyn) is '047'
    brooklyn_fips = '047'
    
    try:
        shapefile_to_zone_csv(
            shapefile_path=shp_path,
            output_path=out_path,
            zone_id_col=zone_column,
            county_fp=brooklyn_fips
        )
        print(f"Successfully created {out_path}")
    except Exception as e:
        print(f"An error occurred: {e}")
