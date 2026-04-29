# Autonomous AI Agent - Stock Market Data Pipeline

This repository contains the robust Medallion Architecture data ingestion pipeline for an Autonomous AI Agent designed to automate stock market technical analysis and swing trading for the Indian Stock Market (NSE).

## System Architecture: Medallion Data Pipeline

The pipeline implements a strict 3-layer data preparation structure for the Data Lake:

1. **Bronze Layer (Raw Data)**: `data/bronze/`
   - Ingests raw OHLCV data directly from Yahoo Finance without any modification.
   - Preserves an immutable source of truth.
   - Includes historical macroeconomic data, such as Daily FII/DII trading activity.
   
2. **Silver Layer (Cleaned Data)**: `data/silver/`
   - Handles missing values (forward and backward fills).
   - Standardizes the Datetime indexes to localized standard timezones.
   - Enforces correct numeric data types for robust downstream consumption.

3. **Gold Layer (Feature Engineered & AI-Ready)**: `data/gold/`
   - Integrates advanced feature engineering.
   - Computes technical indicators: 50-day Simple Moving Average (SMA), 14-day Relative Strength Index (RSI), and Volume Trends.
   - Merges and forward-fills FII/DII Macro Sentiment data to enrich the trading context for the local AI Agent.

## Setup & Installation

### Requirements
You need Python installed. Set up your virtual environment and install the required dependencies:

```bash
python -m venv .venv
# On Windows
.\.venv\Scripts\activate
# Install dependencies
pip install -r requirements.txt
```

*(Note: Dependencies use loose versioning to allow modern pip to fetch pre-built wheels and avoid Windows Long Path build errors.)*

## Usage

### 1. Update Macro Data (FII/DII)
Because historical FII/DII data is not readily available through standard NSE APIs, the pipeline requires an initial CSV backfill or incremental daily updates.
Run the FII/DII pipeline to fetch the *current day's* FII/DII activity and append it to `data/bronze/macro_fii_dii_activity.csv`.

```bash
python fii_dii_pipeline.py
```

### 2. Run the Main Data Pipeline
Once the macro data is updated, run the Medallion pipeline. This will process the `TATASTEEL.NS`, `SUNPHARMA.NS`, and `THANGAMAYL.NS` test nodes through the Bronze, Silver, and Gold layers.

```bash
python medallion_pipeline.py
```

The AI-ready feature datasets will be outputted to `data/gold/`.