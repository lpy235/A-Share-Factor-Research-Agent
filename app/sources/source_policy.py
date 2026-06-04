from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class SourcePolicyResult:
    allowed: bool
    reason: str


class SourcePolicy:
    blocked_domains = {
        "cnki.net",
        "kns.cnki.net",
        "wind.com.cn",
        "choice.eastmoney.com",
    }
    login_hints = ("/login", "login", "signin", "auth", "passport")

    def check_url(self, url: str) -> SourcePolicyResult:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        normalized = f"{hostname}{parsed.path}".lower()
        if any(hostname.endswith(domain) for domain in self.blocked_domains):
            return SourcePolicyResult(False, "blocked_domain")
        if any(hint in normalized for hint in self.login_hints):
            return SourcePolicyResult(False, "login_required_hint")
        if parsed.scheme not in {"http", "https"}:
            return SourcePolicyResult(False, "unsupported_scheme")
        return SourcePolicyResult(True, "public_url_allowed")

