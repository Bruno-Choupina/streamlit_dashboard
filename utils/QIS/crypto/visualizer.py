"""
=============================================================================
Module DEDIE a la sous-section "Indicator Visualizer" du dashboard Streamlit.
=============================================================================

Il regroupe TOUT ce qui concerne cette sous-section, en un seul fichier :
  - la recuperation LIVE des donnees : liste du top 500 ACTUEL par market cap
    (CoinMarketCap) et historique de prix hebdomadaire (Gate.io, via
    data.hist_prix_gate_simple, authentifie avec GATE_API_KEY/GATE_API_SECRET) ;
  - la construction de la figure Plotly facon TradingView (prix en echelle log
    + fleches de signaux 3/3, panneaux d'indicateurs, crosshair, pan/scroll-zoom).

Panneaux (5) : chaque indicateur est trace en bleu ; les quantiles/seuils sont en
vert (cote achat / bas) ou rouge (cote vente / haut). La volatilite a DEUX panneaux
(achat et vente) car ses fenetres/parametres different -> ce sont deux courbes std
distinctes. Le RSI est unique (meme courbe) avec son seuil d'achat (vert) et son
quantile de vente (rouge).

Les indicateurs et parametres sont ceux du backtest, MAIS contrairement a
signals.signaux_achats, les signaux d'achat ne sont PAS restreints aux dates
posterieures au bottom du bear market 2021 (masque volontairement absent ici).

NB : les fonctions LIVE font des appels reseau et requierent st.secrets["CMC_API_KEY"],
st.secrets["GATE_API_KEY"] et st.secrets["GATE_API_SECRET"] configures (machine de
prod) ; elles ne fonctionnent pas sans cle / sans reseau.
"""

import json
from datetime import date
from pathlib import Path

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
ALL_PANELS = ["Volatility (Buy)", "Volatility (Sell)", "Relative Range", "RSI", "ROI"]

# Libelles d'affichage (facon _render_breadth_stats) -> cle interne de
# selection_breadth()['breadth'/'members']. Ordre : cote achat puis vente,
# signaux combines (3/3, 2/3) avant les conditions individuelles.
CRITERION_LABELS = [
    ("Buy Signal (3/3)", "Buy 3/3"),
    ("Buy Signal (2/3)", "Buy 2/3"),
    ("Volatility Low (Buy)", "Vol Low (Buy)"),
    ("Range Low (Buy)", "Range Low (Buy)"),
    ("RSI Low (Buy)", "RSI Low (Buy)"),
    ("Sell Signal (3/3)", "Sell 3/3"),
    ("Sell Signal (2/3)", "Sell 2/3"),
    ("Volatility High (Sell)", "Vol High (Sell)"),
    ("RSI High (Sell)", "RSI High (Sell)"),
    ("ROI High (Sell)", "ROI High (Sell)"),
]

# Panneau(x) d'indicateur pertinents pour chaque critere. Pour les signaux
# combines (3/3, 2/3), les 3 panneaux du cote concerne sont tous pertinents
# puisque le signal depend des 3 conditions simultanement.
CRITERION_PANELS = {
    "Buy 3/3": (),
    "Buy 2/3": (),
    "Vol Low (Buy)": ("Volatility (Buy)",),
    "Range Low (Buy)": ("Relative Range",),
    "RSI Low (Buy)": ("RSI",),
    "Sell 3/3": (),
    "Sell 2/3": (),
    "Vol High (Sell)": ("Volatility (Sell)",),
    "RSI High (Sell)": ("RSI",),
    "ROI High (Sell)": ("ROI",),
}

# Cle d'affichage -> cle du dict renvoye par _compute (voir selection_breadth).
# Volontairement sans la volatilite : std_buy/std_sell sont des ecarts-type de
# PRIX bruts, dont l'echelle differe trop d'un actif a l'autre (BTC vs un
# altcoin a 0.01 $) pour qu'une moyenne inter-actifs ait un sens, sauf a les
# normaliser par le prix (pas fait ici).
LEVEL_SERIES = {
    "Relative Range (at reference date)": "range_raw",
    "Relative Range MA (at reference date)": "range_ma",
    "Lower Range Quantile (Buy)": "range_qbas",
    "RSI (at reference date)": "rsi",
    "Upper RSI Quantile (Sell)": "rsi_qhaut",
    "ROI from recent low (at reference date)": "roi",
    "Upper ROI Quantile (Sell)": "roi_qhaut",
}


# ============================================================================
# Recuperation LIVE des donnees (top 500 actuel + historique hebdo Gate.io)
# ============================================================================

TOP_500_CACHE_FILE = Path(__file__).resolve().parent / "cache" / "top_500_symbols.json"


@st.cache_data(ttl=3600, show_spinner=False)
def top_500_symbols():
    """
    Symboles du top 500 ACTUEL par market cap (CoinMarketCap), avec un cache
    disque quotidien : au plus UN appel a l'API CMC par jour (credits limites),
    quel que soit le nombre d'utilisateurs. Le cache @st.cache_data (ttl=3600)
    au-dessus evite meme de relire ce fichier plus d'une fois par heure tant
    que le process ne redemarre pas.
    """
    today = date.today().isoformat()
    if TOP_500_CACHE_FILE.exists():
        try:
            cached = json.loads(TOP_500_CACHE_FILE.read_text())
            if cached.get("date") == today and cached.get("symbols"):
                return cached["symbols"]
        except Exception:
            pass  # cache illisible/corrompu -> on refait l'appel API

    symbols = dt.get_top_cmc(0, 500)
    # Meme filtre stablecoin que les univers de backtest (data.retirer_stables) :
    # ils faussent les stats de signaux et n'interessent personne a tracer.
    symbols = dt.retirer_stables(pd.DataFrame(columns=symbols)).columns.tolist()
    TOP_500_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOP_500_CACHE_FILE.write_text(json.dumps({"date": today, "symbols": symbols}))
    return symbols


@st.cache_data(ttl=3600, show_spinner=False)
def gate_pairs():
    """Ensemble des paires listees sur Gate.io (endpoint public, sans cle)."""
    with ApiClient(Configuration()) as client:
        tickers = SpotApi(client).list_tickers()
    return {t.currency_pair for t in tickers}


@st.cache_data(ttl=3600, show_spinner="Fetching price history...")
def gate_weekly_close(token):
    """
    Historique hebdomadaire (close) d'un token, via data.hist_prix_gate_simple
    (authentifie avec GATE_API_KEY / GATE_API_SECRET).

    Renvoie un DataFrame a une seule colonne nommee `token`, index datetime trie,
    ou un DataFrame vide si la paire n'existe pas / erreur reseau.
    """
    df = dt.hist_prix_gate_simple(token, timeframe="7d")
    if df.empty or "close" not in df.columns:
        return pd.DataFrame()
    return df[["close"]].rename(columns={"close": token})


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
    if panel == "Volatility (Buy)":
        return dict(traces=[
            (c["vol_qbas"], "Lower Vol. Quantile (buy)", BUY_COLOR),
            (c["std_buy"], "Rolling Volatility", INDICATOR_COLOR),
        ])
    if panel == "Volatility (Sell)":
        return dict(traces=[
            (c["vol_qhaut"], "Upper Vol. Quantile (sell)", SELL_COLOR),
            (c["std_sell"], "Rolling Volatility", INDICATOR_COLOR),
        ])
    if panel == "Relative Range":
        # Cadre l'axe Y sur les valeurs DEPUIS 2020 pour ne pas ecraser le present a cause
        # des vieux pics exageres (pre-2020) ; marge large (x1.4) pour ne pas trop zoomer.
        # L'axe reste zoomable manuellement (scroll sur l'axe).
        recent = pd.concat([c["range_raw"].loc["2020-01-01":].dropna(),
                            c["range_ma"].loc["2020-01-01":].dropna()])
        yrange = [0, float(recent.max()) * 1.4] if len(recent) and recent.max() > 0 else None
        return dict(traces=[
            (c["range_qbas"], "Lower Range Quantile (buy)", BUY_COLOR),
            (c["range_ma"], "MA Relative Range", ORANGE),
            (c["range_raw"], "Relative Range", INDICATOR_COLOR),
        ], yrange=yrange)
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
                             line=dict(color=PRICE_COLOR, width=2.5)), row=1, col=1)

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


@st.cache_data(show_spinner=False)
def _compute_for_token(token, params):
    """
    Calcule les indicateurs (_compute) d'un token, mis en cache independamment
    de lookback_weeks : ce calcul (les quantiles nearest-rank notamment, non
    vectorises) est couteux et ne depend pas de la fenetre de lookback, qui
    n'intervient qu'a l'etape finale (.tail(w).any()) dans selection_breadth.
    Sans ce cache dedie, bouger le slider de lookback recalculait tout pour
    chaque token selectionne, meme si les prix/indicateurs n'avaient pas change.
    """
    df_token = gate_weekly_close(token)
    if df_token.empty:
        return None
    fvi = df_token[token].first_valid_index()
    sub = df_token.loc[fvi:] if fvi is not None else df_token
    if len(sub.dropna()) < 3:
        return None
    return _compute(sub, token, params)


def selection_breadth(tokens, params, lookback_weeks, reference_date=None):
    """
    Statistiques agregees ('market breadth') sur un ensemble de tokens.

    Pour chaque condition d'achat/vente et pour les signaux 3/3 et 2/3 (au sens
    de signals.signaux_vente_decomposee : nombre de conditions satisfaites
    simultanement), calcule la part des tokens de la selection qui l'ont
    declenchee au moins une fois sur les `lookback_weeks` semaines precedant
    `reference_date`. Toutes les statistiques renvoyees sont donc des parts
    de l'univers selectionne (0 a 100%) : aucun niveau de quantile brut n'est
    expose ici (un niveau de ROI ou de volatilite n'est pas borne a 100%, ce
    n'est pas une part d'univers, donc ca n'a pas sa place dans ces stats).

    reference_date permet de comparer la situation actuelle a une date passee
    (ex. le bas d'un bear market) SANS aucun recalcul couteux : les series
    d'indicateurs mises en cache par _compute_for_token sont causales par
    construction (une valeur a la date D ne depend jamais des dates > D), donc
    "les statistiques a la date D" reviennent simplement a relire une tranche
    differente de ces memes series deja calculees.

    Parameters
    ----------
    tokens         : liste de symboles (recuperes via gate_weekly_close)
    params         : dict (meme structure que params_backtest)
    lookback_weeks : int
    reference_date : date-like ou None. None = donnees les plus recentes
                     disponibles (comportement "aujourd'hui").

    Returns
    -------
    dict avec :
      - 'breadth' : nom -> fraction 0-1 ou None
      - 'n_tokens' : nb de tokens exploitables
      - 'evaluated_tokens' : liste des tokens effectivement pris en compte
      - 'members' : nom -> liste des tokens (parmi evaluated_tokens) qui ont
        declenche ce critere au moins une fois sur la fenetre de lookback ;
        permet d'afficher les graphiques des actifs concernes (ou, par
        complement avec evaluated_tokens, de ceux qui ne le sont pas).
    """
    ref_ts = pd.Timestamp(reference_date) if reference_date is not None else None

    breadth_flags = {k: [] for k in [
        "Vol Low (Buy)", "Range Low (Buy)", "RSI Low (Buy)",
        "Vol High (Sell)", "RSI High (Sell)", "ROI High (Sell)",
        "Buy 3/3", "Buy 2/3", "Sell 3/3", "Sell 2/3",
    ]}
    evaluated_tokens = []
    level_values = {k: [] for k in LEVEL_SERIES}
    n_used = 0

    for token in tokens:
        c = _compute_for_token(token, params)
        if c is None:
            continue

        cond_vol_buy = (c["std_buy"] < c["vol_qbas"]).fillna(False)
        cond_range_buy = (c["range_ma"] < c["range_qbas"]).fillna(False)
        cond_rsi_buy = (c["rsi"] < c["seuil"]).fillna(False)
        cond_vol_sell = (c["std_sell"] > c["vol_qhaut"]).fillna(False)
        cond_rsi_sell = (c["rsi"] > c["rsi_qhaut"]).fillna(False)
        cond_roi_sell = (c["roi"] > c["roi_qhaut"]).fillna(False)

        if ref_ts is not None:
            cond_vol_buy = cond_vol_buy.loc[:ref_ts]
            cond_range_buy = cond_range_buy.loc[:ref_ts]
            cond_rsi_buy = cond_rsi_buy.loc[:ref_ts]
            cond_vol_sell = cond_vol_sell.loc[:ref_ts]
            cond_rsi_sell = cond_rsi_sell.loc[:ref_ts]
            cond_roi_sell = cond_roi_sell.loc[:ref_ts]
            if len(cond_vol_buy) < 3:
                # Le token n'existait pas encore (assez) a reference_date : on
                # l'exclut plutot que de le compter avec des conditions toutes
                # a False, ce qui diluerait artificiellement les pourcentages.
                continue

        n_used += 1
        evaluated_tokens.append(token)

        for level_key, series_key in LEVEL_SERIES.items():
            s = c[series_key]
            s = s if ref_ts is None else s.loc[:ref_ts]
            s = s.dropna()
            if len(s):
                level_values[level_key].append(float(s.iloc[-1]))

        buy_count = cond_vol_buy.astype(int) + cond_range_buy.astype(int) + cond_rsi_buy.astype(int)
        sell_count = cond_vol_sell.astype(int) + cond_rsi_sell.astype(int) + cond_roi_sell.astype(int)

        w = lookback_weeks
        breadth_flags["Vol Low (Buy)"].append(bool(cond_vol_buy.tail(w).any()))
        breadth_flags["Range Low (Buy)"].append(bool(cond_range_buy.tail(w).any()))
        breadth_flags["RSI Low (Buy)"].append(bool(cond_rsi_buy.tail(w).any()))
        breadth_flags["Vol High (Sell)"].append(bool(cond_vol_sell.tail(w).any()))
        breadth_flags["RSI High (Sell)"].append(bool(cond_rsi_sell.tail(w).any()))
        breadth_flags["ROI High (Sell)"].append(bool(cond_roi_sell.tail(w).any()))
        breadth_flags["Buy 3/3"].append(bool((buy_count.tail(w) == 3).any()))
        breadth_flags["Buy 2/3"].append(bool((buy_count.tail(w) == 2).any()))
        breadth_flags["Sell 3/3"].append(bool((sell_count.tail(w) == 3).any()))
        breadth_flags["Sell 2/3"].append(bool((sell_count.tail(w) == 2).any()))

    breadth = {k: (sum(v) / len(v) if v else None) for k, v in breadth_flags.items()}
    members = {
        k: [evaluated_tokens[i] for i, matched in enumerate(flags) if matched]
        for k, flags in breadth_flags.items()
    }
    levels = {k: (sum(v) / len(v) if v else None) for k, v in level_values.items()}
    return {
        "breadth": breadth, "n_tokens": n_used,
        "evaluated_tokens": evaluated_tokens, "members": members,
        "levels": levels,
    }


def levels_table(levels):
    """
    Construit un DataFrame d'affichage (Metric / Value / Comment), dans le
    meme format que analysis.stats_trades (colonne Value en pourcentage sauf
    le RSI qui reste sur son echelle brute 0-100), a partir du dict 'levels'
    renvoye par selection_breadth. Complementaire des cartes de breadth : ce
    ne sont PAS des parts de l'univers (un ROI peut depasser 100%), donc
    affichees separement pour eviter toute confusion.
    """
    def pct(x):
        return round(float(x) * 100, 1) if x is not None else None

    def raw(x):
        return round(float(x), 1) if x is not None else None

    rows = [
        ("Relative Range (at reference date)", "Relative Range",
         pct(levels["Relative Range (at reference date)"]),
         "Average relative trading range across the sample, as of the reference date."),
        ("Relative Range MA (at reference date)", "Relative Range MA",
         pct(levels["Relative Range MA (at reference date)"]),
         "Average moving average of the relative trading range across the sample, as of "
         "the reference date."),
        ("Lower Range Quantile (Buy)", "Lower Range Quantile (Buy)",
         pct(levels["Lower Range Quantile (Buy)"]),
         "Average lower relative trading range quantile (buy threshold) across the "
         "sample, as of the reference date."),
        ("RSI (at reference date)", "RSI",
         raw(levels["RSI (at reference date)"]),
         "Average RSI across the sample, as of the reference date (0-100 scale)."),
        ("Upper RSI Quantile (Sell)", "Upper RSI Quantile (Sell)",
         raw(levels["Upper RSI Quantile (Sell)"]),
         "Average upper RSI quantile (sell threshold) across the sample, as of the "
         "reference date (0-100 scale)."),
        ("ROI from recent low (at reference date)", "ROI from recent low",
         pct(levels["ROI from recent low (at reference date)"]),
         "Average ROI from each asset's recent price low across the sample, as of the "
         "reference date."),
        ("Upper ROI Quantile (Sell)", "Upper ROI Quantile (Sell)",
         pct(levels["Upper ROI Quantile (Sell)"]),
         "Average upper ROI quantile (sell threshold) across the sample, as of the "
         "reference date."),
    ]
    rows = [(label, value, comment) for _, label, value, comment in rows]
    return pd.DataFrame(rows, columns=["Metric", "Value", "Comment"])
