import mstarpy as ms
import pandas as pd
import os
import datetime as dt

def get_fund_holdings(fund_ids):
    """
    Fetch holdings data for multiple funds including both shares and weights
    Returns: DataFrame with complete holdings data
    """
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
                    'weight_pct': float(holding.get('weighting', 0.0) or 0.0),
                    'sector': holding.get('sector', '')
                })
                
        except Exception as e:
            print(f"❌ Error processing fund {fund_id}: {str(e)}")
            continue
            
    if not holdings_data:
        print("⚠️  No holdings data collected")
        return pd.DataFrame()
        
    df = pd.DataFrame(holdings_data)
    
    # Ensure proper data types
    df['number_of_shares'] = pd.to_numeric(df['number_of_shares'], errors='coerce').fillna(0.0)
    df['share_change'] = pd.to_numeric(df['share_change'], errors='coerce').fillna(0.0)
    df['weight_pct'] = pd.to_numeric(df['weight_pct'], errors='coerce').fillna(0.0)
    
    return df

def store_fund_holdings(fund_id, holdings_df, dirs):
    """
    Store holdings data for a specific fund
    Args:
        fund_id: Fund identifier
        holdings_df: DataFrame containing holdings data
        dirs: Directory structure dictionary
    Returns:
        str: Path to saved file
    """
    try:
        date_str = dt.datetime.now().strftime("%Y-%m")
        fund_dir = os.path.join(dirs["holdings"], fund_id)
        os.makedirs(fund_dir, exist_ok=True)
        
        file_path = os.path.join(fund_dir, f"holdings_{date_str}.csv")
        
        # Ensure all required columns are present
        required_columns = [
            'fund_id', 'fund_name', 'security_name', 'isin',
            'number_of_shares', 'share_change', 'weight_pct', 'sector'
        ]
        
        for col in required_columns:
            if col not in holdings_df.columns:
                holdings_df[col] = None
        
        holdings_df.to_csv(file_path, index=False)
        print(f"✅ Saved holdings for {fund_id} to {file_path}")
        return file_path
        
    except Exception as e:
        print(f"❌ Error saving holdings for {fund_id}: {str(e)}")
        return None