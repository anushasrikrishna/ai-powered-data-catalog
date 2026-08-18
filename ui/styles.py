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
        :root {{ --bg:{colors['background']}; --surface:{colors['surface']}; --surface-secondary:{colors['secondary']}; --surface-elevated:{colors['elevated']}; --elevated:{colors['elevated']}; --text:{colors['text']}; --text-secondary:{colors['secondary_text']}; --muted:{colors['muted']}; --border:{colors['border']}; --hover:{colors['hover']}; --accent:{colors['accent']}; --icon-primary:{colors['icon_primary']}; --icon-secondary:{colors['icon_secondary']}; --icon-accent:{colors['icon_accent']}; --button-secondary-text:{colors['button_secondary_text']}; --input-bg:{colors['input_bg']}; --input-hover:{colors['input_hover']}; --input-border:{colors['input_border']}; --input-text:{colors['input_text']}; --input-placeholder:{colors['input_placeholder']}; --input-focus:{colors['input_focus']}; --disabled-bg:{colors['disabled_bg']}; --disabled-text:{colors['disabled_text']}; --spinner-active:{colors['spinner_active']}; --spinner-track:{colors['spinner_track']}; --table-distinct:{table_distinct}; --table-range:{table_range}; --table-sample:{table_sample}; --source-blue:{source_blue}; --source-postgres:{source_postgres}; }}
        .stApp {{ background:var(--bg); color:var(--text); }}
        .html-table-wrapper {{ background:var(--surface); border:1px solid var(--border); border-radius:10px; margin:.7rem 0 1.1rem; overflow:hidden; width:100%; }}
        .html-table-scroll {{ overflow-x:auto; width:100%; }}
        .html-table {{ border-collapse:collapse; color:var(--text); font-family:inherit; min-width:900px; table-layout:auto; width:100%; }}
        .html-table-cell {{ border-left:1px solid color-mix(in srgb, var(--border) 45%, transparent); font-size:.78rem; padding:.62rem .8rem; vertical-align:top; }}
        .html-table-cell:first-child {{ border-left:0; }}
        .html-table th {{ background:var(--elevated); border-bottom:1px solid var(--border); color:var(--text); font-size:.74rem; font-weight:750; letter-spacing:.01em; padding:.68rem .8rem; text-align:left; white-space:nowrap; }}
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
        .html-table--metadata td:nth-child(7) {{ color:var(--table-distinct); font-weight:600; }}
        .html-table--metadata td:nth-child(8), .html-table--metadata td:nth-child(9) {{ color:var(--table-range); }}
        .html-table--metadata td:nth-child(11) {{ color:var(--table-sample); }}
        .html-table--catalog td:nth-child(6), .html-table--catalog td:nth-child(7) {{ font-variant-numeric:tabular-nums; font-weight:600; text-align:right; }}
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
        .app-header {{ align-items:center; border-bottom:1px solid var(--border); display:flex; margin:0 auto .25rem; max-width:1320px; padding:.7rem 0 .9rem; }} .app-brand {{ align-items:center; display:flex; gap:.7rem; }} .brand-mark {{ align-items:center; background:var(--accent); border-radius:8px; color:#FFFFFF; display:inline-flex; height:32px; justify-content:center; width:32px; }} .brand-name {{ color:var(--text); font-size:1rem; font-weight:800; line-height:1.1; }} .brand-subtitle {{ color:var(--muted); font-size:.7rem; margin-top:.25rem; }}
        .app-nav-spacer {{ margin:0 auto .25rem; max-width:1320px; }}
        .app-nav-divider {{ border-bottom:1px solid var(--border); margin:.45rem auto 1.2rem; max-width:1320px; }}
        [data-testid="stPageLink"] a {{ align-items:center; background:transparent; border:1px solid transparent; border-bottom:2px solid transparent; border-radius:8px 8px 0 0; color:var(--text-secondary); display:flex; font-size:.86rem; font-weight:650; justify-content:center; min-height:38px; padding:.45rem .6rem; text-align:center; transition:background 180ms ease,border-color 180ms ease,color 180ms ease; }}
        [data-testid="stPageLink"] a:hover {{ background:var(--hover); color:var(--text); transform:none; }}
        [data-testid="stPageLink"] a[aria-current="page"] {{ border-bottom-color:var(--accent); color:var(--accent); font-weight:750; }}
        [data-testid="stPageLink"] a svg, [data-testid="stPageLink"] a [data-testid="stIconMaterial"], [data-testid="stPageLink"] a .material-symbols-rounded, [data-testid="stPageLink"] a .material-symbols-outlined {{ color:currentColor!important; fill:currentColor!important; }}
        .sidebar-heading,.section-kicker {{ color:var(--accent); font-size:.68rem; font-weight:800; letter-spacing:.13em; }} .sidebar-heading {{ margin-bottom:.55rem; }} .sidebar-item {{ border-bottom:1px solid var(--border); padding:.75rem .25rem; }} .sidebar-label,.sidebar-value {{ display:block; }} .sidebar-label {{ color:var(--text-secondary); font-size:.75rem; }} .sidebar-value {{ color:var(--text); font-size:.82rem; font-weight:650; margin-top:.18rem; }} .sidebar-footer {{ border-top:1px solid var(--border); color:var(--muted); font-size:.7rem; margin-top:2rem; padding:.8rem .25rem; }}
        .hero-panel {{ background:var(--surface-secondary); border:1px solid var(--border); border-left:3px solid var(--accent); border-radius:12px; margin:1.35rem 0 .75rem; padding:1.5rem 1.65rem; }} .hero-eyebrow {{ color:var(--accent); font-size:.68rem; font-weight:800; letter-spacing:.13em; }} .hero-title {{ color:var(--text); font-size:clamp(1.35rem,2.5vw,2rem); font-weight:750; letter-spacing:-.025em; margin-top:.55rem; }} .hero-description {{ margin-top:.5rem; }} .section-kicker {{ margin-top:2rem; }}
        .metric-card,.feature-card,.empty-state,.report-card,.status-card,.quick-card {{ background:var(--surface); border:1px solid var(--border); border-radius:12px; box-shadow:0 4px 16px rgba(25,43,55,.06); }} .metric-card {{ min-height:122px; padding:1rem 1.1rem; }} .metric-value {{ color:var(--accent); font-size:1.55rem; font-weight:800; }} .metric-label {{ color:var(--text); font-size:.84rem; font-weight:700; margin-top:.3rem; }} .metric-detail,.card-description {{ color:var(--muted); font-size:.76rem; line-height:1.45; margin-top:.35rem; }} .status-card {{ min-height:150px; padding:.9rem 1rem; }} .status-icon,.workflow-icon,.quick-icon {{ color:var(--icon-accent); height:20px; width:20px; }} .status-label {{ color:var(--text-secondary); font-size:.75rem; margin-top:.45rem; }} .status-value {{ color:var(--text); font-size:1.35rem; font-weight:800; margin-top:.15rem; }} .status-detail {{ color:var(--muted); font-size:.7rem; line-height:1.35; margin-top:.2rem; }} .feature-card {{ min-height:142px; margin:.5rem 0; padding:1.2rem; transition:transform 200ms ease,box-shadow 200ms ease,border-color 200ms ease; }} .feature-card:hover,.report-card:hover,.status-card:hover,.quick-card:hover {{ border-color:var(--accent); box-shadow:0 8px 22px rgba(25,43,55,.12); transform:translateY(-2px); }} .card-icon,.empty-icon {{ color:var(--icon-accent); }} .card-title {{ color:var(--text); font-size:.98rem; font-weight:750; margin-top:.7rem; }} .badge {{ background:var(--elevated); border-radius:999px; color:var(--text-secondary); display:inline-block; font-size:.68rem; margin-top:.7rem; padding:.25rem .6rem; }} .quick-card {{ min-height:108px; padding:1rem; transition:border-color 180ms ease,box-shadow 180ms ease,transform 180ms ease; }} .quick-title {{ color:var(--text); font-size:.92rem; font-weight:750; margin-top:.45rem; }} .quick-description {{ color:var(--muted); font-size:.74rem; margin-top:.25rem; }}
        .empty-state {{ margin:1.3rem 0; padding:1.8rem; text-align:center; }} .empty-icon {{ height:28px; margin:0 auto .6rem; width:28px; }} .empty-title {{ color:var(--text); font-size:1rem; font-weight:700; }} .empty-description {{ color:var(--muted); font-size:.84rem; margin-top:.4rem; }} .stepper {{ align-items:center; display:flex; margin:1.35rem 0; width:100%; }} .step {{ align-items:center; color:var(--muted); display:flex; flex:1; flex-direction:column; font-size:.72rem; gap:.4rem; text-align:center; }} .step-number {{ align-items:center; border:1px solid var(--border); border-radius:50%; color:var(--muted); display:inline-flex; height:28px; justify-content:center; width:28px; }} .step-connector {{ background:var(--border); flex:1; height:1px; margin:0 .35rem 1.25rem; }} .get-started-workflow {{ align-items:center; display:flex; margin:1rem 0 2rem; }} .metadata-scan-workflow {{ margin-left:auto; margin-right:auto; max-width:1100px; width:75%; }} .workflow-item {{ flex:1; min-width:0; padding:.35rem .25rem; }} .workflow-number {{ color:var(--accent); font-size:.7rem; font-weight:800; letter-spacing:.08em; }} .workflow-icon {{ margin-top:.4rem; }} .workflow-title {{ color:var(--text); font-size:.84rem; font-weight:750; margin-top:.35rem; }} .workflow-connector {{ color:var(--border); font-size:1.1rem; padding:0 .25rem; }} .toolbar-panel {{ background:var(--surface-secondary); border:1px solid var(--border); border-radius:12px; margin:1.1rem 0; padding:1rem 1.1rem .25rem; }}
        .stButton>button {{ border-radius:8px; transition:background 180ms ease,border-color 180ms ease,color 180ms ease,transform 180ms ease; }} .stButton>button:hover {{ transform:translateY(-1px); }} .stButton>button[kind="primary"] {{ background:var(--accent); color:#FFFFFF; box-shadow:0 4px 12px rgba(255,86,64,.2); }} .stButton>button[kind="primary"] svg {{ color:#FFFFFF; }} .stButton>button[kind="secondary"] {{ background:transparent; color:var(--button-secondary-text); border:1px solid var(--border); }} .stButton>button[kind="secondary"] svg {{ color:var(--button-secondary-text); }} .stButton>button[kind="secondary"]:hover {{ background:var(--hover); border-color:var(--button-secondary-text); }} [data-testid="stButton"] button[kind="tertiary"] {{ align-items:center; background:transparent; border:1px solid transparent; color:var(--icon-secondary); height:38px; justify-content:center; min-width:38px; padding:0; width:38px; }} [data-testid="stButton"] button[kind="tertiary"] svg {{ color:currentColor; }} [data-testid="stButton"] button[kind="tertiary"]:hover {{ background:var(--input-hover); border-color:var(--border); color:var(--accent); }} @keyframes fade-in {{ from {{ opacity:0; transform:translateY(4px); }} to {{ opacity:1; transform:translateY(0); }} }} @media (max-width:800px) {{ .get-started-workflow {{ flex-wrap:wrap; }} .metadata-scan-workflow {{ width:100%; }} .workflow-item {{ flex:1 1 45%; }} .workflow-connector {{ display:none; }} }} @media (prefers-reduced-motion:reduce) {{ *,*::before,*::after {{ animation-duration:.01ms!important; transition-duration:.01ms!important; }} }}
        </style>
        """,
        unsafe_allow_html=True,
    )
