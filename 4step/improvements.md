# Proposed Improvements for Trip Generation and Demand Modeling

## 1. Objective

The goal of these changes is to significantly improve the accuracy and reliability of the transportation demand model. This will be achieved by building a high-quality **base demand matrix** using local, NYC-specific data *before* proceeding to the calibration phase with the Brooklyn survey data.

---

## 2. The Core Problem with the Current Approach

The current notebook follows a logical but suboptimal path:
1.  **Generate Base Demand:** Creates an initial OD matrix using what are likely generic trip generation tables.
2.  **Calibrate Demand:** Uses iterative fitting to adjust this generic matrix to match observed data from the Brooklyn survey.

The weakness here is that the initial demand is not well-grounded in local reality. Calibrating a poor initial model is difficult and can lead to:
*   **Poor Convergence:** The model may struggle to find a stable solution.
*   **Unrealistic Results:** The fitting process might force a match by creating unrealistic travel patterns in areas not covered by the survey.
*   **Weak Foundation:** The final model loses its connection to the underlying socioeconomic data.

---

## 3. The Solution: A Rebuilt Plan of Action

We will insert a new **Data Preparation Phase** into the notebook. This phase will process the raw NYC trip data into a format suitable for `grid2demand`, ensuring our base demand is as accurate as possible from the very beginning.

### Phase 1: Create a New Data Preparation Section (New)

This is the primary change. We will add a new section to the notebook to process the local trip generation data.

#### **Step 1.1: Load and Inspect Raw NYC Trip Data**

First, use `pandas` to load your raw data and understand its structure. This is a critical first step before any transformation.

**Action:** Add a new cell to load the data from `/input_data/trip_generation/`.

```python
import pandas as pd
import os

# Define file paths
raw_data_path = 'input_data/trip_generation/nyc_trip_rates.csv' # Adjust filename if needed
output_dir = 'input_data'
formatted_data_path = os.path.join(output_dir, 'poi_trip_rate_nyc.csv')

# Load the raw data
try:
    df_raw = pd.read_csv(raw_data_path)
    print("Successfully loaded raw data. Info and first 5 rows:")
    df_raw.info()
    print(df_raw.head())
except FileNotFoundError:
    print(f"ERROR: The file was not found at '{raw_data_path}'. Please check the path.")

# --- Data Transformation ---
# !!! IMPORTANT: You MUST adjust the keys in this dictionary to match your file's column names.
column_mapping = {
    'use_category': 'poi_type',      # The column in your file for land use (e.g., 'residential', 'commercial')
    'purpose': 'trip_purpose',       # The column for trip purpose (e.g., 'HBW', 'HBO')
    'prod_rate': 'production_rate',  # The column for the production rate
    'attr_rate': 'attraction_rate'   # The column for the attraction rate
}

df_formatted = df_raw.rename(columns=column_mapping)

# Add other columns required by grid2demand if they don't exist
if 'time_period' not in df_formatted.columns:
    df_formatted['time_period'] = 'all_day' # Default to 'all_day'

if 'unit' not in df_formatted.columns:
    df_formatted['unit'] = 'default' # A placeholder for the unit of the rate

# Ensure the final DataFrame has the correct columns in a clean order
required_columns = ['poi_type', 'trip_purpose', 'time_period', 'production_rate', 'attraction_rate', 'unit']
df_formatted = df_formatted[required_columns]

print("\nData transformed into grid2demand format. First 5 rows:")
print(df_formatted.head())


# Create the output directory if it doesn't exist
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Save the formatted DataFrame to a new CSV file
df_formatted.to_csv(formatted_data_path, index=False)

print(f"\n✅ Formatted trip generation table saved to: {formatted_data_path}")
