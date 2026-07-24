import streamlit as st
import utils.pricing.option_pricing as op
import utils.pricing.binomial_convergence as bc
import numpy as np

tab_bs_bin,tab_conv=st.tabs(["Black Scholes Pricing","Binomial pricing & convergence to BS"])

with tab_bs_bin:
    st.markdown("## Black Scholes Option Pricer")
    col1, col2=st.columns([2,5])

    with col1:
        st.markdown("### Parameters")
        option_type=st.radio("option type",["call","put"])
        S0=st.slider("Stock Price (S0)",1,500,250)
        K=st.slider("Strike (K)",1,500,250)
        T=st.slider("Time to maturity(years)",0.01,2.0,0.5)
        r=st.slider("Risk free rate (%)",-5.0,7.0,3.0)
        sigma=st.slider("volatility (%)",10,100,20)

        
    r=r/100
    sigma=sigma/100
    bs_price=op.black_scholes_option_price(S0,K,T,r,sigma,option_type)

    df_greeks=op.bs_greeks_df(S0,K,T,r,sigma,option_type)
    df_greeks_S0=op.greeks_S0(K,T,r,sigma,option_type)
    graph_option=op.plotly_option_vs_stock(K,T,r,sigma,option_type)
    dico_graphs_greeks=op.plotly_greeks_S0(df_greeks_S0,K)
    

    with col2:
        st.markdown(" ### Option Price")
        st.metric(label="Price",value=np.round(bs_price,2))
        st.plotly_chart(graph_option)


    st.markdown("## Greeks")
    #st.dataframe(df_greeks)
    col1,col2,co3=st.columns([1,6,1])
    with col2:
        st.dataframe(df_greeks)
        for graph in dico_graphs_greeks.values():
            st.plotly_chart(graph,width=800,)

with tab_conv:
    st.markdown("## Binomial Option Pricer & Convergence to BS")
    col1, col2=st.columns([2,5])

    with col1:
        st.markdown("### Parameters")
        option_type=st.radio("Option Type",["call","put"],key="bin_conv")
        S0=st.slider("Stock Price (S0)",1,500,250,key="bin_conv_S0")
        K=st.slider("Strike (K)",1,500,250,key="bin_conv_K")
        T=st.slider("Time to maturity(years)",0.01,2.0,0.5,key="bin_conv_T")
        r=st.slider("Risk free rate (%)",-5.0,5.0,7.0,key="bin_conv_r")
        sigma=st.slider("volatility (%)",10,100,20,key="bin_conv_sigma")
        N=st.slider("Number of steps for binomial pricing",2,500,100,key="bin_conv_N")

    r=r/100
    sigma=sigma/100

    bs_price_convergence=bc.black_scholes_option_price(S0,K,T,r,sigma,option_type)
    with col2:

        st.markdown("### Option Price & Convergence")
        european_price=bc.binomial_option_price(S0,K,T,r,sigma,N,option_type,"european")
        american_price=bc.binomial_option_price(S0,K,T,r,sigma,N,option_type,"american")

        sous_col1, sous_col2=st.columns([1,1])
        with sous_col1:
            st.metric("European Price",np.round(european_price,2))
        with sous_col2:
            st.metric("American Price",np.round(american_price,2))

        df=bc.binomial_convergence(S0,K,T,r,sigma,option_type,"european",n_max=N)
        plot_convergence=bc.plotly_binomial_convergence(df)
        st.plotly_chart(plot_convergence,height=600)

    st.markdown(
        "Convergence is displayed only for European options since the Black-Scholes model only prices European options."
    )
    st.dataframe(bc.binomial_convergence(S0,K,T,r,sigma,option_type,"european",n_max=N).set_index("N"))

