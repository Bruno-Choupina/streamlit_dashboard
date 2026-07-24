import math
import numpy as np
import pandas as pd
import ta

# %% Fonctions quii calcule l'indicateur en question pour un univers d'une seul et unique crypto

def calculs_quantiles_nearestrank(series, quantile, fenetre_glissante, cumulatif_ou_non, min_periods=15):
    quantiles = []
    donnees_valides = []
    for i in range(len(series)):
        val = series.iloc[i]
        if not pd.isna(val):
            donnees_valides.append(val)
        # -- Cumulatif
        if cumulatif_ou_non:
            if len(donnees_valides) >= min_periods:
                vals_sorted = np.sort(donnees_valides)
                idx = int(np.ceil(quantile * len(vals_sorted)) - 1)
                quantiles.append(vals_sorted[idx])
            else:
                quantiles.append(np.nan)
        # -- Glissant
        else:
            if len(donnees_valides) >= fenetre_glissante:
                vals_sorted = np.sort(donnees_valides[-fenetre_glissante:])
                idx = int(np.ceil(quantile * len(vals_sorted)) - 1)
                quantiles.append(vals_sorted[idx])
            else:
                quantiles.append(np.nan)
    return pd.Series(quantiles, index=series.index)

def calcul_quantile_roi_glissant(series, quantile, fenetre_quantile):
    import pandas as pd
    
#Fonction qui prend pour chaque date les x dernières valeures valides (roi positif si série hausse ou négatives si serie basse), x étant le nb de période souhaitées pour calcul du quantile
    quantiles=[]
    donnees_valides=[]
    for i in range(len(series)):
        #print(series.iloc[i])
        if not pd.isna(series.iloc[i]):

            donnees_valides.append(series.iloc[i])
        
        if len(donnees_valides)>=fenetre_quantile:

            donnees_glissantes=np.sort(donnees_valides[-fenetre_quantile:])
            idx=int(np.ceil(quantile*len(donnees_glissantes))-1)
            
            quantiles.append(donnees_glissantes[idx])
        else:
            quantiles.append(np.nan)
    df=pd.Series(quantiles,index=series.index)
    #display(df.dropna())

    return df


def calcul_quantiles_roi_cumulatifs(series,quantile,min_period=20):

    import pandas as pd

    quantiles=[]
    donnes_valides=[]

    for i in range(len(series)):

        #print(series.iloc[i])
        if not pd.isna(series.iloc[i]):
            donnes_valides.append(series.iloc[i])
        
        if len(donnes_valides)>=min_period:

            donnes_valides_sorted=np.sort(donnes_valides)
            idx=int(math.ceil(quantile*len(donnes_valides))-1)
            quantiles.append(donnes_valides_sorted[idx])
        else:
            quantiles.append(np.nan)
    
    return pd.Series(quantiles,index=series.index)


def volat_glissante_prix_quantiles(df,fenetre_glissante_nb_jours,fenetre_quantile,quantile_haut,quantile_bas):
    df=df.copy()

    secondes_par_bougie=(df.index[1]-df.index[0]).total_seconds()
    fenetre_glissante_secondes=fenetre_glissante_nb_jours*24*60*60
    fenetre_quantile_secondes=fenetre_quantile*24*60*60
    
    nb_bougies_volat=math.ceil(fenetre_glissante_secondes/secondes_par_bougie)
    nb_bougies_quantile=math.ceil(fenetre_quantile_secondes/secondes_par_bougie)

    df["std_glissante_prix"] = df["close"].rolling(nb_bougies_volat).std(ddof=0)


    df["quantile_haut_glissant_std"]=calculs_quantiles_nearestrank(df["std_glissante_prix"],quantile_haut,nb_bougies_quantile,False)
    df["quantile_bas_glissant_std"]=calculs_quantiles_nearestrank(df["std_glissante_prix"],quantile_bas,nb_bougies_quantile,False)
    df["quantile_haut_cumulatif_std"]=calculs_quantiles_nearestrank(df["std_glissante_prix"],quantile_haut,nb_bougies_quantile,True)                                                   
    df["quantile_bas_cumulatif_std"]=calculs_quantiles_nearestrank(df["std_glissante_prix"],quantile_bas,nb_bougies_quantile,True)

    return df                                              

def ecart_relatif_moyen_glissant(df, nb_jours_arriere_ecart_relatif, nb_jour_mm, nb_jour_quantiles, quantile_haut, quantile_bas):

    df=df.copy()

    secondes_par_bougie=(df.index[1]-df.index[0]).total_seconds()
    nb_jours_arriere_secondes=nb_jours_arriere_ecart_relatif*24*60*60
    nb_jour_mm_secondes=nb_jour_mm*24*60*60
    nb_jour_quantiles_secondes=nb_jour_quantiles*24*60*60
    
    nb_bougies_ecart_relatif=math.ceil(nb_jours_arriere_secondes/secondes_par_bougie)
    nb_bougies_mm=math.ceil(nb_jour_mm_secondes/secondes_par_bougie)
    nb_bougies_quantiles=math.ceil(nb_jour_quantiles_secondes/secondes_par_bougie)

    df["haut_glissant"] = df["close"].rolling(nb_bougies_ecart_relatif).max()
    df["bas_glissant"] = df["close"].rolling(nb_bougies_ecart_relatif).min()
    df["ecart_relatif_glissant"] = (df["haut_glissant"] - df["bas_glissant"]) / df["bas_glissant"]

    df.drop(columns=["haut_glissant","bas_glissant"],inplace=True)

    df["moyenne_mobile_ecart_relatif"]=df["ecart_relatif_glissant"].rolling(nb_bougies_mm).mean()

    df["quantile_haut_glissant_ecart_relatif"]=calculs_quantiles_nearestrank(df["ecart_relatif_glissant"],quantile_haut,nb_bougies_quantiles,False)
    df["quantile_bas_glissant_ecart_relatif"]=calculs_quantiles_nearestrank(df["ecart_relatif_glissant"],quantile_bas,nb_bougies_quantiles,False)

    df["quantile_haut_cumulatif_ecart_relatif"]=calculs_quantiles_nearestrank(df["ecart_relatif_glissant"],quantile_haut,nb_bougies_quantiles,True)
    df["quantile_bas_cumulatif_ecart_relatif"]=calculs_quantiles_nearestrank(df["ecart_relatif_glissant"],quantile_bas,nb_bougies_quantiles,True)

    return df

def rsi_avec_quantiles(df,length,nombre_annees_quantiles,quantile_haut,quantile_bas,quantile_intermediaire):

    df=df.copy()

    secondes_par_bougie=(df.index[1]-df.index[0]).total_seconds()
    fenetre_quantile_secondes=nombre_annees_quantiles*365*24*60*60
    
    nb_bougies_quantile=math.ceil(fenetre_quantile_secondes/secondes_par_bougie)

    df["rsi"]=ta.momentum.rsi(df['close'], window=length)

    df["quantile_haut_glissant_rsi"]=calculs_quantiles_nearestrank(df["rsi"],quantile_haut,nb_bougies_quantile,False)
    df["quantile_bas_glissant_rsi"]=calculs_quantiles_nearestrank(df["rsi"],quantile_bas,nb_bougies_quantile,False)
    df["quantile_intermediaire_glissant_rsi"]=calculs_quantiles_nearestrank(df["rsi"],quantile_intermediaire,nb_bougies_quantile,False)

    df["quantile_haut_cumulatif_rsi"]=calculs_quantiles_nearestrank(df["rsi"],quantile_haut,nb_bougies_quantile,True)
    df["quantile_bas_cumulatif_rsi"]=calculs_quantiles_nearestrank(df["rsi"],quantile_bas,nb_bougies_quantile,True)

    return df

# %% Fonctions qui calculent les mêmes indicateurs mais pour plusieurs cryptos dans un même df, 
# #renvoient un df multiindex avec en niveau 0 la crypto et en 1 les indicateurs de chaque crypto

def volat_glissante_prix_quantiles_vectoriel(df_close,fenetre_glissante_nb_jours,fenetre_quantile,quantile_haut,quantile_bas):


    secondes_par_bougie=(df_close.index[1]-df_close.index[0]).total_seconds()
    fenetre_glissante_secondes=fenetre_glissante_nb_jours*24*60*60
    fenetre_quantile_secondes=fenetre_quantile*24*60*60
    
    nb_bougies_volat=math.ceil(fenetre_glissante_secondes/secondes_par_bougie)
    nb_bougies_quantile=math.ceil(fenetre_quantile_secondes/secondes_par_bougie)

    std_glissante_prix=df_close.rolling(nb_bougies_volat).std(ddof=0)
    quantile_haut_glissant_std=std_glissante_prix.apply(lambda s:calculs_quantiles_nearestrank(s,quantile_haut,nb_bougies_quantile,False))
    quantile_bas_glissant_std=std_glissante_prix.apply(lambda s:calculs_quantiles_nearestrank(s,quantile_bas,nb_bougies_quantile,False))
    quantile_haut_cumulatif_std=std_glissante_prix.apply(lambda s:calculs_quantiles_nearestrank(s,quantile_haut,nb_bougies_quantile,True))
    quantile_bas_cumulatif_std=std_glissante_prix.apply(lambda s:calculs_quantiles_nearestrank(s,quantile_bas,nb_bougies_quantile,True))

    dfs={
        "std_glissante_prix":std_glissante_prix,
        "quantile_haut_glissant_std":quantile_haut_glissant_std,
        "quantile_bas_glissant_std":quantile_bas_glissant_std,
        "quantile_haut_cumulatif_std":quantile_haut_cumulatif_std,
        "quantile_bas_cumulatif_std":quantile_bas_cumulatif_std
    }

    df_indicateur = pd.concat(dfs, axis=1)

    df_indicateur = df_indicateur.swaplevel(0, 1, axis=1)
    return df_indicateur
    
def ecart_relatif_moyen_glissant_vectoriel(df_close, nb_jours_arriere_ecart_relatif, nb_jour_mm, nb_jour_quantiles, quantile_haut, quantile_bas):
    secondes_par_bougie = (df_close.index[1] - df_close.index[0]).total_seconds()
    nb_jours_arriere_secondes = nb_jours_arriere_ecart_relatif * 24 * 60 * 60
    nb_jour_mm_secondes = nb_jour_mm * 24 * 60 * 60
    nb_jour_quantiles_secondes = nb_jour_quantiles * 24 * 60 * 60

    nb_bougies_ecart_relatif = math.ceil(nb_jours_arriere_secondes / secondes_par_bougie)
    nb_bougies_mm = math.ceil(nb_jour_mm_secondes / secondes_par_bougie)
    nb_bougies_quantiles = math.ceil(nb_jour_quantiles_secondes / secondes_par_bougie)

    # Utilise apply pour rolling sur chaque colonne indépendamment !
    haut_glissant = df_close.apply(lambda s: s.rolling(nb_bougies_ecart_relatif, min_periods=1).max())
    bas_glissant = df_close.apply(lambda s: s.rolling(nb_bougies_ecart_relatif, min_periods=1).min())


    ecart_relatif = (haut_glissant - bas_glissant) / bas_glissant


    mm_ecart_relatif = ecart_relatif.apply(lambda s: s.rolling(nb_bougies_mm, min_periods=1).mean())


    quantile_glissant_bas_ecart_relatif = ecart_relatif.apply(lambda s: calculs_quantiles_nearestrank(s, quantile_bas, nb_bougies_quantiles, False))

    quantile_glissant_haut_ecart_relatif = ecart_relatif.apply(lambda s: calculs_quantiles_nearestrank(s, quantile_haut, nb_bougies_quantiles, False))


    quantile_cumulatif_bas_ecart_relatif = ecart_relatif.apply(lambda s: calculs_quantiles_nearestrank(s, quantile_bas, nb_bougies_quantiles, True))
    quantile_cumulatif_haut_ecart_relatif = ecart_relatif.apply(lambda s: calculs_quantiles_nearestrank(s, quantile_haut, nb_bougies_quantiles, True))

    dfs = {
        "ecart_relatif": ecart_relatif,
        "mm_ecart_relatif": mm_ecart_relatif,
        "qbas_glissant_ecart_relatif": quantile_glissant_bas_ecart_relatif,
        "qhaut_glissant_ecart_relatif": quantile_glissant_haut_ecart_relatif,
        "qbas_cumul_ecart_relatif": quantile_cumulatif_bas_ecart_relatif,
        "qhaut_cumul_ecart_relatif": quantile_cumulatif_haut_ecart_relatif
    }

    df_indicateur = pd.concat(dfs, axis=1)

    df_indicateur = df_indicateur.swaplevel(0, 1, axis=1)
    
    # Optionnel: trier pour retrouver l'ordre d'origine

    return df_indicateur

def rsi_avec_quantiles_vectoriel(df_close,length,nombre_annees_quantiles,quantile_haut,quantile_bas,quantile_intermediaire):

    secondes_par_bougie=(df_close.index[1]-df_close.index[0]).total_seconds()
    fenetre_quantile_secondes=nombre_annees_quantiles*365*24*60*60
    
    nb_bougies_quantile=math.ceil(fenetre_quantile_secondes/secondes_par_bougie)

    rsi_df = df_close.apply(lambda col: ta.momentum.rsi(col, window=length))
    
    quantile_haut_glissant_rsi=rsi_df.apply(lambda s:calculs_quantiles_nearestrank(s,quantile_haut,nb_bougies_quantile,False))

    quantile_bas_glissant_rsi=rsi_df.apply(lambda s:calculs_quantiles_nearestrank(s,quantile_bas,nb_bougies_quantile,False))
    
    quantile_intermediaire_glissant_rsi=rsi_df.apply(lambda s:calculs_quantiles_nearestrank(s,quantile_intermediaire,nb_bougies_quantile,False))
    
    quantile_haut_cumulatif_rsi=rsi_df.apply(lambda s:calculs_quantiles_nearestrank(s,quantile_haut,nb_bougies_quantile,True))
    
    quantile_bas_cumulatif_rsi=rsi_df.apply(lambda s:calculs_quantiles_nearestrank(s,quantile_bas,nb_bougies_quantile,True))

    dfs={
        "rsi":rsi_df,
        "quantile_haut_glissant_rsi":quantile_haut_glissant_rsi,
        "quantile_bas_glissant_rsi":quantile_bas_glissant_rsi,
        "quantile_intermediaire_glissant_rsi":quantile_intermediaire_glissant_rsi,
        "quantile_haut_cumulatif_rsi":quantile_haut_cumulatif_rsi,
        "quantile_bas_cumulatif_rsi":quantile_bas_cumulatif_rsi
    }

    df_indicateur=pd.concat(dfs,axis=1)
    df_indicateur = df_indicateur.swaplevel(0, 1, axis=1)
    return df_indicateur

def roi_avec_quantile_vectoriel(df_close, periode_roi_en_jours, quantile_haut, quantile_bas, quantile_bas_prix_achat, quantile_haut_prix_achat, nb_annees_quantiles):

    secondes_par_bougie=(df_close.index[1]-df_close.index[0]).total_seconds()
    fenetre_quantile_secondes=nb_annees_quantiles*365*24*60*60
    periode_roi_secondes=periode_roi_en_jours*24*60*60

    nb_bougies_roi=math.ceil(periode_roi_secondes/secondes_par_bougie)
    nb_bougies_quantile=math.ceil(fenetre_quantile_secondes/secondes_par_bougie)

    prix_bas=df_close.apply(lambda s:calculs_quantiles_nearestrank(s,quantile_bas_prix_achat,nb_bougies_roi,False))
    prix_haut=df_close.apply(lambda s:calculs_quantiles_nearestrank(s,quantile_haut_prix_achat,nb_bougies_roi,False))

    roi_hausse=(df_close-prix_bas)/prix_bas
    roi_hausse=roi_hausse.where(roi_hausse>0,np.nan)


    roi_baisse=(df_close-prix_haut)/prix_haut
    roi_baisse=roi_baisse.where(roi_baisse<0,np.nan)

    quantile_haut_glissant_roi=roi_hausse.apply(lambda s:calcul_quantile_roi_glissant(s,quantile_haut,nb_bougies_quantile))
    quantile_haut_cumulatif_roi=roi_hausse.apply(lambda s:calcul_quantiles_roi_cumulatifs(s,quantile_haut))

    quantile_bas_glissant_roi=roi_baisse.apply(lambda s:calcul_quantile_roi_glissant(s,quantile_bas,nb_bougies_quantile))
    quantile_bas_cumulatif_roi=roi_baisse.apply(lambda s:calcul_quantiles_roi_cumulatifs(s,quantile_bas))

    dfs={
        "roi_hausse":roi_hausse,
        "roi_baisse":roi_baisse,
        "quantile_haut_glissant_roi":quantile_haut_glissant_roi,
        "quantile_haut_cumulatif_roi":quantile_haut_cumulatif_roi,
        "quantile_bas_glissant_roi":quantile_bas_glissant_roi,
        "quantile_bas_cumulatif_roi":quantile_bas_cumulatif_roi
    }

    df_indicateurs=pd.concat(dfs,axis=1)
    df_indicateurs=df_indicateurs.swaplevel(0,1,axis=1)
    return df_indicateurs