# Code Review Checklist: 4-Step Model Implementation

Use this checklist to verify fixes in `src/fourstep/` after the refactoring session.

---

## 1. Trip Generation (`trip_generation.py`)

### Vectorization
- [ ] `calculate_zone_trips()` uses vectorized pandas operations instead of `iterrows()`
- [ ] Rate lookup uses `pd.merge()` or vectorized mapping
- [ ] Performance: Should process 345k generators in < 5 seconds

### Trip Rates
- [ ] `TripRates` class can load from YAML file (`from_yaml()` class method)
- [ ] All categories from `brooklyn_settings.yaml` are supported:
  - [ ] "Home Improvement Store"
  - [ ] "Destination Retail"
  - [ ] "Academic University"
  - [ ] "Health Club"
  - [ ] "Museum"
  - [ ] "Passive Park Space"
  - [ ] "Active Park Space"
- [ ] Unknown categories trigger a warning (not silent fallback)

### Validation & Warnings
- [ ] Prints count of generators with missing `trip_gen_category`
- [ ] Prints count of generators with missing/zero `trip_gen_value`
- [ ] Prints breakdown of trips by category after calculation
- [ ] Warns if P/A ratio is > 2.0 or < 0.5 before balancing

---

## 2. Trip Distribution (`trip_distribution.py`)

### Gravity Model Equations
- [ ] Accessibility weighting formula is correct:
  ```python
  # Should sum across DESTINATIONS (axis=1), not origins
  accessibility = (attractions[np.newaxis, :] * F).sum(axis=1)
  ```
- [ ] Verify friction functions produce correct values at boundary conditions:
  - `exponential_friction(0, beta=0.1)` should equal `1.0`
  - `power_friction(1, gamma=2.0)` should equal `1.0`

### Intrazonal Impedance
- [ ] `half_nearest` method is vectorized (no Python loop)
- [ ] Correct formula: `0.5 * min(distance to other zones)`

### Network Skim Loading
- [ ] Uses `pivot()` or vectorized approach instead of `iterrows()`

### Calibration
- [ ] Calibration works for both `beta` (exponential/gamma) and `gamma` (power)
- [ ] Prints convergence status and final parameter value

---

## 3. Mode Choice (`mode_choice.py`)

### Model Structure
- [ ] Multinomial logit formula is numerically stable (subtract max before exp)
- [ ] Handles `-inf` utilities correctly (unavailable modes)
- [ ] Vehicle trip conversion accounts for occupancy correctly

### Future Enhancements (Optional)
- [ ] Consider: Income stratification using ACS data
- [ ] Consider: Auto ownership segmentation

---

## 4. Traffic Assignment (`traffic_assignment.py`)

### Relative Gap Calculation
- [ ] Uses proper formula: `Σ(t_a * (x_a - y_a)) / Σ(t_a * x_a)`
- [ ] Not the simplified: `Σ|x_a - y_a| / Σx_a`

### Volume-Delay Functions
- [ ] BPR formula: `t = t0 * (1 + α * (v/c)^β)` with defaults α=0.15, β=4.0
- [ ] Conical formula is correctly implemented

### Path Tracing
- [ ] Handles disconnected OD pairs gracefully (no infinite loop)
- [ ] Warns about OD pairs with no path

---

## 5. Pipeline (`pipeline.py`)

### OD DataFrame Conversion
- [ ] `to_od_dataframe()` uses vectorized numpy indexing, not nested loops
- [ ] Should use: `np.where(trip_matrix > 0)` approach

### Data Loading
- [ ] Handles both CSV and GeoJSON inputs
- [ ] Correctly parses WKT geometry strings
- [ ] Warns about CRS mismatches

### Zone Alignment
- [ ] Correctly handles zone ID ordering between trip generation and impedance matrix
- [ ] Warns if zones are dropped due to missing impedance

---

## 6. Validation Module (`validation.py`) - NEW

### Trip Length Frequency Distribution
- [ ] `compare_tlfd()` function exists
- [ ] Calculates coincidence ratio
- [ ] Calculates RMSE between modeled and observed

### ACS Comparison
- [ ] `validate_mode_shares()` compares to ACS commute mode data
- [ ] `validate_productions()` compares to ACS workers by residence
- [ ] Prints comparison table with % difference

### Summary Statistics
- [ ] `model_diagnostics()` function provides comprehensive check:
  - Total trips
  - Average trip length
  - Intrazonal percentage
  - Mode shares (if applicable)
  - Max V/C ratio (if assignment run)

---

## 7. Performance Benchmarks

Run with Brooklyn data (345k generators, ~10k zones):

| Operation | Target Time |
|-----------|-------------|
| Load generators | < 3 sec |
| Zone assignment | < 10 sec |
| Trip generation | < 5 sec |
| Impedance matrix | < 30 sec |
| Gravity model | < 10 sec |
| Mode choice | < 5 sec |
| **Total (no assignment)** | **< 2 min** |

---

## 8. Print Output Quality

### Step 1 Output Should Include:
```
STEP 1: TRIP GENERATION
========================================
  Assigning 345,266 generators to 9,856 zones...
  WARNING: 127 generators have missing trip_gen_category
  Assigned generators to 8,234 zones (1,622 zones have no generators)

  Calculating daily trips for purpose: all
  Trip Generation by Category:
    Residential (3+ floors):     2,450,000 trips (45.2%)
    Local Retail:                  890,000 trips (16.4%)
    Office (multi-tenant):         520,000 trips (9.6%)
    ...

  Total productions: 5,420,000
  Total attractions: 4,890,000
  P/A ratio: 1.108 (WARNING: >10% imbalance)

  After balancing (attraction): P=4,890,000, A=4,890,000
```

### Step 2 Output Should Include:
```
STEP 2: TRIP DISTRIBUTION
========================================
  Calculating centroid-to-centroid distances...
  Impedance matrix: 8,234 x 8,234
  Distance range: 0.12 - 18.45 miles
  Mean intrazonal: 0.31 miles

  Running gravity model:
    Friction function: gamma
    Parameters: {'alpha': -0.5, 'beta': 0.12}
    Constraint type: doubly
  Furness converged in 23 iterations

  Results:
    Total trips: 4,890,000
    Average trip length: 3.42 miles
    Intrazonal trips: 12.3%
```

---

## 9. Files to Check

- [ ] `src/fourstep/__init__.py` - exports updated
- [ ] `src/fourstep/trip_generation.py` - vectorized, YAML loading
- [ ] `src/fourstep/trip_distribution.py` - formulas fixed, vectorized
- [ ] `src/fourstep/mode_choice.py` - reviewed
- [ ] `src/fourstep/traffic_assignment.py` - gap formula fixed
- [ ] `src/fourstep/pipeline.py` - OD conversion vectorized
- [ ] `src/fourstep/validation.py` - NEW file with validation functions
- [ ] `run_4step_model.ipynb` - updated to use new features

---

## 10. Test Commands

```python
# Quick sanity check
from fourstep import run_4step_model
from fourstep.trip_generation import TripRates

# Test YAML loading
rates = TripRates.from_yaml('settings/brooklyn_settings.yaml')
print(rates.daily_rates.keys())

# Test full pipeline
result = run_4step_model(
    'data/trip_generators_brooklyn.csv',
    'data/zone_brooklyn_census_blocks.csv'
)

# Test validation
from fourstep.validation import model_diagnostics
model_diagnostics(result)
```
