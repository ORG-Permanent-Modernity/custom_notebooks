"""
Mode Choice Module

Step 3 of the 4-step model: Split person trips by travel mode.

Implements multinomial logit model for mode choice with configurable
utility functions and coefficients.
"""

from dataclasses import dataclass, field
from typing import Optional, Literal
import numpy as np
import pandas as pd


@dataclass
class ModeChoiceModel:
    """
    Mode choice model configuration and coefficients.

    Default coefficients are representative values for urban areas.
    Should be calibrated to local observed mode shares.
    """

    # Available modes
    modes: list = field(default_factory=lambda: [
        "auto_driver",
        "auto_passenger",
        "transit",
        "walk",
        "bike"
    ])

    # Alternative-specific constants (ASC)
    # Base mode is auto_driver (ASC = 0)
    # Note: bike ASC is low because biking has many barriers beyond time/distance
    # (weather, safety, physical ability, carrying capacity, etc.)
    asc: dict = field(default_factory=lambda: {
        "auto_driver": 0.0,
        "auto_passenger": -1.5,
        "transit": -0.8,
        "walk": -1.2,
        "bike": -3.5,  # Strong penalty for non-time/distance barriers
    })

    # Coefficient for in-vehicle travel time (minutes)
    # Negative because more time = less utility
    beta_ivtt: float = -0.025

    # Coefficient for out-of-vehicle travel time (walk, wait, transfer)
    # Typically 2-3x more negative than IVTT
    beta_ovtt: float = -0.050

    # Coefficient for cost (dollars)
    beta_cost: float = -0.15

    # Mode-specific adjustments
    # Transit access/egress time coefficient
    beta_transit_access: float = -0.040

    # Walk/bike distance coefficient (miles)
    beta_walk_distance: float = -0.80
    beta_bike_distance: float = -0.50  # Stronger penalty - biking gets harder with distance

    # Maximum walk distance for walk mode (miles)
    max_walk_distance: float = 2.0

    # Maximum bike distance for bike mode (miles)
    # Most bike trips are under 3 miles; 5 miles is a reasonable cap
    max_bike_distance: float = 5.0

    # Auto occupancy for vehicle trip conversion
    auto_occupancy: dict = field(default_factory=lambda: {
        "auto_driver": 1.0,
        "auto_passenger": 0.0,  # Doesn't add vehicles
    })


@dataclass
class ModeImpedance:
    """
    Impedance matrices by mode.

    Each matrix is (n_zones, n_zones) with travel time or distance.
    """
    auto_time: np.ndarray          # Minutes
    transit_time: np.ndarray       # Minutes (including wait/transfer)
    transit_access_time: np.ndarray  # Walk access/egress time
    walk_distance: np.ndarray      # Miles
    bike_distance: np.ndarray      # Miles (typically same as walk)
    auto_cost: np.ndarray          # Dollars (fuel + parking)
    transit_fare: np.ndarray       # Dollars
    bike_cost: Optional[np.ndarray] = None  # Dollars (bike share per-trip cost)


def calculate_mode_utilities(
    mode_impedance: ModeImpedance,
    model: ModeChoiceModel,
    zone_attributes: Optional[pd.DataFrame] = None
) -> dict[str, np.ndarray]:
    """
    Calculate utility matrices for each mode.

    Args:
        mode_impedance: Impedance matrices by mode
        model: Mode choice model with coefficients
        zone_attributes: Optional zone-level attributes (parking cost, etc.)

    Returns:
        Dictionary of utility matrices by mode
    """
    n_zones = mode_impedance.auto_time.shape[0]
    utilities = {}

    # Auto driver utility
    utilities["auto_driver"] = (
        model.asc["auto_driver"] +
        model.beta_ivtt * mode_impedance.auto_time +
        model.beta_cost * mode_impedance.auto_cost
    )

    # Auto passenger (same time, no cost to passenger)
    utilities["auto_passenger"] = (
        model.asc["auto_passenger"] +
        model.beta_ivtt * mode_impedance.auto_time
    )

    # Transit utility
    utilities["transit"] = (
        model.asc["transit"] +
        model.beta_ivtt * mode_impedance.transit_time +
        model.beta_transit_access * mode_impedance.transit_access_time +
        model.beta_cost * mode_impedance.transit_fare
    )

    # Walk utility (with distance cap)
    walk_utility = (
        model.asc["walk"] +
        model.beta_walk_distance * mode_impedance.walk_distance
    )
    # Set utility to -inf where distance exceeds max
    walk_utility[mode_impedance.walk_distance > model.max_walk_distance] = -np.inf
    utilities["walk"] = walk_utility

    # Bike utility (with distance cap and optional cost)
    bike_utility = (
        model.asc["bike"] +
        model.beta_bike_distance * mode_impedance.bike_distance
    )
    # Add bike share cost if provided (e.g., Citi Bike per-trip fee)
    if mode_impedance.bike_cost is not None:
        bike_utility = bike_utility + model.beta_cost * mode_impedance.bike_cost
    bike_utility[mode_impedance.bike_distance > model.max_bike_distance] = -np.inf
    utilities["bike"] = bike_utility

    return utilities


def multinomial_logit(
    utilities: dict[str, np.ndarray],
    modes: Optional[list] = None
) -> dict[str, np.ndarray]:
    """
    Apply multinomial logit model to calculate mode probabilities.

    P(mode) = exp(U_mode) / sum(exp(U_all_modes))

    Args:
        utilities: Dictionary of utility matrices by mode
        modes: List of modes to include (uses all if None)

    Returns:
        Dictionary of probability matrices by mode
    """
    if modes is None:
        modes = list(utilities.keys())

    # Stack utilities into 3D array (modes, origins, dests)
    n_zones = list(utilities.values())[0].shape[0]
    n_modes = len(modes)

    utility_stack = np.stack([utilities[m] for m in modes], axis=0)

    # Apply logit formula with numerical stability
    # Subtract max for numerical stability (doesn't change probabilities)
    max_utility = np.max(utility_stack, axis=0, keepdims=True)

    # Handle -inf values (unavailable modes)
    max_utility = np.where(np.isinf(max_utility), 0, max_utility)

    exp_utilities = np.exp(utility_stack - max_utility)

    # Handle -inf -> 0 after exp
    exp_utilities = np.where(np.isinf(utility_stack), 0, exp_utilities)

    # Calculate probabilities
    sum_exp = np.sum(exp_utilities, axis=0, keepdims=True)
    sum_exp = np.maximum(sum_exp, 1e-10)  # Avoid division by zero

    probabilities = exp_utilities / sum_exp

    # Convert back to dictionary
    prob_dict = {mode: probabilities[i] for i, mode in enumerate(modes)}

    return prob_dict


def apply_mode_choice(
    trip_matrix: np.ndarray,
    mode_probabilities: dict[str, np.ndarray],
    verbose: bool = False
) -> dict[str, np.ndarray]:
    """
    Apply mode choice probabilities to trip matrix.

    Args:
        trip_matrix: Total person trips (n_zones, n_zones)
        mode_probabilities: Probability matrices by mode
        verbose: Print mode share summary

    Returns:
        Dictionary of trip matrices by mode
    """
    mode_trips = {}

    for mode, prob_matrix in mode_probabilities.items():
        mode_trips[mode] = trip_matrix * prob_matrix

    if verbose:
        total = trip_matrix.sum()
        print("  Mode shares:")
        for mode, trips in mode_trips.items():
            share = trips.sum() / total * 100
            print(f"    {mode}: {trips.sum():,.0f} trips ({share:.1f}%)")

    return mode_trips


def calculate_vehicle_trips(
    mode_trips: dict[str, np.ndarray],
    model: ModeChoiceModel
) -> np.ndarray:
    """
    Convert person trips to vehicle trips.

    Only auto_driver trips contribute to vehicle trips.
    Auto_passenger trips are in shared vehicles.

    Args:
        mode_trips: Person trip matrices by mode
        model: Mode choice model with occupancy factors

    Returns:
        Vehicle trip matrix
    """
    vehicle_trips = np.zeros_like(mode_trips["auto_driver"])

    for mode, trips in mode_trips.items():
        occupancy = model.auto_occupancy.get(mode, 0.0)
        if occupancy > 0:
            vehicle_trips += trips / occupancy

    return vehicle_trips


def create_simple_mode_impedance(
    distance_matrix: np.ndarray,
    auto_speed_mph: float = 25.0,
    transit_speed_mph: float = 15.0,
    walk_speed_mph: float = 3.0,
    bike_speed_mph: float = 12.0,
    transit_wait_min: float = 10.0,
    auto_cost_per_mile: float = 0.20,
    transit_fare: float = 2.75,
    parking_cost: float = 0.0,
    parking_search_min: float = 0.0,
    bike_share_cost: Optional[float] = None
) -> ModeImpedance:
    """
    Create simple mode impedance from distance matrix.

    Useful when detailed network skims are not available.

    Args:
        distance_matrix: Zone-to-zone distance in miles
        auto_speed_mph: Average auto speed
        transit_speed_mph: Average transit in-vehicle speed
        walk_speed_mph: Walking speed
        bike_speed_mph: Biking speed
        transit_wait_min: Average transit wait + transfer time
        auto_cost_per_mile: Auto operating cost per mile
        transit_fare: Flat transit fare
        parking_cost: Destination parking cost
        parking_search_min: Time spent searching for parking (added to auto time)
        bike_share_cost: Per-trip bike share cost in dollars. If None, assumes
            personal bike (no cost). Citi Bike single ride = $4.49, members ~$0.50/trip.

    Returns:
        ModeImpedance object
    """
    # Calculate travel times (minutes)
    auto_time = distance_matrix / auto_speed_mph * 60 + parking_search_min
    transit_ivt = distance_matrix / transit_speed_mph * 60
    transit_time = transit_ivt + transit_wait_min
    transit_access = np.full_like(distance_matrix, 5.0)  # 5 min walk to transit

    # Costs
    auto_cost = distance_matrix * auto_cost_per_mile + parking_cost
    transit_fare_matrix = np.full_like(distance_matrix, transit_fare)

    # Bike cost (None for personal bike, value for bike share)
    bike_cost_matrix = None
    if bike_share_cost is not None:
        bike_cost_matrix = np.full_like(distance_matrix, bike_share_cost)

    return ModeImpedance(
        auto_time=auto_time,
        transit_time=transit_time,
        transit_access_time=transit_access,
        walk_distance=distance_matrix,
        bike_distance=distance_matrix,
        auto_cost=auto_cost,
        transit_fare=transit_fare_matrix,
        bike_cost=bike_cost_matrix
    )


def create_urban_mode_impedance(
    distance_matrix: np.ndarray,
    area_type: str = "urban_core",
    bike_share_cost: Optional[float] = None
) -> ModeImpedance:
    """
    Create mode impedance with realistic urban parameters.

    Pre-configured for different urban contexts. Use this instead of
    create_simple_mode_impedance for more realistic mode choice results.

    Args:
        distance_matrix: Zone-to-zone distance in miles
        area_type: One of:
            - "urban_core": Dense urban (NYC, SF downtown) - low auto, high transit
            - "urban": Urban (Brooklyn, Queens) - moderate auto, good transit
            - "suburban": Suburban - high auto, limited transit
            - "rural": Rural - auto dominant
        bike_share_cost: Per-trip bike share cost in dollars. If None, uses
            area-type default (assumes mix of personal bikes and bike share).
            Common values:
            - Citi Bike single ride: $4.49
            - Citi Bike member (amortized): ~$0.50-1.00/trip
            - Personal bike: $0.00

    Returns:
        ModeImpedance object
    """
    # Parameters by area type
    # bike_share_cost assumes a mix of personal bikes (free) and bike share users
    # Urban core/urban: higher bike share usage, suburban/rural: mostly personal bikes
    params = {
        "urban_core": {
            "auto_speed_mph": 12.0,      # Heavy congestion
            "transit_speed_mph": 18.0,    # Subway is faster than driving
            "transit_wait_min": 5.0,      # High frequency
            "transit_access_min": 3.0,    # Short walk to station
            "auto_cost_per_mile": 0.25,
            "transit_fare": 2.90,
            "parking_cost": 25.0,         # $25/day average
            "parking_search_min": 15.0,   # Significant search time
            "bike_share_cost": 2.00,      # Mix of members ($0.50) and casual ($4.49)
        },
        "urban": {
            "auto_speed_mph": 18.0,       # Moderate congestion
            "transit_speed_mph": 15.0,
            "transit_wait_min": 7.0,      # Good frequency
            "transit_access_min": 5.0,
            "auto_cost_per_mile": 0.22,
            "transit_fare": 2.90,
            "parking_cost": 12.0,         # $12/day average
            "parking_search_min": 8.0,
            "bike_share_cost": 1.50,      # More members in urban areas
        },
        "suburban": {
            "auto_speed_mph": 30.0,       # Less congestion
            "transit_speed_mph": 12.0,    # Bus is slower
            "transit_wait_min": 15.0,     # Lower frequency
            "transit_access_min": 10.0,   # Longer walk/drive to station
            "auto_cost_per_mile": 0.20,
            "transit_fare": 2.75,
            "parking_cost": 3.0,          # Cheap/free parking
            "parking_search_min": 2.0,
            "bike_share_cost": 0.50,      # Mostly personal bikes, limited bike share
        },
        "rural": {
            "auto_speed_mph": 40.0,
            "transit_speed_mph": 10.0,
            "transit_wait_min": 30.0,     # Very low frequency
            "transit_access_min": 20.0,
            "auto_cost_per_mile": 0.18,
            "transit_fare": 2.50,
            "parking_cost": 0.0,          # Free parking
            "parking_search_min": 0.0,
            "bike_share_cost": 0.0,       # No bike share, personal bikes only
        },
    }

    p = params.get(area_type, params["urban"])

    # Calculate travel times
    auto_time = distance_matrix / p["auto_speed_mph"] * 60 + p["parking_search_min"]
    transit_ivt = distance_matrix / p["transit_speed_mph"] * 60
    transit_time = transit_ivt + p["transit_wait_min"]
    transit_access = np.full_like(distance_matrix, p["transit_access_min"])

    # Costs
    auto_cost = distance_matrix * p["auto_cost_per_mile"] + p["parking_cost"]
    transit_fare_matrix = np.full_like(distance_matrix, p["transit_fare"])

    # Bike share cost - use provided value or area-type default
    bike_cost_value = bike_share_cost if bike_share_cost is not None else p["bike_share_cost"]
    bike_cost_matrix = np.full_like(distance_matrix, bike_cost_value) if bike_cost_value > 0 else None

    return ModeImpedance(
        auto_time=auto_time,
        transit_time=transit_time,
        transit_access_time=transit_access,
        walk_distance=distance_matrix,
        bike_distance=distance_matrix,
        auto_cost=auto_cost,
        transit_fare=transit_fare_matrix,
        bike_cost=bike_cost_matrix
    )


def run_mode_choice(
    trip_matrix: np.ndarray,
    impedance: np.ndarray,
    model: Optional[ModeChoiceModel] = None,
    mode_impedance: Optional[ModeImpedance] = None,
    area_type: Optional[str] = None,
    auto_ownership_rate: Optional[float] = None,
    bike_availability_rate: Optional[float] = None,
    verbose: bool = False
) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """
    Run complete mode choice model.

    Args:
        trip_matrix: Person trip matrix from trip distribution
        impedance: Distance matrix (used if mode_impedance not provided)
        model: Mode choice model (uses defaults if None)
        mode_impedance: Detailed mode impedances (created from distance if None)
        area_type: If provided, use create_urban_mode_impedance() with this type
            Options: "urban_core", "urban", "suburban", "rural"
        auto_ownership_rate: Fraction of trips with auto access (0-1).
            If 0.45, only 45% of trips can choose auto modes.
            This caps auto mode share to reflect vehicle availability.
        bike_availability_rate: Fraction of trips with bike access (0-1).
            Reflects bike ownership, bike share coverage, physical ability.
            Default None = no constraint. Typical urban values: 0.10-0.20.
        verbose: Print progress and results

    Returns:
        Tuple of (mode_trips dict, vehicle_trips matrix)
    """
    if model is None:
        model = ModeChoiceModel()

    if mode_impedance is None:
        if area_type is not None:
            if verbose:
                print(f"  Creating {area_type} mode impedance from distance matrix...")
            mode_impedance = create_urban_mode_impedance(impedance, area_type=area_type)
        else:
            if verbose:
                print("  Creating simple mode impedance from distance matrix...")
            mode_impedance = create_simple_mode_impedance(impedance)

    if verbose:
        print("  Calculating mode utilities...")

    utilities = calculate_mode_utilities(mode_impedance, model)

    if verbose:
        print("  Applying multinomial logit model...")

    probabilities = multinomial_logit(utilities, model.modes)

    # Apply auto ownership constraint if specified
    if auto_ownership_rate is not None and 0 < auto_ownership_rate < 1:
        if verbose:
            print(f"  Applying auto ownership constraint ({auto_ownership_rate:.0%} have car access)...")

        # Calculate unconstrained auto share
        auto_modes = ["auto_driver", "auto_passenger"]

        # For trips from households without cars, redistribute auto prob to other modes
        no_car_fraction = 1 - auto_ownership_rate
        non_auto_modes = [m for m in probabilities if m not in auto_modes]

        for mode in auto_modes:
            if mode in probabilities:
                # Calculate reduction amount
                reduction = probabilities[mode] * no_car_fraction

                # Reduce auto probability
                probabilities[mode] = probabilities[mode] * auto_ownership_rate

                # Redistribute to non-auto modes proportionally
                non_auto_total = sum(probabilities[m] for m in non_auto_modes)

                # Avoid division by zero - use np.where for safe division
                for m in non_auto_modes:
                    share = np.where(non_auto_total > 0,
                                    probabilities[m] / non_auto_total,
                                    1.0 / len(non_auto_modes))
                    probabilities[m] = probabilities[m] + reduction * share

    # Apply bike availability constraint if specified
    if bike_availability_rate is not None and 0 < bike_availability_rate < 1:
        if verbose:
            print(f"  Applying bike availability constraint ({bike_availability_rate:.0%} have bike access)...")

        # For trips from people without bike access, redistribute bike prob to other modes
        no_bike_fraction = 1 - bike_availability_rate
        non_bike_modes = [m for m in probabilities if m != "bike"]

        if "bike" in probabilities:
            # Calculate reduction amount
            reduction = probabilities["bike"] * no_bike_fraction

            # Reduce bike probability
            probabilities["bike"] = probabilities["bike"] * bike_availability_rate

            # Redistribute to non-bike modes proportionally
            non_bike_total = sum(probabilities[m] for m in non_bike_modes)

            for m in non_bike_modes:
                share = np.where(non_bike_total > 0,
                                probabilities[m] / non_bike_total,
                                1.0 / len(non_bike_modes))
                probabilities[m] = probabilities[m] + reduction * share

    mode_trips = apply_mode_choice(trip_matrix, probabilities, verbose=verbose)

    if verbose:
        print("  Converting to vehicle trips...")

    vehicle_trips = calculate_vehicle_trips(mode_trips, model)

    if verbose:
        print(f"  Total vehicle trips: {vehicle_trips.sum():,.0f}")

    return mode_trips, vehicle_trips


@dataclass
class ModeChoiceResult:
    """Container for mode choice results."""
    person_trips_by_mode: dict[str, np.ndarray]
    vehicle_trips: np.ndarray
    mode_shares: dict[str, float]
    model: ModeChoiceModel

    @classmethod
    def from_mode_trips(
        cls,
        mode_trips: dict[str, np.ndarray],
        vehicle_trips: np.ndarray,
        model: ModeChoiceModel
    ) -> "ModeChoiceResult":
        """Create result from mode trips."""
        total = sum(m.sum() for m in mode_trips.values())
        mode_shares = {
            mode: trips.sum() / total
            for mode, trips in mode_trips.items()
        }
        return cls(
            person_trips_by_mode=mode_trips,
            vehicle_trips=vehicle_trips,
            mode_shares=mode_shares,
            model=model
        )

    def summary(self) -> str:
        """Return summary as string."""
        lines = [
            "Mode Choice Results",
            "=" * 40,
            "Mode Shares:",
        ]
        for mode, share in self.mode_shares.items():
            trips = self.person_trips_by_mode[mode].sum()
            lines.append(f"  {mode}: {share*100:.1f}% ({trips:,.0f} trips)")

        lines.append(f"\nTotal vehicle trips: {self.vehicle_trips.sum():,.0f}")

        return "\n".join(lines)
