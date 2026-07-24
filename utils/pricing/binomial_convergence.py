
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as plotly
from scipy.stats import norm

# %%
def black_scholes_option_price(
    S0,
    K,
    T,
    r,
    sigma,
    option_type,
):
    d1=(np.log(S0/K)+T*(r+sigma**2/2))/(sigma*np.sqrt(T))
    d2=d1-sigma*np.sqrt(T)
    
    call=(S0*norm.cdf(d1))-(K*np.exp(-r*T)*norm.cdf(d2))

    if option_type=="call":
        return call
    
    elif option_type=="put":
        return call+K*np.exp(-r*T)-S0
    else:
        raise ValueError ("option_type must be 'call' or 'put'")


# %%
def binomial_option_price(
    S0,
    K,
    T,
    r,
    sigma,
    N,
    option_type,
    exercise_style,
):
    """
    Price une option avec un arbre binomial CRR.

    Paramètres
    ----------
    S0 : float
        Prix spot du sous-jacent.
    K : float
        Strike.
    T : float
        Maturité en années.
    r : float
        Taux sans risque annualisé en continu.
    sigma : float
        Volatilité annualisée.
    N : int
        Nombre d'étapes de l'arbre.
    option_type : str
        "call" ou "put".
    exercise_style : str
        "european" ou "american".

    Retour
    ------
    float
        Prix de l'option.
    """


    option_type = option_type.lower()
    exercise_style = exercise_style.lower()

    if N <= 0:
        raise ValueError("N must be strictly positive.")
    if T <= 0:
        raise ValueError("T must be strictly positive.")
    if sigma <= 0:
        raise ValueError("sigma must be strictly positive.")
    if option_type not in ["call", "put"]:
        raise ValueError("option_type must be 'call' or 'put'.")
    if exercise_style not in ["european", "american"]:
        raise ValueError("exercise_style must be 'european' or 'american'.")


    dt=T/N
    discount=np.exp(-r*dt)
    u=np.exp(sigma*np.sqrt(dt)) 
    d=1/u
    p=(np.exp(r*dt)-d)/(u-d)

    if not (0 <= p <= 1):
        raise ValueError(
            f"CRR non valid : p={p:.4f}. Increase N(number of steps) or sigma, and/or decrease r."
        )

    #final payoffs calculations

    possible_nb_downs=np.arange(N+1)
    prices=S0*d**possible_nb_downs*u**(N-possible_nb_downs)

    if option_type=="call":
        values=np.maximum(prices-K,0)
    elif option_type=="put":
        values=np.maximum(K-prices,0)
    else:
        raise ValueError("option_type must be call or put")
    
    #loop for each node level

    for step in range(N-1,-1,-1):

        if exercise_style=="european":

            values =discount*(p*values[:-1]+(1-p)*values[1:])
        
        elif exercise_style=="american":

            values =discount*(p*values[:-1]+(1-p)*values[1:])

            if option_type=="call":
                step_nb_downs=np.arange(step+1)
                step_prices=S0*d**step_nb_downs*u**(step-step_nb_downs)
                exercice_value=np.maximum(step_prices-K,0)
                values=np.maximum(exercice_value,values)


            elif option_type=="put":
                step_nb_downs=np.arange(step+1)
                step_prices=S0*d**step_nb_downs*u**(step-step_nb_downs)
                exercice_value=np.maximum(K-step_prices,0)
                values=np.maximum(exercice_value,values)
                
            else:
                raise ValueError("option_type must be call or put")
        else:
            raise ValueError("exercise_style must be american or european")
        
    return values[0]
            

# %%
def binomial_convergence(
    S0,
    K,
    T,
    r,
    sigma,
    option_type,
    exercise_style,
    n_min=1,
    n_max=100,
    step=1,
):
    """
    Calcule le prix binomial pour plusieurs nombres d'étapes N.
    Sert à visualiser la convergence du modèle.
    """

    rows = []
    bs_price=black_scholes_option_price(S0,K,T,r,sigma,option_type)
    
    for N in range(n_min, n_max + 1, step):
        price = binomial_option_price(
            S0=S0,
            K=K,
            T=T,
            r=r,
            sigma=sigma,
            N=N,
            option_type=option_type,
            exercise_style=exercise_style,
        )

        rows.append(
            {
                "N": N,
                "Binomial Price": price,
                "BS Price":bs_price,
                "pricing error (%)":np.abs((price-bs_price)/bs_price)*100
            }
        )

    return pd.DataFrame(rows)

# %%
def plotly_binomial_convergence(df_conv):

    df_bs=df_conv.copy()

    fig=plotly.Figure()
    line_bin={
        "color":"blue",
        "width":2
    }
    line_bs={
        "color":"red",
        "width":3
    }
    markers={
        "color":"blue",
        "size":5
    }

    fig.add_scatter(name="Binomial Price",x=df_conv["N"],y=df_conv["Binomial Price"],mode="lines+markers",line=line_bin,marker=markers)
    fig.add_scatter(name="Black Scholes Price",x=df_bs["N"],y=df_bs["BS Price"],mode="lines",line=line_bs)
    fig.update_layout(
        title="Convergence Graph",
        xaxis_title="Number of steps N",
        yaxis_title="Option Price",
        showlegend=True,
        template="plotly_white",
        hovermode="x unified"
    )

    return fig