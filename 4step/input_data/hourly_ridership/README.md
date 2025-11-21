# MTA Hourly Ridership Data

## Overview

This directory contains MTA subway hourly ridership data for OD matrix validation, with quarterly samples from 2022.

## Data Files

### Downloaded 2022 Quarterly Data

| Month | File | Size | Season | Records |
|-------|------|------|--------|---------|
| January | `mta_hourly_ridership_2022_01.csv` | 333 MB | Winter | 2,000,000 |
| April | `mta_hourly_ridership_2022_04.csv` | 333 MB | Spring | 2,000,000 |
| July | `mta_hourly_ridership_2022_07.csv` | 333 MB | Summer | 2,000,000 |
| October | `mta_hourly_ridership_2022_10.csv` | 333 MB | Fall | 2,000,000 |

**Total Downloaded**: 1.33 GB (4 months)

- **Source**: NY State Open Data - [MTA Subway Hourly Ridership](https://data.ny.gov/Transportation/MTA-Subway-Hourly-Ridership-Beginning-February-202/wujg-7c2s)
- **Time Resolution**: Hourly
- **Coverage**: Full months for Jan, Apr, Jul, Oct 2022

**Key Fields**:
- `transit_timestamp`: Date and hour of ridership
- `station_complex_id`: Unique station identifier
- `station_complex`: Station name
- `borough`: NYC borough
- `payment_method`: metrocard or omny
- `fare_class_category`: Fare type (Full, Senior, Student, Fair Fare, etc.)
- `ridership`: Number of entries
- `transfers`: Number of transfers
- `latitude`, `longitude`: Station coordinates

**Statistics** (2022 Quarterly):
- 427 unique station complexes
- Coverage: All 5 boroughs
- Payment methods: MetroCard and OMNY

**Seasonal Ridership Patterns** (sample analysis):
| Month | Mean Hourly | Max Hourly | Change vs Jan |
|-------|------------|------------|---------------|
| January | 18.6 | 2,051 | Baseline |
| April | 38.4 | 3,171 | +106.8% |
| July | 36.7 | 2,930 | +97.7% |
| October | 30.4 | 5,127 | +63.8% |

*Note: Significant increase from winter to spring 2022 reflects COVID recovery*

## Full 2022 Data Availability

**Estimated Size for Full 2022**:
- Records: ~18.25 million
- File size: ~3.5 GB
- Download in monthly chunks recommended

## Comparison with Existing OD Data

The project already contains:
- `/data/mta/mta_subway_od_2022_chunk_*.parquet`: Origin-Destination estimates
- This hourly ridership provides entry counts for validation

## Usage for Validation

1. **Entry validation**: Compare total entries to OD matrix row sums
2. **Temporal patterns**: Validate hourly distribution
3. **Station-level checks**: Verify major stations match expected volumes
4. **Payment method trends**: Understand fare type distribution

## Download Additional Months

To download other months of 2022:

```python
import requests
import urllib.parse

# Example: Download February 2022
base_url = 'https://data.ny.gov/resource/wujg-7c2s.csv'
where_clause = "transit_timestamp >= '2022-02-01T00:00:00' AND transit_timestamp < '2022-03-01T00:00:00'"
params = {
    '$where': where_clause,
    '$limit': 2000000
}
url = base_url + '?' + urllib.parse.urlencode(params)

response = requests.get(url, stream=True)
with open('mta_hourly_ridership_2022_02.csv', 'wb') as f:
    for chunk in response.iter_content(chunk_size=8192):
        f.write(chunk)
```

## Data Quality Notes

- Ridership is based on fare payment (MetroCard swipes, OMNY taps)
- Transfers are estimated based on fare rules
- Some stations may have multiple complexes
- Data updated monthly with ~2 month lag

## Integration with OD Matrix

1. **Aggregate to CMS zones**: Map stations to 12 NYC zones
2. **Sum entries**: Total ridership by zone and hour
3. **Compare to survey**: Validate CMS subway trips against actual entries
4. **Calibrate expansion**: Adjust survey weights using actual counts