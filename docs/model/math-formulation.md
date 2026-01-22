# Mathematical formulation

This section describes the mathematical formulation of the MGET model. 

## Objective function

The objective function (Eq. 1) minimizes discounted investment and operational costs. Investment related to arcs can be in:
- new arcs,
- repurposing for fuel,
- making arcs bidirectional.

Operational costs include supply and transport, and exclude demand and storage costs. We also include penalty terms for demand deficits, supply surpluses, and supply deficits.

Typically, investment costs are about three orders of magnitude larger than yearly operational costs, and one–two orders of magnitude larger than refurbishment costs. Operational costs must be scaled to reflect the number of hours in a year represented by an operational period.

**Objective (1):**

$$
\min \; \Big( \text{Total discounted investment cost} + \text{Operational cost} + \text{Penalty terms} \Big).
$$


## Operational restrictions

### Supply

Supply capacity restrictions:
- Supply is bounded above by a supply potential (Eq. 2a).
- Supply may have a lower bound (Eq. 2b), e.g. to reflect extraction from storage or supply by an electrolyzer.
- To ensure feasibility, we allow supply surpluses in Eq. 2b, which are typically heavily penalized in the objective function.

$$
Q_P \le \overline{Q}_P \qquad (2a)
$$

$$
Q_P \ge \underline{Q}_P - Z_U \qquad (2b)
$$



### Demand

Demand for each fuel must be met, at the nodal (Eq. 3a), country (Eq. 3b), EU (Eq. 3c), and/or total system level (Eq. 3d).

To ensure feasibility, we allow demand deficits (Eq. 3a–d), which are typically heavily penalized in the objective function.

**Nodal demand:**

$$
Q_S(n,e,y,h) + Z_D(n,e,y,h) = D(n,e,y,h) \qquad (3a)
$$

**Country-level demand:**

$$
\sum_{n \in N_c} Q_S(n,e,y,h) + Z_D(c,e,y,h) = D(c,e,y,h) \qquad (3b)
$$

**EU-level demand:**

$$
\sum_{n \in N_{EU}} Q_S(n,e,y,h) + Z_D(EU,e,y,h) = D(EU,e,y,h) \qquad (3c)
$$

**System-level demand:**

$$
\sum_{n \in N} Q_S(n,e,y,h) + Z_D(sys,e,y,h) = D(sys,e,y,h) \qquad (3d)
$$

> **Note:** Depending on the model setup, one or more of these demand aggregation levels are enforced.



### Mass balance

Hourly, fuel-specific nodal mass balance (Eq. 4) equates production plus loss-corrected inflows and storage extraction to deliveries, outflows and storage injection.

$$
\begin{aligned}
Q_P(n,e,y,h) + \sum_{a \in In(n)} \eta_{a,e} \, F_A(a,e,y,h) + Q_{W,ext}(n,e,y,h)
&= Q_S(n,e,y,h) + \sum_{a \in Out(n)} F_A(a,e,y,h) + Q_{W,inj}(n,e,y,h)
\end{aligned}
\qquad (4)
$$


### Storage bounds

We set lower and upper bounds for storage injection and extraction:

$$
\underline{Q}_{W,inj} \le Q_{W,inj} \le \overline{Q}_{W,inj} \qquad (5a)
$$

$$
\underline{Q}_{W,ext} \le Q_{W,ext} \le \overline{Q}_{W,ext} \qquad (5b)
$$


### Blending (TO DO)

We set an upper limit for the blending percentage (extension / to be implemented).

$$
\text{(Blending constraint to be added)} \qquad (5c)
$$


## Arc capacity and directionality

### Arc capacity

Volume-based arc capacity restricts the energy-based arc flow multiplied by an energy-to-volume conversion factor (Eq. 6). For bidirectional arcs, the capacity in the opposite direction is also available.

$$
F_A(a,e,y,h)\, vol2_a(e) \le K_A(a,e,y) + K_{OPP}(a,e,y) \qquad (6)
$$


### Bidirectional traversability

The capacity in the opposite direction is only available if the arc has been made bidirectional (Eq. 7a). In that case, the maximum available capacity is the capacity in the opposite direction (Eq. 7b). An arc is bidirectional if it was bidirectional in the previous period, or if it is made bidirectional in this period (Eq. 7c). We account for a fuel-specific volume-dependent cost component when making an arc bidirectional. This cost component considers the largest capacity that will be used in the opposite direction (Eq. 7d) in this or future periods.

$$
K_{OPP}(a,e,y) \le M \cdot BD(a,y) \qquad (7a)
$$

$$
K_{OPP}(a,e,y) \le K_A(\mathrm{rev}(a),e,y) \qquad (7b)
$$

$$
BD(a,y) \ge BD(a,\mathrm{pred}(y)) + B_B(a,y) \qquad (7c)
$$

$$
K_{BID}(a,e,y) \ge K_{OPP}(a,e,y') \quad \forall\, y' \in succ(y) \qquad (7d)
$$

Initialize `BD` for arcs that are bidirectional already.

## Repurposing

Directional fuel-specific arc capacity equals previous period arc capacity in the same direction that is repurposed or stays purposed for use by the specific fuel, plus fuel-specific arc expansion in the previous period (Eq. 8).

$$
\begin{aligned}
K_A(a,f,y) &=
\sum_{e \in E} K_A(a,e,\mathrm{pred}(y)) \, R(a,e,f,y) + X_A(a,f,\mathrm{pred}(y))
\end{aligned}
\qquad (8)
$$

Initialize the first-year capacity variables.

An arc can be repurposed to allow a different fuel to be transported via a specific arc capacity. (Continued dedication of the arc to the same fuel is done by setting the value for the appropriate index combination equal to 1.) We use binary variable to indicate the fuel `e` in previous year and the fuel `f` in year `y`. Fuel `e` and `f` may be equal, in which case no costs accrue.

A specific pipeline can be (re)purposed to carry one fuel type only:

$$
\sum_{f \in E} B_R(a,e,f,y) = 1 \qquad (9)
$$

No repurposing in the first year.

The refurbishment variables are bilinear. They can be computed using the following linearized expressions (Eq. 10a–b), which are a variant of the McCormick reformulation (1976):

$$
R(a,e,f,y) \le K_A(a,e,\mathrm{pred}(y)) \qquad (10a)
$$

$$
R(a,e,f,y) \le M \cdot B_R(a,e,f,y) \qquad (10b)
$$

Restriction (10a) guarantees that the repurposed capacity equals the previous period capacity. Restriction (10b) forces `B_R` to be active for the specific repurposing if the (re)purposed capacity is positive.

Storage usage is implemented; storage repurposing is a TO DO.


## Investment

Planned fuel-specific directional arc capacity expansion sets a lower bound on capacity expansion (Eq. 11a). Limits to infrastructure expansion set an upper bound to capacity expansion (in either direction) (Eq. 11b):

$$
X_A(a,e,y) \ge \underline{X}_A(a,e,y) \qquad (11a)
$$

$$
X_A(a,e,y) \le \overline{X}_A(a,y) \qquad (11b)
$$


