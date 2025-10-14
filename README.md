MFAnalysis — README

Overview
--------
This repository contains small utilities to collect, analyze and compare mutual fund portfolio holdings stored as CSV files under `fund_data`. It supports grouping of funds using `fund_groups.json` so you can run analyses for a named set (for example: `small`, `flexi`, `mid`).

Key scripts
-----------
- `main.py` — CLI entry point. Use to collect holdings, run share-based analysis, compute averages and compare months.
- `mf/mfCollect.py` — Collects and stores holdings for a list of funds.
- `mf/mfAnalyse.py` — Performs per-fund monthly trend analysis and consolidates trends across funds.
- `mf/mfAverage.py` — Calculates average holdings across funds and compares two months.
- `helper/folderAPI.py` — Creates directory structure under `fund_data` (group-aware).
- `fund_groups.json` — Optional JSON file mapping group names to lists of fund IDs.

Quick start
-----------
1. Ensure Python and dependencies are installed. The project uses a virtual environment located at `.venv` by convention.

   Example (zsh):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirement.txt
```

Note: pandas may not have prebuilt wheels for very new Python versions — if you see a Meson / build error, use Python 3.11 or 3.12 when creating the venv.

Commands and usage
------------------
All commands are invoked through `main.py` from the repository root. There are two ways to run commands:

1) Directly for the default fund list

```bash
python main.py <command> [args...]
```

2) Prefixed with a group name defined in `fund_groups.json` (recommended when you have multiple fund groups):

```bash
python main.py <group> <command> [args...]
```

Available commands
------------------
- collect
    - Description: Collect latest holdings for funds and store CSVs under `fund_data/<group>/holdings/<fund_id>/`.
    - Usage:
      - Default funds: `python main.py collect`
      - For a group: `python main.py small collect`

- analyze [months]
    - Description: Analyze share-based trends across the last N monthly files for each fund (default N=2).
    - Arguments: `[months]` (optional integer, default 2)
    - Outputs:
      - Per-fund trend CSVs: `fund_data/<group>/analysis/<fund_id>_trends_<timestamp>.csv`
      - Consolidated trends CSV and markdown summary: `fund_data/<group>/analysis/consolidated_trends_<timestamp>.csv` and `trend_summary_<timestamp>.md`
    - Usage examples:
      - Default: `python main.py analyze`
      - For a group and 3 months: `python main.py small analyze 3`

- average
    - Description: Compute average weight (percentage) of each stock across the selected funds. This mode divides the sum of weights by the total number of funds (including zeros — funds that don't hold the stock contribute zero).
    - Outputs: `fund_data/<group>/analysis/average_holdings_<timestamp>.csv`
    - Example: `python main.py small average`

- average_non_zero
    - Description: Compute average weight across only the funds that hold the stock (holders-only average). Stocks not held by a fund are ignored in the average for that stock.
    - Outputs: `fund_data/<group>/analysis/average_holdings_<timestamp>.csv`
    - Example: `python main.py small average_non_zero`

- avg_compare [prev_month] [curr_month] [--by-holders]
    - Description: Compare average allocations for two months and list which funds increased or decreased allocations for each stock.
    - Arguments:
      - `prev_month` and `curr_month` are optional. If omitted, the tool defaults to the previous full month -> current month (e.g., `2025-09` -> `2025-10`).
      - Accepts month as `YYYY-MM` or as a numeric month `9` (year assumed current year).
      - `--by-holders` flag: when provided, the comparison uses holders-only averaging (equivalent to `average_non_zero`).
    - Outputs: `fund_data/<group>/analysis/compare_<prev>_vs_<curr>_<timestamp>.csv`
    - Example usages:
      - Default (prev->curr):
        - `python main.py avg_compare`
      - Specify months:
        - `python main.py avg_compare 2025-08 2025-09`
        - `python main.py avg_compare 9 10`
      - Using group & holders-only average:
        - `python main.py small avg_compare --by-holders`

Group configuration (`fund_groups.json`)
---------------------------------------
`fund_groups.json` (optional) should be a JSON object mapping keys to arrays of fund IDs. Example:

```json
{
  "small": ["INF194KB1AL4", "INF966L01689"],
  "flexi": ["INF174K01LS2", "INF179K01UT0", "INF192K01CC7"],
  "mid": []
}
```

When a group key is present as the first CLI argument, the command runs for that group's funds and all outputs are written under `fund_data/<group>/...`.

Output locations
----------------
- Holdings are stored under: `fund_data/<group>/holdings/<fund_id>/holdings_YYYY-MM.csv`
- Analysis outputs are stored under: `fund_data/<group>/analysis/`
  - `consolidated_trends_<timestamp>.csv`
  - `trend_summary_<timestamp>.md`
  - `average_holdings_<timestamp>.csv`
  - `compare_<prev>_vs_<curr>_<timestamp>.csv`
  - `immediate_sells.csv` (appended when step-drops/exits are detected)

Troubleshooting
---------------
- pandas install/build errors:
  - If `pip install -r requirement.txt` fails with a Meson error while building pandas, create the virtualenv with Python 3.11 or 3.12 (these versions have more widely available prebuilt pandas wheels):

```bash
# example using system python3.11
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirement.txt
```

- If the CLI writes files into `fund_data/analysis` (root) as well as `fund_data/<group>/analysis`:
  - Ensure you pass a group key as the first argument (for group-scoped runs) and that `fund_groups.json` contains the mapping for that key.
  - The tools were recently updated to write group-scoped files under `fund_data/<group>/analysis`; if you observe mixed behavior, re-run the command and check that other scripts or manual code aren't calling `create_directory_structure()` without a `group`.

Extending groups
-----------------
- Edit `fund_groups.json` and add new keys mapping to arrays of fund IDs. No code changes required.