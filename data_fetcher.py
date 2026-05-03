import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime
import warnings
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import io
import os
import json
from sklearn.linear_model import LinearRegression # புதிய சேர்த்தல்

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
        creds_json = json.loads(os.environ.get('GCP_CREDENTIALS'))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    except:
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        
    client = gspread.authorize(creds)
    sheet_name = 'Phoenix_Market_Data'  
    sheet = client.open(sheet_name).sheet1
    return sheet

# மார்க்கெட் டேட்டாவை அனலைஸ் செய்வது (Regression Prediction சேர்த்தது)
def fetch_market_data():
    print(f"🚀 Project Phoenix V4.3: Trend Regression Scrape at {datetime.now()}...\n")
    nifty_tickers = get_dynamic_nifty_500()
    data_records = []
    
    for ticker in nifty_tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="100d")
            
            if len(hist) >= 50:
                # 1. Technical Indicators கணக்கிடுதல்
                hist['RSI_14'] = ta.rsi(hist['Close'], length=14)
                hist['SMA_50'] = ta.sma(hist['Close'], length=50)
                
                today = hist.iloc[-1]
                yesterday = hist.iloc[-2]
                
                pct_change = ((today['Close'] - yesterday['Close']) / yesterday['Close']) * 100
                vol_multiplier = today['Volume'] / hist['Volume'].tail(10).mean()
                is_uptrend = 1 if today['Close'] > today['SMA_50'] else 0
                
                # 2. Linear Regression Prediction (நாளை விலை என்னவாகும்?)
                # கடந்த 10 நாட்களின் குளோசிங் விலையை எடுக்கிறோம்
                y = hist['Close'].tail(10).values.reshape(-1, 1)
                x = np.array(range(10)).reshape(-1, 1)
                
                reg_model = LinearRegression().fit(x, y)
                # 11-வது நாளுக்கான (நாளை) விலையைக் கணிக்கிறோம்
                next_day_pred = reg_model.predict([[10]])[0][0]
                
                # கணிப்பின் படி எவ்வளவு % மாற்றம் வரும்?
                pred_pct_change = ((next_day_pred - today['Close']) / today['Close']) * 100
                
                data_records.append({
                    "Stock": ticker.replace('.NS', ''),
                    "LTP": round(today['Close'], 2),
                    "Change_Pct": round(pct_change, 2),
                    "Volume_Multiplier": round(vol_multiplier, 1),
                    "RSI_14": round(today['RSI_14'], 2) if not pd.isna(today['RSI_14']) else 50,
                    "SMA_50": round(today['SMA_50'], 2) if not pd.isna(today['SMA_50']) else 0,
                    "Is_Uptrend": is_uptrend,
                    "Pred_Next_Day_Pct": round(pred_pct_change, 2), # புதிய பிரெடிக்ஷன் காலம்
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
        except Exception:
            continue
            
    df = pd.DataFrame(data_records)
    return df

# டேட்டாவை Google Sheet-ல் அப்டேட் செய்தல்
def push_to_google_sheets(df):
    try:
        sheet = connect_to_sheets()
        data_to_push = [df.columns.values.tolist()] + df.values.tolist()
        sheet.clear()
        sheet.update('A1', data_to_push)
        print("✅ Prediction Data successfully pushed to Google Sheets!")
    except Exception as e:
         print(f"❌ Database Error: {e}")

if __name__ == "__main__":
    final_data = fetch_market_data()
    push_to_google_sheets(final_data)
    print("\n✅ Phase 4.3 Prediction Scan Completed Successfully!")