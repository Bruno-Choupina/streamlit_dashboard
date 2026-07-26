about_me="""

# Bruno Quant App

### Quantitative Finance Projects

#### About Me

I am currently pursuing the MSc 272 *Economics and Finance* at
Université Paris Dauphine–PSL and completing the first internship of my
gap year at TotalEnergies as a Short-Term Power Middle Office
Analyst.

This platform showcases my quantitative finance projects, combining
personal research with interactive educational tools inspired by the
concepts studied throughout my master's program.

Its objective is both to present the results of my quantitative
research and to provide hands-on applications of financial concepts
through interactive visualizations, simulations and quantitative
models.

"""


project_overview="""

Cryptocurrency markets tend to evolve through pronounced market cycles.
Long accumulation phases, characterized by relatively stable prices,
are often followed by strong bull markets, while periods of excessive
optimism frequently precede major corrections.

This project aims to identify these market regimes using quantitative
indicators derived exclusively from historical price data.
Buy and sell signals are generated objectively and evaluated through
historical backtesting.

This application provides an interactive environment to configure the
strategy parameters and investment universe, run historical backtests,
analyze the generated trades, and compare different optimized parameter
configurations. Future versions will extend both the trading logic and
the portfolio management methodology.

##### Application Structure

This application is organized into four main sections:

- **Strategy Parameters** — Understand the buy and sell indicators and
  configure their parameters.

- **Investment Universe** — Select the cryptocurrency universe used for
  the backtest.

- **Backtesting** — Run the strategy, analyze the results, and inspect
  the generated trades.

- **Strategy Optimization** — Compare parameter configurations obtained
  with different optimization objectives.

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
##### Price Volatility

Periods of accumulation are often characterized by relatively stable
price movements. This indicator identifies assets whose volatility is
unusually low relative to their historical behaviour.

- **Rolling Window** defines the period used to compute rolling
  volatility.
- **Historical Window** defines the rolling historical period used to
  compute the volatility quantiles.
- **Lower Volatility Quantile** sets the threshold below which volatility
  is considered unusually low.

**Buy condition:** Rolling Volatility < Lower Historical Volatility
Quantile.

---

##### Relative Trading Range

Accumulation phases are also characterized by prices fluctuating within
an unusually narrow range. This indicator is computed as:

$$
\\text{Relative Trading Range}
=
\\frac{\\text{Highest Price}-\\text{Lowest Price}}
{\\text{Lowest Price}}
$$

- **Rolling Window** defines the period used to identify the highest and
  lowest closing prices included in the calculation.
- **Moving Average Window** defines the period used to compute the moving
  average of the Relative Trading Range.
- **Historical Window** defines the rolling historical period used to
  compute the trading range quantiles.
- **Lower Trading Range Quantile** sets the threshold below which the
  trading range is considered unusually compressed.

**Buy condition:** Moving Average of Relative Trading Range < Lower
Trading Range Quantile.

---

##### RSI Confirmation

The Relative Strength Index (RSI) is used as a final confirmation filter
to avoid buying assets that have already experienced a strong recent
price increase. The RSI is computed over a fixed 14-week period and ranges from
0 to 100. Unlike the previous indicators, it does not rely on historical
quantiles. [Learn more about RSI](https://corporatefinanceinstitute.com/resources/career-map/sell-side/capital-markets/relative-strength-index-rsi/?utm_source=chatgpt.com)

**RSI Buy Threshold** defines the maximum RSI value allowed to generate
a buy signal.

**Buy condition:** 14-week RSI < RSI Buy Threshold.

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

This indicator identifies assets whose recent price appreciation has
become unusually large relative to their historical behaviour.

- **ROI Window** defines the period used to compute the recent Return On
  Investment (ROI).
- **Historical Window** defines the rolling historical period used to
  compute the ROI quantiles.
- **Upper ROI Quantile** sets the threshold above which recent price
  appreciation is considered unusually high.

**Sell condition:** ROI > Upper Historical ROI Quantile.

---

##### RSI Filter

The Relative Strength Index (RSI) is used to identify periods during
which upward momentum has become unusually strong. The RSI is computed over a fixed 14-week period and compared with its
historical behaviour. [Learn more about RSI](https://corporatefinanceinstitute.com/resources/career-map/sell-side/capital-markets/relative-strength-index-rsi/?utm_source=chatgpt.com)

- **Historical Window** defines the rolling historical period used to
  compute the RSI quantiles.
- **Upper RSI Quantile** sets the threshold above which the RSI is
  considered unusually high.

**Sell condition:** 14-week RSI > Upper Historical RSI Quantile.

---

##### Price Volatility

Unlike the buy strategy, this indicator uses high volatility as a
confirmation that the market may be entering an excessive bullish phase.

- **Rolling Window** defines the period used to compute rolling
  volatility.
- **Historical Window** defines the rolling historical period used to
  compute the volatility quantiles.
- **Upper Volatility Quantile** sets the threshold above which
  volatility is considered unusually high.

**Sell condition:** Rolling Volatility > Upper Historical Volatility
Quantile.

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


  #Historical market capitalization rankings are obtained through the
  #CoinMarketCap API, while historical price data are downloaded from the
  #Gate.io Exchange API. The current rankings correspond to 15 July 2026.
  #Since not every cryptocurrency is listed on Gate.io, the effective
  #investment universe for the Historical Top 200 contains fewer than
  #200 assets.


bt_methodology = """
The indicators presented above generate objective buy and sell signals,
which are sequentially applied to historical price data through a
systematic backtesting process. 
A buy or sell signal is generated only when all three corresponding
indicators simultaneously satisfy their respective conditions.

This first version evaluates the trading signals independently of any
portfolio allocation strategy. Each cryptocurrency is treated as an
independent investment account with an initial portfolio value of
100 units.

- Independent Assets: Trades executed on one asset never affect the capital allocated to another.
- Position Sizing: Each buy signal invests 100% of the available capital.
- Position Exit: The position is fully liquidated at the first sell signal.

Buy signals are considered only from the peak of the 2021 bull market,
and a default transaction fee of 0.20% is applied to every buy and sell
order. Once the investment universe and strategy parameters have been configured,
the strategy can be executed using the **Run Strategy Backtest** button.
The initial execution may take up to 30 seconds depending on the selected
configuration.

All performance statistics are computed exclusively from closed trades, since
open positions do not yet have a realized return or a definitive maximum
drawdown.
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


about_optimization="""

#### Optimization Methodology

The objective of the optimization process is to identify the indicator
parameter configuration that maximizes a predefined objective function.
The trading strategy itself remains unchanged throughout the
optimization.

Parameter selection is performed using Bayesian optimization. All
optimizations were conducted using historical market data available up
to July 15, 2026, preventing look-ahead bias. Each objective is
optimized over 500 trials, while configurations generating no trades,
no closed trades, or covering fewer than 20% of the investment universe
are automatically pruned.

Three objective functions are available. They are computed from return
statistics alone or from a combination of return and maximum drawdown
statistics. Because these statistics have different orders of
magnitude, they are first normalized before being combined into a
single optimization score.

---

#### Score Normalization

Return statistics are normalized according to

$$
\\text{Return}_{\\text{normalized}}
=
\\operatorname{clip}
\\left(
\\frac{\\text{Return}_{\\text{statistic}}}
{\\text{Return}_{\\text{bound}}},
0,1
\\right)
$$

Maximum drawdown statistics are normalized according to

$$
\\text{MDD}_{\\text{normalized}}
=
\\operatorname{clip}
\\left(
1-
\\frac{|\\text{MDD}_{\\text{statistic}}|}
{\\text{MDD}_{\\text{bound}}},
0,1
\\right)
$$

The function $\\operatorname{clip}(x,0,1)$ limits normalized values to
the interval $[0,1]$.

For example, suppose the return normalization bound is 500%. If a
parameter configuration produces a median trade return of 300%, the
normalized value is equal to 0.60. A median return of 600% would produce
a value of 1.20, but clipping limits it to 1. Consequently, increasing
the median return beyond 500% does not further increase the optimization
score.

---

#### Objective Functions

"""

median_return="""
##### Median Return

The optimization score is equal to the normalized median trade return.

$$
\\text{Score}
=
\\text{Return}_{\\text{normalized}}
$$

where

- $\\text{Return}_{\\text{statistic}}$ = median trade return
- $\\text{Return}_{\\text{bound}}$ = 500%

"""

median_return_mdd="""
##### Median Return & Median MDD

The optimization score is the equally weighted average of the normalized
median trade return and the normalized median maximum drawdown.

$$
\\text{Score}
=
0.5\\times\\text{Return}_{\\text{normalized}}
+
0.5\\times\\text{MDD}_{\\text{normalized}}
$$

where

- $\\text{Return}_{\\text{statistic}}$ = median trade return
- $\\text{MDD}_{\\text{statistic}}$ = median maximum drawdown
- $\\text{Return}_{\\text{bound}}$ = 250%
- $\\text{MDD}_{\\text{bound}}$ = 50%

"""

quantile_return_mdd="""
##### Low Quantile Return & Low Quantile MDD

The optimization score is the equally weighted average of the normalized
10th percentile of trade returns and the normalized 10th percentile of
maximum drawdowns. This objective favours parameter configurations that
remain robust even during weaker trades.

$$
\\text{Score}
=
0.5\\times\\text{Return}_{\\text{normalized}}
+
0.5\\times\\text{MDD}_{\\text{normalized}}
$$

where

- $\\text{Return}_{\\text{statistic}}$ = 10th percentile of trade returns
- $\\text{MDD}_{\\text{statistic}}$ = 10th percentile of maximum drawdowns
- $\\text{Return}_{\\text{bound}}$ = 200%
- $\\text{MDD}_{\\text{bound}}$ = 70%


"""