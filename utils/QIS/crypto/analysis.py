import math
from pprint import pprint
from collections import OrderedDict
import plotly.graph_objects
import plotly

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express
import seaborn as sns
from IPython.display import display

from utils.QIS.crypto.indicators import (
    volat_glissante_prix_quantiles_vectoriel,
    rsi_avec_quantiles_vectoriel,
    roi_avec_quantile_vectoriel,
)

from utils.QIS.crypto.signals import (
    signaux_vente_v3_decomposee,
)

from utils.QIS.crypto.backtesting import mdd_df_trades
from utils.QIS.crypto.params import ensure_params_v3

def best_trades(df_trades,nb):
    #etant donné le df des trades, récupère la liste des nbs assets aux meilleurs return 

    df=df_trades.sort_values(by="Return",ascending=False)
    return df.iloc[0:nb+1]["Asset"].unique().tolist()

def extraire_impaires_paires(liste):

    liste_paire=[]
    liste_impaire=[]

    for i in range(1, len(liste)):
        if i%2 != 0:
            liste_impaire.append(liste[i-1])
        else:
            liste_paire.append(liste[i-1])
    return {
        "pair":liste_paire,
        "impair":liste_impaire
    }

def worst_trades(df_trades,nb):

    df=df_trades.sort_values(by="Return",ascending=True)
    return df.iloc[:nb+1]["Asset"].to_list()


def part_traitee(portfolio,type_part="tokens"):

    nb_crypto=len(portfolio.wrapper.columns)
    
    if nb_crypto ==0:
        return 0
    
    trades=portfolio.trades.records_readable

    if type_part=="tokens":
        tokens_traites=trades["Column"].nunique()
    elif type_part=="trades":
        tokens_traites=len(trades)

    return tokens_traites/nb_crypto

def stats_trades(df_trades, nb_tokens_total):
    """
    Calcule les statistiques principales et avancées des trades.

    Returns:
        dict contenant :
            - "basic_stats" : dictionnaire de 10 statistiques principales
            - "advanced_stats" : DataFrame des statistiques avancées
    """

    df = df_trades.copy()

    required_columns = {"Asset", "Return", "Maximum Drawdown", "Holding Period (Days)"}
    missing_columns = required_columns.difference(df.columns)

    if missing_columns:
        raise ValueError(f"Missing columns in df_trades: {sorted(missing_columns)}")

    for column in ["Return", "Maximum Drawdown", "Holding Period (Days)"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    returns = df["Return"].dropna()
    winning_returns = returns[returns > 0]
    losing_returns = returns[returns < 0]
    drawdowns = df["Maximum Drawdown"].dropna()
    holding_periods = df["Holding Period (Days)"].dropna()

    total_trades = len(df)
    total_assets_traded = int(df["Asset"].nunique())
    universe_coverage = total_assets_traded / nb_tokens_total if nb_tokens_total > 0 else 0

    win_rate = (returns > 0).mean() if not returns.empty else 0
    average_return = returns.mean() * 100 if not returns.empty else 0
    median_return = returns.median() * 100 if not returns.empty else 0
    best_return = returns.max() * 100 if not returns.empty else 0
    worst_return = returns.min() * 100 if not returns.empty else 0
    return_std = returns.std() * 100 if len(returns) > 1 else 0
    return_10th_percentile = returns.quantile(0.10) * 100 if not returns.empty else 0

    if not returns.empty:
        cutoff = max(1, int(len(returns) * 0.95))
        average_return_excluding_top_5 = returns.sort_values().iloc[:cutoff].mean() * 100
    else:
        average_return_excluding_top_5 = 0

    average_loss = losing_returns.mean() * 100 if not losing_returns.empty else 0
    average_gain = winning_returns.mean() * 100 if not winning_returns.empty else 0

    gross_profit = winning_returns.sum()
    gross_loss = abs(losing_returns.sum())

    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf") if gross_profit > 0 else 0
    payoff_ratio = average_gain / abs(average_loss) if average_loss < 0 else float("inf") if average_gain > 0 else 0

    average_maximum_drawdown = drawdowns.mean() if not drawdowns.empty else 0
    maximum_drawdown_10th_percentile = drawdowns.quantile(0.10) if not drawdowns.empty else 0

    average_holding_period = holding_periods.mean() if not holding_periods.empty else 0
    average_winning_duration = df.loc[df["Return"] > 0, "Holding Period (Days)"].mean()
    average_losing_duration = df.loc[df["Return"] < 0, "Holding Period (Days)"].mean()

    basic_stats = {
        "Total Trades": int(total_trades),
        "Total Assets in Universe": int(nb_tokens_total),
        "Total Assets Traded": total_assets_traded,
        "Universe Coverage": round(float(universe_coverage), 4),
        "Win Rate": round(float(win_rate), 4),
        "Average Return": round(float(average_return), 4),
        "Median Return": round(float(median_return), 4),
        "Return Standard Deviation": round(float(return_std), 4),
        "Average Maximum Drawdown": round(float(average_maximum_drawdown), 4),
        "Average Holding Period": round(float(average_holding_period), 2)
    }

    advanced_stats = pd.DataFrame({
        "Metric": [
            "Best Return",
            "Worst Return",
            "Average Return Excluding Top 5%",
            "10th Percentile Return",
            "Average Loss",
            "Profit Factor",
            "Payoff Ratio",
            "10th Percentile Maximum Drawdown",
            "Average Winning Trade Duration (days)",
            "Average Losing Trade Duration (days)"
        ],
        "Value": [
            round(float(best_return), 4),
            round(float(worst_return), 4),
            round(float(average_return_excluding_top_5), 4),
            round(float(return_10th_percentile), 4),
            round(float(average_loss), 4),
            round(float(profit_factor), 4),
            round(float(payoff_ratio), 4),
            round(float(maximum_drawdown_10th_percentile), 4),
            round(float(average_winning_duration), 2),
            round(float(average_losing_duration), 2)
        ],
        "Comment": [
            "Highest return achieved by a single trade (%).",
            "Lowest return achieved by a single trade (%).",
            "Average return after excluding the top 5% highest trade returns (%).",
            "Return exceeded by 90% of trades; only the worst 10% performed below this value (%).",
            "Average return of losing trades (%).",
            "Total gains divided by the absolute value of total losses.",
            "Average winning return divided by the absolute value of the average losing return.",
            "Maximum drawdown exceeded by 90% of trades; only the worst 10% of trades experienced a larger drawdown (%).",
            "Average holding period of profitable trades (days).",
            "Average holding period of losing trades (days)."
        ]
    })

    return {"basic_stats": basic_stats, "advanced_stats": advanced_stats}


def indice_composite_v0(trades, params_optimisation):
    """
    Calcule un indice composite normalisé entre 0 et 1.

    Le dictionnaire params_optimisation doit contenir :

        params_optimisation["quantiles"]["return"]
        params_optimisation["quantiles"]["mdd"]

        params_optimisation["poids"]["return"]
        params_optimisation["poids"]["mdd"]

        params_optimisation["bornes"]["return"]
        params_optimisation["bornes"]["mdd"]
    """

    quantile_return = params_optimisation["quantiles"]["return"]
    quantile_mdd = params_optimisation["quantiles"]["mdd"]

    poids_return = params_optimisation["poids"]["return"]
    poids_mdd = params_optimisation["poids"]["mdd"]

    borne_return = params_optimisation["bornes"]["return"]
    borne_mdd = params_optimisation["bornes"]["mdd"]

    if not 0 <= quantile_return <= 1:
        raise ValueError("Le quantile du return doit être compris entre 0 et 1.")

    if not 0 <= quantile_mdd <= 1:
        raise ValueError("Le quantile du MDD doit être compris entre 0 et 1.")

    if not np.isclose(poids_return + poids_mdd, 1):
        raise ValueError("La somme des poids doit être égale à 1.")

    if borne_return <= 0 or borne_mdd <= 0:
        raise ValueError("Les bornes doivent être strictement positives.")

    trades_closed = trades.loc[
        trades["Status"] == "Closed"
    ].copy()

    if trades_closed.empty:
        return {
            "indice": 0.0,
            "return_stat": np.nan,
            "mdd_stat": np.nan,
            "return_norm": 0.0,
            "mdd_norm": 0.0,
            "contribution_return": 0.0,
            "contribution_mdd": 0.0
        }

    # VectorBT exprime Return sous forme décimale
    returns_pct = trades_closed["Return"] * 100

    # Maximum Drawdown est déjà exprimé en pourcentage
    mdd_pct = trades_closed["max_drawdown"].abs()

    return_stat = returns_pct.quantile(quantile_return)
    mdd_stat = mdd_pct.quantile(quantile_mdd)

    return_norm = np.clip(
        return_stat / borne_return,
        0,
        1
    )

    mdd_norm = np.clip(
        1 - mdd_stat / borne_mdd,
        0,
        1
    )

    contribution_return = poids_return * return_norm
    contribution_mdd = poids_mdd * mdd_norm

    indice = contribution_return + contribution_mdd

    return {
        "indice": float(indice),
        "return_stat": float(return_stat),
        "mdd_stat": float(mdd_stat),
        "return_norm": float(return_norm),
        "mdd_norm": float(mdd_norm),
        "contribution_return": float(contribution_return),
        "contribution_mdd": float(contribution_mdd)
    }


def indice_composite(trades, pondes, type_occurrence="part_token"):

    """
    Calcule un score composite à partir de trades FERMÉS, en normalisant chaque composante
    de façon linéaire selon des bornes absolues définies manuellement.
    - Utilise le PnL médian.
    - Évite les outliers.
    - Intègre un critère sur la part des trades fermés.
    """

    trades_closed = trades[trades["Status"] == "Closed"].copy()
    nb_total_trades = len(trades)
    nb_closed_trades = len(trades_closed)

    if nb_closed_trades == 0 or nb_total_trades == 0:
        return {
            "indice": 0,
            "poids_pnl": 0,
            "poids_win_rate": 0,
            "poids_mdd": 0,
            "poids_occurence": 0,
            "poids_duree": 0,
            "poids_fermes": 0,
        }

    # ---- 1. Part de l'univers traitée
    if type_occurrence == "part_token":
        part_token = trades_closed["Column"].nunique() / trades_closed["nb_tokens_total"].iloc[0]
    elif type_occurrence == "part_trades":
        part_token = nb_closed_trades / trades_closed["nb_trades_total"].iloc[0]
    else:
        raise ValueError("type_occurrence doit être 'part_token' ou 'part_trades'")
    
    part_token = min(max(part_token, 0), 1)

    # ---- 3. PnL médian
    pnl_median = trades_closed["PnL"].median()
    pnl_max = 400
    pnl_norm = pnl_median / pnl_max
    pnl_norm = min(max(pnl_norm, 0), 1)

    # ---- 4. Win rate
    win_rate = (trades_closed["PnL"] > 0).mean()
    win_rate_norm = min(max(win_rate, 0), 1)

    # ---- 5. MDD moyen (linéaire inversée)
    mean_mdd = trades_closed["max_drawdown"].mean()
    mdd_max_abs = 0.75
    mdd_norm = 1 - (abs(mean_mdd) / 100) / mdd_max_abs
    mdd_norm = min(max(mdd_norm, 0), 1)

    # ---- 6. Part de trades fermés parmi tous les trades
    part_fermes = nb_closed_trades / nb_total_trades
    part_fermes_norm = min(max(part_fermes, 0), 1)

    # ---- 7. Pondération finale
    poids_pnl = pondes.get("pnl", 0) * pnl_norm
    poids_win_rate = pondes.get("win_rate", 0) * win_rate_norm
    poids_occurence = pondes.get("occurence", 0) * part_token
    poids_mdd = pondes.get("mdd", 0) * mdd_norm
    poids_fermes = pondes.get("part_fermes", 0) * part_fermes_norm

    indice = poids_pnl + poids_win_rate + poids_mdd + poids_occurence + poids_fermes

    return {
        "indice": indice,
        "poids_pnl": poids_pnl,
        "poids_win_rate": poids_win_rate,
        "poids_mdd": poids_mdd,
        "poids_occurence": poids_occurence,
        "poids_fermes": poids_fermes,
    }



def camemberts(df_trades):
    fig_return=plotly.graph_objects.Figure()
    fig_duree=plotly.graph_objects.Figure()
    fig_mdd=plotly.graph_objects.Figure()

    bins_return= [-float("inf"), -50, -25, -10, 0,25, 50, 100, 200,300,400, 500, float("inf")]
    labels_return = [
        "< -50%",
        "-50% to -25%",
        "-25% to -10%",
        "-10% to 0%",
        "0% to 25%",
        "25% to 50%",
        "50% to 100%",
        "100% to 200%",
        "200% to 300%",
        "300% to 400%",
        "400% to 500%",
        "> 500%"
    ]

    colors_return = [
        "#7F0000",  # < -50%         : perte extrême
        "#B71C1C",  # -50% à -25%    : très forte perte
        "#E53935",  # -25% à -10%    : forte perte
        "#EF9A9A",  # -10% à 0%      : faible perte
        "#D9D9D9",  # 0% à 25%       : rendement faible / neutre
        "#C8E6C9",  # 25% à 50%      : rendement positif modéré
        "#81C784",  # 50% à 100%     : bon rendement
        "#4CAF50",  # 100% à 200%    : très bon rendement
        "#2E7D32",  # 200% à 300%    : excellent rendement
        "#1B5E20",  # 300% à 400%    : rendement exceptionnel
        "#0B3D1B",  # 400% à 500%    : rendement extrêmement élevé
        "#00C853",  # > 500%         : rendement hors norme
    ]

    bins_duree = [0, 50, 100, 200, 300, 500, 750, 1000, float("inf")]
    bins_mdd = [-float("inf"), -90, -80, -70, -60, -50, -40, -30, -20, -10, 0]

    labels_duree = [
        "0–50 days",
        "51–100 days",
        "101–200 days",
        "201–300 days",
        "301–500 days",
        "501–750 days",
        "751–1000 days",
        "> 1000 days"
    ]

    labels_mdd = [
        "< -90%",
        "-90% to -80%",
        "-80% to -70%",
        "-70% to -60%",
        "-60% to -50%",
        "-50% to -40%",
        "-40% to -30%",
        "-30% to -20%",
        "-20% to -10%",
        "-10% to 0%"
    ]

    freq_return=pd.cut(df_trades["Return"]*100,bins=bins_return).value_counts().sort_index()
    freq_duree=pd.cut(df_trades["Holding Period (Days)"],bins=bins_duree).value_counts().sort_index()
    freq_mdd=pd.cut(df_trades["Maximum Drawdown"],bins=bins_mdd,labels=labels_mdd).value_counts().sort_index()
    pourcentages_mdd= freq_mdd / freq_mdd.sum() * 100

    fig_return.add_pie(
        values=freq_return,
        labels=labels_return,
        textinfo="percent",
        hoverinfo="label",
        hoverlabel=dict(bgcolor="black",font_color="white"),
        sort=False,
        marker=dict(colors=colors_return)
    )

    fig_return.update_layout(title="Distribution of Trade Returns")

    fig_duree.add_pie(
        values=freq_duree,
        labels=labels_duree,
        textinfo="percent",
        hoverinfo="label",
        hoverlabel=dict(bgcolor="black",font_color="white"),
        sort=False,
    )
    
    fig_duree.update_layout(title="Distribution of Trade Holding Periods")

    fig_mdd.add_bar(
        x=pourcentages_mdd.index,
        y=pourcentages_mdd.values,    
        text=pourcentages_mdd.values,
        texttemplate="%{text:.1f}%",
        textposition="outside",
        hoverinfo="x+y"
    )

    fig_mdd.update_layout(title="Distribution of Maximum Drawdowns")

    return {
        "return":fig_return,
        "duree":fig_duree,
        "mdd":fig_mdd
    }

def camembert_return(df_trades):
    df = df_trades.copy()
    returns_pct = pd.to_numeric(df["Return"], errors="coerce") * 100

    bins = [-float("inf"), -50, -25, -10, 0, 10, 25, 50, 100, 200, 500, float("inf")]
    labels = [
        "< -50%",
        "-50% to -25%",
        "-25% to -10%",
        "-10% to 0%",
        "0% to 10%",
        "10% to 25%",
        "25% to 50%",
        "50% to 100%",
        "100% to 200%",
        "200% to 500%",
        "> 500%"
    ]

    return_classes = pd.cut(returns_pct, bins=bins, labels=labels, include_lowest=True)
    frequencies = return_classes.value_counts().sort_index()
    frequencies = frequencies[frequencies > 0]

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.pie(frequencies, labels=frequencies.index, autopct="%1.1f%%", startangle=90)
    ax.set_title("Distribution of Trade Returns")
    fig.tight_layout()

    return fig


def camembert_mdd(df_trades):
    df = df_trades.copy()
    mdd_pct = pd.to_numeric(df["Maximum Drawdown"], errors="coerce")

    bins = [-float("inf"), -90, -80, -70, -60, -50, -40, -30, -20, -10, 0]
    labels = [
        "< -90%",
        "-90% to -80%",
        "-80% to -70%",
        "-70% to -60%",
        "-60% to -50%",
        "-50% to -40%",
        "-40% to -30%",
        "-30% to -20%",
        "-20% to -10%",
        "-10% to 0%"
    ]

    mdd_classes = pd.cut(mdd_pct, bins=bins, labels=labels, include_lowest=True)
    frequencies = mdd_classes.value_counts().sort_index()
    frequencies = frequencies[frequencies > 0]

    frequencies_df = frequencies.rename("Count").reset_index()
    frequencies_df.columns = ["Maximum Drawdown Range", "Count"]
    frequencies_df["Frequency"] = frequencies_df["Count"] / frequencies_df["Count"].sum()

    fig, ax = plt.subplots(figsize=(9, 5))
    sns.barplot(data=frequencies_df, x="Maximum Drawdown Range", y="Frequency", ax=ax)

    ax.set_title("Distribution of Trade Maximum Drawdowns")
    ax.set_xlabel("Maximum Drawdown")
    ax.set_ylabel("Share of Trades")
    ax.tick_params(axis="x", rotation=45)

    for bar in ax.patches:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height + 0.005,
            f"{height:.1%}",
            ha="center",
            va="bottom",
            fontsize=8
        )

    fig.tight_layout()
    return fig


def camembert_duree(df_trades):
    df = df_trades.copy()
    duration = pd.to_numeric(df["Holding Period (Days)"], errors="coerce")

    bins = [0, 50, 100, 200, 300, 500, 750, 1000, float("inf")]
    labels = [
        "0–50 days",
        "51–100 days",
        "101–200 days",
        "201–300 days",
        "301–500 days",
        "501–750 days",
        "751–1000 days",
        "> 1000 days"
    ]

    duration_classes = pd.cut(duration, bins=bins, labels=labels, include_lowest=True)
    frequencies = duration_classes.value_counts().sort_index()
    frequencies = frequencies[frequencies > 0]

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.pie(frequencies, labels=frequencies.index, autopct="%1.1f%%", startangle=90)
    ax.set_title("Distribution of Trade Holding Periods")
    fig.tight_layout()

    return fig



def plot_portfolio_stacked(
    portfolio,
    close_for_benchmark,
    title="Évolution du portefeuille (stacked : cash + actif)",
    start=None,
    end=None,
    normalize_from_start=True,     # base 1 si True
    # Visibilité
    show_cash_ratio: bool = True,  # trace taux de cash (0..1) très discret
):
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt

    def _to_1d(x):
        if isinstance(x, pd.DataFrame):
            return x.sum(axis=1) if x.shape[1] > 1 else x.iloc[:, 0]
        return x

    # 1) séries
    total = _to_1d(portfolio.value()).astype(float)
    asset = _to_1d(portfolio.asset_value()).astype(float)
    cash  = _to_1d(portfolio.cash()).astype(float)

    bench_px = close_for_benchmark
    if isinstance(bench_px, pd.DataFrame):
        bench_px = bench_px.iloc[:, 0]
    bench_px = bench_px.astype(float)

    # 2) align + fenêtre
    df = pd.DataFrame({"total": total, "asset": asset, "cash": cash}).dropna(how="all")
    bench_px = bench_px.reindex(df.index).ffill()
    if start or end:
        df = df.loc[start:end]
        bench_px = bench_px.loc[df.index]
    if len(df) == 0:
        raise ValueError("Aucune donnée à tracer sur la fenêtre demandée.")

    # 3) base 1 si normalisé
    if normalize_from_start:
        base = 1.0
        bench = bench_px / bench_px.iloc[0] * base
        scale = base / df.iloc[0]["total"]
        df = df * scale
    else:
        init_total = float(df.iloc[0]["total"])
        bench = bench_px / bench_px.iloc[0] * init_total

    idx = df.index
    y_cash, y_asset = df["cash"].values, df["asset"].values

    # 4) plot principal
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.stackplot(idx, y_cash, y_asset, labels=["Cash", "Actif"], alpha=0.28)   # un peu plus transparent
    ax.plot(idx, df["total"], label="Portefeuille total", linewidth=2.2, color="tab:green")
    ax.plot(idx, bench, label="Benchmark (buy&hold)", linestyle="--", linewidth=1.8, color="crimson")  # plus prononcé

    ax.set_title(title)
    ax.set_xlabel("Date")
    ax.set_ylabel("Valeur (base 1)" if normalize_from_start else "Valeur")
    ax.grid(True, alpha=0.25)

    # 5) taux de cash (0..1) ultra discret sur axe droit
    if show_cash_ratio:
        safe_total = np.where(df["total"].values <= 1e-12, np.nan, df["total"].values)
        cash_ratio = (df["cash"].values / safe_total)  # 0..1
        cash_ratio = pd.Series(cash_ratio, index=idx).clip(lower=0, upper=1)

        ax2 = ax.twinx()
        ax2.set_ylim(0, 1)
        ax2.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
        ax2.set_yticklabels(["0", "0.25", "0.5", "0.75", "1"])
        ax2.set_ylabel("Taux de cash (0–1)", color="#888888", alpha=0.6)

        # très discret : ligne fine, gris clair, alpha faible, pas de marqueurs/labels
        ax2.step(idx, cash_ratio, where="post", linewidth=1.0, color="blue", alpha=0.18, label="_cashratio")

    ax.legend(loc="upper left")
    fig.tight_layout()
    plt.show()

def plot_signaux_vente_avec_ordres(
    df_close_others,
    params,
    orders_df,                          # vbt.Portfolio.orders.records_readable
    start: str | None = None,
    annotate_fontsize: int = 9,
    alpha_red: float = 0.18,
    alpha_blue: float = 0.18,
    show_all_markers: bool = True,
    show_sell_stems: bool = True,       # tiges verticales pour ventes
    stem_scale_sell: float = 0.10,      # hauteur ~ % du prix
    show_buy_stems: bool = True,        # tiges verticales pour achats
    stem_scale_buy: float = 0.08,
):
    """
    Diagnostics signaux de vente (2/3, 3/3) + overlay ordres VENTE **et** ACHAT.

    - Zones: rouge (3/3), bleu (2/3)
    - Points VENTES:
        • rouge si la bougie est 3/3
        • bleu  si la bougie est 2/3
        • gris  sinon
    - Points ACHATS: vert
    Colonnes attendues (souples): 'Timestamp', 'Side' ('Buy'/'Sell'), 'Price', 'Size'.
    """
    import pandas as pd
    import matplotlib.pyplot as plt

    # --- normalisation mono-colonne ---
    if isinstance(df_close_others, pd.Series):
        full_px = df_close_others.dropna().to_frame(name="OTHERS")
    else:
        if df_close_others.shape[1] != 1:
            raise ValueError("df_close_others doit avoir exactement 1 colonne.")
        full_px = df_close_others.dropna().copy()
        if full_px.columns[0] is None:
            full_px.columns = ["OTHERS"]
    asset = full_px.columns[0]

    # --- indicateurs sur l'historique complet ---
    df_volat = volat_glissante_prix_quantiles_vectoriel(
        full_px,
        params["params_volat_vente"]["fenetre_glissante_nb_jours_volat_vente"],
        params["params_volat_vente"]["fenetre_quantile_volat_vente"],
        params["params_volat_vente"]["quantile_haut_volat_vente"],
        params["params_volat_vente"]["quantile_bas"],
    )
    df_rsi = rsi_avec_quantiles_vectoriel(
        full_px,
        params["params_rsi"]["length"],
        params["params_rsi"]["nb_annees_quantile_rsi"],
        params["params_rsi"]["quantile_haut_rsi"],
        params["params_rsi"]["quantile_bas"],
        params["params_rsi"]["quantile_intermediaire"],
    )
    df_roi = roi_avec_quantile_vectoriel(
        full_px,
        params["params_roi"]["periode_roi_en_jours"],
        params["params_roi"]["quantile_haut_roi"],
        params["params_roi"]["quantile_bas"],
        params["params_roi"]["quantile_bas_prix_achat"],
        params["params_roi"]["quantile_haut_prix_achat"],
        params["params_roi"]["nb_annees_quantile_roi"],
    )

    # --- conditions booléennes alignées ---
    c_vol_full = (
        df_volat.xs("std_glissante_prix", level=1, axis=1)[asset]
        > df_volat.xs("quantile_bas_glissant_std", level=1, axis=1)[asset]
    ).reindex(full_px.index).fillna(False)

    c_rsi_full = (
        df_rsi.xs("rsi", level=1, axis=1)[asset]
        > df_rsi.xs("quantile_haut_glissant_rsi", level=1, axis=1)[asset]
    ).reindex(full_px.index).fillna(False)

    c_roi_full = (
        df_roi.xs("roi_hausse", level=1, axis=1)[asset]
        > df_roi.xs("quantile_haut_glissant_roi", level=1, axis=1)[asset]
    ).reindex(full_px.index).fillna(False)

    strength_full = c_vol_full.astype(int) + c_rsi_full.astype(int) + c_roi_full.astype(int)
    cond3_full = strength_full.eq(3)
    cond2_full = strength_full.eq(2)

    # --- tronquage visuel ---
    if start is not None:
        px = full_px.loc[full_px.index >= pd.to_datetime(start)]
        c_vol  = c_vol_full.loc[px.index]
        c_rsi  = c_rsi_full.loc[px.index]
        c_roi  = c_roi_full.loc[px.index]
        cond3  = cond3_full.loc[px.index]
        cond2  = cond2_full.loc[px.index]
    else:
        px    = full_px.copy()
        c_vol = c_vol_full.copy()
        c_rsi = c_rsi_full.copy()
        c_roi = c_roi_full.copy()
        cond3 = cond3_full.copy()
        cond2 = cond2_full.copy()

    def _true_segments(s_bool: pd.Series):
        s = s_bool.fillna(False)
        if s.empty:
            return []
        grp = (s != s.shift()).cumsum()
        out = []
        for _, block in s.groupby(grp):
            if block.iloc[0]:
                out.append((block.index[0], block.index[-1], block.index))
        return out

    # --- plot base ---
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(px.index, px[asset].values, linewidth=2)
    ax.set_title("Diagnostics ventes — OTHERS (signaux + ordres)")
    ax.grid(True)

    # Zones 3/3
    for t0, t1, idx_slice in _true_segments(cond3):
        ax.axvspan(t0, t1, color="red", alpha=alpha_red)
        y_seg_max = px.loc[idx_slice, asset].max()
        y_text = float(y_seg_max) * 1.02
        x_mid = idx_slice[int(len(idx_slice) / 2)]
        ax.text(x_mid, y_text, "ALL", ha="center", va="bottom", fontsize=annotate_fontsize)
        ax.hlines(y_text * 0.999, xmin=t0, xmax=t1, linewidth=1)

    # Zones 2/3
    for t0, t1, idx_slice in _true_segments(cond2):
        ax.axvspan(t0, t1, color="blue", alpha=alpha_blue)
        miss = []
        if not bool(c_vol.loc[idx_slice[0]]): miss.append("vol")
        if not bool(c_rsi.loc[idx_slice[0]]): miss.append("rsi")
        if not bool(c_roi.loc[idx_slice[0]]): miss.append("roi")
        label = "/".join(miss) if miss else "?"
        y_seg_max = px.loc[idx_slice, asset].max()
        y_text = float(y_seg_max) * 1.02
        x_mid = idx_slice[int(len(idx_slice) / 2)]
        ax.text(x_mid, y_text, label, ha="center", va="bottom", fontsize=annotate_fontsize)

    if show_all_markers:
        all_dates = px.index[cond3]
        ax.vlines(all_dates, ymin=px[asset].min()*0.98, ymax=px[asset].max()*1.005, linewidth=0.5, alpha=0.3)

    # ===== Overlay des ordres (VENTES + ACHATS) =====
    if orders_df is not None and len(orders_df) > 0:
        df_ord = orders_df.copy()

        # Normalisation colonnes
        ts_col = "Timestamp" if "Timestamp" in df_ord.columns else ("Entry Timestamp" if "Entry Timestamp" in df_ord.columns else None)
        if ts_col is None:
            raise ValueError("orders_df doit contenir 'Timestamp' ou 'Entry Timestamp'.")
        if "Side" not in df_ord.columns:
            # fallback via Size signée
            if "Size" not in df_ord.columns:
                raise ValueError("orders_df doit contenir 'Side' ou une colonne 'Size' signée.")
            df_ord["Side"] = df_ord["Size"].apply(lambda x: "Sell" if float(x) < 0 else "Buy")

        df_ord[ts_col] = pd.to_datetime(df_ord[ts_col])
        df_ord = df_ord.set_index(ts_col).sort_index()
        df_ord = df_ord.loc[df_ord.index.intersection(px.index)]

        # Split buy / sell
        df_sell = df_ord[df_ord["Side"].str.lower() == "sell"].copy()
        df_buy  = df_ord[df_ord["Side"].str.lower() == "buy"].copy()

        # Helper prix
        def _yvals(df_sub):
            if len(df_sub) == 0:
                return df_sub.index.to_series().rename("y").astype(float)  # empty
            if "Price" in df_sub.columns:
                return df_sub["Price"].astype(float)
            # fallback au close
            return px.reindex(df_sub.index)[asset]

        # --- SELLs ---
        if len(df_sell) > 0:
            y_sell = _yvals(df_sell)
            is3 = cond3.reindex(df_sell.index).fillna(False).astype(bool)
            is2 = cond2.reindex(df_sell.index).fillna(False).astype(bool)
            isOther = ~(is3 | is2)

            ax.scatter(df_sell.index[is3], y_sell[is3], marker="v", s=36, label="Sell 3/3",  zorder=5, color="red")
            ax.scatter(df_sell.index[is2], y_sell[is2], marker="v", s=36, label="Sell 2/3",  zorder=5, color="blue")
            ax.scatter(df_sell.index[isOther], y_sell[isOther], marker="v", s=36, label="Sell autre", zorder=5, color="gray")

            if show_sell_stems:
                for t, y in y_sell.items():
                    if pd.isna(y): 
                        continue
                    h = y * stem_scale_sell
                    ax.vlines(t, y - h, y, linewidth=1.0, color="black", alpha=0.4)

        # --- BUYs ---
        if len(df_buy) > 0:
            y_buy = _yvals(df_buy)
            ax.scatter(df_buy.index, y_buy, marker="^", s=36, label="Buy", zorder=5, color="green")
            if show_buy_stems:
                for t, y in y_buy.items():
                    if pd.isna(y):
                        continue
                    h = y * stem_scale_buy
                    ax.vlines(t, y, y + h, linewidth=1.0, color="green", alpha=0.35)

        ax.legend(loc="best", fontsize=9)

    plt.tight_layout()
    plt.show()

def plot_signaux_vente_v3_simple(
    df_close_1col,
    params,
    orders_df=None,
    start=None,
    end=None,
    alpha_A=0.22,   # zones A (RSI+ROI1) en rouge
    alpha_B=0.18,   # zones B (ROI2 seul) en bleu
    show_stems=False,
):
    import pandas as pd
    import matplotlib.pyplot as plt

    # --- normalisation mono-colonne ---
    if isinstance(df_close_1col, pd.Series):
        full_px = df_close_1col.dropna().to_frame(name="ASSET")
    else:
        if df_close_1col.shape[1] != 1:
            raise ValueError("df_close_1col doit avoir exactement 1 colonne.")
        full_px = df_close_1col.dropna().copy()
        if full_px.columns[0] is None:
            full_px.columns = ["ASSET"]
    asset = full_px.columns[0]

    # --- params robustes ---
    p = ensure_params_v3(params)

    # --- masques de signaux ---
    sigs = signaux_vente_v3_decomposee(
        full_px,
        params_rsi=p["params_rsi"],
        params_roi_1=p["params_roi_1"],
        params_roi_2=p["params_roi_2"],
    )
    A_df = sigs["mask_A"].reindex(full_px.index).fillna(False)
    B_df = sigs["mask_B"].reindex(full_px.index).fillna(False)

    # Series 1D
    A = A_df[asset].astype(bool)                # RSI+ROI1
    B = B_df[asset].astype(bool) & (~A)         # ROI2 seul (exclure les jours A)

    # fenêtre
    idx = full_px.index
    left = pd.to_datetime(start) if start else idx[0]
    right = pd.to_datetime(end) if end else idx[-1]
    px = full_px.loc[left:right]
    A = A.loc[px.index]
    B = B.loc[px.index]

    # util: segments True consécutifs
    def _segments(s_bool: pd.Series):
        s = s_bool.fillna(False)
        if s.empty: return []
        grp = (s != s.shift()).cumsum()
        out = []
        for _, block in s.groupby(grp):
            if block.iloc[0]:
                out.append((block.index[0], block.index[-1], block.index))
        return out

    # plot
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(px.index, px[asset].values, linewidth=2, label="Prix")
    ax.set_title("Diagnostics ventes — OTHERS (signaux + ordres)")
    ax.grid(True)

    # zones A (rouge) et B (bleu)
    for t0, t1, _ in _segments(A):
        ax.axvspan(t0, t1, color="red", alpha=alpha_A)
    for t0, t1, _ in _segments(B):
        ax.axvspan(t0, t1, color="blue", alpha=alpha_B)

    # --- overlay ordres (facultatif) ---
    if orders_df is not None and len(orders_df) > 0:
        df_ord = orders_df.copy()

        # colonnes robustes
        ts_col = ("Timestamp" if "Timestamp" in df_ord.columns
                  else ("Entry Timestamp" if "Entry Timestamp" in df_ord.columns else None))
        if ts_col is None:
            raise ValueError("orders_df doit contenir 'Timestamp' ou 'Entry Timestamp'.")

        if "Side" not in df_ord.columns:
            if "Size" not in df_ord.columns:
                raise ValueError("orders_df doit contenir 'Side' ou une colonne 'Size'.")
            df_ord["Side"] = df_ord["Size"].apply(lambda x: "Sell" if float(x) < 0 else "Buy")

        df_ord[ts_col] = pd.to_datetime(df_ord[ts_col])
        df_ord = df_ord.set_index(ts_col).sort_index()
        df_ord = df_ord.loc[df_ord.index.intersection(px.index)]

        df_sell = df_ord[df_ord["Side"].str.lower() == "sell"].copy()
        df_buy  = df_ord[df_ord["Side"].str.lower() == "buy"].copy()

        def _yvals(df_sub):
            if len(df_sub) == 0: return pd.Series(dtype=float)
            if "Price" in df_sub.columns: return df_sub["Price"].astype(float)
            return px.reindex(df_sub.index)[asset].astype(float)

        # ventes : rouge si date ∈ A, bleu si date ∈ B, sinon gris
        if len(df_sell) > 0:
            y_sell = _yvals(df_sell)
            isA = A.reindex(df_sell.index).fillna(False).astype(bool)
            isB = B.reindex(df_sell.index).fillna(False).astype(bool)
            isOther = ~(isA | isB)

            ax.scatter(df_sell.index[isA], y_sell[isA], marker="v", s=40, color="red",  label="Sell A (RSI+ROI1)", zorder=5)
            ax.scatter(df_sell.index[isB], y_sell[isB], marker="v", s=40, color="blue", label="Sell B (ROI2)",     zorder=5)
            ax.scatter(df_sell.index[isOther], y_sell[isOther], marker="v", s=36, color="gray", label="Sell autre", zorder=5)

            if show_stems:
                for t, y in y_sell.items():
                    if pd.isna(y): continue
                    ax.vlines(t, y*0.90, y, linewidth=1.0, color="black", alpha=0.35)

        # achats : vert
        if len(df_buy) > 0:
            y_buy = _yvals(df_buy)
            ax.scatter(df_buy.index, y_buy, marker="^", s=38, color="green", label="Buy", zorder=5)
            if show_stems:
                for t, y in y_buy.items():
                    if pd.isna(y): continue
                    ax.vlines(t, y, y*1.08, linewidth=1.0, color="green", alpha=0.30)

    # légende propre
    handles, labels = ax.get_legend_handles_labels()
    # dédupliquer en gardant l'ordre
    seen, h2, l2 = set(), [], []
    for h, l in zip(handles, labels):
        if l not in seen:
            h2.append(h); l2.append(l); seen.add(l)
    ax.legend(h2, l2, loc="best", fontsize=9)

    plt.tight_layout()
    plt.show()


def analyse_portfolio_simple(
    portfolio,
    df_close,
    afficher_df_trades=True,
    retirer_trades_non_closed=False,
    afficher_stats=True,
    afficher_indice_composite=True,
    camemberts=True,
    pondes=None,
    retourner_df_trades=False
):
    """
    Analyse un portefeuille vectorbt : calcule les stats, affiche les graphiques et résume les résultats.

    Parameters:
        portfolio (vbt.Portfolio) : portefeuille généré par vectorbt
        afficher_df_trades (bool) : afficher le DataFrame des trades fermés
        afficher_stats (bool) : afficher les statistiques globales
        afficher_indice_composite (bool) : afficher l'indice composite pondéré
        camemberts (bool) : afficher les graphiques camemberts (durée, return, MDD)
        pondes (dict) : dictionnaire de pondération pour l'indice composite
    Returns:
        pd.DataFrame : DataFrame des trades fermés enrichis
    """

    if pondes is None:
        pondes = {
            "pnl": 0.50,
            "win_rate": 0.15,
            "mdd": 0.1,
            "occurence": 0.2,
            "part_fermes": 0.05,
        }

    # 1. Extraction des trades fermés
    df_trades = portfolio.trades.records_readable.copy()
    
    if retirer_trades_non_closed:
        df_trades = df_trades[df_trades["Status"] == "Closed"].copy()

    # 2. Calcul du MDD par trade

    df_trades = mdd_df_trades(df_trades, df_close)

    # 3. Infos supplémentaires
    df_trades["nb_tokens_total"] = len(portfolio.wrapper.columns)
    df_trades["duree_jours"] = (df_trades["Exit Timestamp"] - df_trades["Entry Timestamp"]).dt.total_seconds() / (3600 * 24)

    if afficher_df_trades:
        display(df_trades)

    if afficher_indice_composite:
        print("\nIndice composite :")
        pprint(indice_composite(df_trades, pondes=pondes))

    if afficher_stats:
        nb_tokens = df_trades.iloc[0]["nb_tokens_total"]
        stats = stats_trades(df_trades, nb_tokens)
        print("\nStatistiques :")
        pprint(stats)

    if camemberts:
        camembert_duree(df_trades)
        camembert_return(df_trades)
        camembert_mdd(df_trades)
    
    if retourner_df_trades:
        return df_trades
