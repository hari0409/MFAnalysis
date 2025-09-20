import mstarpy as ms
import pandas as pd
import os
import datetime as dt

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

def store_fund_holdings(fund_id, holdings_df, dirs):
    """Store holdings data for a specific fund"""
    date_str = dt.datetime.now().strftime("%Y-%m")
    fund_dir = os.path.join(dirs["holdings"], fund_id)
    os.makedirs(fund_dir, exist_ok=True)
    
    file_path = os.path.join(fund_dir, f"holdings_{date_str}.csv")
    holdings_df.to_csv(file_path, index=False)
    return file_path
