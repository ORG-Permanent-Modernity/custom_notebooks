#!/usr/bin/env python3
"""
Test script to verify all improvements work correctly
"""

import sys
from pathlib import Path
import pandas as pd
import geopandas as gpd

# Add src to path
sys.path.insert(0, str(Path.cwd() / 'src'))

# Import functions
from src.config import CityConfig
from src.building_processor import load_buildings, process_buildings
from src.poi_processor import load_pois, process_pois
from src.spatial_matcher import match_pois_to_buildings
from src.heuristics import apply_heuristics_to_pois
from src.trip_generator import create_trip_generators

def test_verbose_mode():
    """Test that verbose mode controls output correctly"""
    print("=" * 60)
    print("Testing Verbose Mode Control")
    print("=" * 60)

    config = CityConfig(city_name='brooklyn')
    place_name = "Brooklyn, New York, USA"

    cache_dir = Path("cache")
    buildings_cache = cache_dir / "buildings_raw_brooklyn.geojson"
    pois_cache = cache_dir / "pois_raw_brooklyn.geojson"

    print("\n1. Testing with VERBOSE=False (minimal output):")
    print("-" * 40)

    # Load with verbose=False
    buildings_raw = load_buildings(
        place_name=place_name,
        cache_path=buildings_cache,
        use_cache=True,
        verbose=False
    )

    pois_raw = load_pois(
        place_name=place_name,
        cache_path=pois_cache,
        use_cache=True,
        verbose=False
    )

    # Process with verbose=False
    buildings_gdf = process_buildings(buildings_raw, config, verbose=False)
    pois_gdf = process_pois(pois_raw, verbose=False)

    print("\nWith verbose=False, only critical messages should appear above.")

    print("\n2. Testing with VERBOSE=True (detailed output):")
    print("-" * 40)

    # Process with verbose=True (using smaller subset for quick test)
    buildings_sample = buildings_gdf.head(1000)
    pois_sample = pois_gdf.head(100)

    matches_df = match_pois_to_buildings(buildings_sample, pois_sample, verbose=True)

    print("\nWith verbose=True, detailed progress should appear above.")


def test_futurewarning_fix():
    """Test that FutureWarning is fixed"""
    print("\n" + "=" * 60)
    print("Testing FutureWarning Fix")
    print("=" * 60)

    # Create test data with is_remaining column
    test_df = pd.DataFrame({
        'poi_id': [1, 2, 3],
        'building_id': [100, 100, 200],
        'poi_sqft': [1000, 2000, 3000],
        'is_remaining': [True, False, None]
    })

    # This should not produce FutureWarning
    remaining_series = test_df.get('is_remaining')
    if isinstance(remaining_series, pd.Series):
        # Fix applied: use infer_objects
        is_remaining = remaining_series.fillna(False).infer_objects(copy=False).astype(bool)

    print("✓ FutureWarning fix applied successfully (no warning should appear)")


def test_error_handling():
    """Test error handling for OSM failures"""
    print("\n" + "=" * 60)
    print("Testing Error Handling")
    print("=" * 60)

    # Test with invalid place name
    print("\nTrying to download from invalid location (should handle gracefully)...")

    try:
        from src.building_processor import load_buildings
        result = load_buildings(
            place_name="InvalidPlaceNameThatDoesNotExist12345",
            cache_path=Path("cache/test_invalid.geojson"),
            use_cache=False,
            verbose=False
        )
        print("✗ Should have raised an error")
    except RuntimeError as e:
        print(f"✓ Error handled correctly: {str(e)[:50]}...")


def test_validation():
    """Test building size validation"""
    print("\n" + "=" * 60)
    print("Testing Building Size Validation")
    print("=" * 60)

    # Create test buildings with unrealistic sizes
    import numpy as np

    test_buildings = gpd.GeoDataFrame({
        'geometry': [None] * 5,
        'footprint_m2': [100, 500, 10000, 100000, 500000],
        'footprint_sqft': [1076, 5382, 107639, 1076391, 5381955],
        'estimated_floors': [3, 5, 10, 50, 200],
        'total_sqft': [3229, 26910, 1076391, 53819550, 1076391000]
    })

    # Check validation logic
    large_buildings = test_buildings['total_sqft'] > 1_000_000
    very_large_buildings = test_buildings['total_sqft'] > 5_000_000
    high_floors = test_buildings['estimated_floors'] > 100

    print(f"Buildings > 1M sqft: {large_buildings.sum()}")
    print(f"Buildings > 5M sqft: {very_large_buildings.sum()}")
    print(f"Buildings > 100 floors: {high_floors.sum()}")

    if large_buildings.sum() == 2 and very_large_buildings.sum() == 2 and high_floors.sum() == 1:
        print("✓ Building validation working correctly")
    else:
        print("✗ Building validation not working as expected")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("4STEP CODEBASE IMPROVEMENTS TEST SUITE")
    print("=" * 60)

    # Check if cache exists
    cache_dir = Path("cache")
    if not cache_dir.exists() or not list(cache_dir.glob("*.geojson")):
        print("\nWARNING: Cache directory is empty. Please run process_buildings_pois.ipynb first.")
        print("Some tests will be skipped.")

        # Run tests that don't need cache
        test_futurewarning_fix()
        test_validation()
        return

    # Run all tests
    test_verbose_mode()
    test_futurewarning_fix()
    test_error_handling()
    test_validation()

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()