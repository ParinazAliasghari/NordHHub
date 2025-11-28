# Scalar / Other Parameters (`other.csv`)

This file contains **scalar parameters** used by the MGET model, such as
arc costs, fixed bidirectional costs, and other global or technology-
specific constants.

Each row corresponds to **one parameter value** (possibly specific to a
given fuel and/or technology).

---

## Columns

| Column      | Type / format | Used in Python model | Description |
|------------|---------------|----------------------|-------------|
| `scalar`   | string        | **Yes**              | Short ID of the parameter as used in the model code (e.g. `c_a`, `f_ab`). This is the main key that tells the loader which parameter this row belongs to. |
| `name_id`  | string        | **Yes**              | Secondary identifier, usually the technology / asset / option the scalar applies to (e.g. `BFPipe`, `Bidir`). Together with `scalar` and `fuel` it makes the entry unique. |
| `fuel`     | string        | **Yes** (for fuel-specific parameters) | Fuel / carrier this entry applies to (e.g. `gas`, `hydrogen`, `carbon`). Can be left empty for fuel-independent parameters. |
| `value`    | float         | **Yes**              | Numerical value of the parameter in the given `unit`. This is what is actually used in the Pyomo model. |
| `low`      | float         | *Optional / not yet used* | Lower bound for the parameter (kept for documentation / future calibration; currently ignored by the Python model). |
| `high`     | float         | *Optional / not yet used* | Upper bound for the parameter (kept for documentation / future calibration; currently ignored by the Python model). |
| `type`     | string        | *Optional / not yet used* | Qualitative type of the parameter, e.g. `var` (variable), `fix` (fixed), etc. Mainly descriptive at the moment. |
| `unit`     | string        | **Recommended**      | Unit of `value`, e.g. `€/MWh/100 km`, `per project`. Helps interpret results and keeps the dataset self-documented. |
| `full_name`| string        | **Recommended**      | Human-readable name of the parameter, e.g. “arc cost”, “fix bidirection cost”. Used only for documentation. |
| `source`   | string        | **Recommended**      | Short code or text describing the data source (e.g. `IEA2020`, `assumption`, `literature`). Useful for tracing where numbers came from. |
| `comment`  | string        | **Recommended**      | Free-text notes about this parameter (e.g. calibration notes, methodological choices, links to papers). |

> **Note:** Columns marked as *Optional / not yet used* are currently
> ignored by the Python implementation but are kept for compatibility
> with the original GAMS version and for future extensions.

---

## Example

```csv
scalar,name_id,fuel,value,low,high,type,unit,full_name,source,comment
c_a,BFPipe,gas,0.5,,,var,"€/MWh/100 km","arc cost","IEA2020","Base transport fee (BFPipe)"
c_a,BFPipe,hydrogen,1.0,,,var,"€/MWh/100 km","arc cost","assumption","Hydrogen pipeline cost factor"
f_ab,Bidir,gas,500,,,fix,"per project","fix bidirection cost","assumption","Cost to allow bidirectional operation"
f_ab,Bidir,hydrogen,500,,,fix,"per project","fix bidirection cost","assumption","Same as gas in this scenario"
