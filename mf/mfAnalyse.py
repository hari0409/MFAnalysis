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
    
def record_immediate_sells(fund_id, stock_name, shares_change, action_type):
    """Record immediate sells/exits to a separate file"""
    date_str = dt.datetime.now().strftime("%Y-%m-%d")
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
        existing_data = pd.read_csv(immediate_sells_file)
        updated_data = pd.concat([existing_data, new_entry], ignore_index=True)
    else:
        updated_data = new_entry
    
    updated_data.to_csv(immediate_sells_file, index=False)
  
def analyze_monthly_trends(holdings_list):
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
                record_immediate_sells(
                    fund_id=holdings_list[i]['fund_id'].iloc[0],
                    stock_name=stock,
                    shares_change=shares_change,
                    action_type=action_type
                )
            
            
            # Update appearances count
            if curr_shares > 0 or nxt_shares > 0:
                trend_matrix.loc[stock, 'appearances'] += 1
            
            # Calculate trend score based on share changes
            if curr_shares > 0 and nxt_shares > 0:
                # Both months have position
                share_change_pct = (curr_shares - nxt_shares) / nxt_shares * 100
                if share_change_pct >= 5:  # Significant increase (5% or more)
                    trend_matrix.loc[stock, 'trend_score'] += 1.0
                elif share_change_pct <= -5:  # Significant decrease (5% or more)
                    trend_matrix.loc[stock, 'trend_score'] -= 1.0
            elif curr_shares > 0 and nxt_shares == 0:
                # New position or complete addition
                trend_matrix.loc[stock, 'trend_score'] += 2.0
            elif curr_shares == 0 and nxt_shares > 0:
                # Complete exit
                trend_matrix.loc[stock, 'trend_score'] -= 2.0
            
            # Store most recent shares and change
            if i == 0:
                trend_matrix.loc[stock, 'current_shares'] = float(curr_shares)
                if nxt_shares > 0:
                    change_pct = ((curr_shares - nxt_shares) / nxt_shares * 100)
                    trend_matrix.loc[stock, 'share_change'] = change_pct
    
    return trend_matrix

def analyze_all_funds(fund_ids, considered_months):
    """Analyze holdings changes for all funds using share-based analysis"""
    dirs = create_directory_structure()
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

            # Calculate trend matrix for this fund
            fund_trend_matrix = analyze_monthly_trends(holdings_list)
            fund_trends[fund_id] = fund_trend_matrix

            # Update consolidated trends
            if consolidated_trends is None:
                consolidated_trends = fund_trend_matrix.copy()
            else:
                # Add new stocks to consolidated trends
                new_stocks = set(fund_trend_matrix.index) - set(consolidated_trends.index)
                if new_stocks:
                    new_rows = pd.DataFrame(
                        0,
                        index=list(new_stocks),
                        columns=consolidated_trends.columns
                    )
                    new_rows = new_rows.astype(consolidated_trends.dtypes)
                    consolidated_trends = pd.concat([consolidated_trends, new_rows])

                # Add missing stocks to current fund matrix
                missing_in_fund = set(consolidated_trends.index) - set(fund_trend_matrix.index)
                if missing_in_fund:
                    missing_rows = pd.DataFrame(
                        0,
                        index=list(missing_in_fund),
                        columns=consolidated_trends.columns
                    )
                    missing_rows = missing_rows.astype(consolidated_trends.dtypes)
                    fund_trend_matrix = pd.concat([fund_trend_matrix, missing_rows])

                # Update consolidated metrics
                consolidated_trends['trend_score'] += fund_trend_matrix['trend_score']
                consolidated_trends['appearances'] += fund_trend_matrix['appearances']
                consolidated_trends['current_shares'] += fund_trend_matrix['current_shares']

                # Update share_change with maximum absolute change
                for stock in consolidated_trends.index:
                    existing = consolidated_trends.at[stock, 'share_change']
                    new = fund_trend_matrix.at[stock, 'share_change']
                    if abs(new) > abs(existing):
                        consolidated_trends.at[stock, 'share_change'] = new

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
            # Save consolidated CSV
            output_file = os.path.join(dirs["analysis"],
                                       f"consolidated_trends_{dateTime}.csv")
            consolidated_trends.to_csv(output_file)

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
                        funds = strong_positive.loc[stock, 'appearances']
                        f.write(f"- {stock}:\n")
                        f.write(f"  * Score: {score:.1f}\n")
                        f.write(f"  * Current Shares: {shares:,.0f}\n")
                        f.write(f"  * Found in {funds:.0f} monthly reports\n")
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
                        funds = strong_negative.loc[stock, 'appearances']
                        f.write(f"- {stock}:\n")
                        f.write(f"  * Score: {score:.1f}\n")
                        f.write(f"  * Current Shares: {shares:,.0f}\n")
                        f.write(f"  * Found in {funds:.0f} monthly reports\n")
                        if abs(change) > 0:
                            f.write(f"  * Maximum Change: {change:+.1f}%\n")
                        f.write("\n")

            print(f"✅ Saved consolidated analysis and summary")
    else:
        print("❌ No fund had sufficient data for analysis")

    return fund_trends, consolidated_trends

