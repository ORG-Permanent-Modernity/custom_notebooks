# Citywide Mobility Survey (CMS) Data Directory

This directory stores manually downloaded CMS survey data files.

## Required Files for CMS 2022

Download these files from NYC Open Data following instructions in `/docs/user_guide/manual_downloads.md`:

- `trip_2022.csv` - Trip-level data (origins, destinations, modes, purposes)
- `person_2022.csv` - Person characteristics
- `household_2022.csv` - Household characteristics
- `day_2022.csv` - Daily travel diary information
- `vehicle_2022.csv` - Household vehicle information

## File Organization

```
cms/
├── README.md (this file)
├── trip_2022.csv
├── person_2022.csv
├── household_2022.csv
├── day_2022.csv
├── vehicle_2022.csv
└── [optional subdirectories for other years]
    ├── 2019/
    ├── 2018/
    └── 2017/
```

## Notes

- All CSV files should use UTF-8 encoding
- Files are large (500MB - 1GB each)
- Keep original downloaded files unchanged
- Processed/cleaned versions will be saved to `data/processed/`

## Data Source

NYC Department of Transportation via NYC Open Data Portal:
https://data.cityofnewyork.us

Dataset IDs:
- Trip 2022: x5mc-2gmi
- Person 2022: 7qdz-u9hr
- Household 2022: dt3g-khpi
- Day 2022: 5njs-bq3c
- Vehicle 2022: qyry-gwrj
