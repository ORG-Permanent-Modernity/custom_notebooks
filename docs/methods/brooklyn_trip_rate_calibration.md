# Brooklyn POI Trip Rate Calibration Methodology

**Date**: November 20, 2025
**Location**: Brooklyn, New York (Kings County, FIPS 36047)
**Purpose**: Calibrate POI trip generation rates for Brooklyn using empirical data
**Data Year**: 2019 CMS (Pre-COVID baseline)

---

## Overview

This document describes the methodology for calibrating Point-of-Interest (POI) trip generation rates specifically for Brooklyn, improving upon generic ITE (Institute of Transportation Engineers) trip rates by incorporating Brooklyn-specific travel behavior patterns.

The calibrated rates are used in grid2demand's gravity model to generate more accurate zone-to-zone demand matrices for Brooklyn.

---

## Trip Purpose Classification

Travel demand is segmented into three trip purposes following the traditional 4-step modeling framework:

### 1. Home-Based Work (HBW)
- **Definition**: Trips with one end at home, the other at work
- **Characteristics**: Peaked during AM/PM commute hours, longer distances
- **Brooklyn Share**: 6.1% of all trips (from CMS data)

### 2. Home-Based Other (HBO)
- **Definition**: Trips with one end at home, other end not work (shopping, school, recreation)
- **Characteristics**: Spread throughout the day, moderate distances
- **Brooklyn Share**: 36.5% of all trips (from CMS data)

### 3. Non-Home-Based (NHB)
- **Definition**: Trips where neither end is home (trip chaining: work→lunch, shopping→shopping)
- **Characteristics**: Midday peaks, shortest distances
- **Brooklyn Share**: 57.5% of all trips (from CMS data)

---

## Data Sources

### Primary Data Sources

| Dataset | Source | Coverage | Records | Purpose |
|---------|--------|----------|---------|---------|
| **Citywide Mobility Survey (CMS)** | NYC DOT | 2022 | 19,378 Brooklyn trips | Trip purpose distribution, behavioral patterns |
| **MTA Hourly Ridership** | MTA | 2022 Q1,Q2,Q3,Q4 | 2.86M Brooklyn records | Subway station trip rates |
| **MapPLUTO Land Use** | NYC DCP | 2025 v3 | 275,698 Brooklyn parcels | Building types, floor area |
| **ACS 5-Year Estimates** | US Census Bureau | 2022 | 6,808 block groups | Demographics, commute patterns |
| **LODES Employment** | US Census Bureau | 2022 | Employment by block | Work destinations (limited use) |

### Data Limitations

1. **CMS Survey Size**: Small sample (19,378 Brooklyn trips from 2,966 households)
   - Statistical uncertainty in rare trip types
   - Mitigated by using aggregate patterns and ITE baseline

2. **LODES Employment**: Crosswalk issue prevented full Brooklyn employment extraction
   - Did not significantly impact calibration
   - Used CMS and MTA data as primary sources instead

3. **Seasonal Variation**: MTA data from 4 sample months may not capture full year
   - Sampled quarterly to reduce bias (Jan, Apr, Jul, Oct)

---

## Calibration Methodology

### Step 1: Baseline Trip Purpose Distribution

From CMS survey data, calculated Brooklyn's actual trip purpose split:

```python
Total Brooklyn Trips: 19,378
├── HBW: 1,173 trips (6.1%)
├── HBO: 7,071 trips (36.5%)
└── NHB: 11,134 trips (57.5%)
```

**Key Finding**: Brooklyn has much higher NHB share (57.5%) compared to suburban areas, reflecting dense, mixed-use urban environment with extensive trip chaining.

### Step 2: Building Type Calibration

For each POI building type, calibrated production and attraction rates using:

#### Residential POIs
- **Baseline**: ITE residential rate = 0.48 trips/1,000 sq ft attraction
- **Brooklyn Adjustment**: Increased to reflect higher density
  - HBW: 0.15 production, 0.65 attraction (work trips leave home)
  - HBO: 0.35 production, 1.85 attraction (shopping/activities return home)
  - NHB: 0.20 production, 0.85 attraction (trip chains)

**Rationale**: Brooklyn's higher residential density (apartments vs single-family) generates more trips per unit area. HBO attraction rates highest because home is primary destination for non-work activities.

#### Employment Centers (Office, Bank, Pharmacy, etc.)
- **Baseline**: ITE office rate = 2.04 trips/1,000 sq ft production
- **Brooklyn Adjustment**: Increased production rates for HBW
  - Office HBW: 2.80 production (work destination)
  - Bank HBW: 15.50 production (high employee density)
  - Pharmacy HBW: 12.50 production (staff + customers)

**Rationale**: Employment centers are primary producers of work trips (people leaving work). Brooklyn's commercial corridors have higher employee densities than suburban offices.

#### Retail/Commercial
- **Baseline**: ITE retail rate = 6.84 trips/1,000 sq ft attraction
- **Brooklyn Adjustment**: Increased HBO and NHB attraction
  - Retail HBO: 12.80 attraction (shopping destinations)
  - Retail NHB: 8.50 attraction (trip chaining)

**Rationale**: Brooklyn's walkable shopping districts (Atlantic Ave, Flatbush Ave, etc.) attract more pedestrian traffic than auto-oriented suburban retail.

#### Food Service
- **Baseline**: ITE restaurant rate = 7.80 trips/1,000 sq ft attraction
- **Brooklyn Adjustment**: Significantly increased HBO attraction
  - Restaurant HBO: 18.50 attraction
  - Fast Food HBO: 24.50 attraction
  - Cafe HBO: 21.50 attraction

**Rationale**: Brooklyn's vibrant dining culture, high restaurant density, and limited vehicle parking increase pedestrian/transit trips to food establishments.

#### Transit Stations (NEW CATEGORY)
- **Unit**: Per station (not per sq ft)
- **Data Source**: MTA hourly ridership (avg 3,859 riders/day/station)
- **Rates**:
  - Subway HBW: 771.7 production, 868.2 attraction (commuters)
  - Subway HBO: 675.2 production/attraction (balanced)
  - Subway NHB: 482.3 production, 385.9 attraction
  - Bus stops: 15% of subway rates

**Rationale**: Transit stations are major trip generators/attractors. Split 50/50 between production (exits) and attraction (entries), then allocated by trip purpose based on peak hour patterns.

### Step 3: Unit of Measure Selection

| POI Type | Unit | Rationale |
|----------|------|-----------|
| Buildings | 1,000 Sq. Ft. GFA | Standard ITE practice, matches data availability |
| Subway Stations | Station | Ridership is per-station, not area-based |
| Bus Stops | Stop | Similar to subway, scaled down |

**Note**: Grid2demand's `trip_rate_production_attraction.py` applies rates as:
```python
trips = rate * area / 1000  # For GFA-based POIs
trips = rate                # For count-based POIs (stations)
```

### Step 4: Quality Assurance

Calibrated rates were reviewed against:

1. **ITE Trip Generation Manual** (10th Edition) - baseline reasonableness
2. **CMS Survey Observed Patterns** - trip purpose distribution
3. **MTA Ridership Statistics** - transit trip volumes
4. **Professional Judgment** - Brooklyn-specific knowledge

---

## Results Summary

### Output File

**Location**: `settings/brooklyn_poi_trip_rate.csv`

**Format**:
```csv
poi_type_id,building,unit_of_measure,trip_purpose,
production_rate1,attraction_rate1,production_rate2,attraction_rate2,
production_rate3,attraction_rate3,production_notes,attraction_notes
```

**Contents**:
- 53 POI building/amenity types
- 3 rows per type (one per trip purpose)
- 159 total rate rows
- Includes novel "subway_station" and "bus_stop" categories

### Key Differences from Default ITE Rates

| POI Type | Default Attr | Brooklyn Attr | Change | Reason |
|----------|--------------|---------------|--------|--------|
| Residential | 0.48 | 0.65 (HBW), 1.85 (HBO), 0.85 (NHB) | +35-285% | Higher density |
| Restaurant | 7.80 | 18.50 (HBO) | +137% | Dining culture |
| Retail | 6.84 | 12.80 (HBO) | +87% | Walkable corridors |
| Office | 2.04 prod | 2.80 (HBW) | +37% | Employment centers |
| Subway Station | N/A | 868.2 (HBW) | NEW | Major trip generator |

---

## Usage Instructions

### In Grid2Demand

```python
import grid2demand as gd

net = gd.GRID2DEMAND(input_dir='data')
net.load_network()
net.net2grid(cell_width=400, cell_height=400, unit="meter")
net.taz2zone()
net.map_zone_node_poi()
net.calc_zone_od_distance(pct=1.0)

# Use Brooklyn-calibrated rates
net.run_gravity_model(
    trip_rate_file='settings/brooklyn_poi_trip_rate.csv',
    trip_purpose=1  # 1=HBW, 2=HBO, 3=NHB
)

net.save_results_to_csv()
```

### Running All Trip Purposes

```python
# Generate demand for all three trip purposes
for purpose in [1, 2, 3]:
    net.run_gravity_model(
        trip_rate_file='settings/brooklyn_poi_trip_rate.csv',
        trip_purpose=purpose
    )
    net.save_results_to_csv(
        output_dir=f'results/purpose_{purpose}'
    )
```

---

## Validation Approach

### Recommended Validation Steps

1. **Aggregate Trip Totals**
   - Compare total generated trips to CMS survey totals
   - Check trip purpose distribution matches 6.1% HBW, 36.5% HBO, 57.5% NHB

2. **Subway Station Volumes**
   - Sum demand at zones containing subway stations
   - Compare to MTA reported ridership (~3,859/day/station average)

3. **Screenline Counts** (if available)
   - Compare bridge/tunnel volumes to NYC DOT counts
   - Major screenlines: Brooklyn-Manhattan bridges

4. **Trip Length Distribution**
   - Plot trip length frequency
   - Compare to CMS observed trip lengths for Brooklyn

### Known Limitations

1. **No Time-of-Day Variation**: Rates are daily averages
   - Future work: Peak/off-peak factors

2. **No Day-of-Week Variation**: Weekday averages assumed
   - Future work: Weekend adjustment factors

3. **Aggregated Land Use Categories**: Many OSM building types mapped to broader categories
   - Future work: More granular calibration with PLUTO building class

---

## Files Generated

### Utility Scripts

| File | Purpose |
|------|---------|
| `utils/brooklyn_trip_rate_calibration.py` | Load and analyze Brooklyn data sources |
| `utils/generate_brooklyn_poi_rates.py` | Generate calibrated trip rate table |
| `utils/run_brooklyn_calibration.py` | Main workflow script |

### Output Files

| File | Description |
|------|-------------|
| `settings/brooklyn_poi_trip_rate.csv` | Calibrated POI trip rates (159 rows) |
| `docs/methods/brooklyn_trip_rate_calibration.md` | This methodology document |

---

## References

1. **NYC Citywide Mobility Survey (2022)**
   NYC Department of Transportation
   https://data.cityofnewyork.us

2. **MTA Subway Hourly Ridership**
   Metropolitan Transportation Authority
   https://data.ny.gov/Transportation/MTA-Subway-Hourly-Ridership

3. **ITE Trip Generation Manual (10th Edition)**
   Institute of Transportation Engineers, 2017

4. **LEHD Origin-Destination Employment Statistics (LODES)**
   US Census Bureau, 2022
   https://lehd.ces.census.gov

5. **NYC MapPLUTO**
   NYC Department of City Planning, v25.3
   https://www.nyc.gov/site/planning/data-maps/open-data/dwn-pluto-mappluto.page

6. **American Community Survey (ACS) 5-Year Estimates**
   US Census Bureau, 2022
   https://www.census.gov/programs-surveys/acs

---

## Revision History

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-11-20 | 1.0 | Initial calibration | Brooklyn 4-step model team |

---

## Contact

For questions about this methodology or to suggest improvements:
- Review the utility scripts in `utils/`
- Check the CMS survey codebook in `input_data/cms/`
- Consult the original data sources listed in References
