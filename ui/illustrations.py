from __future__ import annotations


def product_mark(size: int = 20) -> str:
    """Return the original catalog/data product mark as inline SVG."""
    return (
        f'<svg class="product-mark-svg" width="{size}" height="{size}" viewBox="0 0 48 48" '
        'fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="AI-Powered Data Catalog">'
        '<path d="M13 13L24 24L35 13M24 24V35" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
        '<rect x="7" y="7" width="12" height="12" rx="3" fill="currentColor"/>'
        '<rect x="29" y="7" width="12" height="12" rx="3" fill="currentColor"/>'
        '<rect x="18" y="29" width="12" height="12" rx="3" fill="currentColor"/>'
        '<circle cx="24" cy="24" r="4" fill="currentColor"/>'
        '<path d="M21.5 24.2L23.2 25.8L26.7 22.2" stroke="var(--accent, #FF5640)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        '</svg>'
    )
