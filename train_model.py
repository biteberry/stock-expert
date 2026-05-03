import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib
from datetime import datetime, timedelta

def prepare_training_data():
    print("📥 Gathering 2 years of historical data for Nifty 500...")
    # தற்காலிகமாக Nifty 50-ஐ வைத்து ட்ரெய்ன் செய்வோம் (Speed-க்காக)
    tickers = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "SBI.NS", "BHARTIARTL.NS"] 
    
    all_data = []
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="2y") # 2 வருட டேட்டா
            
            if len(df) < 100: continue
            
            # Feature Engineering (அதே இண்டிகேட்டர்கள்)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['SMA_50'] = ta.sma(df['Close'], length=50)
            df['Vol_Avg'] = ta.sma(df['Volume'], length=10)
            
            # Target Labeling: அடுத்த 5 நாட்களில் 5% லாபம் கிடைக்குமா?[cite: 1]
            df['Future_Close'] = df['Close'].shift(-5)
            df['Target'] = ((df['Future_Close'] - df['Close']) / df['Close'] >= 0.05).astype(int)
            
            df.dropna(inplace=True)
            all_data.append(df)
        except:
            continue

    final_df = pd.concat(all_data)
    return final_df

def train_and_save_model():
    df = prepare_training_data()
    
    # Features (X) மற்றும் Target (y)
    features = ['Close', 'RSI', 'SMA_50', 'Volume']
    X = df[features]
    y = df['Target']
    
    print(f"🤖 Training Model on {len(df)} data points...")
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    # மாடலைச் சேமித்தல்[cite: 1]
    joblib.dump(model, 'stock_model.pkl')
    print("✅ Model saved as 'stock_model.pkl'!")

if __name__ == "__main__":
    train_and_save_model()