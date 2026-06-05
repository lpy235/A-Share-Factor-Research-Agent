from app.data.fixture_provider import FixtureAshareDataProvider
from app.data.provider_factory import CachedAshareDataProvider, select_data_provider


def test_select_data_provider_defaults_to_cached_fixture(tmp_path):
    selection = select_data_provider(cache_dir=str(tmp_path))

    assert selection.provider_name == "fixture"
    assert isinstance(selection.provider, CachedAshareDataProvider)
    assert selection.diagnostics["cache_enabled"] is True


def test_select_data_provider_can_disable_cache():
    selection = select_data_provider(provider_name="fixture", cache_enabled=False)

    assert selection.provider_name == "fixture"
    assert isinstance(selection.provider, FixtureAshareDataProvider)
    assert selection.diagnostics["cache_enabled"] is False


def test_select_data_provider_unknown_name_falls_back_to_fixture():
    selection = select_data_provider(provider_name="unknown", cache_enabled=False)

    assert selection.provider_name == "fixture"
    assert selection.diagnostics["fallback_reason"] == "unknown_data_provider"
