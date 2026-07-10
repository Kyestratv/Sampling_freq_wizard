import math
from dataclasses import dataclass

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch, Polygon

from sampling_math import Band, convert_from_hz, format_frequency


@dataclass(frozen=True)
class SpectrumShape:
    start: float
    end: float
    slope: str


def configure_matplotlib() -> None:
    matplotlib.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    matplotlib.rcParams["axes.unicode_minus"] = False
    matplotlib.rcParams["font.size"] = 13
    matplotlib.rcParams["axes.titlesize"] = 15
    matplotlib.rcParams["axes.labelsize"] = 13
    matplotlib.rcParams["xtick.labelsize"] = 12
    matplotlib.rcParams["legend.fontsize"] = 12


class SpectrumPlotter:
    def __init__(self, axes: list[plt.Axes] | np.ndarray, unit: str, show_negative: bool) -> None:
        self.axes = axes
        self.unit = unit
        self.show_negative = show_negative

    def draw_all(self, fs: float, band: Band, fmax: float, render_overlap: bool) -> None:
        self._draw_impulse_spectrum(self.axes[0], fs, band, fmax)
        self._draw_original_band(self.axes[1], fs, band, fmax)
        self._draw_sampled_spectrum(self.axes[2], fs, band, fmax, render_overlap)

    def _u(self, value: float) -> float:
        return convert_from_hz(value, self.unit)

    def _xmin_hz(self, fmax: float) -> float:
        return -fmax if self.show_negative else 0.0

    def _setup_frequency_axis(self, ax: plt.Axes, fmax: float, title: str) -> None:
        ax.clear()
        ax.set_title(title, loc="left", pad=8)
        ax.set_xlim(self._u(self._xmin_hz(fmax)), self._u(fmax))
        ax.set_ylim(0, 1.42)
        ax.set_xlabel(f"频率 ({self.unit})")
        ax.set_yticks([])
        ax.grid(True, axis="x", alpha=0.2)
        ax.axvline(0, color="#1c1c1c", linewidth=1.0)

    def _draw_impulse_spectrum(self, ax: plt.Axes, fs: float, band: Band, fmax: float) -> None:
        self._setup_frequency_axis(ax, fmax, "1. 采样冲击串频谱：频域中以 fs 为间隔的冲击")
        count = int(math.floor(fmax / fs))
        start_index = -count if self.show_negative else 0
        ticks_hz = np.arange(start_index, count + 1) * fs
        ticks = [self._u(value) for value in ticks_hz]
        ax.vlines(ticks, 0, 1.0, color="#1f77b4", linewidth=2.0, label="冲击串频谱")
        ax.scatter(ticks, np.ones_like(ticks), color="#1f77b4", s=26, zorder=3)
        self._draw_band_pair(ax, band.low, band.high, 0.12, 0.26, "#ef7d00", "输入带通范围")
        self._legend(ax)

    def _draw_original_band(self, ax: plt.Axes, fs: float, band: Band, fmax: float) -> None:
        self._setup_frequency_axis(ax, fmax, "2. 输入带通信号频谱：低频率高，高频率低")
        self._draw_nyquist_zones(ax, fs, fmax)
        self._draw_band_pair(ax, band.low, band.high, 0.18, 0.72, "#ef7d00", "原始信号频带")
        ax.text(self._u(band.low), 1.02, f"fL={format_frequency(band.low, self.unit)}", fontsize=12, color="#7a3d00")
        ax.text(self._u(band.high), 1.18, f"fH={format_frequency(band.high, self.unit)}", fontsize=12, color="#7a3d00")
        self._legend(ax, include_zone_note=True)

    def _draw_sampled_spectrum(
        self,
        ax: plt.Axes,
        fs: float,
        band: Band,
        fmax: float,
        render_overlap: bool,
    ) -> None:
        self._setup_frequency_axis(ax, fmax, "3. 采样后频谱：原频谱按 fs 周期复制")
        self._draw_nyquist_zones(ax, fs, fmax)

        max_k = int(math.ceil((fmax + band.high) / fs)) + 1
        original_shapes: list[SpectrumShape] = []
        inverted_shapes: list[SpectrumShape] = []
        y = 0.24
        height = 0.68
        original_labeled = False
        inverted_labeled = False
        xmin = self._xmin_hz(fmax)

        for k in range(-max_k, max_k + 1):
            center = k * fs
            alpha = 0.66 if k == 0 else 0.34
            original_segment = (center + band.low, center + band.high)
            inverted_segment = (center - band.high, center - band.low)
            original_label = None
            inverted_label = None
            if not original_labeled and self._is_visible(original_segment[0], original_segment[1], xmin, fmax):
                original_label = "原始频谱"
                original_labeled = True
            if not inverted_labeled and self._is_visible(inverted_segment[0], inverted_segment[1], xmin, fmax):
                inverted_label = "反转频谱"
                inverted_labeled = True

            self._draw_trapezoid(ax, original_segment[0], original_segment[1], y, height, "#ef7d00", alpha, "down", original_label)
            self._draw_trapezoid(ax, inverted_segment[0], inverted_segment[1], y, height, "#2b8cbe", alpha, "up", inverted_label)
            original_shapes.append(SpectrumShape(original_segment[0], original_segment[1], "down"))
            inverted_shapes.append(SpectrumShape(inverted_segment[0], inverted_segment[1], "up"))

        if render_overlap:
            self._draw_shape_overlaps(ax, original_shapes, inverted_shapes, xmin, fmax, y, height)

        self._legend(ax, include_zone_note=True)

    def _draw_nyquist_zones(self, ax: plt.Axes, fs: float, fmax: float) -> None:
        zone_width = fs / 2
        if zone_width <= 0:
            return
        zones = int(math.ceil(fmax / zone_width))
        colors = ["#f0f3f7", "#e8f5ef"]

        for index in range(zones):
            start_hz = index * zone_width
            end_hz = min((index + 1) * zone_width, fmax)
            start = self._u(start_hz)
            end = self._u(end_hz)
            color = colors[index % 2]
            ax.axvspan(start, end, color=color, alpha=0.72, zorder=0)
            if self.show_negative:
                ax.axvspan(-end, -start, color=color, alpha=0.72, zorder=0)
            if end - start > 0.08 * self._u(fmax):
                ax.text(
                    (start + end) / 2,
                    1.34,
                    self._ordinal(index + 1),
                    ha="center",
                    va="top",
                    fontsize=11,
                    color="#555555",
                )
                if self.show_negative:
                    ax.text(
                        -(start + end) / 2,
                        1.34,
                        self._ordinal(index + 1),
                        ha="center",
                        va="top",
                        fontsize=11,
                        color="#555555",
                    )

        boundary = 0.0
        while boundary <= fmax + zone_width:
            x = self._u(boundary)
            ax.axvline(x, color="#888888", linewidth=0.7, alpha=0.45)
            if self.show_negative:
                ax.axvline(-x, color="#888888", linewidth=0.7, alpha=0.45)
            boundary += zone_width

    def _draw_band_pair(
        self,
        ax: plt.Axes,
        low: float,
        high: float,
        y: float,
        height: float,
        color: str,
        label: str,
    ) -> None:
        self._draw_trapezoid(ax, low, high, y, height, color, 0.74, "down", label)
        if self.show_negative:
            self._draw_trapezoid(ax, -high, -low, y, height, color, 0.42, "up", None)

    def _draw_trapezoid(
        self,
        ax: plt.Axes,
        start_hz: float,
        end_hz: float,
        y: float,
        height: float,
        color: str,
        alpha: float,
        slope: str,
        label: str | None,
    ) -> None:
        start = self._u(start_hz)
        end = self._u(end_hz)
        if end < start:
            start, end = end, start

        if slope == "up":
            y_left = y + height * 0.42
            y_right = y + height
        else:
            y_left = y + height
            y_right = y + height * 0.42

        polygon = Polygon(
            [(start, y), (end, y), (end, y_right), (start, y_left)],
            closed=True,
            facecolor=color,
            edgecolor=color,
            linewidth=1.2,
            alpha=alpha,
            label=label,
            clip_on=True,
        )
        ax.add_patch(polygon)

    def _draw_shape_overlaps(
        self,
        ax: plt.Axes,
        original_shapes: list[SpectrumShape],
        inverted_shapes: list[SpectrumShape],
        xmin: float,
        xmax: float,
        y: float,
        height: float,
    ) -> None:
        labeled = False
        for original in original_shapes:
            for inverted in inverted_shapes:
                start = max(min(original.start, original.end), min(inverted.start, inverted.end), xmin)
                end = min(max(original.start, original.end), max(inverted.start, inverted.end), xmax)
                if end <= start:
                    continue

                label = "频谱重叠" if not labeled else None
                self._draw_overlap_polygon(ax, original, inverted, start, end, y, height, label)
                labeled = True

    def _draw_overlap_polygon(
        self,
        ax: plt.Axes,
        first: SpectrumShape,
        second: SpectrumShape,
        start: float,
        end: float,
        y: float,
        height: float,
        label: str | None,
    ) -> None:
        split_points = [start, end]
        crossing = self._top_crossing(first, second, y, height)
        if crossing is not None and start < crossing < end:
            split_points.append(crossing)
        split_points = sorted(set(split_points))

        top_points = [
            (self._u(x), min(self._top_y(first, x, y, height), self._top_y(second, x, y, height)))
            for x in split_points
        ]
        points = [(self._u(start), y), (self._u(end), y), *reversed(top_points)]
        ax.add_patch(
            Polygon(
                points,
                closed=True,
                facecolor="#c70039",
                edgecolor="#c70039",
                linewidth=1.0,
                alpha=0.68,
                label=label,
                zorder=8,
                clip_on=True,
            )
        )

    def _top_y(self, shape: SpectrumShape, x: float, y: float, height: float) -> float:
        start = min(shape.start, shape.end)
        end = max(shape.start, shape.end)
        if end == start:
            return y
        t = (x - start) / (end - start)
        if shape.slope == "up":
            left = y + height * 0.42
            right = y + height
        else:
            left = y + height
            right = y + height * 0.42
        return left + t * (right - left)

    def _top_crossing(
        self,
        first: SpectrumShape,
        second: SpectrumShape,
        y: float,
        height: float,
    ) -> float | None:
        first_start = min(first.start, first.end)
        first_end = max(first.start, first.end)
        second_start = min(second.start, second.end)
        second_end = max(second.start, second.end)
        if first_end == first_start or second_end == second_start:
            return None

        first_left = self._top_y(first, first_start, y, height)
        first_slope = (self._top_y(first, first_end, y, height) - first_left) / (first_end - first_start)
        second_left = self._top_y(second, second_start, y, height)
        second_slope = (self._top_y(second, second_end, y, height) - second_left) / (second_end - second_start)
        denominator = first_slope - second_slope
        if abs(denominator) < 1e-12:
            return None

        return (second_left - first_left + first_slope * first_start - second_slope * second_start) / denominator

    def _legend(self, ax: plt.Axes, include_zone_note: bool = False) -> None:
        handles, labels = ax.get_legend_handles_labels()
        unique_handles = []
        unique_labels = []
        for handle, label in zip(handles, labels):
            if label and label not in unique_labels:
                unique_handles.append(handle)
                unique_labels.append(label)

        if include_zone_note:
            unique_handles.append(Patch(facecolor="#f0f3f7", edgecolor="#888888", alpha=0.72))
            unique_labels.append("1st/2nd/... = 奈奎斯特区")

        if unique_handles:
            ax.legend(unique_handles, unique_labels, loc="upper right")

    def _is_visible(self, start: float, end: float, xmin: float, xmax: float) -> bool:
        if end < start:
            start, end = end, start
        return max(start, xmin) < min(end, xmax)

    def _ordinal(self, value: int) -> str:
        if 10 <= value % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
        return f"{value}{suffix}"

    def _find_visible_overlaps(
        self,
        segments: list[tuple[float, float]],
        xmin: float,
        xmax: float,
    ) -> list[tuple[float, float]]:
        clipped = []
        for start, end in segments:
            if end < start:
                start, end = end, start
            start = max(start, xmin)
            end = min(end, xmax)
            if end > start:
                clipped.append((start, end))

        clipped.sort()
        overlaps: list[tuple[float, float]] = []
        active_end: float | None = None
        for start, end in clipped:
            if active_end is not None and start < active_end:
                overlap = (start, min(end, active_end))
                if overlap[1] > overlap[0]:
                    overlaps.append(overlap)
                active_end = max(active_end, end)
            else:
                active_end = end

        return self._merge_segments(overlaps)

    def _merge_segments(self, segments: list[tuple[float, float]]) -> list[tuple[float, float]]:
        if not segments:
            return []
        segments.sort()
        merged = [segments[0]]
        for start, end in segments[1:]:
            last_start, last_end = merged[-1]
            if start <= last_end:
                merged[-1] = (last_start, max(last_end, end))
            else:
                merged.append((start, end))
        return merged
