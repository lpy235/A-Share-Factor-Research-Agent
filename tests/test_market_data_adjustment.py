import pandas as pd
import pytest

from app.market_data.adjustment import apply_corporate_action_adjustment


def _bars() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "symbol": ["000001.SZ"] * 3,
            "trade_date": ["2024-01-02", "2024-01-03", "2024-01-04"],
            "open": [100.0, 90.0, 91.0],
            "high": [101.0, 91.0, 92.0],
            "low": [99.0, 89.0, 90.0],
            "close": [100.0, 90.0, 91.0],
            "volume": [1000.0, 1100.0, 1200.0],
            "amount": [100000.0, 99000.0, 109200.0],
        }
    )


def test_adjustment_applies_grouped_cash_bonus_and_capitalization_without_mutating_raw_bars():
    bars = _bars()
    actions = pd.DataFrame(
        {
            "symbol": ["000001.SZ", "000001.SZ", "000001.SZ"],
            "ex_date": ["2024-01-03"] * 3,
            "action_type": ["cash_dividend", "bonus_share", "capitalization"],
            "per_10_shares": [1.0, 0.0, 1.0],
        }
    )

    adjusted, diagnostics = apply_corporate_action_adjustment(bars, actions)

    # (100 - 0.1) / (100 * 1.1) = 0.9081818, making the ex-date close continuous.
    assert adjusted.loc[0, "close"] == pytest.approx(90.8181818)
    assert adjusted.loc[1, "close"] == pytest.approx(90.0)
    assert adjusted.loc[0, "open"] == pytest.approx(90.8181818)
    assert bars.loc[0, "close"] == 100.0
    assert bars.loc[0, "open"] == 100.0
    assert diagnostics == {
        "price_adjustment_mode": "corporate_action_total_return",
        "event_count": 3,
        "applied_event_count": 3,
        "skipped_event_count": 0,
    }


def test_adjustment_skips_events_before_price_window_and_rejects_missing_amounts_in_window():
    bars = _bars()
    original = bars.copy(deep=True)
    before_window = pd.DataFrame(
        {
            "symbol": ["000001.SZ"],
            "ex_date": ["2023-12-29"],
            "action_type": ["cash_dividend"],
            "per_10_shares": [1.0],
        }
    )

    adjusted, diagnostics = apply_corporate_action_adjustment(bars, before_window)

    pd.testing.assert_frame_equal(bars, original)
    assert adjusted["close"].tolist() == original["close"].tolist()
    assert diagnostics["event_count"] == 0
    assert diagnostics["skipped_event_count"] == 0

    missing_amount = pd.DataFrame(
        {
            "symbol": ["000001.SZ"],
            "ex_date": ["2024-01-03"],
            "action_type": ["cash_dividend"],
        }
    )
    with pytest.raises(ValueError, match="per_10_shares"):
        apply_corporate_action_adjustment(bars, missing_amount)


def test_adjustment_excludes_events_for_symbols_absent_from_price_window():
    bars = _bars()
    actions = pd.DataFrame(
        {
            "symbol": ["000001.SZ", "600000.SH"],
            "ex_date": ["2024-01-03", "2024-01-03"],
            "action_type": ["cash_dividend", "cash_dividend"],
            "per_10_shares": [1.0, 1.0],
        }
    )

    adjusted, diagnostics = apply_corporate_action_adjustment(bars, actions)

    assert adjusted.loc[0, "close"] == pytest.approx(99.9)
    assert diagnostics["event_count"] == 1
    assert diagnostics["applied_event_count"] == 1
    assert diagnostics["skipped_event_count"] == 0


def test_adjustment_compounds_multiple_ex_dates_with_raw_prior_closes():
    bars = _bars()
    bars.loc[2, ["open", "high", "low", "close"]] = [80.0, 81.0, 79.0, 80.0]
    bars.loc[len(bars)] = {
        "symbol": "000001.SZ",
        "trade_date": "2024-01-05",
        "open": 81.0,
        "high": 82.0,
        "low": 80.0,
        "close": 81.0,
        "volume": 1300.0,
        "amount": 105300.0,
    }
    actions = pd.DataFrame(
        {
            "symbol": ["000001.SZ", "000001.SZ"],
            "ex_date": ["2024-01-03", "2024-01-04"],
            "action_type": ["cash_dividend", "cash_dividend"],
            "per_10_shares": [1.0, 1.0],
        }
    )

    adjusted, diagnostics = apply_corporate_action_adjustment(bars, actions)

    first_factor = (100.0 - 0.1) / 100.0
    second_factor = (90.0 - 0.1) / 90.0
    assert adjusted.loc[0, "close"] == pytest.approx(100.0 * first_factor * second_factor)
    assert adjusted.loc[1, "close"] == pytest.approx(90.0 * second_factor)
    assert adjusted.loc[2, "close"] == 80.0
    assert adjusted.loc[3, "close"] == 81.0
    assert diagnostics["applied_event_count"] == 2
