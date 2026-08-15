"""
=============================================================================
Module DEDIE a la sous-section "Indicator Visualizer" du dashboard Streamlit.
=============================================================================

Il regroupe TOUT ce qui concerne cette sous-section, en un seul fichier :
  - la recuperation LIVE des donnees : liste du top 500 ACTUEL par market cap
    (CoinMarketCap) et historique de prix hebdomadaire (Gate.io, endpoints
    publics, sans cle) ;
  - la construction de la figure Plotly facon TradingView (prix en echelle log
    + fleches de signaux 3/3, panneaux d'indicateurs, crosshair, pan/scroll-zoom).

Panneaux (4) : chaque indicateur est trace en bleu ; les quantiles/seuils sont en
vert (cote achat / bas) ou rouge (cote vente / haut). Volatilite et RSI ne sont PAS
dupliques : un seul panneau chacun, avec les deux quantiles superposes.

Les indicateurs et parametres sont ceux du backtest, MAIS contrairement a
signals.signaux_achats, les signaux d'achat ne sont PAS restreints aux dates
posterieures au bottom du bear market 2021 (masque volontairement absent ici).

NB : les fonctions LIVE font des appels reseau et requierent
st.secrets["CMC_API_KEY"] configure (machine de prod) ; elles ne fonctionnent pas
sans cle / sans reseau.
"""

from datetime import datetime

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from gate_api import Configuration, ApiClient, SpotApi

from utils.QIS.crypto import indicators as ind
from utils.QIS.crypto import data as dt


# --- Couleurs ---------------------------------------------------------------
PRICE_COLOR = "#1f77b4"        # bleu
INDICATOR_COLOR = "#1f77b4"    # bleu (courbe de l'indicateur)
BUY_COLOR = "#2ca02c"          # vert (quantile bas / cote achat / signaux d'achat)
SELL_COLOR = "#d62728"         # rouge (quantile haut / cote vente / signaux de vente)
ORANGE = "#ff7f0e"             # orange (moyenne mobile du relative range)

# --- Panneaux d'affichage (Volatilite et RSI fusionnes, non dupliques) ------
ALL_PANELS = ["Volatility", "Relative Range", "RSI", "ROI"]


# ============================================================================
# Recuperation LIVE des donnees (top 500 actuel + historique hebdo Gate.io)
# ============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def top_500_symbols():
    """Symboles du top 500 ACTUEL par market cap (CoinMarketCap)."""
    return dt.get_top_cmc(0, 500)


@st.cache_data(ttl=3600, show_spinner=False)
def gate_pairs():
    """Ensemble des paires listees sur Gate.io (endpoint public, sans cle)."""
    with ApiClient(Configuration()) as client:
        tickers = SpotApi(client).list_tickers()
    return {t.currency_pair for t in tickers}


@st.cache_data(ttl=3600, show_spinner="Fetching price history...")
def gate_weekly_close(token):
    """
    Historique hebdomadaire (close) d'un token depuis Gate.io (endpoint public).

    Renvoie un DataFrame a une seule colonne nommee `token`, index datetime trie,
    ou un DataFrame vide si la paire n'existe pas / erreur reseau.
    """
    pair = f"{token}_USDT"
    df_global = pd.DataFrame()
    try:
        with ApiClient(Configuration()) as client:
            api = SpotApi(client)
            to_ts = int(datetime.now().timestamp())
            while True:
                data = api.list_candlesticks(
                    currency_pair=pair, interval="7d", limit=1000, to=to_ts
                )
                if not data:
                    break
                for element in data:
                    del element[-2:]  # retire base_volume + window_closed
                df = pd.DataFrame(
                    data, columns=["date", "volume", "close", "high", "low", "open"]
                )
                df_global = pd.concat([df, df_global], ignore_index=True)
                if len(data) < 1000:
                    break
                to_ts = int(data[0][0]) - 1
    except Exception:
        return pd.DataFrame()

    if df_global.empty:
        return pd.DataFrame()

    df_global["close"] = pd.to_numeric(df_global["close"], errors="coerce")
    df_global["date"] = pd.to_datetime(pd.to_numeric(df_global["date"]), unit="s")
    df_global = df_global.set_index("date").sort_index()
    return df_global[["close"]].rename(columns={"close": token})


# ============================================================================
# Construction de la figure
# ============================================================================


def _compute(sub, token, params):
    """Calcule une seule fois toutes les series d'indicateurs pour l'asset."""
    p = params
    va, vv = p["params_volat_achat"], p["params_volat_vente"]
    pe, pr, proi = p["params_ecart_relatif"], p["params_rsi"], p["params_roi"]

    dvb = ind.volat_glissante_prix_quantiles_vectoriel(
        sub, va["fenetre_glissante_nb_jours_volat_achat"], va["fenetre_quantile_volat_achat"],
        va["quantile_haut"], va["quantile_bas_volat_achat"])[token]
    dvs = ind.volat_glissante_prix_quantiles_vectoriel(
        sub, vv["fenetre_glissante_nb_jours_volat_vente"], vv["fenetre_quantile_volat_vente"],
        vv["quantile_haut_volat_vente"], vv["quantile_bas"])[token]
    de = ind.ecart_relatif_moyen_glissant_vectoriel(
        sub, pe["nb_jours_arriere_ecart_relatif"], pe["nb_jour_mm_ecart_relatif"],
        pe["nb_jour_quantiles_ecart_relatif"], pe["quantile_haut"], pe["quantile_bas_ecart_relatif"])[token]
    dr = ind.rsi_avec_quantiles_vectoriel(
        sub, pr["length"], pr["nb_annees_quantile_rsi"], pr["quantile_haut_rsi"],
        pr["quantile_bas"], pr["quantile_intermediaire"])[token]
    droi = ind.roi_avec_quantile_vectoriel(
        sub, proi["periode_roi_en_jours"], proi["quantile_haut_roi"], proi["quantile_bas"],
        proi["quantile_bas_prix_achat"], proi["quantile_haut_prix_achat"],
        proi["nb_annees_quantile_roi"])[token]

    seuil = p["critère_rsi_achat"]
    return {
        # Volatilite (achat = fenetre achat ; vente = fenetre vente)
        "std_buy": dvb["std_glissante_prix"], "vol_qbas": dvb["quantile_bas_glissant_std"],
        "std_sell": dvs["std_glissante_prix"], "vol_qhaut": dvs["quantile_haut_glissant_std"],
        # Relative range
        "range_raw": de["ecart_relatif"], "range_ma": de["mm_ecart_relatif"],
        "range_qbas": de["qbas_glissant_ecart_relatif"],
        # RSI
        "rsi": dr["rsi"], "rsi_qhaut": dr["quantile_haut_glissant_rsi"],
        "rsi_seuil": pd.Series(seuil, index=sub.index), "seuil": seuil,
        # ROI
        "roi": droi["roi_hausse"], "roi_qhaut": droi["quantile_haut_glissant_roi"],
    }


def _signals(c):
    """Signaux 3/3 achat et vente (sans masque de date)."""
    buy = (c["std_buy"] < c["vol_qbas"]) & (c["range_ma"] < c["range_qbas"]) & (c["rsi"] < c["seuil"])
    sell = (c["std_sell"] > c["vol_qhaut"]) & (c["rsi"] > c["rsi_qhaut"]) & (c["roi"] > c["roi_qhaut"])
    return buy.fillna(False), sell.fillna(False)


def _panel_traces(panel, c):
    """Renvoie les traces (serie, nom, couleur) d'un panneau + yrange optionnel."""
    if panel == "Volatility":
        return dict(traces=[
            (c["vol_qbas"], "Lower Vol. Quantile (buy)", BUY_COLOR),
            (c["vol_qhaut"], "Upper Vol. Quantile (sell)", SELL_COLOR),
            (c["std_buy"], "Rolling Volatility", INDICATOR_COLOR),
        ])
    if panel == "Relative Range":
        return dict(traces=[
            (c["range_qbas"], "Lower Range Quantile (buy)", BUY_COLOR),
            (c["range_ma"], "MA Relative Range", ORANGE),
            (c["range_raw"], "Relative Range", INDICATOR_COLOR),
        ])
    if panel == "RSI":
        return dict(traces=[
            (c["rsi_seuil"], f"Buy Threshold ({c['seuil']})", BUY_COLOR),
            (c["rsi_qhaut"], "Upper RSI Quantile (sell)", SELL_COLOR),
            (c["rsi"], "RSI (14)", INDICATOR_COLOR),
        ], yrange=[0, 100])
    if panel == "ROI":
        return dict(traces=[
            (c["roi_qhaut"], "Upper ROI Quantile (sell)", SELL_COLOR),
            (c["roi"], "ROI (up)", INDICATOR_COLOR),
        ])
    raise ValueError(f"Panneau inconnu : {panel}")


def _add_indicator_panel(fig, row, panel):
    for series, name, color in panel["traces"]:
        fig.add_trace(go.Scatter(x=series.index, y=series.values, mode="lines", name=name,
                                 line=dict(color=color, width=1.3), showlegend=False),
                      row=row, col=1)
    if panel.get("yrange"):
        fig.update_yaxes(range=panel["yrange"], row=row, col=1)


def build_figure(df_token, token, params, panels, panel_height=240):
    """
    Construit la figure Plotly (prix + panneaux d'indicateurs) pour un asset.

    Parameters
    ----------
    df_token     : pd.DataFrame  (une colonne, nommee `token`, index = dates)
    token        : str
    params       : dict          (meme structure que params_backtest)
    panels       : liste de noms de panneaux (sous-ensemble de ALL_PANELS)
    panel_height : int           hauteur (px) de chaque panneau ; l'echelle Y se
                                 zoome ensuite directement sur le graphique (drag/scroll).
    """
    # Historique de l'asset a partir de son premier prix disponible
    fvi = df_token[token].first_valid_index()
    sub = df_token.loc[fvi:] if fvi is not None else df_token
    close = sub[token]

    # Garde-fou : ne JAMAIS planter si l'historique est trop court (< 3 bougies,
    # sinon index[1] leve une IndexError dans les indicateurs vectorises).
    if len(sub.dropna()) < 3:
        fig = go.Figure()
        fig.add_annotation(text=f"Not enough price history for {token}.",
                           showarrow=False, font=dict(size=14, color="#888888"))
        fig.update_layout(height=180, template="plotly_white",
                          xaxis=dict(visible=False), yaxis=dict(visible=False))
        return fig

    c = _compute(sub, token, params)
    buy_sig, sell_sig = _signals(c)
    buy_sig = buy_sig.reindex(sub.index).fillna(False)
    sell_sig = sell_sig.reindex(sub.index).fillna(False)

    panels = [pn for pn in ALL_PANELS if pn in panels]
    n_rows = 1 + len(panels)
    price_px = 320
    row_heights = [price_px] + [panel_height] * len(panels) if panels else [price_px]
    titles = ["Price"] + panels

    fig = make_subplots(rows=n_rows, cols=1, shared_xaxes=True,
                        vertical_spacing=0.03, row_heights=row_heights,
                        subplot_titles=titles)

    # --- Panneau prix -------------------------------------------------------
    fig.add_trace(go.Scatter(x=close.index, y=close.values, mode="lines", name="Close",
                             line=dict(color=PRICE_COLOR, width=1.5)), row=1, col=1)

    buy_dates = close.index[buy_sig.values]
    sell_dates = close.index[sell_sig.values]
    if len(buy_dates):
        fig.add_trace(go.Scatter(
            x=buy_dates, y=close.loc[buy_dates].values * 0.9, mode="markers",
            name="Buy signal (3/3)",
            marker=dict(symbol="triangle-up", color=BUY_COLOR, size=12,
                        line=dict(width=0.5, color="white"))), row=1, col=1)
    if len(sell_dates):
        fig.add_trace(go.Scatter(
            x=sell_dates, y=close.loc[sell_dates].values * 1.1, mode="markers",
            name="Sell signal (3/3)",
            marker=dict(symbol="triangle-down", color=SELL_COLOR, size=12,
                        line=dict(width=0.5, color="white"))), row=1, col=1)
    fig.update_yaxes(type="log", row=1, col=1)

    # --- Panneaux d'indicateurs --------------------------------------------
    for i, panel in enumerate(panels, start=2):
        _add_indicator_panel(fig, i, _panel_traces(panel, c))

    fig.update_layout(
        height=price_px + panel_height * len(panels),
        hovermode="x unified",
        template="plotly_white",
        margin=dict(l=60, r=20, t=45, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.015, xanchor="right", x=1),
        spikedistance=-1,
        dragmode="pan",
    )
    # Echelle Y de chaque panneau ajustable directement (drag / scroll sur l'axe)
    fig.update_yaxes(fixedrange=False)
    # Crosshair vertical traversant tous les panneaux (axes x partages)
    fig.update_xaxes(showspikes=True, spikemode="across", spikesnap="cursor",
                     spikecolor="#888888", spikethickness=1, spikedash="solid")
    fig.update_xaxes(range=[close.index[0], close.index[-1]])
    return fig
