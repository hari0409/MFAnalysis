from mf.mfAnalyse import *
from mf.mfCollect import *
from mf.mfAverage import *
import datetime as _dt
import os

if __name__ == "__main__":
    # default fund ids (will be overridden if a group is provided)
    default_fund_ids = ["INF194KB1AL4","INF966L01689","INF204K01K15","INF247L01BY3","INF179KA1RZ8","INF663L01W06","INF205K013T3","INF277K011O1","INF846K01K35","INF917K01QA1"]

    # load fund groups if present
    groups_file = 'fund_groups.json'
    group_map = {}
    fund_name_map = {}
    try:
        import json
        if os.path.exists(groups_file):
            with open(groups_file, 'r') as gf:
                raw_group_map = json.load(gf)
                # Extract fund_ids and build name mapping
                for group_name, funds_list in raw_group_map.items():
                    processed_funds = []
                    for fund in funds_list:
                        if isinstance(fund, dict):
                            # New format: {"id":"...", "name":"..."}
                            fund_id = fund.get('id')
                            fund_name = fund.get('name', fund_id)
                            processed_funds.append(fund_id)
                            fund_name_map[fund_id] = fund_name
                        else:
                            # Legacy format: just the fund ID string
                            processed_funds.append(fund)
                            if fund not in fund_name_map:
                                fund_name_map[fund] = fund
                    group_map[group_name] = processed_funds
    except Exception:
        group_map = {}
        fund_name_map = {}

    import sys
    # detect if first arg is a group name
    selected_group = None
    args = sys.argv[1:]
    if len(args) >= 1 and args[0] in group_map:
        selected_group = args[0]
        fund_ids = group_map[selected_group]
        # shift args so following parsing sees the command
        args = args[1:]
    else:
        fund_ids = default_fund_ids

    if len(args) > 0:
        cmd = args[0]
        # remaining args for command handlers
        cmd_args = args[1:]
        if cmd == "collect":
            collect_fund_data(fund_ids, group=selected_group)
        elif cmd == "analyze":
            considered_months = int(cmd_args[0]) if len(cmd_args) > 0 else 2
            analyze_all_funds(fund_ids, considered_months, group=selected_group, fund_name_map=fund_name_map)
        elif cmd == "average":
            # average across all funds including zeros
            calculate_fund_averages(fund_ids, average_by_holders=False, group=selected_group)
            # run comparison using same averaging mode (defaults to prev->curr months)
            try:
                df = compare_months(None, None, fund_ids, average_by_holders=False, group=selected_group)
                print(df.head(10).to_string(index=False))
            except Exception as e:
                print(f"Comparison failed: {e}")
        elif cmd == "average_non_zero":
            # average only across funds that hold the stock
            calculate_fund_averages(fund_ids, average_by_holders=True, group=selected_group)
            # run comparison using same averaging mode
            try:
                df = compare_months(None, None, fund_ids, average_by_holders=True, group=selected_group)
                print(df.head(10).to_string(index=False))
            except Exception as e:
                print(f"Comparison failed: {e}")
        elif cmd == "avg_compare":
            # support optional mode flag: --by-holders to average only non-zero holders
            prev_arg = None
            curr_arg = None
            average_by_holders = False
            cargs = cmd_args[:]
            # parse flags at end
            if '--by-holders' in cargs:
                average_by_holders = True
                cargs = [a for a in cargs if a != '--by-holders']
            if len(cargs) >= 1:
                prev_arg = cargs[0]
            if len(cargs) >= 2:
                curr_arg = cargs[1]
            try:
                df = compare_months(prev_arg, curr_arg, fund_ids, average_by_holders=average_by_holders, group=selected_group)
                print(df.head(10).to_string(index=False))
            except Exception as e:
                print(f"Error: {e}\nUsage examples:\n  python3 main.py avg_compare\n  python3 main.py avg_compare 9 10\n  python3 main.py avg_compare 2025-09 2025-10\n  python3 main.py avg_compare --by-holders\n  python3 main.py avg_compare 9 10 --by-holders")
        else:
            print("Invalid argument. Use 'collect', 'analyze [months]', or 'average'")
    else:
        print("Please specify operation: collect, analyze [months], or average")