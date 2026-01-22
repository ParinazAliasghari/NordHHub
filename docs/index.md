# MGET – Multi-Gas Energy Transition Model

The MGET model is an optimization framework for analyzing investment and operation in integrated multi-gas energy networks. It covers natural gas, hydrogen, and CO₂ transport systems and represents production, consumption, conversion, storage, blending, repurposing, and pipeline expansion decisions.

This documentation describes the open-source Python implementation of MGET, based on the original GAMS formulation developed by Ruud Egging (NTNU).  
The Python version reproduces the core mathematical structure and introduces a modular and transparent workflow:

- Excel-based scenario inputs  
- Structured data loader  
- Pyomo model builder  
- Flexible reporting and CSV output

Math inline test: $x^2 + 1$

Math block test:

$$
x^2 + 1
$$


---

## Documentation Structure

### **1. Introduction**
Purpose of MGET, applications, network scope, and overall system representation.

### **2. Model Formulation**
Summary of the mathematical model (investment + operation):
- objective function  
- mass balance  
- arc/pipe capacities  
- storage  
- repurposing options  
- pipeline direction decisions  
- blending limits  
- multi-year investment horizon  
- representative operational hours  

(Full formulation is based on the document by Egging, 2024.)

### **3. Input Data Structure**
Description of the Excel scenario file:
- nodes  
- arcs and directions  
- fuels  
- supply and demand  
- capacities  
- costs and parameters  
- blending rules  
- losses and efficiency parameters

### **4. Python Implementation**
Overview of the codebase:
- data loading module  
- sets and parameters in Pyomo  
- variable definitions  
- constraints  
- objective function  
- solver options and runtime structure  

### **5. Running MGET**
Instructions for executing the model with a given Excel scenario.

### **6. Results and Outputs**
Explanation of the auto-generated CSVs:
- flows  
- injections  
- capacities  
- expansions  
- deficits  
- run logs  
- scenario folder structure  

---

This documentation will evolve as the Python implementation grows toward a fully open-source and reproducible version of MGET.
