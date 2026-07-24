import numpy as np
import pandas as pd
import vectorbt as vbt


from utils.QIS.crypto.signals import (
    signaux_achats,
    signaux_vente,
    signaux_vente_decomposee,
    signaux_vente_v3_decomposee,
)

from utils.QIS.crypto.params import ensure_params_v3

def backtest(df_close, params, fees=0.002, retirer_trades_non_closed=True):
    """
    Exécute le backtest et retourne le portfolio, les trades et les signaux.
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
        fees=fees,
        init_cash=100
    )

    trades = portfolio.trades.records_readable

    if retirer_trades_non_closed:
        trades = trades[trades["Status"] == "Closed"].copy()

    trades = mdd_df_trades(trades, df_close)
    trades["duree_jours"] = (trades["Exit Timestamp"] - trades["Entry Timestamp"]).dt.total_seconds() / 86400

    trades = trades.rename(columns={
        "Column": "Asset",
        "Size": "Quantity",
        "Avg Entry Price": "Average Entry Price",
        "Avg Exit Price": "Average Exit Price",
        "PnL": "Profit & Loss",
        "Status": "Trade Status",
        "max_drawdown": "Maximum Drawdown",
        "pnl_mdd": "PnL / Maximum Drawdown",
        "duree_jours": "Holding Period (Days)"
    })

    # Retire les heures, minutes et secondes
    trades["Entry Timestamp"] = pd.to_datetime(trades["Entry Timestamp"]).dt.date
    trades["Exit Timestamp"] = pd.to_datetime(trades["Exit Timestamp"], errors="coerce").dt.date

    # Colonnes conservées et ordre d'affichage
    useful_columns = [
        "Asset",
        "Quantity",
        "Entry Timestamp",
        "Average Entry Price",
        "Entry Fees",
        "Exit Timestamp",
        "Average Exit Price",
        "Exit Fees",
        "Profit & Loss",
        "Return",
        "Direction",
        "Trade Status",
        "Maximum Drawdown",
        "PnL / Maximum Drawdown",
        "Holding Period (Days)"
    ]

    trades = trades[[column for column in useful_columns if column in trades.columns]]

    return {
        "portfolio": portfolio,
        "trades": trades,
        "buy_signals": df_signaux_achats,
        "sell_signals": df_signaux_vente
    }


def backtest_mono_signaux_sur_echantillon(
    df_multi,
    df_single,
    params,
    freq="1w"
):
    """
    Applique les signaux générés sur un actif unique (df_single) à un DataFrame multi-actifs (df_multi),
    puis exécute le backtest sur chaque actif avec ces signaux identiques.
    """
    # 1. Signaux achat
    df_signaux_achats = signaux_achats(
        df_single,
        params_volat_achat=params["params_volat_achat"],
        params_ecart_relatif=params["params_ecart_relatif"],
        critere_rsi=params["critère_rsi_achat"]
    )
    if isinstance(df_signaux_achats, pd.DataFrame):
        serie_achats = df_signaux_achats.iloc[:, 0]
    else:
        serie_achats = df_signaux_achats

    serie_achats.name = None  # <-- Important fix

    # 2. Signaux vente
    df_signaux_ventes = signaux_vente(
        df_single,
        params["params_volat_vente"],
        params["params_rsi"],
        params["params_roi"]
    )
    if isinstance(df_signaux_ventes, pd.DataFrame):
        serie_ventes = df_signaux_ventes.iloc[:, 0]
    else:
        serie_ventes = df_signaux_ventes

    serie_ventes.name = None  # <-- Important fix

    # 3. Réplication
    entries_multi = pd.concat([serie_achats] * df_multi.shape[1], axis=1)
    exits_multi = pd.concat([serie_ventes] * df_multi.shape[1], axis=1)

    entries_multi.columns = df_multi.columns
    exits_multi.columns = df_multi.columns

    # 4. Alignement index
    entries_multi = entries_multi.reindex(df_multi.index).fillna(False)
    exits_multi = exits_multi.reindex(df_multi.index).fillna(False)
    


    # 5. Backtest vectorbt
    portfolio = vbt.Portfolio.from_signals(
        close=df_multi,
        entries=entries_multi,
        exits=exits_multi,
        freq=freq
    )

    return portfolio

def _to_df(x):
    if isinstance(x, pd.Series):
        name = x.name or "asset"
        return x.to_frame(name=name)
    return x

def _to_1d(s_or_df):

    """Series -> Series; DataFrame -> sum columns (1D)."""
    if isinstance(s_or_df, pd.DataFrame):
        return s_or_df.sum(axis=1)
    return s_or_df

def portfolio_fractionne(
    df_close,
    params,
    init_cash: float = 1000,
    buy_cash_frac: float = 0.20,   # 20% du cash APRÈS la dernière vente (budget fixe par achat)
    sell_pos_frac: float = 0.20,   # % pour déterminer la QUANTITÉ du 1er SELL (puis répétée)
    fee_rate: float = 0.002,
    priorite: str = "vente",       # "vente" ou "achat" si les deux le même jour
    min_cash_eps: float = 0,
    min_units_eps: float = 0,
    freq: str = "1w",
):
    # 0) Prix mono/multi-actifs
    close_df = _to_df(df_close).astype(float)
    if close_df.shape[1] == 1 and close_df.columns[0] != "close":
        close_df = close_df.rename(columns={close_df.columns[0]: "close"})

    # 1) Signaux
    buys_df = signaux_achats(
        close_df,
        params_volat_achat=params["params_volat_achat"],
        params_ecart_relatif=params["params_ecart_relatif"],
        critere_rsi=params["critère_rsi_achat"],
    )
    sells_df = signaux_vente(
        close_df,
        params_volat_vente=params["params_volat_vente"],
        params_rsi=params["params_rsi"],
        params_roi=params["params_roi"],
    )

    # 2) Alignement des masques
    buys_df  = _to_df(buys_df).astype(bool).reindex_like(close_df).fillna(False)
    sells_df = _to_df(sells_df).astype(bool).reindex_like(close_df).fillna(False)

    idx, cols = close_df.index, close_df.columns
    mono = (len(cols) == 1)
    col0 = cols[0] if mono else None

    # 3) États
    cash_vec = pd.Series(init_cash, index=cols, dtype=float)
    units    = pd.Series(0.0,       index=cols, dtype=float)

    # 4) Ancrages
    cash_anchor_after_last_sell = pd.Series(init_cash, index=cols, dtype=float)
    fixed_buy_budget_ttc        = buy_cash_frac * cash_anchor_after_last_sell  # budget TTC constant par achat
    fixed_sell_units            = pd.Series(float("nan"), index=cols, dtype=float)  # quantité du 1er sell à répéter

    # 5) Ordres (UNITÉS signées)
    sizes = pd.DataFrame(0.0, index=idx, columns=cols, dtype=float)
    phase_order = ("sell", "buy") if priorite == "vente" else ("buy", "sell")

    for t in idx:
        px_row = close_df.loc[t].astype(float)

        for phase in phase_order:
            if phase == "sell":
                mask_row = sells_df.loc[t]

                if mono:
                    if not bool(mask_row.iloc[0]):
                        continue
                    # 1er SELL de la séquence → ancrer la quantité vendue
                    if pd.isna(fixed_sell_units[col0]):
                        if units[col0] <= min_units_eps:
                            continue
                        u_init = sell_pos_frac * units[col0]
                        if u_init <= min_units_eps:
                            continue
                        u_sell = min(u_init, units[col0])
                        sizes.at[t, col0] -= u_sell
                        units[col0]       -= u_sell
                        cash_vec[col0]    += u_sell * px_row[col0] * (1.0 - fee_rate)
                        fixed_sell_units[col0] = u_sell
                    else:
                        if units[col0] <= min_units_eps:
                            continue
                        u_sell = min(fixed_sell_units[col0], units[col0])
                        if u_sell <= min_units_eps:
                            continue
                        sizes.at[t, col0] -= u_sell
                        units[col0]       -= u_sell
                        cash_vec[col0]    += u_sell * px_row[col0] * (1.0 - fee_rate)

                    # ré‑ancre cash → budget fixe d’achats
                    cash_anchor_after_last_sell[col0] = cash_vec[col0]
                    fixed_buy_budget_ttc[col0]        = buy_cash_frac * cash_anchor_after_last_sell[col0]


                else:
                    for c in cols:
                        if not bool(mask_row.get(c, False)):
                            continue
                        if pd.isna(fixed_sell_units[c]):
                            if units[c] <= min_units_eps:
                                continue
                            u_init = sell_pos_frac * units[c]
                            if u_init <= min_units_eps:
                                continue
                            u_sell = min(u_init, units[c])
                            sizes.at[t, c] -= u_sell
                            units[c]       -= u_sell
                            cash_vec[c]    += u_sell * px_row[c] * (1.0 - fee_rate)
                            fixed_sell_units[c] = u_sell
                        else:
                            if units[c] <= min_units_eps:
                                continue
                            u_sell = min(fixed_sell_units[c], units[c])
                            if u_sell <= min_units_eps:
                                continue
                            sizes.at[t, c] -= u_sell
                            units[c]       -= u_sell
                            cash_vec[c]    += u_sell * px_row[c] * (1.0 - fee_rate)
                        cash_anchor_after_last_sell[c] = cash_vec[c]
                        fixed_buy_budget_ttc[c]        = buy_cash_frac * cash_anchor_after_last_sell[c]

            else:  # BUY
                mask_row = buys_df.loc[t]

                if mono:
                    if not bool(mask_row.iloc[0]) or px_row[col0] <= 0:
                        continue
                    budget_ttc = min(fixed_buy_budget_ttc[col0], cash_vec[col0])
                    if budget_ttc <= min_cash_eps:
                        continue
                    units_to_buy = budget_ttc / (px_row[col0] * (1.0 + fee_rate))
                    if units_to_buy <= min_units_eps:
                        continue
                    sizes.at[t, col0] += units_to_buy
                    units[col0]       += units_to_buy
                    cash_vec[col0]    -= budget_ttc
                    fixed_sell_units[col0] = float("nan")  # nouvel achat → reset ancrage vente
                else:
                    for c in cols:
                        if not bool(mask_row.get(c, False)) or px_row[c] <= 0:
                            continue
                        budget_ttc = min(fixed_buy_budget_ttc[c], cash_vec[c])
                        if budget_ttc <= min_cash_eps:
                            continue
                        units_to_buy = budget_ttc / (px_row[c] * (1.0 + fee_rate))
                        if units_to_buy <= min_units_eps:
                            continue
                        sizes.at[t, c] += units_to_buy
                        units[c]       += units_to_buy
                        cash_vec[c]    -= budget_ttc
                        fixed_sell_units[c] = float("nan")

    # 6) Portfolio — INTERPRÉTER size EN UNITÉS !
    pf = vbt.Portfolio.from_orders(
        close=close_df,
        size=sizes,   # <-- crucial
        direction="longonly",
        fees=fee_rate,
        init_cash=init_cash,
        cash_sharing=False,
        freq=freq,
    )
    return pf

def portfolio_fractionne_v2(
    df_close,
    params,
    init_cash: float = 1000.0,
    buy_cash_frac: float = 0.20,        # % du cash "ancré après dernière vente" dépensé par achat (budget TTC fixe)
    sell_pos_frac_3on3: float = 0.20,   # 20% du stock ANCRÉ post-achat (pour 3/3)
    sell_pos_frac_2on3: float = 0.05,   # 5% du stock ANCRÉ post-achat (pour 2/3)
    x_streak_2on3: int = 2,             # nb de bougies consécutives ==2/3 avant 1ère vente 2/3 (et avant chaque vente 2/3)
    x_gap_2on3: int = 2,                # nb de bougies mini entre deux ventes 2/3
    fee_rate: float = 0.0005,
    priorite: str = "vente",            # "vente" ou "achat" si les deux le même jour
    min_cash_eps: float = 0.0,
    min_units_eps: float = 0.0,
    freq: str = "1w",
):
    import numpy as np
    import pandas as pd

    close_df = _to_df(df_close).astype(float)
    if close_df.shape[1] == 1 and close_df.columns[0] != "close":
        close_df = close_df.rename(columns={close_df.columns[0]: "close"})

    # 1) Signaux
    buys_df = signaux_achats(
        close_df,
        params_volat_achat=params["params_volat_achat"],
        params_ecart_relatif=params["params_ecart_relatif"],
        critere_rsi=params["critère_rsi_achat"],
    ).reindex_like(close_df).fillna(False)

    sigs = signaux_vente_decomposee(
        close_df,
        params_volat_vente=params["params_volat_vente"],
        params_rsi=params["params_rsi"],
        params_roi=params["params_roi"],
    )
    count_df   = sigs["count"].reindex_like(close_df).fillna(0).astype(int)
    mask3_df   = sigs["mask_3sur3"].reindex_like(close_df).fillna(False)
    mask2_raw  = sigs["mask_2sur3"].reindex_like(close_df).fillna(False)

    idx, cols = close_df.index, close_df.columns
    mono = (len(cols) == 1)
    col0 = cols[0] if mono else None

    # 2) États par actif
    cash_vec = pd.Series(init_cash, index=cols, dtype=float)
    units    = pd.Series(0.0,       index=cols, dtype=float)

    # 3) Ancrages
    # -- achats: budget TTC fixe basé sur le cash après la DERNIÈRE VENTE
    cash_anchor_after_last_sell = pd.Series(init_cash, index=cols, dtype=float)
    fixed_buy_budget_ttc        = buy_cash_frac * cash_anchor_after_last_sell

    # -- ventes: base de calcul = STOCK D'ACTIFS juste après le DERNIER ACHAT
    stock_init_post_buy = pd.Series(0.0, index=cols, dtype=float)

    # 4) Suivi règles 2/3
    pos_of_idx = {t: i for i, t in enumerate(idx)}
    streak_2   = pd.Series(0, index=cols, dtype=int)         # streak de bougies consécutives avec exactement 2/3
    last_sell2_pos = pd.Series(-10**9, index=cols, dtype=int) # dernière vente 2/3 (en positions d'index)

    # 5) Ordres en UNITÉS signées
    sizes = pd.DataFrame(0.0, index=idx, columns=cols, dtype=float)

    phase_order = ("sell", "buy") if priorite == "vente" else ("buy", "sell")

    for t in idx:
        px_row = close_df.loc[t].astype(float)
        i_pos  = pos_of_idx[t]

        for phase in phase_order:

            if phase == "sell":
                # Traitement VENTES : on traite d'abord 3/3, puis 2/3
                if mono:
                    c = col0
                    nb = int(count_df.loc[t, c])
                    # === 3/3 : vente 20% du stock ANCRÉ post-achat ===
                    if nb == 3:
                        if units[c] > min_units_eps and stock_init_post_buy[c] > min_units_eps and px_row[c] > 0:
                            u_sell_base = sell_pos_frac_3on3 * stock_init_post_buy[c]
                            u_sell = min(u_sell_base, units[c])
                            if u_sell > min_units_eps:
                                sizes.at[t, c] -= u_sell
                                units[c]       -= u_sell
                                cash_vec[c]    += u_sell * px_row[c] * (1.0 - fee_rate)
                                # Achat futur: ré-ancrer le budget TTC
                                cash_anchor_after_last_sell[c] = cash_vec[c]
                                fixed_buy_budget_ttc[c]        = buy_cash_frac * cash_anchor_after_last_sell[c]
                        # Dans tous les cas, un 3/3 "casse" la séquence 2/3
                        streak_2[c] = 0

                    # === 2/3 : vente 5% du stock ANCRÉ post-achat, sous conditions ===
                    elif nb == 2:
                        # streak (consécutif exactement 2/3)
                        streak_2[c] += 1
                        # Conditions: streak OK + gap OK
                        if streak_2[c] >= x_streak_2on3:
                            if (i_pos - last_sell2_pos[c]) >= x_gap_2on3:
                                if units[c] > min_units_eps and stock_init_post_buy[c] > min_units_eps and px_row[c] > 0:
                                    u_sell_base = sell_pos_frac_2on3 * stock_init_post_buy[c]
                                    u_sell = min(u_sell_base, units[c])
                                    if u_sell > min_units_eps:
                                        sizes.at[t, c] -= u_sell
                                        units[c]       -= u_sell
                                        cash_vec[c]    += u_sell * px_row[c] * (1.0 - fee_rate)
                                        last_sell2_pos[c] = i_pos
                                        # Achat futur: ré-ancrer le budget TTC
                                        cash_anchor_after_last_sell[c] = cash_vec[c]
                                        fixed_buy_budget_ttc[c]        = buy_cash_frac * cash_anchor_after_last_sell[c]
                    else:
                        streak_2[c] = 0

                else:
                    # Multi-actifs
                    nb_row = count_df.loc[t]
                    for c in cols:
                        nb = int(nb_row[c])
                        if nb == 3:
                            if units[c] > min_units_eps and stock_init_post_buy[c] > min_units_eps and px_row[c] > 0:
                                u_sell_base = sell_pos_frac_3on3 * stock_init_post_buy[c]
                                u_sell = min(u_sell_base, units[c])
                                if u_sell > min_units_eps:
                                    sizes.at[t, c] -= u_sell
                                    units[c]       -= u_sell
                                    cash_vec[c]    += u_sell * px_row[c] * (1.0 - fee_rate)
                                    cash_anchor_after_last_sell[c] = cash_vec[c]
                                    fixed_buy_budget_ttc[c]        = buy_cash_frac * cash_anchor_after_last_sell[c]
                            streak_2[c] = 0
                        elif nb == 2:
                            streak_2[c] += 1
                            if streak_2[c] >= x_streak_2on3 and (i_pos - last_sell2_pos[c]) >= x_gap_2on3:
                                if units[c] > min_units_eps and stock_init_post_buy[c] > min_units_eps and px_row[c] > 0:
                                    u_sell_base = sell_pos_frac_2on3 * stock_init_post_buy[c]
                                    u_sell = min(u_sell_base, units[c])
                                    if u_sell > min_units_eps:
                                        sizes.at[t, c] -= u_sell
                                        units[c]       -= u_sell
                                        cash_vec[c]    += u_sell * px_row[c] * (1.0 - fee_rate)
                                        last_sell2_pos[c] = i_pos
                                        cash_anchor_after_last_sell[c] = cash_vec[c]
                                        fixed_buy_budget_ttc[c]        = buy_cash_frac * cash_anchor_after_last_sell[c]
                        else:
                            streak_2[c] = 0

            else:
                # Phase BUY — inchangée: budget TTC fixe ancré après la dernière vente
                if mono:
                    c = col0
                    if bool(buys_df.loc[t, c]) and px_row[c] > 0:
                        budget_ttc = min(fixed_buy_budget_ttc[c], cash_vec[c])
                        if budget_ttc > min_cash_eps:
                            u_buy = budget_ttc / (px_row[c] * (1.0 + fee_rate))
                            if u_buy > min_units_eps:
                                sizes.at[t, c] += u_buy
                                units[c]       += u_buy
                                cash_vec[c]    -= budget_ttc
                                # ANCRAGE VENTES: stock juste après CE dernier achat
                                stock_init_post_buy[c] = units[c]
                                # Reset séquence 2/3
                                streak_2[c] = 0
                                last_sell2_pos[c] = -10**9
                else:
                    mask_buy = buys_df.loc[t]
                    for c in cols:
                        if bool(mask_buy.get(c, False)) and px_row[c] > 0:
                            budget_ttc = min(fixed_buy_budget_ttc[c], cash_vec[c])
                            if budget_ttc > min_cash_eps:
                                u_buy = budget_ttc / (px_row[c] * (1.0 + fee_rate))
                                if u_buy > min_units_eps:
                                    sizes.at[t, c] += u_buy
                                    units[c]       += u_buy
                                    cash_vec[c]    -= budget_ttc
                                    stock_init_post_buy[c] = units[c]
                                    streak_2[c] = 0
                                    last_sell2_pos[c] = -10**9

    # 6) Portfolio depuis unités
    pf = vbt.Portfolio.from_orders(
        close=close_df,
        size=sizes,
        direction="longonly",
        fees=fee_rate,
        init_cash=init_cash,
        cash_sharing=False,
        freq=freq,
    )
    return pf

def portfolio_fractionne_v3(
    df_close,
    params,
    init_cash: float = 1000.0,
    buy_cash_frac: float = 0.20,
    sell_pos_frac_A: float = 0.20,
    sell_pos_frac_B: float = 0.05,
    fee_rate: float = 0.002,
    priorite: str = "vente",
    min_cash_eps: float = 0.0,
    min_units_eps: float = 0.0,
    freq: str = "1w",
):
    p = ensure_params_v3(params)

    close_df = _to_df(df_close).astype(float)
    if close_df.shape[1] == 1 and close_df.columns[0] != "close":
        close_df = close_df.rename(columns={close_df.columns[0]: "close"})

    buys_df = signaux_achats(
        close_df,
        params_volat_achat=p["params_volat_achat"],
        params_ecart_relatif=p["params_ecart_relatif"],
        critere_rsi=p["critère_rsi_achat"],
    ).reindex_like(close_df).fillna(False)

    sigs = signaux_vente_v3_decomposee(
        close_df,
        params_rsi=p["params_rsi"],
        params_roi_1=p["params_roi_1"],
        params_roi_2=p["params_roi_2"],
    )
    mask_A = sigs["mask_A"].reindex_like(close_df).fillna(False)
    mask_B = sigs["mask_B"].reindex_like(close_df).fillna(False)

    idx, cols = close_df.index, close_df.columns
    mono = (len(cols) == 1); col0 = cols[0] if mono else None

    cash_vec = pd.Series(init_cash, index=cols, dtype=float)
    units    = pd.Series(0.0,       index=cols, dtype=float)

    cash_anchor_after_last_sell = pd.Series(init_cash, index=cols, dtype=float)
    fixed_buy_budget_ttc        = buy_cash_frac * cash_anchor_after_last_sell
    stock_init_post_buy         = pd.Series(0.0, index=cols, dtype=float)

    sizes = pd.DataFrame(0.0, index=idx, columns=cols, dtype=float)
    phase_order = ("sell", "buy") if priorite == "vente" else ("buy", "sell")

    for t in idx:
        px_row = close_df.loc[t].astype(float)

        for phase in phase_order:
            if phase == "sell":
                if mono:
                    c = col0
                    if bool(mask_A.loc[t, c]) and units[c] > min_units_eps and stock_init_post_buy[c] > min_units_eps:
                        u_base = sell_pos_frac_A * stock_init_post_buy[c]
                        u_sell = min(u_base, units[c])   # liquide tout le reste si < u_base
                        if u_sell > min_units_eps:
                            sizes.at[t, c] -= u_sell
                            units[c]       -= u_sell
                            cash_vec[c]    += u_sell * px_row[c] * (1 - fee_rate)
                            cash_anchor_after_last_sell[c] = cash_vec[c]
                            fixed_buy_budget_ttc[c]        = buy_cash_frac * cash_anchor_after_last_sell[c]

                    if bool(mask_B.loc[t, c]) and units[c] > min_units_eps and stock_init_post_buy[c] > min_units_eps:
                        u_base = sell_pos_frac_B * stock_init_post_buy[c]
                        u_sell = min(u_base, units[c])
                        if u_sell > min_units_eps:
                            sizes.at[t, c] -= u_sell
                            units[c]       -= u_sell
                            cash_vec[c]    += u_sell * px_row[c] * (1 - fee_rate)
                            cash_anchor_after_last_sell[c] = cash_vec[c]
                            fixed_buy_budget_ttc[c]        = buy_cash_frac * cash_anchor_after_last_sell[c]

                else:
                    maskA_row = mask_A.loc[t]; maskB_row = mask_B.loc[t]
                    for c in cols:
                        if bool(maskA_row.get(c, False)) and units[c] > min_units_eps and stock_init_post_buy[c] > min_units_eps:
                            u_base = sell_pos_frac_A * stock_init_post_buy[c]
                            u_sell = min(u_base, units[c])
                            if u_sell > min_units_eps:
                                sizes.at[t, c] -= u_sell
                                units[c]       -= u_sell
                                cash_vec[c]    += u_sell * px_row[c] * (1 - fee_rate)
                                cash_anchor_after_last_sell[c] = cash_vec[c]
                                fixed_buy_budget_ttc[c]        = buy_cash_frac * cash_anchor_after_last_sell[c]
                        if bool(maskB_row.get(c, False)) and units[c] > min_units_eps and stock_init_post_buy[c] > min_units_eps:
                            u_base = sell_pos_frac_B * stock_init_post_buy[c]
                            u_sell = min(u_base, units[c])
                            if u_sell > min_units_eps:
                                sizes.at[t, c] -= u_sell
                                units[c]       -= u_sell
                                cash_vec[c]    += u_sell * px_row[c] * (1 - fee_rate)
                                cash_anchor_after_last_sell[c] = cash_vec[c]
                                fixed_buy_budget_ttc[c]        = buy_cash_frac * cash_anchor_after_last_sell[c]

            else:  # BUY
                if mono:
                    c = col0
                    if bool(buys_df.loc[t, c]) and px_row[c] > 0:
                        budget_ttc = min(fixed_buy_budget_ttc[c], cash_vec[c])
                        if budget_ttc > min_cash_eps:
                            u_buy = budget_ttc / (px_row[c] * (1 + fee_rate))
                            if u_buy > min_units_eps:
                                sizes.at[t, c] += u_buy
                                units[c]       += u_buy
                                cash_vec[c]    -= budget_ttc
                                stock_init_post_buy[c] = units[c]
                else:
                    buy_row = buys_df.loc[t]
                    for c in cols:
                        if bool(buy_row.get(c, False)) and px_row[c] > 0:
                            budget_ttc = min(fixed_buy_budget_ttc[c], cash_vec[c])
                            if budget_ttc > min_cash_eps:
                                u_buy = budget_ttc / (px_row[c] * (1 + fee_rate))
                                if u_buy > min_units_eps:
                                    sizes.at[t, c] += u_buy
                                    units[c]       += u_buy
                                    cash_vec[c]    -= budget_ttc
                                    stock_init_post_buy[c] = units[c]

    pf = vbt.Portfolio.from_orders(
        close=close_df,
        size=sizes,
        direction="longonly",
        fees=fee_rate,
        init_cash=init_cash,
        cash_sharing=False,
        freq=freq,
    )
    return pf

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
    
def recup_ordres_strat(ptf):

    ords = ptf.orders.records_readable.copy()

    # 1) Montant de la transaction (en USD par ex)
    ords["Trade_Value"] = ords["Size"] * ords["Price"]

    # Si c'est une vente → cash récupéré (positif)
    # Si c'est un achat → cash utilisé (négatif)
    ords["Cash_Flow"] = ords.apply(lambda row: row["Trade_Value"] if row["Side"] == "Sell" else -row["Trade_Value"], axis=1)

    # 2) Valeur du portefeuille juste après l’ordre
    # `portfolio.value()` donne la valeur totale à chaque timestamp → on mappe par date+colonne
    ptf_value = ptf.value().stack().reset_index()
    ptf_value.columns = ["Timestamp", "Column", "Portfolio_Value"]

    # Fusion pour rattacher la valeur totale à chaque ordre
    ords = ords.merge(ptf_value, on=["Timestamp", "Column"], how="left")

    return ords

def mdd_df_trades(trades_df, df_close):
    # On crée une liste pour stocker chaque MDD
    mdd_list = []
    for _, row in trades_df.iterrows():
        asset = row['Column']
        start = row['Entry Timestamp']
        end = row['Exit Timestamp']
        entry_price = row['Avg Entry Price']
        serie = df_close.loc[start:end, asset]
        mdd = mdd_from_entry(serie, entry_price)
        mdd_list.append(mdd * 100)

    
    # On l’ajoute comme colonne dans le DataFrame
    trades_df = trades_df.copy()
    trades_df['max_drawdown'] = mdd_list
    trades_df['pnl_mdd'] = trades_df['PnL'] / trades_df['max_drawdown'].abs()
    return trades_df


def mdd_from_entry(series, entry_price):
    # Série des drawdowns vs. prix d'entrée
    drawdowns = (series - entry_price) / entry_price
    return drawdowns.min()  # Négatif ou zéro

