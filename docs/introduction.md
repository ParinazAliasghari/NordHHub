# MGET – Multigas Energy Transition Model

The **Multigas Energy Transition (MGET)** model is an open-source Python optimization framework
for analyzing, planning, and transforming gas and energy networks.  
It is designed to support energy transition studies by representing multiple fuels, long-term
infrastructure investment, and hourly operational dynamics in a single integrated model.

MGET is implemented using **Pyomo** and formulated as a **linear or mixed-integer linear
optimization problem**. The framework follows a transparent, modular design:

- **Data Loading Module**  
  Reads an Excel scenario containing nodes, arcs, technologies, fuels, costs, and demand.

- **Model Builder Module**  
  Defines all sets, parameters, variables, objective functions, and constraints.

- **Reporting Module**  
  Extracts results and exports structured CSV files for flows, production, investments, and deficits.

The model is designed to be general, reproducible, and extensible, making it suitable for research,
scenario exploration, and open-access energy system analysis.
