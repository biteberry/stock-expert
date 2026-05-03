import yfinance as yf
import pandas as pd
from datetime import datetime
import warnings
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import io

warnings.filterwarnings('ignore')

# --- புதிய அப்டேட்: Nifty 500-ஐ ஆட்டோமேட்டிக்காக எடுப்பது ---
def get_dynamic_nifty_500():
    print("🌐 Fetching latest Nifty 500 list from NSE Servers...")
    # NSE-ன் அதிகாரப்பூர்வ Nifty 500 CSV லிங்க்
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    
    # NSE சர்வர் நம்மை 'Bot' என்று தடுத்துவிடாமல் இருக்க ஒரு User-Agent அனுப்புகிறோம்
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        # CSV டேட்டாவை Pandas DataFrame ஆக மாற்றுதல்
        df_nse = pd.read_csv(io.StringIO(response.text))
        
        # Yahoo Finance-க்கு புரியும் படி '.NS' என்று சேர்ப்பது (எ.கா: TCS -> TCS.NS)
        tickers = [str(symbol) + ".NS" for symbol in df_nse['Symbol']]
        print(f"✅ Successfully loaded {len(tickers)} Nifty 500 stocks!\n")
        return tickers
        
    except Exception as e:
        print(f"⚠️ Error fetching NSE list: {e}")
        # எப்போதாவது NSE சர்வர் டவுன் ஆனால், Backup ஆக Nifty 50-ஐ மட்டும் கொடுப்போம்
        print("Using fallback Nifty 50 list...")
        return ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS"]

def connect_to_sheets():
    # GitHub Secret-ல் இருந்து JSON டேட்டாவை நேரடியாக வாங்குவது
    import os
    import json
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    try:
        # GitHub-ல் ரன் ஆகும்போது
        creds_json = json.loads(os.environ.get('GCP_CREDENTIALS'))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    except:
        # உங்கள் லோக்கலில் ரன் ஆகும்போது
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        
    client = gspread.authorize(creds)
    sheet_name = 'Phoenix_Market_Data'  
    sheet = client.open(sheet_name).sheet1
    return sheet

def fetch_market_data():
    print(f"🚀 Project Phoenix V2.0: Dynamic Scan Started at {datetime.now()}...\n")
    
    # ஹார்ட்கோட் செய்த லிஸ்ட்டுக்குப் பதிலாக, நமது புதிய ஃபங்ஷனை கூப்பிடுகிறோம்!
    nifty_tickers = get_dynamic_nifty_500()
    
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
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
        except Exception as e:
            pass # 500 கம்பெனிகள் எடுப்பதால், சின்ன சின்ன எரர்களைப் பிரிண்ட் செய்ய வேண்டாம்
            
    df = pd.DataFrame(data_records)
    
    print("🟢 TOP 5 GAINERS (Momentum Engine):")
    print(df.sort_values(by="Change_Pct", ascending=False).head(5).to_string(index=False), "\n")
    
    print("🔴 TOP 5 LOSERS (Reversal Radar):")
    print(df.sort_values(by="Change_Pct", ascending=True).head(5).to_string(index=False), "\n")
    
    print("💎 HIDDEN GEMS (Price < ₹500 & Volume Breakout > 1.5x):")
    hidden_gems = df[(df["LTP"] < 500) & (df["Volume_Multiplier"] > 1.5)]
    if not hidden_gems.empty:
        print(hidden_gems.sort_values(by="Change_Pct", ascending=False).head(5).to_string(index=False), "\n")
    else:
        print("No hidden gems found today.\n")
        
    return df

def push_to_google_sheets(df):
    try:
        sheet = connect_to_sheets()
        data_to_push = [df.columns.values.tolist()] + df.values.tolist()
        sheet.clear()
        sheet.update('A1', data_to_push)
        print("✅ 500 Stocks Data successfully pushed to Google Sheets (Bronze Layer)!")
    except Exception as e:
         print(f"❌ Database Error: {e}")

if __name__ == "__main__":
    final_data = fetch_market_data()
    push_to_google_sheets(final_data)
    print("\n✅ Full Market Scan Completed Successfully!")