# Nodes input file (`nodes.csv`)

This file defines all spatial nodes used in the MGET model  
(e.g. NUTS3 regions where demand, production, and network connections are located).

Each row corresponds to **one node**.

---

## Columns

| Column name      | Type / format | Description |
|------------------|---------------|-------------|
| `idx`            | integer       | Simple running index (1, 2, 3, …). Mainly for checking/debugging large datasets; not used in equations. |
| `node_id`        | string        | Unique identifier of the node, usually the NUTS3 code (e.g. `ES300`, `ES611`, `PT186`). This is the ID that appears in the mathematical model as set **n**. |
| `region`         | string        | Larger regional grouping of the node. In your current data this is often NUTS1 / macro‐region (e.g. `AFR`, `EU`). Useful for aggregation and plotting. |
| `country`        | string        | Country code of the node (e.g. `ES`, `PT`, `DZ`). |
| `nuts2`          | string        | NUTS2 code to which this node (NUTS3) belongs (e.g. `ES30`, `ES61`). Used for multi-level regional analysis. |
| `node_name`      | string        | Human-readable name of the node (e.g. *Madrid*, *Cuenca*, *Alto Alentejo*). Used in tables, plots, and maps. |
| `lat`            | float (°)     | Latitude in decimal degrees (WGS84). Positive = north, negative = south. Used for mapping. |
| `lon`            | float (°)     | Longitude in decimal degrees (WGS84). Positive = east, negative = west. Used for mapping. |
| `gas_share`      | float         | Share of total **gas** demand assigned to this node (typically between 0 and 1). Node-level gas demand can be calculated as `country_gas_demand × gas_share`. |
| `hydrogen_share` | float         | Share of total **hydrogen** demand assigned to this node (0–1). Node-level hydrogen demand can be calculated similarly. |
| `status`         | integer (0/1) | Indicator whether the node is active in the scenario. Convention: `1` = node is included in the model; `0` = node is defined in the dataset but not used in this run. |
| `source`         | string        | Short code or text describing the data source (e.g. `Eurostat_2020`, `assumption`, `GIS`). Useful for transparency and reproducibility. |
| `comments`       | string        | Free-text notes about this node (e.g. data issues, special assumptions, mapping decisions). |

---

## Example

```csv
idx,node_id,region,country,nuts2,node_name,lat,lon,gas_share,hydrogen_share,status,source,comments
1,DZ000,AFR,DZ,DZ00,Algeria,28.04,1.66,1.0,1.0,1,IEA2020,"Aggregated national node"
2,ES300,EU,ES,ES30,Madrid,40.40806,-3.59673,1.0,1.0,1,Eurostat2020,""
3,ES423,EU,ES,ES42,Cuenca,40.03931,-3.14839,0.4701,0.4701,1,Eurostat2020,"Demand split by GDP + population"
