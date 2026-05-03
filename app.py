import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
import plotly.express as px

# 1. Page Configuration
st.set_page_config(page_title="Project Phoenix AI", page_icon="🦅", layout="wide")
st.title("🦅 Project Phoenix - AI Swing Trading Radar")
st.markdown("Autonomous Market Screener & Probability Engine | **System Architect:** Manivannan")
st.markdown("---")

# 2. Database Connection (Google Sheets)
@st.cache_data(ttl=300) # 5 நிமிடங்களுக்கு ஒருமுறை மட்டும் டேட்டாவை ரெஃப்ரெஷ் செய்ய
def load_data():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        # Streamlit Cloud-ல் ரன் ஆகும்போது
        creds_json = json.loads(os.environ.get('GCP_CREDENTIALS'))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    except:
        # லோக்கலில் ரன் ஆகும்போது
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        
    client = gspread.authorize(creds)
    sheet = client.open('Phoenix_Market_Data').sheet1
    data = sheet.get_all_records()
    return pd.DataFrame(data)

# 3. The AI Probability Engine (Rule-based for now)
def apply_ai_logic(df):
    # 1. AI Confidence-ஐ அடிப்படையாகக் கொண்டு சிக்னல் உருவாக்குதல்
    def get_signal(row):
        # ஏஐ 80% மேல் உறுதி அளித்து, ட்ரெண்டும் அப்-ஆக (Uptrend) இருந்தால் அது தங்கம்!
        if row.get('AI_Confidence', 0) >= 80 and row.get('Is_Uptrend', 0) == 1:
            return "🚀 HIGH CONVICTION BUY"
        elif row.get('AI_Confidence', 0) >= 60:
            return "⏳ WATCHLIST"
        else:
            return "🚫 AVOID"
            
    df['AI_Signal'] = df.apply(get_signal, axis=1)
    
    # 2. ப்ரோபபிலிட்டி ஸ்கோரை அப்படியே AI_Confidence-ஆக மாற்றிக்கொள்ளலாம்
    df['AI_Probability_Score'] = df['AI_Confidence']
    
    return df
# --- UI Layout ---
try:
    with st.spinner("Fetching data from Bronze Layer..."):
        raw_df = load_data()
        
    if not raw_df.empty:
        df = apply_ai_logic(raw_df)
        
        # Top Level Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Stocks Scanned", len(df))
        col2.metric("Strong Buy Signals", len(df[df['AI_Signal'] == "🚀 STRONG BUY"]))
        col3.metric("Top Gainer Today", df.loc[df['Change_Pct'].idxmax(), 'Stock'], f"{df['Change_Pct'].max()}%")
        col4.metric("Top Volume Breakout", df.loc[df['Volume_Multiplier'].idxmax(), 'Stock'], f"{df['Volume_Multiplier'].max()}x")
        
        st.markdown("### 🎯 AI Actionable Signals")
        # Filter only Actionable Stocks (Score > 60)
        action_df = df[df['AI_Probability_Score'] >= 60].sort_values(by="AI_Probability_Score", ascending=False)
        
        # Display as a beautiful dataframe
        st.dataframe(
            action_df[['Stock', 'LTP', 'RSI_14', 'Pred_Next_Day_Pct', 'AI_Confidence', 'AI_Signal']],
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown("### 📊 Volume Anomalies (The Hidden Hands)")
        # Plotly Chart for Volume Breakouts
        vol_df = df.sort_values(by="Volume_Multiplier", ascending=False).head(15)
        fig = px.bar(vol_df, x='Stock', y='Volume_Multiplier', color='Change_Pct', 
                     title="Top 15 Stocks with Unusual Volume Activity",
                     color_continuous_scale="RdYlGn")
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("No data found in Google Sheets. Wait for the pipeline to run.")

except Exception as e:
    st.error(f"Error connecting to Database: {e}")