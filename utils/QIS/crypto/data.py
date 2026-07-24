import requests
import pandas as pd
import time

from datetime import datetime, timedelta
import streamlit as st

from gate_api import Configuration, ApiClient, SpotApi



# %% API CMC

def get_top_cmc(debut_classement=0,fin_classement=5000):
#Renvoie la liste des cryptos de CMC classées de debut à fin_classement en fonction du market cap

    url_cmc = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": st.secrets["CMC_API_KEY"]
        }

    parameters = {
        "start": "1",          # point de départ (ex: 1 pour le début)
        "limit": "5000",       # jusqu’à 5000 cryptos
        "convert": "USD"       # pour avoir les prix en USD
    }

    response = requests.get(url_cmc, headers=headers, params=parameters)
    data = response.json()
    top=pd.DataFrame(data["data"])

    if debut_classement==0:
        top=top.iloc[:fin_classement]["symbol"].to_list()
    else:
        top=top.iloc[debut_classement:fin_classement]["symbol"].to_list()

    return top

def recup_top_passe(date_str_sans_slash,classement_debut=0,classement_fin=199):

    #comme get_top_cmc mais prend le classement d'une date passée, 
    # #mettre la date en format annee mois jours sans séparation et en str

    url=f"https://coinmarketcap.com/fr/historical/{date_str_sans_slash}/"
    tables=pd.read_html(url)
    df=tables[2]

    serie_symbols_dispo=df["Symbole"].dropna()

    url_cmc = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": st.secrets["CMC_API_KEY"]
    }

    parameters = {
        "start": "1",          # point de départ (ex: 1 pour le début)
        "limit": "2000",       # jusqu’à 5000 cryptos
        "convert": "USD"       # pour avoir les prix en USD
    }

    response = requests.get(url_cmc, headers=headers, params=parameters)
    data = response.json()
    dfl=pd.DataFrame(data["data"])

    df_top100=df.iloc[20:]["Nom"].to_frame().reset_index(drop=True)
    df_top100.columns=["name"]
    
    dfl=dfl[["name","symbol"]]
    df_final=df_top100.merge(dfl,on="name",how="left")

    serie_finale=pd.concat([serie_symbols_dispo,df_final["symbol"]])
    liste=serie_finale.to_list()
    if classement_debut==0:
        return liste[classement_debut:classement_fin+1]
    else:
        return liste[classement_debut+1:classement_fin+1]

    
def get_close_multiindex(secteurs):

    #A pârtir d'une liste de sceteurs coingecko renvoie un df multiindex en colonnes, dans l'ordre: classe_capi (high mcap, mid, low), secteur, crypto

    paires_gate=get_pairs_gate()

    dico_all={}

    for secteur in secteurs:

        liste_crypto=get_premiers_tokens_cate_mcap(secteur)

        for crypto,capi in liste_crypto.items():
            
            nom = str(crypto).lower()
            if ("usd" in nom) or ("dai" in nom):
                continue  # On saute cette crypto

            if f"{crypto}_USDT" in paires_gate:

                classe_capi=get_capi_class(capi)
                df_crypto=hist_prix_gate_simple(crypto)
                
                if not df_crypto.empty:
                    dico_all[(classe_capi,secteur,crypto)]=df_crypto["close"]

    df_close=pd.DataFrame(dico_all)
    df_close.columns=pd.MultiIndex.from_tuples(df_close.columns,names=["classe_capi","secteur","crypto"])

    return df_close

# %% API Coingecko

def id_categories_coin_gecko():
    cate="https://api.coingecko.com/api/v3/coins/categories"
    categories=requests.get(cate)
    categories=categories.json()
    #On obtient une liste de dictionnaires. Chaque dictionnaire donne plein d'infos sur la catégroie en question.
    # l'id associé à une catégorie d'actif est la valeur associée à la clé "id" pour chaque dicionnaire.

    liste_cate=[]
    for element in categories:
        liste_cate.append(element["id"])
    return liste_cate

def get_premiers_tokens_cate(categorie):

    # Renvoie les 250 premiers tokens en terme de MCAP d'une catégorie coingecko
    id_cate=id_categories_coin_gecko()

    if categorie not in id_cate:
            raise ValueError("la catégorie renseignée ne correspons à celles existantes chez coingecko: vérifier l'orthographe")
    
    url="https://api.coingecko.com/api/v3/coins/markets"
    params={
        "vs_currency":"usd",
        f"category":{categorie},
        "per_page":250
    }

    data=requests.get(url,params=params)
    data=data.json()

    liste_symbol=[]
    for element in data:
        liste_symbol.append(element["symbol"].upper())

    return liste_symbol

def get_premiers_tokens_cate_mcap(categorie):
    
    #renvoie les capis des 250 premiers tokens d'une catégorie coingecko
    id_cate=id_categories_coin_gecko()

    if categorie not in id_cate:
            raise ValueError("la catégorie renseignée ne correspons à celles existantes chez coingecko: vérifier l'orthographe")
    
    url="https://api.coingecko.com/api/v3/coins/markets"
    params={
        "vs_currency":"usd",
        f"category":{categorie},
        "per_page":250
    }

    data=requests.get(url,params=params)
    data=data.json()

    dico_symbol={}

    for element in data:
        dico_symbol[element["symbol"].upper()]=element["market_cap"]

    return dico_symbol

def get_all_tokens_cate(categorie):

    #Fonction qui beug souvent (en ne renvoyant pas forcément tous les tokens de la caté) 
    # car l'API a des restrictions qui limitent pas mal les requêtes.
    #J'ai donc mis un gros time.sleep donc elle met du temps à s'éxécuter

    import time

    id_cate=id_categories_coin_gecko()

    if categorie not in id_cate:
            raise ValueError("la catégorie renseignée ne correspons à celles existantes chez coingecko: vérifier l'orthographe")
    
    i=1
    data_total=[]
    data=[]
    while i==1 or len(data)==250:

        url="https://api.coingecko.com/api/v3/coins/markets"
        params={
            "vs_currency":"usd",
            f"category":{categorie},
            "per_page":250,
            "page":i
        }

        data=requests.get(url,params=params)
        data=data.json()
        time.sleep(4)
        data_total.extend(data)
        i=i+1
    
    data_total=[element for element in data_total if isinstance(element, dict)]

    liste_symbol=[]
    for element in data_total:
        liste_symbol.append(element["symbol"].upper())

    return liste_symbol


# %% API Gate.io

def get_pairs_gate():
    
    from gate_api import Configuration,ApiClient, SpotApi

    API_key=st.secret["GATE_API_KEY"]
    API_secret=st.secret["GATE_API_SECRET"]

    #Rappel de la connection. On configure un objet Configuration avec les clés API, puis on crée une connexion client avec APIClient, 
    # qu'on met dans une boucle car à la fin la connexion se ferme automatiquement, 
    # puis dans la boucle on se situe à partie SpotAPI du client auquel on est connécté

    config=Configuration(key=API_key,secret=API_secret)
    with ApiClient(config) as client:
        api_client=SpotApi(client)

        list_tickers=api_client.list_tickers()

    #pprint(list_tickers)
    #print(len(list_tickers))

    list_pairs=[]
    for element in list_tickers:

        #On a la particularité que l'objet renvoyé par la requête api_client.list_tickers n'est pas une liste de dico,
        # mais un objet propre à l'API, pour accéder aux différentes clés de cet objet similaire à une liste, on y accède avec .clé, 
        # plutôt qu'avec element["currency_pair"], dans le cas d'un dico
        list_pairs.append(element.currency_pair)
    return list_pairs

def hist_prix_gate_simple(crypto,timeframe="7d"):
    import pandas as pd
    from datetime import datetime
    from gate_api import Configuration, ApiClient, SpotApi

    API_key = st.secret["GATE_API_KEY"]
    API_secret = st.secret["GATE_API_SECRET"]

    config = Configuration(key=API_key, secret=API_secret)
    df_global = pd.DataFrame()

    if timeframe != "1d" and timeframe!="7d" and timeframe!="30d":
        raise ValueError("timeframe prend en argument uniquement '1d', '7d', ou '30d'")
    
    tf = timeframe

    try:
        with ApiClient(config) as client:
            api_client = SpotApi(client)
            paire = f"{crypto}_USDT"

            # Timestamp actuel pour commencer le fetch depuis aujourd'hui vers le passé
            to_timestamp = int(datetime.now().timestamp())

            while True:
                donnees = api_client.list_candlesticks(
                    currency_pair=paire,
                    interval=tf,
                    limit=1000,
                    to=to_timestamp
                )

                if not donnees:
                    break

                for element in donnees:
                    del element[-2:]  # Supprime les champs inutiles

                df = pd.DataFrame(donnees, columns=["date", "volume", "close", "high", "low", "open"])
                df_global = pd.concat([df, df_global], ignore_index=True)  # Concat au début pour ordre chronologique

                if len(donnees) < 1000:
                    break

                # Prépare le timestamp pour la prochaine boucle (date du plus ancien point - 1 sec)
                to_timestamp = int(donnees[0][0]) - 1

        # Traitement du DataFrame
        df_global["close"] = pd.to_numeric(df_global["close"], errors="coerce")
        df_global["date"]=pd.to_datetime(df_global["date"],unit="s")
        df_global.set_index("date", inplace=True)
        df_global.sort_index(inplace=True)

        df_global["return"] = df_global["close"].pct_change()

        return df_global
    
    except Exception as e:
        print(f"Erreur lors de la récupération pour {crypto}: {e}")
        return pd.DataFrame()

def hist_prix_gate_complet(crypto,mode="price",timeframe="daily", date_debut=None,date_fin=None,quantile=0.15):

    from gate_api import Configuration,ApiClient, SpotApi
    from datetime import datetime, timedelta

    if not isinstance(quantile,float) and quantile not in range(0,1):
        raise ValueError("le quantile choisi doit être de type float et compris entre 0 et 1 ")
    
    if timeframe=="daily":
    
        tf="1d"

        if date_debut!= None and date_fin!=None:
            ecart_temps=(date_fin-date_debut).total_seconds()
        ecart_max=1000*60*60*24
        
    elif timeframe=="weekly":
        tf="7d"
        if date_debut!= None and date_fin!=None:
            ecart_temps=(date_fin-date_debut).total_seconds()
        ecart_max=1000*60*60*24*7
    
    elif timeframe=="monthly":
        tf="30d"
        if date_debut!= None and date_fin!=None:
            ecart_temps=(date_fin-date_debut).total_seconds()
        ecart_max=1000*60*60*24*30.44

    else:
        raise ValueError("la timeframe doit être 'daily', 'weekly', ou 'monthly'")


    if date_debut is not None and not isinstance(date_debut, datetime):
        raise TypeError("Le paramètre date_debut doit être un objet datetime.datetime")
    if date_fin is not None and not isinstance(date_fin, datetime):
        raise TypeError("Le paramètre date_fin doit être un objet datetime.datetime")
    
    if  date_debut is not None and date_fin is not None and date_debut>date_fin:
        raise ValueError(" la date de début des données ne doit pas être après celle de fin des données ")
    
    #if date_fin-date_debut >max_days:
        #raise ValueError("la durée entre la date de début et de fin des données ne doit pas excéder 1000 périodes")


    API_key=st.secret["GATE_API_KEY"]
    API_secret=st.secret["GATE_API_SECRET"]

        #Rappel de la connection. On configure un objet Configuration avec les clés API, puis on crée une connexion client avec APIClient, 
        # qu'on met dans une boucle car à la fin la connexion se ferme automatiquement, 
        # puis dans la boucle on se situe à partie SpotAPI du client auquel on est connécté

    if date_debut!=None:
        date_debut=int(date_debut.timestamp())

    if date_fin!= None:
        date_fin=int(date_fin.timestamp())

    config=Configuration(key=API_key,secret=API_secret)
    with ApiClient(config) as client:

        api_client=SpotApi(client)

        paire=f"{crypto}_USDT"    

        if paire not in get_pairs_gate():
            raise ValueError("la crypto mise en argument n'est pas listée sur gate.io")

        #Création du dataframe global qui va être concaténé au fur et à mesure
        df_global=pd.DataFrame()   
        
        #Récupération des premières données:

        if date_debut==None:

            if date_fin==None:

                donnees=api_client.list_candlesticks(paire,interval=tf, limit=1000)
            
            else:
                donnees=api_client.list_candlesticks(paire,interval=tf, limit=1000, to=date_fin) 
            
            for element in donnees:
                del element[-2:]
            
            df=pd.DataFrame(donnees,columns=["date","volume","close","high","low","open"])
            df_global=pd.concat([df,df_global],ignore_index=True)

            while len(df)==1000:

                date_fin=df.iloc[0]["date"]
                donnees=api_client.list_candlesticks(paire,interval=tf, limit=1000, to=date_fin)

                for element in donnees:
                    del element[-2:]
                
                df=pd.DataFrame(donnees,columns=["date","volume","close","high","low","open"])
                df_global=pd.concat([df,df_global],ignore_index=True)

        else: #date_debut != None
                
                if date_fin==None: #et date_debut != None
                    ecart_temps=datetime.now().timestamp()-date_debut

                    if ecart_temps < ecart_max:

                        donnees=api_client.list_candlesticks(paire,interval=tf, _from=date_debut, limit=1000)
                        for element in donnees:
                            del element[-2:]
                        df=pd.DataFrame(donnees,columns=["date","volume","close","high","low","open"])
                        df_global=pd.concat([df,df_global],ignore_index=True)                           
                    
                    else: #ecart_temps>ecart_max

                        donnees=api_client.list_candlesticks(paire,interval=tf, limit=1000)
                        for element in donnees:
                            del element[-2:]
                        df=pd.DataFrame(donnees,columns=["date","volume","close","high","low","open"])
                        df_global=pd.concat([df,df_global],ignore_index=True)                            

                        while len(donnees)==1000:

                            date_fin=int(donnees[0][0])
                            ecart_restant=date_fin-date_debut

                            if ecart_restant<ecart_max:

                                donnees=api_client.list_candlesticks(paire,interval=tf, _from=date_debut, to= date_fin)
                            else:
                                donnees=api_client.list_candlesticks(paire,interval=tf, limit=1000, to= date_fin)

                            for element in donnees:
                                del element[-2:]
                            df=pd.DataFrame(donnees,columns=["date","volume","close","high","low","open"])
                            df_global=pd.concat([df,df_global],ignore_index=True)           
                else: #date_fin!=None et date_début!= None
                    
                    if ecart_temps<ecart_max:
                        donnees=api_client.list_candlesticks(paire,interval=tf, _from=date_debut, to= date_fin)
                        for element in donnees:
                            del element[-2:]
                        df=pd.DataFrame(donnees,columns=["date","volume","close","high","low","open"])
                        df_global=pd.concat([df,df_global],ignore_index=True) 

                    else: #ecart_temps>ecart_max

                        donnees=api_client.list_candlesticks(paire,interval=tf, limit=1000, to= date_fin)
                        for element in donnees:
                            del element[-2:]
                        df=pd.DataFrame(donnees,columns=["date","volume","close","high","low","open"])
                        df_global=pd.concat([df,df_global],ignore_index=True)  

                        while len(donnees)==1000:

                            date_fin=int(donnees[0][0])
                            ecart_restant=date_fin-date_debut

                            if ecart_restant<ecart_max:

                                donnees=api_client.list_candlesticks(paire,interval=tf, _from=date_debut, to= date_fin)

                            else:#ecart_restant>ecart_max

                                donnees=api_client.list_candlesticks(paire,interval=tf, limit=1000, to= date_fin)

                            for element in donnees:
                                del element[-2:]
                            df=pd.DataFrame(donnees,columns=["date","volume","close","high","low","open"])
                            df_global=pd.concat([df,df_global],ignore_index=True)    

        #Puis formatage du df obtennu

        df_global["close"]=pd.to_numeric(df_global["close"],"coerce")
        df_global["date"] = pd.to_datetime(df_global["date"].astype(int), unit="s")

        #df["date"]=df["date"].dt.strftime("%d/%m/%Y")
        df_global.set_index("date",inplace=True)
        df_global["return"]=df_global["close"].pct_change()

        if mode=="price":
            df_global["std_21j_glissant"]=df_global["close"].rolling(21).std()

        elif mode=="return":
            
            df_global["std_21j_glissant"]=df_global["return"].rolling(21).std()
        else:
            raise ValueError("le paramêtre mode donné doit être 'price' ou 'return'")
    
        seuil_acc=df_global["std_21j_glissant"].quantile(quantile)
        seuil_dist=df_global["std_21j_glissant"].quantile(1-quantile)
        df_global["accumulation_period"]=df_global["std_21j_glissant"]<seuil_acc
        df_global["distribution_period"]=df_global["std_21j_glissant"]>seuil_dist
        

    return df_global


# %% Construction Univers

def retirer_stables(df_close):
    """
    Retire toutes les colonnes dont le nom contient 'usd' ou 'dai' (insensible à la casse).
    """
    # Liste des colonnes à garder (qui NE contiennent PAS 'usd' ni 'dai')
    cols_to_keep = [
        col for col in df_close.columns
        if not (("usd" in str(col).lower()) or ("dai" in str(col).lower()))
    ]
    return df_close[cols_to_keep]

def get_close_list(liste):
    
    paires_gate=get_pairs_gate()

    dico_all={}

    for crypto in liste:

        if f"{crypto}_USDT" in paires_gate:

            df_crypto=hist_prix_gate_simple(crypto)
            if not df_crypto.empty:
                dico_all[crypto]=df_crypto["close"]
        
    df_close=pd.DataFrame(dico_all)
    df_close=retirer_stables(df_close)
    return df_close


def tri_close_anciennete(df_close,date_naissance_max,type_df="ancien"):

    """
    fonction qui sert séparer l'univers de cryptos en deux groupes :
    les cryptos déjà suffisamment anciennes à une date donnée ;
    les cryptos encore trop récentes à cette même date.
    et renvoie le df des cryptos vieilles ou jeunes selon le paramêtre type_df donné
    """

    ligne=df_close.loc[date_naissance_max]
    ligne_vieux=ligne[~ligne.isna()]
    ligne_jeune=ligne[ligne.isna()]
    colonnes_vieux=ligne_vieux.index
    colonnes_jeunes=ligne_jeune.index

    df_vieux=df_close[colonnes_vieux]
    df_jeune=df_close[colonnes_jeunes]

    if type_df=="ancien":
        return df_vieux
    elif type_df=="jeune":
        return df_jeune
    else:
        raise ValueError("type_df prend en argument 'ancien' ou 'jeune' uniquement")
    
def retirer_jeunes(df_close, date_reference, duree_min_jours):
    """
    Supprime du DataFrame les colonnes (actifs) dont la durée de vie à partir du 1er prix disponible
    jusqu'à `date_reference` est inférieure à `duree_min_jours`.

    Parameters:
        df_close (pd.DataFrame): DataFrame avec les dates en index (datetime) et les actifs en colonnes.
        date_reference (str ou pd.Timestamp): date de référence pour évaluer la durée de vie.
        duree_min_jours (int): durée minimale de vie souhaitée (en jours).

    Returns:
        pd.DataFrame : df_close réduit aux actifs ayant une durée suffisante.
    """
    import pandas as pd

    # S'assurer que la date est bien de type Timestamp
    date_reference = pd.to_datetime(date_reference)

    # Vérifie que la date de référence est bien dans l'index
    if date_reference not in df_close.index:
        raise ValueError("La date de référence n’est pas présente dans l’index du DataFrame.")

    # Récupère toutes les colonnes à conserver
    colonnes_a_conserver = []
    for col in df_close.columns:
        serie = df_close[col].dropna()
        if serie.empty:
            continue
        premiere_date = serie.index[0]
        if date_reference >= premiere_date:
            duree = (date_reference - premiere_date).days
            if duree >= duree_min_jours:
                colonnes_a_conserver.append(col)

    # Retourne le sous-DataFrame filtré
    return df_close[colonnes_a_conserver]

def get_capi_class(capi):
    if capi >= 2e9: return "largecap"
    elif capi>=650e8: return "midcap"
    elif capi>=2e8: return "smallcap"
    else: return "microcap"

def get_close_multiindex(secteurs):

    paires_gate=get_pairs_gate()

    dico_all={}

    for secteur in secteurs:

        liste_crypto=get_premiers_tokens_cate_mcap(secteur)

        for crypto,capi in liste_crypto.items():
            
            nom = str(crypto).lower()
            if ("usd" in nom) or ("dai" in nom):
                continue  # On saute cette crypto

            if f"{crypto}_USDT" in paires_gate:

                classe_capi=get_capi_class(capi)
                df_crypto=hist_prix_gate_simple(crypto)
                
                if not df_crypto.empty:
                    dico_all[(classe_capi,secteur,crypto)]=df_crypto["close"]

    df_close=pd.DataFrame(dico_all)
    df_close.columns=pd.MultiIndex.from_tuples(df_close.columns,names=["classe_capi","secteur","crypto"])

    return df_close
