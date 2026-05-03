import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime
import warnings
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import io
import os
import json

warnings.filterwarnings('ignore')

# NSE-ல் இருந்து Nifty 500 பட்டியலை எடுப்பது
def get_dynamic_nifty_500():
    print("🌐 Fetching latest Nifty 500 list from NSE Servers...")
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        df_nse = pd.read_csv(io.StringIO(response.text))
        tickers = [str(symbol) + ".NS" for symbol in df_nse['Symbol']]
        print(f"✅ Successfully loaded {len(tickers)} Nifty 500 stocks!\n")
        return tickers
    except Exception as e:
        print(f"⚠️ Error fetching NSE list: {e}")
        return ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS"]

# Google Sheets இணைப்பு
def connect_to_sheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        # GitHub Secrets-ல் இருந்து எடுப்பது
        creds_json = json.loads(os.environ.get('GCP_CREDENTIALS'))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    except:
        # லோக்கல் டெஸ்டிங்கிற்காக
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        
    client = gspread.authorize(creds)
    sheet_name = 'Phoenix_Market_Data'  
    sheet = client.open(sheet_name).sheet1
    return sheet

# மார்க்கெட் டேட்டாவை அனலைஸ் செய்வது (Phase 4 Logic)
def fetch_market_data():
    print(f"🚀 Project Phoenix V4.0: Predictive Data Scrape at {datetime.now()}...\n")
    nifty_tickers = get_dynamic_nifty_500()
    data_records = []
    
    for ticker in nifty_tickers:
        try:
            # இண்டிகேட்டர்களுக்காக 100 நாட்கள் டேட்டாவை எடுக்கிறோம்
            stock = yf.Ticker(ticker)
            hist = stock.history(period="100d")
            
            if len(hist) >= 50:
                # Technical Indicators கணக்கிடுதல்
                hist['RSI_14'] = ta.rsi(hist['Close'], length=14)
                hist['SMA_50'] = ta.sma(hist['Close'], length=50)
                hist['SMA_20'] = ta.sma(hist['Close'], length=20)
                
                today = hist.iloc[-1]
                yesterday = hist.iloc[-2]
                
                pct_change = ((today['Close'] - yesterday['Close']) / yesterday['Close']) * 100
                vol_multiplier = today['Volume'] / hist['Volume'].tail(10).mean()
                
                # AI Feature: Bullish Trend கண்டுபிடித்தல்
                is_uptrend = 1 if today['Close'] > today['SMA_50'] else 0
                
                data_records.append({
                    "Stock": ticker.replace('.NS', ''),
                    "LTP": round(today['Close'], 2),
                    "Change_Pct": round(pct_change, 2),
                    "Volume_Multiplier": round(vol_multiplier, 1),
                    "RSI_14": round(today['RSI_14'], 2) if not pd.isna(today['RSI_14']) else 50,
                    "SMA_50": round(today['SMA_50'], 2) if not pd.isna(today['SMA_50']) else 0,
                    "Is_Uptrend": is_uptrend,
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
        except Exception:
            continue
            
    df = pd.DataFrame(data_records)
    
    # கன்சோலில் முக்கிய விவரங்களைக் காண்பித்தல்
    print("🟢 MOMENTUM LEADERS (RSI > 60 & Volume Spike):")
    momentum = df[(df['RSI_14'] > 60) & (df['Volume_Multiplier'] > 1.5)].sort_values(by="Change_Pct", ascending=False).head(5)
    print(momentum.to_string(index=False) if not momentum.empty else "None found", "\n")
    
    return df

# டேட்டாவை Google Sheet-ல் அப்டேட் செய்தல்
def push_to_google_sheets(df):
    try:
        sheet = connect_to_sheets()
        data_to_push = [df.columns.values.tolist()] + df.values.tolist()
        sheet.clear()
        sheet.update('A1', data_to_push)
        print("✅ Gold Layer Data successfully pushed to Google Sheets!")
    except Exception as e:
         print(f"❌ Database Error: {e}")

if __name__ == "__main__":
    final_data = fetch_market_data()
    push_to_google_sheets(final_data)
    print("\n✅ Phase 4 Execution Completed Successfully!")