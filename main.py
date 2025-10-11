from mf.mfAnalyse import *
from mf.mfCollect import *
from mf.mfAverage import *
import datetime as _dt

if __name__ == "__main__":
    fund_ids = ["INF194KB1AL4","INF966L01689","INF204K01K15","INF247L01BY3","INF179KA1RZ8","INF663L01W06","INF205K013T3","INF277K011O1","INF846K01K35","INF917K01QA1"]
    
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "collect":
            collect_fund_data(fund_ids)
        elif sys.argv[1] == "analyze":
            considered_months = int(sys.argv[2]) if len(sys.argv) > 2 else 2
            analyze_all_funds(fund_ids, considered_months)
        elif sys.argv[1] == "average":
            # average across all funds including zeros
            calculate_fund_averages(fund_ids, average_by_holders=False)
            # run comparison using same averaging mode (defaults to prev->curr months)
            try:
                df = compare_months(None, None, fund_ids, average_by_holders=False)
                print(df.head(10).to_string(index=False))
            except Exception as e:
                print(f"Comparison failed: {e}")
        elif sys.argv[1] == "average_non_zero":
            # average only across funds that hold the stock
            calculate_fund_averages(fund_ids, average_by_holders=True)
            # run comparison using same averaging mode
            try:
                df = compare_months(None, None, fund_ids, average_by_holders=True)
                print(df.head(10).to_string(index=False))
            except Exception as e:
                print(f"Comparison failed: {e}")
        elif sys.argv[1] == "avg_compare":
            # avg_compare behavior:
            # - No args: compare previous month -> current month (based on today)
            # - One arg: treat it as current month, compare (current-1) -> current
            # - Two args: treat as <prev> <curr>
            # Month formats accepted: 'YYYY-MM' or numeric month (e.g., 9 or 09) which uses current year
            def _parse_month_arg(a):
                # return 'YYYY-MM' string
                a = str(a)
                if '-' in a and len(a.split('-')[0]) == 4:
                    return a
                try:
                    m = int(a)
                    today = _dt.date.today()
                    year = today.year
                    return f"{year}-{m:02d}"
                except Exception:
                    raise ValueError(f"Invalid month argument: {a}")

            # Pass raw args (or None) to compare_months which will compute defaults
            # support optional mode flag: --by-holders to average only non-zero holders
            prev_arg = None
            curr_arg = None
            average_by_holders = False
            args = sys.argv[2:]
            # parse flags at end
            if '--by-holders' in args:
                average_by_holders = True
                args = [a for a in args if a != '--by-holders']
            if len(args) >= 1:
                prev_arg = args[0]
            if len(args) >= 2:
                curr_arg = args[1]
            try:
                df = compare_months(prev_arg, curr_arg, fund_ids, average_by_holders=average_by_holders)
                print(df.head(10).to_string(index=False))
            except Exception as e:
                print(f"Error: {e}\nUsage examples:\n  python3 main.py avg_compare\n  python3 main.py avg_compare 9 10\n  python3 main.py avg_compare 2025-09 2025-10\n  python3 main.py avg_compare --by-holders\n  python3 main.py avg_compare 9 10 --by-holders")
        else:
            print("Invalid argument. Use 'collect', 'analyze [months]', or 'average'")
    else:
        print("Please specify operation: collect, analyze [months], or average")