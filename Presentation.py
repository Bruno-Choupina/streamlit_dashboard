import streamlit as st

#from utils.option_pricing import show as show_option_pricing


st.set_page_config(
    page_title="Bruno Quant Hub",
    page_icon="📊",
    layout="wide"
)

st.title("Bruno Quant App")
st.header("Quantitative Finance Projects")

st.subheader("About Me")

st.write("""
I am currently pursuing the MSc 272 *Economics and Finance* at
Université Paris Dauphine–PSL and completing the first internship of my
gap year at TotalEnergies as a **Short-Term Power Middle Office
Analyst**.

This platform showcases my quantitative finance projects, combining
personal research with interactive educational tools inspired by the
concepts studied throughout my master's program.

Its objective is both to present the results of my quantitative
research and to provide hands-on applications of financial concepts
through interactive visualizations, simulations and quantitative
models.

""")
