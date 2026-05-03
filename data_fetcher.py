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
    print(f"🚀 Project Phoenix V6.1: Risk-Management Engine Starting...")
    try:
        model = joblib.load('stock_model.pkl')
        print("✅ AI Brain Loaded!")
    except:
        print("⚠️ AI Brain not found!")
        model = None

    nifty_tickers = get_dynamic_nifty_500()
    data_records = []
    
    for ticker in nifty_tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="100d")
            if len(hist) < 50: continue

            today = hist.iloc[-1]
            yesterday = hist.iloc[-2]
            
            # 1. OHLC & Basic Stats
            open_val = round(today['Open'], 2)
            high_val = round(today['High'], 2)
            low_val = round(today['Low'], 2)
            close_val = round(today['Close'], 2)
            pct_change = ((close_val - yesterday['Close']) / yesterday['Close']) * 100
            vol_multiplier = today['Volume'] / hist['Volume'].tail(10).mean()

            # 2. Support & Resistance (Pivot Logic)
            recent_hist = hist.tail(20)
            resistance = round(recent_hist['High'].max(), 2)
            support_val = round(recent_hist['Low'].min(), 2)

            # 3. Risk-Reward 1:2 Prediction Logic
            # Risk = இன்றைய விலை - சப்போர்ட் (Stop Loss)
            risk_amt = close_val - support_val
            
            if risk_amt > 0:
                stop_loss = support_val
                # Target = இன்றைய விலை + (2 * ரிஸ்க்)
                target_1_2 = round(close_val + (2 * risk_amt), 2)
            else:
                # விலை சப்போர்ட்டிற்கு கீழே இருந்தால் 2% SL மற்றும் 4% Target
                stop_loss = round(close_val * 0.98, 2)
                target_1_2 = round(close_val * 1.04, 2)
            
            potential_profit = round(((target_1_2 - close_val) / close_val) * 100, 2)

            # 4. Indicators & AI
            hist['RSI_14'] = ta.rsi(hist['Close'], length=14)
            hist['SMA_50'] = ta.sma(hist['Close'], length=50)
            is_uptrend = 1 if close_val > today['SMA_50'] else 0
            
            ai_score = 0
            if model:
                features = [[close_val, today['RSI_14'], today['SMA_50'], today['Volume']]]
                ai_score = model.predict_proba(features)[0][1] * 100

            data_records.append({
                "Stock": ticker.replace('.NS', ''),
                "Open": open_val,
                "High": high_val,
                "Low": low_val,
                "LTP": close_val,
                "Support_SL": stop_loss,
                "Target_1_2": target_1_2,
                "Profit_Pct": potential_profit,
                "Is_Hammer": is_hammer(open_val, close_val, high_val, low_val),
                "Is_Breakout": 1 if close_val >= resistance else 0,
                "AI_Confidence": round(ai_score, 2),
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        except: continue
            
    return pd.DataFrame(data_records)

def push_to_google_sheets(df):
    try:
        sheet = connect_to_sheets()
        sheet.clear()
        sheet.update('A1', [df.columns.values.tolist()] + df.values.tolist())
        print("✅ Risk-Management Data Pushed!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    final_data = fetch_market_data()
    push_to_google_sheets(final_data)