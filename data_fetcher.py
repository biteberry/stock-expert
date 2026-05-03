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
from sklearn.linear_model import LinearRegression
import joblib

warnings.filterwarnings('ignore')

# Hammer Candle கண்டுபிடிக்கும் லாஜிக்
def is_hammer(open_p, close_p, high_p, low_p):
    body = abs(close_p - open_p)
    lower_shadow = min(open_p, close_p) - low_p
    upper_shadow = high_p - max(open_p, close_p)
    if body > 0 and lower_shadow > (2 * body) and upper_shadow < (0.5 * body):
        return 1
    return 0

def get_dynamic_nifty_500():
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        df_nse = pd.read_csv(io.StringIO(response.text))
        return [str(symbol) + ".NS" for symbol in df_nse['Symbol']]
    except:
        return ["RELIANCE.NS", "TCS.NS"]

def connect_to_sheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        creds_json = json.loads(os.environ.get('GCP_CREDENTIALS'))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    except:
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    return client.open('Phoenix_Market_Data').sheet1

def fetch_market_data():
    print(f"🚀 Project Phoenix V6.1.1: Debug Mode Starting...")
    
    try:
        model = joblib.load('stock_model.pkl')
        print("✅ AI Brain Loaded!")
    except Exception as e:
        print(f"⚠️ Model Load Error: {e}")
        model = None

    nifty_tickers = get_dynamic_nifty_500()
    # டெஸ்டிங்கிற்காக முதல் 10 ஸ்டாக்குகளை மட்டும் முதலில் பார்ப்போம்
    test_tickers = nifty_tickers[:10] 
    data_records = []
    
    for ticker in test_tickers:
        try:
            print(f"🔍 Checking {ticker}...")
            stock = yf.Ticker(ticker)
            hist = stock.history(period="100d")
            
            if hist.empty or len(hist) < 50:
                print(f"❌ {ticker}: Not enough data (Length: {len(hist)})")
                continue

            # Indicators கணக்கிடும்போது எர்ரர் வருகிறதா என்று பார்க்க
            hist['RSI_14'] = ta.rsi(hist['Close'], length=14)
            hist['SMA_50'] = ta.sma(hist['Close'], length=50)
            
            if hist['RSI_14'].isnull().all():
                print(f"❌ {ticker}: RSI Calculation failed")
                continue

            today = hist.iloc[-1]
            yesterday = hist.iloc[-2]
            
            # OHLC & Logic (முந்தைய கோடில் உள்ளது போல...)
            close_val = round(today['Close'], 2)
            recent_hist = hist.tail(20)
            support_val = round(recent_hist['Low'].min(), 2)
            
            # Risk-Reward 
            risk_amt = close_val - support_val
            stop_loss = support_val if risk_amt > 0 else round(close_val * 0.98, 2)
            target_1_2 = round(close_val + (2 * risk_amt), 2) if risk_amt > 0 else round(close_val * 1.04, 2)

            data_records.append({
                "Stock": ticker.replace('.NS', ''),
                "LTP": close_val,
                "Support_SL": stop_loss,
                "Target_1_2": target_1_2,
                "AI_Confidence": 0 # தற்காலிகமாக 0 வைப்போம்
            })
            print(f"✅ {ticker}: Added successfully")

        except Exception as e:
            print(f"💥 {ticker} Error: {str(e)}")
            continue
            
    print(f"\n📊 Total Records Captured: {len(data_records)}")
    return pd.DataFrame(data_records)


def push_to_google_sheets(df):
    try:
        sheet = connect_to_sheets()
        
        # 1. பழைய டேட்டாவை முழுமையாக நீக்குதல்
        sheet.clear()
        
        # 2. NaN மதிப்புகளை காலியான ஸ்ட்ரிங்காக மாற்றுதல் (இல்லையெனில் எர்ரர் வரும்)
        df = df.fillna('')
        
        # 3. ஹெடர் மற்றும் டேட்டாவை தயார் செய்தல்
        data_to_push = [df.columns.values.tolist()] + df.values.tolist()
        
        # 4. புதிய முறையைப் பயன்படுத்தி அப்டேட் செய்தல்
        # .update() என்பதற்கு பதில் .update_cells() அல்லது ஸ்ட்ரிங் ரேஞ்ச் பயன்படுத்துதல்
        sheet.update(f'A1', data_to_push)
        
        print(f"✅ Success: {len(df)} rows pushed to Google Sheets!")
    except Exception as e:
        print(f"❌ Critical Error in Sheet Update: {e}")

if __name__ == "__main__":
    final_data = fetch_market_data()
    push_to_google_sheets(final_data)