import pandas as pd

from app.reports.charts import save_equity_curve


def test_save_equity_curve_creates_png(tmp_path):
    returns = pd.Series([0.01, -0.02, 0.03], index=pd.date_range("2024-01-01", periods=3))
    path = tmp_path / "curve.png"
    save_equity_curve(returns, str(path), title="demo")
    assert path.exists()
    assert path.stat().st_size > 0

