from __future__ import annotations

from html import escape
from typing import Iterable


def build_dataset_growth_trend_svg(points: Iterable[tuple[str, int | None, int | None, float | None]]) -> str | None:
    valid = [point for point in points if point[1] is not None]
    if len(valid) < 2:
        return None
    width, height = 640, 220
    left, right, top, bottom = 44, 14, 18, 38
    values = [int(point[1]) for point in valid]
    minimum, maximum = min(values), max(values)
    span = max(maximum - minimum, 1)

    def x(index: int) -> float:
        return left + (width - left - right) * index / (len(valid) - 1)

    def y(value: int) -> float:
        return top + (height - top - bottom) * (1 - (value - minimum) / span)

    grid_values = [minimum, minimum + span / 2, maximum]
    grid = "".join(
        f'<line x1="{left}" y1="{y(int(value)):.2f}" x2="{width - right}" y2="{y(int(value)):.2f}" class="metadata-trend-grid" />'
        f'<text x="{left - 8}" y="{y(int(value)) + 4:.2f}" text-anchor="end" class="metadata-trend-axis">{int(value):,}</text>'
        for value in grid_values
    )
    coordinates = [(x(index), y(int(point[1]))) for index, point in enumerate(valid)]
    polyline = " ".join(f"{point_x:.2f},{point_y:.2f}" for point_x, point_y in coordinates)
    dots = "".join(
        f'<circle cx="{point_x:.2f}" cy="{point_y:.2f}" r="4" class="metadata-trend-point">'
        f'<title>{escape(point[0])} · {int(point[1]):,} rows · Net change: {_format_count(point[2])} · Growth: {_format_percent(point[3])}</title></circle>'
        for point, (point_x, point_y) in zip(valid, coordinates)
    )
    labels = _axis_labels(valid[0][0], valid[-1][0], width, height, left, right)
    return (
        f'<svg class="metadata-trend-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Dataset growth trend">'
        f'{grid}<polyline points="{polyline}" class="metadata-trend-line" fill="none" />{dots}{labels}</svg>'
    )


def build_schema_evolution_trend_svg(
    points: Iterable[tuple[str, int, int | None, int, int, int]],
) -> str | None:
    valid = list(points)
    if len(valid) < 2:
        return None
    width, height = 640, 220
    left, right, top, bottom = 44, 14, 18, 38
    maximum = max(max(point[1] for point in valid), 1)

    def x(index: int) -> float:
        return left + (width - left - right) * index / (len(valid) - 1)

    def y(value: int) -> float:
        return top + (height - top - bottom) * (1 - value / maximum)

    grid = "".join(
        f'<line x1="{left}" y1="{y(value):.2f}" x2="{width - right}" y2="{y(value):.2f}" class="metadata-trend-grid" />'
        f'<text x="{left - 8}" y="{y(value) + 4:.2f}" text-anchor="end" class="metadata-trend-axis">{value:,}</text>'
        for value in sorted({0, maximum // 2, maximum})
    )
    coordinates = [(x(index), y(point[1])) for index, point in enumerate(valid)]
    polyline = " ".join(f"{point_x:.2f},{point_y:.2f}" for point_x, point_y in coordinates)
    bars = "".join(
        f'<rect x="{point_x - 7:.2f}" y="{height - bottom - min(point[2] or 0, maximum) * (height - top - bottom) / maximum:.2f}" '
        f'width="14" height="{min(point[2] or 0, maximum) * (height - top - bottom) / maximum:.2f}" class="metadata-trend-bar">'
        f'<title>{escape(point[0])} · Columns: {point[1]:,} · Added: {point[3]:,} · Removed: {point[4]:,} · Modified: {point[5]:,} · Schema changes: {(point[2] or 0):,}</title></rect>'
        for point, (point_x, _) in zip(valid, coordinates)
    )
    dots = "".join(
        f'<circle cx="{point_x:.2f}" cy="{point_y:.2f}" r="4" class="metadata-trend-point">'
        f'<title>{escape(point[0])} · Columns: {point[1]:,} · Schema changes: {(point[2] if point[2] is not None else "—")}</title></circle>'
        for point, (point_x, point_y) in zip(valid, coordinates)
    )
    labels = _axis_labels(valid[0][0], valid[-1][0], width, height, left, right)
    return (
        f'<svg class="metadata-trend-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Schema evolution trend">'
        f'{grid}{bars}<polyline points="{polyline}" class="metadata-trend-line" fill="none" />{dots}{labels}</svg>'
    )


def _axis_labels(first: str, last: str, width: int, height: int, left: int, right: int) -> str:
    return (
        f'<text x="{left}" y="{height - 10}" text-anchor="start" class="metadata-trend-axis">{escape(first)}</text>'
        f'<text x="{width - right}" y="{height - 10}" text-anchor="end" class="metadata-trend-axis">{escape(last)}</text>'
    )


def _format_count(value: int | None) -> str:
    return "—" if value is None else f"{value:+,}"


def _format_percent(value: float | None) -> str:
    return "—" if value is None else f"{value:+.2f}%"


__all__ = ["build_dataset_growth_trend_svg", "build_schema_evolution_trend_svg"]
