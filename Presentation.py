import streamlit as st
from utils.QIS.crypto import text

#from utils.option_pricing import show as show_option_pricing


st.set_page_config(
    page_title="Bruno Quant Hub",
    page_icon="📊",
    layout="wide"
)

st.markdown(text.about_me)
