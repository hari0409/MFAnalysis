from helper.folderAPI import *
import datetime as dt
import pandas as pd
import os

# def calculate_average_holdings(holdings_df):
#     """
#     Calculate both share-based and weight-based averages across funds
#     Args:
#         holdings_df: DataFrame containing holdings data
#     Returns:
#         DataFrame with combined average metrics
#     """
#     # Group by security and calculate metrics
#     avg_holdings = (holdings_df.groupby(['security_name', 'isin', 'sector'])
#                    .agg({
#                        'weight_pct': ['mean', 'std'],  # Weight-based metrics
#                        'number_of_shares': ['sum', 'mean', 'std'],  # Share-based metrics
#                        'fund_id': 'nunique'  # Count number of funds holding
#                    })
#                    .reset_index())
    
#     # Flatten column names
#     avg_holdings.columns = [
#         'security_name', 'isin', 'sector',
#         'avg_weight', 'weight_std',
#         'total_shares', 'avg_shares', 'shares_std',
#         'num_funds_holding'
#     ]
    
#     # Normalize weights to sum to 100%
#     total_weight = avg_holdings['avg_weight'].sum()
#     avg_holdings['avg_weight'] = (avg_holdings['avg_weight'] / total_weight) * 100
    
#     # Calculate share percentage
#     total_shares = avg_holdings['total_shares'].sum()
#     avg_holdings['share_pct'] = (avg_holdings['total_shares'] / total_shares) * 100
    
#     # Round numeric columns
#     avg_holdings['avg_weight'] = avg_holdings['avg_weight'].round(2)
#     avg_holdings['weight_std'] = avg_holdings['weight_std'].round(2)
#     avg_holdings['share_pct'] = avg_holdings['share_pct'].round(2)
#     avg_holdings['avg_shares'] = avg_holdings['avg_shares'].round(0)
#     avg_holdings['shares_std'] = avg_holdings['shares_std'].round(0)
    
#     # Sort by share percentage descending
#     return avg_holdings.sort_values(['share_pct', 'avg_weight'], ascending=[False, False])    
    
# def calculate_fund_averages(fund_ids):
#     """Calculate average holdings across all funds"""
#     dirs = create_directory_structure()
#     dateTime = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
#     # Get latest holdings from all funds
#     all_latest_holdings = []
    
#     for fund_id in fund_ids:
#         try:
#             # Get most recent holdings file
#             fund_dir = os.path.join(dirs["holdings"], fund_id)
#             files = sorted([f for f in os.listdir(fund_dir) if f.endswith('.csv')],
#                          reverse=True)
            
#             if not files:
#                 print(f"⚠️  No data found for fund {fund_id}")
#                 continue
                
#             # Read most recent holdings
#             latest_file = os.path.join(fund_dir, files[0])
#             df = pd.read_csv(latest_file)
#             df['weight_pct'] = df['weight_pct'].astype(float)
#             all_latest_holdings.append(df)
#             print(f"✅ Loaded latest holdings for {fund_id}")
            
#         except Exception as e:
#             print(f"❌ Error loading fund {fund_id}: {str(e)}")
    
#     if all_latest_holdings:
#         try:
#             # Combine latest holdings from all funds
#             combined_holdings = pd.concat(all_latest_holdings, ignore_index=True)
            
#             # Calculate average holdings
#             avg_holdings = calculate_average_holdings(combined_holdings)
            
#             # Save average holdings analysis
#             output_file = os.path.join(dirs["analysis"], 
#                                      f"average_holdings_{dateTime}.csv")
#             avg_holdings.to_csv(output_file)
#             print(f"\n✅ Saved average holdings analysis across {len(all_latest_holdings)} funds")
            
#             # Print summary
#             print("\nTop 10 holdings by average weight:")
#             print(avg_holdings[['security_name', 'avg_weight', 'num_funds_holding']]
#                   .head(10).to_string(index=False))
            
#         except Exception as e:
#             print(f"❌ Error calculating averages: {str(e)}")
#     else:
#         print("❌ No holdings data found for any fund")

def calculate_fund_averages(fund_ids):
    """Calculate average weightage of stocks across all funds"""
    dirs = create_directory_structure()
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
            avg_holdings = calculate_average_weightage(combined_holdings, total_funds)
            
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

def calculate_average_weightage(holdings_df, total_funds):
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
    
    # Calculate average weight (accounting for funds not holding the stock)
    avg_holdings['avg_weight_pct'] = avg_holdings['total_weight_pct'] / total_funds
    
    # Calculate coverage percentage
    avg_holdings['coverage_pct'] = (avg_holdings['num_funds_holding'] / total_funds) * 100
    
    # Round numeric columns
    avg_holdings['avg_weight_pct'] = avg_holdings['avg_weight_pct'].round(2)
    avg_holdings['coverage_pct'] = avg_holdings['coverage_pct'].round(1)
    
    # Sort by average weight descending
    return avg_holdings.sort_values('avg_weight_pct', ascending=False)