import datetime as dt
import mstarpy as ms
import pandas as pd
import os
from collections import defaultdict

def get_fund_holdings(fund_ids):
    """Fetch holdings data for multiple funds"""
    holdings_data = []
    
    for fund_id in fund_ids:
        try:
            fund = ms.Funds(fund_id).position()
            fund_name = fund_id
            
            for holding in fund["equityHoldingPage"]["holdingList"]:
                holdings_data.append({
                    'fund_id': fund_id,
                    'fund_name': fund_name,
                    'security_name': holding['securityName'],
                    'isin': holding.get('isin', ''),
                    'number_of_shares': float(holding['numberOfShare'] or 0.0),
                    'share_change': float(holding.get('shareChange', 0.0) or 0.0),
                    'sector': holding.get('sector', '')
                })
                
        except Exception as e:
            print(f"Error processing fund {fund_id}: {str(e)}")
            
    return pd.DataFrame(holdings_data)

def create_directory_structure(base_dir="fund_data"):
    """Create directory structure for storing fund data"""
    directories = {
        "holdings": os.path.join(base_dir, "holdings"),
        "analysis": os.path.join(base_dir, "analysis")
    }
    
    for dir_path in directories.values():
        os.makedirs(dir_path, exist_ok=True)
    
    return directories

def store_fund_holdings(fund_id, holdings_df, dirs):
    """Store holdings data for a specific fund"""
    date_str = dt.datetime.now().strftime("%Y-%m")
    fund_dir = os.path.join(dirs["holdings"], fund_id)
    os.makedirs(fund_dir, exist_ok=True)
    
    file_path = os.path.join(fund_dir, f"holdings_{date_str}.csv")
    holdings_df.to_csv(file_path, index=False)
    return file_path

def collect_fund_data(fund_ids):
    """Collect and store latest fund holdings data"""
    dirs = create_directory_structure()
    
    for fund_id in fund_ids:
        try:
            holdings = get_fund_holdings([fund_id])
            store_fund_holdings(fund_id, holdings, dirs)
            print(f"Successfully collected data for fund: {fund_id}")
        except Exception as e:
            print(f"Error collecting data for fund {fund_id}: {str(e)}")
       
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
            next_shares = next_shares.get(stock, 0.0)
            
            # Update appearances count
            if curr_shares > 0 or next_shares > 0:
                trend_matrix.loc[stock, 'appearances'] += 1
            
            # Calculate trend score based on share changes
            if curr_shares > 0 and next_shares > 0:
                # Both months have position
                share_change_pct = (curr_shares - next_shares) / next_shares * 100
                if share_change_pct >= 5:  # Significant increase (5% or more)
                    trend_matrix.loc[stock, 'trend_score'] += 1.0
                elif share_change_pct <= -5:  # Significant decrease (5% or more)
                    trend_matrix.loc[stock, 'trend_score'] -= 1.0
            elif curr_shares > 0 and next_shares == 0:
                # New position or complete addition
                trend_matrix.loc[stock, 'trend_score'] += 2.0
            elif curr_shares == 0 and next_shares > 0:
                # Complete exit
                trend_matrix.loc[stock, 'trend_score'] -= 2.0
            
            # Store most recent shares and change
            if i == 0:
                trend_matrix.loc[stock, 'current_shares'] = float(curr_shares)
                if next_shares > 0:
                    change_pct = ((curr_shares - next_shares) / next_shares * 100)
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
                
                # Update consolidated metrics
                consolidated_trends['trend_score'] += fund_trend_matrix['trend_score']
                consolidated_trends['appearances'] += fund_trend_matrix['appearances']
                consolidated_trends['current_shares'] += fund_trend_matrix['current_shares']
                # Take the maximum of absolute share changes
                consolidated_trends['share_change'] = consolidated_trends.apply(
                    lambda row: max(abs(row['share_change']), 
                                  abs(fund_trend_matrix.loc[row.name, 'share_change']), 
                                  key=abs) * (1 if row['share_change'] > 0 else -1), 
                    axis=1
                )
            
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