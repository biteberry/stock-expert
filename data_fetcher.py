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
    print(f"🚀 Project Phoenix V5.0: AI Inference Engine Starting...")
    
    # AI மாடலை லோட் செய்தல்
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

            # 1. Technical Indicators
            hist['RSI_14'] = ta.rsi(hist['Close'], length=14)
            hist['SMA_50'] = ta.sma(hist['Close'], length=50)
            today = hist.iloc[-1]
            yesterday = hist.iloc[-2]

            # 2. Basic Stats
            pct_change = ((today['Close'] - yesterday['Close']) / yesterday['Close']) * 100
            vol_multiplier = today['Volume'] / hist['Volume'].tail(10).mean()
            is_uptrend = 1 if today['Close'] > today['SMA_50'] else 0

            # 3. Regression Prediction (Short-term Trend)
            y_reg = hist['Close'].tail(10).values.reshape(-1, 1)
            x_reg = np.array(range(10)).reshape(-1, 1)
            reg_model = LinearRegression().fit(x_reg, y_reg)
            pred_pct = ((reg_model.predict([[10]])[0][0] - today['Close']) / today['Close']) * 100

            # 4. AI Confidence Score (The Master Brain)
            ai_score = 0
            if model:
                features = [[today['Close'], today['RSI_14'], today['SMA_50'], today['Volume']]]
                ai_score = model.predict_proba(features)[0][1] * 100

            data_records.append({
                "Stock": ticker.replace('.NS', ''),
                "LTP": round(today['Close'], 2),
                "Change_Pct": round(pct_change, 2),
                "Volume_Multiplier": round(vol_multiplier, 1),
                "RSI_14": round(today['RSI_14'], 2),
                "SMA_50": round(today['SMA_50'], 2),
                "Is_Uptrend": is_uptrend,
                "Pred_Next_Day_Pct": round(pred_pct, 2),
                "AI_Confidence": round(ai_score, 2),
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        except: continue
            
    return pd.DataFrame(data_records)

def push_to_google_sheets(df):
    sheet = connect_to_sheets()
    sheet.clear()
    sheet.update('A1', [df.columns.values.tolist()] + df.values.tolist())
    print("✅ Full V5.0 Data Pushed!")

if __name__ == "__main__":
    final_data = fetch_market_data()
    push_to_google_sheets(final_data)