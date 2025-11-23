"""Brooklyn-specific heuristics for POI space allocation."""

import pandas as pd


# POI space allocation heuristics
# Format: {poi_type: (floors_occupied, remaining_use)}
POI_HEURISTICS = {
    # RELIGIOUS
    'place_of_worship': ('full', None),

    # EDUCATION
    'school': ('full', None),
    'kindergarten': ('full', None),
    'college': ('full', None),
    'university': ('full', None),
    'library': ('full', None),

    # HEALTHCARE
    'hospital': ('full', None),
    'clinic': ('ground', 'residential'),
    'doctors': ('ground', 'residential'),
    'dentist': ('ground', 'residential'),
    'pharmacy': ('ground', 'residential'),
    'veterinary': ('ground', 'residential'),

    # FOOD/DRINK
    'restaurant': ('ground', 'residential'),
    'cafe': ('ground', 'residential'),
    'fast_food': ('ground', 'residential'),
    'bar': ('ground', 'residential'),
    'pub': ('ground', 'residential'),
    'ice_cream': ('ground', 'residential'),
    'food_court': ('ground', 'residential'),

    # RETAIL
    'supermarket': ('ground', 'residential'),
    'convenience': ('ground', 'residential'),
    'clothes': ('ground', 'residential'),
    'shoes': ('ground', 'residential'),
    'hardware': ('ground', 'residential'),
    'doityourself': ('ground', 'residential'),
    'electronics': ('ground', 'residential'),
    'mobile_phone': ('ground', 'residential'),
    'furniture': ('multi', 'residential'),
    'department_store': ('full', None),
    'mall': ('full', None),
    'bakery': ('ground', 'residential'),
    'butcher': ('ground', 'residential'),
    'greengrocer': ('ground', 'residential'),
    'deli': ('ground', 'residential'),
    'alcohol': ('ground', 'residential'),
    'wine': ('ground', 'residential'),
    'books': ('ground', 'residential'),
    'gift': ('ground', 'residential'),
    'jewelry': ('ground', 'residential'),
    'optician': ('ground', 'residential'),

    # SERVICES
    'bank': ('ground', 'office'),
    'post_office': ('ground', 'office'),
    'laundry': ('ground', 'residential'),
    'dry_cleaning': ('ground', 'residential'),
    'hairdresser': ('ground', 'residential'),
    'beauty': ('ground', 'residential'),
    'copyshop': ('ground', 'office'),

    # OFFICE
    'yes': ('full', None),
    'company': ('full', None),
    'government': ('full', None),
    'insurance': ('full', None),
    'lawyer': ('ground', 'office'),
    'coworking_space': ('multi', 'office'),

    # LEISURE
    'fitness_centre': ('multi', 'residential'),
    'sports_centre': ('full', None),
    'swimming_pool': ('full', None),
    'pitch': ('full', None),

    # ENTERTAINMENT
    'cinema': ('full', None),
    'theatre': ('full', None),
    'nightclub': ('ground', 'residential'),
    'arts_centre': ('full', None),
    'community_centre': ('full', None),
    'museum': ('full', None),

    # ACCOMMODATION
    'hotel': ('full', None),
    'hostel': ('full', None),
    'guest_house': ('full', None),

    # INDUSTRIAL/WAREHOUSE
    'warehouse': ('full', None),
    'industrial': ('full', None),

    # DEFAULT for unknown types by category
    'default_amenity': ('ground', 'residential'),
    'default_shop': ('ground', 'residential'),
    'default_office': ('full', None),
    'default_leisure': ('ground', 'residential'),
    'default_tourism': ('full', None),
}

# Building type to POI type mapping
BUILDING_TYPE_MAP = {
    # Commercial/Retail
    'commercial': 'commercial',
    'retail': 'retail',
    'office': 'office',
    'supermarket': 'supermarket',
    'kiosk': 'convenience',

    # Industrial
    'industrial': 'industrial',
    'warehouse': 'warehouse',

    # Religious
    'church': 'place_of_worship',
    'chapel': 'place_of_worship',
    'cathedral': 'place_of_worship',
    'mosque': 'place_of_worship',
    'synagogue': 'place_of_worship',
    'temple': 'place_of_worship',
    'shrine': 'place_of_worship',
    'kingdom_hall': 'place_of_worship',

    # Education
    'school': 'school',
    'university': 'university',
    'college': 'college',
    'kindergarten': 'kindergarten',

    # Healthcare
    'hospital': 'hospital',

    # Accommodation
    'hotel': 'hotel',
    'dormitory': 'residential',

    # Residential
    'residential': 'residential',
    'apartments': 'residential',
    'house': 'residential',
    'detached': 'residential',
    'semidetached_house': 'residential',
    'terrace': 'residential',
    'bungalow': 'residential',

    # Default
    'yes': 'residential',
}


def get_poi_type(row):
    """Extract the primary POI type from available columns."""
    for col in ['amenity', 'shop', 'office', 'leisure', 'tourism']:
        if col in row.index and pd.notna(row[col]):
            return (col, row[col])
    return ('unknown', 'unknown')


def apply_heuristics_to_pois(pois_matched, buildings_gdf):
    """
    Apply heuristics to estimate POI area and remaining building usage.

    Parameters:
    -----------
    pois_matched : GeoDataFrame
        POIs matched to buildings
    buildings_gdf : GeoDataFrame
        Buildings data with building_id, total_sqft, footprint_sqft, estimated_floors

    Returns:
    --------
    DataFrame
        Processed POIs with square footage allocations
    """
    # Create lookup dict for buildings
    buildings_lookup = buildings_gdf.set_index('building_id').to_dict('index')

    # Group POIs by building
    pois_by_building = pois_matched.groupby('building_id')

    processed_pois = []

    for building_id, building_pois in pois_by_building:
        building_id = int(building_id)
        building_data = buildings_lookup.get(building_id)

        if building_data is None:
            continue

        building_sqft = building_data['total_sqft']
        footprint = building_data['footprint_sqft']
        floors = building_data['estimated_floors']

        # Classify each POI's space requirement
        poi_allocations = []
        for idx, poi in building_pois.iterrows():
            poi_category, poi_type = get_poi_type(poi)

            # Look up heuristic
            if poi_type in POI_HEURISTICS:
                floors_rule, remaining_use = POI_HEURISTICS[poi_type]
            else:
                default_key = f'default_{poi_category}'
                if default_key in POI_HEURISTICS:
                    floors_rule, remaining_use = POI_HEURISTICS[default_key]
                else:
                    floors_rule, remaining_use = ('ground', 'residential')

            poi_allocations.append({
                'poi_id': poi['poi_id'],
                'name': poi.get('name', ''),
                'poi_category': poi_category,
                'poi_type': poi_type,
                'floors_rule': floors_rule,
                'remaining_use': remaining_use,
                'geometry': poi.geometry
            })

        # Allocate space avoiding double-counting
        full_building_pois = [p for p in poi_allocations if p['floors_rule'] == 'full']
        ground_floor_pois = [p for p in poi_allocations if p['floors_rule'] == 'ground']
        multi_floor_pois = [p for p in poi_allocations if p['floors_rule'] == 'multi']

        # Track what's been allocated
        allocated_sqft = 0

        if full_building_pois:
            # Split evenly among full-building POIs
            sqft_per_full = building_sqft / len(full_building_pois)
            for poi_info in full_building_pois:
                processed_pois.append({
                    'poi_id': poi_info['poi_id'],
                    'building_id': building_id,
                    'name': poi_info['name'],
                    'poi_category': poi_info['poi_category'],
                    'poi_type': poi_info['poi_type'],
                    'poi_sqft': sqft_per_full,
                    'building_total_sqft': building_sqft,
                    'building_floors': floors,
                    'geometry': poi_info['geometry']
                })
            remaining_sqft = 0
            remaining_use = None
        else:
            # Ground floor POIs share the ground floor
            if ground_floor_pois:
                ground_floor_sqft = footprint
                sqft_per_ground = ground_floor_sqft / len(ground_floor_pois)
                for poi_info in ground_floor_pois:
                    processed_pois.append({
                        'poi_id': poi_info['poi_id'],
                        'building_id': building_id,
                        'name': poi_info['name'],
                        'poi_category': poi_info['poi_category'],
                        'poi_type': poi_info['poi_type'],
                        'poi_sqft': sqft_per_ground,
                        'building_total_sqft': building_sqft,
                        'building_floors': floors,
                        'geometry': poi_info['geometry']
                    })
                allocated_sqft += ground_floor_sqft

            # Multi-floor POIs get 2 floors, shared if multiple
            if multi_floor_pois:
                multi_floor_sqft = min(footprint * 2, building_sqft - allocated_sqft)
                sqft_per_multi = multi_floor_sqft / len(multi_floor_pois) if multi_floor_pois else 0
                for poi_info in multi_floor_pois:
                    processed_pois.append({
                        'poi_id': poi_info['poi_id'],
                        'building_id': building_id,
                        'name': poi_info['name'],
                        'poi_category': poi_info['poi_category'],
                        'poi_type': poi_info['poi_type'],
                        'poi_sqft': sqft_per_multi,
                        'building_total_sqft': building_sqft,
                        'building_floors': floors,
                        'geometry': poi_info['geometry']
                    })
                allocated_sqft += multi_floor_sqft

            # Calculate remaining space
            remaining_sqft = max(0, building_sqft - allocated_sqft)

            # Determine remaining use
            remaining_uses = [p['remaining_use'] for p in poi_allocations if p['remaining_use']]
            if 'office' in remaining_uses:
                remaining_use = 'office'
            elif remaining_uses:
                remaining_use = 'residential'
            else:
                remaining_use = None

        # Store remaining space info
        if remaining_sqft > 0 and remaining_use:
            rep_geom = poi_allocations[0]['geometry']
            processed_pois.append({
                'poi_id': f"remaining_{building_id}",
                'building_id': building_id,
                'name': f"{remaining_use.title()} (upper floors)",
                'poi_category': 'inferred',
                'poi_type': remaining_use,
                'poi_sqft': remaining_sqft,
                'building_total_sqft': building_sqft,
                'building_floors': floors,
                'geometry': rep_geom,
                'is_remaining': True
            })

    processed_df = pd.DataFrame(processed_pois)
    print(f"Processed POIs (including inferred remaining): {len(processed_df):,}")

    return processed_df