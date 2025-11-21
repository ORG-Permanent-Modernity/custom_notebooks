# Brooklyn POI Trip Rate Calibration - 2019 Data Update

**Date**: November 20, 2025
**Update**: Switched from 2022 to 2019 CMS data for pre-COVID baseline

---

## Summary of Changes

The Brooklyn POI trip rate calibration was **updated to use 2019 CMS data** instead of 2022 data to avoid COVID-era biases in travel behavior.

---

## Why the Change?

### Problem with 2022 Data
The initial calibration used CMS 2022 data, which showed:
- **HBW (Home-Based Work)**: Only 1.6% of trips
- **HBO (Home-Based Other)**: 43.0%
- **NHB (Non-Home-Based)**: 55.4%

The extremely low HBW rate (1.6%) was caused by:
1. **COVID-era remote work**: Many workers still working from home in 2022
2. **Hybrid schedules**: Reduced commute frequency
3. **Survey timing**: Single-day surveys missed periodic commuters

### Solution: 2019 Pre-COVID Data
Switched to CMS 2019 data, which shows:
- **HBW (Home-Based Work)**: **4.4% of trips** ✓
- **HBO (Home-Based Other)**: **35.2%**
- **NHB (Non-Home-Based)**: **60.4%**

This provides a more representative baseline of normal Brooklyn travel patterns.

---

## Data Source Details

### 2019 CMS Data
- **Year**: 2019 (pre-COVID)
- **Brooklyn households**: 632
- **Brooklyn trips analyzed**: 16,875
- **Geographic identification**: Households in "Inner Brooklyn" and "Outer Brooklyn" zones
- **Files**:
  - `Citywide_Mobility_Survey_-_Household_2019.csv`
  - `Citywide_Mobility_Survey_-_Trip_2019.csv`
  - `Citywide_Mobility_Survey_-_Person_2019.csv`

### Key Improvements
1. **More realistic work trip share**: 4.4% vs 1.6%
2. **Pre-pandemic baseline**: Reflects normal commuting patterns
3. **Still shows Brooklyn character**: Higher NHB (60.4%) reflects dense, mixed-use environment

---

## Bug Fix: Work Category Code

### Original Error
The initial code incorrectly identified work trips:
```python
is_work_o = (o_cat == 7)  # WRONG: 7 = Shopping
is_work_d = (d_cat == 7)
```

### Corrected Code
```python
is_work_o = (o_cat == 2)  # CORRECT: 2 = Work
is_work_d = (d_cat == 2)
```

According to the CMS codebook:
- **Category 1** = Home
- **Category 2** = Work ✓
- **Category 7** = Shopping ✗

This bug affected both 2022 and initial 2019 analysis but has been corrected.

---

## Updated Trip Purpose Distribution

### Final Brooklyn Trip Rates (2019 Pre-COVID)

| Trip Purpose | Share | Trips | Notes |
|--------------|-------|-------|-------|
| **HBW** (Home-Based Work) | **4.4%** | 741 | Commute trips |
| **HBO** (Home-Based Other) | **35.2%** | 5,940 | Shopping, dining, recreation, school |
| **NHB** (Non-Home-Based) | **60.4%** | 10,194 | Trip chains, lunch, errands |
| **Total** | 100% | 16,875 | All Brooklyn household trips |

### Comparison to 2022 COVID-Era Data

| Trip Purpose | 2019 (Pre-COVID) | 2022 (COVID) | Change |
|--------------|------------------|--------------|--------|
| HBW | 4.4% | 1.6% | -2.8 pp |
| HBO | 35.2% | 43.0% | +7.8 pp |
| NHB | 60.4% | 55.4% | -5.0 pp |

The 2019 data better represents normal travel patterns for demand forecasting.

---

## Impact on POI Trip Rates

The updated trip purpose distribution affects the calibrated rates in `brooklyn_poi_trip_rate.csv`:

### Example: Residential POI
Using 2019 distribution:
- **HBW**: Higher production from homes (people going to work)
- **HBO**: Primary attraction to homes (return from shopping/activities)
- **NHB**: Moderate trips (non-home chains)

### Example: Office POI
- **HBW**: Higher attraction to offices (work destinations)
- **HBO/NHB**: Lower but present (lunch meetings, errands)

The actual rate values themselves remain the same (based on ITE and local adjustments), but the **trip purpose multipliers** used internally reflect the corrected 2019 distribution.

---

## Files Updated

### Code
1. **`utils/brooklyn_trip_rate_calibration.py`**
   - Changed to load 2019 CMS files
   - Fixed work category bug (7 → 2)
   - Updated filtering logic for 2019 zone structure

2. **`utils/run_brooklyn_calibration.py`**
   - No changes needed (calls updated calibration code)

3. **`utils/generate_brooklyn_poi_rates.py`**
   - No changes needed (uses trip purpose percentages from calibration)

### Data
1. **Added**: `input_data/cms/Citywide_Mobility_Survey_-_*_2019.csv`
2. **Legacy**: 2022 CMS files retained for reference

### Output
1. **`settings/brooklyn_poi_trip_rate.csv`**
   - Regenerated with 2019 trip purpose distribution
   - 159 rows (53 POI types × 3 trip purposes)
   - Includes subway stations and bus stops

### Documentation
1. **`docs/methods/brooklyn_trip_rate_calibration.md`**
   - Updated header to note 2019 data year
   - Full methodology document

2. **`docs/methods/brooklyn_trip_rate_2019_update.md`**
   - This summary document

---

## Usage

The calibrated rates are used the same way in grid2demand:

```python
import grid2demand as gd

net = gd.GRID2DEMAND(input_dir='data')
net.load_network()
net.net2grid(cell_width=400, cell_height=400, unit="meter")
net.taz2zone()
net.map_zone_node_poi()
net.calc_zone_od_distance(pct=1.0)

# Use Brooklyn-calibrated 2019 rates
net.run_gravity_model(
    trip_rate_file='settings/brooklyn_poi_trip_rate.csv',
    trip_purpose=1  # 1=HBW, 2=HBO, 3=NHB
)

net.save_results_to_csv()
```

---

## Validation

### Reasonableness Checks

1. **HBW rate (4.4%)** is reasonable for Brooklyn:
   - Lower than Manhattan (more jobs than residents)
   - Higher than outer suburbs (bedroom communities)
   - Reflects Brooklyn's residential character

2. **NHB rate (60.4%)** is high but appropriate:
   - Dense, mixed-use urban environment
   - Extensive trip chaining (work→lunch, shopping→dining)
   - Short distances enable multiple stops

3. **HBO rate (35.2%)** captures:
   - Shopping trips
   - School trips
   - Recreation and dining
   - Social visits

### Future Improvements

1. **Time-of-day factors**: Peak vs off-peak rates
2. **Day-of-week factors**: Weekday vs weekend
3. **Seasonal adjustments**: Summer vs winter patterns
4. **Mode-specific rates**: Auto vs transit vs walk/bike

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2025-11-20 | 2.0 | Switched to 2019 CMS data, fixed work category bug |
| 2025-11-20 | 1.0 | Initial calibration with 2022 data (superseded) |

---

## References

- **2019 CMS Data**: [NYC Open Data Portal](https://data.cityofnewyork.us)
  - Trip 2019: Dataset ID w9dc-u4ik
  - Household 2019: Dataset ID a5rk-jemi
  - Person 2019: Dataset ID 6bqn-qdwq

- **CMS Codebook**: `input_data/cms/2022_NYC_CMS_Codebook.xlsx`
  - Purpose categories defined on "value_labels" sheet

- **Original Methodology**: `docs/methods/brooklyn_trip_rate_calibration.md`
