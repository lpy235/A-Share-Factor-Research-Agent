from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class BacktestConfig:
    execution_mode: str = "next_open_to_next_open"
    commission_bps: float = 3.0
    stamp_duty_bps: float = 5.0
    slippage_bps: float = 5.0
    exclude_st: bool = True
    min_listing_days: int = 60
    holding_period_days: int = 1

    def __post_init__(self) -> None:
        if self.execution_mode != "next_open_to_next_open":
            raise ValueError(f"Unsupported execution mode: {self.execution_mode}")
        for field_name in ("commission_bps", "stamp_duty_bps", "slippage_bps"):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} must be non-negative")
        if self.min_listing_days < 0:
            raise ValueError("min_listing_days must be non-negative")
        if self.holding_period_days < 1:
            raise ValueError("holding_period_days must be at least 1")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
