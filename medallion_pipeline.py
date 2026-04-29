import os
import yfinance as yf
import pandas as pd
import ta
from datetime import datetime, timedelta

# Constants
STOCKS = ["TATASTEEL.NS", "SUNPHARMA.NS", "THANGAMAYL.NS"]
YEARS_OF_DATA = 2
BASE_DIR = "data"
BRONZE_DIR = os.path.join(BASE_DIR, "bronze")
SILVER_DIR = os.path.join(BASE_DIR, "silver")
GOLD_DIR = os.path.join(BASE_DIR, "gold")

def setup_directories():
    """Create the Medallion architecture directory structure."""
    for directory in [BRONZE_DIR, SILVER_DIR, GOLD_DIR]:
        os.makedirs(directory, exist_ok=True)
        print(f"Ensured directory exists: {directory}")

def fetch_bronze_data(ticker, start_date, end_date):
    """Fetch raw OHLCV data and save to Bronze layer."""
    print(f"[{ticker}] Fetching raw data from {start_date.date()} to {end_date.date()}...")
    df = yf.download(ticker, start=start_date, end=end_date, progress=False)
    
    if df.empty:
        print(f"[{ticker}] Warning: No data fetched!")
        return None
        
    bronze_path = os.path.join(BRONZE_DIR, f"{ticker}_raw.csv")
    df.to_csv(bronze_path)
    print(f"[{ticker}] Saved Bronze data to {bronze_path}")
    return bronze_path

def process_silver_data(ticker, bronze_path):
    """Clean data (handle NaNs, standard datetime, dtypes) and save to Silver layer."""
    print(f"[{ticker}] Processing Bronze -> Silver layer...")
    
    # Read raw data. yfinance sometimes uses MultiIndex columns depending on the version.
    # We read first row to check if 'Price' level exists
    header_check = pd.read_csv(bronze_path, nrows=0)
    if "Price" in header_check.columns or len(header_check.columns) > 0 and header_check.columns[0] == "Price":
        df = pd.read_csv(bronze_path, header=[0, 1], index_col=0)
    else:
        df = pd.read_csv(bronze_path, index_col=0)
    
    # Flatten MultiIndex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # 1. Standardize Datetime Index
    df.index = pd.to_datetime(df.index, utc=True)
    df.index = df.index.tz_convert('Asia/Kolkata').tz_localize(None) # Remove timezone for simplicity, keep IST time
    df.index.name = "Date"
    
    # 2. Verify and enforce data types
    numeric_cols = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
    available_cols = [c for c in numeric_cols if c in df.columns]
    for col in available_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 3. Handle Missing Values
    # Forward fill first (carry forward last known price), then backward fill (if starting with NaNs)
    df.ffill(inplace=True)
    df.bfill(inplace=True)
    
    silver_path = os.path.join(SILVER_DIR, f"{ticker}_cleaned.csv")
    df.to_csv(silver_path)
    print(f"[{ticker}] Saved Silver data to {silver_path}")
    return silver_path

def process_gold_data(ticker, silver_path):
    """Apply feature engineering (SMA, RSI, Volume trends) and save to Gold layer."""
    print(f"[{ticker}] Processing Silver -> Gold layer (Feature Engineering)...")
    df = pd.read_csv(silver_path, index_col=0, parse_dates=True)
    
    # Ensure data is sorted by date
    df.sort_index(inplace=True)
    
    # 1. 50-day Simple Moving Average (SMA)
    df['SMA_50'] = ta.trend.sma_indicator(df['Close'], window=50, fillna=False)
    
    # 2. Relative Strength Index (RSI-14)
    df['RSI_14'] = ta.momentum.rsi(df['Close'], window=14, fillna=False)
    
    # 3. Volume Trends (e.g., Volume 10-day SMA for comparison)
    df['Volume_SMA_10'] = ta.trend.sma_indicator(df['Volume'], window=10, fillna=False)
    df['Volume_Trend'] = (df['Volume'] > df['Volume_SMA_10']).astype(int) # 1 if volume is above 10-day average
    
    # ---------------------------------------------------------
    # NEW: Merge FII/DII Macro Data
    macro_file = os.path.join(BRONZE_DIR, "macro_fii_dii_activity.csv")
    if os.path.exists(macro_file):
        # Load the macro data
        df_macro = pd.read_csv(macro_file, index_col='Date', parse_dates=True)
        
        # Merge using a Left Join (keeps all stock trading days, adds macro data where available)
        df = df.join(df_macro, how='left')
        
        # Forward fill the macro data in case of weekend/holiday mismatches
        macro_cols = ['FII_Buy', 'FII_Sell', 'FII_Net', 'DII_Buy', 'DII_Sell', 'DII_Net']
        if all(c in df.columns for c in macro_cols):
            df[macro_cols] = df[macro_cols].ffill()
            df[macro_cols] = df[macro_cols].fillna(0) # Fill remaining NaNs at the start
    # ---------------------------------------------------------
    
    gold_path = os.path.join(GOLD_DIR, f"{ticker}_features.csv")
    df.to_csv(gold_path)
    print(f"[{ticker}] Saved Gold (AI-Ready) data to {gold_path}")
    return gold_path

def main():
    print("Starting Medallion Data Pipeline...")
    setup_directories()
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * YEARS_OF_DATA)
    
    for ticker in STOCKS:
        print(f"\n--- Processing {ticker} ---")
        bronze_path = fetch_bronze_data(ticker, start_date, end_date)
        if bronze_path:
            silver_path = process_silver_data(ticker, bronze_path)
            if silver_path:
                process_gold_data(ticker, silver_path)
                
    print("\nPipeline execution completed successfully!")

if __name__ == "__main__":
    main()
