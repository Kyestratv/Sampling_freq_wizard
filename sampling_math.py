import math
from dataclasses import dataclass


UNIT_SCALES: dict[str, float] = {
    "Hz": 1.0,
    "kHz": 1_000.0,
    "MHz": 1_000_000.0,
    "GHz": 1_000_000_000.0,
}


@dataclass(frozen=True)
class Band:
    low: float
    high: float

    @property
    def width(self) -> float:
        return self.high - self.low


@dataclass(frozen=True)
class SamplingInterval:
    order: int
    low: float
    high: float | None

    def contains(self, fs: float, eps: float = 1e-9) -> bool:
        if self.high is None:
            return fs + eps >= self.low
        return self.low - eps <= fs <= self.high + eps


def parse_float(value: str, label: str) -> float:
    try:
        result = float(value)
    except ValueError as exc:
        raise ValueError(f"{label} 必须是数字") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} 必须是有限数字")
    return result


def parse_frequency(value: str, label: str, unit: str, allow_zero: bool = False) -> float:
    number = parse_float(value, label)
    if allow_zero:
        if number < 0:
            raise ValueError(f"{label} 不能小于 0")
    elif number <= 0:
        raise ValueError(f"{label} 必须大于 0")
    return number * UNIT_SCALES[unit]


def validate_band(band: Band) -> None:
    if band.low < 0:
        raise ValueError("频率下限 fL 不能小于 0")
    if band.high <= band.low:
        raise ValueError("频率上限 fH 必须大于频率下限 fL")


def get_bandpass_sampling_intervals(band: Band) -> list[SamplingInterval]:
    validate_band(band)

    if band.low == 0:
        return [SamplingInterval(order=1, low=2 * band.high, high=None)]

    intervals = [SamplingInterval(order=1, low=2 * band.high, high=None)]
    max_order = int(math.floor(band.high / band.width))

    for order in range(2, max_order + 1):
        low = 2 * band.high / order
        high = 2 * band.low / (order - 1)
        if low <= high:
            intervals.append(SamplingInterval(order=order, low=low, high=high))

    return intervals


def choose_display_limit(fs: float, band: Band) -> float:
    return max(3 * fs, 2.5 * band.high, 6 * band.width)


def convert_from_hz(value: float, unit: str) -> float:
    return value / UNIT_SCALES[unit]


def convert_to_hz(value: float, unit: str) -> float:
    return value * UNIT_SCALES[unit]


def format_frequency(value: float, unit: str) -> str:
    scaled = convert_from_hz(value, unit)
    magnitude = abs(scaled)
    if magnitude == 0:
        return f"0 {unit}"
    if magnitude >= 100:
        return f"{scaled:,.2f} {unit}"
    if magnitude >= 1:
        return f"{scaled:,.4g} {unit}"
    return f"{scaled:.4g} {unit}"


def format_entry_value(value: float, unit: str) -> str:
    scaled = convert_from_hz(value, unit)
    if abs(scaled) >= 100:
        return f"{scaled:.2f}".rstrip("0").rstrip(".")
    return f"{scaled:.6g}"
