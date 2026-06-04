from app.sources.source_policy import SourcePolicy


def test_allows_public_pdf_url():
    policy = SourcePolicy()
    result = policy.check_url("https://example.com/reports/factor.pdf")
    assert result.allowed is True
    assert result.reason == "public_url_allowed"


def test_rejects_cnki_url():
    policy = SourcePolicy()
    result = policy.check_url("https://kns.cnki.net/kcms/detail/detail.aspx?id=123")
    assert result.allowed is False
    assert result.reason == "blocked_domain"


def test_rejects_login_required_hint():
    policy = SourcePolicy()
    result = policy.check_url("https://broker.example.com/login/report/123")
    assert result.allowed is False
    assert result.reason == "login_required_hint"

