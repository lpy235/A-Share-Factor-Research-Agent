# Realistic A-Share Backtest Design

## Goal

Extend the current single-factor diagnostic backtest into a cost-aware, trade-timing-aware research backtest that reports executable long-only portfolio results while preserving the existing Rank IC and G5-G1 diagnostics.

## Scope

This phase covers:

- signal and execution timing;
- factor-direction normalization;
- equal-weight long-only and research long-short portfolios;
- turnover, commission, stamp duty, and slippage assumptions;
- optional historical universe and tradability fields;
- diagnostics when required tradability data is unavailable;
- gross and net return artifacts and metrics;
- regression tests for timing, costs, filters, and API compatibility.

This phase does not implement a full order-matching engine, intraday limit-order simulation, portfolio optimization, or the versioned factor registry.

## Trading Convention

The current factor value uses information through the close of date t. The new execution convention is:

~~~text
t close: calculate signal
t+1 open: trade into target weights
t+1 open to t+2 open: measure one-day portfolio return
~~~

The final available dates without a subsequent open price are excluded from realized returns. This convention prevents using a closing price to both form a signal and execute that signal.

The existing close-to-next-close forward-return series remains available for Rank IC diagnostics. Portfolio return series use the new open-to-open execution convention.

## Portfolio Construction

For each date, eligible stocks are ranked by the factor after applying FactorSpec.direction:

- positive: highest factor values are preferred;
- negative: multiply the factor by -1 before ranking;
- unknown: reject for executable portfolio construction and retain only for diagnostic IC analysis.

The top quintile becomes an equal-weight long-only portfolio. The existing top-minus-bottom quintile remains a research long-short diagnostic; it is not represented as a claim that ordinary A-share accounts can freely short the bottom leg.

Weights are generated at signal date t and applied at the next available open. Universe and signal eligibility use information available on t; execution constraints such as suspension and price limits are checked on t+1. Existing positions that cannot be sold because of a suspension or limit-down condition are carried forward. A date with no target candidates and no blocked existing positions produces a zero-return observation plus a diagnostic warning.

## Cost Model

Costs are configurable in the research request and saved in backtest_assumptions:

~~~text
commission_bps: charged on traded notional on buys and sells
stamp_duty_bps: charged on sell notional only
slippage_bps: charged on traded notional on buys and sells
~~~

Defaults are explicit configuration values and are not presented as immutable market law. For each rebalance:

~~~text
turnover = sum(abs(target_weight - previous_weight))
commission = turnover * commission_bps / 10,000
slippage = turnover * slippage_bps / 10,000
stamp_duty = sell_turnover * stamp_duty_bps / 10,000
net_return = gross_return - commission - slippage - stamp_duty
~~~

The deterministic demo defaults are 3 bps commission on buys and sells, 5 bps sell-side stamp duty, and 5 bps slippage on buys and sells. Every report displays these values, and callers may set them to zero or replace them with institution-specific assumptions.

The response reports gross and net series, daily turnover, daily cost components, and cumulative cost. Setting all costs to zero must reproduce the gross portfolio series.

## Tradability and Historical Universe

The market-data contract may provide these optional columns:

~~~text
in_universe
is_suspended
is_st
days_since_listing
limit_up
limit_down
~~~

The portfolio builder will:

1. restrict candidates to in_universe when the field exists;
2. exclude suspended or missing-open observations;
3. apply configurable ST and minimum-listing-day filters;
4. prevent new buys when limit_up is true on the execution date;
5. prevent sells when limit_down or is_suspended is true on the execution date, carrying those positions forward;
6. record the number of excluded and retained symbols per date.

When a provider does not supply a status field, the system must record that the corresponding rule was not applied. It must not claim that an unavailable rule was enforced.

Historical universe membership is loaded from an optional registered CSV artifact with:

~~~text
date,symbol,in_universe
~~~

The API accepts a historical_universe_id that resolves through a controlled store; it does not accept an arbitrary server filesystem path. If no historical membership is supplied, the existing fixed-provider universe remains available only as a deterministic demo fallback and the report includes a survivorship-bias warning.

## Data Model and API

Add an explicit backtest configuration object or equivalent validated request fields for:

~~~text
execution_mode: next_open_to_next_open
commission_bps
stamp_duty_bps
slippage_bps
exclude_st
min_listing_days
historical_universe_id
~~~

The response extends existing output without removing fields:

~~~text
gross_backtest_series
net_backtest_series
turnover_series
cost_series
long_only_metrics
tradability_diagnostics
universe_diagnostics
~~~

Existing metrics, oos_metrics, backtest_series, and Rank IC fields remain backward compatible. IS and OOS executable portfolio segments start from flat holdings at their respective boundaries so that segment metrics do not inherit an unreported pre-boundary position.

## Error Handling

An empty data provider result remains a run failure unless the configured fixture fallback is used. An individual date with no eligible stocks produces a zero-return observation and a warning. Missing optional status fields generate diagnostics; they do not trigger a fabricated fallback status. Invalid cost rates, negative listing-day thresholds, malformed universe files, and unsupported execution conventions fail request validation before the workflow starts.

## Testing Strategy

Use small deterministic MultiIndex fixtures to test:

- signal-at-close and execution-at-next-open date separation;
- open-to-open return calculation and final-date exclusion;
- positive and negative factor direction;
- equal-weight long-only and G5-G1 construction;
- turnover, buy/sell cost asymmetry, and zero-cost equivalence;
- suspended, ST, newly listed, limit-up, and limit-down filters;
- date-varying historical universe membership;
- diagnostics when optional fields are absent;
- IS/OOS portfolio series and metric compatibility;
- API request validation and report assumptions.

The full existing test suite and deterministic eval set must continue to pass.

## Acceptance Criteria

The phase is complete when:

1. portfolio returns use next-open execution rather than same-close execution;
2. gross and net returns are both exposed;
3. turnover and all configured cost components are recorded;
4. factor direction controls executable ranking;
5. long-only results are distinct from the research long-short diagnostic;
6. available tradability and historical-universe fields are applied and reported;
7. missing fields produce explicit limitations rather than false claims;
8. existing Rank IC, OOS, report, and API consumers remain compatible;
9. focused and full regression tests pass.

## Follow-up Boundaries

The factor-library phase will consume the validated net metrics and diagnostics for factor approval, versioning, deduplication, and lifecycle management. A future event-driven simulator may replace the vectorized next-open model when intraday order behavior is required.
