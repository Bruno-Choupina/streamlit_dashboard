
project_overview="""

The starting point of this project is the observation that
cryptocurrency markets tend to evolve through pronounced market cycles.
Strong bull markets are often preceded by long accumulation phases,
during which prices remain relatively stable, before entering periods
of rapid appreciation. These expansion phases are generally followed by
significant corrections that retrace a large part of the previous
upward movement.

Based on this observation, the objective of this project was to design
a systematic investment strategy capable of identifying these different
market regimes. More specifically, the strategy attempts to detect
accumulation phases that may offer attractive buying opportunities,
while also identifying periods of excessive optimism that could signal
the end of a bullish trend and justify exiting the market.

To achieve this, several quantitative indicators were developed from
historical price data. These indicators are combined to generate
objective buy and sell signals, which are then evaluated through
historical backtesting.

Since each indicator depends on several parameters, an important part
of the project consists of determining which parameter combinations
produce the most relevant trading signals. Beyond simply evaluating a
trading strategy, this project therefore represents a quantitative
research framework whose objective is to identify historically robust
parameter configurations that may later support future investment
decisions.

This application presents the first version of the project (V0). 
It allows users to interactively configure the strategy parameters 
and investment universe, execute a historical backtest, 
and explore how these choices influence the historical performance of the strategy.
Future versions will extend both the trading logic and the portfolio management methodology.

##### Application Structure

Throughout this page, you will discover each stage of the project's
methodology:

- **Strategy Parameters**  
  Explore the indicators used to generate buy and sell signals,
  understand the intuition behind each of them, and interactively
  modify their parameters.

- **Investment Universe**  
  Select the cryptocurrency universe used during the backtest and
  understand how the choice of assets can influence the results.

- **Backtesting**  
    Understand the assumptions of the historical backtesting methodology, 
    execute the strategy using the selected parameters, analyze the resulting performance statistics, 
    and inspect the individual trades generated throughout the simulation.

- **Strategy Optimization**  
  Discover how different objective functions are used to optimize the
  strategy parameters, compare the resulting optimal configurations,
  and evaluate their impact on the overall performance.

"""

buy_price_vol = """

Periods of accumulation are often characterized by relatively stable price
movements and reduced market activity. The objective of this indicator is to
identify assets whose volatility has become unusually low relative to their
own historical behaviour.

The rolling standard deviation of the closing price is computed over the
selected **Rolling Window** and compared with its historical distribution
over the selected **Historical Window**. The **Lower Volatility Quantile**
defines the threshold below which volatility is considered unusually low.
For example, a value of 0.10 means that the signal is triggered only when
the current rolling volatility belongs to the lowest 10% of historical
observations within the selected Historical Window.

**Buy condition:** Current rolling volatility < historical lower volatility quantile.

"""

buy_relative = r"""

This indicator aims to identify periods during which an asset has been
trading within an unusually narrow price range, which often
characterizes accumulation phases. For each date, the highest and lowest closing prices observed over the
preceding **Rolling Window** are first identified. Their relative
difference is then computed as:

$$
\text{Relative Trading Range}
=
\frac{\text{Highest Price}-\text{Lowest Price}}
{\text{Lowest Price}}
$$

A low value indicates that the asset has experienced little price
dispersion over the selected period, whereas larger values correspond
to wider price fluctuations. To reduce the influence of temporary price movements, a **Moving
Average** of the relative trading range is computed over the selected
**Moving Average Window**. This moving average is then compared with
the historical distribution of the relative trading range computed over
the preceding **Historical Window**. The **Lower Trading Range
Quantile** defines the threshold below which the recent trading range
is considered unusually compressed.

**Buy condition:** Moving Average of Relative Trading Range
< Rolling Lower Historical Quantile.

"""

buy_rsi_confirmation = """

While the previous two indicators identify assets exhibiting
characteristics of an accumulation phase, the Relative Strength Index
(RSI) is used as a final confirmation filter. The Relative Strength Index (RSI) is a widely used momentum indicator
that ranges from 0 to 100 and compares the magnitude of recent gains
and losses. [Learn more about RSI](https://corporatefinanceinstitute.com/resources/career-map/sell-side/capital-markets/relative-strength-index-rsi/?utm_source=chatgpt.com)

In this strategy, it is computed over the preceding
14-day Window, and a buy signal is generated only if the RSI
remains below the selected **RSI Buy Threshold**. Unlike the previous indicators, the RSI does not rely on historical
quantiles. Instead, it prevents buying assets whose prices have already
experienced an excessively strong upward movement over the recent past,
even if the other accumulation indicators are satisfied.

**Buy condition:** 14-day RSI < RSI Buy Threshold

"""

all_buy_indicators="""
##### Price volatility

Periods of accumulation are often characterized by relatively stable price
movements and reduced market activity. The objective of this indicator is to
identify assets whose volatility has become unusually low relative to their
own historical behaviour.

The rolling standard deviation of the closing price is computed over the
selected **Rolling Window** and compared with its historical distribution
over the selected **Historical Window**. The **Lower Volatility Quantile**
defines the threshold below which volatility is considered unusually low.
For example, a value of 0.10 means that the signal is triggered only when
the current rolling volatility belongs to the lowest 10% of historical
observations within the selected Historical Window.

**Buy condition:** Current rolling volatility < historical lower volatility quantile.

---
##### Relative Trading Range

This indicator aims to identify periods during which an asset has been
trading within an unusually narrow price range, which often
characterizes accumulation phases. For each date, the highest and lowest closing prices observed over the
preceding **Rolling Window** are first identified. Their relative
difference is then computed as:

$$
\\text{Relative Trading Range}
=
\\frac{\\text{Highest Price}-\\text{Lowest Price}}
{\\text{Lowest Price}}
$$

A low value indicates that the asset has experienced little price
dispersion over the selected period, whereas larger values correspond
to wider price fluctuations. To reduce the influence of temporary price movements, a **Moving
Average** of the relative trading range is computed over the selected
**Moving Average Window**. This moving average is then compared with
the historical distribution of the relative trading range computed over
the preceding **Historical Window**. The **Lower Trading Range
Quantile** defines the threshold below which the recent trading range
is considered unusually compressed.

**Buy condition:** Moving Average of Relative Trading Range
< Rolling Lower Historical Quantile.

---
##### RSI Confirmation

While the previous two indicators identify assets exhibiting
characteristics of an accumulation phase, the Relative Strength Index
(RSI) is used as a final confirmation filter. The Relative Strength Index (RSI) is a widely used momentum indicator
that ranges from 0 to 100 and compares the magnitude of recent gains
and losses. [Learn more about RSI](https://corporatefinanceinstitute.com/resources/career-map/sell-side/capital-markets/relative-strength-index-rsi/?utm_source=chatgpt.com)

In this strategy, it is computed over the preceding
14-day Window, and a buy signal is generated only if the RSI
remains below the selected **RSI Buy Threshold**. Unlike the previous indicators, the RSI does not rely on historical
quantiles. Instead, it prevents buying assets whose prices have already
experienced an excessively strong upward movement over the recent past,
even if the other accumulation indicators are satisfied.

**Buy condition:** 14-day RSI < RSI Buy Threshold

"""

sell_roi = """
The purpose of this indicator is to identify assets whose recent price
appreciation has become unusually large compared to their own historical
behaviour. For each date, the Return on Investment (ROI) is computed over the
preceding **ROI Window** as the percentage price change observed during
that period. Rather than using a fixed profit target, the current ROI is
compared with its historical distribution computed over the preceding
**Historical Window**. The **Upper ROI Quantile** defines the threshold
above which the recent price appreciation is considered unusually high.

**Sell condition:** ROI > Upper ROI Quantile

"""

sell_rsi_filter = """
The Relative Strength Index (RSI) is a widely used momentum indicator
that measures the strength of recent price movements.
[Learn more about RSI](https://corporatefinanceinstitute.com/resources/career-map/sell-side/capital-markets/relative-strength-index-rsi/?utm_source=chatgpt.com).

In this strategy, the RSI is computed over the preceding **14-day
Window** and compared with its historical distribution computed over
the preceding **Historical Window**. Rather than looking for low RSI
values as in the buy strategy, the **Upper RSI Quantile** is used to
identify periods during which recent upward momentum has become
unusually strong compared to the asset's own historical behaviour.

**Sell condition:** 14-day RSI > Rolling Upper Historical Quantile.

"""

sell_price_volatility = """
Unlike the buy strategy, this
indicator uses high volatility as an additional confirmation that the
market may be entering an excessive bullish phase. For each date, the rolling standard deviation of the closing price is
computed over the preceding **Rolling Window**. This rolling volatility
is then compared with its historical distribution computed over the
preceding **Historical Window**. The **Upper Volatility Quantile**
defines the threshold above which market volatility is considered
unusually high.

**Sell condition:** Rolling Volatility >
Rolling Upper Historical Quantile.

"""

all_sell_indicators="""

##### Return On Investment (ROI)

The purpose of this indicator is to identify assets whose recent price
appreciation has become unusually large compared to their own historical
behaviour. For each date, the Return on Investment (ROI) is computed over the
preceding **ROI Window** as the percentage price change observed during
that period. Rather than using a fixed profit target, the current ROI is
compared with its historical distribution computed over the preceding
**Historical Window**. The **Upper ROI Quantile** defines the threshold
above which the recent price appreciation is considered unusually high.

**Sell condition:** ROI > Upper ROI Quantile

---
##### RSI Filter

The Relative Strength Index (RSI) is a widely used momentum indicator
that measures the strength of recent price movements.
[Learn more about RSI](https://corporatefinanceinstitute.com/resources/career-map/sell-side/capital-markets/relative-strength-index-rsi/?utm_source=chatgpt.com).

In this strategy, the RSI is computed over the preceding **14-day
Window** and compared with its historical distribution computed over
the preceding **Historical Window**. Rather than looking for low RSI
values as in the buy strategy, the **Upper RSI Quantile** is used to
identify periods during which recent upward momentum has become
unusually strong compared to the asset's own historical behaviour.

**Sell condition:** 14-day RSI > Rolling Upper Historical Quantile.

---
##### Price Volatility

Unlike the buy strategy, this
indicator uses high volatility as an additional confirmation that the
market may be entering an excessive bullish phase. For each date, the rolling standard deviation of the closing price is
computed over the preceding **Rolling Window**. This rolling volatility
is then compared with its historical distribution computed over the
preceding **Historical Window**. The **Upper Volatility Quantile**
defines the threshold above which market volatility is considered
unusually high.

**Sell condition:** Rolling Volatility >
Rolling Upper Historical Quantile.


"""

investment_universe = """
The choice of the investment universe can significantly influence the
observed performance of the strategy. Three complementary universes are
therefore available to evaluate both the robustness of the strategy and
the impact of survivorship bias.

- **Historical Top 200:** the 200 largest cryptocurrencies by market
  capitalization on 11 November 2022, corresponding
  to the bottom of the last bear market. This historical universe
  serves as the project's reference universe and is also used for the
  parameter optimization process.

- **Current Top 500 Filtered:** retains only the cryptocurrencies from
  the Historical Top 200 that still belong to the Top 500 by market
  capitalization as of 15 July 2026. This universe therefore evaluates
  the strategy only on assets that managed to remain among today's 500
  largest cryptocurrencies, excluding those that significantly
  underperformed the market or disappeared over the period. This
  introduces a moderate survivorship bias.

- **Current Top 200 Filtered:** retains only the cryptocurrencies from
  the Historical Top 200 that still belong to the Top 200 by market
  capitalization as of 15 July 2026. Compared with the Current Top 500
  Filtered universe, this further narrows the investment universe to
  the strongest performers, resulting in an even stronger survivorship
  bias.

Historical market capitalization rankings are obtained through the
CoinMarketCap API, while historical price data are downloaded from the
Gate.io Exchange API. The current rankings correspond to 15 July 2026.
Since not every cryptocurrency is listed on Gate.io, the effective
investment universe for the Historical Top 200 contains fewer than
200 assets.

"""

bt_methodology = """
The indicators presented above generate objective buy and sell signals, 
which are then sequentially applied to historical price data through a systematic backtesting process.

The objective of this first version is to evaluate the intrinsic quality 
of the trading signals independently of any portfolio allocation strategy. 
Each cryptocurrency is therefore treated as an independent investment account with an initial portfolio value of 100 units.
Trades executed on one asset never affect the capital available for another. 
Whenever a buy signal is generated, 100% of the available capital is invested in the asset, 
and the position is held until the first sell signal, at which point 100% of the position is liquidated.

Buy signals are considered only from the peak of the 2021 bull market in order to focus the analysis
on the most recent complete market cycle. Transaction fees are applied to every buy and sell order. 
A default fee of 0.20% is used, which is representative of trading fees on major cryptocurrency exchanges.

Once the investment universe and strategy parameters have been configured, 
the backtest can be executed using the Run Strategy Backtest button. 
Depending on the selected configuration, the initial execution may take up to 30 seconds. 
Previously computed backtests are automatically cached, 
allowing identical configurations to be retrieved instantly without recomputing the results. 
This makes it easy to compare different parameter combinations and investment universes.

The Configuration Summary section summarizes the exact investment universe and strategy parameters 
used to generate the results presented below.

All performance statistics are computed exclusively from closed trades, 
since open positions do not yet have a realized return or a definitive maximum drawdown.
"""

help_universe_coverage="""
Percentage of the investment universe that generated at least one
closed trade during the backtest.
"""

help_mdd="""
MDD=Maximum Drawdown, 
the maximum losing return achieved by a trade during his life
"""



about_optimization_1 = """
### 1. Why Strategy Optimization?

The objective of the optimization process is to identify the combination
of indicator parameters that produces the strongest historical
performance according to a predefined objective function.

Each indicator used by the strategy contains several configurable
parameters, including rolling window lengths, historical lookback
periods and quantile thresholds. Although reasonable values can be
selected manually, this approach remains subjective and provides no
guarantee that the chosen configuration is close to optimal.

Instead, this project relies on a systematic optimization procedure
that evaluates hundreds of parameter combinations under identical
market conditions. Every candidate configuration is assessed by running
a complete historical backtest before being assigned a quantitative
score.

The optimization does not modify the strategy itself. Throughout the
entire process:

- the same buy indicators are used;
- the same sell indicators are used;
- the same signal generation logic is preserved;
- the same portfolio construction methodology is applied;
- the same transaction costs are considered.

Only the numerical values controlling these indicators are optimized.

The objective is therefore not to invent a new trading strategy, but to
identify the most suitable parameter configuration for the strategy
presented in this project.
"""

about_optimization_2 = """
### 2. Historical Data Used

All optimizations presented on this page were performed exclusively
using historical market data available up to July 15, 2026.

Restricting the optimization to information that was genuinely
available at that date prevents the introduction of look-ahead bias,
which occurs when future information is unintentionally incorporated
into the parameter selection process.

As a result, every parameter combination is evaluated under conditions
that realistically reproduce the information an investor would have had
when making investment decisions.

It is important to understand that the optimal parameters are not fixed
forever. Financial markets continuously evolve as new price history
becomes available and market dynamics change over time.

If the same optimization were performed several months or years later,
using additional historical observations, a different set of parameters
could naturally emerge as optimal.

The results presented here should therefore be interpreted as the best
parameter configuration identified using the information available on
July 15, 2026, rather than as universally optimal values.
"""

about_optimization_2 = """
### 2. Historical Data Used

All optimizations presented on this page were performed exclusively using historical market data
available up to July 15, 2026.

Restricting the optimization to information available at that date prevents look-ahead bias and
ensures that every parameter combination is evaluated under realistic market conditions.

The optimal parameters should therefore be interpreted as the best configuration identified using
the information available on July 15, 2026. If the optimization were repeated in the future using
additional historical data, a different parameter configuration could naturally emerge as optimal.
"""

about_optimization_3 = """
### 3. Optimization Methodology

The optimization is performed with Optuna, a framework designed to explore parameter spaces efficiently.

Each trial represents one complete candidate configuration. For every trial, Optuna selects values for all
buy and sell parameters, generates the corresponding trading signals, runs the historical backtest and
computes the optimization score.

A total of 500 trials is used for each optimization objective. This provides a broad exploration of the
parameter space while keeping the computation time manageable. It does not guarantee that the absolute
global optimum has been found, but it offers a strong compromise between search depth and execution cost.

Some trials are stopped before a score is calculated. A configuration is pruned when it generates no trades,
no closed trades or when the strategy trades fewer than 20% of the assets in the investment universe.

The minimum coverage constraint prevents Optuna from selecting highly concentrated configurations that
produce attractive results on only a small number of cryptocurrencies. Universe coverage is therefore used
as an eligibility condition rather than as a component of the optimization score.
"""

about_optimization_4 = """
### 4. Objective Function Construction

Each valid trial is evaluated using statistics calculated exclusively from closed trades. Depending on the
selected objective, the score is based on return, maximum drawdown or a combination of both.

Because return and drawdown are expressed on different scales, they cannot be combined directly. Each
statistic is therefore normalized between 0 and 1 using a predefined reference bound.

For a return statistic:

$$
Return_{normalized} =
\\operatorname{clip}\\left(
\\frac{Return_{statistic}}{Return_{bound}},
0,
1
\\right)
$$

For a maximum drawdown statistic:

$$
MDD_{normalized} =
\\operatorname{clip}\\left(
1 - \\frac{|MDD_{statistic}|}{MDD_{bound}},
0,
1
\\right)
$$

A higher normalized value is always preferable. A high return increases the return score, while a low
drawdown increases the drawdown score.

Clipping limits every normalized component to the interval from 0 to 1. Once a statistic reaches its
reference bound, further improvements do not increase that component of the score. This prevents extreme
outliers from dominating the optimization and keeps the relative importance of each metric consistent with
the selected weights.

The bounds are not predictions or hard limits on individual trades. They are reference levels used to
translate the selected median or quantile into a comparable score. Their values differ across objectives
because each objective evaluates a different part of the trade distribution and therefore operates on a
different expected scale.
"""


about_optimization_5 = """
### 5. Median Return Optimization

The first objective focuses exclusively on maximizing the median trade return.

$$
Score = Return_{normalized}
$$

The median corresponds to the return of the "typical" trade and is much less
sensitive to extreme winners than the arithmetic mean. This makes the objective
more robust by rewarding parameter configurations that consistently generate
profitable trades rather than relying on a few exceptional outcomes.

The return statistic is normalized using a reference bound of 500%. Any median
return above this threshold receives the maximum normalized score of 1. This
bound was chosen because a median trade return of several hundred percent is
already exceptional and additional gains should not disproportionately influence
the optimization.
"""

about_optimization_6 = """
### 6. Median Return & Median MDD Optimization

The second objective seeks a balance between profitability and risk by combining
the median return and the median maximum drawdown.

$$
Score =
0.5 \\times Return_{normalized}
+
0.5 \\times MDD_{normalized}
$$

Both components receive the same weight, giving equal importance to generating
high returns and limiting drawdowns during each trade.

The normalization uses a return bound of 250% and a maximum drawdown bound of
50%. These values represent ambitious yet realistic reference levels for the
median trade and ensure that neither component dominates the composite score.

As a result, Optuna naturally favours parameter configurations capable of
maintaining attractive returns without exposing positions to excessive downside
risk.
"""

about_optimization_7 = """
### 7. Low Quantile Return & MDD Optimization

The final objective adopts a more conservative perspective by evaluating the
10th percentile of both return and maximum drawdown distributions instead of
their medians.

$$
Score =
0.5 \\times Return_{normalized}^{10\\%}
+
0.5 \\times MDD_{normalized}^{10\\%}
$$

Rather than rewarding the typical trade, this objective evaluates the quality
of relatively poor trades. The goal is to identify parameter configurations
that remain resilient even when market conditions become less favourable.

The normalization uses a return bound of 100% and a maximum drawdown bound of
70%, reflecting the more conservative nature of the evaluated statistics.

Compared with the previous objectives, this optimization generally favours more
stable parameter configurations, potentially at the expense of maximum
profitability.
"""