# Streamlit web apps using Financial Toolkit

This repository contains several web apps that demonstrate common use cases in investment management, leveraging the [Financial Toolkit](https://github.com/khalidnaami3-wq).

## 🚀 Getting Started

Follow these steps to set up and run the applications on your local machine.

### 1. Prerequisites

- Ensure you have [Python 3.9+](https://www.python.org/downloads/) installed.

### 2. Setup Environment

Open your terminal (PowerShell or Command Prompt) and run:

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
.\venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

You can run the unified dashboard to access all apps in one place:

```bash
streamlit run main.py
```

_Alternatively, on Windows, you can just double-click the `run.bat` file._

---

## 📱 Included Applications

### 1. Market Index Data (`indices.py`)

Retrieves data on major equity indices and currencies.
[View App](https://financial-dashboard-analysis.streamlit.app/indices)

### 2. Fama-French Factor Analysis (`factors.py`)

Analyzes fund factor loadings using the Fama-French model.
[View App](https://financial-dashboard-analysis.streamlit.app/factors)

### 3. Portfolio Optimization (`portfolio.py`)

Compares risk–reward profiles of various weighting schemes.
[View App](https://financial-dashboard-analysis.streamlit.app/portfolio)

### 4. Peer Group Analysis (`peers.py`)

Compares fund performance against benchmarks and peers.
[View App](https://financial-dashboard-analysis.streamlit.app/peers)

### 5. Option Strategies (`options.py`)

Calculates values and Greeks for various option strategies.
[View App](https://financial-dashboard-analysis.streamlit.app/options)

---

Visit my [GitHub](https://github.com/khalidnaami3-wq) repository or [Streamlit](https://share.streamlit.io/user/khalidnaami3-wq) profile for source code and more apps like this.
