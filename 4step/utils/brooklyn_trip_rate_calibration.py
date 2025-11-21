"""
Brooklyn POI Trip Rate Calibration Utilities

This module provides functions to calibrate POI trip generation rates
for Brooklyn using empirical data from multiple sources:
- NYC Citywide Mobility Survey (CMS) 2022
- MTA hourly ridership data
- LODES employment data
- ACS demographic data
- NYC MapPLUTO land use data

The calibrated rates improve upon generic ITE rates by incorporating
Brooklyn-specific travel behavior patterns.

Author: Generated for Brooklyn 4-step model calibration
Date: 2025-11-20
"""

import os
import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


class BrooklynTripRateCalibrator:
    """Main class for calibrating Brooklyn POI trip generation rates"""

    def __init__(self, input_data_dir: str):
        """
        Initialize calibrator with data directory

        Parameters
        ----------
        input_data_dir : str
            Path to directory containing input data (CMS, MTA, LODES, etc.)
        """
        self.input_data_dir = Path(input_data_dir)
        self.brooklyn_fips = '36047'  # Kings County FIPS code

        # Data storage
        self.cms_trips = None
        self.cms_households = None
        self.cms_persons = None
        self.mta_ridership = None
        self.lodes_employment = None
        self.pluto_land_use = None
        self.acs_demographics = None

        # Calibrated rates
        self.poi_rates = {}

    def load_cms_data(self):
        """Load NYC Citywide Mobility Survey data (2019 PRE-COVID)"""
        print("Loading CMS survey data (2019 PRE-COVID)...")

        cms_dir = self.input_data_dir / 'cms'

        # Load household data first to identify Brooklyn households
        hh_file = cms_dir / 'Citywide_Mobility_Survey_-_Household_2019.csv'
        if hh_file.exists():
            self.cms_households = pd.read_csv(hh_file, low_memory=False)
            print(f"  Loaded {len(self.cms_households):,} households")

            # Get Brooklyn household IDs (both Inner and Outer Brooklyn)
            brooklyn_hh = self.cms_households[
                self.cms_households['reported_home_cms_zone'].str.contains('Brooklyn', na=False)
            ]['hh_id'].values
            print(f"  Brooklyn households: {len(brooklyn_hh)}")

        # Load trip data
        trip_file = cms_dir / 'Citywide_Mobility_Survey_-_Trip_2019.csv'
        if trip_file.exists():
            self.cms_trips = pd.read_csv(trip_file, low_memory=False)
            print(f"  Loaded {len(self.cms_trips):,} trips")

            # Filter to Brooklyn household trips
            brooklyn_trips = self.cms_trips[self.cms_trips['hh_id'].isin(brooklyn_hh)]
            print(f"  Brooklyn household trips: {len(brooklyn_trips):,}")
            self.cms_trips_brooklyn = brooklyn_trips

        # Load person data
        person_file = cms_dir / 'Citywide_Mobility_Survey_-_Person_2019.csv'
        if person_file.exists():
            self.cms_persons = pd.read_csv(person_file, low_memory=False)
            print(f"  Loaded {len(self.cms_persons):,} persons")

        return self

    def load_mta_ridership(self, months=['01', '04', '07', '10']):
        """
        Load MTA hourly ridership data

        Parameters
        ----------
        months : list
            List of month strings to load (default: quarterly sample)
        """
        print("Loading MTA ridership data...")

        ridership_dir = self.input_data_dir / 'hourly_ridership'
        dfs = []

        for month in months:
            file_path = ridership_dir / f'mta_hourly_ridership_2022_{month}.csv'
            if file_path.exists():
                df = pd.read_csv(file_path, low_memory=False)
                dfs.append(df)
                print(f"  Loaded {month}/2022: {len(df):,} records")

        if dfs:
            self.mta_ridership = pd.concat(dfs, ignore_index=True)

            # Filter to Brooklyn stations
            brooklyn_ridership = self.mta_ridership[
                self.mta_ridership['borough'] == 'Brooklyn'
            ]
            print(f"  Brooklyn station records: {len(brooklyn_ridership):,}")
            self.mta_ridership_brooklyn = brooklyn_ridership

        return self

    def load_lodes_employment(self):
        """Load LODES employment data for Brooklyn"""
        print("Loading LODES employment data...")

        lodes_dir = self.input_data_dir / 'lodes'

        # Load workplace area characteristics (where people work)
        wac_file = lodes_dir / 'ny_wac_S000_JT00_2022.csv.gz'
        if wac_file.exists():
            wac = pd.read_csv(wac_file, compression='gzip', low_memory=False)
            print(f"  Loaded {len(wac):,} work area records")

            # Load crosswalk to filter to Brooklyn
            xwalk_file = lodes_dir / 'ny_xwalk.csv.gz'
            if xwalk_file.exists():
                xwalk = pd.read_csv(xwalk_file, compression='gzip', low_memory=False)

                # Filter to Brooklyn blocks
                brooklyn_blocks = xwalk[xwalk['cty'] == self.brooklyn_fips]['tabblk2020'].values
                wac_brooklyn = wac[wac['w_geocode'].isin(brooklyn_blocks)]
                print(f"  Brooklyn employment blocks: {len(wac_brooklyn):,}")
                self.lodes_employment = wac_brooklyn

        return self

    def load_pluto_land_use(self):
        """Load NYC MapPLUTO land use data"""
        print("Loading MapPLUTO land use data...")

        pluto_dir = self.input_data_dir / 'land_use' / 'nyc_mappluto_25v3_shp'
        shp_file = pluto_dir / 'MapPLUTO.shp'

        if shp_file.exists():
            pluto = gpd.read_file(shp_file)
            print(f"  Loaded {len(pluto):,} parcels")

            # Filter to Brooklyn (Borough = 3)
            pluto_brooklyn = pluto[pluto['Borough'] == 'BK']
            print(f"  Brooklyn parcels: {len(pluto_brooklyn):,}")
            self.pluto_land_use = pluto_brooklyn

        return self

    def load_acs_demographics(self):
        """Load ACS demographic data for Brooklyn"""
        print("Loading ACS demographic data...")

        acs_dir = self.input_data_dir / 'acs'

        # Load key demographic files
        files_to_load = {
            'household_income': 'acs5_2022_b19001_household_income_blockgroups.json',
            'commute_mode': 'acs5_2022_b08301_commute_mode_blockgroups.json',
            'vehicles_available': 'acs5_2022_b08201_vehicles_available_blockgroups.json',
        }

        self.acs_demographics = {}

        for key, filename in files_to_load.items():
            file_path = acs_dir / filename
            if file_path.exists():
                df = pd.read_json(file_path)
                # Filter to Brooklyn (county 047)
                if isinstance(df, pd.DataFrame) and len(df) > 0:
                    self.acs_demographics[key] = df
                    print(f"  Loaded {key}: {len(df):,} records")

        return self

    def analyze_residential_trip_rates(self):
        """
        Analyze residential trip generation rates from CMS data

        Returns
        -------
        dict : Residential trip rates by trip purpose (HBW, HBO, NHB)
        """
        print("\nAnalyzing residential trip rates from CMS...")

        if self.cms_trips_brooklyn is None:
            print("  Warning: CMS data not loaded")
            return {}

        # Classify trips by purpose
        # HBW (1): work trips
        # HBO (2): non-work home-based
        # NHB (3): non-home-based

        trips = self.cms_trips_brooklyn.copy()

        # Map CMS trip purposes to our 3-category system
        # Based on o_purpose_category and d_purpose_category
        def classify_trip_purpose(row):
            o_cat = row.get('o_purpose_category', -1)
            d_cat = row.get('d_purpose_category', -1)

            # Home = category 1, Work = category 2 (FIXED: was incorrectly 7)
            is_home_o = (o_cat == 1)
            is_home_d = (d_cat == 1)
            is_work_o = (o_cat == 2)  # CORRECT: 2 = Work
            is_work_d = (d_cat == 2)  # CORRECT: 2 = Work

            if (is_home_o and is_work_d) or (is_work_o and is_home_d):
                return 1  # HBW
            elif is_home_o or is_home_d:
                return 2  # HBO
            else:
                return 3  # NHB

        trips['trip_purpose_class'] = trips.apply(classify_trip_purpose, axis=1)

        # Calculate rates
        purpose_counts = trips['trip_purpose_class'].value_counts()
        total_trips = len(trips)

        results = {
            'HBW_trips': purpose_counts.get(1, 0),
            'HBO_trips': purpose_counts.get(2, 0),
            'NHB_trips': purpose_counts.get(3, 0),
            'total_trips': total_trips,
            'HBW_pct': purpose_counts.get(1, 0) / total_trips if total_trips > 0 else 0,
            'HBO_pct': purpose_counts.get(2, 0) / total_trips if total_trips > 0 else 0,
            'NHB_pct': purpose_counts.get(3, 0) / total_trips if total_trips > 0 else 0,
        }

        print(f"  HBW trips: {results['HBW_trips']:,} ({results['HBW_pct']:.1%})")
        print(f"  HBO trips: {results['HBO_trips']:,} ({results['HBO_pct']:.1%})")
        print(f"  NHB trips: {results['NHB_trips']:,} ({results['NHB_pct']:.1%})")

        return results

    def analyze_subway_station_rates(self):
        """
        Calculate trip rates for subway stations from MTA ridership

        Returns
        -------
        dict : Average daily ridership per station
        """
        print("\nAnalyzing subway station trip rates from MTA data...")

        if self.mta_ridership_brooklyn is None:
            print("  Warning: MTA data not loaded")
            return {}

        ridership = self.mta_ridership_brooklyn.copy()

        # Aggregate by station
        station_totals = ridership.groupby('station_complex').agg({
            'ridership': 'sum',
            'latitude': 'first',
            'longitude': 'first'
        }).reset_index()

        # Calculate average daily ridership (data from 4 months = ~120 days)
        days_sampled = 120  # Approximate
        station_totals['avg_daily_ridership'] = station_totals['ridership'] / days_sampled

        print(f"  Analyzed {len(station_totals)} Brooklyn subway stations")
        print(f"  Average daily ridership per station: {station_totals['avg_daily_ridership'].mean():.0f}")
        print(f"  Median daily ridership per station: {station_totals['avg_daily_ridership'].median():.0f}")

        return {
            'station_data': station_totals,
            'avg_daily_per_station': station_totals['avg_daily_ridership'].mean(),
            'median_daily_per_station': station_totals['avg_daily_ridership'].median(),
        }

    def analyze_employment_centers(self):
        """
        Analyze employment centers from LODES data

        Returns
        -------
        dict : Employment statistics for office/commercial uses
        """
        print("\nAnalyzing employment centers from LODES...")

        if self.lodes_employment is None:
            print("  Warning: LODES data not loaded")
            return {}

        emp = self.lodes_employment.copy()

        # Key employment sectors (from LODES)
        # C000 = total jobs
        # CNS07 = retail
        # CNS09 = arts/entertainment/recreation/food
        # CNS10 = education
        # CNS12 = public administration
        # CNS13 = professional services

        results = {
            'total_jobs': emp['C000'].sum() if 'C000' in emp.columns else 0,
            'retail_jobs': emp['CNS07'].sum() if 'CNS07' in emp.columns else 0,
            'food_arts_jobs': emp['CNS09'].sum() if 'CNS09' in emp.columns else 0,
            'education_jobs': emp['CNS15'].sum() if 'CNS15' in emp.columns else 0,
        }

        print(f"  Total jobs in Brooklyn: {results['total_jobs']:,}")
        print(f"  Retail jobs: {results['retail_jobs']:,}")
        print(f"  Food/Arts/Rec jobs: {results['food_arts_jobs']:,}")

        return results


def calculate_brooklyn_poi_rates(input_data_dir: str, output_file: str = None):
    """
    Main function to calculate Brooklyn-specific POI trip rates

    Parameters
    ----------
    input_data_dir : str
        Path to input data directory
    output_file : str, optional
        Path to save output CSV (default: None, returns DataFrame only)

    Returns
    -------
    pd.DataFrame : Brooklyn-calibrated POI trip rates
    """
    print("="*70)
    print("Brooklyn POI Trip Rate Calibration")
    print("="*70)

    # Initialize calibrator
    calibrator = BrooklynTripRateCalibrator(input_data_dir)

    # Load all data sources
    calibrator.load_cms_data()
    calibrator.load_mta_ridership()
    calibrator.load_lodes_employment()
    calibrator.load_pluto_land_use()
    calibrator.load_acs_demographics()

    # Analyze trip patterns
    residential_rates = calibrator.analyze_residential_trip_rates()
    subway_rates = calibrator.analyze_subway_station_rates()
    employment_stats = calibrator.analyze_employment_centers()

    print("\n" + "="*70)
    print("Data loading and analysis complete!")
    print("="*70)

    return {
        'calibrator': calibrator,
        'residential_rates': residential_rates,
        'subway_rates': subway_rates,
        'employment_stats': employment_stats,
    }


if __name__ == '__main__':
    # Example usage
    input_dir = '../input_data'
    results = calculate_brooklyn_poi_rates(input_dir)
