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
    
    # நிபந்தனை: கீழ் நிழல் உடலை விட 2 மடங்கு பெரியதாக இருக்க வேண்டும், மேல் நிழல் மிகச் சிறியதாக இருக்க வேண்டும்
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
    print(f"🚀 Project Phoenix V6.0: Price Action & AI Engine Starting...")
    
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

            # 2. OHLC Data
            open_val = round(today['Open'], 2)
            high_val = round(today['High'], 2)
            low_val = round(today['Low'], 2)
            close_val = round(today['Close'], 2)

            # 3. Candlestick Pattern: Hammer
            hammer_signal = is_hammer(open_val, close_val, high_val, low_val)

            # 4. Support & Resistance (Pivot Logic based on 20-day High/Low)
            recent_hist = hist.tail(20)
            resistance = round(recent_hist['High'].max(), 2)
            support = round(recent_hist['Low'].min(), 2)

            # 5. Resistance Breakout Detection[cite: 4]
            # இன்றைய க்ளோசிங், கடந்த 20 நாள் அதிகபட்ச விலையைத் தாண்டினால் அது Breakout.
            is_breakout = 1 if close_val >= resistance else 0

            # 6. Basic Stats & AI Scoring[cite: 4]
            pct_change = ((close_val - yesterday['Close']) / yesterday['Close']) * 100
            vol_multiplier = today['Volume'] / hist['Volume'].tail(10).mean()
            is_uptrend = 1 if close_val > today['SMA_50'] else 0

            # 7. Regression Prediction (Short-term Trend)[cite: 4]
            y_reg = hist['Close'].tail(10).values.reshape(-1, 1)
            x_reg = np.array(range(10)).reshape(-1, 1)
            reg_model = LinearRegression().fit(x_reg, y_reg)
            pred_pct = ((reg_model.predict([[10]])[0][0] - close_val) / close_val) * 100

            # 8. AI Confidence Score[cite: 4]
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
                "Change_Pct": round(pct_change, 2),
                "Vol_Mult": round(vol_multiplier, 1),
                "Is_Hammer": hammer_signal,
                "Support": support,
                "Resistance": resistance,
                "Is_Breakout": is_breakout,
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
    try:
        sheet = connect_to_sheets()
        sheet.clear()
        sheet.update('A1', [df.columns.values.tolist()] + df.values.tolist())
        print("✅ Phase 6 Data Pushed Successfully!")
    except Exception as e:
        print(f"❌ Sheet Update Error: {e}")

if __name__ == "__main__":
    final_data = fetch_market_data()
    push_to_google_sheets(final_data)