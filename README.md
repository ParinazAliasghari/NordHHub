# NordHHub

**Multigas Network Optimization Model (Python)**  
Data Loader · Model Builder · Reporting System · Documentation

---

## 📁 Project Structure

### **1. `data/` — Input Scenarios**
This folder contains Excel files defining model inputs.

- **`mget_input_scenario.xlsx`** – Main scenario file with nodes, arcs, fuels, costs, and demand data.

---

### **2. `src/` — Python Source Code**

| File | Description |
|------|-------------|
| **`mget_load_data.py`** | Reads the Excel scenario and prepares all parameter dictionaries. |
| **`mget_main_model.py`** | Main script: builds the Pyomo model, solves it, and calls reporting. |
| **`report.py`** | Reporting module: creates CSV outputs + run-log tracking system. |

---

### **3. `results/` — Auto-Generated Output**

Each scenario gets its own folder:



