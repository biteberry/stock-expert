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
st.markdown("Autonomous Market Screener & Risk-Management Engine | **System Architect:** Manivannan")
st.markdown("---")

# 2. Database Connection (Google Sheets)
@st.cache_data(ttl=300)
def load_data():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        creds_json = json.loads(os.environ.get('GCP_CREDENTIALS'))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    except:
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        
    client = gspread.authorize(creds)
    sheet = client.open('Phoenix_Market_Data').sheet1
    data = sheet.get_all_records()
    return pd.DataFrame(data)

# 3. Enhanced AI Decision Logic (V6.1)
def apply_ai_logic(df):
    def get_signal(row):
        # AI Confidence + Technical Confirmation
        score = row.get('AI_Confidence', 0)
        is_breakout = row.get('Is_Breakout', 0)
        is_hammer = row.get('Is_Hammer', 0)
        
        if score >= 85 or (score >= 75 and (is_breakout == 1 or is_hammer == 1)):
            return "🚀 HIGH CONVICTION BUY"
        elif score >= 60:
            return "⏳ WATCHLIST"
        else:
            return "🚫 AVOID"
            
    df['AI_Signal'] = df.apply(get_signal, axis=1)
    return df

# --- UI Layout ---
try:
    with st.spinner("Synchronizing with AI Brain..."):
        raw_df = load_data()
        
    if not raw_df.empty:
        df = apply_ai_logic(raw_df)
        
        # Top Level Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Scanned", len(df))
        col2.metric("Conviction Signals", len(df[df['AI_Signal'].str.contains("HIGH CONVICTION")]))
        
        # Gainer logic check
        if 'Change_Pct' in df.columns:
            top_gainer = df.loc[df['Change_Pct'].idxmax()]
            col3.metric("Top Gainer", top_gainer['Stock'], f"{top_gainer['Change_Pct']}%")
        
        col4.metric("Avg AI Confidence", f"{round(df['AI_Confidence'].mean(), 1)}%")

        st.markdown("### 🎯 AI Actionable Intelligence (1:2 Risk-Reward)")
        
        # Filter and Sort by Confidence
        action_df = df[df['AI_Confidence'] >= 50].sort_values(by="AI_Confidence", ascending=False)
        
        # Displaying the Advanced Table
        st.dataframe(
            action_df[[
                'Stock', 'LTP', 'Open', 'High', 'Low', 'Is_Hammer', 
                'Support_SL', 'Target_1_2', 'Profit_Pct', 
                'Is_Breakout', 'AI_Confidence', 'AI_Signal'
            ]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Support_SL": st.column_config.NumberColumn("Stop Loss", format="₹%.2f"),
                "Target_1_2": st.column_config.NumberColumn("Target (1:2)", format="₹%.2f"),
                "Profit_Pct": st.column_config.NumberColumn("Target Profit", format="%.2f%%"),
                "AI_Confidence": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=100, format="%f%%")
            }
        )
        
        # Visualizing Risk-Reward Distribution
        st.markdown("### 📊 Potential Profit Analysis")
        fig = px.scatter(action_df.head(20), x="AI_Confidence", y="Profit_Pct", 
                         size="LTP", color="AI_Signal", hover_name="Stock",
                         title="Top 20 Confidence vs Potential Profit (%)")
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("Data Synchronization Pending...")

except Exception as e:
    st.error(f"Platform Error: {e}")