# Cell 1: Imports
# Load libraries

import osmnx as ox
import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path
from shapely.geometry import box

import folium
from folium.plugins import MarkerCluster

# ---------------------------------------------------------------------------

# Cell 2: Data Loading
# Load the processed trip generator and building datasets
trip_generators_gdf = gpd.read_file("data/trip_generators_brooklyn.geojson")
buildings_4326 = gpd.read_file("data/buildings_brooklyn.geojson")

# ---------------------------------------------------------------------------

# Cell 3: Map Visualization
# Define an inspection area
INSPECT_BOUNDS = {
    'min_lat': 40.671, 'max_lat': 40.680,
    'min_lon': -73.980, 'max_lon': -73.965
}

# --- Data Preparation ---

# Create a bounding box for spatial intersection
bbox = box(INSPECT_BOUNDS['min_lon'], INSPECT_BOUNDS['min_lat'], INSPECT_BOUNDS['max_lon'], INSPECT_BOUNDS['max_lat'])
bbox_gdf = gpd.GeoDataFrame([1], geometry=[bbox], crs="EPSG:4326")

# Filter buildings and generators to the inspection area
inspect_buildings = gpd.sjoin(buildings_4326, bbox_gdf, how="inner", predicate="intersects").drop(columns=['index_right'])
inspect_generators = gpd.sjoin(trip_generators_gdf, bbox_gdf, how="inner", predicate="intersects").drop(columns=['index_right'])

print(f"Buildings in inspection area: {len(inspect_buildings):,}")
print(f"POIs / Land Use units in inspection area: {len(inspect_generators):,}")
print("\nLand use breakdown in inspection area:")
print(inspect_generators['land_use_type'].value_counts().head(15))

# --- Map Generation ---

# Determine primary use for each building for coloring
# Take the generator with the largest square footage in each building
primary_use = inspect_generators.loc[inspect_generators.groupby('building_id')['sqft'].idxmax()]
building_primary_use = primary_use[['building_id', 'land_use_type']].set_index('building_id')

# Join this primary use back to the buildings GeoDataFrame
inspect_buildings = inspect_buildings.join(building_primary_use, on='building_id')
inspect_buildings['primary_use'] = inspect_buildings['land_use_type'].fillna('unknown')

# Create a color mapping
color_map = {
    'residential': '#3388ff', 'restaurant': '#ff8c00', 'cafe': '#ffa500',
    'supermarket': '#228b22', 'convenience': '#32cd32', 'office': '#808080',
    'school': '#dc143c', 'place_of_worship': '#8b0000', 'industrial': '#2f4f4f',
    'unknown': '#cccccc'
}
inspect_buildings['color'] = inspect_buildings['primary_use'].map(color_map).fillna('#cccccc')

# --- Create Folium Map ---
m = folium.Map(location=[40.675, -73.9725], zoom_start=16, tiles="CartoDB positron")

# Prepare data for popups
popup_data = inspect_generators.groupby('building_id').apply(
    lambda grp: "<br>".join([f"• {row.land_use_type}: {row.sqft:,.0f} sqft ({row.source})" for _, row in grp.iterrows()])
).to_dict()

# Add popups to the inspect_buildings gdf
inspect_buildings['popup_html'] = inspect_buildings.apply(
    lambda row: f"""
        <b>Building ID:</b> {row.building_id}<br>
        <b>Total SqFt:</b> {row.total_sqft:,.0f}<br>
        <b>Floors:</b> {row.estimated_floors}<br>
        <hr>
        <b>Land Use Units:</b><br>
        {popup_data.get(row.building_id, 'No POIs found')}
    """,
    axis=1
)

# Add the single building layer with a style function and popups
folium.GeoJson(
    inspect_buildings,
    style_function=lambda x: {
        'fillColor': x['properties']['color'],
        'color': 'black',
        'weight': 1,
        'fillOpacity': 0.7
    },
    popup=folium.GeoJsonPopup(fields=['popup_html']),
    name='Buildings'
).add_to(m)

# Add POI markers in a MarkerCluster for efficiency
mc = MarkerCluster(name='POI Markers')
for idx, row in inspect_generators.iterrows():
    # Only add markers for actual OSM POIs, not inferred uses
    if row['source'] == 'osm_poi':
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=3,
            color='red',
            fill=True,
            fill_color='red',
            fill_opacity=0.7,
            popup=f"{row['name']}<br>({row['land_use_type']})"
        ).add_to(mc)
mc.add_to(m)

# Add layer control and display map
folium.LayerControl().add_to(m)

m
