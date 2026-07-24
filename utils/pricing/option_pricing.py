
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

def plotly_option_vs_stock(K, T, r, sigma, option_type="call",n_min=1,n_max=500):
    liste_S0=[]
    liste_price=[]

    for price in range(n_min,n_max+1,1):
        liste_S0.append(price)
        liste_price.append(black_scholes_option_price(price,K,T,r,sigma,option_type))
    

    line={
        "color":"blue",
        "width":3
    }

    fig=plotly.Figure()
    fig.add_scatter(name="Option Price",x=liste_S0,y=liste_price,line=line)

    fig.update_layout(
        title="Option Price vs Stock Price",
        xaxis_title="Stock Price (S0)",
        yaxis_title="Option Price",
        showlegend=True,
        template="plotly_white",
        hovermode="x unified"
    )
    return fig


# %%
def bs_greeks_df(S0, K, T, r, sigma, option_type="call"):

    d1 = (np.log(S0 / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    gamma = norm.pdf(d1) / (S0 * sigma * np.sqrt(T))
    vega = S0 * norm.pdf(d1) * np.sqrt(T) / 100
    # Vega /100 = impact pour +1 point de volatilité, ex: 20% -> 21%

    if option_type == "call":
        delta = norm.cdf(d1)

        theta_annual = (
            -S0 * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
            - r * K * np.exp(-r * T) * norm.cdf(d2)
        )

        rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100

    elif option_type == "put":
        delta = norm.cdf(d1) - 1

        theta_annual = (
            -S0 * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
            + r * K * np.exp(-r * T) * norm.cdf(-d2)
        )

        rho = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100

    else:
        raise ValueError("option_type must be 'call' or 'put'")

    theta_daily = theta_annual / 365

    return pd.DataFrame(
        {
            "Greek": ["Delta", "Gamma", "Theta", "Vega", "Rho"],
            "Value": [delta, gamma, theta_daily, vega, rho],
            "Unit": [
                "per +1 unit of S0",
                "per +1 unit of S0",
                "per calendar day",
                "per +1 volatility point",
                "per +1 interest rate point",
            ],
        }
    )

# %%
def greeks_S0(K, T, r, sigma, option_type="call",n_min=1,n_max=500):
    liste_S0=[]
    liste_delta=[]
    liste_gamma=[]
    liste_theta=[]
    liste_vega=[]
    liste_rho=[]

    for price in range(n_min,n_max+1,1):
        df=bs_greeks_df(price, K, T, r, sigma, option_type=option_type)
        liste_S0.append(price)
        liste_delta.append(df.loc[df["Greek"]=="Delta","Value"].iloc[0])
        liste_gamma.append(df.loc[df["Greek"]=="Gamma","Value"].iloc[0])
        liste_theta.append(df.loc[df["Greek"]=="Theta","Value"].iloc[0])
        liste_vega.append(df.loc[df["Greek"]=="Vega","Value"].iloc[0])
        liste_rho.append(df.loc[df["Greek"]=="Rho","Value"].iloc[0])
    
    dico={
        "Stock Price":liste_S0,
        "Delta":liste_delta,
        "Gamma":liste_gamma,
        "Theta":liste_theta,
        "Vega":liste_vega,
        "Rho":liste_rho,
    }

    df=pd.DataFrame(dico)
    return df

# %%
def plotly_greeks_S0(df,K):
    
    dico_graphs={}
    df=df.copy()
    df=df.set_index("Stock Price")
    greeks=df.columns.tolist()

    line={
        "color":"blue",
        "width":3
    }

    for greek in greeks:
        serie=df[greek]
        fig=plotly.Figure()
        fig.add_scatter(name=greek,x=serie.index,y=serie.values,mode="lines",line=line)
        fig.add_vline(
            x=K,
            line_color="grey",
            line_dash="dash",
            annotation_text="Strike",
            annotation_position="top"
        )
        fig.update_layout(
            title= f"{greek} vs. Stock Price",
            xaxis_title="Stock Price (S0)",
            yaxis_title=greek,
            showlegend=True,
            template="plotly_white",
            hovermode="x unified"
        )
        dico_graphs[greek]=fig
    
    return dico_graphs
        
        




