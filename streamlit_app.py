"""
Streamlit Backend App — Groww Mutual Fund RAG Chatbot
=====================================================
Wraps the existing OrchestratorService in a premium Streamlit chat UI.
Loads GROQ_API_KEY from the project-root .env file automatically
(handled by src/mf_faq/__init__.py's built-in dotenv loader).

Deploy on Streamlit Cloud:
  1. Push repo to GitHub
  2. Go to https://share.streamlit.io → New App → select this repo
  3. Set Main file path: streamlit_app.py
  4. In Advanced Settings → Secrets, add:  GROQ_API_KEY = "gsk_..."
  5. Deploy
"""

import os
import sys

# ---------------------------------------------------------------------------
# 1. Ensure 'src/' is on sys.path so `mf_faq` package resolves correctly
# ---------------------------------------------------------------------------
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# ---------------------------------------------------------------------------
# 2. Load .env from project root (before any mf_faq imports)
# ---------------------------------------------------------------------------
_dotenv_path = os.path.join(ROOT_DIR, ".env")
if os.path.exists(_dotenv_path):
    with open(_dotenv_path, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _val = _line.split("=", 1)
                _key, _val = _key.strip(), _val.strip()
                if _val.startswith(('"', "'")) and _val.endswith(('"', "'")):
                    _val = _val[1:-1]
                if _key and _val and _key not in os.environ:
                    os.environ[_key] = _val

# Also pull from Streamlit secrets (Streamlit Cloud deployment)
try:
    import streamlit as st
    if hasattr(st, "secrets"):
        for _key in ("GROQ_API_KEY",):
            if _key in st.secrets and _key not in os.environ:
                os.environ[_key] = st.secrets[_key]
except Exception:
    pass

# ---------------------------------------------------------------------------
# 3. Streamlit page config (MUST be first st.* call)
# ---------------------------------------------------------------------------
import streamlit as st

st.set_page_config(
    page_title="GROWWW — HDFC Mutual Fund RAG Chatbot",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# 4. Import the orchestrator (triggers mf_faq.__init__ → env loader)
# ---------------------------------------------------------------------------
from mf_faq.orchestrator.service import OrchestratorService
from mf_faq.config import load_sources

# ---------------------------------------------------------------------------
# 5. Cache heavy resources so they survive Streamlit reruns
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="Loading RAG engine …")
def get_orchestrator():
    """Singleton OrchestratorService — loaded once, reused across sessions."""
    return OrchestratorService()

@st.cache_data(show_spinner=False)
def get_schemes():
    """Load the 5 whitelisted HDFC scheme cards."""
    orch = get_orchestrator()
    sources = load_sources(orch.config_dir)
    schemes = []
    for s in sources.get("schemes", []):
        url = s.get("sources", [{}])[0].get("url", "")
        schemes.append({
            "id": s.get("id"),
            "name": s.get("name"),
            "category": s.get("category"),
            "url": url,
        })
    return schemes

# ---------------------------------------------------------------------------
# 6. Inject custom CSS for the Groww purple + sea-green + white theme
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* ---------- Google Font ---------- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="st-"] {
    font-family: 'Inter', sans-serif;
}

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #2d1654 0%, #1a0d30 100%);
}
section[data-testid="stSidebar"] * {
    color: #e8e0f5 !important;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #ffffff !important;
}

/* ---------- Scheme card in sidebar ---------- */
.scheme-card {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 10px;
    transition: transform 0.2s, border-color 0.2s;
}
.scheme-card:hover {
    transform: translateY(-2px);
    border-color: #00d09c;
}
.scheme-card .card-name {
    font-weight: 600;
    font-size: 0.92rem;
    margin-bottom: 4px;
}
.scheme-card .card-cat {
    font-size: 0.78rem;
    opacity: 0.75;
    display: inline-block;
    background: rgba(0,208,156,0.18);
    padding: 2px 10px;
    border-radius: 20px;
    margin-top: 4px;
    color: #00d09c !important;
}
.scheme-card a {
    color: #c9a7ff !important;
    font-size: 0.78rem;
    text-decoration: none;
}
.scheme-card a:hover {
    text-decoration: underline;
}

/* ---------- Chat bubbles ---------- */
div[data-testid="stChatMessage"] {
    border-radius: 14px;
    margin-bottom: 4px;
}

/* ---------- Header banner ---------- */
.hero-banner {
    background: linear-gradient(135deg, #7835d6 0%, #5b21b6 60%, #00b386 100%);
    border-radius: 16px;
    padding: 28px 32px;
    color: #fff;
    margin-bottom: 24px;
}
.hero-banner h1 { margin: 0 0 6px 0; font-size: 1.8rem; }
.hero-banner p  { margin: 0; opacity: 0.88; font-size: 0.95rem; }

/* ---------- Disclaimer footer ---------- */
.disclaimer-bar {
    text-align: center;
    font-size: 0.75rem;
    color: #888;
    padding: 12px 0 4px;
    border-top: 1px solid #eee;
    margin-top: 20px;
}

/* ---------- Metric pill ---------- */
.metric-pill {
    display: inline-block;
    background: rgba(120,53,214,0.08);
    border: 1px solid rgba(120,53,214,0.18);
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.8rem;
    color: #7835d6;
    margin-right: 6px;
    margin-bottom: 6px;
}

/* ---------- Sample question buttons ---------- */
.stButton > button {
    border-radius: 20px !important;
    border: 1px solid #7835d6 !important;
    color: #7835d6 !important;
    background: #faf5ff !important;
    font-size: 0.82rem !important;
    padding: 4px 16px !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: #7835d6 !important;
    color: #fff !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 7. Sidebar — Brand + 5 Scheme Cards
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 📈 GROWWW")
    st.markdown("##### Mutual Fund Hub · Facts Only")
    st.divider()

    schemes = get_schemes()
    st.markdown("### Whitelisted Schemes")
    for scheme in schemes:
        st.markdown(f"""
        <div class="scheme-card">
            <div class="card-name">{scheme['name']}</div>
            <span class="card-cat">{scheme['category']}</span><br/>
            <a href="{scheme['url']}" target="_blank">View on Groww ↗</a>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # Status indicators
    groq_key = os.getenv("GROQ_API_KEY", "")
    engine_label = "🟢 Groq LLM (llama-3.3-70b)" if groq_key else "🟡 Extractive Fallback"
    st.markdown(f"**Engine:** {engine_label}")
    st.markdown(f"**Corpus:** 5 HDFC Schemes")
    st.markdown(f"**Safety:** PII Guard · Refusal · Compliance")

# ---------------------------------------------------------------------------
# 8. Main panel — Hero + Chat
# ---------------------------------------------------------------------------
st.markdown("""
<div class="hero-banner">
    <h1>HDFC Mutual Fund RAG Assistant</h1>
    <p>Ask objective, factual questions about exit loads, expense ratios, portfolio allocation,
       minimum investments, and lock-in periods for our 5 whitelisted HDFC schemes.</p>
</div>
""", unsafe_allow_html=True)

# Safety disclaimer
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.info(
        "🛡️ **Safety Active** — Speculative advice, comparisons, and Indian PII "
        "(PAN/Aadhaar/phone/email) are automatically deflected. Answers are capped at 3 sentences.",
        icon="🛡️",
    )

# ---------------------------------------------------------------------------
# 9. Sample question pills
# ---------------------------------------------------------------------------
st.markdown("##### 💡 Try a sample question")
sample_cols = st.columns(4)
sample_questions = [
    "What is the exit load of HDFC Equity Fund?",
    "What is the expense ratio of HDFC Mid Cap Fund?",
    "Is there a lock-in period for HDFC ELSS Tax Saver?",
    "What is the minimum investment for HDFC Large Cap Fund?",
]

sample_clicked = None
for i, q in enumerate(sample_questions):
    with sample_cols[i]:
        if st.button(q, key=f"sample_{i}", use_container_width=True):
            sample_clicked = q

st.divider()

# ---------------------------------------------------------------------------
# 10. Chat session state
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Welcome! I'm your **GROWWW RAG Assistant**. I answer objective, "
                "factual questions about HDFC Mid Cap, Equity, Focused, ELSS, and Large Cap schemes.\n\n"
                "🛡️ **Safety Active:** Speculative advice and Indian PII are automatically deflected."
            ),
        }
    ]

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="📈" if msg["role"] == "assistant" else "👤"):
        st.markdown(msg["content"])

# ---------------------------------------------------------------------------
# 11. Handle user input (typed or sample-click)
# ---------------------------------------------------------------------------
user_input = st.chat_input("Ask a factual question about HDFC Mutual Funds…")

# If a sample button was clicked, use that as input
if sample_clicked:
    user_input = sample_clicked

if user_input:
    # Show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)

    # Generate response
    with st.chat_message("assistant", avatar="📈"):
        with st.spinner("Retrieving & reasoning …"):
            try:
                orch = get_orchestrator()
                result = orch.ask(user_input)

                answer = result.get("answer", "Sorry, something went wrong.")
                source_url = result.get("source_url")
                intent = result.get("intent", "unknown")
                confidence = result.get("confidence", 0.0)

                # Display answer
                st.markdown(answer)

                # Metadata pills
                pills_html = ""
                if intent:
                    pills_html += f'<span class="metric-pill">Intent: {intent}</span>'
                if confidence:
                    pills_html += f'<span class="metric-pill">Confidence: {confidence:.2f}</span>'
                if source_url:
                    pills_html += f'<span class="metric-pill"><a href="{source_url}" target="_blank" style="color:#7835d6;text-decoration:none;">Source ↗</a></span>'
                if pills_html:
                    st.markdown(pills_html, unsafe_allow_html=True)

                # Store in session
                display_text = answer
                if source_url:
                    display_text += f"\n\n🔗 [Source]({source_url})"
                st.session_state.messages.append(
                    {"role": "assistant", "content": display_text}
                )

            except Exception as e:
                error_msg = f"⚠️ Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append(
                    {"role": "assistant", "content": error_msg}
                )

# ---------------------------------------------------------------------------
# 12. Disclaimer footer
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="disclaimer-bar">⚠️ Facts-only. No investment advice. '
    "Data sourced exclusively from Groww.in for 5 HDFC schemes.</div>",
    unsafe_allow_html=True,
)
