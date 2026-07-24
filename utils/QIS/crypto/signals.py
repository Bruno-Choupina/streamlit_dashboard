import math
import numpy as np
import pandas as pd
import ta

from utils.QIS.crypto.indicators import (
    volat_glissante_prix_quantiles_vectoriel,
    ecart_relatif_moyen_glissant_vectoriel,
    rsi_avec_quantiles_vectoriel,
    roi_avec_quantile_vectoriel,
)

def signaux_achats(df_plat, params_volat_achat, params_ecart_relatif, length_rsi=14, critere_rsi=50):
    # Indicateurs volat
    df_volat = volat_glissante_prix_quantiles_vectoriel(
        df_plat,
        params_volat_achat["fenetre_glissante_nb_jours_volat_achat"],
        params_volat_achat["fenetre_quantile_volat_achat"],
        params_volat_achat["quantile_haut"],
        params_volat_achat["quantile_bas_volat_achat"]
    )

    # Indicateurs écart relatif
    df_ecart_relatif = ecart_relatif_moyen_glissant_vectoriel(
        df_plat,
        params_ecart_relatif["nb_jours_arriere_ecart_relatif"],
        params_ecart_relatif["nb_jour_mm_ecart_relatif"],
        params_ecart_relatif["nb_jour_quantiles_ecart_relatif"],
        params_ecart_relatif["quantile_haut"],
        params_ecart_relatif["quantile_bas_ecart_relatif"]
    )

    # RSI direct (calculé pour chaque colonne/crypto)



    rsi = df_plat.apply(lambda x: ta.momentum.rsi(x, window=length_rsi), result_type="expand")
    
    df_rsi = rsi.copy()
    df_rsi.columns = pd.MultiIndex.from_product([rsi.columns, ["rsi"]])


    # Concaténation des indicateurs
    df_signaux_achats = pd.concat([df_volat, df_ecart_relatif, df_rsi], axis=1)
    df_signaux_achats = df_signaux_achats.stack(level=0, dropna=False)



    # Critère d'achat
    df_signaux = (
        (df_signaux_achats["std_glissante_prix"] < df_signaux_achats["quantile_bas_glissant_std"]) &
        (df_signaux_achats["mm_ecart_relatif"] < df_signaux_achats["qbas_glissant_ecart_relatif"]) &
        (df_signaux_achats["rsi"] < critere_rsi)
    )

    df_signaux = df_signaux.unstack(level=1)
    # Remettre dans l’ordre original des cryptos
    order = df_plat.columns
    df_signaux = df_signaux[order]
    df_signaux[df_signaux.index < "2021-11-08"] = False #2021-11-08
    
    return df_signaux

def signaux_vente(df_plat,params_volat_vente,params_rsi,params_roi):

    df_volat=volat_glissante_prix_quantiles_vectoriel(
        df_plat,
        params_volat_vente["fenetre_glissante_nb_jours_volat_vente"],
        params_volat_vente["fenetre_quantile_volat_vente"],
        params_volat_vente["quantile_haut_volat_vente"],
        params_volat_vente["quantile_bas"]
        )
    

    df_rsi=rsi_avec_quantiles_vectoriel(
        df_plat,
        params_rsi["length"],
        params_rsi["nb_annees_quantile_rsi"],
        params_rsi["quantile_haut_rsi"],
        params_rsi["quantile_bas"],
        params_rsi["quantile_intermediaire"]
        )
    

    df_roi=roi_avec_quantile_vectoriel(
        df_plat,
        params_roi["periode_roi_en_jours"],
        params_roi["quantile_haut_roi"],
        params_roi["quantile_bas"],
        params_roi["quantile_bas_prix_achat"],
        params_roi["quantile_haut_prix_achat"],
        params_roi["nb_annees_quantile_roi"]
    )

    df_signaux_vente=pd.concat([df_volat,df_rsi,df_roi],axis=1)
    df_signaux_vente=df_signaux_vente.stack(level=0,dropna=False)

    #cond_rsi = (
    #(df_signaux_vente["quantile_haut_glissant_rsi"] < 70) &
    #(df_signaux_vente["rsi"] > 70)
#) | (
#    (df_signaux_vente["quantile_haut_glissant_rsi"] >= 70) &
 #   (df_signaux_vente["rsi"] > df_signaux_vente["quantile_haut_glissant_rsi"])
#)

    df_signaux=(df_signaux_vente["std_glissante_prix"]>df_signaux_vente["quantile_haut_glissant_std"]) & (df_signaux_vente["rsi"]>df_signaux_vente["quantile_haut_glissant_rsi"])&(df_signaux_vente["roi_hausse"]>df_signaux_vente["quantile_haut_glissant_roi"])
    df_signaux=df_signaux.unstack(level=1)

    order=df_plat.columns
    df_signaux=df_signaux[order]

    return df_signaux

def signaux_vente_decomposee(df_plat, params_volat_vente, params_rsi, params_roi):
    """
    Sorties:
      - sig_volat, sig_rsi, sig_roi : DataFrames bool (index dates, colonnes actifs)
      - count : nb de signaux vrais (0..3)
      - mask_3sur3 : True si 3/3
      - mask_2sur3 : True si exactement 2/3
    """
    # === VOLAT ===
    df_volat = volat_glissante_prix_quantiles_vectoriel(
        df_plat,
        params_volat_vente["fenetre_glissante_nb_jours_volat_vente"],
        params_volat_vente["fenetre_quantile_volat_vente"],
        params_volat_vente["quantile_haut_volat_vente"],
        params_volat_vente["quantile_bas"]
    )
    # niveau1 = nom d'indicateur
    vol_std   = df_volat.xs("std_glissante_prix",       axis=1, level=1)
    vol_q_bas = df_volat.xs("quantile_bas_glissant_std", axis=1, level=1)
    sig_volat = (vol_std > vol_q_bas)

    # === RSI ===
    df_rsi = rsi_avec_quantiles_vectoriel(
        df_plat,
        params_rsi["length"],
        params_rsi["nb_annees_quantile_rsi"],
        params_rsi["quantile_haut_rsi"],
        params_rsi["quantile_bas"],
        params_rsi["quantile_intermediaire"]
    )
    rsi_val   = df_rsi.xs("rsi",                      axis=1, level=1)
    rsi_qhaut = df_rsi.xs("quantile_haut_glissant_rsi", axis=1, level=1)
    sig_rsi   = (rsi_val > rsi_qhaut)

    # === ROI ===
    df_roi = roi_avec_quantile_vectoriel(
        df_plat,
        params_roi["periode_roi_en_jours"],
        params_roi["quantile_haut_roi"],
        params_roi["quantile_bas"],
        params_roi["quantile_bas_prix_achat"],
        params_roi["quantile_haut_prix_achat"],
        params_roi["nb_annees_quantile_roi"]
    )
    roi_up    = df_roi.xs("roi_hausse",                axis=1, level=1)
    roi_qhaut = df_roi.xs("quantile_haut_glissant_roi", axis=1, level=1)
    sig_roi   = (roi_up > roi_qhaut)

    # Alignements & NaN -> False
    sig_volat = sig_volat.reindex_like(df_plat).fillna(False)
    sig_rsi   = sig_rsi.reindex_like(df_plat).fillna(False)
    sig_roi   = sig_roi.reindex_like(df_plat).fillna(False)

    count = sig_volat.astype(int) + sig_rsi.astype(int) + sig_roi.astype(int)
    mask_3sur3 = (count == 3)
    mask_2sur3 = (count == 2)

    return {
        "sig_volat": sig_volat,
        "sig_rsi":   sig_rsi,
        "sig_roi":   sig_roi,
        "count":     count.astype(int),
        "mask_3sur3": mask_3sur3,
        "mask_2sur3": mask_2sur3,
    }

def signaux_vente_v3_decomposee(df_plat, params_rsi, params_roi_1, params_roi_2):
    """
    Renvoie:
      - mask_A: vente type A (RSI + ROI#1)
      - mask_B: vente type B (ROI#2 seul)
    """
    # RSI
    df_rsi = rsi_avec_quantiles_vectoriel(
        df_plat,
        params_rsi["length"],
        params_rsi["nb_annees_quantile_rsi"],
        params_rsi["quantile_haut_rsi"],
        params_rsi["quantile_bas"],
        params_rsi["quantile_intermediaire"],
    )

    # ROI #1
    df_roi_1 = roi_avec_quantile_vectoriel(
        df_plat,
        params_roi_1["periode_roi_en_jours"],
        params_roi_1["quantile_haut_roi"],
        params_roi_1["quantile_bas"],
        params_roi_1["quantile_bas_prix_achat"],
        params_roi_1["quantile_haut_prix_achat"],
        params_roi_1["nb_annees_quantile_roi"],
    )

    # ROI #2 (autre set de paramètres)
    df_roi_2 = roi_avec_quantile_vectoriel(
        df_plat,
        params_roi_2["periode_roi_en_jours"],
        params_roi_2["quantile_haut_roi"],
        params_roi_2["quantile_bas"],
        params_roi_2["quantile_bas_prix_achat"],
        params_roi_2["quantile_haut_prix_achat"],
        params_roi_2["nb_annees_quantile_roi"],
    )

    # Conditions
    c_rsi = (
        df_rsi.xs("rsi", level=1, axis=1) >
        df_rsi.xs("quantile_haut_glissant_rsi", level=1, axis=1)
    ).reindex(df_plat.index).fillna(False)

    c_roi1 = (
        df_roi_1.xs("roi_hausse", level=1, axis=1) >
        df_roi_1.xs("quantile_haut_glissant_roi", level=1, axis=1)
    ).reindex(df_plat.index).fillna(False)

    c_roi2 = (
        df_roi_2.xs("roi_hausse", level=1, axis=1) >
        df_roi_2.xs("quantile_haut_glissant_roi", level=1, axis=1)
    ).reindex(df_plat.index).fillna(False)

    mask_A = (c_rsi & c_roi1).astype(bool)
    mask_B = (c_roi2).astype(bool)

    # Option: éviter double-compte le même jour (A prioritaire)
    mask_B = mask_B & (~mask_A)

    return {"mask_A": mask_A, "mask_B": mask_B}

