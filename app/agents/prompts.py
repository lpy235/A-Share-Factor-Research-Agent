FACTOR_EXTRACTION_PROMPT = """
You are a quant research assistant for A-share factor research.
Extract candidate factor hypotheses that can be tested with daily OHLCV data.
Return JSON only with a top-level "factors" list.

Research topic:
{research_topic}

Chunks:
{chunks}
"""

FACTOR_DSL_PROMPT = """
Convert the factor hypothesis into the restricted Factor DSL.
Allowed fields: open, high, low, close, volume, amount.
Allowed operators: returns, delay, ts_mean, ts_std, ts_min, ts_max, rank, zscore, winsorize.
Return JSON only.

Hypothesis:
{hypothesis}
"""

