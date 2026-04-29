import os
import pandas as pd
from datetime import datetime
import nselib.capital_market.capital_market_data as cmd

# Directories
BASE_DIR = "data"
BRONZE_DIR = os.path.join(BASE_DIR, "bronze")
FII_DII_FILE = os.path.join(BRONZE_DIR, "macro_fii_dii_activity.csv")

def fetch_and_update_fii_dii():
    """
    Fetches the latest FII/DII activity from NSE and updates the historical dataset.
    Note: NSE libraries only provide current-day FII/DII data reliably. 
    For a full 1-year backfill, you should download a historical CSV from Moneycontrol 
    or StockEdge once, and let this script append to it daily.
    """
    print("Fetching latest FII/DII data using nselib...")
    
    try:
        # Fetch the latest FII/DII data
        latest_data = cmd.fii_dii_trading_activity()
        
        # Standardize the date
        # Assuming nselib returns date format like '28-Apr-2026'
        latest_data['Date'] = pd.to_datetime(latest_data['date']).dt.normalize()
        
        # Pivot the data so we have columns: Date, FII_Buy, FII_Sell, FII_Net, DII_Buy, DII_Sell, DII_Net
        pivot_data = {}
        date_val = latest_data['Date'].iloc[0]
        pivot_data['Date'] = date_val
        
        for _, row in latest_data.iterrows():
            category = row['category'].split('/')[0] # 'FII' or 'DII'
            pivot_data[f'{category}_Buy'] = float(row['buyValue'])
            pivot_data[f'{category}_Sell'] = float(row['sellValue'])
            pivot_data[f'{category}_Net'] = float(row['netValue'])
            
        df_latest = pd.DataFrame([pivot_data])
        df_latest.set_index('Date', inplace=True)
        
        # Append to existing historical data or create new
        if os.path.exists(FII_DII_FILE):
            print(f"Found existing data at {FII_DII_FILE}, appending new data...")
            df_historical = pd.read_csv(FII_DII_FILE, index_col='Date', parse_dates=['Date'])
            
            # Update/Append the new row (this overwrites if the date already exists)
            df_combined = pd.concat([df_historical, df_latest])
            df_combined = df_combined[~df_combined.index.duplicated(keep='last')]
            df_combined.sort_index(inplace=True)
        else:
            print("No historical data found. Creating new file...")
            df_combined = df_latest
            
        # Save back to Bronze
        df_combined.to_csv(FII_DII_FILE)
        print(f"Successfully saved FII/DII data to {FII_DII_FILE}")
        
    except Exception as e:
        print(f"Error fetching FII/DII data: {e}")

if __name__ == "__main__":
    # Ensure bronze directory exists
    os.makedirs(BRONZE_DIR, exist_ok=True)
    fetch_and_update_fii_dii()
