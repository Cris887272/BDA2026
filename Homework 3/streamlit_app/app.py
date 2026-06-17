#
# HOMEWORK #3 - PART 3 : STREAMLIT DASHBOARD
# Page 1 - Time Analysis
#
# The app is self-contained: it rebuilds the star schema from the three CSV files
# (same ETL logic as the notebook) and renders four interactive charts that all
# react to a date-range filter.
#
# Run from a terminal with:   streamlit run app.py
# 
 
from datetime import date
import pandas as pd
import altair as alt
import streamlit as st
 
# Folder containing the three CSV files (same folder as this script by default).
DATA_DIR = "."
 
# 
# DATA LOADING : rebuild the star schema and return one denormalized dataframe.
# @st.cache_data runs this only once and caches the result, so moving the date
# slider does NOT re-run the whole ETL every time (the app stays fast).
# 
@st.cache_data
def load_data(data_dir: str) -> pd.DataFrame:
    # Load the three raw CSV files (same parameters as Part 2.1) 
    tx = pd.read_csv(f"{data_dir}/account-statement-1-1-2024-12-31-2024.csv",
                     sep=";", encoding="utf-8-sig", dtype={"IDTransaction": str})
    symbols = pd.read_csv(f"{data_dir}/symbols.csv", sep=";", encoding="utf-8-sig")
    country = pd.read_csv(f"{data_dir}/country.csv", sep=",", encoding="utf-8-sig",
                          keep_default_na=False, na_values=[""])
 
    # Clean the transactions 
    if "Unnamed: 5" in tx.columns:
        tx = tx.drop(columns=["Unnamed: 5"])
    tx = tx.dropna(how="all").reset_index(drop=True)
    tx["TransactionType"] = tx["TransactionType"].str.strip().replace({"DIVIDENT": "DIVIDEND"})
    tx["Date"] = pd.to_datetime(tx["Date"], format="%d/%m/%Y %H:%M:%S")
    tx["date"] = tx["Date"].dt.normalize()          # day-level timestamp (time set to 00:00)
    tx["Unit"] = tx["Unit"].astype(int)
 
    # Build the geography reference (only modeled columns)
    geo = country[["name", "alpha-2", "sub-region", "region"]].copy()
    geo = geo.rename(columns={"name": "country", "alpha-2": "alpha_2", "sub-region": "sub_region"})
    geo.loc[geo["country"] == "Taiwan, Province of China", ["sub_region", "region"]] = ["Eastern Asia", "Asia"]
 
    # Enrich transactions with symbol info and geography (left joins)
    name_fix = {"Turkey": "Türkiye", "Taiwan": "Taiwan, Province of China"}
    sym = symbols.copy()
    sym["country"] = sym["country"].replace(name_fix)
    df = tx.merge(sym[["symbol", "company_name", "sector", "industry", "country"]],
                  left_on="Symbol", right_on="symbol", how="left")
    df = df.merge(geo, on="country", how="left")
 
    # Fill missing enrichment with "Unknown" (keep all transactions)
    for col in ["company_name", "sector", "industry", "country", "alpha_2", "sub_region", "region"]:
        df[col] = df[col].fillna("Unknown")
 
    # Keep only the columns the dashboard needs 
    df = df.rename(columns={"Symbol": "symbol_ticker", "Unit": "units",
                            "TransactionType": "transaction_type"})
    return df[["date", "symbol_ticker", "sector", "industry",
               "transaction_type", "units"]]
 
 
# 
# PAGE CONFIG & TITLE
# 
st.set_page_config(page_title="Financial Transactions Dashboard", layout="wide")
st.title("Financial Transactions Dashboard")
st.header("Page 1 — Time Analysis")
 
# Load the data once (cached).
data = load_data(DATA_DIR)
 
# 
# FILTER : date range (default 01/01/2024 - 31/12/2024). All charts react to it.
# 
st.sidebar.header("Filters")
date_range = st.sidebar.date_input(
    "Date range",
    value=(date(2024, 1, 1), date(2024, 12, 31)),   # default values required by the assignment
    min_value=date(2024, 1, 1),
    max_value=date(2024, 12, 31),
)
 
# date_input returns a single date while the user is still picking the second one;
# guard against that so the app does not crash mid-selection.
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = date(2024, 1, 1), date(2024, 12, 31)
 
# Apply the filter: keep only BUY/SELL transactions inside the selected range.
# (DIVIDEND is excluded: the charts measure trading activity, as in Part 2.2.)
mask = ((data["date"] >= pd.Timestamp(start_date))
        & (data["date"] <= pd.Timestamp(end_date))
        & (data["transaction_type"].isin(["BUY", "SELL"])))
fdata = data[mask]
 
# If no transactions match the selection, show a message and stop.
if fdata.empty:
    st.warning("No transactions found for the selected date range.")
    st.stop()
 
# 
# CHART 1 : line chart - total transactions (BUY + SELL) over time (per day).
# 
st.subheader("Total transactions over time (BUY + SELL)")
daily = (fdata.groupby("date").size()
              .rename("transactions").reset_index())
line = (alt.Chart(daily)
          .mark_line()
          .encode(x=alt.X("date:T", title="Date"),
                  y=alt.Y("transactions:Q", title="Number of transactions")))
st.altair_chart(line, use_container_width=True)
 
# Small helper that builds a sorted "top N" bar chart for a given column.
def top_bar(frame: pd.DataFrame, column: str, n: int, label: str, exclude_unknown: bool):
    d = frame
    if exclude_unknown:                              # drop "Unknown" for enrichment attributes
        d = d[d[column] != "Unknown"]
    d = (d.groupby(column).size()
           .sort_values(ascending=False).head(n)
           .rename("transactions").reset_index())
    return (alt.Chart(d)
              .mark_bar()
              .encode(x=alt.X(f"{column}:N", sort="-y", title=label),
                      y=alt.Y("transactions:Q", title="Number of transactions")))
 
# 
# CHART 2 : top 3 traded symbols by transaction count.
# (symbol is never "Unknown", so nothing is excluded here.)
# 
st.subheader("Top 3 traded symbols")
st.altair_chart(top_bar(fdata, "symbol_ticker", 3, "Symbol", exclude_unknown=False),
                use_container_width=True)
 
# 
# CHART 3 : top 5 sectors by transaction count.
# 
st.subheader("Top 5 sectors")
st.altair_chart(top_bar(fdata, "sector", 5, "Sector", exclude_unknown=True),
                use_container_width=True)
 
# 
# CHART 4 : top 5 industries by transaction count.
# 
st.subheader("Top 5 industries")
st.altair_chart(top_bar(fdata, "industry", 5, "Industry", exclude_unknown=True),
                use_container_width=True)