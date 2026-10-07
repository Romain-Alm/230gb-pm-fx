# MFE 230GB (Currency Markets), Fall 2026: Final Project Assignment

This file gives the official assignment, then explains how to read it and how our
project answers each requirement. Read it together with `PROJECT_SPEC.md`, which
contains the implementation details.

---

## 1. Official assignment text

> **MFE 230GB: Currency Markets**
> **Final Project: Designing and Testing Global Trading Strategies**
>
> The final project asks you to design, motivate, and empirically evaluate two trading
> strategies using ideas from the course. The objective is not simply to find a strategy
> with a high historical Sharpe ratio. The goal is to connect an economic hypothesis to
> measurable signals and a transparent trading rule, and then evaluate whether the data
> support the proposed mechanism. Projects may be completed in groups of up to four.
>
> You should develop two distinct strategies. The first should trade only
> developed/OECD markets and may use currencies, short- and long-term sovereign bonds,
> FX forwards, and/or options. The second must involve either emerging markets or crypto
> assets. The two strategies may share a broad theme, but they should be meaningfully
> different applications with clearly specified asset universes, positions, and
> horizons.
>
> Each strategy should begin with a clear theory for why its signal or combination of
> signals should predict returns or changes in risk. Possible mechanisms include, for
> example, terms-of-trade shocks, carry and currency risk premia, country or sovereign
> risk, global financial conditions, market segmentation, order flow, and changes in the
> investor base or asset demand. At least one important part of the project should use
> alternative data rather than relying only on standard asset prices and macroeconomic
> releases. Prediction markets are especially encouraged, including changes in event
> probabilities, disagreement across contracts or platforms, and interactions between
> prediction-market information and FX, bond, or crypto prices. Other possibilities
> include positioning or fund flows, trade or shipping data, text data, and blockchain
> data. The economic logic should come first rather than being constructed after seeing
> the backtest.
>
> For each strategy, explain how the signals are constructed and translated into
> positions, including portfolio formation, holding period, rebalancing, and any use of
> leverage or options. Report standard performance measures such as cumulative returns,
> average returns, volatility, Sharpe ratio, maximum drawdown, turnover, and the effect
> of reasonable transaction costs. Include at least one meaningful out-of-sample or
> robustness exercise. Also analyze when the strategy loses money and construct
> economically meaningful measures of its risk, such as exposure to carry crashes,
> commodity shocks, global risk-off episodes, liquidity, country risk, or concentration
> across assets and time.
>
> **Deliverables**
>
> - Short presentation on Thursday, October 8, during class (3:00-6:00 PM). All group
>   members should participate.
> - A complete replication package with the data, or code/instructions for obtaining it,
>   all code needed to reproduce the results, and a short README.
> - A self-contained interactive HTML page showcasing the economic idea, signals,
>   strategy, key results, charts, and risk analysis.
> - Use of AI is allowed. AI prompts, generated code, and other AI-generated material
>   that materially contributes to the project should be documented in the replication
>   package.
> - The project may share data, code, or ideas with projects completed for other
>   courses.
>
> Projects will be evaluated on the quality of the economic idea, use of course
> concepts, creativity and innovation, especially in the use of alternative data,
> empirical implementation, treatment of risk and robustness, reproducibility, and
> clarity of presentation. Complexity by itself is not rewarded. A simple strategy with
> a strong economic foundation and careful empirical testing can be more successful
> than an elaborate black-box approach.

---

## 2. How to read the assignment

**What is being graded is the reasoning, not the Sharpe ratio.** A strategy that does
not work, but whose mechanism is clearly stated, honestly tested and well explained,
scores better than a high-Sharpe result obtained by searching over signals. In practice:

- Every signal must come with an economic story written *before* the backtest.
- Every parameter must be justified or shown in a robustness grid, never cherry-picked.
- Negative or null results are reported and interpreted, not hidden.
- Simple and transparent beats complex and opaque.

**"Two distinct strategies" is a hard constraint.** They can share the prediction-market
theme, but they must differ in universe, mechanism, positions and horizon. The grader
will check whether the second strategy is just the first one applied to other assets.
We must show empirically that they are different (low return correlation, different
risk profiles).

**Strategy A universe is restricted to developed / OECD markets.** No EM asset may enter
Strategy A, even as a hedge. Instruments allowed: currencies, short and long sovereign
bonds, FX forwards, options.

**Strategy B must involve EM or crypto.** We use EM currencies (forwards and NDFs).

**Alternative data must be central, not decorative.** The instructor explicitly
encourages prediction markets, and in conversation showed strong interest in this idea.
The assignment names three uses that we should cover where possible:
1. changes in event probabilities (our theme indices and shocks);
2. disagreement across contracts or platforms (our false-shock filter, cross-platform
   checks);
3. interactions between prediction-market information and FX or bond prices (our
   regressions, weekend gap test, timing rule).

**Risk analysis must be economic, not only statistical.** Volatility and drawdown are
not enough. The assignment asks for exposures that relate to course concepts: carry
crashes, commodity shocks, global risk-off, liquidity, country risk, concentration.

**Reproducibility is graded.** Someone else must be able to rebuild every number and
figure from the package and the README. AI-generated material that matters must be
documented.

**Course concepts should be visible.** The course (Topics 1 to 3) covers FX market
structure and instruments (spot, forwards, NDFs, swaps, CIP), exchange rate regimes,
reserves and the trilemma, PPP, CIP and the cross-currency basis, UIP failure, carry and
crash risk, downside-risk CAPM, fiscal policy and FX (monetary vs fiscal dominance), and
terms-of-trade shocks. The presentation and HTML page should name these concepts
explicitly where they motivate a choice.

---

## 3. Our answer in one paragraph

We build continuous, country-level "theme indices" (monetary, inflation,
fiscal / political, trade / tariffs, geopolitics) from prediction-market contracts
(Probalytics data). **Strategy A** trades G10 currencies (and, for the fiscal theme,
long-end sovereign bonds) on country-relative theme signals, with signs taken from
course theory, including the monetary vs fiscal dominance distinction, and a test of
weekend information when FX is closed. **Strategy B** holds a standard EM carry portfolio
(forwards and NDFs) and times its exposure with a global geopolitical prediction-market
index, cutting fast on confirmed shocks and re-risking slowly, to reduce the crash risk
that explains the carry premium.

---

## 4. Requirement checklist (mapped to `PROJECT_SPEC.md`)

| Requirement | Where it is addressed |
|---|---|
| Two distinct strategies, clear universes, positions, horizons | Spec 6 (A), 7 (B), 10.4 (A vs B correlation) |
| Strategy A: developed / OECD only | Spec 6.2; OECD EM-like currencies (PLN, HUF, CZK) kept out of A |
| Strategy B: EM or crypto | Spec 7.2 |
| Economic theory before backtest | Spec 0.1, 6.1, 7.1, 4.4 sign conventions, 6.3 fixed spillover map |
| Alternative data, prediction markets | Spec 2.1, 4 (processing), 4.6 (cross-platform filter), 6.6 (weekend test) |
| Signal construction | Spec 4.5, 4.6, 5 |
| Translation into positions, portfolio formation | Spec 6.5, 7.2, 7.4 |
| Holding period and rebalancing | Spec 6.5 (daily with no-trade band), 7.2 (monthly), 7.4 (daily shock overlay) |
| Leverage / options | Spec 6.5 (vol target, leverage cap); options not used (state it explicitly in README) |
| Cumulative and average returns, vol, Sharpe, max drawdown, turnover | Spec 10.1 |
| Transaction costs | Spec 8 |
| Out-of-sample or robustness exercise | Spec 6.5 (2026 OOS), 10.2 (grids, placebos, leave-one-event-out) |
| When does the strategy lose money | Spec 10.3 |
| Economic risk measures (carry crash, commodity, risk-off, liquidity, country, concentration) | Spec 10.4, 7.6 |
| Presentation, Thursday Oct 8, 3 to 6 PM, all members | Spec 11.3 (figure exports) |
| Replication package with data instructions, code, README | Spec 11.1 |
| Self-contained interactive HTML page | Spec 11.2 |
| AI use documented | Spec 0.5, 4.2, 11.1 (`ai_log/`) |

---

## 5. Things the grader is likely to probe (prepare answers)

- **"Is the prediction-market signal just a proxy for VIX or for rates?"** Answered by
  the benchmark phase (Spec 9) and placebos (Spec 10.2).
- **"Did you choose the events after seeing the results?"** No: inclusion rules,
  taxonomy, sign conventions and spillover map are fixed ex ante (Spec 4, 6.3); the
  weekend test uses every weekend (Spec 6.6).
- **"Are A and B really different?"** Different universe, mechanism (relative alpha vs
  timing of a risk premium), signal (country-relative vs global aggregate) and horizon;
  shown by return correlation and risk exposures (Spec 10.4).
- **"Is the sample long enough?"** Liquidity starts around 2024. We use a strict
  out-of-sample year, pooled estimation for power, a high significance threshold and
  report uncertainty honestly.
- **"What does the strategy not protect against?"** Funding-driven carry crashes such as
  August 2024 (Spec 7.6).