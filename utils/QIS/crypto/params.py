import pandas as pd
import numpy as np


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

def recup_params_depuis_moyenne_trials(study, top_n=1):
    """
    Reconstruit le dictionnaire structuré des paramètres à partir 
    de la moyenne des top_n meilleurs trials d’une étude Optuna.

    Parameters:
        study (optuna.study.Study) : étude Optuna contenant tous les essais
        top_n (int) : nombre de meilleurs trials à utiliser pour la moyenne

    Returns:
        dict : dictionnaire de paramètres structurés
    """

    # Récupération des top_n meilleurs trials
    top_trials = sorted(
        [trial for trial in study.trials if trial.state.name == "COMPLETE"],
        key=lambda t: t.value,
        reverse=True
    )[:top_n]

    # Création du DataFrame à partir des params des trials
    df_trials = pd.DataFrame([trial.params for trial in top_trials])

    # Conversion explicite en float pour éviter erreurs avec certaines colonnes
    df_trials = df_trials.apply(pd.to_numeric, errors='coerce')

    # Calcul des moyennes
    moyennes = df_trials.mean()

    # Reconstruit la structure des paramètres comme avant
    params_test = {
        "params_volat_achat": {
            "fenetre_glissante_nb_jours_volat_achat": int(round(moyennes["fenetre_glissante_nb_jours_volat_achat"])),
            "fenetre_quantile_volat_achat": int(round(moyennes["fenetre_quantile_volat_achat"])),
            "quantile_haut": 0.9,
            "quantile_bas_volat_achat": moyennes["quantile_bas_volat_achat"]
        },
        "params_ecart_relatif": {
            "nb_jours_arriere_ecart_relatif": int(round(moyennes["nb_jours_arriere_ecart_relatif"])),
            "nb_jour_mm_ecart_relatif": int(round(moyennes["nb_jour_mm_ecart_relatif"])),
            "nb_jour_quantiles_ecart_relatif": int(round(moyennes["nb_jour_quantiles_ecart_relatif"])),
            "quantile_haut": 0.9,
            "quantile_bas_ecart_relatif": moyennes["quantile_bas_ecart_relatif"]
        },
        "params_volat_vente": {
            "fenetre_glissante_nb_jours_volat_vente": int(round(moyennes["fenetre_glissante_nb_jours_volat_vente"])),
            "fenetre_quantile_volat_vente": int(round(moyennes["fenetre_quantile_volat_vente"])),
            "quantile_haut_volat_vente": moyennes["quantile_haut_volat_vente"],
            "quantile_bas": 0.1
        },
        "params_roi": {
            "periode_roi_en_jours": int(round(moyennes["periode_roi_en_jours"])),
            "quantile_haut_roi": moyennes["quantile_haut_roi"],
            "quantile_bas": 0.1,
            "quantile_bas_prix_achat": 0.05,
            "quantile_haut_prix_achat": 0.95,
            "nb_annees_quantile_roi": moyennes["nb_annees_quantile_roi"]
        },
        "params_rsi": {
            "length": 14,
            "nb_annees_quantile_rsi": moyennes["nb_annees_quantile_rsi"],
            "quantile_haut_rsi": moyennes["quantile_haut_rsi"],
            "quantile_bas": 0.1,
            "quantile_intermediaire": 0.5
        },
        "critère_rsi_achat": int(round(moyennes["critère_rsi_achat"]))
    }

    return params_test

def recup_params_depuis_params_trial(dico_params):
    """
    Transforme un dictionnaire plat de paramètres issus d’un trial Optuna 
    en dictionnaire structuré conforme au format `params_test`.
    """

    params_test = {
        "params_volat_achat": {
            "fenetre_glissante_nb_jours_volat_achat": dico_params["fenetre_glissante_nb_jours_volat_achat"],
            "fenetre_quantile_volat_achat": dico_params["fenetre_quantile_volat_achat"],
            "quantile_haut": 0.9,
            "quantile_bas_volat_achat": dico_params["quantile_bas_volat_achat"]
        },
        "params_ecart_relatif": {
            "nb_jours_arriere_ecart_relatif": dico_params["nb_jours_arriere_ecart_relatif"],
            "nb_jour_mm_ecart_relatif": dico_params["nb_jour_mm_ecart_relatif"],
            "nb_jour_quantiles_ecart_relatif": dico_params["nb_jour_quantiles_ecart_relatif"],
            "quantile_haut": 0.9,
            "quantile_bas_ecart_relatif": dico_params["quantile_bas_ecart_relatif"]
        },
        "params_volat_vente": {
            "fenetre_glissante_nb_jours_volat_vente": dico_params["fenetre_glissante_nb_jours_volat_vente"],
            "fenetre_quantile_volat_vente": dico_params["fenetre_quantile_volat_vente"],
            "quantile_haut_volat_vente": dico_params["quantile_haut_volat_vente"],
            "quantile_bas": 0.1
        },
        "params_roi": {
            "periode_roi_en_jours": dico_params["periode_roi_en_jours"],
            "quantile_haut_roi": dico_params["quantile_haut_roi"],
            "quantile_bas": 0.05,
            "quantile_bas_prix_achat": 0.05,
            "quantile_haut_prix_achat": 0.95,
            "nb_annees_quantile_roi": dico_params["nb_annees_quantile_roi"]
        },
        "params_rsi": {
            "length": 14,
            "nb_annees_quantile_rsi": dico_params["nb_annees_quantile_rsi"],
            "quantile_haut_rsi": dico_params["quantile_haut_rsi"],
            "quantile_bas": 0.1,
            "quantile_intermediaire": 0.5
        },
        "critère_rsi_achat": dico_params["critère_rsi_achat"]
    }

    return params_test

def recup_params_v2_depuis_study(study, top_n=1, weighted=False):
    """
    Version dédiée à l'optim V2 (clés courtes) :
    - Récupère les top_n trials COMPLETES
    - Fait une moyenne simple ou pondérée par la valeur (score)
    - Reconstruit le dict params attendu par portfolio_fractionne_v2
      (inclut x_streak_2on3, x_gap_2on3, sell_pos_frac_3on3, sell_pos_frac_2on3)
    """
    import pandas as pd
    import numpy as np

    # 1) Trials complets triés par score décroissant
    complete = [t for t in study.trials if getattr(t, "state", None) 
                and t.state.name == "COMPLETE" and t.value is not None]
    if not complete:
        raise ValueError("Aucun trial COMPLETE avec valeur dans l'étude.")
    complete = sorted(complete, key=lambda t: t.value, reverse=True)
    top = complete[:max(1, min(top_n, len(complete)))]

    # 2) DataFrame des params + vecteur des scores
    df = pd.DataFrame([t.params for t in top]).apply(pd.to_numeric, errors="coerce")
    scores = np.array([t.value for t in top], dtype=float)

    # 3) Moyenne simple ou pondérée
    if weighted and len(top) > 1:
        s = scores - np.nanmin(scores)
        if np.nanmax(s) > 0:
            w = s / np.nansum(s)
        else:
            w = np.ones_like(s) / len(s)
        moy = (df.fillna(df.mean()).values * w[:, None]).sum(axis=0)
        moy = pd.Series(moy, index=df.columns)
    else:
        moy = df.mean()

    # 4) Helpers
    def geti(k, default=None):
        v = moy.get(k, np.nan)
        if pd.isna(v):
            if default is None:
                raise KeyError(f"Clé manquante dans trials: {k}")
            v = default
        return int(round(float(v)))

    def getf(k, default=None):
        v = moy.get(k, np.nan)
        if pd.isna(v):
            if default is None:
                raise KeyError(f"Clé manquante dans trials: {k}")
            v = default
        return float(v)

    # 5) Construction du dict final
    params = {
        "params_volat_achat": {
            "fenetre_glissante_nb_jours_volat_achat": geti("fen_gliss_volat_achat"),
            "fenetre_quantile_volat_achat":          geti("fen_q_volat_achat"),
            "quantile_haut": 0.90,
            "quantile_bas_volat_achat":              getf("q_bas_volat_achat"),
        },
        "params_ecart_relatif": {
            "nb_jours_arriere_ecart_relatif":        geti("jours_back_ecart_rel"),
            "nb_jour_mm_ecart_relatif":              geti("jours_mm_ecart_rel"),
            "nb_jour_quantiles_ecart_relatif":       geti("jours_q_ecart_rel"),
            "quantile_haut": 0.90,
            "quantile_bas_ecart_relatif":            getf("q_bas_ecart_rel"),
        },
        "params_volat_vente": {
            "fenetre_glissante_nb_jours_volat_vente": geti("fen_gliss_volat_vente"),
            "fenetre_quantile_volat_vente":           geti("fen_q_volat_vente"),
            "quantile_haut_volat_vente":              getf("q_haut_volat_vente"),
            "quantile_bas": 0.10,
        },
        "params_roi": {
            "periode_roi_en_jours":                  geti("periode_roi_j"),
            "quantile_haut_roi":                     getf("q_haut_roi"),
            "quantile_bas": 0.05,
            "quantile_bas_prix_achat": 0.05,
            "quantile_haut_prix_achat": 0.95,
            "nb_annees_quantile_roi":                getf("nb_ans_q_roi"),
        },
        "params_rsi": {
            "length": 14,
            "nb_annees_quantile_rsi":                getf("nb_ans_q_rsi"),
            "quantile_haut_rsi":                     getf("q_haut_rsi"),
            "quantile_bas": 0.10,
            "quantile_intermediaire": 0.50,
        },
        "critère_rsi_achat":                         geti("critere_rsi_achat"),

        # Nouveaux paramètres V2
        "x_streak_2on3":                             geti("x_streak_2on3", default=2),
        "x_gap_2on3":                                geti("x_gap_2on3",    default=3),

        # Nouveaux paramètres ventes
        "sell_pos_frac_3on3":                        getf("sell_pos_frac_3on3", default=0.20),
        "sell_pos_frac_2on3":                        getf("sell_pos_frac_2on3", default=0.05),
    }
    return params

def recup_params_v3_depuis_study(study):
    b = getattr(study, "best_params", {})
    def g(k, dflt):
        return b[k] if k in b else dflt

    params = {
        "params_volat_achat": {
            "fenetre_glissante_nb_jours_volat_achat": g("fen_gliss_volat_achat", 90),
            "fenetre_quantile_volat_achat":          g("fen_q_volat_achat", 800),
            "quantile_haut": 0.90,
            "quantile_bas_volat_achat":              g("q_bas_volat_achat", 0.15),
        },
        "params_ecart_relatif": {
            "nb_jours_arriere_ecart_relatif":  g("jours_back_ecart_rel", 180),
            "nb_jour_mm_ecart_relatif":        g("jours_mm_ecart_rel", 40),
            "nb_jour_quantiles_ecart_relatif": g("jours_q_ecart_rel", 800),
            "quantile_haut": 0.90,
            "quantile_bas_ecart_relatif":      g("q_bas_ecart_rel", 0.15),
        },
        "params_rsi": {
            "length": 14,
            "nb_annees_quantile_rsi": g("nb_ans_q_rsi", 3.0),
            "quantile_haut_rsi":      g("q_haut_rsi", 0.90),
            "quantile_bas":           0.10,
            "quantile_intermediaire": 0.50,
        },
        "params_roi_1": {
            "periode_roi_en_jours":   g("periode_roi1_j", 120),
            "quantile_haut_roi":      g("q_haut_roi1", 0.85),
            "quantile_bas":           0.05,
            "quantile_bas_prix_achat": 0.05,
            "quantile_haut_prix_achat": 0.95,
            "nb_annees_quantile_roi": g("nb_ans_q_roi1", 3.0),
        },
        "params_roi_2": {
            "periode_roi_en_jours":   g("periode_roi2_j", 180),
            "quantile_haut_roi":      g("q_haut_roi2", 0.90),
            "quantile_bas":           0.05,
            "quantile_bas_prix_achat": 0.05,
            "quantile_haut_prix_achat": 0.95,
            "nb_annees_quantile_roi": g("nb_ans_q_roi2", 3.0),
        },
        "critère_rsi_achat": g("critere_rsi_achat", 50),
        "sell_pos_frac_A":   g("sell_pos_frac_A", 0.20),
        "sell_pos_frac_B":   g("sell_pos_frac_B", 0.05),
        "pas_fraction_buy":     g("buy_cash_frac", 0.20),  # ← ajout important
    }
    return params

def ensure_params_v3(params: dict) -> dict:
    """Back-compat + sane defaults for V3 params (mutates a copy)."""
    p = dict(params)  # shallow copy

    # ROI back-compat: accept single params_roi
    if "params_roi_1" not in p or "params_roi_2" not in p:
        base_roi = p.get("params_roi")
        if base_roi is None:
            # if not provided, raise explicit error later in the pipeline
            base_roi = {
                "periode_roi_en_jours": 90,
                "quantile_haut_roi": 0.85,
                "quantile_bas": 0.05,
                "quantile_bas_prix_achat": 0.05,
                "quantile_haut_prix_achat": 0.95,
                "nb_annees_quantile_roi": 3.0,
            }
        p.setdefault("params_roi_1", base_roi)
        p.setdefault("params_roi_2", base_roi)

    # defaults (kept if absent)
    p.setdefault("sell_pos_frac_A", 0.20)
    p.setdefault("sell_pos_frac_B", 0.05)
    p.setdefault("critère_rsi_achat", 50)

    return p

def recup_params_depuis_moyenne_trials_fractionne(
    study, 
    top_n: int = 1
):
    """
    Reconstruit le dictionnaire structuré des paramètres à partir 
    de la moyenne des top_n meilleurs trials d’une étude Optuna,
    incluant buy_cash_frac et sell_pos_frac directement dans le dico principal.
    """

    import pandas as pd
    import numpy as np

    # 1) Sélection des top_n meilleurs trials
    top_trials = sorted(
        [t for t in study.trials if getattr(t, "state", None) and t.state.name == "COMPLETE" and t.value is not None],
        key=lambda t: t.value,
        reverse=True
    )[:max(1, top_n)]

    if not top_trials:
        raise ValueError("Aucun trial COMPLETE avec une valeur.")

    # 2) Moyenne des paramètres
    df_trials = pd.DataFrame([trial.params for trial in top_trials]).apply(pd.to_numeric, errors="coerce")
    moyennes = df_trials.mean()

    # 3) Construction du dico structuré
    params_test = {
        "params_volat_achat": {
            "fenetre_glissante_nb_jours_volat_achat": int(round(moyennes["fenetre_glissante_nb_jours_volat_achat"])),
            "fenetre_quantile_volat_achat": int(round(moyennes["fenetre_quantile_volat_achat"])),
            "quantile_haut": 0.9,
            "quantile_bas_volat_achat": moyennes["quantile_bas_volat_achat"]
        },
        "params_ecart_relatif": {
            "nb_jours_arriere_ecart_relatif": int(round(moyennes["nb_jours_arriere_ecart_relatif"])),
            "nb_jour_mm_ecart_relatif": int(round(moyennes["nb_jour_mm_ecart_relatif"])),
            "nb_jour_quantiles_ecart_relatif": int(round(moyennes["nb_jour_quantiles_ecart_relatif"])),
            "quantile_haut": 0.9,
            "quantile_bas_ecart_relatif": moyennes["quantile_bas_ecart_relatif"]
        },
        "params_volat_vente": {
            "fenetre_glissante_nb_jours_volat_vente": int(round(moyennes["fenetre_glissante_nb_jours_volat_vente"])),
            "fenetre_quantile_volat_vente": int(round(moyennes["fenetre_quantile_volat_vente"])),
            "quantile_haut_volat_vente": moyennes["quantile_haut_volat_vente"],
            "quantile_bas": 0.1
        },
        "params_roi": {
            "periode_roi_en_jours": int(round(moyennes["periode_roi_en_jours"])),
            "quantile_haut_roi": moyennes["quantile_haut_roi"],
            "quantile_bas": 0.1,
            "quantile_bas_prix_achat": 0.05,
            "quantile_haut_prix_achat": 0.95,
            "nb_annees_quantile_roi": moyennes["nb_annees_quantile_roi"]
        },
        "params_rsi": {
            "length": 14,
            "nb_annees_quantile_rsi": moyennes["nb_annees_quantile_rsi"],
            "quantile_haut_rsi": moyennes["quantile_haut_rsi"],
            "quantile_bas": 0.1,
            "quantile_intermediaire": 0.5
        },
        "critère_rsi_achat": int(round(moyennes["critère_rsi_achat"])),
        "buy_cash_frac": moyennes.get("buy_cash_frac", 0.20),
        "sell_pos_frac": moyennes.get("sell_pos_frac", 0.20)
    }

    return params_test

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