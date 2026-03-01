"""GovGrab — All CSS styles as a single constant."""

GA_SCRIPT = """
<script async src="https://www.googletagmanager.com/gtag/js?id=G-D7Y426FBJ9"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-D7Y426FBJ9');
</script>
"""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
div[data-testid="stToolbar"] {display: none;}
.stDeployButton {display: none;}
header[data-testid="stHeader"] {
    display: none !important;
    height: 0 !important;
}

/* Sidebar — ensure it stays visible and expanded */
[data-testid="stSidebar"],
section[data-testid="stSidebar"] {
    transform: none !important;
    visibility: visible !important;
    position: relative !important;
}

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* ── Dark theme globals ── */
.stApp, [data-testid="stAppViewContainer"], .main, .block-container {
    background-color: #111118 !important;
    color: #CBD5E1 !important;
}
.block-container { padding-top: 2rem; max-width: 1280px; }

/* Override Streamlit widget styles for dark theme */
input, textarea,
[data-baseweb="select"], [data-baseweb="input"],
[data-baseweb="base-input"], [data-baseweb="input-container"],
.stTextInput > div > div, .stNumberInput > div > div,
.stSelectbox > div > div, .stMultiSelect > div > div,
.stTextArea > div > div {
    background-color: #232334 !important;
    color: #F8FAFC !important;
    border-color: #3D4560 !important;
}
input::placeholder, textarea::placeholder { color: #8891A5 !important; opacity: 1 !important; }
/* Selectbox placeholder text */
[data-baseweb="select"] span, [data-baseweb="select"] div[aria-selected] { color: #F8FAFC !important; }
input:focus, textarea:focus {
    border-color: #0EA5E9 !important;
    box-shadow: 0 0 0 1px #0EA5E9 !important;
    background-color: #2A2A3D !important;
}
[data-baseweb="select"] > div,
[data-baseweb="select"] > div > div { background-color: #232334 !important; }
[data-baseweb="popover"], [data-baseweb="popover"] > div { background-color: #232334 !important; border: 1px solid #3D4560 !important; }
[data-baseweb="menu"], [role="listbox"] { background-color: #232334 !important; }
[data-baseweb="menu"] li, [role="option"] { color: #E2E8F0 !important; }
[data-baseweb="menu"] li:hover, [role="option"]:hover,
[data-baseweb="menu"] li[aria-selected="true"], [role="option"][aria-selected="true"] { background-color: #2A2A3D !important; }
/* Number input steppers */
.stNumberInput button { background-color: #232334 !important; color: #CBD5E1 !important; border-color: #3D4560 !important; }
.stNumberInput button:hover { background-color: #2A2A3D !important; color: #F8FAFC !important; }
/* Make sure nested inputs are transparent on their bg */
[data-baseweb="input"] input, [data-baseweb="base-input"] input { background-color: transparent !important; }
label, .stTextInput label, .stSelectbox label, .stNumberInput label { color: #E2E8F0 !important; }
.stMarkdown, .stMarkdown p { color: #E2E8F0 !important; }
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 { color: #F8FAFC !important; }
.stMarkdown a { color: #0EA5E9 !important; }
.stMarkdown strong { color: #F8FAFC !important; }
.stCaption, [data-testid="stCaptionContainer"] { color: #94A3B8 !important; }
hr { border-color: #2D3748 !important; }

/* Streamlit buttons */
.stButton > button {
    background: linear-gradient(135deg, #0EA5E9, #0284C7) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    box-shadow: 0 0 20px rgba(14, 165, 233, 0.4) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
    background: #1A1A24 !important;
    border: 1px solid #2D3748 !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #0EA5E9 !important;
    box-shadow: 0 0 12px rgba(14, 165, 233, 0.2) !important;
}

/* Checkbox & slider */
.stCheckbox label span { color: #E2E8F0 !important; }
.stCheckbox [data-testid="stCheckbox"] { color: #E2E8F0 !important; }
[data-testid="stSlider"] { color: #E2E8F0 !important; }
[data-testid="stSlider"] [data-testid="stTickBarMin"],
[data-testid="stSlider"] [data-testid="stTickBarMax"] { color: #94A3B8 !important; }

/* Spinner */
.stSpinner > div { color: #0EA5E9 !important; }

/* Info / Warning / Success boxes */
[data-testid="stAlert"] { background-color: #1A1A24 !important; border-color: #2D3748 !important; color: #CBD5E1 !important; }

/* Dark scrollbar */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #111118; }
::-webkit-scrollbar-thumb { background: #1E293B; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #334155; }

/* ── Animations ── */
@keyframes gradientShift {
    0% { transform: translate(-50%, -50%) rotate(0deg); }
    50% { transform: translate(-50%, -50%) rotate(180deg); }
    100% { transform: translate(-50%, -50%) rotate(360deg); }
}
@keyframes pulseUrgent {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}

/* ── Compact Hero ── */
.hero-compact {
    background: linear-gradient(135deg, #111118 0%, #1A1A24 100%);
    border-radius: 14px;
    padding: 32px 36px 28px 36px;
    margin-bottom: 16px;
    position: relative;
    overflow: hidden;
    border: 1px solid #2D3748;
}
.hero-compact::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, #0EA5E9, #A855F7, transparent);
}
.hero-compact::after {
    content: '';
    position: absolute;
    top: -50%; left: -50%; width: 200%; height: 200%;
    background: radial-gradient(circle at 30% 50%, rgba(14,165,233,0.06) 0%, transparent 50%),
                radial-gradient(circle at 70% 80%, rgba(168,85,247,0.04) 0%, transparent 50%);
    pointer-events: none;
}
.hero-text { position: relative; z-index: 1; }
.hero-compact h1 { color: #F8FAFC; font-size: 32px; font-weight: 900; margin-bottom: 6px; letter-spacing: -0.5px; }
.hero-compact p { color: #94A3B8; font-size: 15px; margin: 0; line-height: 1.5; }
.hero-compact .hl {
    background: linear-gradient(135deg, #0EA5E9, #22D3EE);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.hero-stats {
    display: flex; gap: 24px; margin-top: 16px;
    position: relative; z-index: 1;
}
.hero-stat {
    font-size: 13px; color: #94A3B8;
}
.hero-stat strong { color: #0EA5E9; font-weight: 800; margin-right: 4px; }

/* ── How it works ── */
.how-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 28px 0; }
.step-card {
    background: #1A1A24; border: 1px solid #2D3748; border-radius: 12px;
    padding: 28px 20px; text-align: center; transition: all 0.3s ease;
    position: relative; overflow: hidden;
}
.step-card::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background: radial-gradient(circle at 50% 0%, rgba(14,165,233,0.06) 0%, transparent 70%);
    opacity: 0; transition: opacity 0.3s ease;
}
.step-card:hover {
    transform: translateY(-3px);
    border-color: #0EA5E9;
    box-shadow: 0 8px 32px rgba(14,165,233,0.12);
}
.step-card:hover::before { opacity: 1; }
.step-card .icon { font-size: 32px; margin-bottom: 10px; position: relative; }
.step-card h3 { font-size: 17px; font-weight: 700; color: #F8FAFC; margin-bottom: 6px; position: relative; }
.step-card p { font-size: 13px; color: #94A3B8; line-height: 1.5; margin: 0; position: relative; }

/* ── Category pills ── */
.cat-pills { display: flex; flex-wrap: wrap; gap: 10px; margin: 20px 0 32px 0; }

/* ── Listing grid ── */
.listing-grid { display: grid; gap: 16px; margin: 16px 0; }
.listing-grid-2 { grid-template-columns: repeat(2, 1fr); }
.listing-grid-3 { grid-template-columns: repeat(3, 1fr); }
.listing-grid-4 { grid-template-columns: repeat(4, 1fr); }

.card-link { text-decoration: none !important; color: inherit !important; }
.listing-card {
    background: #1A1A24;
    border: 1px solid #2D3748;
    border-radius: 10px;
    overflow: hidden;
    transition: all 0.25s ease;
    cursor: pointer;
}
.listing-card:hover {
    box-shadow: 0 4px 24px rgba(14,165,233,0.15);
    border-color: #0EA5E9;
    transform: translateY(-3px);
}

.card-img-wrap {
    position: relative;
    width: 100%;
    height: 200px;
    background: #111118;
    overflow: hidden;
}
.card-img-wrap::after {
    content: '';
    position: absolute; bottom: 0; left: 0; right: 0; height: 40px;
    background: linear-gradient(transparent, rgba(19,19,26,0.8));
    pointer-events: none;
}
.card-badge {
    position: absolute;
    top: 8px; left: 8px;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    color: white;
    z-index: 2;
}
.card-time-overlay {
    position: absolute;
    bottom: 8px; right: 8px;
    z-index: 2;
}
.card-body { padding: 12px 14px 14px 14px; }
.card-title {
    font-size: 14px;
    font-weight: 600;
    color: #F8FAFC;
    line-height: 1.35;
    margin-bottom: 4px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
.card-location { font-size: 12px; color: #94A3B8; margin-bottom: 8px; }
.card-price-row { display: flex; align-items: baseline; justify-content: space-between; }
.card-price {
    font-size: 18px; font-weight: 700;
    background: linear-gradient(135deg, #84CC16, #22C55E);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.card-true-cost { font-size: 11px; color: #94A3B8; margin-top: 1px; }
.card-bids { font-size: 12px; color: #94A3B8; font-weight: 500; }
.card-time { font-size: 13px; color: white; background: rgba(255,255,255,0.15); padding: 5px 10px; border-radius: 6px; backdrop-filter: blur(4px); font-weight: 600; }
.card-time-urgent {
    font-size: 14px; color: white;
    background: linear-gradient(135deg, #EC4899, #F43F5E);
    padding: 5px 12px; border-radius: 6px; font-weight: 700;
    letter-spacing: 0.3px;
    box-shadow: 0 0 12px rgba(236,72,153,0.4);
    animation: pulseUrgent 2s ease-in-out infinite;
}

/* ── Section headers ── */
.sh { font-size: 24px; font-weight: 700; color: #F8FAFC; margin-bottom: 4px; }
.ss { font-size: 14px; color: #94A3B8; margin-bottom: 20px; }

/* ── Blog banners ── */
.blog-banner {
    display: flex; align-items: center; justify-content: center;
    border-radius: 10px 10px 0 0; font-size: 48px;
    position: relative; overflow: hidden;
}
.blog-banner::after {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background: radial-gradient(circle at 70% 30%, rgba(255,255,255,0.15) 0%, transparent 60%);
    pointer-events: none;
}

/* ── Blog cards ── */
.blog-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }
.blog-card {
    background: #1A1A24; border: 1px solid #2D3748; border-radius: 10px;
    overflow: hidden; transition: all 0.25s ease;
}
.blog-card .blog-card-body { padding: 20px 24px 24px 24px; }
.blog-card:hover {
    box-shadow: 0 4px 24px rgba(168,85,247,0.15);
    border-color: #A855F7;
}
.blog-card .cat { font-size: 11px; font-weight: 700; color: #A855F7; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
.blog-card h3 { font-size: 16px; font-weight: 700; color: #F8FAFC; margin-bottom: 6px; line-height: 1.3; }
.blog-card .desc { font-size: 13px; color: #94A3B8; line-height: 1.5; margin-bottom: 10px; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.blog-card .date { font-size: 12px; color: #94A3B8; }

/* ── Blog article ── */
.article-header { margin-bottom: 28px; }
.article-header h1 { font-size: 30px; font-weight: 800; color: #F8FAFC; line-height: 1.2; margin-bottom: 8px; }
.article-header .meta { font-size: 13px; color: #94A3B8; }
.article-body { font-size: 16px; line-height: 1.8; color: #CBD5E1; max-width: 720px; }
.article-body h2 { font-size: 22px; font-weight: 700; color: #F8FAFC; margin-top: 28px; margin-bottom: 10px; }
.article-body h3 { font-size: 18px; font-weight: 600; color: #F8FAFC; margin-top: 20px; margin-bottom: 8px; }
.article-body a { color: #0EA5E9 !important; text-decoration: underline; text-underline-offset: 2px; }
.article-body table { width: 100%; border-collapse: collapse; margin: 16px 0; }
.article-body th, .article-body td { padding: 10px 14px; border: 1px solid #2D3748; text-align: left; color: #CBD5E1; }
.article-body th { background: #1A1A24; font-weight: 600; color: #F8FAFC; }
.article-body strong { color: #F8FAFC; }

/* ── Value section ── */
.value-section {
    background: #1A1A24; border: 1px solid #2D3748; border-radius: 12px; padding: 36px;
    text-align: center; margin: 36px 0; position: relative; overflow: hidden;
}
.value-section::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, #0EA5E9, #A855F7, transparent);
}
.value-section h2 { font-size: 26px; font-weight: 800; color: #F8FAFC; margin-bottom: 8px; }
.value-section p { font-size: 15px; color: #94A3B8; max-width: 500px; margin: 0 auto; }

/* ── Empty state ── */
.empty-state {
    text-align: center; padding: 60px 20px; color: #94A3B8;
}
.empty-state .icon { font-size: 56px; margin-bottom: 12px; opacity: 0.6; }
.empty-state h3 { font-size: 18px; font-weight: 600; color: #CBD5E1; margin-bottom: 4px; }
.empty-state p { font-size: 14px; color: #94A3B8; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #111118 !important;
    border-right: none !important;
    min-width: 260px !important;
    width: 260px !important;
}
section[data-testid="stSidebar"] > div:first-child {
    width: 260px !important;
    min-width: 260px !important;
}
section[data-testid="stSidebar"] * { color: #CBD5E1 !important; }
section[data-testid="stSidebar"] hr { border-color: #2D3748 !important; }

/* Sidebar radio → styled nav pills */
section[data-testid="stSidebar"] [data-testid="stRadio"] > div { gap: 2px !important; }
section[data-testid="stSidebar"] [data-testid="stRadio"] > div[role="radiogroup"] { gap: 2px !important; }
section[data-testid="stSidebar"] [data-testid="stRadio"] label {
    display: flex !important; align-items: center !important;
    padding: 10px 14px !important; margin: 0 !important;
    border-radius: 8px !important; border: 1px solid transparent !important;
    background: transparent !important;
    color: #94A3B8 !important; font-size: 14px !important; font-weight: 500 !important;
    cursor: pointer !important; transition: all 0.15s ease !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: #1A1A24 !important; color: #F8FAFC !important;
    border-color: #2D3748 !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label[data-checked="true"],
section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
    background: linear-gradient(135deg, rgba(14,165,233,0.15), rgba(14,165,233,0.06)) !important;
    color: #0EA5E9 !important; font-weight: 600 !important;
    border-color: rgba(14,165,233,0.3) !important;
    box-shadow: 0 0 12px rgba(14,165,233,0.1) !important;
}
/* Hide the radio circle */
section[data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child {
    display: none !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label input[type="radio"] {
    display: none !important;
}

/* ── Fee reminder banner ── */
.fee-banner {
    background: linear-gradient(135deg, rgba(14,165,233,0.08), rgba(14,165,233,0.03));
    border: 1px solid rgba(14,165,233,0.15);
    border-radius: 10px;
    padding: 12px 18px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 14px;
    font-size: 13px;
    color: #94A3B8;
    line-height: 1.5;
}
.fee-banner .fee-icon { font-size: 18px; flex-shrink: 0; }
.fee-banner strong { color: #E2E8F0; }
.fee-banner .fee-chips { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 4px; }
.fee-chip {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
}
.fee-chip { background: rgba(14,165,233,0.12); color: #7DD3FC; }

/* ── Misc ── */
.results-bar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; padding: 8px 0; border-bottom: 1px solid #1E293B; }
.results-count { font-size: 14px; color: #94A3B8; }
.results-count strong { color: #F8FAFC; }

/* ── Platform status ── */
.platform-status {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 500;
    margin-right: 6px;
    margin-bottom: 4px;
}
.platform-status-ok { background: rgba(34,197,94,0.12); color: #4ADE80; }
.platform-status-empty { background: rgba(251,191,36,0.12); color: #FCD34D; }
.platform-status-error { background: rgba(248,113,113,0.12); color: #FCA5A5; }

/* ── Responsive ── */
@media (max-width: 768px) {
    .hero-compact { padding: 24px 20px 20px 20px; }
    .hero-compact h1 { font-size: 24px; }
    .hero-stats { flex-wrap: wrap; gap: 12px; }
    .how-grid { grid-template-columns: 1fr; }
    .listing-grid-3, .listing-grid-4 { grid-template-columns: repeat(2, 1fr); }
    .blog-grid { grid-template-columns: 1fr; }
}
@media (max-width: 480px) {
    .listing-grid-2, .listing-grid-3, .listing-grid-4 { grid-template-columns: 1fr; }
    .hero-compact h1 { font-size: 20px; }
}
</style>
"""
