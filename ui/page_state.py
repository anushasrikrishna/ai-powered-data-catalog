from __future__ import annotations

from typing import Any, MutableMapping, Sequence


def load_widget_state(
    state: MutableMapping[str, Any],
    permanent_key: str,
    widget_key: str,
    default: Any,
    options: Sequence[Any] | None = None,
) -> Any:
    """Restore a widget from durable page state before the widget is created."""
    value = state.get(permanent_key, default)
    if options is not None and value not in options:
        value = default
        state[permanent_key] = value
    elif permanent_key not in state:
        state[permanent_key] = value
    state[widget_key] = value
    return value


def store_widget_state(state: MutableMapping[str, Any], permanent_key: str, widget_key: str) -> None:
    """Copy a widget value into durable page state from its change callback."""
    if widget_key in state:
        state[permanent_key] = state[widget_key]


__all__ = ["load_widget_state", "store_widget_state"]
