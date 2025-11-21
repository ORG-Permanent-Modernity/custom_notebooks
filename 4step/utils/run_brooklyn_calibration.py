#!/usr/bin/env python
"""
Main script to run Brooklyn POI trip rate calibration

This script:
1. Loads and analyzes all Brooklyn data sources
2. Calculates empirical trip generation rates
3. Generates calibrated POI trip rate table
4. Saves output to settings/brooklyn_poi_trip_rate.csv

Usage:
    python run_brooklyn_calibration.py

Author: Generated for Brooklyn 4-step model calibration
Date: 2025-11-20
"""

from pathlib import Path
from brooklyn_trip_rate_calibration import calculate_brooklyn_poi_rates
from generate_brooklyn_poi_rates import create_brooklyn_poi_trip_rates


def main():
    """Main calibration workflow"""

    # Set up paths
    project_root = Path(__file__).parent.parent
    input_data_dir = project_root / 'input_data'
    settings_dir = project_root / 'settings'
    output_file = settings_dir / 'brooklyn_poi_trip_rate.csv'

    print("="*80)
    print(" Brooklyn POI Trip Rate Calibration - Main Workflow")
    print("="*80)
    print(f"\nProject root: {project_root}")
    print(f"Input data: {input_data_dir}")
    print(f"Output file: {output_file}\n")

    # Step 1: Analyze Brooklyn data
    print("\n" + "="*80)
    print("STEP 1: Analyzing Brooklyn Data Sources")
    print("="*80)

    analysis_results = calculate_brooklyn_poi_rates(str(input_data_dir))

    # Step 2: Generate calibrated trip rates
    print("\n" + "="*80)
    print("STEP 2: Generating Brooklyn-Calibrated POI Trip Rates")
    print("="*80)

    trip_rate_df = create_brooklyn_poi_trip_rates(
        analysis_results,
        output_path=str(output_file)
    )

    # Step 3: Generate summary report
    print("\n" + "="*80)
    print("STEP 3: Summary Report")
    print("="*80)

    print(f"\nCalibration complete!")
    print(f"\nKey Statistics:")
    print(f"  - CMS Brooklyn trips analyzed: {analysis_results['residential_rates'].get('total_trips', 0):,}")
    print(f"  - MTA subway stations: {len(analysis_results['subway_rates'].get('station_data', [])) if 'station_data' in analysis_results['subway_rates'] else 0}")
    print(f"  - POI building types in output: {len(trip_rate_df['building'].unique())}")
    print(f"  - Total rate rows (all trip purposes): {len(trip_rate_df)}")

    print(f"\nTrip Purpose Distribution (from CMS):")
    res_rates = analysis_results['residential_rates']
    print(f"  - Home-Based Work (HBW):    {res_rates.get('HBW_pct', 0):.1%}")
    print(f"  - Home-Based Other (HBO):   {res_rates.get('HBO_pct', 0):.1%}")
    print(f"  - Non-Home-Based (NHB):     {res_rates.get('NHB_pct', 0):.1%}")

    print(f"\nOutput file saved: {output_file}")
    print("\nTo use in grid2demand:")
    print("  net.run_gravity_model(")
    print(f"      trip_rate_file='settings/brooklyn_poi_trip_rate.csv',")
    print("      trip_purpose=1  # or 2, or 3")
    print("  )")

    print("\n" + "="*80)
    print("Calibration Complete!")
    print("="*80)

    return trip_rate_df


if __name__ == '__main__':
    main()
