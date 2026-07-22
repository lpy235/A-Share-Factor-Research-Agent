import io
from pathlib import Path
import re
from uuid import uuid4

import pandas as pd


REQUIRED_COLUMNS = ["date", "symbol", "in_universe"]
UNIVERSE_ID_PATTERN = re.compile(r"universe_[0-9a-f]{12}")


class HistoricalUniverseStore:
    def __init__(self, root: str | Path = "historical_universes") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def register(self, content: bytes) -> str:
        try:
            frame = pd.read_csv(io.BytesIO(content), dtype={"symbol": str})
        except Exception as exc:
            raise ValueError("Historical universe is not a readable CSV") from exc
        frame = self._validate(frame)
        universe_id = f"universe_{uuid4().hex[:12]}"
        frame.to_csv(self.root / f"{universe_id}.csv", index=False)
        return universe_id

    def load(self, universe_id: str) -> pd.Series:
        if not UNIVERSE_ID_PATTERN.fullmatch(universe_id):
            raise ValueError("Invalid historical universe id")
        path = self.root / f"{universe_id}.csv"
        if not path.is_file():
            raise KeyError(universe_id)
        frame = pd.read_csv(path, dtype={"symbol": str})
        frame = self._validate(frame)
        return frame.set_index(["date", "symbol"])["in_universe"].sort_index()

    @staticmethod
    def _validate(frame: pd.DataFrame) -> pd.DataFrame:
        if list(frame.columns) != REQUIRED_COLUMNS:
            raise ValueError("Historical universe CSV must contain date,symbol,in_universe")
        if frame.empty:
            raise ValueError("Historical universe CSV must contain at least one row")
        result = frame.copy()
        try:
            result["date"] = pd.to_datetime(result["date"], errors="raise").dt.normalize()
        except (ValueError, TypeError) as exc:
            raise ValueError("Historical universe contains an invalid date") from exc
        if result["symbol"].isna().any() or result["symbol"].astype(str).str.strip().eq("").any():
            raise ValueError("Historical universe contains an empty symbol")
        result["symbol"] = result["symbol"].astype(str).str.strip()
        try:
            result["in_universe"] = result["in_universe"].map(_parse_bool)
        except ValueError as exc:
            raise ValueError("Historical universe contains an invalid in_universe value") from exc
        if result.duplicated(["date", "symbol"]).any():
            raise ValueError("Historical universe contains duplicate date,symbol rows")
        return result


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1"}:
        return True
    if normalized in {"false", "0"}:
        return False
    raise ValueError(f"Invalid boolean value: {value}")
