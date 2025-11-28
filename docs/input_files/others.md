# Scalar / Other Parameters (`other.csv`)

This file contains **scalar parameters** used by the MGET model, such as
arc costs, fixed bidirectional costs, and other global or technology-
specific constants.

Each row corresponds to **one parameter value** (possibly specific to a
given fuel and/or technology).

---

## Columns

| Column      | Type / format | Description |
|------------|---------------|-------------|
| `scalar`   | string        | Short ID of the parameter as used in the model code (e.g. `c_a`, `f_ab`). This is the main key that tells the loader which parameter this row belongs to. |
| `name_id`  | string        | Secondary identifier, usually the technology / asset / option the scalar applies to (e.g. `BFPipe`, `Bidir`). Together with `scalar` and `fuel` it makes the entry unique. |
| `fuel`     | string        | Fuel / carrier this entry applies to (e.g. `gas`, `hydrogen`, `carbon`). Can be left empty for fuel-independent parameters. |
| `value`    | float         | Numerical value of the parameter in the given `unit`. This is what is actually used in the optimization model. |
| `low`      | float         | *Optional / not yet used* — lower bound for the parameter (kept for documentation / future calibration). |
| `high`     | float         | *Optional / not yet used* — upper bound for the parameter (kept for documentation / future calibration). |
| `type`     | string        | *Optional / not yet used* — qualitative type of the parameter, e.g. `var` (variable), `fix` (fixed), etc. Mainly descriptive at the moment. |
| `unit`     | string        | Unit of `value`, e.g. `€/MWh/100 km`, `per project`. Helps interpret results and keeps the dataset self-documented. |
| `full_name`| string        | Human-readable name of the parameter, e.g. “arc cost”, “fix bidirection cost”. Used only for documentation. |
| `source`   | string        | Short code or text describing the data source (e.g. `IEA2020`, `assumption`, `literature`). Useful for tracing where numbers came from. |
| `comment`  | string        | Free-text notes about this parameter (e.g. calibration notes, methodological choices, links to papers). |

> **Note:** Columns marked as *Optional / not yet used* are mainly
> included for compatibility with the original GAMS version and for
> possible future extensions.

---

## Example

```csv
scalar,name_id,fuel,value,low,high,type,unit,full_name,source,comment
c_a,BFPipe,gas,0.5,,,var,"€/MWh/100 km","arc cost","IEA2020","Base transport fee (BFPipe)"
c_a,BFPipe,hydrogen,1.0,,,var,"€/MWh/100 km","arc cost","assumption","Hydrogen pipeline cost factor"
f_ab,Bidir,gas,500,,,fix,"per project","fix bidirection cost","assumption","Cost to allow bidirectional operation"
f_ab,Bidir,hydrogen,500,,,fix,"per project","fix bidirection cost","assumption","Same as gas in this scenario"
