"""Replaceable normalized sources for raw A-share market data."""

from app.market_data.sources.base import RawMarketDataSource, SourceCapabilityError

__all__ = ["RawMarketDataSource", "SourceCapabilityError"]
