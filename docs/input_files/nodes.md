# Nodes input file (`nodes.csv`)

This file defines all spatial nodes used in the MGET model  
(e.g., NUTS3 regions where demand, production, and network connections are located).

Each row corresponds to **one node**.

---

## Columns

| Column name | Type / format | Description |
|-------------|---------------|-------------|
| <span style="color:green;">`idx`</span> | integer | Simple running index (1, 2, 3, …). Mainly for checking large datasets; **not used in equations**. |
| <span style="color:green;">`node_id`</span> | string | Unique identifier of the node, usually the NUTS3 code (e.g. `ES300`). Appears in model set **n**. |
| <span style="color:green;">`region`</span> | string | Larger regional grouping (NUTS1 or macro-region). Useful for aggregation and plotting. |
| <span style="color:green;">`country`</span> | string | Country code (e.g. `ES`, `PT`, `DZ`). |
| <span style="color:blue;">`nuts2`</span> | string | Parent NUTS2 region (e.g. `ES30`). Helps with multi-level analysis. |
| <span style="color:blue;">`node_name`</span> | string | Human-readable name (e.g. *Madrid*, *Alto Alentejo*). |
| <span style="color:blue;">`lat`</span> | float | Latitude (WGS84). Used for maps. |
| <span style="color:blue;">`lon`</span> | float | Longitude (WGS84). Used for maps. |
| <span style="color:blue;">`gas_share`</span> | float | Share of **gas** demand assigned to this node (0–1). |
| <span style="color:blue;">`hydrogen_share`</span> | float | Share of **hydrogen** demand assigned to this node (0–1). |
| <span style="color:green;">`status`</span> | 0/1 integer | `1` = active node, `0` = defined but unused. |
| <span style="color:blue;">`source`</span> | string | Data source (e.g. `Eurostat2020`). |
| <span style="color:blue;">`comments`</span> | string | Free-text notes (optional). |

---

## Example

```csv
idx,node_id,region,country,nuts2,node_name,lat,lon,gas_share,hydrogen_share,status,source,comments
1,DZ000,AFR,DZ,DZ00,Algeria,28.04,1.66,1.0,1.0,1,IEA2020,"Aggregated national node"
2,ES300,EU,ES,ES30,Madrid,40.40806,-3.59673,1.0,1.0,1,Eurostat2020,""
3,ES423,EU,ES,ES42,Cuenca,40.03931,-3.14839,0.4701,0.4701,1,Eurostat2020,"Demand split by GDP + population"
