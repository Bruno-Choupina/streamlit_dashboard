import pandas as pd
import numpy as np
import optuna
import vectorbt as vbt
from IPython.display import display
from pprint import pprint

from utils.QIS.crypto.signals import (
    signaux_achats,
    signaux_vente,
)

from utils.QIS.crypto.backtesting import (
    backtest,
    portfolio_fractionne,
    portfolio_fractionne_v2,
    portfolio_fractionne_v3,
    mdd_df_trades,
)

from utils.QIS.crypto.analysis import (
    indice_composite_v0,
    stats_trades,
    camembert_duree,
    camembert_return,
    camembert_mdd,
)

from utils.QIS.crypto.params import (
    ensure_params_v3,
    recup_params_depuis_moyenne_trials,
    recup_params_depuis_params_trial,
    recup_params_depuis_moyenne_trials_fractionne,
    recup_params_v2_depuis_study,
    recup_params_v3_depuis_study,
)

def fonction_objectif_v0(
    df_close,
    params,
    params_optimisation
):
    """
    Génère les signaux, effectue le backtest et retourne
    l'indice composite utilisé par Optuna.
    """

    # 1. Génération des signaux
    df_signaux_achats = signaux_achats(
        df_close,
        params_volat_achat=params["params_volat_achat"],
        params_ecart_relatif=params["params_ecart_relatif"],
        critere_rsi=params["critère_rsi_achat"]
    )

    df_signaux_vente = signaux_vente(
        df_close,
        params["params_volat_vente"],
        params["params_rsi"],
        params["params_roi"]
    )

    # 2. Backtest VectorBT
    portfolio = vbt.Portfolio.from_signals(
        close=df_close,
        entries=df_signaux_achats,
        exits=df_signaux_vente,
        init_cash=100,
        fees=0.001,
        freq="1d"
    )

    # 3. Extraction des trades
    trades = portfolio.trades.records_readable.copy()

    if trades.empty:
        raise optuna.TrialPruned("Aucun trade généré.")

    trades = mdd_df_trades(
        trades,
        df_close
    )

    trades_closed = trades.loc[
        trades["Status"] == "Closed"
    ].copy()
    #trades_closed["Maximum Drawdown"]=

    if trades_closed.empty:
        raise optuna.TrialPruned("Aucun trade fermé.")

    # 4. Couverture de l'univers
    nb_tokens_total = len(portfolio.wrapper.columns)
    nb_tokens_traded = trades_closed["Column"].nunique()

    universe_coverage = (
        nb_tokens_traded / nb_tokens_total
        if nb_tokens_total > 0
        else 0
    )

    couverture_min = params_optimisation[
        "contraintes"
    ]["couverture_min"]

    if universe_coverage < couverture_min:
        raise optuna.TrialPruned(
            f"Universe coverage trop faible : "
            f"{universe_coverage:.1%} < {couverture_min:.1%}"
        )

    # 5. Indice composite
    score = indice_composite_v0(
        trades=trades,
        params_optimisation=params_optimisation
    )

    return score["indice"]

def optimisation_optuna_v0(df_close, params_optimisation):
    
    def optimisation(trial):

        params_test = {
            "params_volat_achat": {
                "fenetre_glissante_nb_jours_volat_achat": trial.suggest_int("fenetre_glissante_nb_jours_volat_achat", 30, 120),
                "fenetre_quantile_volat_achat": trial.suggest_int("fenetre_quantile_volat_achat", 500, 1300),
                "quantile_haut": 0.9,
                "quantile_bas_volat_achat": trial.suggest_float("quantile_bas_volat_achat", 0.05, 0.25)
            },
            "params_ecart_relatif": {
                "nb_jours_arriere_ecart_relatif": trial.suggest_int("nb_jours_arriere_ecart_relatif", 60, 300),
                "nb_jour_mm_ecart_relatif": trial.suggest_int("nb_jour_mm_ecart_relatif", 20, 75),
                "nb_jour_quantiles_ecart_relatif": trial.suggest_int("nb_jour_quantiles_ecart_relatif", 500, 1300),
                "quantile_haut": 0.9,
                "quantile_bas_ecart_relatif": trial.suggest_float("quantile_bas_ecart_relatif", 0.05, 0.25)
            },
            "params_volat_vente": {
                "fenetre_glissante_nb_jours_volat_vente": trial.suggest_int("fenetre_glissante_nb_jours_volat_vente", 30, 120),
                "fenetre_quantile_volat_vente": trial.suggest_int("fenetre_quantile_volat_vente", 500, 1500),
                "quantile_haut_volat_vente": trial.suggest_float("quantile_haut_volat_vente", 0.75, 0.965),
                "quantile_bas": 0.1
            },
            "params_roi": {
                "periode_roi_en_jours": trial.suggest_int("periode_roi_en_jours", 30, 365),
                "quantile_haut_roi": trial.suggest_float("quantile_haut_roi", 0.75, 0.95),
                "quantile_bas": 0.05,
                "quantile_bas_prix_achat": 0.05,
                "quantile_haut_prix_achat": 0.95,
                "nb_annees_quantile_roi": trial.suggest_float("nb_annees_quantile_roi", 1.5, 4)
            },
            "params_rsi": {
                "length": 14,
                "nb_annees_quantile_rsi": trial.suggest_float("nb_annees_quantile_rsi", 1.5, 4),
                "quantile_haut_rsi": trial.suggest_float("quantile_haut_rsi", 0.75, 0.95),
                "quantile_bas": 0.1,
                "quantile_intermediaire": 0.5
            },
            "critère_rsi_achat": trial.suggest_int("critère_rsi_achat", 35, 60)
        }

        return fonction_objectif_v0(
            df_close=df_close,
            params=params_test,
            params_optimisation=params_optimisation
        )

    return optimisation

def optimisation_optuna(df_close):
    
    def optimisation(trial):

        params_test={
        "params_volat_achat":{
            "fenetre_glissante_nb_jours_volat_achat":trial.suggest_int("fenetre_glissante_nb_jours_volat_achat",30,120),
            "fenetre_quantile_volat_achat":trial.suggest_int("fenetre_quantile_volat_achat",500,1300),
            "quantile_haut":0.9,
            "quantile_bas_volat_achat":trial.suggest_float("quantile_bas_volat_achat",0.05,0.25)
        },
        "params_ecart_relatif":{
            "nb_jours_arriere_ecart_relatif":trial.suggest_int("nb_jours_arriere_ecart_relatif",60,300),
            "nb_jour_mm_ecart_relatif":trial.suggest_int("nb_jour_mm_ecart_relatif",20,75),
            "nb_jour_quantiles_ecart_relatif":trial.suggest_int("nb_jour_quantiles_ecart_relatif",500,1300),
            "quantile_haut":0.9,
            "quantile_bas_ecart_relatif":trial.suggest_float("quantile_bas_ecart_relatif",0.05,0.25)
        },
        "params_volat_vente":{
            
            "fenetre_glissante_nb_jours_volat_vente":trial.suggest_int("fenetre_glissante_nb_jours_volat_vente",30,120),
            "fenetre_quantile_volat_vente":trial.suggest_int("fenetre_quantile_volat_vente",500,1500),
            "quantile_haut_volat_vente":trial.suggest_float("quantile_haut_volat_vente",0.75,0.965),
            "quantile_bas":0.1
        },
        "params_roi":{
            "periode_roi_en_jours":trial.suggest_int("periode_roi_en_jours",30,365),
            "quantile_haut_roi":trial.suggest_float("quantile_haut_roi",0.75,0.95),
            "quantile_bas":0.05,
            "quantile_bas_prix_achat":0.05,
            "quantile_haut_prix_achat":0.95,
            "nb_annees_quantile_roi":trial.suggest_float("nb_annees_quantile_roi",1.5,4)
        },
        "params_rsi":{
            "length":14,
            "nb_annees_quantile_rsi":trial.suggest_float("nb_annees_quantile_rsi",1.5,4),
            "quantile_haut_rsi":trial.suggest_float("quantile_haut_rsi",0.75,0.95),
            "quantile_bas":0.1,
            "quantile_intermediaire":0.5
        },
        "critère_rsi_achat":trial.suggest_int("critère_rsi_achat",35,60)
        }
        
        pondes={
        "pnl":0.50,
        "win_rate":0.15,
        "mdd":0.1,
        "occurence":0.2,
        "part_fermes":0.05,
        }


        score = fonction_objectif(df_close,params=params_test,pondes=pondes)
        return score

    return optimisation


def fonction_objectif_monotoken(df_close, params):
    """
    Objectif pour un seul actif : maximiser la valeur finale du portefeuille.
    Contrainte : au moins 2 trades fermés + durée moyenne < 900 jours.
    """

    df_signaux_achats = signaux_achats(
        df_close,
        params_volat_achat=params["params_volat_achat"],
        params_ecart_relatif=params["params_ecart_relatif"],
        critere_rsi=params["critère_rsi_achat"]
    )

    df_signaux_vente = signaux_vente(
        df_close,
        params["params_volat_vente"],
        params["params_rsi"],
        params["params_roi"]
    )

    portfolio = vbt.Portfolio.from_signals(
        close=df_close,
        entries=df_signaux_achats,
        exits=df_signaux_vente,
        freq="1w",
        init_cash=1000
    )

    trades = portfolio.trades.records_readable
    trades_closed = trades[trades["Status"] == "Closed"]

    nb_closed = len(trades_closed)
    trades_closed["duree_jours"] = (trades_closed["Exit Timestamp"] - trades_closed["Entry Timestamp"]).dt.days
    duree_moyenne = trades_closed["duree_jours"].mean()
    #print(f"{nb_closed} trades fermés, durée moyenne = {duree_moyenne:.1f} jours")



    # ⚠️ Contrainte : au moins 2 trades fermés
    if nb_closed < 2:
        raise optuna.TrialPruned("Trop peu de trades fermés")

    if duree_moyenne > 1000:
        raise optuna.TrialPruned("Durée moyenne des trades trop longue (> 1000 jours)")

    # ✅ Score = valeur finale du portefeuille
    valeur_finale = portfolio.value().iloc[-1]

    return valeur_finale


def optimisation_optuna_monotoken(df_close):
    
    def optimisation_monotoken(trial):

        params_test = {
            "params_volat_achat": {
                "fenetre_glissante_nb_jours_volat_achat": trial.suggest_int("fenetre_glissante_nb_jours_volat_achat", 30, 120),
                "fenetre_quantile_volat_achat": trial.suggest_int("fenetre_quantile_volat_achat", 500, 1300),
                "quantile_haut": 0.9,
                "quantile_bas_volat_achat": trial.suggest_float("quantile_bas_volat_achat", 0.05, 0.25)
            },
            "params_ecart_relatif": {
                "nb_jours_arriere_ecart_relatif": trial.suggest_int("nb_jours_arriere_ecart_relatif", 60, 300),
                "nb_jour_mm_ecart_relatif": trial.suggest_int("nb_jour_mm_ecart_relatif", 20, 75),
                "nb_jour_quantiles_ecart_relatif": trial.suggest_int("nb_jour_quantiles_ecart_relatif", 500, 1300),
                "quantile_haut": 0.9,
                "quantile_bas_ecart_relatif": trial.suggest_float("quantile_bas_ecart_relatif", 0.05, 0.25)
            },
            "params_volat_vente": {
                "fenetre_glissante_nb_jours_volat_vente": trial.suggest_int("fenetre_glissante_nb_jours_volat_vente", 30, 120),
                "fenetre_quantile_volat_vente": trial.suggest_int("fenetre_quantile_volat_vente", 500, 1500),
                "quantile_haut_volat_vente": trial.suggest_float("quantile_haut_volat_vente", 0.75, 0.965),
                "quantile_bas": 0.1
            },
            "params_roi": {
                "periode_roi_en_jours": trial.suggest_int("periode_roi_en_jours", 30, 365),
                "quantile_haut_roi": trial.suggest_float("quantile_haut_roi", 0.75, 0.95),
                "quantile_bas": 0.05,
                "quantile_bas_prix_achat": 0.05,
                "quantile_haut_prix_achat": 0.95,
                "nb_annees_quantile_roi": trial.suggest_float("nb_annees_quantile_roi", 1.5, 4)
            },
            "params_rsi": {
                "length": 14,
                "nb_annees_quantile_rsi": trial.suggest_float("nb_annees_quantile_rsi", 1.5, 4),
                "quantile_haut_rsi": trial.suggest_float("quantile_haut_rsi", 0.75, 0.95),
                "quantile_bas": 0.1,
                "quantile_intermediaire": 0.5
            },
            "critère_rsi_achat": trial.suggest_int("critère_rsi_achat", 35, 60)
        }

        # Lancement de l'objectif
        score = fonction_objectif_monotoken(df_close, params_test)
        return score

    return optimisation_monotoken



def fonction_objectif_monotoken_fractionne(
    df_close,
    params,
    buy_cash_frac: float = 0.20,   # % du cash ancré dépensé par ACHAT (budget TTC fixe)
    sell_pos_frac: float = 0.20,   # % des unités vendues à CHAQUE signal (optimisé)
    frais: float = 0.002,
    min_closed: int = 7,           # nb MIN de ventes exécutées
    use_realized: bool = True,     # True => score sur P&L réalisé ; False => latent
    pnl_method: str = "avgcost",   # "avgcost" (PRU) ou "fifo"
):
    ###
    # Cette fonction prend un DataFrame de clôtures mono-token et un dictionnaire de paramètres
    # issus de l’optimisation. Elle génère d’abord les signaux d’achat à partir de l’écart
    # relatif, du RSI et de la volatilité glissante sur le prix, puis les signaux de vente
    # exclusivement à partir du RSI, d’un ROI glissant et de la volatilité glissante.
    # À l’exécution, chaque achat dépense un ticket TTC fixe égal à :
    # buy_cash_frac × (cash ancré après la dernière vente).
    # Si plusieurs signaux d’achat se présentent d’affilée, ce ticket est répété à chaque signal
    # jusqu’à épuisement du cash disponible.
    # Côté vente, dès qu’un signal apparaît après un achat, on vend une quantité fixe
    # égale à :
    # sell_pos_frac × (unités détenues juste avant le dernier achat).
    # Tant qu’il reste des unités et que de nouveaux signaux de vente surviennent, on revend
    # la même quantité à chaque signal, jusqu’à épuisement des unités.
    # Il n’y a aucune exigence de barres consécutives (streak) ni de délai (cooldown) : on agit
    # dès l’apparition du signal. En cas de coïncidence achat/vente le même jour, on applique
    # l’ordre des phases défini (par défaut “vente” puis “achat”). Les frais sont inclus : côté achat
    # via un prix TTC (1 + fee_rate), côté vente via un encaissement net (1 − fee_rate).
    # En sortie, selon le mode choisi, la fonction renvoie soit le PNL réalisé rapporté à la
    # mise de départ (par exemple via PRU/FIFO), soit le PNL latent défini comme la valeur finale
    # du portefeuille divisée par le cash initial — autrement dit, le multiple/ROI en version
    # réalisée ou latente.
    ###
    
    import pandas as pd
    import optuna

    init_cash = 100_000.0

    # --- Backtest
    pf = portfolio_fractionne(
        df_close=df_close,
        params=params,
        init_cash=init_cash,
        buy_cash_frac=buy_cash_frac,
        sell_pos_frac=sell_pos_frac,
        fee_rate=frais,
        priorite="vente",
        freq="1w",
    )

    # --- Contrainte : nb mini de ventes (mono-actif)
    orders = pf.orders.records_readable.copy()
    orders = orders.sort_values("Timestamp").reset_index(drop=True)
    if "Fees" not in orders.columns:
        orders["Fees"] = 0.0

    nb_ventes = int(((orders["Side"] == "Sell") & (orders["Size"].abs() > 1e-12)).sum())
    if nb_ventes < min_closed:
        raise optuna.TrialPruned(f"Trop peu de ventes exécutées (< {min_closed})")

    # --- Score latent si demandé
    if not use_realized:
        value_last = pf.value().iloc[-1]
        total_last = float(value_last)
        return total_last / init_cash

    # ========== P&L réalisé (mono-actif) ==========
    def realized_pnl_avgcost(df: pd.DataFrame) -> float:
        """PRU dynamique (coût moyen pondéré), frais inclus."""
        qty_pos = 0.0
        avg_cost = 0.0
        realized = 0.0
        for _, r in df.iterrows():
            side = str(r["Side"]).lower()
            q    = float(r["Size"])
            px   = float(r["Price"])
            fee  = float(r["Fees"])
            if q <= 0 or px <= 0:
                continue
            if side == "buy":
                total_cost_before = qty_pos * avg_cost
                total_cost_after  = total_cost_before + (px * q + fee)
                qty_pos += q
                if qty_pos > 0:
                    avg_cost = total_cost_after / qty_pos
            elif side == "sell":
                realized += (px - avg_cost) * q - fee
                qty_pos = max(0.0, qty_pos - q)
                if qty_pos == 0.0:
                    avg_cost = 0.0
        return realized

    def realized_pnl_fifo(df: pd.DataFrame) -> float:
        """Lots FIFO, frais inclus (achats ajoutent au coût, ventes retirent)."""
        fifo = []  # liste de [qty_restante, cost_per_unit]
        realized = 0.0
        for _, r in df.iterrows():
            side = str(r["Side"]).lower()
            q    = float(r["Size"])
            px   = float(r["Price"])
            fee  = float(r["Fees"])
            if q <= 0 or px <= 0:
                continue
            if side == "buy":
                cost_unit = (px * q + fee) / q
                fifo.append([q, cost_unit])
            elif side == "sell":
                sell_unit = (px * q - fee) / q
                remain = q; i = 0
                while remain > 1e-18 and i < len(fifo):
                    lot_q, lot_c = fifo[i]
                    take = min(lot_q, remain)
                    realized += (sell_unit - lot_c) * take
                    lot_q -= take; remain -= take
                    if lot_q <= 1e-18:
                        fifo.pop(i)
                    else:
                        fifo[i][0] = lot_q; i += 1
        return realized

    realized_total = (
        realized_pnl_avgcost(orders) if pnl_method == "avgcost" else realized_pnl_fifo(orders)
    )
    return realized_total / init_cash
def optimisation_optuna_monotoken_fractionne(df_close):
    
    def optimisation_monotoken(trial):

        sell_pos_frac = trial.suggest_float("sell_pos_frac", 0.15, 0.4)  
        buy_cash_frac=trial.suggest_float("buy_cash_frac", 0.05, 0.2)  
        

        params_test = {
            "params_volat_achat": {
                "fenetre_glissante_nb_jours_volat_achat": trial.suggest_int("fenetre_glissante_nb_jours_volat_achat", 30, 120),
                "fenetre_quantile_volat_achat": trial.suggest_int("fenetre_quantile_volat_achat", 500, 1300),
                "quantile_haut": 0.9,
                "quantile_bas_volat_achat": trial.suggest_float("quantile_bas_volat_achat", 0.05, 0.25)
            },
            "params_ecart_relatif": {
                "nb_jours_arriere_ecart_relatif": trial.suggest_int("nb_jours_arriere_ecart_relatif", 60, 300),
                "nb_jour_mm_ecart_relatif": trial.suggest_int("nb_jour_mm_ecart_relatif", 20, 75),
                "nb_jour_quantiles_ecart_relatif": trial.suggest_int("nb_jour_quantiles_ecart_relatif", 500, 1300),
                "quantile_haut": 0.9,
                "quantile_bas_ecart_relatif": trial.suggest_float("quantile_bas_ecart_relatif", 0.05, 0.25)
            },
            "params_volat_vente": {
                "fenetre_glissante_nb_jours_volat_vente": trial.suggest_int("fenetre_glissante_nb_jours_volat_vente", 30, 120),
                "fenetre_quantile_volat_vente": trial.suggest_int("fenetre_quantile_volat_vente", 500, 1500),
                "quantile_haut_volat_vente": trial.suggest_float("quantile_haut_volat_vente", 0.75, 0.965),
                "quantile_bas": 0.1
            },
            "params_roi": {
                "periode_roi_en_jours": trial.suggest_int("periode_roi_en_jours", 30, 365),
                "quantile_haut_roi": trial.suggest_float("quantile_haut_roi", 0.75, 0.95),
                "quantile_bas": 0.05,
                "quantile_bas_prix_achat": 0.05,
                "quantile_haut_prix_achat": 0.95,
                "nb_annees_quantile_roi": trial.suggest_float("nb_annees_quantile_roi", 1.5, 4)
            },
            "params_rsi": {
                "length": 14,
                "nb_annees_quantile_rsi": trial.suggest_float("nb_annees_quantile_rsi", 1.5, 4),
                "quantile_haut_rsi": trial.suggest_float("quantile_haut_rsi", 0.75, 0.95),
                "quantile_bas": 0.1,
                "quantile_intermediaire": 0.5
            },
            "critère_rsi_achat": trial.suggest_int("critère_rsi_achat", 35, 60)
        }

        # Lancement de l'objectif
        score = fonction_objectif_monotoken_fractionne(df_close, params_test,sell_pos_frac=sell_pos_frac,buy_cash_frac=buy_cash_frac,min_closed=0,use_realized=True)
        return score

    return optimisation_monotoken


def fonction_objectif_monotoken_fractionne_v2(
    df_close,
    params,
    pas_fraction_buy: float = 0.20,   # % du cash ancré dépensé par achat
    frais: float = 0.002,
    min_ventes: int = 12,             # nb minimum de ventes totales
    min_ventes_post2023: int = 5,     # nb minimum de ventes depuis 2023-01-01
    priorite: str = "vente",
    eps_size: float = 1e-12,
):
    import pandas as pd
    import optuna

    # ---- Contrainte : % vente 3/3 >= 2 × % vente 2/3 ----
    #if params["sell_pos_frac_3on3"] < 1 * params["sell_pos_frac_2on3"]:
     #   raise optuna.TrialPruned("Ratio 3/3 < 1.5 × 2/3 => prune")

    # ---- Backtest ----
    pf = portfolio_fractionne_v2(
        df_close=df_close,
        params=params,
        init_cash=100000,
        buy_cash_frac=pas_fraction_buy,
        sell_pos_frac_3on3=params["sell_pos_frac_3on3"],
        sell_pos_frac_2on3=params["sell_pos_frac_2on3"],
        x_streak_2on3=int(params["x_streak_2on3"]),
        x_gap_2on3=int(params["x_gap_2on3"]),
        fee_rate=frais,
        priorite=priorite,
        freq="1w",
        min_cash_eps=0.0,
        min_units_eps=0.0,
    )

    # ---- Comptage ventes ----
    orders = pf.orders.records_readable.copy()
    if "Timestamp" not in orders.columns:
        raise RuntimeError("La table des ordres n'a pas de colonne 'Timestamp'.")

    orders["Timestamp"] = pd.to_datetime(orders["Timestamp"])
    ventes_mask = (orders["Side"] == "Sell") & (orders["Size"].abs() > eps_size)

    nb_ventes_total = int(ventes_mask.sum())
    nb_ventes_post2023 = int((ventes_mask & (orders["Timestamp"] >= pd.Timestamp("2023-01-01"))).sum())

    # ---- Prunes sur volume de trades ----
    if nb_ventes_total < min_ventes:
        raise optuna.TrialPruned(f"Trop peu de ventes totales (< {min_ventes})")
    if nb_ventes_post2023 < min_ventes_post2023:
        raise optuna.TrialPruned(f"Trop peu de ventes après 2023 (< {min_ventes_post2023})")

    # ---- Score = valeur finale ----
    value_last = pf.value().iloc[-1]
    score = float(value_last.sum() if hasattr(value_last, "sum") else value_last)

    return score/100000
def optimisation_optuna_monotoken_fractionne_v2(df_close):
    import math
    import numpy as np
    import optuna

    def _objective(trial):
        # --- On génère d'abord le % vente 2/3 ---
        frac2 = trial.suggest_float("sell_pos_frac_2on3", 0.05, 0.15)

        # --- Puis on force le % vente 3/3 >= 2 × frac2 ---
        frac3 = trial.suggest_float("sell_pos_frac_3on3", 0.15, 0.3)

        params_test = {
            "params_volat_achat": {
                "fenetre_glissante_nb_jours_volat_achat": trial.suggest_int("fen_gliss_volat_achat", 30, 120),
                "fenetre_quantile_volat_achat": trial.suggest_int("fen_q_volat_achat", 500, 1300),
                "quantile_haut": 0.90,
                "quantile_bas_volat_achat": trial.suggest_float("q_bas_volat_achat", 0.05, 0.25),
            },
            "params_ecart_relatif": {
                "nb_jours_arriere_ecart_relatif": trial.suggest_int("jours_back_ecart_rel", 60, 300),
                "nb_jour_mm_ecart_relatif": trial.suggest_int("jours_mm_ecart_rel", 20, 75),
                "nb_jour_quantiles_ecart_relatif": trial.suggest_int("jours_q_ecart_rel", 500, 1300),
                "quantile_haut": 0.90,
                "quantile_bas_ecart_relatif": trial.suggest_float("q_bas_ecart_rel", 0.05, 0.25),
            },
            "params_volat_vente": {
                "fenetre_glissante_nb_jours_volat_vente": trial.suggest_int("fen_gliss_volat_vente", 30, 120),
                "fenetre_quantile_volat_vente": trial.suggest_int("fen_q_volat_vente", 500, 1500),
                "quantile_haut_volat_vente": trial.suggest_float("q_haut_volat_vente", 0.75, 0.98),
                "quantile_bas": 0.10,
            },
            "params_roi": {
                "periode_roi_en_jours": trial.suggest_int("periode_roi_j", 30, 365),
                "quantile_haut_roi": trial.suggest_float("q_haut_roi", 0.75, 0.95),
                "quantile_bas": 0.05,
                "quantile_bas_prix_achat": 0.05,
                "quantile_haut_prix_achat": 0.95,
                "nb_annees_quantile_roi": trial.suggest_float("nb_ans_q_roi", 1.5, 4.0),
            },
            "params_rsi": {
                "length": 14,
                "nb_annees_quantile_rsi": trial.suggest_float("nb_ans_q_rsi", 1.5, 4.0),
                "quantile_haut_rsi": trial.suggest_float("q_haut_rsi", 0.75, 0.95),
                "quantile_bas": 0.10,
                "quantile_intermediaire": 0.50,
            },
            "critère_rsi_achat": trial.suggest_int("critere_rsi_achat", 35, 60),

            # Nouveautés à optimiser
            "x_streak_2on3": trial.suggest_int("x_streak_2on3", 1, 6),
            "x_gap_2on3":    trial.suggest_int("x_gap_2on3",    1, 6),

            # Paramètres ventes
            "sell_pos_frac_3on3": frac3,
            "sell_pos_frac_2on3": frac2,
        }

        score = fonction_objectif_monotoken_fractionne_v2(
            df_close=df_close,
            params=params_test,
            min_ventes=0,
            min_ventes_post2023=0,
            priorite="vente",
        )
        return score

    return _objective


def fonction_objectif_monotoken_fractionne_v3(
    df_close,
    params,
    pas_fraction_buy: float = 0.20,
    frais: float = 0.002,
    min_ventes: int = 12,
    min_ventes_post2023: int = 5,
    priorite: str = "vente",
    eps_size: float = 1e-12,
    # --- modes & score ---
    mode: str = "score",     # "score" | "latent" | "realized"
    w_ret: float = 0.5,
    w_mdd: float = 0.5,
    cap_ret: float = 3.0,
    use_realized_pru: bool = True,  # seulement pour mode="realized"
    # --- PRUNING en MULTIPLES ---
    prune_latent_multiple_min: float | None = None,
    prune_realized_multiple_min: float | None = None,
    # --- Compat rétro (%) ---
    prune_latent_gain_pct_min: float | None = None,
    prune_realized_gain_pct_min: float | None = None,
    # --- NOUVEAU: PRUNING MDD ---
    prune_mdd_max: float | None = None,         # ex. 0.50 pour 50%
    prune_mdd_pct_max: float | None = None,     # ex. 50 pour 50%
):
    import optuna
    import pandas as pd

    def _to_series_last(v):
        return v.sum(axis=1) if hasattr(v, "columns") else v
    def _max_drawdown(s: pd.Series) -> float:
        s = pd.Series(s, dtype=float).dropna()
        if s.empty: return 0.0
        cm = s.cummax()
        dd = (s - cm) / cm
        return float(-dd.min())

    # -- back-compat: % -> multiples
    if prune_latent_multiple_min is None and prune_latent_gain_pct_min is not None:
        prune_latent_multiple_min = 1.0 + float(prune_latent_gain_pct_min) / 100.0
    if prune_realized_multiple_min is None and prune_realized_gain_pct_min is not None:
        prune_realized_multiple_min = 1.0 + float(prune_realized_gain_pct_min) / 100.0
    # -- back-compat: % -> fraction pour MDD
    if prune_mdd_max is None and prune_mdd_pct_max is not None:
        prune_mdd_max = float(prune_mdd_pct_max) / 100.0

    # ---- backtest ----
    p = ensure_params_v3(params)
    init_cash = 100_000.0
    pf = portfolio_fractionne_v3(
        df_close=df_close, params=p, init_cash=init_cash,
        buy_cash_frac=pas_fraction_buy,
        sell_pos_frac_A=p["sell_pos_frac_A"], sell_pos_frac_B=p["sell_pos_frac_B"],
        fee_rate=frais, priorite=priorite, freq="1w",
        min_cash_eps=0.0, min_units_eps=0.0,
    )

    # ---- contraintes de ventes ----
    orders = pf.orders.records_readable.copy()
    if "Timestamp" not in orders.columns:
        raise RuntimeError("orders table missing 'Timestamp'.")
    orders["Timestamp"] = pd.to_datetime(orders["Timestamp"])
    ventes_mask = (orders["Side"] == "Sell") & (orders["Size"].abs() > eps_size)
    if int(ventes_mask.sum()) < min_ventes:
        raise optuna.TrialPruned(f"Trop peu de ventes totales (< {min_ventes})")
    if int((ventes_mask & (orders["Timestamp"] >= pd.Timestamp("2023-01-01"))).sum()) < min_ventes_post2023:
        raise optuna.TrialPruned(f"Trop peu de ventes après 2023 (< {min_ventes_post2023})")

    # ---- métriques equity ----
    equity   = _to_series_last(pf.value())
    last_val = float(equity.iloc[-1])
    latent   = last_val / init_cash          # multiple
    mdd      = _max_drawdown(equity)         # 0..1
    risk_norm = max(0.0, min(1.0, 1.0 - mdd))

    # ---- PRUNE MDD si demandé ----
    if prune_mdd_max is not None and mdd > float(prune_mdd_max):
        thr_pct = float(prune_mdd_max) * 100.0
        raise optuna.TrialPruned(f"MDD {mdd*100:.1f}% > {thr_pct:.1f}%")

    # ---- PRUNING LATENT en multiple ----
    if mode in ("score", "latent") and prune_latent_multiple_min is not None:
        if latent < float(prune_latent_multiple_min):
            raise optuna.TrialPruned(f"Latent {latent:.3f}x < {prune_latent_multiple_min}x")

    # ---- modes simples ----
    if mode == "latent":
        return latent

    if mode == "realized":
        if "Fees" not in orders.columns:
            orders["Fees"] = 0.0
        orders = orders.sort_values("Timestamp")
        units = pru = realized_pnl = 0.0
        for _, row in orders.iterrows():
            side = str(row["Side"]).lower()
            qty  = float(row["Size"]);  px = float(row["Price"]);  fees = float(row["Fees"])
            if qty <= 0 or px <= 0: 
                continue
            if side == "buy":
                total_cost = pru * units + (px * qty + fees)
                units += qty
                pru = total_cost / max(units, 1e-18)
            elif side == "sell" and units > 0:
                realized_pnl += (px - pru) * qty - fees
                units -= qty
                if units <= 1e-18: pru = 0.0
        realized_ratio = 1.0 + realized_pnl / init_cash

        thr = prune_realized_multiple_min if prune_realized_multiple_min is not None else prune_latent_multiple_min
        if thr is not None and realized_ratio < float(thr):
            raise optuna.TrialPruned(f"Réalisé {realized_ratio:.3f}x < {thr}x")

        return realized_ratio

    # ---- mode "score" (borné 0..1) ----
    denom = max(1e-12, float(cap_ret) - 1.0)
    gain  = max(0.0, latent - 1.0)
    ret_norm = max(0.0, min(1.0, gain / denom))

    # Poids somme=1
    w_ret  = max(0.0, min(1.0, float(w_ret)))
    w_mdd  = max(0.0, min(1.0, float(w_mdd)))
    s = w_ret + w_mdd
    w_ret, w_mdd = (0.5, 0.5) if s <= 0 else (w_ret / s, w_mdd / s)

    score = w_ret * ret_norm + w_mdd * risk_norm
    return max(0.0, min(1.0, float(score)))
def optimisation_optuna_monotoken_fractionne_v3(
    df_close,
    mode: str = "score",          # "score" | "latent" | "realized"
    w_ret: float = 0.5,           # si optimize_weights=False, poids fixes
    w_mdd: float = 0.5,           # (renormalisés à somme=1 dans l’objectif)
    cap_ret: float = 3.0,         # plafond pour ret_norm linéaire
    use_realized_pru: bool = True,
    optimize_weights: bool = False,   # True => on optimise w_ret (et w_mdd=1-w_ret)
    # --- seuils de pruning en MULTIPLES ---
    prune_latent_multiple_min: float | None = None,     # ex: 40.0 => prune si latent < x40
    prune_realized_multiple_min: float | None = None,   # ex: 40.0 => prune si réalisé < x40
    # --- pruning MDD ---
    prune_mdd_max: float | None = None,     # ex: 0.50 pour 50%
    prune_mdd_pct_max: float | None = None, # ex: 50    pour 50%
):
    import optuna

    def _objective(trial):
        # --- hyperparams à optimiser ---
        frac_A = trial.suggest_float("sell_pos_frac_A", 0.05, 0.3)
        frac_B = trial.suggest_float("sell_pos_frac_B", 0.05, 0.3)
        buy_cash_frac = trial.suggest_float("buy_cash_frac", 0.05, 0.25)

        params_test = {
            "params_volat_achat": {
                "fenetre_glissante_nb_jours_volat_achat": trial.suggest_int("fen_gliss_volat_achat", 30, 120),
                "fenetre_quantile_volat_achat":           trial.suggest_int("fen_q_volat_achat", 500, 1300),
                "quantile_haut": 0.90,
                "quantile_bas_volat_achat":               trial.suggest_float("q_bas_volat_achat", 0.05, 0.25),
            },
            "params_ecart_relatif": {
                "nb_jours_arriere_ecart_relatif":  trial.suggest_int("jours_back_ecart_rel", 60, 300),
                "nb_jour_mm_ecart_relatif":        trial.suggest_int("jours_mm_ecart_rel", 20, 75),
                "nb_jour_quantiles_ecart_relatif": trial.suggest_int("jours_q_ecart_rel", 500, 1300),
                "quantile_haut": 0.90,
                "quantile_bas_ecart_relatif":      trial.suggest_float("q_bas_ecart_rel", 0.05, 0.25),
            },
            "params_rsi": {
                "length": 14,
                "nb_annees_quantile_rsi": trial.suggest_float("nb_ans_q_rsi", 1.5, 4.0),
                "quantile_haut_rsi":      trial.suggest_float("q_haut_rsi", 0.75, 0.95),
                "quantile_bas":           0.10,
                "quantile_intermediaire": 0.50,
            },
            "params_roi_1": {
                "periode_roi_en_jours":   trial.suggest_int("periode_roi1_j", 30, 365),
                "quantile_haut_roi":      trial.suggest_float("q_haut_roi1", 0.75, 0.95),
                "quantile_bas":           0.05,
                "quantile_bas_prix_achat": 0.05,
                "quantile_haut_prix_achat": 0.95,
                "nb_annees_quantile_roi": trial.suggest_float("nb_ans_q_roi1", 1.5, 4.0),
            },
            "params_roi_2": {
                "periode_roi_en_jours":   trial.suggest_int("periode_roi2_j", 30, 365),
                "quantile_haut_roi":      trial.suggest_float("q_haut_roi2", 0.75, 0.98),
                "quantile_bas":           0.05,
                "quantile_bas_prix_achat": 0.05,
                "quantile_haut_prix_achat": 0.95,
                "nb_annees_quantile_roi": trial.suggest_float("nb_ans_q_roi2", 1.5, 4.0),
            },
            "critère_rsi_achat": trial.suggest_int("critere_rsi_achat", 35, 60),
            "sell_pos_frac_A":   frac_A,
            "sell_pos_frac_B":   frac_B,
        }

        # --- poids du score ---
        if mode == "score" and optimize_weights:
            w_ret_trial = trial.suggest_float("w_ret", 0.0, 1.0)
            w_mdd_trial = 1.0 - w_ret_trial
        else:
            w_ret_trial, w_mdd_trial = w_ret, w_mdd

        # --- appel de la fonction objectif ---
        return fonction_objectif_monotoken_fractionne_v3(
            df_close=df_close,
            params=params_test,
            pas_fraction_buy=buy_cash_frac,
            frais=0.002,
            min_ventes=10,
            min_ventes_post2023=3,
            priorite="vente",
            mode=mode,
            w_ret=w_ret_trial, w_mdd=w_mdd_trial,
            cap_ret=cap_ret,
            use_realized_pru=use_realized_pru,
            # pruning en multiples
            prune_latent_multiple_min=prune_latent_multiple_min,
            prune_realized_multiple_min=prune_realized_multiple_min,
            # pruning MDD
            prune_mdd_max=prune_mdd_max,
            prune_mdd_pct_max=prune_mdd_pct_max,
            # on n'utilise pas les versions en %
            prune_latent_gain_pct_min=None,
            prune_realized_gain_pct_min=None,
        )

    return _objective



def recup_best_trials(study, top_n=10):
    """
    Extrait les top_n meilleurs trials d'une étude Optuna sous forme de DataFrame.

    Parameters:
        study (optuna.Study): L'étude Optuna.
        top_n (int): Le nombre de meilleurs trials à extraire.

    Returns:
        pd.DataFrame: DataFrame avec une ligne par trial, une colonne 'score', 
                      et les colonnes correspondant aux hyperparamètres.
    """
    best_trials = sorted(study.trials, key=lambda t: t.value if t.value is not None else float('-inf'), reverse=True)[:top_n]

    df = pd.DataFrame(
        [trial.params for trial in best_trials],
        index=[f"Trial_{trial.number}" for trial in best_trials]
    )

    df["score"] = [trial.value for trial in best_trials]
    
    # On place la colonne 'score' en première colonne
    cols = ['score'] + [col for col in df.columns if col != 'score']
    df = df[cols]
    
    return df.round(4)

def compter_trials_fail(study):
    from optuna.trial import TrialState
    """
    Retourne le nombre de trials qui ont échoué (état FAIL) dans une étude Optuna.
    
    Paramètre :
        study (optuna.Study) : L'étude Optuna à analyser.
    
    Retour :
        int : Nombre de trials en échec.
    """
    return sum(1 for t in study.trials if t.state == TrialState.FAIL)

def analyse_resultats_optuna(
    study,
    df_top200_trie,
    nb_best_trials=1,
    retirer_trades_non_closed=True,
    afficher_df_trades=False,
    afficher_best_trials=False,
    afficher_score_optimal=True,
    afficher_indice_composite=True,
    afficher_params_optimaux=True,
    afficher_stats=True,
    camemberts=True,
    afficher_optim_history=False,
    afficher_param_importances=False,
    retourner_portfolio=False,
    pondes=None
):
    from pprint import pprint
    import optuna.visualization as vis

    if pondes is None:
        pondes = {
            "pnl": 0.50,
            "win_rate": 0.15,
            "mdd": 0.1,
            "occurence": 0.2,
            "part_fermes": 0.05,
        }

    # Affichage du meilleur score
    if afficher_score_optimal:
        print("Meilleur score :", study.best_value)

    # Affichage des paramètres optimaux (bruts)
    if afficher_params_optimaux:
        print("\nParamètres optimaux :")
        pprint(study.best_params)
    
    if afficher_optim_history:
        print("\n📈 Historique de l'optimisation :")
        vis.plot_optimization_history(study).show()

    if afficher_param_importances:
        print("\n📊 Importance des hyperparamètres :")
        vis.plot_param_importances(study).show()

    # Extraction des best trials
    bests_trials = recup_best_trials(study, top_n=nb_best_trials)

    if afficher_best_trials:
        print(f"\nTop {nb_best_trials} trials :")
        display(bests_trials)

    # Paramètres moyens à partir des best trials
    params = recup_params_depuis_moyenne_trials(study, nb_best_trials)

    # Exécution du backtest (avec ou sans retour du portfolio)
    if retourner_portfolio:
        portfolio = backtest(df_top200_trie, params, retourner_portfolio_seulement=True)
    else:
        portfolio = None

    # Récupération des trades, pour stats et affichages
    df_trades = backtest(df_top200_trie, params, retirer_trades_non_closed=False)
    
    df_trades_filtered = (
        df_trades[df_trades["Status"] == "Closed"]
        if retirer_trades_non_closed
        else df_trades
    )

    # Affichage du dataframe des trades
    if afficher_df_trades:
        display(df_trades_filtered)

    # Affichage de l’indice composite
    if afficher_indice_composite:
        print("\nIndice composite :")
        pprint(indice_composite(df_trades, pondes=pondes))

    # Affichage des statistiques
    if afficher_stats:
        nb_tokens = df_trades_filtered.iloc[0]["nb_tokens_total"]
        stats = stats_trades(df_trades_filtered, nb_tokens)
        print("\nStatistiques :")
        pprint(stats)

    # Camemberts
    if camemberts:
        camembert_duree(df_trades_filtered)
        camembert_return(df_trades_filtered)
        camembert_mdd(df_trades_filtered)


    # Retour du portfolio à la toute fin, s’il est demandé
    if retourner_portfolio:
        return portfolio

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
