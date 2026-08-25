from __future__ import annotations

from html import escape
import math
from typing import Iterable


def build_quality_trend_svg(points: Iterable[tuple[str, float]]) -> str | None:
    """Build a dependency-free, responsive SVG for chronological quality scores."""
    valid_points: list[tuple[str, float]] = []
    for label, raw_score in points:
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            continue
        if math.isfinite(score):
            valid_points.append((str(label), max(0.0, min(score, 100.0))))
    if len(valid_points) < 2:
        return None

    width, height = 640, 220
    left, right, top, bottom = 40, 14, 18, 38
    plot_width = width - left - right
    plot_height = height - top - bottom

    def x_position(index: int) -> float:
        return left + (plot_width * index / (len(valid_points) - 1))

    def y_position(score: float) -> float:
        return top + plot_height * (1.0 - score / 100.0)

    coordinates = [(x_position(index), y_position(score)) for index, (_, score) in enumerate(valid_points)]
    polyline = " ".join(f"{x:.2f},{y:.2f}" for x, y in coordinates)
    grid = "".join(
        f'<line x1="{left}" y1="{y_position(score):.2f}" x2="{width - right}" y2="{y_position(score):.2f}" class="quality-trend-grid" />'
        f'<text x="{left - 8}" y="{y_position(score) + 4:.2f}" text-anchor="end" class="quality-trend-axis">{score}</text>'
        for score in (100, 50, 0)
    )
    dots = "".join(
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" class="quality-trend-point">'
        f'<title>{escape(label)} · {score:g}%</title></circle>'
        for (label, score), (x, y) in zip(valid_points, coordinates)
    )
    first_label = escape(valid_points[0][0])
    last_label = escape(valid_points[-1][0])
    labels = (
        f'<text x="{left}" y="{height - 10}" text-anchor="start" class="quality-trend-axis">{first_label}</text>'
        f'<text x="{width - right}" y="{height - 10}" text-anchor="end" class="quality-trend-axis">{last_label}</text>'
    )
    return (
        f'<svg class="quality-trend-svg" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Quality score trend from oldest to newest run">'
        f'{grid}<polyline points="{polyline}" class="quality-trend-line" fill="none" />{dots}{labels}</svg>'
    )


__all__ = ["build_quality_trend_svg"]
