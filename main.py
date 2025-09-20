from mf.mfAnalyse import *
from mf.mfCollect import *

if __name__ == "__main__":
    fund_ids = ["INF846K01K35", "INF0QA701BK8", "INF761K01EP7", 
                "INF740K01QD1", "INF205K013T3"]
    
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "collect":
            collect_fund_data(fund_ids)
        elif sys.argv[1] == "analyze":
            # Get number of months to consider (default to 2 if not specified)
            considered_months = int(sys.argv[2]) if len(sys.argv) > 2 else 2
            analyze_all_funds(fund_ids, considered_months)
        else:
            print("Invalid argument. Use 'collect' or 'analyze [months]'")
    else:
        print("Please specify operation: collect or analyze [months]")