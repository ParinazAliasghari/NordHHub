# Model overview

## Introduction

Given supply potentials and demand projections (at NUTS2 and/or country and/or EU level), for various gases (natural gas, hydrogen and carbon dioxide), repurpose (retrofit) and expand the European transport network (and storages) for various gases (mostly natural gas, some H2, some CO2). Minimize investment and operational costs, 2020–2050, five-year steps, considering representative hours. Gas networks (and storages) have NUTS2-level detail, for part or whole of Europe. :contentReference[oaicite:1]{index=1}

We consider a European-wide central planner TSO who minimizes costs while ensuring that all gas demands are met and the pipeline network (and storages) can accommodate the flows to bring various gases from supply nodes to demand nodes. In the network, each pipeline (and storage) is dedicated to a specific gas. The planner can invest in new pipelines (and storages), in repurposing existing pipelines (and storages) to become usable for another gas, and to make one-directional pipelines bidirectional. The model applies mixed integer programming. :contentReference[oaicite:2]{index=2}

Assume linear costs for production, transportation, investment, making bidirectional and repurposing. The latter two (bidirectional and repurposing) also have a fixed cost component, independent of capacity. :contentReference[oaicite:3]{index=3}

In the below we write fuel instead of gas, to avoid confusion about the one (natural) gas vs various gases or gas types. :contentReference[oaicite:4]{index=4}


## Storage operation (modes)

Model takes storage injection and extraction bounds as external input. Storages can be considered as supply or demand sources. In a specific operational hour, injected or extracted volumes are restricted within a range (or fixed at a specific value), depending on the season. :contentReference[oaicite:1]{index=1}

Model decides on storage repurposing and usage, and may consider seasonal balancing. This requires additional constraints connecting operational periods, hence the model will be much more complex. Numerical tractability may be considerably worse, and the model is unlikely to solve within reasonable time for the entire EU. :contentReference[oaicite:2]{index=2}


## Wishlist

Blending in H2 in gas (flow based, not capacity based). :contentReference[oaicite:7]{index=7}

## Investment and repurposing options

### Investment

Figure 1 provides two examples of investment. Figure 1a shows that an investment adds a fuel-specific arc (for “h”). Figure 1b illustrates that an arc has been made bidirectional (for “g”). :contentReference[oaicite:0]{index=0}

![Figure 1. MGET investment options examples.](assets/figures/fig1-investment-options.png)

*Figure 1. MGET investment options examples.* :contentReference[oaicite:1]{index=1}


### Repurposing

Figure 2 shows repurposing of arcs. Figure 2a indicates how a single arc (for “g”) is repurposed to transport another fuel (for “h”), whereas Figure 2b illustrates that repurposing of two arcs (for “c” and for “g”) to carry the same fuel (“h”) leads to aggregated capacity. :contentReference[oaicite:2]{index=2}

![Figure 2. MGET repurposing options examples.](assets/figures/fig2-repurposing-options.png)

*Figure 2. MGET repurposing options examples.* :contentReference[oaicite:3]{index=3}


### Time structure

Investment periods each contain one or more operational hours. Operational hours are decoupled from each other (because we do not model storage balances). Figure 3 illustrates the two period types considered in the model. :contentReference[oaicite:4]{index=4}

![Figure 3. MGET time structure: investment and operational periods.](assets/figures/fig3-time-structure.png)

*Figure 3. MGET time structure: investment and operational periods.* :contentReference[oaicite:5]{index=5}
