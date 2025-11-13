"""
Script to add two columns to NYC buildings shapefile:
1. district_type: Classification based on ZoneDist1 field
2. has_amenity: Whether amenity points are present within building polygons
"""

import geopandas as gpd
import pandas as pd
import os

def get_district_type(zone_code):
    """
    Classify zoning district based on first character(s)

    Categories:
    - R1-1 - R10H: Residential Districts
    - C1-6 - C8-4: Commercial Districts
    - M1-1 - M3-2: Manufacturing Districts
    - M1-1/R5 - M1-9/R12: Mixed Manufacturing & Residential Districts
    - BPC: Battery Park City
    - PARK: Areas designated as PARK, BALL FIELD, PLAYGROUND and PUBLIC SPACE
    """
    if pd.isna(zone_code) or zone_code == '':
        return 'Unknown'

    zone_str = str(zone_code).strip().upper()

    # Check for specific patterns
    if zone_str.startswith('R'):
        # Check if it's mixed (contains '/')
        if '/' in zone_str:
            return 'Mixed Manufacturing & Residential'
        return 'Residential'
    elif zone_str.startswith('C'):
        return 'Commercial'
    elif zone_str.startswith('M'):
        # Check if it's mixed (contains '/')
        if '/' in zone_str:
            return 'Mixed Manufacturing & Residential'
        return 'Manufacturing'
    elif 'BPC' in zone_str:
        return 'Battery Park City'
    elif 'PARK' in zone_str or 'BALL' in zone_str or 'PLAYGROUND' in zone_str or 'PUBLIC SPACE' in zone_str:
        return 'Park/Public Space'
    else:
        return 'Other'


def add_district_type_column(buildings_gdf):
    """Add district_type column based on ZoneDist1 field"""
    print("\n=== STEP 1: Adding district_type column ===")
    buildings_gdf['district_type'] = buildings_gdf['ZoneDist1'].apply(get_district_type)

    print("\nDistrict type distribution:")
    print(buildings_gdf['district_type'].value_counts())
    return buildings_gdf


def add_amenity_presence_column(buildings_gdf, amenities_gdf):
    """Add has_amenity column using spatial join"""
    print("\n=== STEP 2: Adding has_amenity column ===")

    # Check CRS compatibility
    print(f"Buildings CRS: {buildings_gdf.crs}")
    print(f"Amenities CRS: {amenities_gdf.crs}")

    # Ensure both datasets have the same CRS
    if buildings_gdf.crs != amenities_gdf.crs:
        print(f"Converting amenities to buildings CRS...")
        amenities_gdf = amenities_gdf.to_crs(buildings_gdf.crs)
        print("✓ Conversion complete")

    print(f"\nPerforming spatial join...")
    print(f"Buildings: {len(buildings_gdf):,}")
    print(f"Amenities: {len(amenities_gdf):,}")
    print("This may take a while for large datasets...")

    # Perform spatial join
    buildings_with_amenities = gpd.sjoin(
        buildings_gdf,
        amenities_gdf[['geometry']],  # Only need geometry column
        how='left',
        predicate='contains'  # Buildings that contain amenity points
    )

    # Check if any amenity was found for each building
    # Use groupby with level=0 to handle duplicate indices from multiple amenities per building
    has_amenity_series = buildings_with_amenities.groupby(level=0)['index_right'].apply(
        lambda x: x.notna().any()
    )

    # Assign back to the buildings dataframe
    buildings_gdf['has_amenity'] = has_amenity_series.astype(int)

    # Fill any NaN values (buildings that weren't in the result) with 0
    buildings_gdf['has_amenity'] = buildings_gdf['has_amenity'].fillna(0).astype(int)

    print("\n✓ Spatial join complete!")
    print(f"Buildings with amenities: {buildings_gdf['has_amenity'].sum():,}")
    print(f"Buildings without amenities: {(buildings_gdf['has_amenity'] == 0).sum():,}")
    print(f"Percentage with amenities: {buildings_gdf['has_amenity'].mean() * 100:.2f}%")

    return buildings_gdf


def main():
    # File paths
    buildings_path = '/Users/loucas/ORG Dropbox/03_LIBRARY/06 GIS DATA/NYC/land_parcels/property_plots/buildings.shp'
    amenity_path = '/Users/loucas/ORG Dropbox/03_LIBRARY/06 GIS DATA/NYC/amenities/nyc_amenities.shp'

    # Output path
    output_path = buildings_path.replace('buildings.shp', 'buildings_updated.shp')

    print("="*70)
    print("NYC Buildings - Add District Type and Amenity Presence Columns")
    print("="*70)

    # Load data
    print("\n=== LOADING DATA ===")
    print(f"Loading buildings from:\n  {buildings_path}")
    buildings = gpd.read_file(buildings_path)
    print(f"✓ Loaded {len(buildings):,} buildings")

    print(f"\nLoading amenities from:\n  {amenity_path}")
    amenities = gpd.read_file(amenity_path)
    print(f"✓ Loaded {len(amenities):,} amenities")

    # Add district_type column
    buildings = add_district_type_column(buildings)

    # Add has_amenity column
    buildings = add_amenity_presence_column(buildings, amenities)

    # Save updated file
    print("\n=== STEP 3: Saving updated file ===")
    print(f"Output path:\n  {output_path}")
    buildings.to_file(output_path)
    print("✓ File saved successfully!")

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total buildings: {len(buildings):,}")
    print(f"New columns added: 'district_type', 'has_amenity'")
    print(f"\nOutput files created:")
    output_dir = os.path.dirname(output_path)
    for file in sorted(os.listdir(output_dir)):
        if file.startswith('buildings_updated'):
            print(f"  - {file}")

    print("\nSample data:")
    print(buildings[['ZoneDist1', 'district_type', 'has_amenity']].head(10))

    print("\n" + "="*70)
    print("DONE!")
    print("="*70)


if __name__ == "__main__":
    main()
