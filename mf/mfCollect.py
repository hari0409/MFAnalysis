from helper.dataAPI import *
from helper.folderAPI import *

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

