import streamlit as st


def render_global_styles(colors: dict[str, str]) -> None:
    dark_theme = colors["background"] == "#192B37"
    table_distinct = "#7DD3FC" if dark_theme else "#315C7A"
    table_range = "#99F6E4" if dark_theme else "#27675F"
    table_sample = "#D1D5D7" if dark_theme else "#27675F"
    source_blue = "#9BD8F5" if dark_theme else "#4E88A8"
    source_postgres = "#A9C7FF" if dark_theme else "#4E73A8"
    st.markdown(
        f"""
        <style>
        :root {{ --bg:{colors['background']}; --surface:{colors['surface']}; --surface-secondary:{colors['secondary']}; --surface-elevated:{colors['elevated']}; --elevated:{colors['elevated']}; --text:{colors['text']}; --text-secondary:{colors['secondary_text']}; --muted:{colors['muted']}; --border:{colors['border']}; --hover:{colors['hover']}; --accent:{colors['accent']}; --icon-primary:{colors['icon_primary']}; --icon-secondary:{colors['icon_secondary']}; --icon-accent:{colors['icon_accent']}; --button-secondary-text:{colors['button_secondary_text']}; --button-primary-bg:{'#47555F' if dark_theme else '#192B37'}; --button-primary-hover:{'#5E6A73' if dark_theme else '#30404B'}; --button-primary-disabled-bg:{'#30404B' if dark_theme else '#E8EAEB'}; --button-primary-disabled-text:{'#BABFC3' if dark_theme else '#8C959B'}; --button-secondary-hover:{'#30404B' if dark_theme else '#E8EAEB'}; --button-secondary-hover-border:{'#47555F' if dark_theme else '#BABFC3'}; --input-bg:{colors['input_bg']}; --input-hover:{colors['input_hover']}; --input-border:{colors['input_border']}; --input-text:{colors['input_text']}; --input-placeholder:{colors['input_placeholder']}; --input-focus:{colors['input_focus']}; --disabled-bg:{colors['disabled_bg']}; --disabled-text:{colors['disabled_text']}; --spinner-active:{colors['spinner_active']}; --spinner-track:{colors['spinner_track']}; --table-distinct:{table_distinct}; --table-range:{table_range}; --table-sample:{table_sample}; --source-blue:{source_blue}; --source-postgres:{source_postgres}; }}
        .stApp {{ background:var(--bg); color:var(--text); }}
        .html-table-wrapper {{ background:var(--surface); border:1px solid var(--border); border-radius:10px; margin:.7rem 0 1.1rem; overflow:hidden; width:100%; }}
        .html-table-scroll {{ overflow-x:auto; width:100%; }}
        [class*="st-key-table-shell-"] {{ position:relative; }}
        [class*="st-key-table-shell-"] [data-testid="stHorizontalBlock"] {{ align-items:flex-start; display:flex; justify-content:flex-end; opacity:0; pointer-events:none; position:absolute; right:.45rem; top:.45rem; transition:opacity 120ms ease, visibility 120ms ease; visibility:hidden; width:auto!important; z-index:20; }}
        [class*="st-key-table-shell-"]:hover [data-testid="stHorizontalBlock"] {{ opacity:1; pointer-events:auto; visibility:visible; }}
        [class*="st-key-table-shell-"] [data-testid="stDownloadButton"] button {{ background:var(--surface); border:1px solid var(--border); color:var(--icon-secondary); height:30px; min-height:28px; min-width:30px; padding:0 .25rem; width:30px; }}
        [class*="st-key-table-shell-"] [data-testid="stDownloadButton"] button:hover {{ background:var(--input-hover); color:var(--accent); }}
        [class*="st-key-table-shell-"] [data-testid="stIconMaterial"] {{ font-size:17px!important; }}
        .html-table {{ border-collapse:collapse; color:var(--text); font-family:inherit; min-width:900px; table-layout:auto; width:100%; }}
        .html-table-cell {{ border-left:1px solid color-mix(in srgb, var(--border) 45%, transparent); font-size:.78rem; padding:.62rem .8rem; vertical-align:middle; }}
        .html-table-cell:first-child {{ border-left:0; }}
        .html-table th {{ background:var(--elevated); border-bottom:1px solid var(--border); color:var(--text); font-size:.74rem; font-weight:750; letter-spacing:.01em; padding:.68rem .8rem; text-align:left; vertical-align:middle; white-space:nowrap; }}
        .html-table td {{ border-top:1px solid color-mix(in srgb, var(--border) 65%, transparent); color:var(--text); line-height:1.45; overflow-wrap:normal; word-break:normal; }}
        .html-table tbody tr:nth-child(even) {{ background:color-mix(in srgb, var(--elevated) 32%, var(--surface)); }}
        .html-table tbody tr:hover {{ background:var(--hover); }}
        .html-table-cell--identifier {{ min-width:7.5rem; white-space:nowrap; }}
        .html-table-cell--numeric {{ font-variant-numeric:tabular-nums; text-align:right; white-space:nowrap; width:1%; }}
        .html-table-cell--wide {{ max-width:28rem; min-width:12rem; white-space:normal; }}
        .html-table--catalog th:nth-child(1), .html-table--catalog td:nth-child(1) {{ width:14%; }}
        .html-table--catalog th:nth-child(2), .html-table--catalog td:nth-child(2) {{ width:20%; }}
        .html-table--catalog th:nth-child(3), .html-table--catalog td:nth-child(3) {{ width:11%; }}
        .html-table--catalog th:nth-child(4), .html-table--catalog td:nth-child(4) {{ width:22%; }}
        .html-table--catalog th:nth-child(5), .html-table--catalog td:nth-child(5) {{ width:12%; }}
        .html-table--metadata th:nth-child(1), .html-table--metadata td:nth-child(1) {{ width:15%; }}
        .html-table--metadata th:nth-child(2), .html-table--metadata td:nth-child(2) {{ width:11%; }}
        .html-table--metadata th:nth-child(3), .html-table--metadata td:nth-child(3) {{ width:12%; }}
        .html-table--metadata th:nth-child(4), .html-table--metadata td:nth-child(4) {{ width:8%; }}
        .html-table--metadata th:nth-child(5), .html-table--metadata td:nth-child(5) {{ width:7%; }}
        .html-table-badge {{ border:1px solid transparent; border-radius:5px; display:inline-block; font-size:.69rem; font-weight:650; letter-spacing:.01em; line-height:1.35; padding:2px 7px; white-space:nowrap; }}
        .html-table-badge--datatype-number {{ background:color-mix(in srgb, #4E88A8 18%, var(--surface)); border-color:color-mix(in srgb, #4E88A8 42%, var(--border)); color:color-mix(in srgb, var(--text) 72%, #4E88A8); }}
        .html-table-badge--datatype-text {{ background:color-mix(in srgb, #3F968A 18%, var(--surface)); border-color:color-mix(in srgb, #3F968A 42%, var(--border)); color:color-mix(in srgb, var(--text) 72%, #3F968A); }}
        .html-table-badge--datatype-date {{ background:color-mix(in srgb, #8265A8 18%, var(--surface)); border-color:color-mix(in srgb, #8265A8 42%, var(--border)); color:color-mix(in srgb, var(--text) 72%, #8265A8); }}
        .html-table-badge--datatype-boolean {{ background:color-mix(in srgb, #B48736 18%, var(--surface)); border-color:color-mix(in srgb, #B48736 42%, var(--border)); color:color-mix(in srgb, var(--text) 72%, #B48736); }}
        .html-table-badge--datatype-other {{ background:var(--elevated); border-color:var(--border); color:var(--text-secondary); }}
        .html-table-badge--nullable-yes {{ background:color-mix(in srgb, #4E9A62 18%, var(--surface)); border-color:color-mix(in srgb, #4E9A62 42%, var(--border)); color:color-mix(in srgb, var(--text) 68%, #4E9A62); }}
        .html-table-badge--nullable-no {{ background:color-mix(in srgb, #D16A5B 18%, var(--surface)); border-color:color-mix(in srgb, #D16A5B 42%, var(--border)); color:color-mix(in srgb, var(--text) 68%, #D16A5B); }}
        .html-table-badge--table-type {{ background:color-mix(in srgb, #4E88A8 18%, var(--surface)); border-color:color-mix(in srgb, #4E88A8 42%, var(--border)); color:color-mix(in srgb, var(--text) 72%, #4E88A8); }}
        .html-table-badge--category-identifier, .html-table-badge--category-quantity {{ background:color-mix(in srgb, #4E88A8 18%, var(--surface)); border-color:color-mix(in srgb, #4E88A8 42%, var(--border)); color:color-mix(in srgb, var(--text) 72%, #4E88A8); }}
        .html-table-badge--category-contact, .html-table-badge--category-text {{ background:color-mix(in srgb, #3F968A 18%, var(--surface)); border-color:color-mix(in srgb, #3F968A 42%, var(--border)); color:color-mix(in srgb, var(--text) 72%, #3F968A); }}
        .html-table-badge--category-date-time {{ background:color-mix(in srgb, #8265A8 18%, var(--surface)); border-color:color-mix(in srgb, #8265A8 42%, var(--border)); color:color-mix(in srgb, var(--text) 72%, #8265A8); }}
        .html-table-badge--category-financial, .html-table-badge--category-boolean {{ background:color-mix(in srgb, #B48736 18%, var(--surface)); border-color:color-mix(in srgb, #B48736 42%, var(--border)); color:color-mix(in srgb, var(--text) 72%, #B48736); }}
        .html-table-badge--category-name, .html-table-badge--category-location {{ background:color-mix(in srgb, var(--accent) 14%, var(--surface)); border-color:color-mix(in srgb, var(--accent) 38%, var(--border)); color:color-mix(in srgb, var(--text) 70%, var(--accent)); }}
        .html-table-badge--category-other {{ background:var(--elevated); border-color:var(--border); color:var(--text-secondary); }}
        .html-table-source {{ align-items:center; display:inline-flex; gap:.35rem; white-space:nowrap; }}
        .html-table-source-icon {{ color:var(--accent); font-size:.88rem; line-height:1; }}
        .html-table-source--snowflake .html-table-source-icon {{ color:var(--source-blue); }}
        .html-table-source--postgresql .html-table-source-icon {{ color:var(--source-postgres); }}
        .html-table-column-name {{ align-items:center; display:inline-flex; gap:.42rem; white-space:nowrap; }}
        .html-table-column-icon {{ align-items:center; border-radius:4px; display:inline-flex; font-size:.67rem; font-weight:750; height:1.15rem; justify-content:center; width:1.15rem; }}
        .html-table-column-icon--number {{ background:color-mix(in srgb, #4E88A8 18%, var(--surface)); color:color-mix(in srgb, var(--text) 72%, #4E88A8); }}
        .html-table-column-icon--text {{ background:color-mix(in srgb, #3F968A 18%, var(--surface)); color:color-mix(in srgb, var(--text) 72%, #3F968A); }}
        .html-table-column-icon--date {{ background:color-mix(in srgb, #8265A8 18%, var(--surface)); color:color-mix(in srgb, var(--text) 72%, #8265A8); }}
        .html-table-column-icon--boolean {{ background:color-mix(in srgb, #B48736 18%, var(--surface)); color:color-mix(in srgb, var(--text) 72%, #B48736); }}
        .html-table-column-icon--other {{ background:var(--elevated); color:var(--text-secondary); }}
        .html-table--metadata td:nth-child(8) {{ color:var(--table-distinct); font-weight:600; }}
        .html-table--metadata td:nth-child(9), .html-table--metadata td:nth-child(10) {{ color:var(--table-range); }}
        .html-table--metadata td:nth-child(11) {{ color:var(--table-sample); }}
        .html-table--catalog td:nth-child(6), .html-table--catalog td:nth-child(7) {{ font-variant-numeric:tabular-nums; font-weight:600; text-align:right; }}
        .documentation-count-breakdown {{ align-items:center; background:var(--surface-secondary); border:1px solid var(--border); border-radius:10px; display:flex; flex-wrap:wrap; gap:.45rem .65rem; margin:.75rem 0 1rem; padding:.7rem .85rem; }}
        .documentation-count-title {{ color:var(--accent); flex-basis:100%; font-size:.65rem; font-weight:800; letter-spacing:.12em; margin-bottom:.1rem; }}
        .documentation-count-description {{ color:var(--text-secondary); flex-basis:100%; font-size:.72rem; margin-bottom:.15rem; }}
        .documentation-count-item {{ align-items:center; background:var(--surface); border:1px solid var(--border); border-radius:6px; display:inline-flex; gap:.4rem; padding:.3rem .5rem; white-space:nowrap; }}
        .documentation-count-item--category {{ border-color:color-mix(in srgb, var(--accent) 32%, var(--border)); }}
        .documentation-count-label {{ color:var(--text-secondary); font-size:.72rem; }}
        .documentation-count-value {{ color:var(--text); font-size:.75rem; font-variant-numeric:tabular-nums; font-weight:750; }}
        .documentation-subsection-title {{ color:var(--text); font-size:.86rem; font-weight:750; letter-spacing:.02em; margin-top:1rem; }}
        .html-table-empty {{ background:var(--surface); border:1px solid var(--border); border-radius:8px; color:var(--muted); margin:.65rem 0 1rem; padding:1rem; text-align:center; }}
        [data-testid="stHeader"] {{ background:transparent; }}
        [data-testid="stToolbar"] {{ visibility:hidden; height:0; }}
        [data-testid="stMainBlockContainer"] {{ max-width:1320px; padding-top:1.25rem; padding-bottom:3rem; }}
        [data-testid="stSidebar"] {{ background:var(--surface-secondary); border-right:1px solid var(--border); }}
        [data-testid="stSidebar"] > div:first-child {{ padding-top:1.5rem; }}
        [data-testid="stSidebarNav"] {{ display:none; }}
        h1,h2,h3,p,label {{ color:var(--text); }} h1 {{ font-size:clamp(2rem,3vw,2.5rem)!important; letter-spacing:-.03em; margin-bottom:.25rem!important; }} h2 {{ font-size:1.3rem!important; margin-top:1.8rem!important; }}
        [data-baseweb="input"], [data-baseweb="select"], [data-baseweb="textarea"] {{ background:var(--input-bg); border-color:var(--input-border); color:var(--input-text); }}
        [data-baseweb="input"]:hover, [data-baseweb="select"]:hover, [data-baseweb="textarea"]:hover {{ background:var(--input-hover); }}
        [data-baseweb="input"] input, [data-baseweb="textarea"] textarea, [data-baseweb="select"] * {{ background:var(--input-bg); color:var(--input-text); caret-color:var(--input-focus); }}
        [data-baseweb="input"] input::placeholder, [data-baseweb="textarea"] textarea::placeholder {{ color:var(--input-placeholder); opacity:1; }}
        [data-baseweb="input"]:focus-within, [data-baseweb="select"]:focus-within, [data-baseweb="textarea"]:focus-within {{ border-color:var(--input-focus); box-shadow:0 0 0 1px rgba(255,86,64,.15); }}
        [data-baseweb="select"] svg {{ color:var(--text-secondary); fill:currentColor; }}
        [data-baseweb="popover"] [role="listbox"], [data-baseweb="popover"] [role="option"] {{ background:var(--input-bg); color:var(--input-text); }}
        [data-baseweb="popover"] [role="option"]:hover, [data-baseweb="popover"] [aria-selected="true"] {{ background:var(--input-hover); color:var(--input-text); }}
        [data-testid="stRadio"] label, [data-testid="stCheckbox"] label, [data-testid="stToggle"] label {{ color:var(--text); }}
        [data-testid="stRadio"] svg, [data-testid="stCheckbox"] svg, [data-testid="stToggle"] svg {{ color:var(--input-text); }}
        [data-baseweb="input"]:has(input:disabled), [data-baseweb="select"]:has([aria-disabled="true"]) {{ background:var(--disabled-bg); color:var(--disabled-text); opacity:.82; }}
        [data-testid="stSpinner"] {{ color:var(--text); }} [data-testid="stSpinnerIcon"] {{ border-color:var(--spinner-track); border-top-color:var(--spinner-active); }}
        .page-content {{ animation:fade-in 220ms ease-out; }} .page-title-row {{ align-items:center; display:flex; gap:.6rem; }} .page-title-row h1 {{ margin:0!important; }} .page-title-row .svg-icon {{ color:var(--icon-primary); }} .page-subtitle {{ color:var(--text-secondary); font-size:1rem; font-weight:650; }}
        .hero-copy,.hero-description {{ color:var(--text-secondary); font-size:.94rem; line-height:1.55; max-width:780px; }}
        .app-header {{ align-items:center; display:flex; margin:0 auto .25rem; max-width:1320px; padding:.7rem 0 .9rem; }} .app-brand {{ align-items:center; display:flex; gap:.7rem; }} .brand-mark {{ align-items:center; background:var(--accent); border-radius:8px; color:#FFFFFF; display:inline-flex; height:32px; justify-content:center; width:32px; }} .brand-name {{ color:var(--text); font-size:1rem; font-weight:800; line-height:1.1; }} .brand-subtitle {{ color:var(--muted); font-size:.7rem; margin-top:.25rem; }}
        [class*="st-key-header-actions"] {{ display:flex; justify-content:flex-end; width:100%; }} [class*="st-key-header-actions"] [data-testid="stHorizontalBlock"] {{ align-items:center; display:flex; gap:.65rem; justify-content:flex-end; width:max-content!important; }} [class*="st-key-header-actions"] [data-testid="stHorizontalBlock"] > div {{ flex:0 0 auto; width:max-content!important; }} [class*="st-key-header-actions"] [data-testid="stButton"] button {{ min-height:32px; }} [class*="st-key-authenticated-account-control"] {{ align-items:center; background:var(--surface); border:1px solid var(--border); border-radius:7px; display:flex; height:32px; max-width:220px; min-height:32px; min-width:120px; overflow:hidden; width:fit-content!important; }} [class*="st-key-authenticated-account-control"] [data-testid="stHorizontalBlock"] {{ align-items:stretch; display:flex; gap:0; height:30px; width:max-content!important; }} [class*="st-key-authenticated-account-control"] [data-testid="stHorizontalBlock"] > div:first-child {{ flex:0 1 auto!important; height:30px; max-width:176px; min-width:78px; width:max-content!important; }} [class*="st-key-authenticated-account-control"] [data-testid="stHorizontalBlock"] > div:last-child {{ flex:0 0 42px!important; height:30px; max-width:42px; min-width:42px; width:42px!important; }} .authenticated-username {{ align-items:center; color:var(--text); display:flex; font-size:.78rem; font-weight:700; height:30px; justify-content:center; max-width:176px; min-height:30px; overflow:hidden; padding:0 .55rem; text-align:center; text-overflow:ellipsis; white-space:nowrap; }} [class*="st-key-authenticated-account-control"] [data-testid="stPopover"] button {{ align-items:center; background:var(--surface)!important; border:0; border-left:1px solid var(--border); border-radius:0; color:var(--text-secondary)!important; display:flex; height:30px; justify-content:center; min-height:30px; min-width:42px; padding:0 .35rem; width:42px; }} [class*="st-key-authenticated-account-control"] [data-testid="stPopover"] button:hover {{ background:var(--hover)!important; color:var(--accent)!important; }} [data-baseweb="popover"], [data-testid="stPopoverBody"] {{ background:var(--surface)!important; border:1px solid var(--border); border-radius:8px; box-shadow:0 8px 22px rgba(25,43,55,.16); color:var(--text); max-width:210px; min-width:170px; }} [data-baseweb="popover"] [data-testid="stMarkdownContainer"], [data-testid="stPopoverBody"] [data-testid="stMarkdownContainer"] {{ color:var(--text)!important; }} [data-baseweb="popover"] [data-testid="stButton"] button, [data-testid="stPopoverBody"] [data-testid="stButton"] button {{ background:var(--surface)!important; border:1px solid var(--border); color:var(--text)!important; min-height:30px; }} [data-baseweb="popover"] [data-testid="stButton"] button:hover, [data-testid="stPopoverBody"] [data-testid="stButton"] button:hover {{ background:var(--hover)!important; border-color:var(--accent); color:var(--text)!important; }} [data-baseweb="popover"] svg, [data-testid="stPopoverBody"] svg {{ color:var(--text-secondary)!important; fill:currentColor!important; stroke:currentColor!important; }}
        [class*="st-key-login-form-shell"] {{ margin:0 auto; max-width:30rem; }} [class*="st-key-login-secondary-actions"] {{ margin:0 auto; max-width:30rem; }} [class*="st-key-login-secondary-actions"] .auth-secondary {{ margin-top:1.05rem; }} [class*="st-key-login-secondary-right"] [data-testid="stPageLink"] a {{ color:var(--accent); font-weight:750; }}
        [class*="st-key-login-form-shell"] [data-baseweb="input"], [class*="st-key-login-form-shell"] [data-baseweb="input"] > div {{ background:var(--input-bg); border-color:var(--input-border); }} [class*="st-key-login-form-shell"] input {{ color:var(--input-text); }} [class*="st-key-login-form-shell"] input::placeholder {{ color:var(--input-placeholder); }} [class*="st-key-login-form-shell"] [data-baseweb="input"]:focus-within {{ border-color:var(--input-focus); box-shadow:0 0 0 1px var(--input-focus); }}
        .app-nav-spacer {{ margin:0 auto .25rem; max-width:1320px; }}
        [class*="st-key-authenticated-header-row"] > [data-testid="stHorizontalBlock"] {{ align-items:center; display:flex; justify-content:space-between; width:100%; }} [class*="st-key-authenticated-header-row"] > [data-testid="stHorizontalBlock"] > div:first-child {{ flex:1 1 auto!important; min-width:0; width:auto!important; }} [class*="st-key-authenticated-header-row"] > [data-testid="stHorizontalBlock"] > div:last-child {{ flex:0 0 auto!important; width:max-content!important; }}
        [class*="st-key-header-actions"] {{ align-items:center; display:flex; justify-content:flex-end; width:100%!important; }} [class*="st-key-header-actions"] > [data-testid="stHorizontalBlock"] {{ justify-content:flex-end; width:100%!important; }}
        .app-nav-divider {{ border-bottom:1px solid var(--border); margin:.45rem auto 1.2rem; max-width:100%; }}
        [data-testid="stPageLink"] a {{ align-items:center; background:transparent; border:1px solid transparent; border-bottom:2px solid transparent; border-radius:8px 8px 0 0; color:var(--text-secondary); display:flex; font-size:.86rem; font-weight:650; justify-content:center; min-height:38px; padding:.45rem .6rem; text-align:center; transition:background 180ms ease,border-color 180ms ease,color 180ms ease; }}
        [data-testid="stPageLink"] a:hover {{ background:var(--hover); color:var(--text); transform:none; }}
        [data-testid="stPageLink"] a[aria-current="page"] {{ border-bottom-color:var(--accent); color:var(--accent); font-weight:750; }}
        [data-testid="stPageLink"] a svg, [data-testid="stPageLink"] a [data-testid="stIconMaterial"], [data-testid="stPageLink"] a .material-symbols-rounded, [data-testid="stPageLink"] a .material-symbols-outlined {{ color:currentColor!important; fill:currentColor!important; }}
        .sidebar-heading,.section-kicker {{ color:var(--accent); font-size:.68rem; font-weight:800; letter-spacing:.13em; }} .sidebar-heading {{ margin-bottom:.55rem; }} .sidebar-item {{ border-bottom:1px solid var(--border); padding:.75rem .25rem; }} .sidebar-label,.sidebar-value {{ display:block; }} .sidebar-label {{ color:var(--text-secondary); font-size:.75rem; }} .sidebar-value {{ color:var(--text); font-size:.82rem; font-weight:650; margin-top:.18rem; }} .sidebar-footer {{ border-top:1px solid var(--border); color:var(--muted); font-size:.7rem; margin-top:2rem; padding:.8rem .25rem; }}
        .hero-panel {{ background:var(--surface-secondary); border:1px solid var(--border); border-left:3px solid var(--accent); border-radius:12px; margin:1.35rem 0 .75rem; padding:1.5rem 1.65rem; }} .hero-eyebrow {{ color:var(--accent); font-size:.68rem; font-weight:800; letter-spacing:.13em; }} .hero-title {{ color:var(--text); font-size:clamp(1.35rem,2.5vw,2rem); font-weight:750; letter-spacing:-.025em; margin-top:.55rem; }} .hero-description {{ margin-top:.5rem; }} .section-kicker {{ margin-top:2rem; }}
        .metric-card,.feature-card,.empty-state,.report-card,.status-card,.quick-card {{ background:var(--surface); border:1px solid var(--border); border-radius:12px; box-shadow:0 4px 16px rgba(25,43,55,.06); }} .metric-card {{ min-height:122px; padding:1rem 1.1rem; }} .metric-value {{ color:var(--accent); font-size:1.55rem; font-weight:800; }} .metric-label {{ color:var(--text); font-size:.84rem; font-weight:700; margin-top:.3rem; }} .metric-detail,.card-description {{ color:var(--muted); font-size:.76rem; line-height:1.45; margin-top:.35rem; }} .status-card {{ min-height:150px; padding:.9rem 1rem; }} .status-icon,.workflow-icon,.quick-icon {{ color:var(--icon-accent); height:20px; width:20px; }} .status-label {{ color:var(--text-secondary); font-size:.75rem; margin-top:.45rem; }} .status-value {{ color:var(--text); font-size:1.35rem; font-weight:800; margin-top:.15rem; }} .status-detail {{ color:var(--muted); font-size:.7rem; line-height:1.35; margin-top:.2rem; }} .feature-card {{ min-height:142px; margin:.5rem 0; padding:1.2rem; transition:transform 200ms ease,box-shadow 200ms ease,border-color 200ms ease; }} .feature-card:hover,.report-card:hover,.status-card:hover,.quick-card:hover {{ border-color:var(--accent); box-shadow:0 8px 22px rgba(25,43,55,.12); transform:translateY(-2px); }} .card-icon,.empty-icon {{ color:var(--icon-accent); }} .card-title {{ color:var(--text); font-size:.98rem; font-weight:750; margin-top:.7rem; }} .badge {{ background:var(--elevated); border-radius:999px; color:var(--text-secondary); display:inline-block; font-size:.68rem; margin-top:.7rem; padding:.25rem .6rem; }} .quick-card {{ min-height:108px; padding:1rem; transition:border-color 180ms ease,box-shadow 180ms ease,transform 180ms ease; }} .quick-title {{ color:var(--text); font-size:.92rem; font-weight:750; margin-top:.45rem; }} .quick-description {{ color:var(--muted); font-size:.74rem; margin-top:.25rem; }}
         .empty-state {{ margin:1.3rem 0; padding:1.8rem; text-align:center; }} .empty-icon {{ height:28px; margin:0 auto .6rem; width:28px; }} .empty-title {{ color:var(--text); font-size:1rem; font-weight:700; }} .empty-description {{ color:var(--muted); font-size:.84rem; margin-top:.4rem; }} .stepper {{ align-items:center; display:flex; margin:1.35rem 0; width:100%; }} .step {{ align-items:center; color:var(--muted); display:flex; flex:1; flex-direction:column; font-size:.72rem; gap:.4rem; text-align:center; }} .step-number {{ align-items:center; border:1px solid var(--border); border-radius:50%; color:var(--muted); display:inline-flex; height:28px; justify-content:center; width:28px; }} .step-connector {{ background:var(--border); flex:1; height:1px; margin:0 .35rem 1.25rem; }} .get-started-workflow {{ align-items:center; display:flex; margin:1rem 0 2rem; }} .metadata-scan-workflow {{ margin-left:auto; margin-right:auto; max-width:1100px; width:75%; }} .workflow-item {{ flex:1; min-width:0; padding:.35rem .25rem; }} .workflow-number {{ color:var(--accent); font-size:.7rem; font-weight:800; letter-spacing:.08em; }} .workflow-icon {{ margin-top:.4rem; }} .workflow-title {{ color:var(--text); font-size:.84rem; font-weight:750; margin-top:.35rem; }} .workflow-connector {{ color:var(--border); font-size:1.1rem; padding:0 .25rem; }}
        .stButton>button {{ border-radius:8px; transition:background 180ms ease,border-color 180ms ease,color 180ms ease,transform 180ms ease; }} .stButton>button:hover {{ transform:translateY(-1px); }} .stButton>button[kind="primary"] {{ background:var(--accent); color:#FFFFFF; box-shadow:0 4px 12px rgba(255,86,64,.2); }} .stButton>button[kind="primary"] svg {{ color:#FFFFFF; }} .stButton>button[kind="secondary"] {{ background:transparent; color:var(--button-secondary-text); border:1px solid var(--border); }} .stButton>button[kind="secondary"] svg {{ color:var(--button-secondary-text); }} .stButton>button[kind="secondary"]:hover {{ background:var(--hover); border-color:var(--button-secondary-text); }} [data-testid="stButton"] button[kind="tertiary"] {{ align-items:center; background:transparent; border:1px solid transparent; color:var(--icon-secondary); height:38px; justify-content:center; min-width:38px; padding:0; width:38px; }} [data-testid="stButton"] button[kind="tertiary"] svg {{ color:currentColor; }} [data-testid="stButton"] button[kind="tertiary"]:hover {{ background:var(--input-hover); border-color:var(--border); color:var(--accent); }} @keyframes fade-in {{ from {{ opacity:0; transform:translateY(4px); }} to {{ opacity:1; transform:translateY(0); }} }} @media (max-width:800px) {{ .get-started-workflow {{ flex-wrap:wrap; }} .metadata-scan-workflow {{ width:100%; }} .workflow-item {{ flex:1 1 45%; }} .workflow-connector {{ display:none; }} }} @media (prefers-reduced-motion:reduce) {{ *,*::before,*::after {{ animation-duration:.01ms!important; transition-duration:.01ms!important; }} }}
        .stButton>button {{ transition:background 180ms ease,border-color 180ms ease,color 180ms ease,box-shadow 180ms ease,transform 180ms ease; }}
        .stButton>button:active {{ transform:translateY(0); }}
        .stButton>button:focus-visible {{ box-shadow:0 0 0 2px var(--bg),0 0 0 4px color-mix(in srgb, var(--accent) 60%, transparent); outline:none; }}
        .stButton>button[kind="primary"] {{ box-shadow:0 2px 8px rgba(255,86,64,.18); }}
        .stButton>button[kind="primary"]:hover {{ background:color-mix(in srgb, var(--accent) 88%, #000000); box-shadow:0 4px 10px rgba(255,86,64,.24); }}
        .stButton>button[kind="primary"]:active {{ background:color-mix(in srgb, var(--accent) 78%, #000000); }}
        .stButton>button[kind="secondary"]:hover {{ color:var(--button-secondary-text); }}
        .stButton>button[kind="secondary"]:active {{ background:var(--input-hover); }}
        .stButton>button[kind="secondary"]:hover {{ background:var(--button-secondary-hover); border-color:var(--button-secondary-hover-border); }}
        [class*="st-key-quality-add-rule-button"] button[kind="primary"], [class*="st-key-quality-run-quality-checks"] button[kind="primary"] {{ background:var(--button-primary-bg); border-color:var(--button-primary-bg); color:#FFFFFF; }}
        [class*="st-key-quality-add-rule-button"] button[kind="primary"] svg, [class*="st-key-quality-run-quality-checks"] button[kind="primary"] svg {{ color:#FFFFFF; }}
        [class*="st-key-quality-add-rule-button"] button[kind="primary"]:hover, [class*="st-key-quality-run-quality-checks"] button[kind="primary"]:hover {{ background:var(--button-primary-hover); border-color:var(--button-primary-hover); color:#FFFFFF; }}
        [class*="st-key-quality-add-rule-button"] button[kind="primary"]:disabled, [class*="st-key-quality-run-quality-checks"] button[kind="primary"]:disabled {{ background:var(--button-primary-disabled-bg); border-color:var(--border); color:var(--button-primary-disabled-text); opacity:1; }}
        [class*="st-key-quality-add-rule-button"] button[kind="primary"]:disabled:hover, [class*="st-key-quality-run-quality-checks"] button[kind="primary"]:disabled:hover {{ background:var(--button-primary-disabled-bg); border-color:var(--border); box-shadow:none; transform:none; }}
        /* Refined shared rhythm and hierarchy. Streamlit controls remain semantic and native. */
        .stApp [data-testid="stMainBlockContainer"] {{ max-width:1320px; padding-top:1rem; padding-bottom:2.5rem; }}
        .page-content {{ margin-bottom:.25rem; }}
        .page-title-row {{ margin-bottom:.25rem; }}
        .page-subtitle {{ line-height:1.35; }}
        .section-kicker {{ margin-top:1.45rem; margin-bottom:.45rem; }}
        .hero-panel {{ margin:1rem 0 .7rem; padding:1.15rem 1.35rem; }}
        .hero-title {{ margin-top:.4rem; }}
        .hero-description {{ margin-top:.35rem; }}
        .app-header {{ padding:.55rem 0 .7rem; }}
        .app-nav-spacer {{ margin-bottom:.1rem; }}
        .app-nav-divider {{ margin:.25rem auto .9rem; }}
        [data-testid="stPageLink"] a {{ min-height:34px; padding:.35rem .5rem; }}
        .status-card {{ min-height:116px; padding:.68rem .85rem; box-shadow:0 2px 10px rgba(25,43,55,.045); }}
        .status-card--compact {{ min-height:108px; padding:.62rem .75rem; box-shadow:none; }}
        .status-card--compact .status-icon {{ display:none; }}
        .status-card--compact .status-label {{ margin-top:0; }}
        .status-card--compact .status-value {{ font-size:1.1rem; }}
        .status-card--no-detail {{ display:flex; flex-direction:column; justify-content:center; }}
        .status-card--no-detail .status-label {{ margin-top:.35rem; }}
        .status-heading {{ align-items:center; display:flex; gap:.5rem; height:24px; }}
        .status-heading .status-icon {{ align-items:center; display:flex; flex:0 0 20px; height:20px; justify-content:center; width:20px; }}
        .status-heading .status-label {{ margin-top:0; }}
        .status-label {{ color:var(--text); font-weight:650; }}
        .status-detail {{ color:var(--muted); font-size:.69rem; margin-top:.16rem; }}
        [class*="st-key-catalog-summary-grid"] [data-testid="stHorizontalBlock"] {{ gap:1rem; }}
        [class*="st-key-catalog-summary-grid"] .status-card {{ min-height:108px; }}
        [class*="st-key-catalog-summary-grid"] .status-card--compact .status-icon {{ display:flex; margin-bottom:.15rem; }}
        [class*="st-key-catalog-summary-grid"] .status-card--compact .status-label {{ margin-top:0; }}
        [class*="st-key-catalog-filter-row"] {{ margin-top:1.15rem; }}
        [class*="st-key-catalog-filter-row"] [data-testid="stHorizontalBlock"] {{ align-items:flex-end; }}
        [class*="st-key-catalog-filter-row"] [data-testid="stTextInput"], [class*="st-key-catalog-filter-row"] [data-testid="stSelectbox"] {{ margin-bottom:0; }}
        .metric-card {{ min-height:96px; padding:.8rem .95rem; box-shadow:0 2px 10px rgba(25,43,55,.045); }}
        .feature-card {{ min-height:118px; margin:.35rem 0; padding:1rem; box-shadow:0 2px 10px rgba(25,43,55,.045); }}
        .quick-card {{ min-height:78px; padding:.75rem .85rem .45rem; border:0; border-radius:0; box-shadow:none; }}
        .quick-card-content {{ align-items:center; display:flex; gap:.65rem; }}
        [class*="st-key-quick-card"] [data-testid="stPageLink"] {{ padding:0 .85rem .65rem; }}
        [class*="st-key-quick-card"] [data-testid="stPageLink"] a {{ align-items:center; background:transparent; border:0; border-radius:5px; color:var(--text-secondary); display:inline-flex; font-size:.74rem; font-weight:650; justify-content:flex-end; min-height:26px; padding:.2rem 0; width:100%; }}
        [class*="st-key-quick-card"] [data-testid="stPageLink"] a:hover {{ background:transparent; color:var(--accent); }}
        [class*="st-key-quick-card-"] {{ background:var(--surface); border:1px solid var(--border); border-radius:10px; overflow:hidden; transition:border-color 180ms ease,box-shadow 180ms ease; }}
        [class*="st-key-quick-card-"]:hover {{ border-color:var(--accent); box-shadow:0 4px 14px rgba(25,43,55,.08); }}
        [class*="st-key-quick-card-"] .stButton>button {{ min-height:32px; }}
        .quick-title {{ margin-top:0; }}
        .empty-state {{ margin:1rem 0; padding:1.25rem; box-shadow:none; }}
        .get-started-workflow {{ align-items:center; margin:.75rem auto 1.45rem; max-width:860px; width:100%; }}
        .metadata-scan-workflow {{ max-width:720px; width:100%; }}
        .workflow-item {{ align-items:center; display:flex; flex-direction:column; justify-content:flex-start; min-height:86px; padding:.25rem .2rem; text-align:center; }}
        .workflow-number {{ height:1rem; }}
        .workflow-icon {{ align-items:center; display:flex; height:24px; justify-content:center; margin-top:.35rem; }}
        .workflow-title {{ height:1.2rem; margin-top:.3rem; }}
        .workflow-connector {{ align-items:center; color:var(--accent); display:flex; flex:0 0 42px; font-size:1rem; height:86px; justify-content:center; opacity:.7; padding:0; }}
        .stButton>button, [data-testid="stDownloadButton"] button {{ min-height:36px; padding:.35rem .8rem; }}
        [data-baseweb="input"], [data-baseweb="select"] {{ min-height:36px; }}
        [data-testid="stRadio"] {{ margin-bottom:.25rem; }}
        .html-table-wrapper {{ margin:.55rem 0 .9rem; border-radius:9px; }}
        .html-table-cell {{ padding:.55rem .72rem; }}
        .documentation-count-breakdown {{ align-content:flex-start; display:flex; min-height:136px; margin:.25rem 0 .65rem; padding:.8rem .9rem; }}
        .documentation-count-footer {{ color:var(--text-secondary); flex-basis:100%; font-size:.72rem; margin-top:.45rem; }}
        .ranking-score {{ align-items:baseline; background:var(--surface-secondary); border:1px solid var(--border); border-radius:8px; display:flex; justify-content:space-between; margin:.1rem 0 .75rem; padding:.55rem .7rem; }}
        .ranking-score span {{ color:var(--text-secondary); font-size:.78rem; font-weight:650; }}
        .ranking-score strong {{ color:var(--accent); font-size:1.15rem; font-weight:800; }}
        .ranking-chips {{ display:flex; flex-wrap:wrap; gap:.35rem; margin:.3rem 0 .65rem; }}
        .ranking-chip {{ background:var(--elevated); border:1px solid var(--border); border-radius:999px; color:var(--text-secondary); display:inline-flex; font-size:.7rem; padding:.2rem .5rem; }}
        .ranking-chip--accent {{ border-color:color-mix(in srgb, var(--accent) 38%, var(--border)); color:var(--text); }}
        .ranking-breakdown {{ border-top:1px solid var(--border); margin-top:.35rem; }}
        .ranking-breakdown-row {{ align-items:center; border-bottom:1px solid color-mix(in srgb, var(--border) 60%, transparent); color:var(--text-secondary); display:flex; font-size:.72rem; justify-content:space-between; padding:.35rem .1rem; }}
        .ranking-breakdown-row strong {{ color:var(--text); font-variant-numeric:tabular-nums; }}
        .quality-context-item {{ background:var(--surface); border:1px solid var(--border); border-radius:8px; min-height:62px; padding:.55rem .65rem; }}
        .quality-context-item span {{ color:var(--text-secondary); display:block; font-size:.68rem; }}
        .quality-context-item strong {{ color:var(--text); display:block; font-size:.78rem; margin-top:.25rem; overflow-wrap:anywhere; }}
        .quality-count-item {{ background:var(--surface-secondary); border:1px solid var(--border); border-radius:8px; padding:.55rem .7rem; }}
        .quality-count-item span {{ color:var(--text-secondary); display:block; font-size:.7rem; }}
        .quality-count-item strong {{ color:var(--text); display:block; font-size:1.15rem; margin-top:.18rem; }}
        .quality-result-status {{ border:1px solid transparent; border-radius:999px; display:inline-block; font-size:.68rem; font-weight:750; letter-spacing:.02em; line-height:1.25; padding:.2rem .5rem; white-space:nowrap; }}
        .quality-result-status--pass {{ background:color-mix(in srgb, #4E9A62 14%, var(--surface)); border-color:color-mix(in srgb, #4E9A62 42%, var(--border)); color:color-mix(in srgb, var(--text) 62%, #4E9A62); }}
        .quality-result-status--fail {{ background:color-mix(in srgb, #D16A5B 14%, var(--surface)); border-color:color-mix(in srgb, #D16A5B 48%, var(--border)); color:color-mix(in srgb, var(--text) 60%, #D16A5B); }}
        .quality-result-status--error {{ background:color-mix(in srgb, #B48736 16%, var(--surface)); border-color:color-mix(in srgb, #B48736 48%, var(--border)); color:color-mix(in srgb, var(--text) 58%, #B48736); }}
        .quality-results-heading {{ margin-top:1.35rem; }}
        #html-table-quality-results td:last-child {{ max-width:28rem; min-width:12rem; overflow-wrap:anywhere; white-space:normal; }}
        .quality-history-heading {{ margin-top:2rem; }}
        .quality-history-table-heading {{ margin-top:1.35rem; }}
        .reports-section-kicker {{ margin-top:1.05rem; margin-bottom:.42rem; }}
        .reports-preview-heading {{ color:var(--accent); font-size:.92rem; font-weight:850; letter-spacing:.14em; margin-bottom:.8rem; margin-top:1.35rem; }}
        .auth-shell {{ margin:8vh auto 1.25rem; max-width:30rem; text-align:center; }}
        .auth-eyebrow {{ color:var(--accent); font-size:.68rem; font-weight:800; letter-spacing:.13em; }}
        .auth-shell h1 {{ color:var(--text); font-size:2rem; margin:.55rem 0 .35rem; }}
        .auth-copy {{ color:var(--text-secondary); margin:0; }}
        [class*="st-key-auth-card-"] {{ background:var(--surface); border:1px solid var(--border); border-radius:14px; box-shadow:0 8px 28px rgba(25,43,55,.08); margin:8vh auto 1rem; max-width:30rem; padding:1.75rem 2rem 1.5rem; }}
        [class*="st-key-auth-card-"] .auth-brand {{ text-align:center; }}
        [class*="st-key-auth-card-"] .auth-brand-title {{ color:var(--text); font-size:1.25rem; font-weight:800; }}
        [class*="st-key-auth-card-"] .auth-brand-subtitle {{ color:var(--muted); font-size:.78rem; margin-top:.15rem; }}
        [class*="st-key-auth-card-"] .auth-title {{ color:var(--text); font-size:1.65rem; margin:1.35rem 0 .3rem; text-align:center; }}
        [class*="st-key-auth-card-"] .auth-copy {{ color:var(--text-secondary); margin-bottom:1.15rem; text-align:center; }}
        [class*="st-key-auth-card-"] [data-testid="stFormSubmitButton"] button {{ min-height:2.55rem; }}
        [class*="st-key-auth-card-"] [data-testid="stPageLink"] {{ justify-content:center; margin-top:.65rem; }}
        .auth-secondary {{ color:var(--muted); font-size:.78rem; margin-top:1.15rem; text-align:center; }}
        [class*="st-key-reports-export-"] [data-testid="stDownloadButton"] button {{ align-items:center; background:var(--surface); border:1px solid var(--border); color:var(--text)!important; display:flex; justify-content:center; }}
        [class*="st-key-reports-export-"] [data-testid="stDownloadButton"] button svg, [class*="st-key-reports-export-"] [data-testid="stDownloadButton"] button svg * {{ color:currentColor!important; fill:currentColor!important; stroke:currentColor!important; }}
        [class*="st-key-reports-export-"] [data-testid="stDownloadButton"] button:hover {{ background:var(--hover); border-color:var(--accent); color:var(--text)!important; }}
        [class*="st-key-reports-export-"] [data-testid="stDownloadButton"] button:focus-visible {{ border-color:var(--accent); box-shadow:0 0 0 2px color-mix(in srgb, var(--accent) 28%, transparent); color:var(--text)!important; outline:none; }}
        [class*="st-key-reports-preview-summary"] {{ margin:.85rem 0 1rem; }}
        [class*="st-key-reports-preview-summary"] [data-testid="stHorizontalBlock"] {{ align-items:stretch; gap:1.15rem; }}
        [class*="st-key-reports-preview-summary"] [data-testid="stHorizontalBlock"] > div {{ align-self:stretch; }}
        [class*="st-key-reports-quality-trend"] {{ background:var(--surface); border:1px solid var(--border); border-radius:10px; min-height:250px; padding:.85rem 1rem; }}
        .quality-result-table {{ table-layout:fixed; }}
        .quality-result-table th, .quality-result-table td {{ box-sizing:border-box; }}
        [class*="st-key-quality-history-summary"] {{ margin:1rem 0 1.25rem; }}
        [class*="st-key-quality-history-trend"] {{ background:var(--surface); border:1px solid var(--border); border-radius:10px; min-height:250px; padding:.85rem 1rem; }}
        .quality-history-panel-title {{ color:var(--text-secondary); font-size:.68rem; font-weight:800; letter-spacing:.08em; }}
        .quality-history-latest {{ background:var(--surface); border:1px solid var(--border); border-radius:10px; min-height:250px; padding:.85rem 1rem; }}
        .quality-history-latest-row {{ border-bottom:1px solid color-mix(in srgb, var(--border) 62%, transparent); display:flex; justify-content:space-between; padding:.48rem 0; }}
        .quality-history-latest-row:last-child {{ border-bottom:0; }}
        .quality-history-latest-row span {{ color:var(--text-secondary); font-size:.72rem; }}
        .quality-history-latest-row strong {{ color:var(--text); font-size:.76rem; text-align:right; }}
        .quality-trend-svg {{ display:block; height:auto; max-width:100%; width:100%; }}
        .quality-trend-grid {{ stroke:var(--border); stroke-width:1; opacity:.65; }}
        .quality-trend-axis {{ fill:var(--muted); font-family:inherit; font-size:10px; }}
        .quality-trend-line {{ stroke:var(--accent); stroke-linecap:round; stroke-linejoin:round; stroke-width:3; }}
        .quality-trend-point {{ fill:var(--surface); stroke:var(--accent); stroke-width:3; }}
        @media (max-width:800px) {{
            [class*="st-key-quality-history-summary"] [data-testid="stHorizontalBlock"] {{ flex-direction:column; gap:1rem; }}
            [class*="st-key-quality-history-summary"] [data-testid="stHorizontalBlock"] > div {{ width:100%!important; }}
        }}
        .quality-detail-heading {{ margin-top:1.25rem; }}
        .quality-visual-panel {{ background:var(--surface); border:1px solid var(--border); border-radius:10px; box-sizing:border-box; min-height:166px; padding:.9rem 1rem; }}
        .quality-visual-title,.quality-detail-panel-title {{ color:var(--text-secondary); font-size:.68rem; font-weight:800; letter-spacing:.08em; }}
        .quality-visual-score {{ color:var(--accent); font-size:1.75rem; font-weight:800; line-height:1.2; margin:.7rem 0 .85rem; }}
        .quality-progress-track,.quality-status-bar-track {{ background:var(--elevated); border-radius:999px; overflow:hidden; }}
        .quality-progress-track {{ height:10px; width:100%; }}
        .quality-progress-fill {{ background:var(--accent); border-radius:inherit; height:100%; min-width:0; }}
        .quality-status-bar {{ align-items:center; display:grid; gap:.5rem; grid-template-columns:3.2rem 1fr 1.5rem; margin-top:.72rem; }}
        .quality-status-bar-label {{ font-size:.7rem; font-weight:750; }}
        .quality-status-bar-label--pass {{ color:#4E9A62; }}
        .quality-status-bar-label--fail {{ color:#D16A5B; }}
        .quality-status-bar-label--error {{ color:#B48736; }}
        .quality-status-bar-track {{ height:8px; }}
        .quality-status-bar-fill {{ border-radius:inherit; display:block; height:100%; min-width:0; }}
        .quality-status-bar-fill--pass {{ background:#4E9A62; }}
        .quality-status-bar-fill--fail {{ background:#D16A5B; }}
        .quality-status-bar-fill--error {{ background:#B48736; }}
        .quality-status-bar strong {{ color:var(--text); font-size:.72rem; text-align:right; }}
        .quality-detail-item {{ background:var(--surface-secondary); border:1px solid var(--border); border-radius:8px; min-height:54px; margin-bottom:.45rem; padding:.5rem .65rem; }}
        .quality-detail-item span {{ color:var(--text-secondary); display:block; font-size:.68rem; }}
        .quality-detail-item strong {{ color:var(--text); display:block; font-size:.78rem; margin-top:.2rem; overflow-wrap:anywhere; }}
        .quality-detail-panel {{ background:var(--surface); border:1px solid var(--border); border-radius:10px; min-height:100%; padding:.85rem 1rem; }}
        .quality-detail-row {{ border-bottom:1px solid color-mix(in srgb, var(--border) 62%, transparent); display:flex; gap:1rem; justify-content:space-between; padding:.48rem 0; }}
        .quality-detail-row:last-child {{ border-bottom:0; }}
        .quality-detail-row span {{ color:var(--text-secondary); font-size:.72rem; }}
        .quality-detail-row strong {{ color:var(--text); font-size:.76rem; max-width:68%; overflow-wrap:anywhere; text-align:right; }}
        .quality-detail-panel .quality-result-status {{ align-self:center; }}
        .quality-detail-subheading {{ color:var(--text-secondary); font-size:.68rem; font-weight:750; letter-spacing:.08em; margin:1rem 0 .45rem; }}
        [class*="st-key-quality-review-visual-summary"], [class*="st-key-quality-review-detail-panels"] {{ margin:1.5rem 0; }}
        @media (max-width:800px) {{
            [class*="st-key-quality-review-visual-summary"] [data-testid="stHorizontalBlock"], [class*="st-key-quality-review-detail-panels"] [data-testid="stHorizontalBlock"] {{ flex-direction:column; gap:1rem; }}
            [class*="st-key-quality-review-visual-summary"] [data-testid="stHorizontalBlock"] > div, [class*="st-key-quality-review-detail-panels"] [data-testid="stHorizontalBlock"] > div {{ width:100%!important; }}
        }}
        .html-table-badge--rule {{ background:color-mix(in srgb, var(--accent) 8%, var(--surface)); border-color:color-mix(in srgb, var(--accent) 26%, var(--border)); color:var(--text); }}
        .connection-status {{ align-items:center; border:1px solid var(--border); border-radius:999px; display:inline-flex; font-size:.7rem; gap:.3rem; line-height:1.25; padding:.2rem .5rem; white-space:nowrap; }}
        .connection-status--connected {{ background:color-mix(in srgb, #4E9A62 14%, var(--surface)); border-color:color-mix(in srgb, #4E9A62 38%, var(--border)); color:color-mix(in srgb, var(--text) 68%, #4E9A62); }}
        .html-table-secondary {{ color:var(--text-secondary); display:block; font-size:.78rem; line-height:1.45; overflow-wrap:normal; word-break:normal; }}
        [class*="st-key-html-table-interactive-"]:not([class*="st-key-html-table-interactive-row-"]) {{ background:var(--surface); border:1px solid var(--border); border-radius:10px; margin:.7rem 0 1.1rem; min-width:900px; overflow-x:auto; overflow-y:hidden; width:100%; }}
        [class*="st-key-html-table-interactive-"]:not([class*="st-key-html-table-interactive-row-"])[data-testid="stVerticalBlock"], [class*="st-key-html-table-interactive-"]:not([class*="st-key-html-table-interactive-row-"]) > [data-testid="stVerticalBlock"] {{ gap:0; }}
        [class*="st-key-html-table-interactive-"]:not([class*="st-key-html-table-interactive-row-"]) [data-testid="stHorizontalBlock"] {{ align-items:center; gap:0; margin:0; min-width:900px; width:100%; }}
        [class*="st-key-html-table-interactive-"] [data-testid="stHorizontalBlock"] > div {{ align-items:center; align-self:stretch; border-left:1px solid color-mix(in srgb, var(--border) 45%, transparent); box-sizing:border-box; display:flex; min-width:0; padding:0 .9rem; }}
        [class*="st-key-html-table-interactive-"] [data-testid="stHorizontalBlock"] > div:first-child {{ border-left:0; }}
        [class*="st-key-html-table-interactive-"]:not([class*="st-key-html-table-interactive-row-"]) > div:first-child {{ background:var(--elevated); border-bottom:1px solid var(--border); }}
        .html-table-interactive-header {{ align-items:center; box-sizing:border-box; color:var(--text); display:flex; font-size:.74rem; font-weight:750; line-height:1.35; min-height:0; padding:.72rem 0 .84rem; width:100%; white-space:nowrap; }}
        .html-table-interactive-cell {{ align-items:center; box-sizing:border-box; color:var(--text); display:flex; font-size:.78rem; height:100%; line-height:1.45; min-height:0; padding:.88rem 0 1.16rem; vertical-align:middle; width:100%; }}
        .html-table-interactive-cell--special {{ padding-bottom:.86rem; padding-top:.86rem; }}
        .html-table-interactive-header p, .html-table-interactive-cell p {{ margin:0; }}
        .html-table-interactive-cell > .html-table-badge, .html-table-interactive-cell > .html-table-column-name, .html-table-interactive-cell > .html-table-secondary {{ line-height:1.35; margin:0; }}
        [class*="st-key-html-table-interactive-row-"] {{ background:var(--surface); border-bottom:1px solid color-mix(in srgb, var(--border) 65%, transparent); transition:background 140ms ease; }}
        [class*="st-key-html-table-interactive-row-"]:nth-of-type(even) {{ background:color-mix(in srgb, var(--elevated) 24%, var(--surface)); }}
        [class*="st-key-html-table-interactive-row-"]:hover {{ background:var(--hover); }}
        [class*="st-key-html-table-interactive-row-"] [data-testid="stHorizontalBlock"] > div:last-child {{ align-items:center; display:flex; justify-content:center; min-width:0; padding-left:0; padding-right:0; }}
        [class*="st-key-html-table-interactive-row-"] [data-testid="stHorizontalBlock"] > div:last-child [data-testid="stVerticalBlock"], [class*="st-key-html-table-interactive-row-"] [data-testid="stHorizontalBlock"] > div:last-child [data-testid="stButton"] {{ align-items:center; display:flex; justify-content:center; height:100%; }}
        [class*="st-key-html-table-interactive-"] [data-testid="stButton"] {{ align-items:center; display:flex; justify-content:center; margin:0; width:100%; }}
        [class*="st-key-html-table-interactive-"] [data-testid="stButton"] button {{ align-items:center; color:var(--text-secondary); display:flex; font-size:.7rem; height:26px; justify-content:center; min-height:26px; min-width:32px; padding:0; white-space:nowrap; width:32px; }}
        [class*="st-key-html-table-interactive-"] [data-testid="stButton"] button:hover {{ background:var(--hover); border-color:var(--accent); color:var(--accent); transform:none; }}
        [class*="st-key-html-table-action-"] [data-testid="stButton"] {{ width:auto; }}
        [class*="st-key-html-table-action-"] [data-testid="stButton"] button {{ min-width:0; padding:0 .45rem; width:auto; }}
        [class*="st-key-html-table-action-session-connections-"] [data-testid="stVerticalBlock"] {{ align-items:center; gap:0; justify-content:center; }}
        [class*="st-key-html-table-action-session-connections-"] [data-testid="stButton"] button {{ background:color-mix(in srgb, #D16A5B 14%, var(--surface)); border:1px solid color-mix(in srgb, #D16A5B 52%, var(--border)); border-radius:999px; color:color-mix(in srgb, var(--text) 62%, #D16A5B); font-size:.7rem; height:auto; line-height:1.25; min-height:0; min-width:0; padding:.2rem .5rem; width:auto; }}
        [class*="st-key-html-table-action-session-connections-"] [data-testid="stButton"] button:hover {{ background:color-mix(in srgb, #D16A5B 24%, var(--surface)); border-color:#D16A5B; color:var(--text); }}
        [class*="st-key-html-table-action-session-connections-"] [data-testid="stButton"] button:focus-visible {{ border-color:#D16A5B; box-shadow:0 0 0 2px color-mix(in srgb, #D16A5B 30%, transparent); outline:none; }}
        [class*="st-key-html-table-interactive-row-session-connections-"] [data-testid="stHorizontalBlock"] > div {{ align-items:center; }}
        #html-table-connected-quality-sources .html-table-cell {{ padding:.88rem .9rem 1.16rem; }}
        #html-table-connected-quality-sources .html-table-cell--special {{ padding:.86rem .9rem; }}
        #html-table-connected-quality-sources th {{ padding:.72rem .9rem .84rem; }}
        [class*="st-key-html-table-interactive-"]:not([class*="st-key-html-table-interactive-row-"]) > div:first-child [data-testid="stHorizontalBlock"] > div:last-child .html-table-interactive-header {{ justify-content:center; text-align:center; width:100%; }}
        [data-testid="stExpander"] details > summary,
        [data-testid="stExpander"] details[open] > summary,
        [data-testid="stExpander"] details > summary:hover,
        [data-testid="stExpander"] details > summary:focus,
        [data-testid="stExpander"] details > summary:focus-visible,
        [data-testid="stExpander"] details > summary:active {{ background:var(--surface-secondary)!important; border-color:var(--border)!important; color:var(--text)!important; outline-color:var(--accent); }}
        [data-testid="stExpander"] details > summary > div,
        [data-testid="stExpander"] details > summary p {{ background:transparent!important; color:var(--text)!important; }}
        [data-testid="stExpander"] details > summary svg,
        [data-testid="stExpander"] details > summary [data-testid="stExpanderToggleIcon"] {{ color:var(--text-secondary)!important; fill:currentColor!important; }}
        [data-testid="stExpander"] details > summary:hover svg,
        [data-testid="stExpander"] details > summary:focus-visible svg {{ color:var(--accent)!important; }}
        .documentation-summary-gap {{ height:1.25rem; }}
        .documentation-subsection-title {{ margin-top:.75rem; }}
        [class*="st-key-quality-run-quality-checks"] {{ margin-top:1.5rem; }}
        [class*="st-key-quality-add-rule-button"] button[kind="primary"]:not(:disabled), [class*="st-key-quality-reset-common-checks"] button[kind="primary"]:not(:disabled), [class*="st-key-quality-add-business-rule"] button[kind="primary"]:not(:disabled), [class*="st-key-quality-run-quality-checks"] button[kind="primary"]:not(:disabled) {{ background:var(--accent); border-color:var(--accent); color:#FFFFFF; }}
        [class*="st-key-quality-add-rule-button"] button[kind="primary"]:not(:disabled):hover, [class*="st-key-quality-reset-common-checks"] button[kind="primary"]:not(:disabled):hover, [class*="st-key-quality-add-business-rule"] button[kind="primary"]:not(:disabled):hover, [class*="st-key-quality-run-quality-checks"] button[kind="primary"]:not(:disabled):hover {{ background:color-mix(in srgb, var(--accent) 86%, #192B37); border-color:color-mix(in srgb, var(--accent) 86%, #192B37); color:#FFFFFF; }}
        [class*="st-key-quality-add-rule-button"] button[kind="primary"]:disabled, [class*="st-key-quality-run-quality-checks"] button[kind="primary"]:disabled {{ background:var(--button-primary-disabled-bg); border-color:var(--border); color:var(--button-primary-disabled-text); }}
        @media (max-width:800px) {{
            .metadata-scan-workflow {{ width:100%; }}
            .quick-card {{ min-height:74px; }}
        }}
        @media (max-width:640px) {{
            .app-brand {{ gap:.5rem; }}
            .brand-name {{ font-size:.92rem; }}
            .brand-subtitle {{ font-size:.66rem; }}
            .section-kicker {{ margin-top:1.15rem; }}
            .documentation-count-breakdown {{ margin-top:.25rem; }}
        }}
        [class*="st-key-auth-page-shell"] {{ min-height:calc(100vh - 3.5rem); padding:1rem 0 2rem; position:relative; }}
        [class*="st-key-auth-theme-control"] {{ display:flex; justify-content:flex-end; margin-bottom:.2rem; }}
        [class*="st-key-auth-theme-control"] [data-testid="stButton"] {{ width:auto; }}
        [class*="st-key-auth-theme-control"] [data-testid="stButton"] button {{ align-items:center; background:transparent; border:1px solid transparent; border-radius:999px; color:var(--icon-secondary); height:34px; justify-content:center; min-height:34px; min-width:34px; padding:0; width:34px; }}
        [class*="st-key-auth-theme-control"] [data-testid="stButton"] button:hover {{ background:var(--hover); border-color:var(--border); color:var(--accent); }}
        [class*="st-key-auth-theme-control"] [data-testid="stButton"] button:focus-visible {{ border-color:var(--accent); box-shadow:0 0 0 2px color-mix(in srgb, var(--accent) 28%, transparent); outline:none; }}
        [class*="st-key-auth-page-shell"] > [data-testid="stHorizontalBlock"] {{ align-items:stretch; gap:clamp(2rem,6vw,6rem); margin:clamp(2rem,8vh,5.5rem) auto 0; max-width:1120px; }}
        [class*="st-key-auth-page-shell"] > [data-testid="stHorizontalBlock"] > div {{ align-self:stretch; min-width:0; }}
        .auth-brand-panel {{ align-items:flex-start; display:flex; flex-direction:column; justify-content:flex-start; min-height:25rem; padding:clamp(4rem,10vh,6.5rem) 0 1.5rem; }}
        .auth-brand-mark {{ display:grid; gap:.35rem; grid-template-columns:repeat(2,1.15rem); margin-bottom:1.7rem; transform:rotate(-8deg); }}
        .auth-brand-mark span {{ background:var(--accent); border-radius:4px; display:block; height:1.15rem; width:1.15rem; }}
        .auth-brand-mark span:nth-child(2), .auth-brand-mark span:nth-child(3) {{ background:color-mix(in srgb, var(--accent) 58%, var(--surface)); }}
        .auth-brand-eyebrow, .auth-card-eyebrow {{ color:var(--accent); font-size:.67rem; font-weight:850; letter-spacing:.14em; }}
        .auth-brand-heading {{ color:var(--text); font-size:clamp(1.7rem,3vw,2.55rem); font-weight:800; letter-spacing:-.035em; line-height:1.08; margin-top:.8rem; max-width:28rem; }}
        .auth-brand-copy {{ color:var(--text-secondary); font-size:.95rem; line-height:1.55; margin-top:1.3rem; }}
        .auth-brand-note {{ border-left:2px solid var(--accent); color:var(--muted); font-size:.76rem; line-height:1.45; margin-top:2rem; max-width:23rem; padding-left:.75rem; }}
        [class*="st-key-auth-card-"] {{ box-sizing:border-box; margin:0 0 0 auto; max-width:520px; padding:2rem 2.15rem 1.75rem; width:100%; }}
        [class*="st-key-auth-card-"] .auth-card-eyebrow {{ text-align:left; }}
        [class*="st-key-auth-card-"] .auth-title {{ font-size:1.8rem; letter-spacing:-.025em; margin: .55rem 0 .3rem; text-align:left; }}
        [class*="st-key-auth-card-"] .auth-copy {{ margin-bottom:1.35rem; text-align:left; }}
        [class*="st-key-auth-card-"] [data-testid="stForm"] {{ width:100%; }}
        [class*="st-key-auth-card-"] [data-testid="stFormSubmitButton"] button {{ min-height:2.65rem; }}
        [class*="st-key-auth-card-"] [data-testid="stPageLink"] {{ margin-top:.7rem; }}
        [class*="st-key-auth-card-"] .auth-secondary {{ margin-top:1.2rem; }}
        @media (max-width:800px) {{
            [class*="st-key-auth-page-shell"] {{ min-height:0; }}
            [class*="st-key-auth-page-shell"] > [data-testid="stHorizontalBlock"] {{ flex-direction:column; gap:1.2rem; margin-top:1rem; }}
            [class*="st-key-auth-page-shell"] > [data-testid="stHorizontalBlock"] > div {{ width:100%!important; }}
            .auth-brand-panel {{ min-height:0; padding:.75rem 0 0; }}
            .auth-brand-mark {{ margin-bottom:1rem; }}
            .auth-brand-heading {{ font-size:1.65rem; max-width:34rem; }}
            .auth-brand-note {{ margin-top:1rem; }}
            [class*="st-key-auth-card-"] {{ margin:0 auto; max-width:520px; padding:1.5rem 1.25rem 1.35rem; }}
        }}
        [class*="st-key-auth-page-shell"] {{ box-sizing:border-box; min-height:calc(100vh - 2.5rem); padding:.25rem 0 1rem; }}
        [class*="st-key-auth-page-shell"] > [data-testid="stHorizontalBlock"] {{ margin-top:clamp(.75rem,4vh,2.5rem); }}
        .auth-brand-mark {{ margin-bottom:1rem; }}
        .auth-data-visual {{ height:5.5rem; margin:0 0 1.2rem .1rem; position:relative; width:16rem; }}
        .auth-data-visual::before, .auth-data-visual::after {{ background:var(--border); content:""; height:1px; left:1.25rem; position:absolute; transform-origin:left center; width:8rem; }}
        .auth-data-visual::before {{ top:1.2rem; transform:rotate(21deg); }}
        .auth-data-visual::after {{ top:3.9rem; transform:rotate(-20deg); }}
        .auth-data-visual i {{ background:var(--surface); border:2px solid var(--accent); border-radius:50%; display:block; height:.8rem; position:absolute; width:.8rem; z-index:1; }}
        .auth-data-visual i:nth-child(1) {{ left:.85rem; top:.85rem; }}
        .auth-data-visual i:nth-child(2) {{ left:7.8rem; top:2.25rem; }}
        .auth-data-visual i:nth-child(3) {{ left:1.1rem; top:4.15rem; }}
        .auth-data-visual i:nth-child(4) {{ border-color:var(--text-secondary); left:9.6rem; top:3.45rem; }}
        .auth-data-visual b {{ background:var(--accent); border-radius:3px; display:block; height:1.35rem; position:absolute; transform:rotate(45deg); width:1.35rem; }}
        .auth-data-visual b:nth-of-type(1) {{ left:4rem; top:0; }}
        .auth-data-visual b:nth-of-type(2) {{ background:color-mix(in srgb, var(--accent) 58%, var(--surface)); left:4.1rem; top:4rem; }}
        .hero-layout {{ align-items:center; display:flex; gap:2rem; justify-content:space-between; }}
        .hero-copy-block {{ min-width:0; }}
        .hero-visual {{ flex:0 0 15rem; height:8rem; position:relative; }}
        .hero-visual-line {{ background:var(--border); height:2px; left:1.2rem; position:absolute; transform-origin:left center; width:9.5rem; }}
        .hero-visual-line--one {{ top:2rem; transform:rotate(20deg); }}
        .hero-visual-line--two {{ top:5.5rem; transform:rotate(-18deg); }}
        .hero-visual-node {{ align-items:center; background:var(--accent); border-radius:8px; color:#FFFFFF; display:flex; font-size:1.15rem; font-weight:800; height:2.2rem; justify-content:center; position:absolute; width:2.2rem; }}
        .hero-visual-node--one {{ left:0; top:.9rem; }}
        .hero-visual-node--two {{ background:var(--surface); border:2px solid var(--accent); color:var(--accent); left:5.5rem; top:2.85rem; }}
        .hero-visual-node--three {{ background:var(--text); color:var(--bg); left:10.8rem; top:4.7rem; }}
        .hero-visual-caption {{ bottom:-.1rem; color:var(--muted); font-size:.57rem; font-weight:800; letter-spacing:.11em; line-height:1.45; position:absolute; right:0; text-align:right; }}
        .hero-visual-caption span {{ color:var(--accent); }}
        .hero-panel {{ padding:1rem 1.35rem; }}
        .hero-title {{ font-size:clamp(1.4rem,2.35vw,1.95rem); }}
        .hero-description {{ max-width:46rem; }}
        .status-card {{ min-height:104px; padding:.65rem .8rem; }}
        .status-card:hover {{ transform:translateY(-1px); }}
        @media (max-width:800px) {{
            .hero-layout {{ align-items:flex-start; }}
            .hero-visual {{ display:none; }}
            [class*="st-key-auth-page-shell"] > [data-testid="stHorizontalBlock"] {{ margin-top:.75rem; }}
        }}
        @media (max-width:520px) {{
            .auth-brand-panel {{ display:none; }}
            [class*="st-key-auth-page-shell"] > [data-testid="stHorizontalBlock"] {{ margin-top:.75rem; }}
        }}
        .product-mark-svg {{ display:block; }}
        .process-stepper {{ align-items:flex-start; display:flex; margin:1rem auto 1.5rem; max-width:920px; width:100%; }}
        .process-step {{ align-items:center; display:flex; flex:1 1 0; flex-direction:column; min-width:0; position:relative; text-align:center; }}
        .process-step-number {{ color:var(--accent); font-size:.64rem; font-weight:850; letter-spacing:.12em; line-height:1; margin-bottom:.38rem; }}
        .process-step-node {{ align-items:center; background:var(--surface); border:1px solid var(--accent); border-radius:9px; color:var(--accent); display:flex; height:2.25rem; justify-content:center; transition:background 180ms ease,border-color 180ms ease,box-shadow 180ms ease,transform 180ms ease; width:2.25rem; }}
        .process-step-node svg {{ color:currentColor; height:1.1rem; width:1.1rem; }}
        .process-step-label {{ color:var(--text); font-size:.71rem; font-weight:800; letter-spacing:.035em; line-height:1.2; margin-top:.45rem; white-space:nowrap; }}
        .process-step-connector {{ align-items:center; display:flex; flex:0 1 5rem; height:2.25rem; justify-content:center; margin:1.05rem .35rem 0; min-width:1.5rem; }}
        .process-step-connector span {{ background:var(--border); display:block; height:1px; position:relative; width:100%; }}
        .process-step-connector span::after {{ border-right:1px solid var(--accent); border-top:1px solid var(--accent); content:""; height:.32rem; position:absolute; right:0; top:-.15rem; transform:rotate(45deg); width:.32rem; }}
        .process-step:hover .process-step-node {{ background:var(--surface-secondary); box-shadow:0 3px 10px rgba(25,43,55,.1); transform:translateY(-1px); }}
        .process-stepper .process-step:nth-child(1) {{ animation:process-step-in 360ms ease-out both; }}
        .process-stepper .process-step:nth-child(3) {{ animation:process-step-in 360ms 55ms ease-out both; }}
        .process-stepper .process-step:nth-child(5) {{ animation:process-step-in 360ms 110ms ease-out both; }}
        .process-stepper .process-step:nth-child(7) {{ animation:process-step-in 360ms 165ms ease-out both; }}
        .process-stepper .process-step:nth-child(9) {{ animation:process-step-in 360ms 220ms ease-out both; }}
        @keyframes process-step-in {{ from {{ opacity:0; transform:translateY(4px); }} to {{ opacity:1; transform:translateY(0); }} }}
        .hero-visual {{ align-items:center; display:flex; flex:0 0 clamp(12rem,25%,15rem); justify-content:center; }}
        .hero-visual-node {{ box-shadow:0 2px 8px rgba(25,43,55,.08); }}
        @media (max-width:800px) {{
            .process-stepper {{ gap:.2rem; margin-bottom:1rem; }}
            .process-step-connector {{ flex-basis:2rem; margin-left:.1rem; margin-right:.1rem; }}
            .process-step-label {{ font-size:.64rem; }}
        }}
        @media (max-width:560px) {{
            .process-stepper {{ align-items:stretch; flex-direction:column; gap:.45rem; }}
            .process-step {{ align-items:flex-start; flex-direction:row; gap:.55rem; text-align:left; }}
            .process-step-number {{ min-width:1.4rem; padding-top:.55rem; }}
            .process-step-node {{ flex:0 0 2rem; height:2rem; width:2rem; }}
            .process-step-label {{ align-self:center; margin-top:0; }}
            .process-step-connector {{ align-self:flex-start; flex:0 0 1rem; height:1rem; margin:0 0 0 2.2rem; width:1px; }}
            .process-step-connector span {{ height:100%; width:1px; }}
            .process-step-connector span::after {{ border-bottom:1px solid var(--accent); border-right:0; border-top:0; bottom:0; right:-.15rem; top:auto; transform:rotate(45deg); }}
        }}
        [class*="st-key-auth-card-topbar-"] {{ min-height:2.15rem; position:relative; }}
        [class*="st-key-auth-card-topbar-"] [class*="st-key-auth-theme-control-"] {{ background:transparent!important; position:absolute; right:0; top:-.2rem; z-index:2; }}
        [class*="st-key-auth-card-topbar-"] [class*="st-key-auth-theme-control-"] > [data-testid="stVerticalBlock"] {{ background:transparent!important; padding:0!important; }}
        [class*="st-key-auth-card-topbar-"] [class*="st-key-auth-theme-control-"] [data-testid="stButton"] button {{ background:var(--surface)!important; border:1px solid var(--border); color:var(--icon-secondary)!important; height:32px; min-height:32px; min-width:32px; width:32px; }}
        [class*="st-key-auth-card-topbar-"] [class*="st-key-auth-theme-control-"] [data-testid="stButton"] button:hover {{ background:var(--hover)!important; border-color:var(--accent); color:var(--accent)!important; }}
        [class*="st-key-auth-card-topbar-"] [class*="st-key-auth-theme-control-"] [data-testid="stButton"] button:focus-visible {{ box-shadow:0 0 0 2px color-mix(in srgb, var(--accent) 30%, transparent); outline:none; }}
        .auth-card-eyebrow-row {{ align-items:center; display:flex; gap:.45rem; min-height:2rem; padding-right:2.4rem; }}
        .auth-card-mark {{ align-items:center; background:var(--accent); border-radius:5px; color:#FFFFFF; display:inline-flex; flex:0 0 1.55rem; height:1.55rem; justify-content:center; width:1.55rem; }}
        .auth-card-mark .product-mark-svg {{ height:1rem; width:1rem; }}
        [class*="st-key-auth-card-"] [data-testid="stTextInput"] label, [class*="st-key-auth-card-"] [data-testid="stWidgetLabel"], [class*="st-key-auth-card-"] [data-testid="stWidgetLabel"] p {{ color:var(--text)!important; }}
        [class*="st-key-auth-card-"] [data-baseweb="input"], [class*="st-key-auth-card-"] [data-baseweb="input"] > div, [class*="st-key-auth-card-"] [data-baseweb="select"] {{ background:var(--input-bg)!important; border-color:var(--input-border)!important; color:var(--input-text)!important; }}
        [class*="st-key-auth-card-"] [data-baseweb="input"] input, [class*="st-key-auth-card-"] [data-baseweb="textarea"] textarea {{ background:transparent!important; color:var(--input-text)!important; caret-color:var(--input-focus)!important; -webkit-text-fill-color:var(--input-text)!important; opacity:1!important; }}
        [class*="st-key-auth-card-"] [data-baseweb="input"] input::placeholder, [class*="st-key-auth-card-"] [data-baseweb="textarea"] textarea::placeholder {{ color:var(--input-placeholder)!important; opacity:1!important; }}
        [class*="st-key-auth-card-"] [data-baseweb="input"] svg, [class*="st-key-auth-card-"] [data-baseweb="input"] button {{ color:var(--text-secondary)!important; fill:currentColor!important; opacity:1!important; }}
        [class*="st-key-auth-card-"] [data-baseweb="input"]:focus-within {{ background:var(--input-bg)!important; border-color:var(--input-focus)!important; box-shadow:0 0 0 1px var(--input-focus)!important; }}
        [class*="st-key-auth-card-"] [data-testid="stCaptionContainer"], [class*="st-key-auth-card-"] [data-testid="stCaptionContainer"] p {{ color:var(--muted)!important; }}
        [class*="st-key-auth-card-"] [data-testid="stFormSubmitButton"] p {{ color:#FFFFFF!important; }}
        [class*="st-key-auth-card-"] [data-testid="stAlert"] {{ background:var(--surface-secondary); border-color:var(--border); color:var(--text); }}
        [class*="st-key-auth-card-"] [data-testid="stPageLink"] {{ margin-top:.65rem; width:max-content; }}
        [class*="st-key-auth-card-"] [data-testid="stPageLink"] a {{ align-items:center; background:var(--surface); border:1px solid var(--border); border-radius:8px; color:var(--text)!important; display:flex; font-size:.76rem; font-weight:650; min-height:34px; padding:.35rem .75rem; white-space:nowrap; }}
        [class*="st-key-auth-card-"] [data-testid="stPageLink"] a:hover {{ background:var(--hover); border-color:var(--text-secondary); color:var(--text)!important; }}
        [class*="st-key-auth-card-"] [data-testid="stPageLink"] a:focus-visible {{ border-color:var(--accent); box-shadow:0 0 0 2px color-mix(in srgb, var(--accent) 28%, transparent); outline:none; }}
        [class*="st-key-auth-card-"] [data-testid="stButton"] button[kind="secondary"] {{ background:var(--surface); border:1px solid var(--border); color:var(--text); min-height:34px; }}
        [class*="st-key-auth-card-"] [data-testid="stButton"] button[kind="secondary"]:hover {{ background:var(--hover); border-color:var(--text-secondary); color:var(--text); }}
        [class*="st-key-login-secondary-actions"] {{ box-sizing:border-box; max-width:100%; width:100%; }}
        [class*="st-key-login-secondary-actions"] [data-testid="stHorizontalBlock"] {{ align-items:center; box-sizing:border-box; gap:.75rem; justify-content:space-between!important; margin:0!important; max-width:100%; width:100%!important; }}
        [class*="st-key-login-secondary-actions"] [data-testid="stHorizontalBlock"] > div {{ box-sizing:border-box; flex:0 0 auto!important; min-width:0; max-width:100%; }}
        [class*="st-key-login-secondary-actions"] [data-testid="stPageLink"] {{ display:flex; flex:0 0 auto!important; margin-top:0; }}
        [class*="st-key-login-secondary-actions"] [data-testid="stPageLink"] a {{ min-height:34px; margin:0!important; width:auto!important; }}
        @media (max-width:560px) {{
            [class*="st-key-login-secondary-actions"] [data-testid="stHorizontalBlock"] {{ align-items:stretch; flex-direction:column; gap:.15rem; }}
            [class*="st-key-login-secondary-actions"] [data-testid="stPageLink"], [class*="st-key-login-secondary-actions"] [data-testid="stPageLink"] a {{ width:100%; }}
            [class*="st-key-login-secondary-actions"] [data-testid="stPageLink"] a {{ justify-content:center; }}
        }}
        /* Auth pages: keep one intentional surface and a compact shared top row. */
        [class*="st-key-auth-card-topbar-"] {{ align-items:center; background:transparent!important; border:0!important; border-radius:0!important; box-shadow:none!important; display:block; margin:0!important; padding:0!important; width:100%; }}
        [class*="st-key-auth-card-topbar-"] > [data-testid="stVerticalBlock"] {{ background:transparent!important; border:0!important; box-shadow:none!important; padding:0!important; }}
        [class*="st-key-auth-card-topbar-"] [class*="st-key-auth-theme-control-"] {{ align-items:center; display:flex; height:32px; margin:0!important; padding:0!important; right:0; width:32px!important; }}
        [class*="st-key-auth-card-topbar-"] [class*="st-key-auth-theme-control-"] > [data-testid="stVerticalBlock"] {{ align-items:center; display:flex; height:32px; margin:0!important; padding:0!important; width:32px!important; }}
        [class*="st-key-auth-card-topbar-"] [class*="st-key-auth-theme-control-"] [data-testid="stButton"] {{ height:32px; margin:0!important; width:32px!important; }}
        [class*="st-key-auth-card-topbar-"] [class*="st-key-auth-theme-control-"] [data-testid="stButton"] button {{ background:transparent!important; border:1px solid transparent; border-radius:999px; color:var(--icon-secondary)!important; height:32px; min-height:32px; min-width:32px; padding:0; width:32px; }}
        [class*="st-key-auth-card-topbar-"] [class*="st-key-auth-theme-control-"] [data-testid="stButton"] button:hover {{ background:var(--hover)!important; border-color:var(--border); color:var(--accent)!important; }}
        [class*="st-key-auth-card-topbar-"] [class*="st-key-auth-theme-control-"] [data-testid="stButton"] button:focus-visible {{ border-color:var(--accent); box-shadow:0 0 0 2px color-mix(in srgb, var(--accent) 30%, transparent); outline:none; }}
        [class*="st-key-auth-card-"] [data-testid="stForm"] {{ background:transparent!important; border:0!important; border-radius:0!important; box-shadow:none!important; margin:0!important; padding:0!important; }}
        [class*="st-key-auth-card-"] form[data-testid="stForm"] {{ background:transparent!important; border:0!important; box-shadow:none!important; padding:0!important; }}
        [class*="st-key-auth-card-"] [data-testid="stForm"] > [data-testid="stVerticalBlock"] {{ background:transparent!important; padding:0!important; }}
        [class*="st-key-auth-card-"] [data-baseweb="input"] input:-webkit-autofill {{ -webkit-text-fill-color:var(--input-text)!important; box-shadow:0 0 0 1000px var(--input-bg) inset!important; }}
        [class*="st-key-auth-card-"] [data-testid="stAlert"] p {{ color:var(--text)!important; }}
        /* Streamlit tooltips are portalled; keep the shared theme readable in both modes. */
        [data-baseweb="tooltip"], [data-testid="stTooltip"], [role="tooltip"] {{ background:var(--surface-elevated)!important; border:1px solid var(--border)!important; border-radius:6px; color:var(--text)!important; }}
        [data-baseweb="tooltip"] *, [data-testid="stTooltip"] *, [role="tooltip"] * {{ color:var(--text)!important; }}
        </style>
        """,
        unsafe_allow_html=True,
    )
