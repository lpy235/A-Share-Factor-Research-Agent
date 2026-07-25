from app.storage.factor_registry import FactorRegistryStore


def _candidate_payload() -> dict:
    return {
        "factor_name": "volume_price_momentum",
        "formula": "rank(ts_mean(volume, 5)) * rank(returns(close, 20))",
        "direction": "positive",
        "required_fields": ["close", "volume"],
        "source_evidence": {"source_title": "研究报告", "source_url": "https://example.com/report"},
        "metrics": {"mean_rank_ic": 0.04, "mean_rank_ic_oos": 0.03},
        "run_id": "run_001",
        "data_version": "v20200131_test",
        "manifest_hash": "a" * 64,
    }


def test_registry_keeps_immutable_factor_version_and_append_only_decisions(tmp_path):
    store = FactorRegistryStore(tmp_path / "factors.db")

    version = store.register_candidate(_candidate_payload())
    approved = store.record_decision(
        version["version_id"],
        status="approved",
        decision_maker="portfolio_manager",
        reason="OOS and walk-forward checks passed.",
    )
    retired = store.record_decision(
        version["version_id"],
        status="retired",
        decision_maker="portfolio_manager",
        reason="Superseded by a newer version.",
    )

    record = store.get(version["version_id"])
    assert version["status"] == "candidate"
    assert approved["status"] == "approved"
    assert retired["status"] == "retired"
    assert record["formula"] == _candidate_payload()["formula"]
    assert record["data_version"] == "v20200131_test"
    assert [item["status"] for item in record["decisions"]] == ["candidate", "approved", "retired"]
    assert record["decisions"][-1]["reason"] == "Superseded by a newer version."


def test_registry_rejects_invalid_decision_status_and_missing_payload_fields(tmp_path):
    store = FactorRegistryStore(tmp_path / "factors.db")

    try:
        store.register_candidate({"factor_name": "incomplete"})
    except ValueError as exc:
        assert "missing candidate fields" in str(exc)
    else:
        raise AssertionError("incomplete candidate payload must fail")

    version = store.register_candidate(_candidate_payload())
    try:
        store.record_decision(version["version_id"], "auto_approved", "agent", "not allowed")
    except ValueError as exc:
        assert "invalid factor status" in str(exc)
    else:
        raise AssertionError("invalid decision status must fail")
