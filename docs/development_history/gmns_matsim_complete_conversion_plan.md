# Complete GMNS to MATSim Conversion Plan: Network + Demand

## Executive Summary

This document provides a comprehensive plan for converting GMNS network data and grid2demand demand matrices into complete MATSim simulation inputs. This includes both network.xml (infrastructure) and population.xml (travel demand) file generation.

**Status**: Planning Phase - Extended Research Complete
**Date**: 2025-11-19
**Project**: Complete GMNS + Demand to MATSim Converter

---

## Table of Contents

1. [Overview of Conversion Scope](#1-overview-of-conversion-scope)
2. [Data Source Comparison: OSMnx vs osm2gmns](#2-data-source-comparison-osmnx-vs-osm2gmns)
3. [Network Conversion (GMNS → MATSim network.xml)](#3-network-conversion-gmns--matsim-networkxml)
4. [Demand Conversion (grid2demand → MATSim population.xml)](#4-demand-conversion-grid2demand--matsim-populationxml)
5. [Complete Converter Architecture](#5-complete-converter-architecture)
6. [Implementation Workflow](#6-implementation-workflow)
7. [Testing and Validation](#7-testing-and-validation)
8. [Usage Examples](#8-usage-examples)

---

## 1. Overview of Conversion Scope

### 1.1 Input Data Sources

**Network Data (Two Options)**:
1. **OSMnx + Custom Parser** (Current Manhattan implementation)
   - Direct NetworkX graph from OSM
   - Manual GMNS CSV generation
   - Simple but requires custom parsing

2. **osm2gmns Library** (Recommended for completeness)
   - Professional GMNS export with full specification compliance
   - Advanced features: geometry preservation, capacity refinement
   - More comprehensive link attributes

**Demand Data**:
- **grid2demand Library** outputs:
  - `zone.csv` - Traffic Analysis Zones with production/attraction
  - `demand.csv` - Origin-Destination matrix (o_zone_id, d_zone_id, volume)
  - `node.csv` - Network nodes (updated with zone assignments)

### 1.2 Output Requirements

**MATSim Inputs**:
1. **network.xml** - Road infrastructure (nodes, links)
2. **population.xml** - Travel demand (agents, plans, activities, trips)

### 1.3 Conversion Challenges Summary

| Component | Input Format | Output Format | Key Challenge | Priority |
|-----------|--------------|---------------|---------------|----------|
| Network Nodes | CSV (WGS84) | XML (projected) | Coordinate transformation | **CRITICAL** |
| Network Links | CSV (various units) | XML (standardized) | Unit conversions, mode mapping | **HIGH** |
| Demand Matrix | CSV (zone-to-zone) | XML (agent plans) | Disaggregation to individuals | **CRITICAL** |
| Zone Centroids | CSV coordinates | XML link references | Zone-to-link mapping | **HIGH** |

---

## 2. Data Source Comparison: OSMnx vs osm2gmns

### 2.1 Feature Comparison

| Feature | OSMnx + Custom | osm2gmns | Winner |
|---------|----------------|----------|--------|
| **Basic Network** | ✓ | ✓ | Tie |
| **Node Coordinates** | ✓ WGS84 | ✓ WGS84 | Tie |
| **Link Length** | ✓ Meters | ✓ Meters | Tie |
| **Lane Count** | Manual parsing | ✓ Auto-filled | **osm2gmns** |
| **Capacity** | Manual calc (1800/lane) | ✓ Type-specific defaults | **osm2gmns** |
| **Free Speed** | Fixed (35 mph) | ✓ Type-specific defaults | **osm2gmns** |
| **Geometry WKT** | Empty | ✓ Full LINESTRING | **osm2gmns** |
| **Link Type** | OSM tag only | ✓ Facility type + link type | **osm2gmns** |
| **OSM Way ID** | Not preserved | ✓ Preserved | **osm2gmns** |
| **Allowed Uses** | Not captured | ✓ (auto, bike, walk) | **osm2gmns** |
| **Multi-resolution** | No | ✓ (macro/meso/micro) | **osm2gmns** |
| **Lane Changes** | Not modeled | ✓ Segment splitting | **osm2gmns** |
| **Setup Complexity** | Simple | Moderate | **OSMnx** |

### 2.2 Data Quality Comparison

**Manhattan Dataset (OSMnx approach)**:
```csv
# node.csv
node_id,osm_node_id,x_coord,y_coord,longitude,latitude,activity_type,is_boundary,zone_id
0,42421728,-73.9600437,40.7980478,-73.9600437,40.7980478,node,0,-1

# link.csv
link_id,from_node_id,to_node_id,length,lanes,capacity,free_speed,link_type,geometry
0,0,1298,85.34515470462713,1,1800,35,secondary,
```

**Brooklyn Dataset (osm2gmns approach)**:
```csv
# node.csv
node_id,x_coord,y_coord,production,attraction,zone_id,geometry,_zone_id,activity_type
1,-73.9891992,40.6910987,50,50,11,POINT (-73.9891992 40.6910987),-1,

# link.csv (significantly richer)
link_id,name,osm_way_id,from_node_id,to_node_id,directed,geometry,dir_flag,length,facility_type,link_type,free_speed,lanes,capacity,allowed_uses,notes
1,Boerum Place,5029221,1,2,1,"LINESTRING (-73.9891992 40.6910987, -73.9891848 40.6911486, -73.9891573 40.6912592, -73.9891327 40.6913611)",1,29.71,primary,3,40,3,,auto,
```

### 2.3 Key Differences in osm2gmns Output

1. **Geometry Preservation**
   - Full LINESTRING WKT geometry for each link
   - Captures curved roads, not just straight lines
   - Better visualization and potentially more accurate routing

2. **Intelligent Default Values**
   - Type-specific capacity: motorway=2300, primary=1800, residential=600
   - Type-specific speeds: motorway=120, primary=80, residential=40
   - Automatically fills missing OSM data

3. **Road Name Preservation**
   - Street names preserved from OSM
   - Useful for debugging and visualization

4. **Allowed Uses**
   - Explicitly captures mode restrictions (auto, bike, walk)
   - Directly maps to MATSim modes attribute

5. **Facility Type Classification**
   - Structured road hierarchy (motorway, trunk, primary, secondary, tertiary, residential)
   - Numeric link_type codes for programmatic processing

### 2.4 Recommendation

**Use osm2gmns for production converters** because:
- ✓ More complete GMNS specification compliance
- ✓ Better default values reduce manual configuration
- ✓ Geometry preservation improves accuracy
- ✓ Allowed uses directly support multi-modal conversion
- ✓ Professional tool maintained by research community

**Use OSMnx for rapid prototyping** when:
- Quick testing needed
- Simplified network sufficient
- Direct NetworkX integration required

---

## 3. Network Conversion (GMNS → MATSim network.xml)

### 3.1 Enhanced Mapping with osm2gmns Data

| GMNS Field (osm2gmns) | MATSim Field | Transformation | Priority |
|----------------------|--------------|----------------|----------|
| node_id | node.id | Direct | Required |
| x_coord | node.x | **CRS projection** | **CRITICAL** |
| y_coord | node.y | **CRS projection** | **CRITICAL** |
| link_id | link.id | Direct | Required |
| from_node_id | link.from | Direct | Required |
| to_node_id | link.to | Direct | Required |
| length | link.length | Validate (already meters) | Required |
| lanes | link.permlanes | Direct (osm2gmns fills defaults) | Required |
| capacity | link.capacity | Use osm2gmns values | Required |
| free_speed | link.freespeed | **Unit conversion (to m/s)** | Required |
| allowed_uses | link.modes | **Parse and map** | High |
| geometry | _(visualization only)_ | Store as metadata | Optional |
| name | _(metadata)_ | Store as attribute | Optional |

### 3.2 Coordinate Reference System Transformation

**Same as original plan** - this is still critical:

```python
from pyproj import Transformer

# For Manhattan/Brooklyn (NYC), use UTM Zone 18N
transformer = Transformer.from_crs("EPSG:4326", "EPSG:32618", always_xy=True)

# Transform all nodes
x_projected, y_projected = transformer.transform(
    nodes_df['x_coord'].values,
    nodes_df['y_coord'].values
)
```

**CRS Options**:
- **EPSG:32618** (UTM 18N) - Recommended for NYC
- **EPSG:2263** (NY State Plane) - Alternative (requires feet→meters)

### 3.3 Enhanced Mode Mapping with osm2gmns

osm2gmns provides `allowed_uses` field with explicit mode permissions:

```python
def map_allowed_uses_to_matsim_modes(allowed_uses_str, facility_type):
    """
    Map osm2gmns allowed_uses to MATSim modes

    Args:
        allowed_uses_str: e.g., "auto", "auto,bike", "walk"
        facility_type: e.g., "motorway", "primary", "residential"

    Returns:
        MATSim modes string (e.g., "car,bus")
    """
    if pd.isna(allowed_uses_str) or allowed_uses_str == '':
        # Use facility type as fallback
        return fallback_mode_mapping(facility_type)

    # Parse allowed_uses
    allowed = set(str(allowed_uses_str).split(','))

    matsim_modes = []

    # Map osm2gmns modes to MATSim modes
    if 'auto' in allowed:
        matsim_modes.append('car')
        # Add bus on major roads
        if facility_type in ['motorway', 'trunk', 'primary', 'secondary', 'tertiary']:
            matsim_modes.append('bus')

    if 'bike' in allowed:
        matsim_modes.append('bike')

    if 'walk' in allowed:
        matsim_modes.append('walk')

    return ','.join(matsim_modes) if matsim_modes else 'car'
```

### 3.4 Speed Unit Conversion

osm2gmns uses **km/h** for free_speed (not mph):

```python
def convert_speed_kmh_to_ms(speed_kmh):
    """Convert km/h to m/s for MATSim"""
    return speed_kmh * 0.277778  # 1 km/h = 0.277778 m/s

# Example: 40 km/h → 11.11 m/s
```

### 3.5 Network Conversion Summary (Enhanced)

**Input**: osm2gmns GMNS files (node.csv, link.csv)
**Output**: MATSim network.xml

**Key Improvements over OSMnx approach**:
1. ✓ Pre-filled lane counts and capacities
2. ✓ Type-specific speed defaults
3. ✓ Explicit mode restrictions
4. ✓ Geometry preservation for validation
5. ✓ Road names for debugging

---

## 4. Demand Conversion (grid2demand → MATSim population.xml)

### 4.1 Understanding the Input Data

**zone.csv** (Traffic Analysis Zones):
```csv
zone_id,x_coord,y_coord,longitude,latitude,poi_count,production,attraction
1,-74.011152625,40.70706084375,-74.011152625,40.70706084375,3748,3748.0,3748.0
```

**demand.csv** (OD Matrix):
```csv
o_zone_id,d_zone_id,volume
1,2,34152.41
1,3,2221.02
9,10,87341.52
```

**Interpretation**:
- `production`: Number of trip origins from this zone (person-trips/day)
- `attraction`: Number of trip destinations to this zone (person-trips/day)
- `volume`: Number of trips from origin zone to destination zone (person-trips/day)

### 4.2 Understanding MATSim Population Format

**population.xml Structure**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE population SYSTEM "http://www.matsim.org/files/dtd/population_v6.dtd">
<population>
  <person id="1">
    <plan selected="yes">
      <activity type="home" link="123" end_time="08:00:00" />
      <leg mode="car" />
      <activity type="work" link="456" end_time="17:00:00" />
      <leg mode="car" />
      <activity type="home" link="123" />
    </plan>
  </person>
  <!-- ... more persons ... -->
</population>
```

**Key Components**:
1. **Person** - Individual agent with unique ID
2. **Plan** - Daily activity chain (selected="yes")
3. **Activity** - Location (link) + purpose (type) + timing
4. **Leg** - Trip between activities with mode

### 4.3 Critical Challenge: OD Matrix Disaggregation

**Problem**:
- Input: Aggregate zone-to-zone flows (e.g., 34,152 trips from zone 1 to zone 2)
- Output: Individual agents with specific activities and timings

**MATSim Requirements**:
- Each agent needs specific link locations (not just zones)
- Each agent needs time-of-day schedules
- Each agent needs activity types (home, work, shopping, etc.)

### 4.4 Demand Conversion Strategy

#### Option 1: Simple Disaggregation (Recommended for Initial Implementation)

**Approach**: Create one round-trip per traveler with simple assumptions

```python
def create_simple_population(demand_df, zone_df, network):
    """
    Create simple population from OD matrix

    Assumptions:
    - Each OD pair represents commuters
    - Morning departure: 7-9 AM (normal distribution)
    - Evening return: 5-7 PM (normal distribution)
    - Activity types: home → work → home
    """

    persons = []
    person_id = 0

    for _, od_row in demand_df.iterrows():
        o_zone = od_row['o_zone_id']
        d_zone = od_row['d_zone_id']
        volume = od_row['volume']

        # Create individual agents for this OD pair
        num_agents = int(round(volume))  # Round to integer

        for i in range(num_agents):
            person_id += 1

            # Find network links in origin/destination zones
            home_link = get_random_link_in_zone(network, o_zone)
            work_link = get_random_link_in_zone(network, d_zone)

            # Generate departure times (7-9 AM with normal distribution)
            morning_depart = sample_departure_time(mean_hour=8, std_hour=0.5)
            evening_depart = sample_departure_time(mean_hour=17, std_hour=0.5)

            person = {
                'id': person_id,
                'home_link': home_link,
                'work_link': work_link,
                'morning_depart': morning_depart,
                'evening_depart': evening_depart,
                'mode': 'car'  # Default mode
            }
            persons.append(person)

    return persons
```

#### Option 2: Activity-Based Disaggregation (Advanced)

**Approach**: Use POI data and trip purpose inference

```python
def create_activity_based_population(demand_df, zone_df, poi_df, network):
    """
    Create realistic population using POI data

    Enhanced features:
    - Multiple trip purposes (home, work, shopping, education)
    - Activity duration distributions
    - Multi-modal choice based on distance
    - Realistic activity chains
    """

    persons = []
    person_id = 0

    for _, od_row in demand_df.iterrows():
        o_zone = od_row['o_zone_id']
        d_zone = od_row['d_zone_id']
        volume = od_row['volume']

        # Analyze POI types in destination zone
        dest_pois = poi_df[poi_df['zone_id'] == d_zone]
        trip_purpose = infer_trip_purpose(dest_pois)  # work, shopping, education, etc.

        # Distance-based mode choice
        distance = calculate_zone_distance(zone_df, o_zone, d_zone)
        mode = choose_mode_by_distance(distance)  # car for >5km, bike/walk for <2km

        # Purpose-specific timing
        departure_dist = get_departure_distribution(trip_purpose)
        duration_dist = get_duration_distribution(trip_purpose)

        num_agents = int(round(volume))

        for i in range(num_agents):
            person_id += 1

            # Sample origin/destination from zone POIs
            origin_link = sample_link_from_zone(network, o_zone, activity_type='home')
            dest_link = sample_link_from_zone(network, d_zone, activity_type=trip_purpose)

            # Generate timing
            depart_time = sample_time(departure_dist)
            duration = sample_time(duration_dist)

            person = create_person_with_plan(
                person_id, origin_link, dest_link,
                trip_purpose, depart_time, duration, mode
            )
            persons.append(person)

    return persons
```

### 4.5 Zone-to-Link Mapping

**Challenge**: MATSim requires specific link IDs, but demand is zone-based

**Solution Strategies**:

#### Strategy A: Random Link Selection
```python
def get_random_link_in_zone(network, zone_id, zone_df, node_df):
    """
    Select a random link within a zone boundary

    Steps:
    1. Find all nodes assigned to this zone
    2. Find all links with from_node or to_node in this zone
    3. Sample randomly (weighted by capacity for realism)
    """
    # Get nodes in this zone
    zone_nodes = node_df[node_df['zone_id'] == zone_id]['node_id'].tolist()

    if not zone_nodes:
        # Fallback: find nearest zone with nodes
        zone_centroid = zone_df[zone_df['zone_id'] == zone_id][['x_coord', 'y_coord']].iloc[0]
        zone_nodes = find_nearest_zone_nodes(node_df, zone_centroid)

    # Get links connected to these nodes
    zone_links = network[
        (network['from_node_id'].isin(zone_nodes)) |
        (network['to_node_id'].isin(zone_nodes))
    ]

    if len(zone_links) == 0:
        raise ValueError(f"No links found in zone {zone_id}")

    # Weight by capacity (busier roads more likely)
    weights = zone_links['capacity'].values / zone_links['capacity'].sum()
    selected_link = np.random.choice(zone_links['link_id'], p=weights)

    return selected_link
```

#### Strategy B: Zone Centroid Mapping
```python
def get_centroid_link(network, zone_id, zone_df):
    """
    Find the nearest link to zone centroid

    More deterministic than random selection
    Useful for debugging and reproducibility
    """
    zone_info = zone_df[zone_df['zone_id'] == zone_id].iloc[0]
    zone_x, zone_y = zone_info['x_coord'], zone_info['y_coord']

    # Calculate distance from zone centroid to all link midpoints
    network['midpoint_x'] = (network['from_node_x'] + network['to_node_x']) / 2
    network['midpoint_y'] = (network['from_node_y'] + network['to_node_y']) / 2

    network['distance_to_zone'] = np.sqrt(
        (network['midpoint_x'] - zone_x)**2 +
        (network['midpoint_y'] - zone_y)**2
    )

    # Return nearest link
    nearest_link = network.loc[network['distance_to_zone'].idxmin(), 'link_id']
    return nearest_link
```

### 4.6 Time-of-Day Distributions

**Realistic departure time sampling**:

```python
import numpy as np
from datetime import time

def sample_departure_time(mean_hour=8, std_hour=0.5, purpose='work'):
    """
    Sample realistic departure times

    Purpose-specific distributions:
    - work: 7-9 AM peak
    - school: 7-8 AM sharp peak
    - shopping: 10 AM - 8 PM spread
    - leisure: 6-10 PM peak
    """

    distributions = {
        'work': {'mean': 8, 'std': 0.5},      # 8 AM ± 30 min
        'school': {'mean': 7.5, 'std': 0.25},  # 7:30 AM ± 15 min
        'shopping': {'mean': 14, 'std': 2},    # 2 PM ± 2 hours
        'leisure': {'mean': 19, 'std': 1}      # 7 PM ± 1 hour
    }

    params = distributions.get(purpose, {'mean': mean_hour, 'std': std_hour})

    # Sample from normal distribution
    hour_float = np.random.normal(params['mean'], params['std'])

    # Clamp to reasonable bounds (5 AM - 11 PM)
    hour_float = np.clip(hour_float, 5, 23)

    # Convert to HH:MM:SS
    hours = int(hour_float)
    minutes = int((hour_float - hours) * 60)
    seconds = int(((hour_float - hours) * 60 - minutes) * 60)

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
```

### 4.7 Mode Choice Model

**Distance-based mode selection**:

```python
def choose_mode_by_distance(distance_km, has_car=True):
    """
    Simple distance-based mode choice

    Rules (typical urban behavior):
    - < 1 km: walk (80%), bike (20%)
    - 1-3 km: bike (40%), car (50%), pt (10%)
    - 3-10 km: car (60%), pt (40%)
    - > 10 km: car (70%), pt (30%)
    """

    if distance_km < 1:
        return np.random.choice(['walk', 'bike'], p=[0.8, 0.2])
    elif distance_km < 3:
        if has_car:
            return np.random.choice(['bike', 'car', 'pt'], p=[0.4, 0.5, 0.1])
        else:
            return np.random.choice(['bike', 'pt'], p=[0.7, 0.3])
    elif distance_km < 10:
        if has_car:
            return np.random.choice(['car', 'pt'], p=[0.6, 0.4])
        else:
            return 'pt'
    else:
        if has_car:
            return np.random.choice(['car', 'pt'], p=[0.7, 0.3])
        else:
            return 'pt'
```

### 4.8 Population XML Generation

```python
def write_matsim_population(persons, output_path):
    """
    Generate MATSim population.xml from person list
    """
    import xml.etree.ElementTree as ET
    from xml.dom import minidom

    # Create root
    root = ET.Element('population')

    for person_data in persons:
        person = ET.SubElement(root, 'person')
        person.set('id', str(person_data['id']))

        # Add attributes (optional)
        if 'car_avail' in person_data:
            attrs = ET.SubElement(person, 'attributes')
            attr = ET.SubElement(attrs, 'attribute')
            attr.set('name', 'carAvail')
            attr.set('class', 'java.lang.String')
            attr.text = person_data['car_avail']

        # Create plan
        plan = ET.SubElement(person, 'plan')
        plan.set('selected', 'yes')

        # Activity 1: Origin (home)
        act1 = ET.SubElement(plan, 'activity')
        act1.set('type', person_data['origin_type'])
        act1.set('link', str(person_data['origin_link']))
        act1.set('end_time', person_data['depart_time'])

        # Leg 1: Trip to destination
        leg1 = ET.SubElement(plan, 'leg')
        leg1.set('mode', person_data['mode'])

        # Activity 2: Destination (work/shop/etc)
        act2 = ET.SubElement(plan, 'activity')
        act2.set('type', person_data['dest_type'])
        act2.set('link', str(person_data['dest_link']))
        act2.set('end_time', person_data['return_time'])

        # Leg 2: Return trip
        leg2 = ET.SubElement(plan, 'leg')
        leg2.set('mode', person_data['mode'])

        # Activity 3: Return home
        act3 = ET.SubElement(plan, 'activity')
        act3.set('type', person_data['origin_type'])
        act3.set('link', str(person_data['origin_link']))
        # No end_time for final activity

    # Pretty print
    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")

    # Add DOCTYPE
    doctype = '<!DOCTYPE population SYSTEM "http://www.matsim.org/files/dtd/population_v6.dtd">'
    lines = xml_str.split('\n')
    lines.insert(1, doctype)
    xml_str = '\n'.join(lines)

    # Write file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(xml_str)

    print(f"✓ Population written: {output_path}")
    print(f"  Total persons: {len(persons):,}")
```

### 4.9 Demand Conversion Validation

```python
def validate_demand_conversion(original_demand_df, generated_population):
    """
    Validate that generated population preserves OD flows
    """

    # Extract trips from population
    generated_trips = []
    for person in generated_population:
        trip = {
            'o_zone': get_zone_from_link(person['origin_link']),
            'd_zone': get_zone_from_link(person['dest_link'])
        }
        generated_trips.append(trip)

    generated_od = pd.DataFrame(generated_trips).groupby(
        ['o_zone', 'd_zone']
    ).size().reset_index(name='generated_volume')

    # Compare with original
    comparison = original_demand_df.merge(
        generated_od,
        left_on=['o_zone_id', 'd_zone_id'],
        right_on=['o_zone', 'd_zone'],
        how='outer'
    )

    comparison['error'] = comparison['generated_volume'] - comparison['volume']
    comparison['pct_error'] = (comparison['error'] / comparison['volume']) * 100

    print("Demand Validation Report:")
    print(f"  Total original trips: {original_demand_df['volume'].sum():,.0f}")
    print(f"  Total generated agents: {len(generated_population):,}")
    print(f"  Mean error: {comparison['error'].mean():.2f} trips/OD pair")
    print(f"  RMSE: {np.sqrt((comparison['error']**2).mean()):.2f}")
    print(f"  Max error: {comparison['error'].abs().max():.0f}")

    return comparison
```

### 4.10 Key Considerations for Demand Conversion

**Scaling Factors**:
- Grid2demand volumes may represent daily, peak-hour, or other periods
- MATSim simulates 24-hour day by default
- May need to scale volumes: `agents = volume * scaling_factor`
- Typical scaling: 1% to 10% sample for large cities

**Activity Chains**:
- Simple approach: home → work → home (round trips)
- Realistic approach: home → work → shop → home (multi-stage)
- Advanced: use trip purpose inference from POI types

**Temporal Distribution**:
- Not all trips happen simultaneously
- Use time-of-day curves (AM peak, PM peak, off-peak)
- Sample departure times from distributions

**Spatial Distribution**:
- Within-zone variation matters for large zones
- Random link selection adds spatial diversity
- Capacity-weighted sampling = more realistic

---

## 5. Complete Converter Architecture

### 5.1 Module Structure

```
gmns_matsim_converter/
├── __init__.py
├── network/
│   ├── __init__.py
│   ├── network_converter.py      # Network conversion orchestration
│   ├── coordinate_transformer.py # CRS transformations
│   ├── unit_converter.py         # Speed, distance units
│   ├── mode_mapper.py            # OSM → MATSim modes
│   └── xml_writer.py             # MATSim network.xml generation
├── demand/
│   ├── __init__.py
│   ├── demand_converter.py       # Demand conversion orchestration
│   ├── disaggregator.py          # OD matrix → individual agents
│   ├── zone_mapper.py            # Zone → link mapping
│   ├── time_sampler.py           # Departure time distributions
│   ├── mode_choice.py            # Mode selection logic
│   └── population_writer.py      # MATSim population.xml generation
├── validation/
│   ├── __init__.py
│   ├── network_validator.py      # Network QA checks
│   ├── demand_validator.py       # Demand conservation checks
│   └── report_generator.py       # Validation reports
├── utils/
│   ├── __init__.py
│   ├── config.py                 # Configuration parameters
│   ├── logger.py                 # Logging utilities
│   └── spatial.py                # Spatial analysis helpers
└── cli.py                        # Command-line interface
```

### 5.2 Main Converter Class

```python
class GMNSMATSimConverter:
    """
    Complete converter from GMNS + grid2demand to MATSim scenario

    Inputs:
        - node.csv (GMNS network nodes)
        - link.csv (GMNS network links)
        - zone.csv (grid2demand zones)
        - demand.csv (grid2demand OD matrix)

    Outputs:
        - network.xml (MATSim network)
        - population.xml (MATSim agents)
        - validation_report.txt (QA summary)
    """

    def __init__(self, config):
        self.config = config
        self.network_converter = NetworkConverter(config)
        self.demand_converter = DemandConverter(config)
        self.validator = Validator(config)

    def convert(self, input_dir, output_dir):
        """
        Complete conversion workflow

        Steps:
        1. Load GMNS network files
        2. Load grid2demand zone and demand files
        3. Convert network to MATSim format
        4. Convert demand to MATSim population
        5. Validate outputs
        6. Generate reports
        """

        print("="*60)
        print("GMNS + grid2demand → MATSim Converter")
        print("="*60)

        # 1. Load network data
        print("\n[1/6] Loading network data...")
        network_data = self.load_network_data(input_dir)

        # 2. Load demand data
        print("\n[2/6] Loading demand data...")
        demand_data = self.load_demand_data(input_dir)

        # 3. Convert network
        print("\n[3/6] Converting network to MATSim format...")
        network_xml_path = os.path.join(output_dir, 'network.xml')
        network_result = self.network_converter.convert(
            network_data,
            network_xml_path
        )

        # 4. Convert demand (requires network for zone-link mapping)
        print("\n[4/6] Converting demand to MATSim population...")
        population_xml_path = os.path.join(output_dir, 'population.xml')
        population_result = self.demand_converter.convert(
            demand_data,
            network_result,
            population_xml_path
        )

        # 5. Validate
        print("\n[5/6] Validating conversion...")
        validation_results = self.validator.validate_all(
            network_data, demand_data,
            network_result, population_result
        )

        # 6. Generate report
        print("\n[6/6] Generating validation report...")
        report_path = os.path.join(output_dir, 'conversion_report.txt')
        self.generate_report(validation_results, report_path)

        print("\n" + "="*60)
        print("✓ Conversion complete!")
        print(f"  Network:    {network_xml_path}")
        print(f"  Population: {population_xml_path}")
        print(f"  Report:     {report_path}")
        print("="*60)

        return {
            'network': network_result,
            'population': population_result,
            'validation': validation_results
        }
```

---

## 6. Implementation Workflow

### 6.1 Phase 1: Network Converter (Weeks 1-2)

**Tasks**:
- [x] Research and planning (completed)
- [ ] Implement coordinate transformation module
- [ ] Implement unit conversion utilities
- [ ] Implement mode mapper (with osm2gmns support)
- [ ] Implement network XML writer
- [ ] Unit tests for network conversion

**Deliverable**: Working network.xml generator

### 6.2 Phase 2: Basic Demand Converter (Weeks 3-4)

**Tasks**:
- [ ] Implement simple disaggregation (Option 1)
- [ ] Implement zone-to-link random mapping
- [ ] Implement time-of-day sampling
- [ ] Implement basic population XML writer
- [ ] Validate demand conservation
- [ ] Integration tests with real data

**Deliverable**: Working population.xml generator (simple mode)

### 6.3 Phase 3: Enhanced Demand Converter (Week 5)

**Tasks**:
- [ ] Implement activity-based disaggregation (Option 2)
- [ ] Implement POI-based trip purpose inference
- [ ] Implement distance-based mode choice
- [ ] Implement multi-stop activity chains
- [ ] Advanced validation and reporting

**Deliverable**: Production-ready converter with realistic agent behavior

### 6.4 Phase 4: Integration and Testing (Week 6)

**Tasks**:
- [ ] End-to-end testing with multiple datasets
- [ ] MATSim compatibility testing (load and run scenarios)
- [ ] Performance optimization
- [ ] Documentation and examples
- [ ] CLI interface

**Deliverable**: Complete, tested, documented converter

---

## 7. Testing and Validation

### 7.1 Network Validation Tests

```python
def test_network_conversion():
    """Test network.xml generation"""

    # Test coordinate transformation
    assert_coordinate_transformation_accurate()

    # Test unit conversions
    assert_speed_conversion_correct()
    assert_capacity_values_reasonable()

    # Test topology
    assert_no_orphan_links()
    assert_no_duplicate_nodes()

    # Test MATSim compatibility
    assert_xml_validates_against_dtd()
    assert_matsim_can_load_network()
```

### 7.2 Demand Validation Tests

```python
def test_demand_conversion():
    """Test population.xml generation"""

    # Test trip conservation
    assert_total_trips_preserved()
    assert_od_flows_preserved(tolerance=0.05)  # 5% error allowed

    # Test spatial distribution
    assert_all_zones_have_agents()
    assert_agent_locations_valid()

    # Test temporal distribution
    assert_departure_times_reasonable()
    assert_activity_durations_realistic()

    # Test MATSim compatibility
    assert_xml_validates_against_dtd()
    assert_matsim_can_load_population()
```

### 7.3 Integration Testing

```python
def test_complete_scenario():
    """Test complete MATSim scenario"""

    # Convert full dataset
    converter.convert('input_data/', 'output_scenario/')

    # Load in MATSim
    matsim_scenario = load_matsim_scenario('output_scenario/')

    # Run 1 iteration
    matsim_scenario.run(iterations=1)

    # Check results
    assert_simulation_completed_successfully()
    assert_all_agents_have_plans()
    assert_link_volumes_reasonable()
```

---

## 8. Usage Examples

### 8.1 Basic Conversion (OSMnx data)

```python
from gmns_matsim_converter import GMNSMATSimConverter

# Initialize converter
converter = GMNSMATSimConverter(
    source_crs='EPSG:4326',
    target_crs='EPSG:32618',  # UTM 18N for NYC
    network_name='manhattan',
    demand_mode='simple'       # Simple disaggregation
)

# Convert
converter.convert(
    input_dir='manhattan_network_data/',
    output_dir='matsim_scenario_manhattan/'
)
```

**Output**:
```
============================================================
GMNS + grid2demand → MATSim Converter
============================================================

[1/6] Loading network data...
  ✓ Loaded 4,619 nodes
  ✓ Loaded 9,901 links
  ✓ Loaded 128 zones
  ✓ Loaded 4,154 OD pairs

[2/6] Loading demand data...
  ✓ Total demand: 1,234,567 trips/day

[3/6] Converting network to MATSim format...
  ✓ Transformed coordinates (EPSG:4326 → EPSG:32618)
  ✓ Converted 9,901 links
  ✓ Speed range: 11.1 to 33.3 m/s
  ✓ Mode distribution:
      car: 3,500 links (35.4%)
      car,bus: 4,000 links (40.4%)
      car,bike: 2,401 links (24.2%)

[4/6] Converting demand to MATSim population...
  ✓ Generated 123,457 agents (10% sample)
  ✓ Departure time range: 05:00:00 to 23:59:59
  ✓ Mode distribution:
      car: 85,720 agents (69.4%)
      pt: 24,691 agents (20.0%)
      bike: 12,346 agents (10.0%)
      walk: 700 agents (0.6%)

[5/6] Validating conversion...
  ✓ Network topology valid
  ✓ OD flows preserved (RMSE: 12.3 trips, 0.3% error)
  ✓ All zones have agents

[6/6] Generating validation report...

============================================================
✓ Conversion complete!
  Network:    matsim_scenario_manhattan/network.xml
  Population: matsim_scenario_manhattan/population.xml
  Report:     matsim_scenario_manhattan/conversion_report.txt
============================================================
```

### 8.2 Advanced Conversion (osm2gmns data)

```python
from gmns_matsim_converter import GMNSMATSimConverter

# Advanced configuration
config = {
    'crs': {
        'source': 'EPSG:4326',
        'target': 'EPSG:32618'
    },
    'network': {
        'name': 'brooklyn',
        'use_osm2gmns_geometry': True,
        'mode_mapping': 'auto'  # Use allowed_uses field
    },
    'demand': {
        'mode': 'activity_based',  # Enhanced disaggregation
        'scaling_factor': 0.1,      # 10% sample
        'use_poi_inference': True,
        'time_distribution': 'realistic',
        'mode_choice': 'distance_based'
    },
    'validation': {
        'od_tolerance': 0.05,  # 5% error allowed
        'generate_plots': True
    }
}

converter = GMNSMATSimConverter(config)

# Convert osm2gmns output
converter.convert(
    input_dir='network_data_testing/',  # osm2gmns output
    output_dir='matsim_scenario_brooklyn/'
)
```

### 8.3 Command-Line Interface

```bash
# Basic usage
python -m gmns_matsim_converter \
    --input manhattan_network_data/ \
    --output matsim_scenario/ \
    --crs EPSG:32618 \
    --network-name manhattan

# Advanced usage
python -m gmns_matsim_converter \
    --input network_data_testing/ \
    --output matsim_scenario/ \
    --crs EPSG:32618 \
    --network-name brooklyn \
    --demand-mode activity_based \
    --scaling-factor 0.1 \
    --use-poi-inference \
    --mode-choice distance_based \
    --validation-plots
```

### 8.4 Batch Processing

```python
# Convert multiple cities
cities = [
    {'name': 'manhattan', 'crs': 'EPSG:32618', 'input': 'manhattan_network_data/'},
    {'name': 'brooklyn', 'crs': 'EPSG:32618', 'input': 'brooklyn_network_data/'},
    {'name': 'queens', 'crs': 'EPSG:32618', 'input': 'queens_network_data/'}
]

for city in cities:
    print(f"\n{'='*60}")
    print(f"Processing: {city['name']}")
    print('='*60)

    converter = GMNSMATSimConverter(
        target_crs=city['crs'],
        network_name=city['name']
    )

    converter.convert(
        input_dir=city['input'],
        output_dir=f"matsim_scenarios/{city['name']}/"
    )
```

---

## 9. Key Recommendations

### 9.1 Data Source Selection

**Recommendation: Use osm2gmns for production**

| Criteria | OSMnx | osm2gmns | Winner |
|----------|-------|----------|--------|
| Data completeness | Basic | Comprehensive | osm2gmns |
| Default values | Manual | Intelligent | osm2gmns |
| Geometry | Missing | Full WKT | osm2gmns |
| Mode restrictions | Inferred | Explicit | osm2gmns |
| Setup complexity | Simple | Moderate | OSMnx |

**Use osm2gmns unless**:
- Quick prototype needed
- Simplified network acceptable
- Integration with NetworkX required

### 9.2 Demand Conversion Approach

**For initial implementation**: Simple disaggregation (Option 1)
- Faster development
- Easier validation
- Sufficient for many studies

**For realistic simulations**: Activity-based disaggregation (Option 2)
- Better behavioral realism
- Proper mode choice
- Realistic time distributions

### 9.3 Scaling Considerations

**Large networks (>50k links)**:
- Use 1-10% demand sample
- Consider spatial subsets
- Optimize zone-link mapping (KD-tree)

**Small networks (<10k links)**:
- Use 100% demand
- Full detail simulation
- Better calibration

---

## 10. Dependencies and Requirements

### 10.1 Python Libraries

```python
# requirements.txt
pandas>=1.5.0           # Data manipulation
numpy>=1.23.0           # Numerical operations
pyproj>=3.4.0           # Coordinate transformations
geopandas>=0.12.0       # Spatial data handling
shapely>=2.0.0          # Geometry operations
lxml>=4.9.0             # XML parsing
scipy>=1.9.0            # Statistical distributions
matplotlib>=3.6.0       # Visualization (optional)

# Data sources
osmnx>=1.3.0            # OSM network download (Option A)
osm2gmns>=1.0.0         # OSM to GMNS conversion (Option B - recommended)
grid2demand>=0.1.0      # Demand matrix generation

# Testing
pytest>=7.2.0
```

### 10.2 System Requirements

- **Python**: 3.8 or higher
- **Memory**: 8GB RAM (for large cities like NYC)
- **Disk**: ~1GB for typical city network + demand
- **OS**: Platform-independent

---

## 11. Known Limitations and Future Work

### 11.1 Current Limitations

1. **Simple Activity Chains**
   - Basic implementation: home-work-home only
   - Real behavior: complex multi-stop tours

2. **Static Network**
   - No time-of-day capacity changes
   - No construction/closures

3. **Simplified Mode Choice**
   - Distance-based only
   - No socioeconomic factors
   - No public transit schedules

4. **Aggregate Zones**
   - Large zones = coarse spatial resolution
   - May not capture local patterns

### 11.2 Future Enhancements

**Phase 2 Features** (demand):
- [ ] Multi-stop activity chains
- [ ] Socioeconomic-based mode choice
- [ ] Public transit integration (GTFS → MATSim transit schedule)
- [ ] Within-zone spatial distribution models

**Phase 3 Features** (network):
- [ ] Time-varying link capacities
- [ ] Turn restrictions from OSM
- [ ] Signal timing integration
- [ ] Multi-resolution networks (osm2gmns micro/meso)

**Phase 4 Features** (advanced):
- [ ] Synthetic population integration
- [ ] Activity-based model integration
- [ ] Calibration tools
- [ ] Scenario comparison utilities

---

## 12. Success Criteria

### 12.1 Network Conversion

- [x] Research complete
- [ ] Convert network with 100% node/link preservation
- [ ] Accurate coordinate transformation (< 1m error)
- [ ] Correct unit conversions (speed, capacity)
- [ ] Valid MATSim XML (DTD compliance)
- [ ] MATSim loads network without errors

### 12.2 Demand Conversion

- [x] Research complete
- [ ] Generate agents for all OD pairs
- [ ] Preserve total trip volumes (< 5% error)
- [ ] Preserve OD flow distribution (< 10% RMSE)
- [ ] Realistic departure time distributions
- [ ] Valid MATSim population XML
- [ ] MATSim simulates scenario successfully

### 12.3 End-to-End

- [ ] Complete Brooklyn or Manhattan scenario
- [ ] MATSim runs 10 iterations without crashes
- [ ] Reasonable link volumes (compared to input demand)
- [ ] Comprehensive documentation
- [ ] Example notebooks and CLI

---

## 13. References

### 13.1 GMNS and Data Sources

- **GMNS Specification**: https://github.com/zephyr-data-specs/GMNS
- **osm2gmns Documentation**: https://osm2gmns.readthedocs.io/
- **OSMnx Documentation**: https://osmnx.readthedocs.io/
- **grid2demand**: https://github.com/asu-trans-ai-lab/grid2demand

### 13.2 MATSim

- **MATSim Website**: https://matsim.org/
- **MATSim User Guide**: https://matsim.org/docs/userguide
- **MATSim DTD Files**: http://www.matsim.org/files/dtd/
- **MATSim Examples**: https://github.com/matsim-org/matsim-code-examples

### 13.3 Coordinate Systems

- **EPSG:4326 (WGS84)**: https://epsg.io/4326
- **EPSG:32618 (UTM 18N)**: https://epsg.io/32618
- **Pyproj Documentation**: https://pyproj4.github.io/pyproj/

---

## Document Control

- **Version**: 2.0 (Extended with demand conversion)
- **Status**: Planning Complete - Ready for Implementation
- **Author**: Claude Code Research
- **Date**: 2025-11-19
- **Previous Version**: [gmns_to_matsim_conversion_plan.md](gmns_to_matsim_conversion_plan.md)

---

## Appendix A: Data Format Examples

### A.1 osm2gmns Link CSV (Enhanced)

```csv
link_id,name,osm_way_id,from_node_id,to_node_id,directed,geometry,dir_flag,length,facility_type,link_type,free_speed,lanes,capacity,allowed_uses,notes
1,Boerum Place,5029221,1,2,1,"LINESTRING (-73.9891992 40.6910987, -73.9891327 40.6913611)",1,29.71,primary,3,40,3,,auto,
```

### A.2 grid2demand Zone CSV

```csv
zone_id,x_coord,y_coord,longitude,latitude,poi_count,production,attraction
1,-74.011152625,40.70706084375,-74.011152625,40.70706084375,3748,3748.0,3748.0
```

### A.3 grid2demand Demand CSV

```csv
o_zone_id,d_zone_id,volume
1,2,34152.41
1,3,2221.02
```

### A.4 MATSim network.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE network SYSTEM "http://www.matsim.org/files/dtd/network_v1.dtd">
<network name="brooklyn">
  <nodes>
    <node id="1" x="585234.123" y="4515678.234"/>
  </nodes>
  <links capperiod="01:00:00">
    <link id="1" from="1" to="2" length="29.71" freespeed="11.11"
          capacity="5400.0" permlanes="3.0" modes="car,bus"/>
  </links>
</network>
```

### A.5 MATSim population.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE population SYSTEM "http://www.matsim.org/files/dtd/population_v6.dtd">
<population>
  <person id="1">
    <plan selected="yes">
      <activity type="home" link="123" end_time="08:15:30"/>
      <leg mode="car"/>
      <activity type="work" link="456" end_time="17:30:00"/>
      <leg mode="car"/>
      <activity type="home" link="123"/>
    </plan>
  </person>
</population>
```

---

**End of Document**
