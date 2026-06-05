# A-Share Factor Research Agent V7 Real Data Cache Design

## Goal

V7 adds optional real A-share daily data mode with local caching.

The project must remain deterministic by default. `fixture` remains the default provider. `akshare` is available only when explicitly requested, and live failures can fall back to fixture data.

## Scope

In scope:

- Add `data_provider` request/state field with `fixture` and `akshare`.
- Add `fallback_to_fixture` request/state field.
- Add `cache_enabled` request/state field.
- Add a filesystem CSV cache for daily bars.
- Add provider selection in a small factory.
- Add market data diagnostics to graph state and trace summaries.

Out of scope:

- Full index constituent universe from live data.
- Wind/Choice/Tushare paid data.
- Corporate action research beyond the existing `qfq` AkShare call.
- Intraday or tick data.

## Behavior

Defaults:

```text
data_provider = "fixture"
cache_enabled = true
fallback_to_fixture = true
market_data_cache_dir = "data_cache"
```

When `data_provider="fixture"`:

- Use `FixtureAshareDataProvider`.
- Do not require network.

When `data_provider="akshare"`:

- Use `AkshareAshareDataProvider`.
- Cache per-symbol daily bars as CSV files.
- If live fetch/cache read fails and `fallback_to_fixture=true`, use fixture data and record fallback diagnostics.
- If fallback is disabled, raise a hard workflow error.

## File Layout

```text
app/data/provider_factory.py
app/data/cache.py
tests/test_data_cache.py
tests/test_data_provider_factory.py
```

## Success Criteria

- Existing V6 tests still pass.
- Fixture mode remains the default.
- Cache wrapper can write and read daily bar CSV files.
- AkShare provider selection can be tested without live network by injecting a fake provider.
- Workflow records `market_data_summary["provider"]`.
- API accepts data provider controls.

