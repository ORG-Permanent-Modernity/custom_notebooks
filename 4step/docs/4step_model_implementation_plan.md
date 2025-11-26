# 4-Step Model Implementation Plan

## Overview

This plan outlines the implementation of a classic 4-step transportation demand model using the `trip_generators_brooklyn.csv` file as input. The implementation will be modular, with configurable options for gravity model improvements.

---

## Input Data Available

### Primary Input: `trip_generators_brooklyn.csv` (345,266 records)
| Column | Description |
|--------|-------------|
| `generator_id` | Unique identifier |
| `source` | Origin type: `osm_poi`, `inferred_remaining`, `building_inferred` |
| `building_id` | Associated building |
| `land_use_type` | Specific use (restaurant, school, residential, etc.) |
| `land_use_category` | Broad category (amenity, shop, inferred) |
| `trip_gen_category` | NYC CEQR category for trip rates |
| `trip_gen_value` | Converted value (DU, students, 1000_sf, etc.) |
| `trip_gen_unit` | Unit of measurement |
| `sqft` | Square footage |
| `lat`, `lon` | Coordinates |

### Secondary Inputs
- `zone_brooklyn_census_blocks.csv` - 9,856 census block zones with polygon geometries
- ACS demographic data in `/input_data/acs/` - income, vehicle ownership, household size

---

## Step 1: Trip Generation

**Objective**: Calculate total trip productions (P) and attractions (A) for each zone.

### 1.1 Zone Assignment
```
Function: assign_generators_to_zones(generators_gdf, zones_gdf) -> DataFrame
```
- Spatial join trip generators to census block zones
- Handle edge cases (generators outside zone boundaries)
- Output: generators with `zone_id` column

### 1.2 Trip Rate Application
```
Function: calculate_zone_trips(
    generators_df,
    trip_rates_file,
    trip_purpose: str = 'HBW',  # HBW, HBO, NHB
    time_period: str = 'daily', # daily, AM_peak, PM_peak
    directional: bool = True    # separate production/attraction rates
) -> DataFrame[zone_id, production, attraction]
```

**Trip Rate Categories** (from NYC CEQR manual):
| Category | Unit | Typical Daily Rate |
|----------|------|-------------------|
| Residential (low-rise) | DU | 9.5 trips/DU |
| Residential (high-rise) | DU | 4.2 trips/DU |
| Office | 1000 sf | 11.0 trips/1000sf |
| Retail | 1000 sf | 42.0 trips/1000sf |
| Restaurant | 1000 sf | 127.0 trips/1000sf |
| School | student | 1.0 trips/student |
| Hotel | room | 8.2 trips/room |

**Production/Attraction Split** (by purpose):
- HBW: Residential produces, employment attracts
- HBO: Residential produces, retail/services attract
- NHB: All land uses both produce and attract

### 1.3 Balancing
```
Function: balance_trip_ends(
    zone_trips_df,
    method: str = 'attraction'  # 'attraction', 'production', 'average'
) -> DataFrame
```
- Ensure total productions = total attractions
- Options for balancing target

---

## Step 2: Trip Distribution (Gravity Model)

**Objective**: Distribute trips from production zones to attraction zones.

### 2.1 Distance/Impedance Matrix
```
Function: calculate_impedance_matrix(
    zones_gdf,
    network_skim: Optional[DataFrame] = None,
    impedance_type: str = 'distance'  # 'distance', 'time', 'generalized_cost'
) -> np.ndarray[n_zones, n_zones]
```
- If no network skim provided, use centroid-to-centroid Euclidean distance
- Option to load pre-computed network skims (travel time)

### 2.2 Standard Gravity Model
```
Function: gravity_model(
    productions: np.ndarray,
    attractions: np.ndarray,
    impedance: np.ndarray,
    friction_function: str = 'exponential',
    **friction_params
) -> np.ndarray[n_zones, n_zones]
```

**Standard Formula**:
```
T_ij = P_i * (A_j * f(c_ij)) / Σ_k(A_k * f(c_ik))
```

Where `f(c_ij)` is the friction function.

### 2.3 Friction Function Options

```python
friction_function: str = 'exponential'  # Options below
friction_params: dict  # Function-specific parameters
```

| Function | Formula | Parameters | Use Case |
|----------|---------|------------|----------|
| `exponential` | `exp(-β * c)` | `beta` | Short trips, urban |
| `power` | `c^(-γ)` | `gamma` | Longer trips |
| `gamma` | `c^a * exp(-β * c)` | `alpha`, `beta` | Combined (most flexible) |
| `tanner` | `c^a * exp(-b * c)` | `a`, `b` | Traditional 4-step |

### 2.4 Gravity Model Improvements (Optional Parameters)

```python
def gravity_model_enhanced(
    productions: np.ndarray,
    attractions: np.ndarray,
    impedance: np.ndarray,

    # Standard parameters
    friction_function: str = 'gamma',
    friction_params: dict = {'alpha': -0.5, 'beta': 0.1},

    # IMPROVEMENT 1: Doubly-constrained vs singly-constrained
    constraint_type: str = 'doubly',  # 'singly_production', 'singly_attraction', 'doubly'
    convergence_threshold: float = 0.001,
    max_iterations: int = 100,

    # IMPROVEMENT 2: K-factors (socioeconomic adjustment)
    k_factors: Optional[np.ndarray] = None,  # [n_zones, n_zones] adjustment matrix

    # IMPROVEMENT 3: Intrazonal trips
    intrazonal_method: str = 'half_nearest',  # 'half_nearest', 'terminal_time', 'area_based'

    # IMPROVEMENT 4: Trip purpose stratification
    purpose_weights: Optional[dict] = None,  # {'HBW': 0.3, 'HBO': 0.4, 'NHB': 0.3}

    # IMPROVEMENT 5: Destination choice accessibility
    accessibility_weight: float = 0.0,  # 0 = standard, >0 = accessibility-weighted

    # IMPROVEMENT 6: Distance decay calibration
    calibrate: bool = False,
    target_avg_trip_length: Optional[float] = None,
    observed_trip_length_distribution: Optional[np.ndarray] = None,

    # Output options
    verbose: bool = False
) -> Tuple[np.ndarray, dict]  # (trip_matrix, diagnostics)
```

---

## Step 3: Mode Choice

**Objective**: Split person trips by travel mode.

```
Function: mode_choice(
    trip_matrix: np.ndarray,
    zone_attributes: DataFrame,  # parking cost, transit access, etc.
    impedance_by_mode: dict,     # {'auto': skim, 'transit': skim, 'walk': skim}
    model_type: str = 'multinomial_logit',
    coefficients: dict = None    # calibrated or default
) -> dict[str, np.ndarray]       # trip matrices by mode
```

**Mode Categories**:
- Auto (driver)
- Auto (passenger)
- Transit
- Walk
- Bike

**Utility Function Components**:
- In-vehicle time
- Out-of-vehicle time (walk, wait, transfer)
- Cost (fare, parking, fuel)
- Mode-specific constants (ASC)

---

## Step 4: Traffic Assignment

**Objective**: Assign vehicle trips to network links.

```
Function: traffic_assignment(
    vehicle_trip_matrix: np.ndarray,
    network: Network,  # from path4gmns
    method: str = 'user_equilibrium',  # 'all_or_nothing', 'user_equilibrium', 'stochastic'
    vdf_type: str = 'bpr',  # volume-delay function
    convergence: float = 0.01,
    max_iterations: int = 100
) -> Tuple[Network, DataFrame]  # network with flows, link volumes
```

**Assignment Methods**:
- All-or-nothing (AON) - baseline
- User Equilibrium (UE) - iterative
- Stochastic User Equilibrium (SUE) - with perception error

---

## Implementation Modules

### New Files to Create in `/4step/src/`

```
src/
├── trip_generation.py      # Step 1
├── trip_distribution.py    # Step 2 (gravity model)
├── mode_choice.py          # Step 3
├── traffic_assignment.py   # Step 4
├── calibration.py          # Model calibration utilities
└── validation.py           # Model validation and reporting
```

### Configuration Files in `/4step/settings/`

```
settings/
├── trip_rates_nyc_ceqr.yaml      # Trip generation rates by land use
├── gravity_model_params.yaml      # Friction function parameters
├── mode_choice_coefficients.yaml  # Logit model coefficients
└── assignment_params.yaml         # Network assignment settings
```

---

## Detailed Implementation Order

### Phase 1: Trip Generation Module
1. Create `trip_generation.py`
2. Implement zone assignment (spatial join)
3. Load and apply NYC CEQR trip rates
4. Implement P/A balancing
5. Create unit tests

### Phase 2: Trip Distribution Module
1. Create `trip_distribution.py`
2. Implement impedance matrix calculation
3. Implement standard gravity model (singly-constrained)
4. Add friction function options (exponential, power, gamma)
5. Add doubly-constrained iteration
6. Add K-factor support
7. Add intrazonal trip handling
8. Add calibration routine (match target trip length)
9. Create unit tests

### Phase 3: Mode Choice Module
1. Create `mode_choice.py`
2. Implement multinomial logit framework
3. Load/create impedance by mode
4. Apply mode split to trip matrix
5. Create unit tests

### Phase 4: Traffic Assignment Module
1. Create `traffic_assignment.py`
2. Integrate with path4gmns library
3. Implement AON assignment
4. Implement UE assignment
5. Output link volumes and V/C ratios
6. Create unit tests

### Phase 5: Integration and Validation
1. Create main workflow notebook
2. End-to-end pipeline test
3. Validation against observed data (if available)
4. Documentation

---

## Gravity Model Improvement Details

### Improvement 1: Doubly-Constrained Model
Ensures both row sums (productions) and column sums (attractions) match targets.

```python
# Iterative balancing (Furness method)
while not converged:
    # Balance rows to match productions
    row_factors = P / T.sum(axis=1)
    T = T * row_factors[:, np.newaxis]

    # Balance columns to match attractions
    col_factors = A / T.sum(axis=0)
    T = T * col_factors[np.newaxis, :]

    # Check convergence
    converged = check_convergence(T, P, A, threshold)
```

### Improvement 2: K-Factors
Adjustment factors for zone pairs with known over/under-estimation.

```python
# Apply K-factors to friction matrix
adjusted_friction = base_friction * k_factors
```

Use cases:
- River/barrier crossings
- Socioeconomic clustering
- Observed vs. modeled discrepancies

### Improvement 3: Intrazonal Trip Handling
Options for computing intrazonal impedance:

```python
if intrazonal_method == 'half_nearest':
    # Half the distance to nearest zone centroid
    intrazonal_impedance[i] = 0.5 * min(impedance[i, j] for j != i)
elif intrazonal_method == 'area_based':
    # Based on zone area
    intrazonal_impedance[i] = 0.5 * sqrt(zone_area[i] / pi)
elif intrazonal_method == 'terminal_time':
    # Fixed terminal time
    intrazonal_impedance[i] = terminal_time
```

### Improvement 4: Trip Purpose Stratification
Run separate gravity models per purpose, then combine:

```python
total_trips = np.zeros((n_zones, n_zones))
for purpose, weight in purpose_weights.items():
    purpose_trips = gravity_model(P[purpose], A[purpose], impedance,
                                   friction_params=params[purpose])
    total_trips += weight * purpose_trips
```

### Improvement 5: Accessibility Weighting
Modify attractions based on zone accessibility:

```python
# Hansen accessibility measure
accessibility = np.sum(attractions[:, np.newaxis] * friction, axis=0)
weighted_attractions = attractions * (accessibility ** accessibility_weight)
```

### Improvement 6: Calibration to Observed Data
Adjust friction parameters to match target trip length distribution:

```python
def calibrate_gravity(P, A, impedance, target_avg_length, method='bisection'):
    """
    Iteratively adjust beta until model average trip length matches target.
    """
    while abs(model_avg_length - target_avg_length) > tolerance:
        # Adjust beta
        beta = beta * (model_avg_length / target_avg_length) ** alpha
        # Recalculate model
        trips = gravity_model(P, A, impedance, beta=beta)
        model_avg_length = calc_avg_trip_length(trips, impedance)
    return beta, trips
```

---

## Function Signature Summary

```python
# Main entry point
def run_4step_model(
    trip_generators_file: str,
    zones_file: str,
    network_file: Optional[str] = None,

    # Trip generation options
    trip_rates_file: str = 'settings/trip_rates_nyc_ceqr.yaml',
    trip_purpose: str = 'all',  # 'HBW', 'HBO', 'NHB', 'all'
    balance_method: str = 'attraction',

    # Trip distribution options
    friction_function: str = 'gamma',
    friction_params: dict = None,
    constraint_type: str = 'doubly',
    k_factors: Optional[np.ndarray] = None,
    intrazonal_method: str = 'half_nearest',
    calibrate_to_length: Optional[float] = None,

    # Mode choice options
    run_mode_choice: bool = True,
    mode_choice_model: str = 'multinomial_logit',

    # Assignment options
    run_assignment: bool = True,
    assignment_method: str = 'user_equilibrium',

    # Output options
    output_dir: str = 'output',
    verbose: bool = True
) -> dict:
    """
    Run complete 4-step model pipeline.

    Returns:
        dict with keys: 'productions', 'attractions', 'trip_matrix',
                        'mode_splits', 'link_volumes', 'diagnostics'
    """
```

---

## Validation Metrics

1. **Trip Generation**: Compare total productions/attractions to census journey-to-work data
2. **Trip Distribution**:
   - Average trip length vs. observed
   - Trip length frequency distribution (TLFD)
   - Coincidence ratio
3. **Mode Choice**: Mode shares vs. ACS commute mode data
4. **Assignment**: V/C ratios, screenline counts vs. observed

---

## Dependencies

```
numpy
pandas
geopandas
scipy
shapely
matplotlib (visualization)
path4gmns (assignment)
```
