# GMNS to MATSim Network Conversion Plan

## Executive Summary

This document outlines a comprehensive plan to build a custom converter from GMNS (General Modeling Network Specification) format to MATSim network XML format. The converter will transform the existing GMNS-compatible network data (node.csv, link.csv) into MATSim-compatible network.xml files for agent-based traffic simulation.

**Status**: Planning Phase
**Date**: 2025-11-19
**Project**: Custom Transportation Network Converter

---

## 1. Overview of Format Specifications

### 1.1 GMNS Format (Source)

GMNS is a CSV-based, human and machine-readable format for sharing routable road network files. Based on the current Manhattan dataset:

**node.csv Structure**:
```csv
node_id,osm_node_id,x_coord,y_coord,longitude,latitude,activity_type,is_boundary,zone_id
```

| Field | Data Type | Required | Description | Example |
|-------|-----------|----------|-------------|---------|
| node_id | integer | Yes | Unique sequential node identifier | 0, 1, 2, ... |
| osm_node_id | integer | No | Original OpenStreetMap node ID | 42421728 |
| x_coord | float | Yes | X coordinate (currently WGS84 longitude) | -73.9600437 |
| y_coord | float | Yes | Y coordinate (currently WGS84 latitude) | 40.7980478 |
| longitude | float | No | WGS84 longitude | -73.9600437 |
| latitude | float | No | WGS84 latitude | 40.7980478 |
| activity_type | string | No | Node type classification | "node" |
| is_boundary | integer | No | Boundary node flag | 0 or 1 |
| zone_id | integer | No | Associated traffic analysis zone | -1 (unassigned) |

**Current Data Stats**:
- **Nodes**: 4,619 intersection points
- **Coordinate System**: WGS84 (EPSG:4326) - decimal degrees

**link.csv Structure**:
```csv
link_id,from_node_id,to_node_id,length,lanes,capacity,free_speed,link_type,geometry
```

| Field | Data Type | Required | Description | Example |
|-------|-----------|----------|-------------|---------|
| link_id | integer | Yes | Unique sequential link identifier | 0, 1, 2, ... |
| from_node_id | integer | Yes | Origin node reference | 0 |
| to_node_id | integer | Yes | Destination node reference | 1298 |
| length | float | Yes | Link length in meters | 85.345 |
| lanes | integer | Yes | Number of lanes | 1, 2, 3, 4 |
| capacity | integer | Yes | Flow capacity (veh/hour) | 1800, 3600, 5400, 7200 |
| free_speed | float | Yes | Maximum speed (mph) | 35 |
| link_type | string | No | OSM highway classification | "secondary", "primary", "residential", "tertiary" |
| geometry | string | No | WKT geometry (currently empty) | "" |

**Current Data Stats**:
- **Links**: 9,901 directed edges
- **Capacity Calculation**: lanes × 1800 veh/hour/lane
- **Default Free Speed**: 35 mph
- **Network Type**: Directed graph (unidirectional links)

### 1.2 MATSim Format (Target)

MATSim uses XML format with DTD validation for network representation.

**network.xml Structure**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE network SYSTEM "http://www.matsim.org/files/dtd/network_v1.dtd">
<network name="network_name">
  <nodes>
    <node id="NODE_ID" x="X_COORD" y="Y_COORD" />
  </nodes>
  <links capperiod="01:00:00">
    <link id="LINK_ID" from="FROM_NODE" to="TO_NODE"
          length="LENGTH_M" freespeed="SPEED_M_S"
          capacity="CAP_VEH_HR" permlanes="LANES"
          modes="car" />
  </links>
</network>
```

**Node Attributes**:
| Attribute | Data Type | Required | Description | Units |
|-----------|-----------|----------|-------------|-------|
| id | string/int | Yes | Unique node identifier | - |
| x | float | Yes | X coordinate in projected CRS | meters (projected) |
| y | float | Yes | Y coordinate in projected CRS | meters (projected) |

**Link Attributes**:
| Attribute | Data Type | Required | Description | Units |
|-----------|-----------|----------|-------------|-------|
| id | string/int | Yes | Unique link identifier | - |
| from | string/int | Yes | Origin node ID reference | - |
| to | string/int | Yes | Destination node ID reference | - |
| length | float | Yes | Link length | meters |
| freespeed | float | Yes | Maximum speed | meters/second |
| capacity | float | Yes | Flow capacity | vehicles/hour |
| permlanes | float | Yes | Number of lanes | count (can be decimal) |
| modes | string | No | Allowed transport modes (comma-separated) | Default: "car" |

**Key Requirements**:
- **Coordinate System**: MUST use projected coordinate system (meters), NOT WGS84
- **Speed Units**: meters per second (NOT mph)
- **Unidirectional Links**: Same as GMNS (already compatible)
- **DTD Validation**: Output must conform to network_v1.dtd or network_v2.dtd

---

## 2. Conversion Mapping

### 2.1 Direct Field Mappings

| GMNS Field | MATSim Field | Transformation Required | Notes |
|------------|--------------|-------------------------|-------|
| node.node_id | node.id | None | Direct integer mapping |
| node.x_coord | node.x | **Coordinate Projection** | Must convert WGS84 → projected CRS |
| node.y_coord | node.y | **Coordinate Projection** | Must convert WGS84 → projected CRS |
| link.link_id | link.id | None | Direct integer mapping |
| link.from_node_id | link.from | None | Direct reference mapping |
| link.to_node_id | link.to | None | Direct reference mapping |
| link.length | link.length | Validation | Already in meters (verify) |
| link.lanes | link.permlanes | None | Direct integer mapping |
| link.capacity | link.capacity | Validation | Already in veh/hr (verify) |
| link.free_speed | link.freespeed | **Unit Conversion** | Convert mph → m/s |

### 2.2 Calculated/Derived Fields

| MATSim Field | Source | Calculation | Default Value |
|--------------|--------|-------------|---------------|
| link.modes | link.link_type | Map OSM highway types → transport modes | "car" |
| network.name | - | User-defined or derived from filename | "manhattan_network" |
| links.capperiod | - | Standard MATSim parameter | "01:00:00" |

---

## 3. Critical Conversion Issues and Solutions

### 3.1 **CRITICAL: Coordinate Reference System (CRS) Mismatch**

**Issue**:
- GMNS data uses WGS84 (EPSG:4326) - geographic coordinates in decimal degrees
- MATSim REQUIRES projected coordinates in meters for distance calculations
- Current x_coord/y_coord values are identical to longitude/latitude (both in degrees)

**Impact**:
- MATSim will produce incorrect distance/speed/travel time calculations
- Network topology will be distorted
- Simulation results will be invalid

**Solution**:
```python
# Use pyproj for coordinate transformation
from pyproj import Transformer

# For Manhattan, NY, use appropriate UTM zone (Zone 18N)
# EPSG:32618 = WGS 84 / UTM zone 18N
transformer = Transformer.from_crs("EPSG:4326", "EPSG:32618", always_xy=True)

# Transform coordinates
x_projected, y_projected = transformer.transform(longitude, latitude)
```

**Recommended CRS for Manhattan**:
- **UTM Zone 18N (EPSG:32618)**: Most accurate for Manhattan
- **NAD83 / New York Long Island (EPSG:2263)**: State Plane alternative (US Survey Feet - requires conversion to meters)
- **Web Mercator (EPSG:3857)**: Less accurate but widely supported

**Implementation Priority**: **CRITICAL** - Must be implemented first

---

### 3.2 Speed Unit Conversion

**Issue**:
- GMNS stores free_speed in mph (35 mph default)
- MATSim requires freespeed in meters/second

**Conversion Formula**:
```python
speed_m_s = speed_mph * 0.44704
# Example: 35 mph * 0.44704 = 15.6464 m/s
```

**Validation Check**:
- Verify GMNS speed unit assumption by checking realistic speed ranges
- Check if speed values are already in m/s (unlikely given value of 35)

---

### 3.3 Missing Transport Mode Information

**Issue**:
- MATSim uses `modes` attribute to specify allowed transport types (car, bus, bike, walk, etc.)
- GMNS link_type contains OSM highway classifications (primary, secondary, residential, tertiary)
- Direct mapping between link_type and modes is not standardized

**Current Data Distribution**:
```
Estimated link_type distribution in Manhattan dataset:
- primary: Major arterials (multi-lane, higher capacity)
- secondary: Important through streets
- residential: Local neighborhood streets
- tertiary: Minor through streets
```

**Proposed Mapping Strategy**:

| GMNS link_type | MATSim modes | Rationale |
|----------------|--------------|-----------|
| motorway, trunk, primary | "car" | High-speed, car-only facilities |
| secondary, tertiary | "car,bus" | Major streets with transit |
| residential, living_street | "car,bike" | Low-speed, multi-modal access |
| service, unclassified | "car" | Service roads, default car access |
| cycleway | "bike" | Dedicated cycling infrastructure |
| footway, pedestrian, path | "walk" | Pedestrian facilities |
| (missing/unknown) | "car" | Conservative default |

**Advanced Option**:
- Analyze OSM tags if available in original data (osm_node_id reference)
- Use lane count and capacity as proxy:
  - ≥3 lanes + high capacity → car-only
  - 1-2 lanes + low capacity → multi-modal

**Implementation**:
```python
def map_link_type_to_modes(link_type, lanes, capacity):
    """Map GMNS link_type to MATSim modes"""
    mode_mapping = {
        'motorway': 'car',
        'trunk': 'car',
        'primary': 'car',
        'secondary': 'car,bus',
        'tertiary': 'car,bus',
        'residential': 'car,bike',
        'living_street': 'car,bike',
        'service': 'car',
        'cycleway': 'bike',
        'footway': 'walk',
        'pedestrian': 'walk',
        'path': 'walk'
    }

    modes = mode_mapping.get(link_type, 'car')  # Default to car

    # Additional logic based on capacity/lanes
    if lanes >= 3 and capacity >= 5400:
        modes = 'car'  # High-capacity facilities

    return modes
```

---

### 3.4 Empty Geometry Field

**Issue**:
- GMNS link.geometry field is empty in current dataset
- MATSim does not require explicit geometry (uses straight-line between nodes)
- May lose information about curved roads

**Impact**:
- **Low** - MATSim will assume straight-line links between nodes
- Link length is preserved, so travel time calculations remain accurate
- Visualization may show simplified network topology

**Solution Options**:
1. **Accept straight-line approximation** (recommended for initial implementation)
   - MATSim can function perfectly without curved geometry
   - Actual travel distances preserved in link.length field

2. **Add intermediate nodes for curved links** (advanced, future enhancement)
   - Parse geometry WKT if available
   - Insert intermediate nodes along curves
   - Split single link into multiple segments

**Recommendation**: Proceed with Option 1 for initial converter

---

### 3.5 Link Length Validation

**Issue**:
- Coordinate projection changes distances
- GMNS length may be calculated in WGS84 (degrees) or already in meters
- Need to verify and potentially recalculate after projection

**Solution**:
```python
from shapely.geometry import Point
from pyproj import Geod

def validate_and_recalculate_length(from_node, to_node, stated_length, tolerance=0.1):
    """
    Validate link length after CRS transformation
    tolerance: acceptable deviation (10% default)
    """
    # Calculate geodesic distance in meters
    geod = Geod(ellps='WGS84')
    _, _, distance = geod.inv(
        from_node['x'], from_node['y'],
        to_node['x'], to_node['y']
    )

    # Check if stated length is reasonable
    if abs(distance - stated_length) / distance > tolerance:
        print(f"Warning: Length mismatch - Stated: {stated_length}m, Calculated: {distance}m")
        return distance  # Use calculated distance

    return stated_length
```

**Recommendation**:
- Validate sample of links during initial conversion
- If systematic error detected, recalculate all lengths
- Add validation flag to converter output

---

### 3.6 Capacity Calculation Formula

**Issue**:
- Current GMNS capacity = lanes × 1800 veh/hr/lane
- MATSim typical capacity = lanes × 2000 veh/hr/lane (can vary)
- Need to verify if 1800 is appropriate for Manhattan urban environment

**Analysis**:
- 1800 veh/hr/lane is reasonable for urban streets with signals
- Highway Capacity Manual suggests 1900-2000 for uninterrupted flow
- Manhattan's signalized intersections justify 1800 or lower

**Solution**:
- **Accept existing capacity values** (already appropriate)
- Add option to recalculate with custom saturation flow rate
- Document assumption in converter metadata

---

### 3.7 Network Name and Metadata

**Issue**:
- MATSim network.xml requires `name` attribute
- No equivalent field in GMNS

**Solution**:
```python
# Derive from input filename or allow user specification
network_name = "manhattan_network"  # or from file: "manhattan_network_data"
```

**Additional Metadata to Track**:
- Source CRS (EPSG:4326)
- Target CRS (EPSG:32618 or user-specified)
- Conversion timestamp
- Converter version
- Data source attribution (OpenStreetMap)

---

### 3.8 Node Type and Control Type

**Issue**:
- MATSim nodes can have optional `type` attribute
- GMNS has activity_type field (currently all "node")
- No traffic control information (signals, stop signs)

**Impact**:
- **Low** - MATSim does not require node type for basic simulation
- Traffic signal information would enhance realism but is not critical

**Solution**:
- Omit node type attribute (optional in MATSim)
- Future enhancement: Add signal timing data from separate source
- Document limitation in converter output

---

## 4. Converter Architecture

### 4.1 Proposed Module Structure

```
gmns_to_matsim/
├── __init__.py
├── converter.py              # Main conversion orchestration
├── coordinate_transformer.py # CRS transformation utilities
├── unit_converter.py         # Speed, distance unit conversions
├── mode_mapper.py            # Link type → transport mode mapping
├── validators.py             # Data validation and QA checks
├── xml_writer.py             # MATSim XML generation
└── config.py                 # Conversion parameters and defaults
```

### 4.2 Core Converter Class

```python
class GMNSToMATSimConverter:
    """
    Convert GMNS network format to MATSim network.xml

    Attributes:
        source_crs (str): Source coordinate system (default: EPSG:4326)
        target_crs (str): Target projected CRS (required for MATSim)
        network_name (str): Name for MATSim network
        capacity_multiplier (float): Adjustment factor for link capacity
        speed_unit (str): 'mph' or 'm/s' for GMNS free_speed field
    """

    def __init__(self, source_crs='EPSG:4326', target_crs='EPSG:32618',
                 network_name='network', speed_unit='mph'):
        self.source_crs = source_crs
        self.target_crs = target_crs
        self.network_name = network_name
        self.speed_unit = speed_unit
        self.transformer = self._init_transformer()
        self.validation_report = {}

    def convert(self, node_csv_path, link_csv_path, output_xml_path):
        """
        Main conversion workflow

        Steps:
        1. Load GMNS node.csv and link.csv
        2. Validate input data
        3. Transform node coordinates
        4. Convert link attributes
        5. Map transport modes
        6. Generate MATSim XML
        7. Validate output
        8. Write network.xml file
        """
        # Implementation details in next section
        pass
```

### 4.3 Conversion Workflow

```python
def convert(self, node_csv_path, link_csv_path, output_xml_path):
    """Detailed conversion workflow"""

    # 1. Load GMNS data
    print("Loading GMNS network data...")
    nodes_df = pd.read_csv(node_csv_path)
    links_df = pd.read_csv(link_csv_path)

    # 2. Validate input data
    print("Validating input data...")
    self._validate_gmns_data(nodes_df, links_df)

    # 3. Transform node coordinates (CRITICAL)
    print(f"Transforming coordinates from {self.source_crs} to {self.target_crs}...")
    nodes_df = self._transform_coordinates(nodes_df)

    # 4. Convert link attributes
    print("Converting link attributes...")
    links_df = self._convert_link_attributes(links_df)

    # 5. Map transport modes
    print("Mapping transport modes...")
    links_df = self._map_transport_modes(links_df)

    # 6. Validate conversions
    print("Validating converted data...")
    self._validate_conversions(nodes_df, links_df)

    # 7. Generate MATSim XML
    print("Generating MATSim network.xml...")
    self._write_matsim_xml(nodes_df, links_df, output_xml_path)

    # 8. Generate validation report
    print("Creating validation report...")
    self._write_validation_report(output_xml_path.replace('.xml', '_validation.txt'))

    print(f"✓ Conversion complete: {output_xml_path}")
```

---

## 5. Implementation Details

### 5.1 Coordinate Transformation

```python
def _transform_coordinates(self, nodes_df):
    """Transform WGS84 coordinates to projected CRS"""
    from pyproj import Transformer

    # Initialize transformer (handles datum transformations)
    transformer = Transformer.from_crs(
        self.source_crs,
        self.target_crs,
        always_xy=True  # Ensure (lon, lat) order
    )

    # Transform all node coordinates
    x_projected, y_projected = transformer.transform(
        nodes_df['x_coord'].values,
        nodes_df['y_coord'].values
    )

    # Update dataframe with projected coordinates
    nodes_df['x'] = x_projected
    nodes_df['y'] = y_projected

    # Store original WGS84 for reference
    nodes_df['lon_original'] = nodes_df['longitude']
    nodes_df['lat_original'] = nodes_df['latitude']

    print(f"  Transformed {len(nodes_df)} nodes")
    print(f"  X range: {x_projected.min():.2f} to {x_projected.max():.2f} meters")
    print(f"  Y range: {y_projected.min():.2f} to {y_projected.max():.2f} meters")

    return nodes_df
```

### 5.2 Speed Unit Conversion

```python
def _convert_speed(self, speed_value, from_unit='mph'):
    """Convert speed to meters/second"""
    conversion_factors = {
        'mph': 0.44704,      # miles/hour to m/s
        'km/h': 0.277778,    # kilometers/hour to m/s
        'm/s': 1.0           # already in m/s
    }

    factor = conversion_factors.get(from_unit, 0.44704)
    return speed_value * factor
```

### 5.3 Link Attribute Conversion

```python
def _convert_link_attributes(self, links_df):
    """Convert all link attributes to MATSim requirements"""

    # Convert free_speed from mph to m/s
    links_df['freespeed'] = links_df['free_speed'].apply(
        lambda x: self._convert_speed(x, self.speed_unit)
    )

    # Rename fields for MATSim
    links_df['from'] = links_df['from_node_id']
    links_df['to'] = links_df['to_node_id']
    links_df['permlanes'] = links_df['lanes']

    # Validate capacity values
    links_df['capacity'] = links_df['capacity'].astype(int)

    print(f"  Converted {len(links_df)} links")
    print(f"  Speed range: {links_df['freespeed'].min():.2f} to {links_df['freespeed'].max():.2f} m/s")

    return links_df
```

### 5.4 Transport Mode Mapping

```python
def _map_transport_modes(self, links_df):
    """Map OSM link types to MATSim transport modes"""

    mode_mapping = {
        'motorway': 'car',
        'trunk': 'car',
        'primary': 'car',
        'secondary': 'car,bus',
        'tertiary': 'car,bus',
        'residential': 'car,bike',
        'living_street': 'car,bike',
        'service': 'car',
        'unclassified': 'car',
        'cycleway': 'bike',
        'footway': 'walk',
        'pedestrian': 'walk',
        'path': 'walk'
    }

    # Apply mapping with default fallback
    links_df['modes'] = links_df['link_type'].map(mode_mapping).fillna('car')

    # Refinement based on capacity/lanes
    high_capacity_mask = (links_df['lanes'] >= 3) & (links_df['capacity'] >= 5400)
    links_df.loc[high_capacity_mask, 'modes'] = 'car'

    # Print mode distribution
    mode_counts = links_df['modes'].value_counts()
    print(f"  Mode distribution:")
    for mode, count in mode_counts.items():
        print(f"    {mode}: {count} links ({count/len(links_df)*100:.1f}%)")

    return links_df
```

### 5.5 XML Generation

```python
def _write_matsim_xml(self, nodes_df, links_df, output_path):
    """Generate MATSim network.xml file"""
    import xml.etree.ElementTree as ET
    from xml.dom import minidom

    # Create root element with DTD reference
    root = ET.Element('network')
    root.set('name', self.network_name)

    # Add DOCTYPE in final output
    doctype = '<!DOCTYPE network SYSTEM "http://www.matsim.org/files/dtd/network_v1.dtd">'

    # Create nodes section
    nodes_elem = ET.SubElement(root, 'nodes')
    for _, node in nodes_df.iterrows():
        node_elem = ET.SubElement(nodes_elem, 'node')
        node_elem.set('id', str(node['node_id']))
        node_elem.set('x', f"{node['x']:.6f}")
        node_elem.set('y', f"{node['y']:.6f}")

    # Create links section
    links_elem = ET.SubElement(root, 'links')
    links_elem.set('capperiod', '01:00:00')

    for _, link in links_df.iterrows():
        link_elem = ET.SubElement(links_elem, 'link')
        link_elem.set('id', str(link['link_id']))
        link_elem.set('from', str(link['from']))
        link_elem.set('to', str(link['to']))
        link_elem.set('length', f"{link['length']:.6f}")
        link_elem.set('freespeed', f"{link['freespeed']:.6f}")
        link_elem.set('capacity', f"{link['capacity']:.1f}")
        link_elem.set('permlanes', f"{link['permlanes']:.1f}")
        link_elem.set('modes', link['modes'])

    # Pretty print XML
    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")

    # Insert DOCTYPE after XML declaration
    xml_lines = xml_str.split('\n')
    xml_lines.insert(1, doctype)
    xml_str = '\n'.join(xml_lines)

    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(xml_str)

    print(f"  Written: {output_path}")
    print(f"  Nodes: {len(nodes_df)}, Links: {len(links_df)}")
```

---

## 6. Data Validation Strategy

### 6.1 Input Validation Checks

```python
def _validate_gmns_data(self, nodes_df, links_df):
    """Validate GMNS input data quality"""

    issues = []

    # Check required columns
    required_node_cols = ['node_id', 'x_coord', 'y_coord']
    required_link_cols = ['link_id', 'from_node_id', 'to_node_id', 'length',
                         'lanes', 'capacity', 'free_speed']

    missing_node_cols = set(required_node_cols) - set(nodes_df.columns)
    missing_link_cols = set(required_link_cols) - set(links_df.columns)

    if missing_node_cols:
        issues.append(f"Missing node columns: {missing_node_cols}")
    if missing_link_cols:
        issues.append(f"Missing link columns: {missing_link_cols}")

    # Check for duplicate IDs
    if nodes_df['node_id'].duplicated().any():
        issues.append("Duplicate node IDs found")
    if links_df['link_id'].duplicated().any():
        issues.append("Duplicate link IDs found")

    # Check for orphan links (referencing non-existent nodes)
    node_ids = set(nodes_df['node_id'])
    orphan_from = set(links_df['from_node_id']) - node_ids
    orphan_to = set(links_df['to_node_id']) - node_ids

    if orphan_from:
        issues.append(f"Links reference {len(orphan_from)} non-existent from_nodes")
    if orphan_to:
        issues.append(f"Links reference {len(orphan_to)} non-existent to_nodes")

    # Check for invalid values
    if (links_df['length'] <= 0).any():
        issues.append("Invalid link lengths (≤0) detected")
    if (links_df['lanes'] <= 0).any():
        issues.append("Invalid lane counts (≤0) detected")
    if (links_df['capacity'] <= 0).any():
        issues.append("Invalid capacities (≤0) detected")
    if (links_df['free_speed'] <= 0).any():
        issues.append("Invalid speeds (≤0) detected")

    # Check coordinate ranges (WGS84 validity)
    if not (-180 <= nodes_df['x_coord'].min() <= 180):
        issues.append("X coordinates outside valid WGS84 range")
    if not (-90 <= nodes_df['y_coord'].min() <= 90):
        issues.append("Y coordinates outside valid WGS84 range")

    # Report results
    if issues:
        print("⚠ Validation warnings:")
        for issue in issues:
            print(f"  - {issue}")
        self.validation_report['input_issues'] = issues
    else:
        print("✓ Input validation passed")

    return len(issues) == 0
```

### 6.2 Output Validation Checks

```python
def _validate_conversions(self, nodes_df, links_df):
    """Validate converted data before XML generation"""

    issues = []
    warnings = []

    # Check coordinate transformation results
    if nodes_df['x'].isnull().any() or nodes_df['y'].isnull().any():
        issues.append("Coordinate transformation produced null values")

    # Check for unrealistic coordinate ranges (should be in meters)
    x_range = nodes_df['x'].max() - nodes_df['x'].min()
    y_range = nodes_df['y'].max() - nodes_df['y'].min()

    if x_range > 100000 or y_range > 100000:  # > 100km seems large for Manhattan
        warnings.append(f"Large coordinate range detected: {x_range:.0f}m × {y_range:.0f}m")

    # Check speed conversion (should be reasonable m/s values)
    if links_df['freespeed'].min() < 1 or links_df['freespeed'].max() > 50:
        warnings.append(f"Unusual speed range: {links_df['freespeed'].min():.2f} to {links_df['freespeed'].max():.2f} m/s")

    # Check mode assignments
    if (links_df['modes'] == '').any():
        issues.append("Some links have empty modes attribute")

    # Report results
    if issues:
        print("❌ Validation errors:")
        for issue in issues:
            print(f"  - {issue}")
        self.validation_report['conversion_errors'] = issues

    if warnings:
        print("⚠ Validation warnings:")
        for warning in warnings:
            print(f"  - {warning}")
        self.validation_report['conversion_warnings'] = warnings

    if not issues and not warnings:
        print("✓ Conversion validation passed")

    return len(issues) == 0
```

### 6.3 Validation Report Generation

```python
def _write_validation_report(self, report_path):
    """Generate comprehensive validation report"""

    report = f"""
GMNS to MATSim Conversion Validation Report
{'='*60}

Conversion Parameters:
- Source CRS: {self.source_crs}
- Target CRS: {self.target_crs}
- Network Name: {self.network_name}
- Speed Unit: {self.speed_unit}

Input Validation:
{self._format_validation_section('input_issues')}

Conversion Validation:
{self._format_validation_section('conversion_errors')}
{self._format_validation_section('conversion_warnings')}

Output Statistics:
{self._format_output_statistics()}

Recommendations:
{self._format_recommendations()}
"""

    with open(report_path, 'w') as f:
        f.write(report)

    print(f"  Validation report: {report_path}")
```

---

## 7. Usage Examples

### 7.1 Basic Conversion

```python
from gmns_to_matsim import GMNSToMATSimConverter

# Initialize converter with Manhattan-appropriate CRS
converter = GMNSToMATSimConverter(
    source_crs='EPSG:4326',      # WGS84
    target_crs='EPSG:32618',     # UTM Zone 18N
    network_name='manhattan',
    speed_unit='mph'
)

# Perform conversion
converter.convert(
    node_csv_path='manhattan_network_data/node.csv',
    link_csv_path='manhattan_network_data/link.csv',
    output_xml_path='manhattan_network.xml'
)
```

**Expected Output**:
```
Loading GMNS network data...
Validating input data...
✓ Input validation passed
Transforming coordinates from EPSG:4326 to EPSG:32618...
  Transformed 4619 nodes
  X range: 580000.00 to 590000.00 meters
  Y range: 4510000.00 to 4520000.00 meters
Converting link attributes...
  Converted 9901 links
  Speed range: 15.65 to 15.65 m/s
Mapping transport modes...
  Mode distribution:
    car: 3500 links (35.4%)
    car,bus: 4000 links (40.4%)
    car,bike: 2401 links (24.2%)
Validating converted data...
✓ Conversion validation passed
Generating MATSim network.xml...
  Written: manhattan_network.xml
  Nodes: 4619, Links: 9901
Creating validation report...
  Validation report: manhattan_network_validation.txt
✓ Conversion complete: manhattan_network.xml
```

### 7.2 Advanced Configuration

```python
# Custom mode mapping
custom_mode_mapper = {
    'primary': 'car,taxi',
    'secondary': 'car,bus,taxi',
    'residential': 'car,bike,walk'
}

converter = GMNSToMATSimConverter(
    target_crs='EPSG:2263',      # NY State Plane (requires feet to meters)
    network_name='manhattan_multimodal',
    speed_unit='mph'
)

converter.set_custom_mode_mapping(custom_mode_mapper)
converter.convert(...)
```

### 7.3 Batch Processing

```python
import glob

# Convert multiple networks
network_dirs = glob.glob('*/network_data/')

for network_dir in network_dirs:
    name = network_dir.split('/')[0]
    converter = GMNSToMATSimConverter(network_name=name)
    converter.convert(
        f'{network_dir}/node.csv',
        f'{network_dir}/link.csv',
        f'matsim_networks/{name}_network.xml'
    )
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

```python
# Test coordinate transformation
def test_coordinate_transformation():
    converter = GMNSToMATSimConverter()

    # Manhattan test point: Times Square
    lon, lat = -73.9855, 40.7580

    # Expected UTM 18N coordinates (approximate)
    expected_x, expected_y = 585775, 4511024

    x, y = converter.transformer.transform(lon, lat)

    assert abs(x - expected_x) < 1.0  # Within 1 meter
    assert abs(y - expected_y) < 1.0

# Test speed conversion
def test_speed_conversion():
    converter = GMNSToMATSimConverter(speed_unit='mph')

    assert abs(converter._convert_speed(35) - 15.6464) < 0.001
    assert abs(converter._convert_speed(60) - 26.8224) < 0.001

# Test mode mapping
def test_mode_mapping():
    links_df = pd.DataFrame({
        'link_type': ['primary', 'residential', 'cycleway'],
        'lanes': [3, 1, 1],
        'capacity': [5400, 1800, 1800]
    })

    converter = GMNSToMATSimConverter()
    result = converter._map_transport_modes(links_df)

    assert result.loc[0, 'modes'] == 'car'
    assert result.loc[1, 'modes'] == 'car,bike'
    assert result.loc[2, 'modes'] == 'bike'
```

### 8.2 Integration Tests

```python
def test_full_conversion():
    """Test complete conversion workflow"""

    converter = GMNSToMATSimConverter()

    # Use small test dataset (100 nodes, 200 links)
    converter.convert(
        'test_data/node_small.csv',
        'test_data/link_small.csv',
        'test_output/network_test.xml'
    )

    # Validate output file exists and is valid XML
    assert os.path.exists('test_output/network_test.xml')

    # Parse XML and validate structure
    tree = ET.parse('test_output/network_test.xml')
    root = tree.getroot()

    assert root.tag == 'network'
    assert root.find('nodes') is not None
    assert root.find('links') is not None
    assert len(root.find('nodes')) == 100
    assert len(root.find('links')) == 200
```

### 8.3 MATSim Compatibility Test

```python
def test_matsim_loading():
    """Test that generated XML can be loaded by MATSim"""

    # Requires MATSim Java libraries or matsim-python-tools
    from matsimtools import MATSimNetwork

    network = MATSimNetwork.from_xml('test_output/network_test.xml')

    assert network.num_nodes() == 100
    assert network.num_links() == 200

    # Test network connectivity
    assert network.is_connected()
```

---

## 9. Known Limitations and Future Enhancements

### 9.1 Current Limitations

1. **No Multi-Modal Transit Support**
   - Current implementation focuses on road network
   - Does not generate MATSim transit schedule files
   - **Workaround**: Use MATSim's pt2matsim tool separately

2. **Simplified Network Topology**
   - Ignores curved link geometries
   - No turn restrictions or lane-specific routing
   - **Impact**: Moderate - travel times remain accurate

3. **Limited Traffic Control Information**
   - No signal timing data
   - No stop sign or yield information
   - **Workaround**: MATSim can estimate signal timing from network structure

4. **Basic Mode Assignment Logic**
   - Heuristic-based mode mapping
   - May not reflect actual access restrictions
   - **Workaround**: Manual review and adjustment of high-importance corridors

5. **No Time-Varying Attributes**
   - Fixed capacity and speed (no time-of-day variation)
   - **Workaround**: Use MATSim's network change events

### 9.2 Planned Enhancements

**Phase 2 Features**:
- [ ] Support for GMNS geometry parsing and intermediate node insertion
- [ ] Integration with GMNS segment.csv and lane.csv (dynamic attributes)
- [ ] Configurable mode mapping via external configuration file
- [ ] Network simplification options (merge short links, remove degree-2 nodes)
- [ ] Batch processing CLI interface

**Phase 3 Features**:
- [ ] Transit network integration (movement.csv → transit schedule)
- [ ] Signal timing import from GMNS timing_phase.csv
- [ ] Turn restriction handling
- [ ] Network topology validation and repair
- [ ] Visualization output (network plots, validation maps)

**Phase 4 Features**:
- [ ] Bi-directional conversion (MATSim → GMNS)
- [ ] Integration with demand matrix conversion
- [ ] Automated scenario generation for MATSim
- [ ] Performance optimization for large networks (>100k links)

---

## 10. Dependencies and Requirements

### 10.1 Python Libraries

```python
# requirements.txt
pandas>=1.5.0           # Data manipulation
numpy>=1.23.0           # Numerical operations
pyproj>=3.4.0           # Coordinate transformations
shapely>=2.0.0          # Geometry operations (future enhancement)
geopandas>=0.12.0       # Spatial data handling (optional)
lxml>=4.9.0             # XML parsing and validation
```

### 10.2 Optional Dependencies

```python
# For testing and validation
pytest>=7.2.0
matsim-tools>=0.0.14    # Python bindings for MATSim (if available)

# For visualization
matplotlib>=3.6.0
folium>=0.14.0
```

### 10.3 System Requirements

- **Python**: 3.8 or higher
- **Memory**: Minimum 4GB RAM (for Manhattan-sized networks)
- **Disk Space**: ~50MB for code + 3x network file size for processing
- **Operating System**: Platform-independent (Windows, macOS, Linux)

---

## 11. Implementation Timeline

### Phase 1: Core Converter (Weeks 1-2)
- ✓ Research and planning (this document)
- Implement coordinate transformation module
- Implement unit conversion utilities
- Implement basic XML writer
- Unit tests for core functions

### Phase 2: Mode Mapping and Validation (Week 3)
- Implement mode mapping logic
- Develop validation framework
- Integration tests with Manhattan dataset
- Generate validation reports

### Phase 3: Documentation and Refinement (Week 4)
- User documentation and examples
- API documentation
- Performance optimization
- Bug fixes and edge case handling

### Phase 4: Testing and Deployment (Week 5)
- MATSim compatibility testing
- Large-scale network testing
- Code review and refactoring
- Package for distribution

---

## 12. Success Criteria

### 12.1 Functional Requirements

- [ ] Successfully convert Manhattan GMNS dataset (4,619 nodes, 9,901 links)
- [ ] Generated network.xml validates against MATSim DTD
- [ ] MATSim can load and simulate using generated network
- [ ] Coordinate transformation produces accurate projected coordinates
- [ ] All unit conversions mathematically correct
- [ ] Transport mode assignments reasonable and configurable

### 12.2 Quality Requirements

- [ ] 100% of nodes converted without data loss
- [ ] 100% of links converted without data loss
- [ ] Link length accuracy within 1% after projection
- [ ] Speed conversion exact (no rounding errors >0.01 m/s)
- [ ] Zero orphan links (all references valid)
- [ ] XML output well-formed and pretty-printed

### 12.3 Performance Requirements

- [ ] Process Manhattan network in <60 seconds on standard laptop
- [ ] Memory usage <2GB for networks up to 50,000 links
- [ ] Support networks up to 1 million links (tested on synthetic data)

### 12.4 Documentation Requirements

- [ ] Complete API documentation with examples
- [ ] User guide with common use cases
- [ ] Troubleshooting guide for common issues
- [ ] Data format specification reference
- [ ] Validation report interpretation guide

---

## 13. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| CRS transformation errors | Medium | **Critical** | Extensive testing with known coordinates; validation against external tools |
| Mode mapping inaccuracies | High | Medium | Provide configurable mapping; document assumptions; allow manual override |
| MATSim compatibility issues | Low | High | Test with multiple MATSim versions; follow official DTD strictly |
| Performance bottlenecks | Medium | Low | Profile code; optimize pandas operations; implement chunking for large networks |
| Missing GMNS fields | Medium | Medium | Graceful degradation; use sensible defaults; document limitations |
| Link length inconsistencies | Medium | Medium | Implement validation and recalculation option; allow tolerance thresholds |

---

## 14. References and Resources

### 14.1 Specifications

- **GMNS Official Specification**: https://github.com/zephyr-data-specs/GMNS
- **GMNS Documentation**: https://zephyr-data-specs.github.io/GMNS/
- **MATSim Network DTD**: http://www.matsim.org/files/dtd/network_v1.dtd
- **MATSim User Guide**: https://matsim.org/docs/userguide

### 14.2 Related Tools

- **osm2gmns**: Python package for OSM to GMNS conversion
- **osm2matsim**: Java tool for OSM to MATSim conversion
- **pt2matsim**: MATSim extension for public transit networks
- **matsim-python-tools**: Python interface to MATSim

### 14.3 Coordinate Systems

- **EPSG:4326** (WGS84): https://epsg.io/4326
- **EPSG:32618** (UTM 18N): https://epsg.io/32618
- **EPSG:2263** (NY State Plane): https://epsg.io/2263
- **Pyproj Documentation**: https://pyproj4.github.io/pyproj/

### 14.4 Standards

- **Frictionless Data Table Schema**: https://specs.frictionlessdata.io/table-schema/
- **Well-Known Text (WKT)**: https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry
- **XML DTD Specification**: https://www.w3.org/TR/xml/

---

## 15. Appendices

### Appendix A: GMNS Manhattan Dataset Summary

```
Dataset: grid2demand/manhattan_network_data/
Generated: 2025 (grid2demand extension project)
Source: OpenStreetMap via OSMnx

node.csv:
- Records: 4,619
- File size: 313.67 KB
- Coordinate system: WGS84 (EPSG:4326)
- Bounding box:
  - Longitude: -74.02° to -73.91°
  - Latitude: 40.70° to 40.88°
- Coverage: Manhattan, New York City

link.csv:
- Records: 9,901
- File size: 522.64 KB
- Network type: Directed graph (unidirectional links)
- Lane distribution:
  - 1 lane: ~60% of links
  - 2 lanes: ~20% of links
  - 3 lanes: ~15% of links
  - 4+ lanes: ~5% of links
- Speed: Uniform 35 mph
- Capacity: 1800 * lanes veh/hr

zone.csv:
- Records: 128 zones (8×16 grid)
- File size: 9.95 KB

poi.csv:
- Records: 72,466 points of interest
- File size: 24.56 MB
```

### Appendix B: MATSim Network.xml Example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE network SYSTEM "http://www.matsim.org/files/dtd/network_v1.dtd">
<network name="manhattan">
  <nodes>
    <node id="0" x="585234.123456" y="4515678.234567"/>
    <node id="1" x="585345.654321" y="4515789.876543"/>
    <!-- ... -->
  </nodes>
  <links capperiod="01:00:00">
    <link id="0" from="0" to="1" length="138.033090"
          freespeed="15.646400" capacity="1800.0"
          permlanes="1.0" modes="car,bus"/>
    <link id="1" from="1" to="0" length="138.033090"
          freespeed="15.646400" capacity="1800.0"
          permlanes="1.0" modes="car,bus"/>
    <!-- ... -->
  </links>
</network>
```

### Appendix C: Unit Conversion Reference

| Measure | From | To | Formula | Example |
|---------|------|----|---------| --------|
| Speed | mph | m/s | mph × 0.44704 | 35 mph = 15.6464 m/s |
| Speed | km/h | m/s | km/h × 0.277778 | 60 km/h = 16.6667 m/s |
| Length | miles | meters | miles × 1609.344 | 1 mile = 1609.344 m |
| Length | feet | meters | feet × 0.3048 | 100 ft = 30.48 m |
| Capacity | veh/hr/lane | veh/hr | lanes × veh/hr/lane | 2 lanes × 1800 = 3600 veh/hr |

### Appendix D: OSM Highway Type Reference

| OSM Type | Description | Typical Use | Suggested Modes |
|----------|-------------|-------------|-----------------|
| motorway | Controlled-access highway | Interstate highways | car |
| trunk | Major highway | US/State routes | car |
| primary | Primary road | Major arterials | car |
| secondary | Secondary road | Important through streets | car,bus |
| tertiary | Tertiary road | Through streets | car,bus |
| residential | Residential street | Neighborhood access | car,bike |
| living_street | Pedestrian priority | Shared space | car,bike,walk |
| service | Service road | Parking, alleys | car |
| unclassified | Minor road | Minor through streets | car |

---

## Document Control

- **Version**: 1.0
- **Status**: Planning Complete - Ready for Implementation
- **Author**: Claude Code Research Agent
- **Last Updated**: 2025-11-19
- **Next Review**: Upon completion of Phase 1 implementation

---

## Approval and Sign-off

- [ ] Technical approach validated
- [ ] Data quality requirements confirmed
- [ ] Implementation timeline approved
- [ ] Success criteria agreed upon
- [ ] Ready to proceed with implementation
