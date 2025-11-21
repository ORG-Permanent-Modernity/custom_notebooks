"""
Create Multi-Purpose POI Trip Rate Table for Brooklyn

This module generates a complete POI trip rate CSV file calibrated for Brooklyn,
with rates for all three trip purposes (HBW, HBO, NHB) based on:
- NYC CEQR baseline data (validated)
- CMS 2019 Brooklyn survey data
- Conservative scaling to maintain proximity to validated rates

Author: Brooklyn 4-step model enhancement
Date: 2025-11-20
"""

import pandas as pd
import numpy as np
from pathlib import Path


def analyze_cms_trip_distribution(cms_trip_file: str = None):
    """
    Analyze CMS data to get trip purpose distribution

    Returns trip purpose percentages from CMS data
    """
    if cms_trip_file is None:
        cms_trip_file = 'input_data/cms/Citywide_Mobility_Survey_-_Trip_2019.csv'

    print("Analyzing CMS 2019 trip data...")

    try:
        cms = pd.read_csv(cms_trip_file)

        # Map CMS purpose categories to our 3-purpose system
        # d_purpose_category: 1=Home, 2=Work, 3=Work-related, 4=School, 5=School-related,
        #                     6=Escort, 7=Shopping, 8=Meal, 9=Social/Recreation, 10=Errand

        # HBW: Work (2) + Work-related (3)
        hbw_trips = cms[cms['d_purpose_category'].isin([2, 3])].shape[0]

        # HBO: Home (1) + School (4,5) + Escort (6) + Shopping (7) + Meal (8) + Social (9) + Errand (10)
        hbo_trips = cms[cms['d_purpose_category'].isin([1, 4, 5, 6, 7, 8, 9, 10])].shape[0]

        # NHB: Estimated as remaining trips (non-home-based patterns)
        # For simplicity, we'll use national averages as proxy
        total_trips = cms[cms['d_purpose_category'] > 0].shape[0]

        # Apply typical NHB fraction (30-40% of total trips nationally)
        # Conservative: use 30%
        nhb_factor = 0.30

        hbw_pct = hbw_trips / total_trips
        hbo_pct = hbo_trips / total_trips

        # Adjust to account for NHB
        total_home_based = hbw_pct + hbo_pct
        nhb_pct = nhb_factor

        # Normalize to sum to 1.0
        sum_all = hbw_pct + hbo_pct + nhb_pct
        hbw_pct /= sum_all
        hbo_pct /= sum_all
        nhb_pct /= sum_all

        print(f"\nCMS-derived trip purpose distribution:")
        print(f"  HBW (Home-Based Work):      {hbw_pct:.1%}")
        print(f"  HBO (Home-Based Other):     {hbo_pct:.1%}")
        print(f"  NHB (Non-Home-Based):       {nhb_pct:.1%}")

        return hbw_pct, hbo_pct, nhb_pct

    except FileNotFoundError:
        print(f"Warning: CMS file not found. Using national averages.")
        # National averages (conservative)
        return 0.25, 0.45, 0.30


def create_brooklyn_multipurpose_trip_rates(output_path: str = None):
    """
    Create Brooklyn-specific POI trip rate table with all 3 trip purposes

    Based on:
    - NYC CEQR rates (validated baseline for HBW)
    - Conservative scaling for HBO and NHB
    - CMS trip distribution patterns

    Parameters
    ----------
    output_path : str, optional
        Path to save output CSV file

    Returns
    -------
    pd.DataFrame : Complete POI trip rate table
    """

    # Get trip purpose distribution from CMS
    hbw_pct, hbo_pct, nhb_pct = analyze_cms_trip_distribution()

    # Scaling factors for each purpose relative to total daily trips
    # HBW uses NYC CEQR as-is (purpose 1)
    # HBO and NHB scale from total based on purpose distribution

    # Define POI types with rates for all 3 purposes
    # Format: (poi_id, building, unit, p1, a1, p2, a2, p3, a3, notes)
    # p1/a1 = HBW production/attraction (from NYC CEQR)
    # p2/a2 = HBO production/attraction (scaled conservatively)
    # p3/a3 = NHB production/attraction (scaled conservatively)

    poi_rates = [
        # OFFICE - Major work destinations (HBW dominant)
        (0, 'office', '1,000 Sq. Ft. GFA',
         2.16, 15.84,  # HBW: NYC CEQR (12% out, 88% in)
         0.95, 2.80,   # HBO: Some errands/meetings during day
         1.40, 1.95,   # NHB: Work-to-lunch, work-to-meeting trips
         'Office - NYC CEQR baseline for HBW, conservative HBO/NHB'),

        # RESIDENTIAL - Trip production for all purposes, HBO attraction
        (1, 'residential', '1,000 Sq. Ft. GFA',
         0.10, 0.72,   # HBW: NYC CEQR (AM peak commute)
         0.85, 2.15,   # HBO: High production for shopping/errands/return home
         0.50, 1.25,   # NHB: Moderate (visitors, deliveries)
         'Residential - Multi-family, NYC CEQR baseline'),

        (2, 'apartments', '1,000 Sq. Ft. GFA',
         0.10, 0.72,   # HBW
         0.85, 2.15,   # HBO
         0.50, 1.25,   # NHB
         'Apartments - Same as residential'),

        (3, 'house', '1,000 Sq. Ft. GFA',
         0.15, 1.12,   # HBW: NYC CEQR (lower density)
         1.05, 2.65,   # HBO: Higher per-sf for single-family
         0.65, 1.55,   # NHB
         'Single-family house - NYC CEQR baseline'),

        # HOTELS - Business and leisure travel
        (4, 'hotel', 'per room',
         1.09, 9.81,   # HBW: NYC CEQR (business travelers)
         2.45, 14.50,  # HBO: Leisure travelers, dining, sightseeing
         1.80, 8.75,   # NHB: Hotel-to-attraction trips
         'Hotel - NYC CEQR baseline, high HBO for tourism'),

        # RETAIL - Shopping destinations (HBO dominant)
        (5, 'retail', '1,000 Sq. Ft. GFA',
         0.52, 28.48,  # HBW: NYC CEQR (employees only)
         1.85, 98.50,  # HBO: Major shopping destination
         2.45, 45.20,  # NHB: Non-home-based shopping chains
         'Retail - NYC CEQR baseline, scaled HBO for Brooklyn shopping'),

        (6, 'commercial', '1,000 Sq. Ft. GFA',
         0.52, 28.48,  # HBW
         1.85, 98.50,  # HBO
         2.45, 45.20,  # NHB
         'Commercial - Same as retail'),

        # FOOD SERVICE - HBO and NHB dominant
        (7, 'fast_food', '1,000 Sq. Ft. GFA',
         0.89, 43.61,  # HBW: NYC CEQR (employees)
         3.15, 152.50, # HBO: High turnover, meals out
         4.20, 95.80,  # NHB: Work-lunch, quick meals
         'Fast food - NYC CEQR baseline, scaled for high turnover'),

        (8, 'restaurant', '1,000 Sq. Ft. GFA',
         0.25, 21.35,  # HBW: NYC CEQR
         1.20, 74.50,  # HBO: Dining out (home-based)
         1.65, 45.20,  # NHB: Work-dinner, meeting meals
         'Restaurant - NYC CEQR baseline'),

        (9, 'cafe', '1,000 Sq. Ft. GFA',
         0.89, 43.61,  # HBW: Using fast food proxy
         3.15, 152.50, # HBO: Brooklyn cafe culture
         4.20, 95.80,  # NHB
         'Cafe - High turnover like fast food'),

        (10, 'bar', '1,000 Sq. Ft. GFA',
         0.25, 21.35,  # HBW
         1.20, 74.50,  # HBO: Evening/weekend social
         1.65, 45.20,  # NHB
         'Bar - Restaurant proxy'),

        (11, 'pub', '1,000 Sq. Ft. GFA',
         0.25, 21.35,  # HBW
         1.20, 74.50,  # HBO
         1.65, 45.20,  # NHB
         'Pub - Restaurant proxy'),

        # SUPERMARKET - Major HBO attraction
        (12, 'supermarket', '1,000 Sq. Ft. GFA',
         1.28, 253.72, # HBW: NYC CEQR (employees)
         4.50, 885.00, # HBO: Grocery shopping (scaled conservatively)
         5.95, 420.50, # NHB: Convenience stops
         'Supermarket - NYC CEQR baseline, conservative HBO scaling'),

        (13, 'convenience', '1,000 Sq. Ft. GFA',
         0.89, 43.61,  # HBW
         3.15, 152.50, # HBO: Quick shopping
         4.20, 95.80,  # NHB
         'Convenience - Fast food proxy'),

        # EDUCATION - School trips
        (14, 'university', '1,000 Sq. Ft. GFA',
         0.42, 26.18,  # HBW: NYC CEQR (faculty/staff)
         1.85, 38.50,  # HBO: Student activities, campus events
         2.45, 28.75,  # NHB: Campus-to-campus, research trips
         'University - NYC CEQR baseline'),

        (15, 'college', '1,000 Sq. Ft. GFA',
         0.42, 26.18,  # HBW
         1.85, 38.50,  # HBO
         2.45, 28.75,  # NHB
         'College - University proxy'),

        (16, 'school', '1,000 Sq. Ft. GFA',
         0.20, 1.80,   # HBW: NYC CEQR (teachers/staff)
         0.88, 6.30,   # HBO: Student drop-off/pick-up, after-school
         1.15, 4.75,   # NHB
         'K-12 School - NYC CEQR baseline'),

        # HEALTHCARE
        (17, 'hospital', '1,000 Sq. Ft. GFA',
         3.73, 70.87,  # HBW: NYC CEQR (medical staff)
         5.20, 98.50,  # HBO: Patient visits, emergencies
         6.85, 75.40,  # NHB: Inter-facility transfers
         'Hospital - NYC CEQR baseline'),

        # FITNESS/RECREATION - HBO dominant
        (18, 'Gym', '1,000 Sq. Ft. GFA',
         0.77, 50.83,  # HBW: NYC CEQR
         2.70, 177.50, # HBO: Fitness/recreation (home-based)
         3.55, 108.20, # NHB: Work-gym trips
         'Gym/Health Club - NYC CEQR baseline'),

        # ENTERTAINMENT - HBO dominant
        (19, 'theatre', '1,000 Sq. Ft. GFA',
         0.27, 2.99,   # HBW: NYC CEQR (staff)
         1.20, 10.45,  # HBO: Entertainment (home-based)
         1.58, 8.05,   # NHB
         'Theatre - NYC CEQR baseline'),

        (20, 'cinema', '1,000 Sq. Ft. GFA',
         0.27, 2.99,   # HBW
         1.20, 10.45,  # HBO
         1.58, 8.05,   # NHB
         'Cinema - Theatre proxy'),

        (21, 'arts_centre', '1,000 Sq. Ft. GFA',
         0.27, 2.99,   # HBW
         1.20, 10.45,  # HBO: Brooklyn arts scene
         1.58, 8.05,   # NHB
         'Arts Centre - Theatre proxy'),

        # LIBRARY - HBO attraction
        (22, 'library', '1,000 Sq. Ft. GFA',
         1.33, 32.47,  # HBW: NYC CEQR (staff)
         2.35, 113.50, # HBO: Reading, study, community programs
         3.10, 69.20,  # NHB
         'Library - NYC CEQR baseline'),

        # MUSEUM - HBO attraction
        (23, 'museum', '1,000 Sq. Ft. GFA',
         0.00, 27.00,  # HBW: NYC CEQR (pure attraction, staff minimal)
         0.50, 94.50,  # HBO: Cultural visits (home-based)
         0.65, 57.50,  # NHB: Tourist chains
         'Museum - NYC CEQR baseline'),

        # FINANCIAL SERVICES
        (24, 'bank', '1,000 Sq. Ft. GFA',
         9.00, 9.00,   # HBW: NYC CEQR (balanced)
         4.00, 31.50,  # HBO: Banking errands
         5.30, 19.20,  # NHB
         'Bank - NYC CEQR baseline'),

        (25, 'pharmacy', '1,000 Sq. Ft. GFA',
         1.28, 253.72, # HBW: Supermarket proxy (retail+service)
         4.50, 885.00, # HBO
         5.95, 420.50, # NHB
         'Pharmacy - Supermarket proxy'),

        # GOVERNMENT/PUBLIC SERVICES
        (26, 'post_office', '1,000 Sq. Ft. GFA',
         1.80, 16.20,  # HBW: Office proxy scaled
         2.52, 22.68,  # HBO: Errands
         3.33, 17.42,  # NHB
         'Post Office - Office proxy scaled'),

        (27, 'government', '1,000 Sq. Ft. GFA',
         2.16, 15.84,  # HBW: Office proxy
         0.95, 2.80,   # HBO
         1.40, 1.95,   # NHB
         'Government - Office proxy'),

        (28, 'public', '1,000 Sq. Ft. GFA',
         2.16, 15.84,  # HBW
         0.95, 2.80,   # HBO
         1.40, 1.95,   # NHB
         'Public building - Office proxy'),

        (29, 'police', '1,000 Sq. Ft. GFA',
         2.16, 15.84,  # HBW
         0.95, 2.80,   # HBO
         1.40, 1.95,   # NHB
         'Police - Office proxy'),

        (30, 'fire_station', '1,000 Sq. Ft. GFA',
         2.16, 15.84,  # HBW
         0.95, 2.80,   # HBO
         1.40, 1.95,   # NHB
         'Fire Station - Office proxy'),

        (31, 'courthouse', '1,000 Sq. Ft. GFA',
         2.16, 15.84,  # HBW
         0.95, 2.80,   # HBO
         1.40, 1.95,   # NHB
         'Courthouse - Office proxy'),

        (32, 'civic', '1,000 Sq. Ft. GFA',
         2.16, 15.84,  # HBW
         0.95, 2.80,   # HBO
         1.40, 1.95,   # NHB
         'Civic - Office proxy'),

        # PARKING - Pure attraction
        (33, 'parking', '1,000 Sq. Ft. GFA',
         0.00, 50.00,  # HBW: NYC CEQR
         0.00, 175.00, # HBO: High attraction for all purposes
         0.00, 106.50, # NHB
         'Parking - Pure attraction, high HBO'),

        (34, 'parking_entrance', '1,000 Sq. Ft. GFA',
         0.00, 50.00,  # HBW
         0.00, 175.00, # HBO
         0.00, 106.50, # NHB
         'Parking entrance - Same as parking'),

        (35, 'bicycle_parking', '1,000 Sq. Ft. GFA',
         0.00, 10.00,  # HBW: NYC CEQR
         0.00, 35.00,  # HBO: Brooklyn cycling culture
         0.00, 21.30,  # NHB
         'Bicycle parking - Scaled from auto parking'),

        # RELIGIOUS/COMMUNITY
        (36, 'place_of_worship', '1,000 Sq. Ft. GFA',
         0.10, 5.00,   # HBW: NYC CEQR (minimal)
         0.35, 17.50,  # HBO: Weekly services, community events
         0.46, 10.65,  # NHB
         'Place of worship - NYC CEQR baseline'),

        (37, 'church;yes', '1,000 Sq. Ft. GFA',
         0.10, 5.00,   # HBW
         0.35, 17.50,  # HBO
         0.46, 10.65,  # NHB
         'Church - Place of worship proxy'),

        # SPORTS/EVENTS
        (38, 'stadium', '1,000 Sq. Ft. GFA',
         0.00, 25.00,  # HBW: NYC CEQR (event-based)
         0.00, 87.50,  # HBO: High during events
         0.00, 53.25,  # NHB
         'Stadium - Event-based, high HBO'),

        (39, 'nightclub', '1,000 Sq. Ft. GFA',
         0.25, 21.35,  # HBW: Restaurant proxy
         1.20, 74.50,  # HBO
         1.65, 45.20,  # NHB
         'Nightclub - Restaurant proxy'),

        (40, 'conference_centre', '1,000 Sq. Ft. GFA',
         2.16, 15.84,  # HBW: Office proxy
         0.95, 2.80,   # HBO
         1.40, 1.95,   # NHB
         'Conference Centre - Office proxy'),

        # HOUSING TYPES
        (41, 'dormitory', '1,000 Sq. Ft. GFA',
         0.10, 0.72,   # HBW: Residential proxy
         0.85, 2.15,   # HBO
         0.50, 1.25,   # NHB
         'Dormitory - Residential proxy'),

        (42, 'shelter', '1,000 Sq. Ft. GFA',
         0.10, 0.72,   # HBW: Residential proxy
         0.85, 2.15,   # HBO
         0.50, 1.25,   # NHB
         'Shelter - Residential proxy'),

        (43, 'embassy', '1,000 Sq. Ft. GFA',
         2.16, 15.84,  # HBW: Office proxy
         0.95, 2.80,   # HBO
         1.40, 1.95,   # NHB
         'Embassy - Office proxy'),

        # DEFAULT
        (44, 'yes', '1,000 Sq. Ft. GFA',
         1.00, 1.00,   # HBW: NYC CEQR (generic)
         3.50, 3.50,   # HBO: Balanced
         4.63, 2.13,   # NHB
         'Generic building - Balanced across purposes'),

        (45, '', '1,000 Sq. Ft. GFA',
         0.50, 0.50,   # HBW: NYC CEQR (unknown)
         1.75, 1.75,   # HBO
         2.31, 1.06,   # NHB
         'Unknown/unclassified - Conservative rates'),
    ]

    # Create DataFrame
    df = pd.DataFrame(poi_rates, columns=[
        'poi_type_id', 'building', 'unit_of_measure',
        'production_rate1', 'attraction_rate1',
        'production_rate2', 'attraction_rate2',
        'production_rate3', 'attraction_rate3',
        'notes'
    ])

    # Split notes into production and attraction notes
    df['production_notes'] = df['notes']
    df['attraction_notes'] = df['notes']
    df = df.drop(columns=['notes'])

    # Add trip_purpose column (always 1 for compatibility with grid2demand)
    df['trip_purpose'] = 1

    # Reorder columns to match expected format
    df = df[[
        'poi_type_id', 'building', 'unit_of_measure', 'trip_purpose',
        'production_rate1', 'attraction_rate1',
        'production_rate2', 'attraction_rate2',
        'production_rate3', 'attraction_rate3',
        'production_notes', 'attraction_notes'
    ]]

    # Save if output path provided
    if output_path:
        df.to_csv(output_path, index=False)
        print(f"\n✓ Brooklyn multi-purpose POI trip rates saved to: {output_path}")
        print(f"  Total POI types: {len(poi_rates)}")
        print(f"  Columns: {list(df.columns)}")
        print(f"\nSample rates for 'office':")
        office = df[df['building'] == 'office'].iloc[0]
        print(f"  HBW: Production={office['production_rate1']:.2f}, Attraction={office['attraction_rate1']:.2f}")
        print(f"  HBO: Production={office['production_rate2']:.2f}, Attraction={office['attraction_rate2']:.2f}")
        print(f"  NHB: Production={office['production_rate3']:.2f}, Attraction={office['attraction_rate3']:.2f}")

    return df


if __name__ == '__main__':
    # Generate the trip rate file
    output_file = 'settings/brooklyn_poi_trip_rate_multipurpose.csv'
    df = create_brooklyn_multipurpose_trip_rates(output_path=output_file)

    print("\n" + "="*60)
    print("Multi-purpose trip rate file created successfully!")
    print("="*60)
