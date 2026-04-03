import pandas as pd
import numpy as np
import streamlit as st
import toolkit as ftk


@st.cache_data
def get_datasets():
    return ftk.get_famafrench_datasets()


@st.cache_data(ttl=3600)
def get_factors(dataset, mom):
    factors = ftk.get_famafrench_factors(dataset, mom)
    # Return raw factors (DatetimeIndex) to allow resample() to handle normalization
    if hasattr(factors.index, 'to_timestamp'):
        factors.index = factors.index.to_timestamp()
    factors.index = pd.to_datetime(factors.index)
    return factors


@st.cache_data(ttl=60)
def get_price(ticker):
    try:
        raw_price = ftk.get_yahoo(ticker)
        if raw_price is None or raw_price.empty:
            return pd.DataFrame()
        # Return portfolio returns as originally intended
        return ftk.price_to_return(raw_price)
    except Exception as e:
        st.error(f"Error fetching data for ticker {ticker}: {e}")
        return pd.DataFrame()


# Return (portfolio_returns, factors, rfr)
def resample(portfolio_returns, factors):
    # Ensure both are DatetimeIndex and deduplicated
    def sanitize(df):
        if hasattr(df.index, 'to_timestamp'):
            df.index = df.index.to_timestamp()
        df.index = pd.to_datetime(df.index)
        return df[~df.index.duplicated(keep='first')]

    portfolio_returns = sanitize(portfolio_returns)
    factors = sanitize(factors)

    # Normalize Kenneth French factors to Month-End (ME)
    factors.index = factors.index.to_period('M').to_timestamp('M')

    # Aggregatively resample daily returns to monthly returns using compounding
    # Periodicity > 12 means higher frequency than monthly
    try:
        if ftk.periodicity(portfolio_returns) > 12:
            portfolio_returns = portfolio_returns.resample('ME').aggregate(ftk.compound_return)
        else:
            portfolio_returns.index = portfolio_returns.index.to_period('M').to_timestamp('M')
    except:
        portfolio_returns.index = portfolio_returns.index.to_period('M').to_timestamp('M')

    # Merge on Month-End (ME) to ensure alignment
    merged = pd.merge(portfolio_returns, factors, left_index=True, right_index=True).dropna()

    # Convert to PeriodIndex('M') - this is the MOST ROBUST for Fama-French analytics.
    # It removes the need for manual frequency assignment and handles gaps gracefully.
    merged.index = merged.index.to_period('M')
    
    return merged.iloc[:, 0], merged.iloc[:, 1:-1], merged.iloc[:, -1]

@st.cache_data(ttl=60)
def get_bestfit(portfolio):

    def analyse(portfolio, model):        
        portfolio, factors, rfr = resample(portfolio, get_factors(model, mom))
        if portfolio.empty or factors.empty:
            return 0.0
        return ftk.rsquared(portfolio - rfr, factors, adjusted=True)

    models = get_datasets()
    return pd.Series([analyse(portfolio, model) for model in models], index=models).sort_values(ascending=False)

if 'price' not in st.session_state:
    st.session_state.price = None

with st.sidebar:


    dataset = st.selectbox(
        'Select a factor',
        options=get_datasets(),
        format_func=lambda x: x.replace('_', ' '),
        index=23)

    mom = st.toggle('Add momentum factor')

st.title('Fama–French Factor Model')

with st.form("my_form"):
    ticker = st.text_input('Search for a ticker (e.g. SPY, QQQ, TSLA)', 'ARKK')
    submitted = st.form_submit_button("Search")
    if submitted:
        try:
            price = get_price(ticker)
            if price is None or price.empty:
                st.error(f"No data found for ticker '{ticker}'. This ticker might not exist or lacks historical data.")
                st.session_state.price = None
            else:
                st.session_state.price = price
        except Exception as e:
            st.error(f"Error fetching data for '{ticker}': {e}")
            st.session_state.price = None

portfolio = st.session_state.price

if portfolio is not None:
    st.header(portfolio.name)

    if st.button('Check model of best fit'):
        best = get_bestfit(portfolio)
        st.info(f'The model of best fit is {best.index[0]} with adjusted R-squared of {best.iloc[0]:.2%}')

    factors = get_factors(dataset, mom)

    portfolio, factors, rfr = resample(portfolio, factors)
    
    if portfolio.empty or factors.empty:
        st.error("No overlapping historical data found between the portfolio and the selected factor dataset. Please try a different factor model or ticker.")
        st.stop()
        
    # Sanitizing Data: Replace inf with NaN and then drop all NaNs to prevent RuntimeWarnings in statsmodels
    def sanitize_math(ds):
        import numpy as np # Local import for robustness
        return ds.replace([np.inf, -np.inf], np.nan).dropna()

    excess_returns = sanitize_math(portfolio - rfr)
    factors = sanitize_math(factors).reindex(excess_returns.index).dropna()
    # Keep only the rows where BOTH excess_returns and factors have valid data
    excess_returns = excess_returns.reindex(factors.index).dropna()
    factors = factors.reindex(excess_returns.index).dropna()

    # Align portfolio and rfr to the same index as excess_returns/factors
    # Without this, pd.concat fills missing rows with NaN → only one line shows on chart
    portfolio_aligned = portfolio.reindex(excess_returns.index)
    rfr_aligned = rfr.reindex(excess_returns.index)

    betas = ftk.beta(excess_returns, factors)

    attribution = pd.concat([betas * factors, rfr_aligned], axis=1)
    explained = attribution.sum(axis=1)
    combined = pd.concat([portfolio_aligned, explained], axis=1).dropna()
    combined.columns = ['Portfolio', 'Factors']
    # Safely handle the attribution and contribution calculation
    # k is the Carino attribution factor to convert arithmetic returns to geometric components
    try:
        total_return = ftk.compound_return(portfolio_aligned)
        cf = ftk.carino(portfolio_aligned, 0)
        tf = ftk.carino(total_return, 0)
        # Avoid division by zero in Carino transformation
        k = (attribution.T * cf).T / tf if tf != 0 else attribution
        contribution = k.sum()
    except:
        total_return = ftk.compound_return(portfolio_aligned)
        contribution = attribution.sum()

    # Create the result summary table
    summary_df = pd.DataFrame({
        'Beta': [np.nan, np.nan],
        'Contribution': [total_return - contribution.sum(), total_return]
    }, index=['Unexplained', 'Total'])

    # Combine statistical betas with contribution percentages
    table = pd.concat([betas.to_frame('Beta'), contribution.to_frame('Contribution')], axis=1)
    
    # Fix FutureWarning by ensuring consistent column structure for concatenation
    table = pd.concat([table, summary_df])
    table['Contribution'] = table['Contribution'] * 100

    table = table.rename(index={'Mkt-RF': 'Market returns above risk-free rate (Mkt-RF)',
                                'HML': 'High minus low (HML)',
                                'RF': 'Risk-Free Rate (RF)',
                                'CMA': 'Conservative minus aggressive (CMA)',
                                'WML': 'Winners minus losers (WML)',
                                'SMB': 'Small minus big (SMB)',
                                'RMW': 'Robust minus weak (RMW)'})
    table = table.sort_values('Beta', ascending=False)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric('Portfolio Ann. Return',
                f'{ftk.compound_return(portfolio_aligned, annualize=True):.2%}')
    col2.metric('Factor Ann. Return',
                f'{ftk.compound_return(explained, annualize=True):.2%}')
    col3.metric('R-Squared', f'{ftk.rsquared(excess_returns, factors):.2%}')
    col4.metric('Adj. R-Squared',
                f'{ftk.rsquared(excess_returns, factors, adjusted=True):.2%}')

    st.dataframe(table,
                 column_config={
                     "Beta": st.column_config.NumberColumn(
                         "Beta",
                         format='%.2f'
                     ),
                     "Contribution": st.column_config.NumberColumn(
                         "Contribution (%)",
                         format='%.1f'
                     ),
                 },)
    # return_to_price needs PeriodIndex with freq intact — do NOT convert before calling it.
    # It internally calls .to_timestamp() and uses .freq. Convert only the output.
    chart_data = ftk.return_to_price(combined)
    chart_data = chart_data.replace([np.inf, -np.inf], np.nan).dropna()
    st.line_chart(chart_data)
else:
    st.write(
        'Please search a ticker in the box above (e.g. `SPY`, `QQQ`, `ARKK`, `BRK-B`) to get started.')

st.markdown(open('data/signature.md').read())
