from pathlib import Path


class MarketDataPaths:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    @property
    def database_path(self) -> Path:
        return self.root / "warehouse.duckdb"

    @property
    def manifest_dir(self) -> Path:
        return self.root / "manifests"

    @property
    def lake_dir(self) -> Path:
        return self.root / "lake"

    def raw_daily_bar_partition(self, data_version: str, year: int) -> Path:
        return self.table_partition("raw_daily_bars", data_version, year=year)

    def table_partition(self, table_name: str, data_version: str, year: int | None = None) -> Path:
        path = self.lake_dir / table_name / f"data_version={data_version}"
        if year is not None:
            path /= f"year={year}"
        return path / "part-000.parquet"
