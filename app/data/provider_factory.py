from dataclasses import dataclass
from typing import Protocol

import pandas as pd

from app.data.ashare_provider import AkshareAshareDataProvider
from app.data.cache import DailyBarCache
from app.data.fixture_provider import FixtureAshareDataProvider


class AShareDataProvider(Protocol):
    def get_universe(self, universe_name: str, date: str) -> list[str]:
        pass

    def get_daily_bars(
        self,
        symbols: list[str],
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        pass


@dataclass(frozen=True)
class ProviderSelection:
    provider: AShareDataProvider
    provider_name: str
    diagnostics: dict


class CachedAshareDataProvider:
    def __init__(
        self,
        provider: AShareDataProvider,
        provider_name: str,
        cache: DailyBarCache,
    ) -> None:
        self.provider = provider
        self.provider_name = provider_name
        self.cache = cache
        self.cache_hits = 0
        self.cache_misses = 0

    def get_universe(self, universe_name: str, date: str) -> list[str]:
        return self.provider.get_universe(universe_name, date)

    def get_daily_bars(
        self,
        symbols: list[str],
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        frames = []
        for symbol in symbols:
            cached = self.cache.read(self.provider_name, symbol, start_date, end_date)
            if cached is not None:
                self.cache_hits += 1
                frames.append(cached)
                continue

            self.cache_misses += 1
            fetched = self.provider.get_daily_bars([symbol], start_date, end_date)
            self.cache.write(self.provider_name, symbol, start_date, end_date, fetched)
            if not fetched.empty:
                frames.append(fetched)

        if not frames:
            return _empty_daily_bars()
        return pd.concat(frames).sort_index()


def select_data_provider(
    provider_name: str = "fixture",
    cache_enabled: bool = True,
    cache_dir: str = "data_cache",
) -> ProviderSelection:
    normalized = provider_name if provider_name in {"fixture", "akshare"} else "fixture"
    if normalized == "akshare":
        provider: AShareDataProvider = AkshareAshareDataProvider()
    else:
        provider = FixtureAshareDataProvider()

    diagnostics = {
        "requested_provider": provider_name,
        "provider": normalized,
        "cache_enabled": cache_enabled,
        "cache_dir": cache_dir if cache_enabled else None,
        "cache_hits": 0,
        "cache_misses": 0,
    }
    if provider_name != normalized:
        diagnostics["fallback_reason"] = "unknown_data_provider"

    if cache_enabled:
        provider = CachedAshareDataProvider(provider, normalized, DailyBarCache(cache_dir))

    return ProviderSelection(provider=provider, provider_name=normalized, diagnostics=diagnostics)


def _empty_daily_bars() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["open", "high", "low", "close", "volume", "amount"],
        index=pd.MultiIndex.from_arrays([[], []], names=["symbol", "date"]),
    )
