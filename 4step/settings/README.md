# 4-Step Model Settings

This directory contains configuration files and data tables that drive the land use processing and trip generation calculations.

### `city_config.yaml`

This file contains city-specific parameters for building and POI processing. The workflow is designed to be adaptable to different urban environments, and this file allows for tuning key variables without changing the processing scripts.

- **`default_city`**: The city to use if none is specified.
- **`cities`**: A collection of city-specific configurations.
    - **`building`**: Parameters related to physical building characteristics (e.g., `default_floors`, `avg_floor_height_m`).
    - **`residential`**: Parameters for converting residential building area into dwelling units (e.g., `sqft_per_du`).
    - **`commercial`**: Parameters for converting commercial building area into relevant units (e.g., `sqft_per_hotel_room`).

### `heuristics.yaml`

This file defines the core heuristics for two key processes: allocating building square footage among POIs and inferring land use for buildings without any matched POIs.

- **`poi_heuristics`**: A mapping where each POI type is assigned a rule for how it occupies a building.
    - `floors_occupied`: Can be `'full'`, `'ground'`, or `'multi'`.
    - `remaining_use`: The inferred use of the rest of the building (e.g., `'residential'`, `'office'`).
- **`building_type_map`**: A mapping from OSM `building` tags (e.g., `apartments`, `retail`) to the model's internal land use categories. This is used for buildings that have no POIs inside them.

### `nyc_trip_gen_rates.csv`

This file contains the core trip generation rates for New York City. The rates determine the number of trips produced by or attracted to a given land use.

**IMPORTANT METADATA:**

-   **Source**: The origin of these rates is not specified in the original project. They are likely derived from a combination of the Institute of Transportation Engineers (ITE) Trip Generation Manual and local data sources like the NYC Citywide Mobility Survey (CMS). **Verification of these rates is critical before use.**
-   **Rate Columns**: The columns `production_rate1`, `attraction_rate1`, through `4` likely correspond to different trip purposes or time periods, a standard practice in travel demand modeling. A common 4-purpose model is:
    1.  **Home-Based Work (HBW)**: Trips between home and a primary workplace.
    2.  **Home-Based Other (HBO)**: Trips between home and any other location (e.g., shopping, recreation).
    3.  **Non-Home-Based (NHB)**: Trips that do not begin or end at home (e.g., from an office to a restaurant).
    4.  **Truck & Taxi**: Commercial vehicle trips.

    **This interpretation is an assumption and must be confirmed before applying these rates.**

-   **`unit_of_measure`**: Specifies the unit that the rate applies to (e.g., `per 1000 sf`, `per DU`). The land use processing scripts are designed to convert square footage into these specific units.
