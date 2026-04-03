import streamlit as st

st.set_page_config(
    page_title="Financial Toolkit Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Define the navigation structure
pages = {
    "Market Analysis": [
        st.Page("indices.py", title="World Indices Monitor", icon="🌍"),
        st.Page("factors.py", title="Fama–French Factor Analysis", icon="📊"),
    ],
    "Portfolio & Risk": [
        st.Page("portfolio.py", title="Portfolio Optimization", icon="🏹"),
        st.Page("peers.py", title="Peer Group Analysis", icon="👥"),
    ],
    "Derivatives": [
        st.Page("options.py", title="Option Strategies", icon="📜"),
    ],
}

# Create the navigation
pg = st.navigation(pages)

# Run the app
pg.run()
