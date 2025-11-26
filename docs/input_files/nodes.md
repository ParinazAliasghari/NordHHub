# Nodes Input File

The `nodes.csv` (or `nodes.xlsx`) file defines the geographic and structural information
for all nodes in the MGET (Multi-Gas Energy Transition) model.

This file specifies:
- The unique node identifiers used in the network
- The geographic hierarchy (country, region, NUTS levels)
- Whether the node exists in the base year
- Optional attributes used for scenario design (shares, comments, sources)

---

## Required Columns

| Column Name | Description |
|------------|-------------|
| **node_id** | Unique ID of the node (e.g., NUTS3 code, custom ID). |
| **country** | Country code (e.g., `ES`, `FR`, `DE`). |
| **region** | Sub-national region (e.g., NUTS2). |

---

## Optional Columns

| Column Name | Description |
|------------|-------------|
| **nuts3** | NUTS-3 region name (if applicable). |
| **node_name** | Human-readable name for display plots or maps. |
| **exist** | `1` if the node exists in the base system, `0` if only used for planning. |
| **gas_share** | Share of natural gas at this node (optional). |
| **h2_share** | Share of hydrogen at this node (optional). |
| **source** | Data source reference (optional). |
| **comment** | Notes for documentation (optional). |

---

## Example

```csv
node_id,country,region,nuts3,node_name,exist,gas_share,h2_share,source,comment
ES111,ES,Aragon,Huesca,Huesca,1,0.80,0.20,IGME,Industrial cluster
ES112,ES,Aragon,Zaragoza,Zaragoza,1,0.75,0.25,TSO,Main demand center
ES113,ES,Aragon,Teruel,Teruel,0,0.00,0.00,,Future hydrogen hub

