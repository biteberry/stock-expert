import yfinance as yf
import pandas as pd
from datetime import datetime
import warnings

# தேவையற்ற வார்னிங் மெசேஜ்களை மறைக்க
warnings.filterwarnings('ignore')

def fetch_nifty_data():
    print(f"🚀 Project Phoenix: Scanning Market at {datetime.now()}...\n")
    
    # Step 1: Nifty 50 கம்பெனிகளின் குறியீடுகள் (Demo-விற்காக Nifty 50. Nifty 500-க்கும் இதே லாஜிக்தான்)
    # yfinance-ல் இந்தியப் பங்குகளுக்கு ".NS" என்று முடிய வேண்டும்.
    nifty_tickers = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", 
        "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
        "TATASTEEL.NS", "ZOMATO.NS", "SUZLON.NS", "IREDA.NS", "NHPC.NS" # சில Small/Mid caps
    ]
    
    data_records = []
    
    # Step 2: ஒவ்வொரு சர்வராக (Stock) பிங் செய்து டேட்டாவை எடுப்பது
    for ticker in nifty_tickers:
        try:
            stock = yf.Ticker(ticker)
            # கடந்த 2 நாட்களின் டேட்டாவை எடுக்கிறோம் (நேற்றைய விலையை ஒப்பிட)
            hist = stock.history(period="5d")
            
            if len(hist) >= 2:
                # பிரைஸ் மற்றும் வால்யூம் கால்குலேஷன்
                today_close = hist['Close'].iloc[-1]
                yesterday_close = hist['Close'].iloc[-2]
                
                today_vol = hist['Volume'].iloc[-1]
                avg_vol_5days = hist['Volume'].mean()
                
                # சதவீதம் எவ்வளவு ஏறியுள்ளது/இறங்கியுள்ளது?
                pct_change = ((today_close - yesterday_close) / yesterday_close) * 100
                
                data_records.append({
                    "Stock": ticker.replace('.NS', ''),
                    "LTP (₹)": round(today_close, 2),
                    "Change (%)": round(pct_change, 2),
                    "Volume Multiplier": round(today_vol / avg_vol_5days, 1)
                })
        except Exception as e:
            print(f"⚠️ Error fetching {ticker}: {e}")
            
    # Step 3: டேட்டாவை Pandas DataFrame-ஆக மாற்றுதல் (Silver Layer Processing)
    df = pd.DataFrame(data_records)
    
    # --- 🎯 AI FILTERS & LOGIC ---
    
    print("🟢 TOP 3 GAINERS (Momentum Engine):")
    top_gainers = df.sort_values(by="Change (%)", ascending=False).head(3)
    print(top_gainers.to_string(index=False), "\n")
    
    print("🔴 TOP 3 LOSERS (Reversal Radar):")
    top_losers = df.sort_values(by="Change (%)", ascending=True).head(3)
    print(top_losers.to_string(index=False), "\n")
    
    print("💎 HIDDEN GEMS (Price < ₹200 & Volume Breakout > 1.5x):")
    # Rule: விலை 200க்குக் கீழ் இருக்க வேண்டும், ட்ரேடிங் வால்யூம் வழக்கத்தை விட 1.5 மடங்கு அதிகம் இருக்க வேண்டும்
    hidden_gems = df[(df["LTP (₹)"] < 200) & (df["Volume Multiplier"] > 1.5)]
    if not hidden_gems.empty:
        print(hidden_gems.to_string(index=False), "\n")
    else:
        print("No hidden gems found today.\n")

    return df

# கோடை ரன் செய்ய
if __name__ == "__main__":
    final_data = fetch_nifty_data()
    print("✅ System Execution Completed Successfully!")
