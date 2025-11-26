"""
4-Step Transportation Demand Model

A modular implementation of the classic 4-step travel demand model:
1. Trip Generation - Calculate productions and attractions by zone
2. Trip Distribution - Gravity model to distribute trips between zones
3. Mode Choice - Split trips by travel mode
4. Traffic Assignment - Assign vehicle trips to network

Author: Custom implementation for Brooklyn, NY
"""

from .trip_generation import (
    assign_generators_to_zones,
    calculate_zone_trips,
    balance_trip_ends,
    create_zone_arrays,
    TripRates
)

from .trip_distribution import (
    gravity_model,
    calculate_impedance_matrix,
    furness_balance,
    calibrate_friction_parameter,
    FrictionFunction,
    GravityModelResult
)

from .mode_choice import (
    multinomial_logit,
    apply_mode_choice,
    ModeChoiceModel,
    create_urban_mode_impedance,
    run_mode_choice
)

from .traffic_assignment import (
    all_or_nothing,
    user_equilibrium,
    NetworkAssignment
)

from .validation import (
    compare_tlfd,
    validate_mode_shares,
    validate_productions,
    model_diagnostics,
    reasonableness_checks
)

from .acs_data import (
    get_auto_ownership_by_tract,
    get_commute_mode_shares_by_tract,
    get_zone_auto_ownership,
    join_acs_to_zones,
    estimate_bike_availability,
    estimate_bike_availability_from_acs,
    get_bike_availability_for_zones,
    STATE_FIPS,
    NYC_COUNTIES,
    BIKE_AVAILABILITY_RATES
)

from .cms_data import (
    load_cms_trips,
    load_cms_persons,
    load_cms_households,
    filter_brooklyn_trips,
    calculate_mode_shares,
    get_brooklyn_mode_shares,
    get_ownership_statistics,
    get_brooklyn_ownership,
    get_trip_length_distribution,
    get_person_bike_usage,
    get_mode_choice_calibration_targets,
    analyze_cms_data,
    CMSModeShares,
    CMSOwnershipStats,
    MODE_TYPE_CODES,
    BROOKLYN_ZONES,
)

from .pipeline import run_4step_model

__version__ = "0.1.0"
__all__ = [
    # Trip Generation
    "assign_generators_to_zones",
    "calculate_zone_trips",
    "balance_trip_ends",
    "create_zone_arrays",
    "TripRates",
    # Trip Distribution
    "gravity_model",
    "calculate_impedance_matrix",
    "furness_balance",
    "calibrate_friction_parameter",
    "FrictionFunction",
    "GravityModelResult",
    # Mode Choice
    "multinomial_logit",
    "apply_mode_choice",
    "ModeChoiceModel",
    "create_urban_mode_impedance",
    "run_mode_choice",
    # Traffic Assignment
    "all_or_nothing",
    "user_equilibrium",
    "NetworkAssignment",
    # Validation
    "compare_tlfd",
    "validate_mode_shares",
    "validate_productions",
    "model_diagnostics",
    "reasonableness_checks",
    # ACS Data
    "get_auto_ownership_by_tract",
    "get_commute_mode_shares_by_tract",
    "get_zone_auto_ownership",
    "join_acs_to_zones",
    "estimate_bike_availability",
    "estimate_bike_availability_from_acs",
    "get_bike_availability_for_zones",
    "STATE_FIPS",
    "NYC_COUNTIES",
    "BIKE_AVAILABILITY_RATES",
    # CMS Data
    "load_cms_trips",
    "load_cms_persons",
    "load_cms_households",
    "filter_brooklyn_trips",
    "calculate_mode_shares",
    "get_brooklyn_mode_shares",
    "get_ownership_statistics",
    "get_brooklyn_ownership",
    "get_trip_length_distribution",
    "get_person_bike_usage",
    "get_mode_choice_calibration_targets",
    "analyze_cms_data",
    "CMSModeShares",
    "CMSOwnershipStats",
    "MODE_TYPE_CODES",
    "BROOKLYN_ZONES",
    # Pipeline
    "run_4step_model",
]
