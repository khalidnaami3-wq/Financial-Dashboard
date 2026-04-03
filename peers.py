import calendar
import pandas as pd
import streamlit as st
import toolkit as ftk

@st.cache_data(ttl=3600)
def get_price(tickers):
    try:
        df = ftk.get_yahoo_bulk(tickers, period='20Y')
        if df is None or df.empty:
            # Handle empty data scenario
            st.error("Financial data could not be retrieved. Please verify the tickers in the URL.")
            st.stop()
        
        # Ensure the index is a DatetimeIndex to support resampling later
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        
        # Clean up any invalid dates
        df = df[df.index.notnull()]
        
        return df
    except Exception as e:
        # Catch connection failures or other API errors
        st.error(f"Failed to fetch market data from Yahoo Finance: {e}")
        st.stop()

def get_rolling(df, annualize):    
    n = len(df) // 12
    df2 = df.T.copy()
    for i in range(1, n + 1):
        df2[f'{i}Y'] = df.T.iloc[:, -i * 12:].apply(lambda x: ftk.compound_return(x, annualize), axis=1)
    return (df2.iloc[:, -n:]).style.format('{0:.2%}').highlight_max(color='lightgreen')

def get_table(df, period):
    return (df.resample(period).aggregate(ftk.compound_return).T).style.format('{0:,.2%}').highlight_max(color='lightgreen')

def format_table(s):
    tbl = s.groupby([(s.index.year), (s.index.month)]).sum()
    tbl = tbl.unstack(level=1).sort_index(ascending=False)
    tbl.columns = [calendar.month_abbr[m] for m in range(1, 13)]
    tbl['YTD'] = tbl.agg(ftk.compound_return, axis=1)
    return tbl.style.format('{0:.2%}')    

# Pre-process the data
st.title('Peer Group Analysis')

# Default funds and benchmark for cases where query params are missing
DEFAULT_FUNDS = ['PRCOX', 'GQEFX', 'STSEX', 'NUESX', 'VTCLX', 'CAPEX', 'USBOX', 'VPMCX', 'JDEAX', 'DFUSX', 'GALLX']
DEFAULT_BENCHMARK = '^SP500TR'

# Get initial values from query parameters if available
query_funds = st.query_params.get_all('fund')
query_benchmark = st.query_params.get('benchmark', DEFAULT_BENCHMARK)

if not query_funds:
    query_funds = DEFAULT_FUNDS

with st.sidebar:
    st.header("Search Parameters")
    with st.expander("Ticker Selection", expanded=True):
        fund_list = st.text_area(
            'Funds tickers (one per line)', 
            value="\n".join(query_funds),
            height=200
        )
        benchmark_ticker = st.text_input(
            'Benchmark ticker', 
            value=query_benchmark
        )
    
    funds = [f.strip() for f in fund_list.split("\n") if f.strip()]
    benchmark = benchmark_ticker.strip()
    tickers = funds + [benchmark]

price = get_price(tickers)

try:
    # Resample to monthly periods for analysis
    periods = price.resample('M').last().to_period()
    
    with st.sidebar:
        # Default fallback if the data is too short for the 60-month default
        start_idx = -60 if len(periods.index) > 60 else 0
        horizon = st.select_slider(
            'Sample period',
            options=periods.index,
            value=[periods.index[start_idx], periods.index[-1]]
        )
except Exception as e:
    st.error(f"Error processing time-series data: {e}. One or more tickers may have insufficient historical records.")
    st.stop()
    rfr_annualized = st.slider(
        'Risk-free rate (%)', value=2., min_value=0.0, max_value=10., step=0.1
    )

# Process the data
rtn = ftk.price_to_return(price.resample('M').last())[horizon[0] : horizon[1]]
rtn['RF'] = (1 + rfr_annualized / 100) ** (1 / 12) - 1 # M
rtn = rtn.dropna(axis=1)

funds = rtn.iloc[:, :-2]
benchmark = rtn.iloc[:, -2]
rfr = rtn.iloc[:, -1]
fund_n_bm = rtn.iloc[:, :-1]

dropped = [x for x in tickers if x not in list(rtn.columns)]

summary = pd.DataFrame(ftk.summary(funds, benchmark, rfr)).iloc[:, 2:]

# Charts and Tables
if len(dropped) > 0:
    st.warning(f'WARNING: **{len(dropped)}** fund(s) were dropped due to short track record - **{", ".join(dropped)}**')

st.line_chart(ftk.return_to_price(fund_n_bm))

col1, col2 = st.columns(2)
col1.scatter_chart(summary.reset_index(), x='Annualized Volatility', y='Annualized Return', color='index')
col2.scatter_chart(summary.reset_index(), x='Annualized Tracking Error', y='Annualized Active Return', color='index')

st.header('Performance')
category_tabs = st.tabs(['Rolling Period', 'By Year', 'By Quarter', 'By Month', 'By Fund'])

with category_tabs[0]:
    annualize = st.toggle('Annualize', value=True)
    st.dataframe(get_rolling(fund_n_bm, annualize), use_container_width=False)

with category_tabs[1]:
    st.dataframe(get_table(fund_n_bm, 'Y'))

with category_tabs[2]:
    st.dataframe(get_table(fund_n_bm, 'Q'))

with category_tabs[3]:
    st.dataframe(get_table(fund_n_bm, 'M'))

with category_tabs[4]:
    tabs = st.tabs(list(fund_n_bm.columns))
    for i, tab in enumerate(tabs):
        tab.write(format_table(fund_n_bm.iloc[:, i]))

st.header('Risk')
st.write(summary.style.highlight_max(color='lightgreen'))

st.markdown(open('data/signature.md').read())
