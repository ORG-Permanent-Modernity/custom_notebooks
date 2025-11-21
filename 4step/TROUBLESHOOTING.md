# Troubleshooting Guide - Brooklyn Multi-Modal Demand Modeling

This guide addresses common issues you may encounter when running the [multimodal.ipynb](multimodal.ipynb) notebook.

---

## Issue 1: Trip Rate File Not Found

**Error Message:**
```
FileNotFoundError: settings/brooklyn_poi_trip_rate_multipurpose.csv not found
```

**Solution:**
Run the trip rate generation script:
```bash
cd /Users/dpbirge/GITHUB/custom_notebooks/4step
python utils/create_multipurpose_trip_rates.py
```

This will create `settings/brooklyn_poi_trip_rate_multipurpose.csv` with rates for all 3 trip purposes.

---

## Issue 2: grid2demand Not Available

**Error Message:**
```
ModuleNotFoundError: No module named 'grid2demand'
```

**Solution:**
Activate the correct conda environment that has grid2demand installed:
```bash
conda activate 4step  # or whatever your environment is named
```

Or install grid2demand:
```bash
pip install grid2demand
```

---

## Issue 3: osm2gmns Import Error

**Error Message:**
```
ModuleNotFoundError: No module named 'osm2gmns'
```

**Solution:**
Install osm2gmns:
```bash
pip install osm2gmns
```

---

## Issue 4: Demand Matrix Files Not Created

**Symptom:**
- Cell 3 completes but no `demand_{mode}_purpose{X}.csv` files in `data/` folder
- Warning message: "⚠ Warning: Could not find output file"

**Possible Causes & Solutions:**

### Cause 1: grid2demand saved to different filename
**Check:** Does `data/demand_od_matrix.csv` exist after running?
**Solution:** The notebook now handles this automatically by looking for both `demand.csv` and `demand_od_matrix.csv`.

### Cause 2: File permissions issue
**Check:** Do you have write permissions in the `data/` directory?
**Solution:**
```bash
chmod u+w data/
```

### Cause 3: Disk space
**Check:** Sufficient disk space for ~9 CSV files (~500KB each)?
**Solution:** Free up disk space or change `output_dir` to a different location.

---

## Issue 5: Visualization Shows No Data

**Symptom:**
- Charts appear but show "data unavailable" or empty plots
- Message: "⚠ No demand matrices available for visualization"

**Solution:**
1. Verify Cell 3 completed successfully
2. Check that `all_demand_matrices` dictionary is populated:
   ```python
   print(f"Matrices available: {list(all_demand_matrices.keys())}")
   print(f"Total matrices: {len(all_demand_matrices)}")
   ```
3. If empty, re-run Cell 3

---

## Issue 6: High Memory Usage

**Symptom:**
- Kernel crashes or system becomes unresponsive during Cell 3
- Out of memory errors

**Solutions:**

### Solution 1: Process fewer modes at once
Edit Cell 3 to process one mode at a time:
```python
# Change this:
modes = ['auto', 'walk', 'bike']

# To this (run separately):
modes = ['auto']  # First run
# Then change to: modes = ['walk']  # Second run
# Then change to: modes = ['bike']  # Third run
```

### Solution 2: Reduce zone resolution
Edit Cell 3 to use larger zones:
```python
# Change this:
net.net2grid(cell_width=1250, cell_height=1250, unit="meter")

# To this (fewer zones):
net.net2grid(cell_width=2000, cell_height=2000, unit="meter")
```

### Solution 3: Process subset of zones
Edit Cell 3 to sample zones:
```python
# Change this:
net.calc_zone_od_distance(pct=1.0)

# To this (50% sample):
net.calc_zone_od_distance(pct=0.5)
```

---

## Issue 7: Trip Rates Look Unrealistic

**Symptom:**
- Total trips are extremely high or low
- Mode shares don't match expectations
- Trip lengths seem incorrect

**Diagnostic Steps:**

1. **Check trip rate file format:**
   ```bash
   head -5 settings/brooklyn_poi_trip_rate_multipurpose.csv
   ```
   Should show columns: `production_rate1`, `attraction_rate1`, `production_rate2`, `attraction_rate2`, `production_rate3`, `attraction_rate3`

2. **Verify POI counts:**
   ```bash
   wc -l data/poi.csv
   ```
   Brooklyn should have ~346,000 POIs

3. **Check zone generation:**
   Look for message in Cell 3 output:
   ```
   Successfully loaded zone.csv: XXX Zones loaded
   ```
   Should be ~170 zones for 1250m grid, ~420 zones for 800m grid

4. **Inspect friction parameters:**
   Check if alpha/beta/gamma values in Cell 3 match expected ranges:
   - Alpha: 28,000 - 75,000
   - Beta: -0.80 to -2.50 (negative!)
   - Gamma: -0.10 to -0.18 (negative!)

**Solutions:**

- If trip volumes too high: Reduce alpha values or make beta/gamma more negative
- If trip volumes too low: Increase alpha values or make beta/gamma less negative
- If mode shares incorrect: Adjust mode-specific friction factors
- For calibration, compare to CMS observed mode split:
  - Walk: 36%
  - Auto: 28%
  - Transit: 22%
  - Bike: 2%

---

## Issue 8: Numeric Overflow Error

**Error Message:**
```
OverflowError: (34, 'Numerical result out of range')
```

**Location:** During `run_gravity_model()` in Cell 3

**Cause:**
The friction factor calculation `F = α × d^β × exp(γ × d)` can overflow when:
- Distances are very large (>15 km)
- Alpha values are too high (>20,000)
- Beta/Gamma magnitudes are too extreme

**Solution:**
The notebook now uses calibrated parameters that prevent overflow:
- Auto: α=5000, β=-0.50, γ=-0.08
- Walk: α=15000, β=-2.00, γ=-0.25
- Bike: α=8000, β=-1.20, γ=-0.15

These maintain relative mode sensitivities while avoiding numeric issues.

**If you still get overflow:**
1. Reduce alpha values further (try dividing by 2)
2. Make beta less negative (e.g., -0.50 → -0.30)
3. Make gamma less negative (e.g., -0.08 → -0.05)
4. Reduce zone size to decrease maximum distances

**Advanced**: Add try-except blocks (already in notebook) to catch and skip problematic combinations.

---

## Issue 9: CMS Data Files Missing

**Error Message:**
```
FileNotFoundError: input_data/cms/Citywide_Mobility_Survey_-_Trip_2019.csv
```

**Context:**
The CMS data is only used by the trip rate generation script (`utils/create_multipurpose_trip_rates.py`). The multimodal notebook itself doesn't require it since the trip rates are pre-generated.

**Solution:**
If you need to regenerate trip rates with CMS calibration, download the 2019 trip file from NYC Open Data. Otherwise, use the existing trip rate file which was already generated with CMS data.

---

## Issue 9: Network Distance Calculator Not Working

**Symptom:**
- Messages about path4gmns not available
- Using Haversine fallback

**Context:**
This is **expected behavior** if path4gmns is not installed. The notebook will work fine with Haversine (straight-line) distances.

**To Enable Network Distances (Optional):**

1. **Install path4gmns:**
   ```bash
   pip install path4gmns
   ```

2. **Or install from source:**
   ```bash
   cd 4step/src/path4gmns
   pip install -e .
   ```

3. **Verify installation:**
   ```python
   import path4gmns as pg
   print(pg.__version__)
   ```

4. **Use network distances:**
   Add this code before the mode loop in Cell 3:
   ```python
   from utils.network_distance_calculator import calculate_network_od_matrix_by_mode

   # Calculate network distances for each mode
   for mode in modes:
       od_dist = calculate_network_od_matrix_by_mode(
           zone_dict=net.zone_dict,
           network_dir=output_dir,
           mode=mode,
           output_file=f'{output_dir}/zone_od_dist_matrix_{mode}.csv'
       )
   ```

---

## Issue 10: Slow Performance

**Symptom:**
- Cell 3 takes more than 15 minutes to run
- Progress seems stalled

**Expected Runtime:**
- Full run (3 modes × 3 purposes): 5-10 minutes
- Per mode-purpose combination: ~30-60 seconds
- Distance calculation: ~10 seconds (parallelized)

**Solutions:**

### If stuck on distance calculation:
Check CPU usage - should be near 100% on multiple cores. If not:
```python
# Edit Cell 3 to reduce parallelization
net.calc_zone_od_distance(pct=1.0)  # Uses all CPU cores by default
```

### If stuck on gravity model:
The gravity model itself is fast (<1 second). If slow, likely issue with I/O or POI processing.

### Monitor progress:
Add this to mode loop in Cell 3 to see detailed progress:
```python
import time
start = time.time()
# ... (existing code)
elapsed = time.time() - start
print(f"    Time: {elapsed:.1f}s")
```

---

## Issue 11: Matplotlib/Visualization Errors

**Error Messages:**
```
ImportError: No module named 'seaborn'
ValueError: No objects to concatenate
```

**Solutions:**

### Missing seaborn:
```bash
pip install seaborn
```

### Empty pivot tables:
This happens if no demand data available. Check `all_demand_matrices`:
```python
print(len(all_demand_matrices))  # Should be 9 (3 modes × 3 purposes)
```

If 0, re-run Cell 3.

### Plot formatting issues:
The notebook uses modern matplotlib. If using old version:
```bash
pip install --upgrade matplotlib
```

---

## Issue 12: Git/Version Control Issues

**Symptom:**
- Large CSV files (node.csv, poi.csv, link.csv) causing git issues
- Repository too large

**Solution:**
Add data files to `.gitignore`:
```bash
echo "4step/data/*.csv" >> .gitignore
echo "4step/data/*.osm" >> .gitignore
git add .gitignore
git commit -m "Ignore large data files"
```

Keep only the essential files in git:
- Notebooks (*.ipynb)
- Trip rate files (settings/*.csv)
- Utility scripts (utils/*.py)
- Documentation (*.md)

---

## Getting Help

If you encounter an issue not covered here:

1. **Check the Implementation Summary:** [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

2. **Review inline comments:** The notebook cells have detailed comments explaining each step

3. **Check grid2demand documentation:** https://github.com/asu-trans-ai-lab/grid2demand

4. **Verify your environment:**
   ```bash
   conda list | grep -E "grid2demand|osm2gmns|pandas|geopandas"
   ```

5. **Check file structure:**
   ```bash
   tree -L 2 4step/
   ```
   Should show:
   ```
   4step/
   ├── data/
   │   ├── node.csv
   │   ├── link.csv
   │   ├── poi.csv
   │   ├── zone.csv
   │   └── demand_*.csv (9 files after running)
   ├── settings/
   │   └── brooklyn_poi_trip_rate_multipurpose.csv
   ├── utils/
   │   ├── create_multipurpose_trip_rates.py
   │   └── network_distance_calculator.py
   └── multimodal.ipynb
   ```

---

## Debug Mode

To enable verbose debugging, add this to the top of Cell 3:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Also set grid2demand to verbose
net = gd.GRID2DEMAND(
    input_dir=output_dir,
    mode_type=mode,
    verbose=True  # Enable verbose output
)
```

This will show detailed progress for each grid2demand operation.

---

**Last Updated:** 2025-11-20
