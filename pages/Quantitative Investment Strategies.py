import streamlit as st
import pandas as pd
import vectorbt as vbt
import optuna

from pathlib import Path
from utils.QIS.crypto import data as dt
from utils.QIS.crypto import indicators as ind
from utils.QIS.crypto import signals as sin
from utils.QIS.crypto import backtesting as bt
from utils.QIS.crypto import params
from utils.QIS.crypto import analysis
from utils.QIS.crypto import optimization as opt
from utils.QIS.crypto import text

#st.markdown("# Choose The Project")
#projet=st.segmented_control(label="Choose The Project",options=["Crypto Investment","VEC statistical arbitrage"],default=None)

tab1,tab2=st.tabs(["Systematic Crypto Investing",""])

with tab1:


    st.markdown("# Systematic Crypto Strategy")
    st.markdown("## Project Overview")
    with st.expander(label="About the Project",expanded=False):
        st.markdown(text.project_overview)

    ROOT_DIR = Path(__file__).resolve().parent.parent
    CRYPTO_DIR = ROOT_DIR / "utils" / "QIS" / "crypto"
    OPTIMIZATIONS_DIR = CRYPTO_DIR / "optimizations"

    file_top_200_passe = CRYPTO_DIR / "top_200_passe.xlsx"
    file_top200_filtre = CRYPTO_DIR / "top_200_filtre.xlsx"
    file_top500_filtre = CRYPTO_DIR / "top_500_filtre.xlsx"

    @st.cache_data
    def load_universe(path):
        return pd.read_excel(path, index_col=0)

    df_top_200_passe = load_universe(file_top_200_passe)
    df_top_200_filtre = load_universe(file_top200_filtre)
    df_top_500_filtre = load_universe(file_top500_filtre)


    st.divider()
    st.markdown("## Strategy Parameters")

    # ============================================================
    # BUY STRATEGY
    # ============================================================
    with st.form("backtesting_params",border=False):

        #st.markdown("### Buy Strategy")
        #st.markdown("**A buy or sell signal is generated only when all three corresponding indicators simultaneously satisfy their respective conditions.**")

        with st.expander("Understanding the Buy Indicators",expanded=False):
            st.markdown(text.all_buy_indicators)

        with st.expander("Understanding the Sell Indicators"):
            st.markdown(text.all_sell_indicators)

        with st.expander("Configure Strategy Parameters",expanded=False):

            col1, col2,col3 =st.columns([5,1,5])

            with col1:
                st.markdown("#### Buy Indicators")
                st.markdown("##### Price Volatility")
                fenetre_glissante_volat_achat = st.slider("Rolling Window (days)", 30, 120, 60, key="buy_vol_window")
                fenetre_quantile_volat_achat = st.slider("Historical Window (days)", 500, 1300, 750, key="buy_vol_historical_window")
                quantile_bas_volat_achat = st.slider("Lower Volatility Quantile", 0.05, 0.25, 0.10, 0.01, key="buy_lower_vol_quantile")

                st.text("")
                st.markdown("##### Relative Trading Range")
                nb_jours_arriere_ecart_relatif = st.slider("Rolling Window (days)", 60, 300, 120, key="buy_range_window")
                nb_jour_mm_ecart_relatif = st.slider("Moving Average Window (days)", 20, 75, 40, key="buy_range_ma_window")
                nb_jour_quantiles_ecart_relatif = st.slider("Historical Window (days)", 500, 1300, 750, key="buy_range_historical_window")
                quantile_bas_ecart_relatif = st.slider("Lower Trading Range Quantile", 0.05, 0.25, 0.10, 0.01, key="buy_lower_range_quantile")

                st.text("")
                st.markdown("##### RSI Confirmation")
                critere_rsi_achat = st.slider("RSI Buy Threshold", 35, 60, 40)

            with col3:
                
                st.markdown("#### Sell Indicators")
                st.markdown("##### ROI")

                periode_roi_en_jours = st.slider("Rolling Window (days)", 30, 365, 180, key="sell_roi_window")
                nb_annees_quantile_roi = st.slider("Historical Window (years)", 1.5, 4.0, 2.0, 0.1, key="sell_roi_historical_window")
                quantile_haut_roi = st.slider("Upper ROI Quantile", 0.75, 0.95, 0.85, 0.01)
                
                st.text("")
                st.markdown("##### RSI")

                nb_annees_quantile_rsi = st.slider("Historical Window (years)", 1.5, 4.0, 2.0, 0.1, key="sell_rsi_historical_window")
                quantile_haut_rsi = st.slider("Upper RSI Quantile", 0.75, 0.95, 0.85, 0.01)

                st.text("")
                st.markdown("##### Price Volatility")

                fenetre_glissante_volat_vente = st.slider("Rolling Window (days)", 30, 120, 60, key="sell_vol_window")
                fenetre_quantile_volat_vente = st.slider("Historical Window (days)", 500, 1500, 750, key="sell_vol_historical_window")
                quantile_haut_volat_vente = st.slider("Upper Volatility Quantile", 0.75, 0.965, 0.85, 0.005, key="sell_upper_vol_quantile")



        # ============================================================
        # GLOBAL PARAMETER DICTIONARY
        # ============================================================

        params_backtest = {
            "params_volat_achat": {
                "fenetre_glissante_nb_jours_volat_achat": fenetre_glissante_volat_achat,
                "fenetre_quantile_volat_achat": fenetre_quantile_volat_achat,
                "quantile_haut": 0.9,
                "quantile_bas_volat_achat": quantile_bas_volat_achat
            },

            "params_ecart_relatif": {
                "nb_jours_arriere_ecart_relatif": nb_jours_arriere_ecart_relatif,
                "nb_jour_mm_ecart_relatif": nb_jour_mm_ecart_relatif,
                "nb_jour_quantiles_ecart_relatif": nb_jour_quantiles_ecart_relatif,
                "quantile_haut": 0.9,
                "quantile_bas_ecart_relatif": quantile_bas_ecart_relatif
            },

            "params_volat_vente": {
                "fenetre_glissante_nb_jours_volat_vente": fenetre_glissante_volat_vente,
                "fenetre_quantile_volat_vente": fenetre_quantile_volat_vente,
                "quantile_haut_volat_vente": quantile_haut_volat_vente,
                "quantile_bas": 0.1
            },

            "params_roi": {
                "periode_roi_en_jours": periode_roi_en_jours,
                "quantile_haut_roi": quantile_haut_roi,
                "quantile_bas": 0.05,
                "quantile_bas_prix_achat": 0.05,
                "quantile_haut_prix_achat": 0.95,
                "nb_annees_quantile_roi": nb_annees_quantile_roi
            },

            "params_rsi": {
                "length": 14,
                "nb_annees_quantile_rsi": nb_annees_quantile_rsi,
                "quantile_haut_rsi": quantile_haut_rsi,
                "quantile_bas": 0.1,
                "quantile_intermediaire": 0.5
            },

            "critère_rsi_achat": critere_rsi_achat
        }

        st.divider()
        st.markdown("## Investment Universe")
        with st.expander("About the Investment Universes",expanded=False):
            st.markdown(text.investment_universe)

        st.text("")
        universe=st.segmented_control(label="Investment Universe",options=["Historical Top 200","Current Top 500 Filtered","Current Top 200 Filtered"],default="Historical Top 200")

        if universe=="Historical Top 200":
            df=df_top_200_passe
        elif universe=="Current Top 500 Filtered":
            df=df_top_500_filtre
        else:
            df=df_top_200_filtre




        # ======================
        # Backtesting Results
        # ======================
        st.divider()
        st.markdown("## Backtesting")


        with st.expander("About the Backtesting Methodology"):
            st.markdown(text.bt_methodology)
        st.text("")

        #st.markdown("")

        col_button, col2 = st.columns([1,3])

        with col_button:
            bouton = st.form_submit_button(
                "Run Strategy Backtest",
                type="primary",
                use_container_width=True,
                help="Run the strategy using the selected universe and indicator parameters."
            )

    @st.cache_resource(ttl=3600,show_spinner=False,scope="session")
    def recup_backtest(df_close,params):
        return bt.backtest(df_close,params,retirer_trades_non_closed=False)
    
    if bouton==True:
        with st.spinner(text="Running Backtest"):
            resultats=recup_backtest(df,params_backtest)
            st.session_state["resultats_backtest"]=resultats


    if "resultats_backtest" not in st.session_state:
        st.info("Choose the parameters and run a backtest.")
        st.stop()

    
    st.text("")
    st.markdown("#### Configuration Summary")

    with st.expander("Backtest Parameters", expanded=False):

        st.markdown("#### Investment Universe")
        st.markdown(f"**{universe}**")

        st.text("")

        col_buy, col_sell = st.columns(2)

        with col_buy:

            st.markdown("#### Buy Strategy")

            st.markdown("**Price Volatility**")
            st.markdown(f"Rolling Window: {fenetre_glissante_volat_achat} days")
            st.markdown(f"Historical Window: {fenetre_quantile_volat_achat} days")
            st.markdown(f"Lower Volatility Quantile: {quantile_bas_volat_achat:.0%}")

            st.markdown("")

            st.markdown("**Relative Trading Range**")
            st.markdown(f"Rolling Window: {nb_jours_arriere_ecart_relatif} days")
            st.markdown(f"Moving Average Window: {nb_jour_mm_ecart_relatif} days")
            st.markdown(f"Historical Window: {nb_jour_quantiles_ecart_relatif} days")
            st.markdown(f"Lower Trading Range Quantile: {quantile_bas_ecart_relatif:.0%}")

            st.markdown("")

            st.markdown("**RSI Confirmation**")
            st.markdown(f"Buy Threshold: {critere_rsi_achat}")

        with col_sell:

            st.markdown("#### Sell Strategy")

            st.markdown("**Return On Investment (ROI)**")
            st.markdown(f"Rolling Window: {periode_roi_en_jours} days")
            st.markdown(f"Historical Window: {nb_annees_quantile_roi:.1f} years")
            st.markdown(f"Upper ROI Quantile: {quantile_haut_roi:.0%}")

            st.markdown("")

            st.markdown("**RSI Filter**")
            st.markdown(f"Historical Window: {nb_annees_quantile_rsi:.1f} years")
            st.markdown(f"Upper RSI Quantile: {quantile_haut_rsi:.0%}")

            st.markdown("")

            st.markdown("**Price Volatility**")
            st.markdown(f"Rolling Window: {fenetre_glissante_volat_vente} days")
            st.markdown(f"Historical Window: {fenetre_quantile_volat_vente} days")
            st.markdown(f"Upper Volatility Quantile: {quantile_haut_volat_vente:.1%}")

    st.text("")

    st.markdown("#### Statistical Results")

    resultats=st.session_state["resultats_backtest"]
    trades_total=resultats["trades"].copy()

    #trades closed for statistics
    trades=trades_total[trades_total["Trade Status"]=="Closed"].copy()

    stats=analysis.stats_trades(trades,df.shape[1])


    basic_stats=stats["basic_stats"]
    advanced_stats=stats["advanced_stats"]

    col1, col2, col3, col4,col5 = st.columns(5)

    col1.metric("Total Trades", basic_stats["Total Trades"])
    col2.metric("Total Assets Traded", f'{basic_stats["Total Assets Traded"]}')
    col3.metric("Total Assets in Universe", basic_stats["Total Assets in Universe"])
    col4.metric("Universe Coverage", f'{basic_stats["Universe Coverage"]:.1%}', help=text.help_universe_coverage)
    col5.metric("Average trading duration (days)",int(basic_stats["Average Holding Period"]))

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Win Rate", f'{basic_stats["Win Rate"]:.1%}')
    col2.metric("Average Return", f'{basic_stats["Average Return"]:.2f}%')
    col3.metric("Median Return", f'{basic_stats["Median Return"]:.2f}%')
    col4.metric("Avg. Maximum Drawdown", f'{basic_stats["Average Maximum Drawdown"]:.2f}%',help=text.help_mdd)
    col5.metric("Median Maximum Drawdown", f'{basic_stats["Median Maximum Drawdown"]:.2f}%',help=text.help_mdd)

    with st.expander("Other Trade Statistics", expanded=False):
        st.dataframe(advanced_stats, hide_index=True, use_container_width=True)

    camemberts=analysis.camemberts(trades)

    col1,col2=st.columns(2)
    col1.plotly_chart(camemberts["return"])
    col2.plotly_chart(camemberts["duree"])
    
    col1,col2,col3=st.columns([1,3,1])
    col2.plotly_chart(camemberts["mdd"])

    st.write("")
    st.write("")

    nb_trades=trades["Asset"].nunique()
    nb_max = max(1, nb_trades//2)

    portfolio=resultats["portfolio"]

    st.markdown("#### Individual Trade Analysis")
    st.markdown("Explore the complete history and the price charts of the trades generated by the strategy.")
    
    with st.expander("Closed Trades",expanded=True):
        trades_display = trades_total.copy()
        trades_display["Return"] *= 100

        trades_display.rename(columns={
            "Trade Status": "Status",
            "Entry Timestamp": "Entry Date",
            "Exit Timestamp": "Exit Date",
            "Average Entry Price": "Entry Price",
            "Average Exit Price": "Exit Price",
            "Profit & Loss": "P&L",
            "Return": "Return (%)",
            "Maximum Drawdown": "Maximum Drawdown (%)",
            "PnL / Maximum Drawdown": "Return / Maximum Drawdown"
        }, inplace=True)

        trades_display = trades_display[[
            "Asset","Direction", "Status", "Entry Date", "Exit Date",
            "Holding Period (Days)", "Entry Price", "Exit Price",
            "P&L", "Return (%)", "Maximum Drawdown (%)",
            "Return / Maximum Drawdown","Entry Fees","Exit Fees"
        ]]
        trades_display.set_index("Asset",inplace=True)
        st.dataframe(trades_display[trades_display["Status"]=="Closed"],use_container_width=True)

    with st.expander("Best Trades",expanded=False):

        nb=st.slider(label="Number of best trades to display",min_value=1,max_value=nb_trades,value=5)

        best_tokens=analysis.best_trades(trades,nb)
        dico_liste=analysis.extraire_impaires_paires(best_tokens)

        token_paire=dico_liste["pair"]
        token_impaire=dico_liste["impair"]


        col1,col2=st.columns(2)
        with col1:

            for token in token_impaire:

                fig=portfolio.plot(column=token,subplots=["orders"])
                fig.update_yaxes(type="log")

                close=portfolio.close[token]
                close=close.dropna()
                fig.update_xaxes(range=[close.index[0],close.index[-1]])

                fig.update_layout(title=token)
                st.plotly_chart(fig,key=f"{token}_buy")

        with col2:

            for token in token_paire:

                fig=portfolio.plot(column=token,subplots=["orders"])
                fig.update_yaxes(type="log")

                close=portfolio.close[token]
                close=close.dropna()
                fig.update_xaxes(range=[close.index[0],close.index[-1]])

                fig.update_layout(title=token)
                st.plotly_chart(fig,key=f"{token}_buy")

    with st.expander("Worst Trades",expanded=False):


        nb=st.slider(label="Number of worst trades to display",min_value=1,max_value=nb_max,value=5)

        worst_tokens=analysis.worst_trades(trades,nb)

        dico_liste=analysis.extraire_impaires_paires(worst_tokens)

        token_paire=dico_liste["pair"]
        token_impaire=dico_liste["impair"]

        col1,col2=st.columns(2)

        with col1:

            for token in token_impaire:

                fig=portfolio.plot(column=token,subplots=["orders"])
                fig.update_yaxes(type="log")

                close=portfolio.close[token]
                close=close.dropna()
                fig.update_xaxes(range=[close.index[0],close.index[-1]])

                fig.update_layout(title=token)
                st.plotly_chart(fig,key=f"{token}_sell")

        with col2:

            for token in token_paire:

                fig=portfolio.plot(column=token,subplots=["orders"])
                fig.update_yaxes(type="log")

                close=portfolio.close[token]
                close=close.dropna()
                fig.update_xaxes(range=[close.index[0],close.index[-1]])

                fig.update_layout(title=token)
                st.plotly_chart(fig,key=f"{token}_sell")
    


    st.divider()
    st.markdown("## Strategy Optimization")

    median_return = f"sqlite:///{OPTIMIZATIONS_DIR / 'v0_median_return'}"
    median = f"sqlite:///{OPTIMIZATIONS_DIR / 'v0_median'}"
    low_quantile = f"sqlite:///{OPTIMIZATIONS_DIR / 'v0_low_quantile'}"
    
    with st.expander("About the Optimization", expanded=False):

        st.markdown(text.about_optimization)
        st.markdown(text.median_return)
        st.text("")
        st.text("")
        st.markdown(text.median_return_mdd)
        st.text("")
        st.text("")
        st.markdown(text.quantile_return_mdd)

    optimisation_type=st.segmented_control("Optimisation Criterium",["Median Return",'Median Return & Median MDD',"Low Quantile Return & MDD"],default="Median Return")

    if optimisation_type=="Median Return":
        file=median_return
        study_name="v0_median_return"
    elif optimisation_type=='Median Return & Median MDD':
        file=median
        study_name="v0_median"
    else:
        file=low_quantile
        study_name="v0_low_quantile"

    study=optuna.load_study(study_name=study_name,storage=file)

    params=params.recup_params_depuis_moyenne_trials(study,1)


    st.text("")
    with st.spinner(text="Running Optimal Backtest"):
        resultats_opt=recup_backtest(df,params)

    with st.expander("Optimal Parameters", expanded=False):

        col_buy, col_sell = st.columns(2)

        with col_buy:

            st.markdown("#### Buy Strategy")

            st.markdown("**Price Volatility**")
            st.markdown(f"Rolling Window: {params['params_volat_achat']['fenetre_glissante_nb_jours_volat_achat']} days")
            st.markdown(f"Historical Window: {params['params_volat_achat']['fenetre_quantile_volat_achat']} days")
            st.markdown(f"Lower Volatility Quantile: {params['params_volat_achat']['quantile_bas_volat_achat']:.0%}")

            st.markdown("")

            st.markdown("**Relative Trading Range**")
            st.markdown(f"Rolling Window: {params['params_ecart_relatif']['nb_jours_arriere_ecart_relatif']} days")
            st.markdown(f"Moving Average Window: {params['params_ecart_relatif']['nb_jour_mm_ecart_relatif']} days")
            st.markdown(f"Historical Window: {params['params_ecart_relatif']['nb_jour_quantiles_ecart_relatif']} days")
            st.markdown(f"Lower Trading Range Quantile: {params['params_ecart_relatif']['quantile_bas_ecart_relatif']:.0%}")

            st.markdown("")

            st.markdown("**RSI Confirmation**")
            st.markdown(f"Buy Threshold: {params['critère_rsi_achat']}")

        with col_sell:

            st.markdown("#### Sell Strategy")

            st.markdown("**Return on Investment (ROI)**")
            st.markdown(f"Rolling Window: {params['params_roi']['periode_roi_en_jours']} days")
            st.markdown(f"Historical Window: {params['params_roi']['nb_annees_quantile_roi']:.1f} years")
            st.markdown(f"Upper ROI Quantile: {params['params_roi']['quantile_haut_roi']:.0%}")

            st.markdown("")

            st.markdown("**RSI Filter**")
            st.markdown(f"Historical Window: {params['params_rsi']['nb_annees_quantile_rsi']:.1f} years")
            st.markdown(f"Upper RSI Quantile: {params['params_rsi']['quantile_haut_rsi']:.0%}")

            st.markdown("")

            st.markdown("**Price Volatility**")
            st.markdown(f"Rolling Window: {params['params_volat_vente']['fenetre_glissante_nb_jours_volat_vente']} days")
            st.markdown(f"Historical Window: {params['params_volat_vente']['fenetre_quantile_volat_vente']} days")
            st.markdown(f"Upper Volatility Quantile: {params['params_volat_vente']['quantile_haut_volat_vente']:.1%}")

        
    trades_total=resultats_opt["trades"].copy()

    #trades closed for statistics
    trades=trades_total[trades_total["Trade Status"]=="Closed"].copy()

    stats=analysis.stats_trades(trades,df_top_200_passe.shape[1])


    basic_stats=stats["basic_stats"]
    advanced_stats=stats["advanced_stats"]

    with st.expander("Statistical Results"):
        col1, col2, col3, col4,col5 = st.columns(5)

        col1.metric("Total Trades", basic_stats["Total Trades"])
        col2.metric("Total Assets Traded", f'{basic_stats["Total Assets Traded"]}')
        col3.metric("Total Assets in Universe", basic_stats["Total Assets in Universe"])
        col4.metric("Universe Coverage", f'{basic_stats["Universe Coverage"]:.1%}', help=text.help_universe_coverage)
        col5.metric("Average trading duration (days)",int(basic_stats["Average Holding Period"]))

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Win Rate", f'{basic_stats["Win Rate"]:.1%}')
        col2.metric("Average Return", f'{basic_stats["Average Return"]:.2f}%')
        col3.metric("Median Return", f'{basic_stats["Median Return"]:.2f}%')
        col4.metric("Avg. Maximum Drawdown", f'{basic_stats["Average Maximum Drawdown"]:.2f}%',help=text.help_mdd)
        col5.metric("Median Maximum Drawdown", f'{basic_stats["Median Maximum Drawdown"]:.2f}%')

        if st.toggle("Other Trade Statistics", value=False):
            st.dataframe(advanced_stats, hide_index=True, use_container_width=True)

        camemberts=analysis.camemberts(trades)

        col1,col2=st.columns(2)
        col1.plotly_chart(camemberts["return"])
        col2.plotly_chart(camemberts["duree"])
        
        col1,col2,col3=st.columns([1,3,1])
        col2.plotly_chart(camemberts["mdd"])


        st.write("")
        st.write("")

        nb_trades=trades["Asset"].nunique()
        nb_max = max(1, nb_trades//2)

        portfolio=resultats_opt["portfolio"]

    #st.markdown("### Individual Trade Analysis")
    #st.markdown("Explore the price charts and complete history of the trades generated by the strategy.")
   
    with st.expander("Closed Trades",expanded=False):
        trades_display = trades_total.copy()
        trades_display["Return"] *= 100

        trades_display.rename(columns={
            "Trade Status": "Status",
            "Entry Timestamp": "Entry Date",
            "Exit Timestamp": "Exit Date",
            "Average Entry Price": "Entry Price",
            "Average Exit Price": "Exit Price",
            "Profit & Loss": "P&L",
            "Return": "Return (%)",
            "Maximum Drawdown": "Maximum Drawdown (%)",
            "PnL / Maximum Drawdown": "Return / Maximum Drawdown"
        }, inplace=True)

        trades_display = trades_display[[
            "Asset","Direction", "Status", "Entry Date", "Exit Date",
            "Holding Period (Days)", "Entry Price", "Exit Price",
            "P&L", "Return (%)", "Maximum Drawdown (%)",
            "Return / Maximum Drawdown","Entry Fees","Exit Fees"
        ]]
        trades_display.set_index("Asset",inplace=True)
        st.dataframe(trades_display[trades_display["Status"]=="Closed"],use_container_width=True)

    with st.expander("Best Trades",expanded=False):

        nb=st.slider(label="Number of best trades to display",min_value=1,max_value=nb_trades,value=5)

        best_tokens=analysis.best_trades(trades,nb)
        dico_liste=analysis.extraire_impaires_paires(best_tokens)

        token_paire=dico_liste["pair"]
        token_impaire=dico_liste["impair"]


        col1,col2=st.columns(2)
        with col1:

            for token in token_impaire:

                fig=portfolio.plot(column=token,subplots=["orders"])
                fig.update_yaxes(type="log")

                close=portfolio.close[token]
                close=close.dropna()
                fig.update_xaxes(range=[close.index[0],close.index[-1]])

                fig.update_layout(title=token)
                st.plotly_chart(fig,key=f"{token}_buy_opt")

        with col2:

            for token in token_paire:

                fig=portfolio.plot(column=token,subplots=["orders"])
                fig.update_yaxes(type="log")

                close=portfolio.close[token]
                close=close.dropna()
                fig.update_xaxes(range=[close.index[0],close.index[-1]])

                fig.update_layout(title=token)
                st.plotly_chart(fig,key=f"{token}_buy_opt")

    with st.expander("Worst Trades",expanded=False):


        nb=st.slider(label="Number of worst trades to display",min_value=1,max_value=nb_max,value=5)

        worst_tokens=analysis.worst_trades(trades,nb)

        dico_liste=analysis.extraire_impaires_paires(worst_tokens)

        token_paire=dico_liste["pair"]
        token_impaire=dico_liste["impair"]

        col1,col2=st.columns(2)

        with col1:

            for token in token_impaire:

                fig=portfolio.plot(column=token,subplots=["orders"])
                fig.update_yaxes(type="log")

                close=portfolio.close[token]
                close=close.dropna()
                fig.update_xaxes(range=[close.index[0],close.index[-1]])

                fig.update_layout(title=token)
                st.plotly_chart(fig,key=f"{token}_sell_opt")

        with col2:

            for token in token_paire:

                fig=portfolio.plot(column=token,subplots=["orders"])
                fig.update_yaxes(type="log")

                close=portfolio.close[token]
                close=close.dropna()
                fig.update_xaxes(range=[close.index[0],close.index[-1]])

                fig.update_layout(title=token)
                st.plotly_chart(fig,key=f"{token}_sell_opt")

