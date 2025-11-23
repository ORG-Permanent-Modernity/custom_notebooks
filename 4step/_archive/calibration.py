"""
Calibration and balancing utilities for the 4-step travel demand model.
"""
import pandas as pd
import numpy as np

def get_cms_control_totals(cms_trip_df: pd.DataFrame, cms_household_df: pd.DataFrame):
    """
    Calculates control totals from the CMS survey data for Brooklyn.

    Args:
        cms_trip_df (pd.DataFrame): The CMS trip data.
        cms_household_df (pd.DataFrame): The CMS household data.

    Returns:
        dict: A dictionary containing 'total_trips' and 'avg_trip_length'.
    """
    print("Calculating control totals from CMS data for Brooklyn...")

    # Get Brooklyn household IDs
    brooklyn_hh = cms_household_df[
        cms_household_df['reported_home_cms_zone'].str.contains('Brooklyn', na=False)
    ]['hh_id'].unique()
    
    print(f"  Found {len(brooklyn_hh):,} unique Brooklyn households.")

    # Filter trips to only those made by Brooklyn households
    brooklyn_trips = cms_trip_df[cms_trip_df['hh_id'].isin(brooklyn_hh)].copy()
    
    total_trips = len(brooklyn_trips)
    print(f"  Found {total_trips:,} total trips made by Brooklyn households.")

    # Calculate average trip length (assuming 'trip_distance_miles' column exists)
    if 'trip_distance_miles' not in brooklyn_trips.columns:
        raise ValueError("CMS trip data must contain a 'trip_distance_miles' column.")
        
    # Remove outliers and invalid values
    brooklyn_trips['trip_distance_miles'] = pd.to_numeric(brooklyn_trips['trip_distance_miles'], errors='coerce')
    brooklyn_trips.dropna(subset=['trip_distance_miles'], inplace=True)
    # Filter for reasonable trip lengths (e.g., > 0 and < 100 miles)
    valid_trips = brooklyn_trips[
        (brooklyn_trips['trip_distance_miles'] > 0) & 
        (brooklyn_trips['trip_distance_miles'] < 100)
    ]
    
    avg_trip_length = valid_trips['trip_distance_miles'].mean()
    print(f"  Calculated average trip length: {avg_trip_length:.2f} miles.")

    return {
        'total_trips': total_trips,
        'avg_trip_length': avg_trip_length
    }

def balance_productions_attractions(zone_dict: dict, total_target_trips: int, max_iterations: int = 100, tolerance: float = 0.01):
    """
    Balances production and attraction vectors using Iterative Proportional Fitting (IPF) or "Furnessing".

    Args:
        zone_dict (dict): The zone dictionary from grid2demand, containing 'production' and 'attraction' keys.
        total_target_trips (int): The control total for trips from an external source (e.g., CMS).
        max_iterations (int): The maximum number of iterations to perform.
        tolerance (float): The convergence tolerance.

    Returns:
        dict: The updated zone_dict with balanced 'production' and 'attraction' values.
    """
    print("Balancing productions and attractions...")

    # Extract P and A vectors
    p_initial = np.array([zone_dict[z].get('production', 0) for z in zone_dict])
    a_initial = np.array([zone_dict[z].get('attraction', 0) for z in zone_dict])

    # Scale initial P and A to match the global target
    if p_initial.sum() > 0:
        p_scaled = p_initial * (total_target_trips / p_initial.sum())
    else:
        p_scaled = p_initial

    if a_initial.sum() > 0:
        a_scaled = a_initial * (total_target_trips / a_initial.sum())
    else:
        a_scaled = a_initial

    # Create a dummy OD matrix for iteration
    # In a full implementation, this would be the output of the gravity model
    # For balancing P and A vectors, we can just scale them to the grand total.
    # A true Furness process requires an initial seed matrix.
    
    print("  Scaling productions and attractions to match control total.")
    
    # For this implementation, we will do a simple scaling, as a full IPF
    # requires an OD matrix. We will scale P and A independently to the target total.
    
    p_balanced = p_scaled
    a_balanced = a_scaled

    # Update the zone_dict with the balanced values
    for i, zone_id in enumerate(zone_dict.keys()):
        zone_dict[zone_id]['production'] = p_balanced[i]
        zone_dict[zone_id]['attraction'] = a_balanced[i]
        
    print(f"  New total productions: {p_balanced.sum():,.0f}")
    print(f"  New total attractions: {a_balanced.sum():,.0f}")

    return zone_dict

def calibrate_gravity_model(net, target_avg_trip_length: float, trip_purpose: int, trip_rate_file: str):
    """
    Calibrates the gravity model by finding the best beta parameter.

    This is a simplified calibration that focuses on the 'beta' parameter,
    which most directly controls trip length decay.

    Args:
        net (GRID2DEMAND): The grid2demand network object.
        target_avg_trip_length (float): The target average trip length from CMS.
        trip_purpose (int): The trip purpose to use.
        trip_rate_file (str): Path to the trip rate file.

    Returns:
        dict: A dictionary with the best parameters and the final demand DataFrame.
    """
    print("Calibrating gravity model...")
    print(f"  Target average trip length: {target_avg_trip_length:.2f} miles.")

    # Define a range of beta values to test
    beta_values = np.linspace(-2.0, -0.1, 20)
    best_beta = None
    smallest_diff = float('inf')
    final_demand_df = None

    # Fixed alpha and gamma for simplicity in this calibration
    alpha = 1.0
    gamma = 0.0

    for beta in beta_values:
        print(f"  Testing beta = {beta:.4f}...")
        
        # Run the gravity model
        demand_df = net.run_gravity_model(
            alpha=alpha,
            beta=beta,
            gamma=gamma,
            trip_rate_file=trip_rate_file,
            trip_purpose=trip_purpose
        )

        # Calculate the average trip length for this run
        # This requires merging with the distance matrix
        dist_matrix_df = pd.DataFrame(net.zone_od_dist_matrix.items(), columns=['od_pair', 'distance_m'])
        dist_matrix_df['o_zone_id'] = dist_matrix_df['od_pair'].apply(lambda x: x[0])
        dist_matrix_df['d_zone_id'] = dist_matrix_df['od_pair'].apply(lambda x: x[1])
        
        # Convert meters to miles
        dist_matrix_df['distance'] = dist_matrix_df['distance_m'] * 0.000621371

        merged_df = demand_df.merge(dist_matrix_df, on=['o_zone_id', 'd_zone_id'])
        
        if merged_df['volume'].sum() > 0:
            model_avg_trip_length = (merged_df['volume'] * merged_df['distance']).sum() / merged_df['volume'].sum()
        else:
            model_avg_trip_length = 0

        diff = abs(model_avg_trip_length - target_avg_trip_length)
        print(f"    Model avg trip length: {model_avg_trip_length:.2f}, Difference: {diff:.2f}")

        if diff < smallest_diff:
            smallest_diff = diff
            best_beta = beta
            final_demand_df = demand_df

    print(f"\n  Best beta found: {best_beta:.4f}")
    
    return {
        'best_beta': best_beta,
        'alpha': alpha,
        'gamma': gamma,
        'demand_df': final_demand_df
    }
