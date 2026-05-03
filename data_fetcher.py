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
    print(f"🚀 Project Phoenix V6.5: Full Production Master Starting...")
    
    try:
        model = joblib.load('stock_model.pkl')
        print("✅ AI Brain Loaded!")
    except Exception as e:
        print(f"⚠️ Model Load Error: {e}")
        model = None

    nifty_tickers = get_dynamic_nifty_500()
    data_records = []
    
    for ticker in nifty_tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="100d")
            
            if hist.empty or len(hist) < 50:
                continue

            # Indicators கணக்கிடுதல்
            hist['RSI_14'] = ta.rsi(hist['Close'], length=14)
            hist['SMA_50'] = ta.sma(hist['Close'], length=50)
            
            today = hist.iloc[-1]
            yesterday = hist.iloc[-2]
            
            # 1. OHLC & Change Pct
            open_val = round(today['Open'], 2)
            high_val = round(today['High'], 2)
            low_val = round(today['Low'], 2)
            close_val = round(today['Close'], 2)
            # Metric Card-க்கு மிக முக்கியமான 'Change_Pct'
            pct_change = ((close_val - yesterday['Close']) / yesterday['Close']) * 100
            
            # 2. Risk-Reward Logic (1:2)
            recent_hist = hist.tail(20)
            resistance = round(recent_hist['High'].max(), 2)
            support_val = round(recent_hist['Low'].min(), 2)
            
            risk_amt = close_val - support_val
            stop_loss = support_val if risk_amt > 0 else round(close_val * 0.98, 2)
            target_1_2 = round(close_val + (2 * risk_amt), 2) if risk_amt > 0 else round(close_val * 1.04, 2)
            profit_pct = round(((target_1_2 - close_val) / close_val) * 100, 2)

            # 3. AI Confidence Score
            ai_score = 0
            if model and not pd.isna(today['RSI_14']):
                features = [[close_val, today['RSI_14'], today['SMA_50'], today['Volume']]]
                ai_score = model.predict_proba(features)[0][1] * 100

            # 4. Next Day Prediction Logic (Regression)[cite: 7]
            y_reg = hist['Close'].tail(10).values.reshape(-1, 1)
            x_reg = np.array(range(10)).reshape(-1, 1)
            reg_model = LinearRegression().fit(x_reg, y_reg)
            pred_pct = ((reg_model.predict([[10]])[0][0] - close_val) / close_val) * 100

            # 5. Data Records-ல் அனைத்தையும் சேர்த்தல்[cite: 7]
            data_records.append({
                "Stock": ticker.replace('.NS', ''),
                "Open": open_val,
                "High": high_val,
                "Low": low_val,
                "LTP": close_val,
                "Change_Pct": round(pct_change, 2),  # மீண்டும் சேர்க்கப்பட்டது[cite: 7]
                "Support_SL": stop_loss,
                "Target_1_2": target_1_2,
                "Profit_Pct": profit_pct,
                "Is_Hammer": is_hammer(open_val, close_val, high_val, low_val),
                "Is_Breakout": 1 if close_val >= resistance else 0,
                "Is_Uptrend": 1 if close_val > today['SMA_50'] else 0,
                "Pred_Next_Day_Pct": round(pred_pct, 2), # மீண்டும் சேர்க்கப்பட்டது[cite: 7]
                "AI_Confidence": round(ai_score, 2),
                "RSI_14": round(today['RSI_14'], 2),
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

        except Exception:
            continue
            
    print(f"📊 Total Records Captured: {len(data_records)}")
    return pd.DataFrame(data_records)

def push_to_google_sheets(df):
    try:
        sheet = connect_to_sheets()
        sheet.clear()
        df = df.fillna('')
        data_to_push = [df.columns.values.tolist()] + df.values.tolist()
        sheet.update('A1', data_to_push)
        print(f"✅ Success: {len(df)} rows pushed to Google Sheets!")
    except Exception as e:
        print(f"❌ Critical Error in Sheet Update: {e}")

if __name__ == "__main__":
    final_data = fetch_market_data()
    if not final_data.empty:
        push_to_google_sheets(final_data)