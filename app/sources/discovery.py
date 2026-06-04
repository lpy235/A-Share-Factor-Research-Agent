from dataclasses import dataclass
from typing import Any

from app.rag.retriever import tokenize
from app.sources.fetch import PublicSourceFetcher
from app.sources.source_policy import SourcePolicy


@dataclass(frozen=True)
class DiscoveredSource:
    title: str
    url: str
    source_type: str
    text: str
    score: int

    def to_source_dict(self) -> dict[str, Any]:
        return {
            "source_title": self.title,
            "source_type": self.source_type,
            "text": self.text,
            "source_url": self.url,
        }


PUBLIC_SOURCE_SEEDS = [
    {
        "title": "中国A股市场动量效应的特征和形成机理研究",
        "url": "https://qks.sufe.edu.cn/J/CJYJ/Article/Details/A160824000397/CN",
        "source_type": "public_paper",
        "text": (
            "公开期刊页面讨论中国A股市场动量效应的特征和形成机理。"
            "材料指出不同形成期和持有期下动量收益表现不同，"
            "可用于提出过去收益率动量因子、反转因子以及分周期稳定性检验。"
        ),
    },
    {
        "title": "基于A股价量因子的行业轮动策略研究",
        "url": "https://image.hanspub.org/Html/156-1701085_74516.htm",
        "source_type": "public_article",
        "text": (
            "开放获取论文页面研究A股价量因子在行业轮动策略中的应用。"
            "材料说明价量数据可以构建多因子模型，价格趋势和成交量可反映市场情绪，"
            "可支持量价复合因子的研究假设。"
        ),
    },
    {
        "title": "中国股票市场月频动量效应消失之谜",
        "url": "https://qks.sufe.edu.cn/WorkingPaper/Details/WP2020-0016",
        "source_type": "public_paper",
        "text": (
            "上海财经大学期刊社公开工作论文页面讨论中国股票市场月频动量效应。"
            "材料关注A股动量效应在不同制度和交易频率下的表现，"
            "可用于提出动量因子失效、短周期动量或反转检验。"
        ),
    },
    {
        "title": "A 股收益率预测与行业轮动模型的实证研究",
        "url": "https://www.cfrn.com.cn/uploads/fileupload/4184/paper/1311100421019295.pdf",
        "source_type": "public_paper",
        "text": (
            "公开PDF论文讨论A股收益率预测和行业轮动模型。"
            "材料包含市场、估值、成长、质量和宏观等多类变量，"
            "可支持将价格动量、成交量和市场类变量纳入候选因子研究。"
        ),
    },
    {
        "title": "Time series momentum and contrarian effects in the Chinese stock market",
        "url": "https://arxiv.org/abs/1702.07374",
        "source_type": "public_paper",
        "text": (
            "公开论文研究中国股票市场主要指数上的时间序列动量和反转效应。"
            "材料讨论价格序列、动量策略和反向效应，"
            "可用于提出过去收益率动量、短期反转以及波动控制因子。"
        ),
    },
    {
        "title": "登录后研报：不可使用样例",
        "url": "https://broker.example.com/login/report/volume-price",
        "source_type": "public_report",
        "text": "这个样例用于验证 source policy 会过滤登录来源。",
    },
]


class PublicSourceDiscovery:
    def __init__(
        self,
        seeds: list[dict[str, str]] | None = None,
        fetcher: PublicSourceFetcher | None = None,
    ) -> None:
        self.seeds = seeds or PUBLIC_SOURCE_SEEDS
        self.policy = SourcePolicy()
        self.fetcher = fetcher or PublicSourceFetcher()

    def discover(
        self,
        query: str,
        max_sources: int = 3,
        allow_live_fetch: bool = False,
    ) -> list[DiscoveredSource]:
        query_tokens = tokenize(query)
        candidates: list[DiscoveredSource] = []
        for source in self.seeds:
            url = source.get("url", "")
            if not self.policy.check_url(url).allowed:
                continue

            text = source.get("text", "")
            score = len(query_tokens & tokenize(f"{source.get('title', '')} {url} {text}"))
            if score <= 0:
                continue

            if allow_live_fetch:
                fetched = self._try_fetch(url)
                if fetched:
                    text = fetched

            candidates.append(
                DiscoveredSource(
                    title=source.get("title", "public source"),
                    url=url,
                    source_type=source.get("source_type", "public_article"),
                    text=text,
                    score=score,
                )
            )

        candidates.sort(key=lambda item: item.score, reverse=True)
        return candidates[:max_sources]

    def _try_fetch(self, url: str) -> str | None:
        try:
            text = self.fetcher.fetch_text(url)
        except Exception:
            return None
        cleaned = text.strip()
        return cleaned or None
