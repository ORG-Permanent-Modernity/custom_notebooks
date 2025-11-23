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
from .trip_generator import (
    create_trip_generators,
    save_trip_generators,
    print_trip_gen_summary,
    TRIP_GEN_LAND_USE_MAP
)
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

    # Trip generator (new preferred naming)
    'create_trip_generators',
    'save_trip_generators',
    'print_trip_gen_summary',
    'TRIP_GEN_LAND_USE_MAP',

    # Configuration
    'CityConfig',
    'get_city_config',
]
