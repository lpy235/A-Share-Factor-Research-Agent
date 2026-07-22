import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.storage.universes import HistoricalUniverseStore


def test_universe_store_registers_and_loads_valid_csv(tmp_path):
    store = HistoricalUniverseStore(tmp_path)

    universe_id = store.register(
        b"date,symbol,in_universe\n2024-01-02,000001,true\n2024-01-02,000002,false\n"
    )
    loaded = store.load(universe_id)

    assert universe_id.startswith("universe_")
    assert bool(loaded.loc[(pd.Timestamp("2024-01-02"), "000001")]) is True
    assert bool(loaded.loc[(pd.Timestamp("2024-01-02"), "000002")]) is False


@pytest.mark.parametrize(
    "content",
    [
        b"date,symbol\n2024-01-02,000001\n",
        b"date,symbol,in_universe\nbad,000001,true\n",
        b"date,symbol,in_universe\n2024-01-02,000001,maybe\n",
        b"date,symbol,in_universe\n2024-01-02,,true\n",
    ],
)
def test_universe_store_rejects_malformed_csv(tmp_path, content):
    with pytest.raises(ValueError):
        HistoricalUniverseStore(tmp_path).register(content)


def test_universe_store_rejects_path_like_identifier(tmp_path):
    with pytest.raises(ValueError, match="Invalid historical universe id"):
        HistoricalUniverseStore(tmp_path).load("../membership.csv")


def test_universe_upload_api_returns_controlled_identifier():
    response = TestClient(app).post(
        "/universes",
        files={
            "file": (
                "membership.csv",
                b"date,symbol,in_universe\n2024-01-02,000001,true\n",
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["historical_universe_id"].startswith("universe_")


def test_universe_upload_api_rejects_non_csv_file():
    response = TestClient(app).post(
        "/universes",
        files={"file": ("membership.txt", b"not csv", "text/plain")},
    )

    assert response.status_code == 400
