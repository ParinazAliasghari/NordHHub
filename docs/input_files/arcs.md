# Arcs Input File (`arcs.csv`)

The `arcs.csv` file defines all network links (pipelines or connections) between nodes in the MGET model.  
Each row represents **one directed arc** that can carry gas or hydrogen.

---

## Columns

| Column name           | Type / format | Description |
|-----------------------|---------------|-------------|
| **idx**               | integer       | Simple row index (1, 2, 3, …). Used only for debugging. |
| **arc_id**            | string        | Unique identifier for the arc, recommended format: `START_END` (e.g., `ES300_ES611`). |
| **start_node**        | string        | Node ID where the arc begins. Must match `node_id` in `nodes.csv`. |
| **end_node**          | string        | Node ID where the arc ends. Must match `node_id` in `nodes.csv`. |
| **fuel**              | string        | Carrier transported on the arc (e.g., `G` = gas, `H` = hydrogen). |
| **capacity**          | float         | Existing/installed transport capacity (units consistent with the model). |
| **length_km**         | float (km)    | Total physical length of the arc in kilometres. |
| **length_offshore_km**| float (km)    | Offshore portion of the corridor (0 if fully onshore). |
| **status**            | binary (0/1)  | **1 = arc is active**, **0 = arc is defined but excluded** in this scenario. |
| **bidirectional**     | binary (0/1)  | Physical infrastructure supports two-way flow. |
| **reversible**        | binary (0/1)  | Model may operate this arc in both directions (mathematical reversibility). |
| **opposite**          | string        | `arc_id` of the reverse arc, if defined separately (optional). |
| **cal_x**             | float         | Calibration factor for CAPEX scaling. |
| **cal_c**             | float         | Calibration factor for OPEX scaling. |
| **cal_b**             | float         | Calibration factor for base/fixed costs. |
| **cal_r**             | float         | Calibration factor for repurposing costs. |
| **cal_l**             | float         | Calibration factor for transport losses. |

---

## Notes

### Bidirectional vs. Reversible
- **bidirectional = 1** → Pipeline physically designed for flow in both directions.  
- **reversible = 1** → Model may allow reversing flow direction even if the asset is technically one-directional.

### Opposite Arcs
If the arc is modeled explicitly in both directions:
