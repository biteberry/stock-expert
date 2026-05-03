import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

# 1. Page Configuration
st.set_page_config(page_title="Project Phoenix AI", page_icon="🦅", layout="wide")
st.title("🦅 Project Phoenix - AI Swing Trading Radar")
st.markdown("Autonomous Market Screener & Risk-Management Engine | **System Architect:** Manivannan")
st.markdown("---")

# 2. Database Connection
@st.cache_data(ttl=60)
def load_data():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        creds_json = json.loads(os.environ.get('GCP_CREDENTIALS', '{}'))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    except:
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    
    client = gspread.authorize(creds)
    sheet = client.open('Phoenix_Market_Data').sheet1
    data = sheet.get_all_records()
    return pd.DataFrame(data)

# --- UI Layout ---
try:
    with st.spinner("Synchronizing with AI Brain..."):
        df = load_data()
        
    if not df.empty:
        available_cols = df.columns.tolist()

        # 3. Top Level Metrics (Restoring Gainer & Loser)
        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric("Total Stocks", len(df))
        
        # Conviction Logic
        if 'AI_Confidence' in available_cols:
            conviction_count = len(df[df['AI_Confidence'] >= 80])
            col2.metric("Conviction Signals", conviction_count)

        # Gainer & Loser Restoration Logic
        # ஷீட்டில் 'Change_Pct' என்ற பெயரில் காலம் இருப்பதை உறுதி செய்கிறோம்
        if 'Change_Pct' in available_cols:
            # பர்சடேஜ் மதிப்புகளை வரிசைப்படுத்தி டாப் மற்றும் பாட்டம் எடுக்கிறோம்
            top_gainer = df.loc[df['Change_Pct'].idxmax()]
            top_loser = df.loc[df['Change_Pct'].idxmin()]
            
            col3.metric("🟢 Top Gainer", f"{top_gainer['Stock']}", f"{top_gainer['Change_Pct']}%")
            col4.metric("🔴 Top Loser", f"{top_loser['Stock']}", f"{top_loser['Change_Pct']}%")
        else:
            st.warning("⚠️ 'Change_Pct' column not found in Google Sheets. Please check headers.")

        st.markdown("### 🎯 AI Actionable Intelligence")

        # 4. Actionable Table with all restoration[cite: 6, 7]
        preferred_order = [
            'Stock', 'LTP', 'Change_Pct', 'Pred_Next_Day_Pct', 'AI_Confidence', 
            'Support_SL', 'Target_1_2', 'Profit_Pct', 'Is_Hammer', 'Is_Breakout'
        ]
        final_cols = [c for c in preferred_order if c in available_cols]
        
        st.dataframe(
            df[final_cols].sort_values(by="AI_Confidence", ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "AI_Confidence": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=100, format="%.0f%%"),
                "Change_Pct": st.column_config.NumberColumn("Today %", format="%.2f%%"),
                "Pred_Next_Day_Pct": st.column_config.NumberColumn("Next Day Pred %", format="%.2f%%")
            }
        )

    else:
        st.warning("Waiting for data push from data_fetcher.py...")

except Exception as e:
    st.error(f"Platform Sync Error: {e}")