from mf.mfAnalyse import *
from mf.mfCollect import *
from mf.mfAverage import *

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
            calculate_fund_averages(fund_ids)
        else:
            print("Invalid argument. Use 'collect', 'analyze [months]', or 'average'")
    else:
        print("Please specify operation: collect, analyze [months], or average")