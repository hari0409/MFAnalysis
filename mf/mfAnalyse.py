import datetime as dt
import pandas as pd
import os
from helper.dataAPI import *
from helper.folderAPI import *

def max_abs_change(row, fund_trend_matrix):
    if row.name in fund_trend_matrix.index:
        other_value = fund_trend_matrix.loc[row.name, 'share_change']
        return max(abs(row['share_change']), abs(other_value)) * (
            1 if abs(row['share_change']) >= abs(other_value)
            else (1 if other_value > 0 else -1)
        )
    else:
        return row['share_change']
    
def record_immediate_sells(fund_id, stock_name, shares_change, action_type, analysis_dir=None):
    """Record immediate sells/exits to a separate file.

    Writes the file under the provided analysis_dir when given, otherwise falls back
    to the legacy "fund_data/analysis" path.
    """
    date_str = dt.datetime.now().strftime("%Y-%m-%d")
    if analysis_dir:
        immediate_sells_file = os.path.join(analysis_dir, "immediate_sells.csv")
    else:
        immediate_sells_file = os.path.join("fund_data", "analysis", "immediate_sells.csv")

    # Create DataFrame for new entry
    new_entry = pd.DataFrame({
        'date': [date_str],
        'fund_id': [fund_id],
        'stock': [stock_name],
        'action': [action_type],
        'shares_change': [abs(shares_change)]
    })

    # Append or create file
    if os.path.exists(immediate_sells_file):
        try:
            existing_data = pd.read_csv(immediate_sells_file)
            updated_data = pd.concat([existing_data, new_entry], ignore_index=True)
        except Exception:
            # If file is corrupted or unreadable, overwrite
            updated_data = new_entry
    else:
        updated_data = new_entry

    updated_data.to_csv(immediate_sells_file, index=False)
  
def analyze_monthly_trends(holdings_list, analysis_dir=None):
    """
    Analyze month-to-month trends for each stock using share count
    Args:
        holdings_list: List of monthly holdings DataFrames (newest to oldest)
    Returns:
        DataFrame with trend scores for each stock
    """
    all_stocks = set()
    for holdings in holdings_list:
        all_stocks.update(holdings['security_name'].unique())
    
    # Initialize trend matrix with explicit dtypes
    trend_matrix = pd.DataFrame(
        index=list(all_stocks),
        columns={
            'trend_score': pd.Series(dtype='float64'),
            'appearances': pd.Series(dtype='int64'),
            'current_shares': pd.Series(dtype='float64'),
            'share_change': pd.Series(dtype='float64')
        }
    )
    
    # Initialize with correct data types
    trend_matrix['trend_score'] = 0.0
    trend_matrix['appearances'] = 0
    trend_matrix['current_shares'] = 0.0
    trend_matrix['share_change'] = 0.0
    
    # For each consecutive month pair
    for i in range(len(holdings_list) - 1):
        current_month = holdings_list[i]
        next_month = holdings_list[i + 1]
        
        current_shares = dict(zip(current_month['security_name'], 
                                current_month['number_of_shares'].astype(float)))
        next_shares = dict(zip(next_month['security_name'], 
                             next_month['number_of_shares'].astype(float)))
        
        for stock in all_stocks:
            curr_shares = current_shares.get(stock, 0.0)
            nxt_shares = next_shares.get(stock, 0.0)
            
            if curr_shares != nxt_shares:
                trend_matrix.loc[stock, 'has_changes'] = True
            
            # Check for sells/exits and record them
            if curr_shares < nxt_shares:
                action_type = 'decrease' if curr_shares > 0 else 'exit'
                shares_change = nxt_shares - curr_shares
                # record to the provided analysis_dir when available so group runs don't
                # write into the global analysis folder
                record_immediate_sells(
                    fund_id=holdings_list[i]['fund_id'].iloc[0],
                    stock_name=stock,
                    shares_change=shares_change,
                    action_type=action_type,
                    analysis_dir=analysis_dir
                )
            
            
            # Update appearances count
            if curr_shares > 0 or nxt_shares > 0:
                trend_matrix.loc[stock, 'appearances'] += 1

            # Update trend score by direction of change between months
            # (curr_shares is from the newer month, nxt_shares is from the older month)
            if curr_shares > nxt_shares:
                # Accumulation / increase
                trend_matrix.loc[stock, 'trend_score'] += 1.0
            elif curr_shares < nxt_shares:
                # Reduction / sell
                trend_matrix.loc[stock, 'trend_score'] -= 1.0
            
            # Store most recent shares and change
            if i == 0:
                trend_matrix.loc[stock, 'current_shares'] = float(curr_shares)
                if nxt_shares > 0:
                    change_pct = ((curr_shares - nxt_shares) / nxt_shares * 100)
                    trend_matrix.loc[stock, 'share_change'] = change_pct
    
    return trend_matrix

def analyze_all_funds(fund_ids, considered_months, group=None):
    """Analyze holdings changes for all funds using share-based analysis"""
    dirs = create_directory_structure(group=group)
    dateTime = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Store individual fund trends and consolidated trends
    fund_trends = {}
    consolidated_trends = None

    for fund_id in fund_ids:
        try:
            # Get all available holdings files
            fund_dir = os.path.join(dirs["holdings"], fund_id)
            files = sorted([f for f in os.listdir(fund_dir) if f.endswith('.csv')],
                           reverse=True)

            if len(files) < 2:
                print(f"⚠️  Skipping fund {fund_id}: Need at least 2 months of data (found {len(files)})")
                continue

            # Get the required number of files
            available_months = min(considered_months, len(files))
            relevant_files = files[:available_months]  # Already in reverse order

            print(f"📊 Analyzing {len(relevant_files)} months of data for fund {fund_id}")

            # Read all relevant holdings
            holdings_list = []
            for file in relevant_files:
                file_path = os.path.join(fund_dir, file)
                df = pd.read_csv(file_path)
                # Ensure proper data types for share analysis
                df['number_of_shares'] = df['number_of_shares'].astype(float)
                df['share_change'] = df['share_change'].astype(float)
                df['date'] = file.split('_')[1].split('.')[0]
                holdings_list.append(df)

            # Calculate trend matrix for this fund (pass analysis dir so temporary logs
            # like immediate_sells go into the group's analysis folder)
            fund_trend_matrix = analyze_monthly_trends(holdings_list, analysis_dir=dirs.get('analysis'))
            fund_trends[fund_id] = fund_trend_matrix

            # Update consolidated trends
            if consolidated_trends is None:
                # Start consolidated trends and add a `funds` column (set of fund_ids that contributed)
                consolidated_trends = fund_trend_matrix.copy()
                # initialize funds as sets where this fund contributed (non-zero trend_score or appearances)
                funds_col = []
                funds_entered_col = []
                funds_exited_col = []
                for stock in consolidated_trends.index:
                    ts = consolidated_trends.at[stock, 'trend_score']
                    ap = consolidated_trends.at[stock, 'appearances']
                    if (ts != 0) or (ap != 0):
                        funds_col.append(set([fund_id]))
                    else:
                        funds_col.append(set())

                    # classify entered vs exited by sign of trend_score
                    if ts > 0:
                        funds_entered_col.append(set([fund_id]))
                    else:
                        funds_entered_col.append(set())

                    if ts < 0:
                        funds_exited_col.append(set([fund_id]))
                    else:
                        funds_exited_col.append(set())

                consolidated_trends['funds'] = funds_col
                consolidated_trends['funds_entered'] = funds_entered_col
                consolidated_trends['funds_exited'] = funds_exited_col
                # initialize counts for averaging current_shares and share_change
                # count a fund for a stock if that fund had appearances > 0 for that stock
                cs_count = []
                sc_count = []
                for stock in consolidated_trends.index:
                    ap = consolidated_trends.at[stock, 'appearances']
                    # current_shares count: include if fund had the stock
                    # share_change count: include only if there was a non-zero share_change
                    try:
                        sc_val = float(consolidated_trends.at[stock, 'share_change'])
                    except Exception:
                        sc_val = 0.0
                    cs_count.append(1 if ap > 0 else 0)
                    sc_count.append(1 if abs(sc_val) > 0 else 0)
                consolidated_trends['current_shares_count'] = cs_count
                consolidated_trends['share_change_count'] = sc_count
            else:
                # Add new stocks to consolidated trends
                new_stocks = set(fund_trend_matrix.index) - set(consolidated_trends.index)
                if new_stocks:
                    # Create new rows for stocks that exist in this fund but not in consolidated_trends
                    new_rows = pd.DataFrame(
                        0,
                        index=list(new_stocks),
                        columns=[c for c in consolidated_trends.columns if c not in ('funds', 'funds_entered', 'funds_exited')]
                    )
                    # add empty funds sets for these new stocks
                    new_rows['funds'] = [set() for _ in range(len(new_rows))]
                    new_rows['funds_entered'] = [set() for _ in range(len(new_rows))]
                    new_rows['funds_exited'] = [set() for _ in range(len(new_rows))]
                    # initialize counts for averaging
                    new_rows['current_shares_count'] = [0 for _ in range(len(new_rows))]
                    new_rows['share_change_count'] = [0 for _ in range(len(new_rows))]
                    # Ensure dtype compatibility for numeric columns
                    for col in new_rows.columns:
                        if col not in ('funds', 'funds_entered', 'funds_exited'):
                            new_rows[col] = new_rows[col].astype(consolidated_trends[col].dtype)
                    consolidated_trends = pd.concat([consolidated_trends, new_rows])

                # Add missing stocks to current fund matrix
                missing_in_fund = set(consolidated_trends.index) - set(fund_trend_matrix.index)
                if missing_in_fund:
                    # Add missing stocks into the current fund matrix with zeros and empty funds set
                    missing_rows = pd.DataFrame(
                        0,
                        index=list(missing_in_fund),
                        columns=[c for c in consolidated_trends.columns if c not in ('funds', 'funds_entered', 'funds_exited')]
                    )
                    missing_rows['funds'] = [set() for _ in range(len(missing_rows))]
                    missing_rows['funds_entered'] = [set() for _ in range(len(missing_rows))]
                    missing_rows['funds_exited'] = [set() for _ in range(len(missing_rows))]
                    missing_rows['current_shares_count'] = [0 for _ in range(len(missing_rows))]
                    missing_rows['share_change_count'] = [0 for _ in range(len(missing_rows))]
                    for col in missing_rows.columns:
                        if col not in ('funds', 'funds_entered', 'funds_exited'):
                            missing_rows[col] = missing_rows[col].astype(consolidated_trends[col].dtype)
                    fund_trend_matrix = pd.concat([fund_trend_matrix, missing_rows])

                # Update consolidated metrics
                # Update aggregated numeric metrics
                consolidated_trends['trend_score'] += fund_trend_matrix['trend_score']
                consolidated_trends['appearances'] += fund_trend_matrix['appearances']

                # For current_shares and share_change, compute incremental averages across funds
                for stock in consolidated_trends.index:
                    # Update current_shares average if this fund had the stock (appearances > 0)
                    try:
                        fund_ap = int(fund_trend_matrix.at[stock, 'appearances'])
                    except Exception:
                        fund_ap = 0
                    if fund_ap > 0:
                        # current_shares average
                        new_cs = float(fund_trend_matrix.at[stock, 'current_shares'])
                        existing_cs = float(consolidated_trends.at[stock, 'current_shares'])
                        if 'current_shares_count' in consolidated_trends.columns:
                            try:
                                existing_cs_count = int(consolidated_trends.at[stock, 'current_shares_count'])
                            except Exception:
                                existing_cs_count = 0
                        else:
                            existing_cs_count = 0
                        updated_cs_count = existing_cs_count + 1
                        updated_cs = (existing_cs * existing_cs_count + new_cs) / updated_cs_count if updated_cs_count > 0 else new_cs
                        consolidated_trends.at[stock, 'current_shares'] = updated_cs
                        consolidated_trends.at[stock, 'current_shares_count'] = updated_cs_count

                        # share_change average
                        new_sc = float(fund_trend_matrix.at[stock, 'share_change'])
                        existing_sc = float(consolidated_trends.at[stock, 'share_change'])
                        if 'share_change_count' in consolidated_trends.columns:
                            try:
                                existing_sc_count = int(consolidated_trends.at[stock, 'share_change_count'])
                            except Exception:
                                existing_sc_count = 0
                        else:
                            existing_sc_count = 0
                        updated_sc_count = existing_sc_count + 1
                        updated_sc = (existing_sc * existing_sc_count + new_sc) / updated_sc_count if updated_sc_count > 0 else new_sc
                        consolidated_trends.at[stock, 'share_change'] = updated_sc
                        consolidated_trends.at[stock, 'share_change_count'] = updated_sc_count

                    # If this fund contributed to trend_score or appearances, add it to the funds set and classify entered/exited
                    try:
                        contributed = (fund_trend_matrix.at[stock, 'trend_score'] != 0) or (fund_trend_matrix.at[stock, 'appearances'] != 0)
                    except Exception:
                        contributed = False
                    if contributed:
                        # ensure the columns exist and are sets
                        for col_name in ('funds', 'funds_entered', 'funds_exited'):
                            if col_name not in consolidated_trends.columns:
                                consolidated_trends[col_name] = [set() for _ in range(len(consolidated_trends))]

                        if not isinstance(consolidated_trends.at[stock, 'funds'], set):
                            existing_val = consolidated_trends.at[stock, 'funds']
                            consolidated_trends.at[stock, 'funds'] = set(existing_val) if existing_val else set()
                        consolidated_trends.at[stock, 'funds'].add(fund_id)

                        # classify entered vs exited by the sign of the fund's trend_score for this stock
                        try:
                            sc = float(fund_trend_matrix.at[stock, 'trend_score'])
                        except Exception:
                            sc = 0.0
                        if sc > 0:
                            if not isinstance(consolidated_trends.at[stock, 'funds_entered'], set):
                                val = consolidated_trends.at[stock, 'funds_entered']
                                consolidated_trends.at[stock, 'funds_entered'] = set(val) if val else set()
                            consolidated_trends.at[stock, 'funds_entered'].add(fund_id)
                        elif sc < 0:
                            if not isinstance(consolidated_trends.at[stock, 'funds_exited'], set):
                                val = consolidated_trends.at[stock, 'funds_exited']
                                consolidated_trends.at[stock, 'funds_exited'] = set(val) if val else set()
                            consolidated_trends.at[stock, 'funds_exited'].add(fund_id)

        except Exception as e:
            print(f"❌ Error analyzing fund {fund_id}: {str(e)}")

    # Save results only if we have data
    if fund_trends:
        # Save individual fund trends
        for fund_id, trend_matrix in fund_trends.items():
            output_file = os.path.join(dirs["analysis"],
                                       f"{fund_id}_trends_{dateTime}.csv")
            trend_matrix.to_csv(output_file)
            print(f"✅ Saved trend analysis for {fund_id}")

        # Save consolidated trends and create summary report
        if consolidated_trends is not None:
            # Save consolidated CSV (convert funds sets to CSV-friendly strings)
            output_file = os.path.join(dirs["analysis"],
                                       f"consolidated_trends_{dateTime}.csv")
            ct_for_save = consolidated_trends.copy()
            def funds_to_str(x):
                if isinstance(x, set):
                    return ",".join(sorted(x)) if x else ""
                # if it's list-like or already string
                try:
                    return ",".join(sorted(x))
                except Exception:
                    return str(x)
            if 'funds' in ct_for_save.columns:
                ct_for_save['funds'] = ct_for_save['funds'].apply(funds_to_str)
            if 'funds_entered' in ct_for_save.columns:
                ct_for_save['funds_entered'] = ct_for_save['funds_entered'].apply(funds_to_str)
            if 'funds_exited' in ct_for_save.columns:
                ct_for_save['funds_exited'] = ct_for_save['funds_exited'].apply(funds_to_str)
            ct_for_save.to_csv(output_file)

            # Create summary markdown report
            summary_file = os.path.join(dirs["analysis"],
                                        f"trend_summary_{dateTime}.md")
            with open(summary_file, 'w') as f:
                f.write("# Holdings Trend Analysis (Share-based)\n\n")
                f.write(f"Period: {relevant_files[-1].split('_')[1].split('.')[0]} ")
                f.write(f"to {relevant_files[0].split('_')[1].split('.')[0]}\n\n")

                # Strong positive trends (significant share accumulation)
                strong_positive = consolidated_trends[
                    consolidated_trends['trend_score'] > 1].sort_values(
                    ['trend_score', 'current_shares'], ascending=[False, False])
                if not strong_positive.empty:
                    f.write("## 📈 Strong Share Accumulation\n")
                    for stock in strong_positive.index:
                        score = strong_positive.loc[stock, 'trend_score']
                        shares = strong_positive.loc[stock, 'current_shares']
                        change = strong_positive.loc[stock, 'share_change']
                        appearances = strong_positive.loc[stock, 'appearances']
                        funds_set = consolidated_trends.loc[stock, 'funds'] if 'funds' in consolidated_trends.columns else None
                        funds_list_str = ", ".join(sorted(funds_set)) if isinstance(funds_set, set) and funds_set else (str(funds_set) if funds_set else "")
                        entered_set = consolidated_trends.loc[stock, 'funds_entered'] if 'funds_entered' in consolidated_trends.columns else None
                        exited_set = consolidated_trends.loc[stock, 'funds_exited'] if 'funds_exited' in consolidated_trends.columns else None
                        entered_list = ", ".join(sorted(entered_set)) if isinstance(entered_set, set) and entered_set else ""
                        exited_list = ", ".join(sorted(exited_set)) if isinstance(exited_set, set) and exited_set else ""
                        f.write(f"- {stock}:\n")
                        f.write(f"  * Score: {score:.1f}\n")
                        f.write(f"  * Current Shares: {shares:,.0f}\n")
                        f.write(f"  * Found in {appearances:.0f} monthly reports\n")
                        if funds_list_str:
                            f.write(f"  * Funds: {funds_list_str}\n")
                        if entered_list:
                            f.write(f"  * Funds Entered: {entered_list}\n")
                        if exited_list:
                            f.write(f"  * Funds Exited: {exited_list}\n")
                        if abs(change) > 0:
                            f.write(f"  * Maximum Change: {change:+.1f}%\n")
                        f.write("\n")

                # Strong negative trends (significant share reduction)
                strong_negative = consolidated_trends[
                    consolidated_trends['trend_score'] < -1].sort_values(
                    ['trend_score', 'current_shares'])
                if not strong_negative.empty:
                    f.write("\n## 📉 Strong Share Reduction\n")
                    for stock in strong_negative.index:
                        score = strong_negative.loc[stock, 'trend_score']
                        shares = strong_negative.loc[stock, 'current_shares']
                        change = strong_negative.loc[stock, 'share_change']
                        appearances = strong_negative.loc[stock, 'appearances']
                        funds_set = consolidated_trends.loc[stock, 'funds'] if 'funds' in consolidated_trends.columns else None
                        funds_list_str = ", ".join(sorted(funds_set)) if isinstance(funds_set, set) and funds_set else (str(funds_set) if funds_set else "")
                        entered_set = consolidated_trends.loc[stock, 'funds_entered'] if 'funds_entered' in consolidated_trends.columns else None
                        exited_set = consolidated_trends.loc[stock, 'funds_exited'] if 'funds_exited' in consolidated_trends.columns else None
                        entered_list = ", ".join(sorted(entered_set)) if isinstance(entered_set, set) and entered_set else ""
                        exited_list = ", ".join(sorted(exited_set)) if isinstance(exited_set, set) and exited_set else ""
                        f.write(f"- {stock}:\n")
                        f.write(f"  * Score: {score:.1f}\n")
                        f.write(f"  * Current Shares: {shares:,.0f}\n")
                        f.write(f"  * Found in {appearances:.0f} monthly reports\n")
                        if funds_list_str:
                            f.write(f"  * Funds: {funds_list_str}\n")
                        if entered_list:
                            f.write(f"  * Funds Entered: {entered_list}\n")
                        if exited_list:
                            f.write(f"  * Funds Exited: {exited_list}\n")
                        if abs(change) > 0:
                            f.write(f"  * Maximum Change: {change:+.1f}%\n")
                        f.write("\n")

            print(f"✅ Saved consolidated analysis and summary")
    else:
        print("❌ No fund had sufficient data for analysis")

    return fund_trends, consolidated_trends