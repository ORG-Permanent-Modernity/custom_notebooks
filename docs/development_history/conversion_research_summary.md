# GMNS to MATSim Conversion Research Summary

## Quick Reference Guide

**Date**: 2025-11-19
**Status**: Research Complete - Ready for Implementation

---

## Executive Summary

Research completed for converting GMNS network data + grid2demand outputs into complete MATSim simulation scenarios (network + population). Two conversion components required:

1. **Network Conversion**: GMNS CSV → MATSim network.xml
2. **Demand Conversion**: grid2demand OD matrix → MATSim population.xml

---

## Key Findings

### 1. Data Source Recommendation: **osm2gmns > OSMnx**

| Feature | OSMnx + Custom | osm2gmns | Advantage |
|---------|----------------|----------|-----------|
| Geometry | Empty | Full WKT LINESTRING | osm2gmns |
| Lane defaults | Manual | Auto-filled by type | osm2gmns |
| Speed defaults | Fixed (35 mph) | Type-specific | osm2gmns |
| Capacity | Manual (1800/lane) | Type-specific | osm2gmns |
| Mode restrictions | Inferred | Explicit (allowed_uses) | osm2gmns |
| Multi-resolution | No | Yes (macro/meso/micro) | osm2gmns |

**Recommendation**: Use osm2gmns for production converters

---

## Critical Conversion Issues

### Network Conversion Issues

| Issue | Impact | Solution | Priority |
|-------|--------|----------|----------|
| **CRS Mismatch** | CRITICAL | Transform WGS84 → UTM 18N (EPSG:32618) | **CRITICAL** |
| Speed units | High | Convert km/h → m/s (×0.277778) | **HIGH** |
| Mode mapping | Medium | Parse allowed_uses → MATSim modes | **HIGH** |
| Empty geometry | Low | Accept (MATSim uses straight lines) | **LOW** |

**Most Critical**: Coordinate transformation - MATSim requires projected CRS in meters, not WGS84 degrees.

### Demand Conversion Issues

| Issue | Impact | Solution | Priority |
|-------|--------|----------|----------|
| **OD disaggregation** | CRITICAL | Generate individual agents from aggregate flows | **CRITICAL** |
| Zone-to-link mapping | High | Random/centroid link selection within zones | **HIGH** |
| Time distributions | High | Sample departure times by trip purpose | **HIGH** |
| Mode choice | Medium | Distance-based or POI-based inference | **MEDIUM** |

**Most Critical**: Converting aggregate OD matrix (34,152 trips zone 1→2) into individual agents with specific activities and timings.

---

## Conversion Architecture

### Input Files

**From osm2gmns**:
- `node.csv` - Network nodes with WGS84 coordinates
- `link.csv` - Links with geometry, speeds, capacities, allowed_uses

**From grid2demand**:
- `zone.csv` - TAZ centroids with production/attraction
- `demand.csv` - OD matrix (o_zone_id, d_zone_id, volume)
- `node.csv` - Updated with zone assignments

### Output Files

**MATSim scenario**:
- `network.xml` - Road infrastructure (nodes in projected CRS, links with attributes)
- `population.xml` - Travel demand (agents with daily activity plans)

---

## Demand Conversion Strategies

### Option 1: Simple Disaggregation (Initial Implementation)

**Concept**: Create round-trip commuters
- Each OD pair → N individual agents (N = volume)
- Activity chain: home → work → home
- Departure times: Normal distribution around peak hours
- Mode: Default to car or distance-based choice

**Pros**: Fast, simple, easy to validate
**Cons**: Unrealistic behavior patterns

### Option 2: Activity-Based Disaggregation (Production)

**Concept**: Realistic daily activity patterns
- Infer trip purpose from destination POI types
- Multi-stop chains: home → work → shop → home
- Purpose-specific time distributions
- Distance-based mode choice
- POI-weighted location selection

**Pros**: Realistic, better for policy analysis
**Cons**: More complex, requires POI data

---

## Key Algorithms

### 1. Coordinate Transformation

```python
from pyproj import Transformer

# Manhattan/Brooklyn: Use UTM Zone 18N
transformer = Transformer.from_crs("EPSG:4326", "EPSG:32618", always_xy=True)
x_proj, y_proj = transformer.transform(lon, lat)
```

### 2. Speed Conversion

```python
# osm2gmns uses km/h, MATSim needs m/s
speed_ms = speed_kmh * 0.277778
```

### 3. Mode Mapping

```python
# Parse osm2gmns allowed_uses field
allowed = set(allowed_uses_str.split(','))  # {'auto', 'bike'}

matsim_modes = []
if 'auto' in allowed:
    matsim_modes.append('car')
    if facility_type in ['primary', 'secondary']:
        matsim_modes.append('bus')
if 'bike' in allowed:
    matsim_modes.append('bike')

modes = ','.join(matsim_modes)  # "car,bus"
```

### 4. Zone-to-Link Mapping

```python
def get_random_link_in_zone(network, zone_id, node_df):
    """Map zone to specific network link"""
    # Get nodes in zone
    zone_nodes = node_df[node_df['zone_id'] == zone_id]['node_id']

    # Get links connected to these nodes
    zone_links = network[
        network['from_node_id'].isin(zone_nodes) |
        network['to_node_id'].isin(zone_nodes)
    ]

    # Sample weighted by capacity
    weights = zone_links['capacity'] / zone_links['capacity'].sum()
    selected = np.random.choice(zone_links['link_id'], p=weights)
    return selected
```

### 5. Departure Time Sampling

```python
import numpy as np

def sample_departure_time(purpose='work'):
    """Sample realistic departure times"""
    distributions = {
        'work': {'mean': 8, 'std': 0.5},      # 8 AM ± 30 min
        'school': {'mean': 7.5, 'std': 0.25},  # 7:30 AM ± 15 min
        'shopping': {'mean': 14, 'std': 2},    # 2 PM ± 2 hours
    }

    params = distributions[purpose]
    hour_float = np.random.normal(params['mean'], params['std'])
    hour_float = np.clip(hour_float, 5, 23)  # 5 AM - 11 PM

    hours = int(hour_float)
    minutes = int((hour_float - hours) * 60)
    return f"{hours:02d}:{minutes:02d}:00"
```

---

## Data Comparison: Brooklyn Dataset

### OSMnx Approach (Manhattan)
```
Nodes: 4,619
Links: 9,901
Geometry: Empty
Speed: Fixed 35 mph
Capacity: 1800 × lanes
```

### osm2gmns Approach (Brooklyn)
```
Nodes: 16,623
Links: 36,755
Geometry: Full LINESTRING WKT
Speed: Type-specific (40 km/h residential, 120 km/h motorway)
Capacity: Type-specific (600-2300 veh/hr)
Allowed_uses: Explicit (auto, bike, walk)
```

**Conclusion**: osm2gmns provides significantly richer data for MATSim conversion

---

## grid2demand Demand Data

### Brooklyn Example (from notebook)

**Zones**: 79 grid cells (1km × 1km)
**OD Pairs**: 6,241 (with volume > 0)
**Total Trips**: 1,760,040 trips/day

**Top OD Flow**:
- Zone 75 ↔ 76: 16,948 trips (bidirectional)
- Zone 76 ↔ 77: 14,400 trips
- Zone 74 ↔ 75: 7,052 trips

**Conversion Task**: Convert these 1.76M aggregate trips into individual MATSim agents with:
- Specific departure times
- Specific link locations (not just zones)
- Activity types (home, work, etc.)
- Transport modes

---

## MATSim Format Requirements

### network.xml Structure

```xml
<network name="brooklyn">
  <nodes>
    <node id="1" x="585234.12" y="4515678.23"/>
  </nodes>
  <links capperiod="01:00:00">
    <link id="1" from="1" to="2" length="29.71"
          freespeed="11.11" capacity="5400.0"
          permlanes="3.0" modes="car,bus"/>
  </links>
</network>
```

**Key**: Coordinates MUST be in meters (projected CRS)

### population.xml Structure

```xml
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

**Key**: Each person needs specific link IDs and times

---

## Validation Strategy

### Network Validation
- ✓ Coordinate transformation accuracy (< 1m error)
- ✓ All nodes have projected coordinates
- ✓ No orphan links (all references valid)
- ✓ Speed conversions correct
- ✓ MATSim can load network.xml

### Demand Validation
- ✓ Total trips preserved (original 1.76M ≈ generated agents)
- ✓ OD flow distribution preserved (RMSE < 5%)
- ✓ All zones have agents
- ✓ Departure times realistic (peak hours show peaks)
- ✓ MATSim can load population.xml
- ✓ MATSim simulation runs successfully

---

## Implementation Phases

### Phase 1: Network Converter (Weeks 1-2)
- Coordinate transformation
- Unit conversions
- Mode mapping
- XML generation

**Deliverable**: Working network.xml

### Phase 2: Basic Demand Converter (Weeks 3-4)
- Simple disaggregation
- Zone-to-link mapping
- Time sampling
- Population XML generation

**Deliverable**: Working population.xml (simple)

### Phase 3: Enhanced Demand (Week 5)
- Activity-based disaggregation
- POI inference
- Mode choice
- Multi-stop chains

**Deliverable**: Production-ready converter

### Phase 4: Integration (Week 6)
- End-to-end testing
- MATSim compatibility validation
- Documentation
- CLI interface

**Deliverable**: Complete tested converter

---

## Quick Start Guide

### Recommended Workflow

1. **Download network with osm2gmns**:
   ```python
   import osm2gmns as og
   net = og.getNetFromFile('map.osm', mode_types='auto', POI=True)
   og.fillLinkAttributesWithDefaultValues(net)
   og.outputNetToCSV(net, 'network_data/')
   ```

2. **Generate demand with grid2demand**:
   ```python
   import grid2demand as gd
   net = gd.GRID2DEMAND(input_dir='network_data/')
   net.load_network()
   net.net2grid(cell_width=1, cell_height=1, unit="km")
   net.taz2zone()
   net.run_gravity_model()
   net.save_results_to_csv(overwrite_file=True)
   ```

3. **Convert to MATSim** (to be implemented):
   ```python
   from gmns_matsim_converter import GMNSMATSimConverter

   converter = GMNSMATSimConverter(
       source_crs='EPSG:4326',
       target_crs='EPSG:32618',
       network_name='brooklyn'
   )

   converter.convert(
       input_dir='network_data/',
       output_dir='matsim_scenario/'
   )
   ```

---

## Critical Success Factors

1. **Coordinate Transformation**: Must be accurate - this is make-or-break
2. **Demand Conservation**: Generated agents must preserve OD flows
3. **MATSim Compatibility**: Files must load and simulate without errors
4. **Realistic Behavior**: Time/space/mode distributions must be plausible
5. **Documentation**: Users need clear examples and troubleshooting

---

## Related Documentation

- **Detailed Plan**: [gmns_matsim_complete_conversion_plan.md](gmns_matsim_complete_conversion_plan.md)
- **Network-Only Plan**: [gmns_to_matsim_conversion_plan.md](gmns_to_matsim_conversion_plan.md)

---

## Next Steps

1. Review and approve research findings
2. Confirm: Use osm2gmns as primary data source
3. Confirm: Start with simple disaggregation (Option 1)
4. Begin Phase 1 implementation (network converter)
5. Set up testing framework

---

**Status**: ✅ Research Complete - Awaiting Implementation Approval
