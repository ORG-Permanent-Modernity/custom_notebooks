"""Buildings and POI processing library for OSM data."""

from .building_processor import load_buildings, process_buildings, save_buildings
from .poi_processor import load_pois, process_pois, save_pois
from .spatial_matcher import match_pois_to_buildings, join_matches_to_pois
from .heuristics import (
    apply_heuristics_to_pois,
    POI_HEURISTICS,
    BUILDING_TYPE_MAP,
    get_poi_type
)
from .unified_poi_generator import (
    create_unified_pois,
    save_unified_pois,
    print_summary_statistics
)
from .trip_generator import (
    create_trip_generators,
    save_trip_generators,
    print_trip_gen_summary,
    convert_to_trip_gen_units,
    TRIP_GEN_LAND_USE_MAP
)
from .trip_generator_optimized import create_trip_generators_optimized
from .config import CityConfig, get_city_config

__all__ = [
    # Building processor
    'load_buildings',
    'process_buildings',
    'save_buildings',

    # POI processor
    'load_pois',
    'process_pois',
    'save_pois',

    # Spatial matcher
    'match_pois_to_buildings',
    'join_matches_to_pois',

    # Heuristics
    'apply_heuristics_to_pois',
    'POI_HEURISTICS',
    'BUILDING_TYPE_MAP',
    'get_poi_type',

    # Unified POI generator (legacy naming)
    'create_unified_pois',
    'save_unified_pois',
    'print_summary_statistics',

    # Trip generator (new preferred naming)
    'create_trip_generators',
    'save_trip_generators',
    'print_trip_gen_summary',
    'convert_to_trip_gen_units',
    'TRIP_GEN_LAND_USE_MAP',

    # Optimized trip generator
    'create_trip_generators_optimized',

    # Configuration
    'CityConfig',
    'get_city_config',
]