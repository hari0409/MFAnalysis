from helper.folderAPI import *
import datetime as dt
import pandas as pd
import os

def calculate_fund_averages(fund_ids, average_by_holders=False, group=None):
    """Calculate average weightage of stocks across all funds

    Args:
        fund_ids: list of fund ids
        average_by_holders: if True, average only across funds that hold the stock
            (i.e., divide by num_funds_holding). If False, divide by total number of funds.
    """
    dirs = create_directory_structure(group=group)
    dateTime = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Get latest holdings from all funds
    all_holdings = []
    total_funds = len(fund_ids)
    
    for fund_id in fund_ids:
        try:
            # Get most recent holdings file
            fund_dir = os.path.join(dirs["holdings"], fund_id)
            files = sorted([f for f in os.listdir(fund_dir) if f.endswith('.csv')],
                         reverse=True)
            
            if not files:
                print(f"⚠️  No data found for fund {fund_id}")
                continue
                
            # Read most recent holdings
            latest_file = os.path.join(fund_dir, files[0])
            df = pd.read_csv(latest_file)
            all_holdings.append(df)
            print(f"✅ Loaded latest holdings for {fund_id}")
            
        except Exception as e:
            print(f"❌ Error loading fund {fund_id}: {str(e)}")
    
    if all_holdings:
        try:
            # Combine all holdings
            combined_holdings = pd.concat(all_holdings, ignore_index=True)
            
            # Calculate average weightage
            avg_holdings = calculate_average_weightage(combined_holdings, total_funds, average_by_holders=average_by_holders)
            
            # Save average holdings analysis
            output_file = os.path.join(dirs["analysis"], 
                                     f"average_holdings_{dateTime}.csv")
            avg_holdings.to_csv(output_file)
            
            # Print summary
            print(f"\n✅ Analyzed holdings across {len(all_holdings)} funds")
            print("\nTop 10 holdings by average weight:")
            summary = avg_holdings[['security_name', 'avg_weight_pct', 
                                  'num_funds_holding', 'sector']].head(10)
            print(summary.to_string(index=False))
            
        except Exception as e:
            print(f"❌ Error calculating averages: {str(e)}")
    else:
        print("❌ No holdings data found")

def calculate_average_weightage(holdings_df, total_funds, average_by_holders=False):
    """
    Calculate average weightage of each stock across funds
    Args:
        holdings_df: Combined holdings DataFrame
        total_funds: Total number of funds being analyzed
    Returns:
        DataFrame with average weightage metrics
    """
    # Group by security and calculate metrics
    avg_holdings = (holdings_df.groupby(['security_name', 'isin', 'sector'])
                   .agg({
                       'weight_pct': 'sum',  # Sum of weights across funds
                       'fund_id': 'nunique'  # Number of funds holding the stock
                   })
                   .reset_index())
    
    # Rename columns
    avg_holdings.columns = ['security_name', 'isin', 'sector', 
                          'total_weight_pct', 'num_funds_holding']
    
    # Calculate average weight
    if average_by_holders:
        # divide by number of funds holding the stock (coverage-aware)
        # avoid division by zero
        avg_holdings['avg_weight_pct'] = avg_holdings.apply(
            lambda r: (r['total_weight_pct'] / r['num_funds_holding']) if r['num_funds_holding'] > 0 else 0.0,
            axis=1
        )
    else:
        # divide by total funds (include zeros)
        avg_holdings['avg_weight_pct'] = avg_holdings['total_weight_pct'] / total_funds
    
    # Calculate coverage percentage
    avg_holdings['coverage_pct'] = (avg_holdings['num_funds_holding'] / total_funds) * 100
    
    # Round numeric columns
    avg_holdings['avg_weight_pct'] = avg_holdings['avg_weight_pct'].round(2)
    avg_holdings['coverage_pct'] = avg_holdings['coverage_pct'].round(1)
    
    # Sort by average weight descending
    return avg_holdings.sort_values('avg_weight_pct', ascending=False)

def compare_months(prev_month=None, curr_month=None, fund_ids=None, average_by_holders=False, group=None):
    """
    Compare average allocations between two months.

    Args:
        prev_month: string like '2025-09' for the older month (files named holdings_2025-09.csv)
        curr_month: string like '2025-10' for the newer month
        fund_ids: optional list of fund ids to include; if None, all folders under holdings/ are used

    Produces a CSV in analysis/ with per-stock average change and lists of funds that increased/decreased allocation.
    """
    dirs = create_directory_structure(group=group)
    # helper to parse month input (accept 'YYYY-MM' or numeric month like '9' or 9)
    def _parse_month_arg(a):
        if a is None:
            return None
        a = str(a)
        if '-' in a and len(a.split('-')[0]) == 4:
            return a
        try:
            m = int(a)
            today = dt.date.today()
            year = today.year
            return f"{year}-{m:02d}"
        except Exception:
            raise ValueError(f"Invalid month argument: {a}")

    # Compute defaults if not provided
    if prev_month is None and curr_month is None:
        today = dt.date.today()
        curr_dt = dt.date(today.year, today.month, 1)
        prev_month_dt = (curr_dt.replace(day=1) - dt.timedelta(days=1)).replace(day=1)
        prev_month = prev_month_dt.strftime('%Y-%m')
        curr_month = curr_dt.strftime('%Y-%m')
    elif prev_month is None and curr_month is not None:
        # interpret curr_month and compute prev
        curr_month = _parse_month_arg(curr_month)
        y, m = map(int, curr_month.split('-'))
        curr_dt = dt.date(y, m, 1)
        prev_month_dt = (curr_dt.replace(day=1) - dt.timedelta(days=1)).replace(day=1)
        prev_month = prev_month_dt.strftime('%Y-%m')
    else:
        # both provided: parse both
        prev_month = _parse_month_arg(prev_month) if prev_month is not None else prev_month
        curr_month = _parse_month_arg(curr_month) if curr_month is not None else curr_month
    # discover funds if not provided
    if fund_ids is None:
        holdings_root = dirs['holdings']
        fund_ids = [d for d in os.listdir(holdings_root) if os.path.isdir(os.path.join(holdings_root, d))]

    total_funds = len(fund_ids)
    # per-fund dictionaries: fund -> {stock: weight_pct}
    prev_holdings = {}
    curr_holdings = {}

    for fund_id in fund_ids:
        prev_file = os.path.join(dirs['holdings'], fund_id, f"holdings_{prev_month}.csv")
        curr_file = os.path.join(dirs['holdings'], fund_id, f"holdings_{curr_month}.csv")
        try:
            if os.path.exists(prev_file):
                dfp = pd.read_csv(prev_file)
                prev_holdings[fund_id] = dict(zip(dfp['security_name'], dfp['weight_pct'].astype(float)))
            else:
                prev_holdings[fund_id] = {}
        except Exception:
            prev_holdings[fund_id] = {}
        try:
            if os.path.exists(curr_file):
                dfc = pd.read_csv(curr_file)
                curr_holdings[fund_id] = dict(zip(dfc['security_name'], dfc['weight_pct'].astype(float)))
            else:
                curr_holdings[fund_id] = {}
        except Exception:
            curr_holdings[fund_id] = {}

    # union of all stocks
    all_stocks = set()
    for d in (prev_holdings, curr_holdings):
        for f in d:
            all_stocks.update(d[f].keys())

    rows = []
    for stock in sorted(all_stocks):
        # compute per-fund weights (0 if missing)
        prev_weights = {f: prev_holdings.get(f, {}).get(stock, 0.0) for f in fund_ids}
        curr_weights = {f: curr_holdings.get(f, {}).get(stock, 0.0) for f in fund_ids}

        # average depending on mode
        if average_by_holders:
            # average only across funds that hold the stock
            holders_prev = [w for w in prev_weights.values() if w > 0]
            holders_curr = [w for w in curr_weights.values() if w > 0]
            avg_prev = sum(holders_prev) / len(holders_prev) if len(holders_prev) > 0 else 0.0
            avg_curr = sum(holders_curr) / len(holders_curr) if len(holders_curr) > 0 else 0.0
        else:
            # average across all funds (including zeros)
            avg_prev = sum(prev_weights.values()) / total_funds if total_funds > 0 else 0.0
            avg_curr = sum(curr_weights.values()) / total_funds if total_funds > 0 else 0.0
        delta = avg_curr - avg_prev
        pct_delta = (delta / avg_prev * 100) if avg_prev != 0 else (100.0 if delta > 0 else 0.0)

        funds_increased = [f for f in fund_ids if curr_weights[f] > prev_weights[f]]
        funds_decreased = [f for f in fund_ids if curr_weights[f] < prev_weights[f]]

        rows.append({
            'security_name': stock,
            'avg_prev_pct': round(avg_prev, 4),
            'avg_curr_pct': round(avg_curr, 4),
            'delta_pct': round(delta, 4),
            'pct_change_of_prev': round(pct_delta, 2),
            'funds_increased': ",".join(sorted(funds_increased)),
            'funds_decreased': ",".join(sorted(funds_decreased)),
            'num_funds_increased': len(funds_increased),
            'num_funds_decreased': len(funds_decreased)
        })

    result_df = pd.DataFrame(rows).sort_values('delta_pct', ascending=False)
    out_file = os.path.join(dirs['analysis'], f"compare_{prev_month}_vs_{curr_month}_{dt.datetime.now().strftime('%Y-%m-%d_%H%M%S')}.csv")
    result_df.to_csv(out_file, index=False)
    print(f"✅ Saved comparison to {out_file}")
    return result_df