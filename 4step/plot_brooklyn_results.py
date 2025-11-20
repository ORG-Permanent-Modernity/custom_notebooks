# Draw results

import os
import contextily as cx
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely import wkt
from matplotlib.collections import LineCollection
import numpy as np
import pandas as pd
import osmnx as ox


def plot_results(output_dir, place_name="Brooklyn, New York City, New York, USA"):
    """
    Plot grid2demand results with zones, OD pairs, and basemap.

    Parameters
    ----------
    output_dir : str
        Directory containing zone.csv and demand.csv files
    place_name : str, optional
        Place name for geocoding boundary (default: Brooklyn)
    """
    print("Testing basemap with zone boxes, numbers, and OD pairs...")

    # Get boundary (for extent calculation only)
    brooklyn_boundary = ox.geocode_to_gdf(place_name)

    # Load zone data
    zone_df = pd.read_csv(os.path.join(output_dir, 'zone.csv'))
    print(f"Loaded {len(zone_df)} zones")

    # Check if population data exists
    has_population = 'population' in zone_df.columns
    if has_population:
        print(f"✓ Population data found in zone.csv")
    else:
        print(f"Note: No population column in zone.csv")

    # Filter to zones with demand
    demand_df = pd.read_csv(os.path.join(output_dir, 'demand.csv'))
    zones_with_demand = set()
    zones_with_demand.update(demand_df[demand_df['volume'] > 0]['o_zone_id'].unique())
    zones_with_demand.update(demand_df[demand_df['volume'] > 0]['d_zone_id'].unique())
    zone_df_filtered = zone_df[zone_df['zone_id'].isin(zones_with_demand)].copy()
    print(f"Filtered to {len(zone_df_filtered)} zones with demand")

    # Calculate combined A-B + B-A trips for each OD pair
    print("Calculating combined bidirectional trips...")
    od_combined = []
    processed_pairs = set()

    for _, row in demand_df.iterrows():
        o_zone = row['o_zone_id']
        d_zone = row['d_zone_id']

        if (d_zone, o_zone) in processed_pairs or o_zone == d_zone:
            continue

        reverse_trip = demand_df[(demand_df['o_zone_id'] == d_zone) &
                                 (demand_df['d_zone_id'] == o_zone)]

        volume_ab = row['volume']
        volume_ba = reverse_trip['volume'].values[0] if len(reverse_trip) > 0 else 0

        od_combined.append({
            'zone_a': o_zone,
            'zone_b': d_zone,
            'combined_volume': volume_ab + volume_ba
        })

        processed_pairs.add((o_zone, d_zone))

    od_combined_df = pd.DataFrame(od_combined)
    top_200_od = od_combined_df.nlargest(200, 'combined_volume')
    print(f"✓ Selected top 200 OD pairs by combined volume")

    # Load actual zone polygons from the geometry column
    zone_df_filtered['polygon_geometry'] = zone_df_filtered['geometry'].apply(wkt.loads)
    zone_poly_gdf = gpd.GeoDataFrame(
        zone_df_filtered[['zone_id']],
        geometry=zone_df_filtered['polygon_geometry'],
        crs='EPSG:4326'
    )

    # Create zone centroids
    zone_centroids = gpd.GeoDataFrame(
        zone_df_filtered,
        geometry=gpd.points_from_xy(zone_df_filtered['x_coord'], zone_df_filtered['y_coord']),
        crs='EPSG:4326'
    )

    # Convert to Web Mercator
    brooklyn_merc = brooklyn_boundary.to_crs(epsg=3857)
    zone_poly_merc = zone_poly_gdf.to_crs(epsg=3857)
    zone_centroids_merc = zone_centroids.to_crs(epsg=3857)

    # Create bigger plot with tight margins
    fig, ax = plt.subplots(figsize=(16, 20))

    # Plot zone boxes (this sets the extent)
    zone_poly_merc.plot(ax=ax, facecolor='none', edgecolor='black', linewidth=0.5, alpha=1.0, zorder=3)

    # Set tight axis limits based on zone bounds with minimal margin
    zone_bounds = zone_poly_merc.total_bounds  # (minx, miny, maxx, maxy)
    margin_x = (zone_bounds[2] - zone_bounds[0]) * 0.02  # 2% margin
    margin_y = (zone_bounds[3] - zone_bounds[1]) * 0.02  # 2% margin
    ax.set_xlim(zone_bounds[0] - margin_x, zone_bounds[2] + margin_x)
    ax.set_ylim(zone_bounds[1] - margin_y, zone_bounds[3] + margin_y)

    # Plot top 200 OD pairs as lines
    lines = []
    widths = []

    max_volume = top_200_od['combined_volume'].max()
    min_volume = top_200_od['combined_volume'].min()

    from pyproj import Transformer
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

    for _, od_row in top_200_od.iterrows():
        zone_a = zone_df_filtered[zone_df_filtered['zone_id'] == od_row['zone_a']]
        zone_b = zone_df_filtered[zone_df_filtered['zone_id'] == od_row['zone_b']]

        if len(zone_a) == 0 or len(zone_b) == 0:
            continue

        zone_a = zone_a.iloc[0]
        zone_b = zone_b.iloc[0]

        x1, y1 = transformer.transform(zone_a['x_coord'], zone_a['y_coord'])
        x2, y2 = transformer.transform(zone_b['x_coord'], zone_b['y_coord'])

        line = [(x1, y1), (x2, y2)]
        lines.append(line)

        # Scale line width with better differentiation for medium values
        # Using power scaling to spread out medium values more (1.0 to 6.0 range)
        normalized_volume = (od_row['combined_volume'] - min_volume) / (max_volume - min_volume)
        # Apply square root to compress high values and expand medium values
        width = 1.0 + (normalized_volume ** 0.5) * 5.0
        widths.append(width)

    lc = LineCollection(lines, linewidths=widths, colors='red', alpha=0.6, zorder=4)
    ax.add_collection(lc)

    print(f"✓ Plotted {len(lines)} OD pairs")
    print(f"  Line width range: 1.0 - 6.0")

    # Add zone numbers and data labels
    from matplotlib import font_manager
    for idx, row in zone_poly_merc.iterrows():
        zone_id = row['zone_id']

        # Get corresponding zone data from filtered dataframe
        zone_data = zone_df_filtered[zone_df_filtered['zone_id'] == zone_id].iloc[0]

        # Get the bounds of this zone polygon
        bounds = row.geometry.bounds  # (minx, miny, maxx, maxy)

        # Upper left corner - Zone ID
        x_upper_left = bounds[0] + (bounds[2] - bounds[0]) * 0.05  # 5% from left edge
        y_upper_left = bounds[3] - (bounds[3] - bounds[1]) * 0.05  # 5% from top edge

        ax.annotate(text=str(int(zone_id)),
                   xy=(x_upper_left, y_upper_left),
                   fontsize=7, ha='left', va='top',
                   color='black', weight='bold', zorder=5,
                   fontfamily='Arial',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='none', alpha=0.7))

        # Bottom left corner - POI count (bigger font, black)
        poi_count = len(eval(zone_data['poi_id_list'])) if 'poi_id_list' in zone_data and pd.notna(zone_data['poi_id_list']) else 0
        x_bottom_left = bounds[0] + (bounds[2] - bounds[0]) * 0.05
        y_bottom_left = bounds[1] + (bounds[3] - bounds[1]) * 0.05  # 5% from bottom edge

        ax.annotate(text=f"POI:{poi_count}",
                   xy=(x_bottom_left, y_bottom_left),
                   fontsize=7, ha='left', va='bottom',
                   color='black', weight='normal', zorder=5,
                   fontfamily='Arial',
                   bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor='none', alpha=0.6))

        # Bottom right corner - Population (if available)
        if has_population:
            population = zone_data['population'] if pd.notna(zone_data['population']) else 0
            x_bottom_right = bounds[2] - (bounds[2] - bounds[0]) * 0.05
            y_bottom_right = bounds[1] + (bounds[3] - bounds[1]) * 0.05

            ax.annotate(text=f"Pop:{int(population)}",
                       xy=(x_bottom_right, y_bottom_right),
                       fontsize=5, ha='right', va='bottom',
                       color='darkblue', weight='normal', zorder=5,
                       fontfamily='Arial',
                       bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor='none', alpha=0.6))

    print(f"✓ Added {len(zone_poly_merc)} zone labels with POI counts")

    # Add basemap AFTER plotting data
    print("Adding basemap...")
    cx.add_basemap(ax, source=cx.providers.OpenStreetMap.Mapnik, alpha=0.5, zorder=1)

    ax.set_title("Brooklyn Zones with Top 200 OD Pairs and OSM Basemap", fontsize=16, fontweight='bold')
    ax.axis('off')
    plt.tight_layout()
    plt.show()

    print("✓ Test complete!")
    print(f"  {len(zone_poly_merc)} zone boxes plotted")
    print(f"  {len(lines)} OD pairs plotted")
    print(f"  Top 200 volume range: {min_volume:.0f} - {max_volume:.0f}")