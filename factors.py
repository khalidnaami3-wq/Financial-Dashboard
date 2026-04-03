import pandas as pd
import streamlit as st
import toolkit as ftk


@st.cache_data
def get_datasets():
    return ftk.get_famafrench_datasets()


@st.cache_data(ttl=3600)
def get_factors(dataset, mom):
    return ftk.get_famafrench_factors(dataset, mom)


@st.cache_data(ttl=60)
def get_price(ticker):
    try:
        raw_price = ftk.get_yahoo(ticker)
        if raw_price is None or raw_price.empty:
            return pd.DataFrame()
        return ftk.price_to_return(raw_price).asfreq("B")
    except Exception as e:
        # Catch unexpected errors during data retrieval or calculation
        st.error(f"Error fetching data for ticker {ticker}: {e}")
        return pd.DataFrame()


# Return (portfolio, factors, rfr)
def resample(portfolio, factors):
    # Ensure both have DatetimeIndex
    if not isinstance(portfolio.index, pd.DatetimeIndex):
        portfolio.index = pd.to_datetime(portfolio.index)
    if not isinstance(factors.index, pd.DatetimeIndex):
        factors.index = pd.to_datetime(factors.index)

    # Handle missing frequencies to prevent ftk.periodicity from crashing
    if portfolio.index.freqstr is None:
        portfolio.index.freq = pd.infer_freq(portfolio.index)
    if factors.index.freqstr is None:
        factors.index.freq = pd.infer_freq(factors.index)

    # Use default frequency if inference fails
    p_freq = portfolio.index.freqstr if portfolio.index.freqstr else 'B'
    f_freq = factors.index.freqstr if factors.index.freqstr else 'B'

    try:
        # Standardize frequencies if mismatch occurs
        p_period = ftk.periodicity(portfolio) if portfolio.index.freqstr else 252
        f_period = ftk.periodicity(factors) if factors.index.freqstr else 252
        
        if p_period > f_period:
            portfolio = portfolio.resample(f_freq).aggregate(ftk.compound_return)
    except:
        # If periodicity fails, proceed with raw merged data
        pass

    merged = pd.merge(portfolio, factors, left_index=True, right_index=True)
    return merged.iloc[:, 0], merged.iloc[:, 1:-1], merged.iloc[:, -1]

@st.cache_data(ttl=60)
def get_bestfit(portfolio):

    def analyse(portfolio, model):        
        portfolio, factors, rfr = resample(portfolio, get_factors(model, mom))
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
    betas = ftk.beta(portfolio - rfr, factors)

    attribution = pd.concat([betas * factors, rfr], axis=1)
    explained = attribution.sum(axis=1)
    combined = pd.concat([portfolio, explained], axis=1)
    combined.columns = ['Portfolio', 'Factors']

    total_return = ftk.compound_return(portfolio)
    k = (attribution.T * ftk.carino(portfolio, 0)).T / \
        ftk.carino(total_return, 0)
    contribution = k.sum().sort_values(ascending=False)

    summary = pd.DataFrame({'Beta': {'Unexplained': None, 'Total': None},
                            'Contribution': {'Unexplained': total_return - contribution.sum(), 'Total': total_return}})

    table = pd.concat([betas, contribution], axis=1)
    table.columns = ['Beta', 'Contribution']
    table = pd.concat([table, summary])
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
                f'{ftk.compound_return(portfolio, annualize=True):.2%}')
    col2.metric('Factor Ann. Return',
                f'{ftk.compound_return(explained, annualize=True):.2%}')
    col3.metric('R-Squared', f'{ftk.rsquared(portfolio - rfr, factors):.2%}')
    col4.metric('Adj. R-Squared',
                f'{ftk.rsquared(portfolio - rfr, factors, adjusted=True):.2%}')

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
    st.line_chart(ftk.return_to_price(combined))
else:
    st.write(
        'Please search a ticker in the box above (e.g. `SPY`, `QQQ`, `ARKK`, `BRK-B`) to get started.')

st.markdown(open('data/signature.md').read())
