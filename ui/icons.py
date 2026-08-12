ICONS = {
    "dashboard": '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    "database": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v7c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12v7c0 1.7 3.6 3 8 3s8-1.3 8-3v-7"/>',
    "search": '<circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 5 5"/>',
    "catalog": '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 7h8M8 11h8M8 15h5"/>',
    "quality": '<circle cx="12" cy="12" r="9"/><path d="m8 12 2.5 2.5L16 9"/>',
    "report": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v5h4M9 12h6M9 16h6"/>',
}


def svg_icon(name: str, size: int = 20) -> str:
    paths = ICONS.get(name, ICONS["catalog"])
    return (
        f'<svg aria-hidden="true" fill="none" height="{size}" viewBox="0 0 24 24" '
        f'width="{size}" xmlns="http://www.w3.org/2000/svg" stroke="currentColor" '
        f'stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8">{paths}</svg>'
    )
