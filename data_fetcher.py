import os
import yfinance as yf
import pandas as pd
from datetime import datetime
import warnings
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

warnings.filterwarnings('ignore')

# Google Sheets Configuration (The Database Connection)
def connect_to_sheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # GitHub Secret-ல் இருந்து JSON டேட்டாவை நேரடியாக வாங்குவது
    creds_json = json.loads(os.environ.get('GCP_CREDENTIALS'))
    
    # File-க்கு பதிலாக Dict-ஐ பயன்படுத்துகிறோம்
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(creds)
    
    sheet_name = 'Phoenix_Market_Data'  
    sheet = client.open(sheet_name).sheet1
    return sheet

#def connect_to_sheets():
#    # உங்கள் credentials.json ஃபைல் இதே ஃபோல்டரில் இருக்க வேண்டும்
#    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
#    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
#    client = gspread.authorize(creds)
#    
#    # உங்கள் Google Sheet பெயர்
#    sheet_name = 'Phoenix_Market_Data'  # நீங்கள் உருவாக்கிய ஷீட்டின் பெயரை இங்கே மாற்றவும்
#    sheet = client.open(sheet_name).sheet1
#    return sheet

def fetch_nifty_data():
    print(f"🚀 Project Phoenix: Scanning Market at {datetime.now()}...\n")
    
    nifty_tickers = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", 
        "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
        "TATASTEEL.NS", "ZOMATO.NS", "SUZLON.NS", "IREDA.NS", "NHPC.NS" 
    ]
    
    data_records = []
    
    for ticker in nifty_tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            
            if len(hist) >= 2:
                today_close = hist['Close'].iloc[-1]
                yesterday_close = hist['Close'].iloc[-2]
                
                today_vol = hist['Volume'].iloc[-1]
                avg_vol_5days = hist['Volume'].mean()
                
                pct_change = ((today_close - yesterday_close) / yesterday_close) * 100
                
                data_records.append({
                    "Stock": ticker.replace('.NS', ''),
                    "LTP": round(today_close, 2),
                    "Change_Pct": round(pct_change, 2),
                    "Volume_Multiplier": round(today_vol / avg_vol_5days, 1),
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S") # எப்போது எடுத்தோம் என்று பதிய
                })
        except Exception as e:
            print(f"⚠️ Error fetching {ticker}: {e}")
            
    df = pd.DataFrame(data_records)
    
    # AI Filters
    print("🟢 TOP 3 GAINERS:")
    print(df.sort_values(by="Change_Pct", ascending=False).head(3).to_string(index=False), "\n")
    
    print("🔴 TOP 3 LOSERS:")
    print(df.sort_values(by="Change_Pct", ascending=True).head(3).to_string(index=False), "\n")
    
    return df

def push_to_google_sheets(df):
    try:
        sheet = connect_to_sheets()
        
        # DataFrame-ஐ List of Lists ஆக மாற்றுதல் (Google Sheet-க்கு புரியும் பார்மட்)
        # முதலில் Column பெயர்களைச் சேர்ப்போம்
        data_to_push = [df.columns.values.tolist()] + df.values.tolist()
        
        # ஷீட்டில் பழைய டேட்டா இருந்தால் அதை அழித்துவிட்டுப் புதிய டேட்டாவைப் போடலாம் 
        # (அல்லது append_row மூலம் தொடர்ந்து சேர்க்கலாம். இப்போதைக்கு க்ளியர் செய்வோம்)
        sheet.clear()
        
        # டேட்டாவை மொத்தமாக அப்டேட் செய்தல்
        sheet.update('A1', data_to_push)
        print("✅ Data successfully pushed to Google Sheets (Bronze Layer)!")
        
    except Exception as e:
         print(f"❌ Database Error: {e}")

if __name__ == "__main__":
    # 1. டேட்டாவை எடு
    final_data = fetch_nifty_data()
    # 2. டேட்டாபேஸில் தள்ளு
    push_to_google_sheets(final_data)
    print("\n✅ System Execution Completed Successfully!")