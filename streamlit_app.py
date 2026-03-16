"""
streamlit_app.py — VidChat AI
Bold SaaS dark UI inspired by modern AI video tools
"""
import streamlit as st
import requests

API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="VidChat AI",
    page_icon="▶",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
    --bg:        #0A0A0A;
    --bg2:       #111111;
    --bg3:       #1A1A1A;
    --border:    #222222;
    --border2:   #2E2E2E;
    --text:      #FFFFFF;
    --text2:     #A0A0A0;
    --text3:     #505050;
    --green:     #00E96A;
    --green2:    #00C459;
    --green-dim: rgba(0,233,106,0.12);
    --green-glow:rgba(0,233,106,0.25);
}

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    background: var(--bg) !important;
    color: var(--text) !important;
}

#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stSidebarCollapsedControl"] { display: none !important; visibility: hidden !important; }

/* Hide sidebar entirely — we embed everything inline */
[data-testid="stSidebar"] { display: none !important; }

.main .block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

/* ── NAV ── */
.nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1.2rem 3rem;
    border-bottom: 1px solid var(--border);
    background: rgba(10,10,10,0.95);
    backdrop-filter: blur(12px);
    position: sticky;
    top: 0;
    z-index: 100;
}
.nav-logo {
    font-size: 1.25rem;
    font-weight: 800;
    color: var(--text);
    letter-spacing: -0.03em;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.nav-logo .dot { color: var(--green); }
.nav-links {
    display: flex;
    gap: 2rem;
    font-size: 0.82rem;
    color: var(--text2);
    font-weight: 500;
}
.nav-cta {
    background: var(--green);
    color: #000 !important;
    font-weight: 700;
    font-size: 0.8rem;
    padding: 0.5rem 1.25rem;
    border-radius: 100px;
    cursor: pointer;
    letter-spacing: 0.01em;
}

/* ── HERO ── */
.hero {
    text-align: center;
    padding: 5rem 2rem 3rem;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute;
    top: -100px; left: 50%;
    transform: translateX(-50%);
    width: 600px; height: 400px;
    background: radial-gradient(ellipse, rgba(0,233,106,0.08) 0%, transparent 70%);
    pointer-events: none;
}
.hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: var(--green-dim);
    border: 1px solid rgba(0,233,106,0.3);
    border-radius: 100px;
    padding: 0.3rem 0.9rem;
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--green);
    letter-spacing: 0.04em;
    margin-bottom: 1.5rem;
}
.hero-badge .badge-dot {
    width: 5px; height: 5px;
    background: var(--green);
    border-radius: 50%;
    animation: pulse 2s infinite;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }

.hero-title {
    font-size: clamp(2.5rem, 5vw, 4rem);
    font-weight: 800;
    line-height: 1.1;
    letter-spacing: -0.04em;
    color: var(--text);
    margin-bottom: 1rem;
}
.hero-title .hl { color: var(--green); }

.hero-sub {
    font-size: 1rem;
    color: var(--text2);
    max-width: 560px;
    margin: 0 auto 2.5rem;
    line-height: 1.65;
    font-weight: 400;
}

/* ── URL INPUT BOX ── */
.input-shell {
    max-width: 640px;
    margin: 0 auto 1rem;
    position: relative;
}
.input-shell [data-testid="stTextInput"] {
    margin: 0 !important;
}
.input-shell [data-testid="stTextInput"] input {
    background: var(--bg2) !important;
    border: 1.5px solid var(--border2) !important;
    border-radius: 100px !important;
    color: var(--text) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.95rem !important;
    padding: 1rem 1.5rem !important;
    height: 56px !important;
    width: 100% !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.input-shell [data-testid="stTextInput"] input:focus {
    border-color: var(--green) !important;
    box-shadow: 0 0 0 4px var(--green-glow) !important;
    outline: none !important;
}
.input-shell [data-testid="stTextInput"] input::placeholder {
    color: var(--text3) !important;
}
.input-shell [data-testid="stTextInput"] label { display: none !important; }

/* ── BUTTONS ── */
.stButton > button {
    background: var(--green) !important;
    color: #000000 !important;
    border: none !important;
    border-radius: 100px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.88rem !important;
    padding: 0.75rem 2rem !important;
    transition: all 0.2s !important;
    cursor: pointer !important;
    letter-spacing: 0.01em !important;
}
.stButton > button:hover {
    background: var(--green2) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px var(--green-glow) !important;
}

/* ── FEATURES ROW ── */
.features {
    display: flex;
    justify-content: center;
    gap: 2rem;
    flex-wrap: wrap;
    margin: 1rem auto 3rem;
    max-width: 640px;
}
.feat {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.78rem;
    color: var(--text2);
    font-weight: 500;
}
.feat .check { color: var(--green); font-size: 0.7rem; }

/* ── DIVIDER ── */
.section-divider {
    border: none;
    border-top: 1px solid var(--border);
    margin: 0;
}

/* ── CHAT SECTION ── */
.chat-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1.2rem 3rem;
    border-bottom: 1px solid var(--border);
    background: var(--bg);
}
.chat-video-tag {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: var(--bg3);
    border: 1px solid var(--border2);
    border-radius: 100px;
    padding: 0.35rem 1rem;
    font-size: 0.78rem;
    color: var(--text2);
    font-weight: 500;
}
.chat-video-tag .live { color: var(--green); font-size: 0.65rem; }

.chat-wrap {
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem 2rem 0;
}

/* User bubble */
.msg-user {
    display: flex;
    justify-content: flex-end;
    margin: 1rem 0;
}
.msg-user-bubble {
    background: var(--bg3);
    border: 1px solid var(--border2);
    border-radius: 18px 18px 4px 18px;
    padding: 0.85rem 1.2rem;
    max-width: 70%;
    font-size: 0.9rem;
    line-height: 1.6;
    color: var(--text);
}

/* AI bubble */
.msg-ai {
    display: flex;
    gap: 0.85rem;
    margin: 1rem 0;
    align-items: flex-start;
}
.msg-ai-icon {
    width: 34px; height: 34px;
    background: var(--green-dim);
    border: 1px solid rgba(0,233,106,0.3);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.85rem;
    flex-shrink: 0;
    color: var(--green);
    font-weight: 800;
}
.msg-ai-bubble {
    background: var(--bg2);
    border: 1px solid var(--border2);
    border-radius: 4px 18px 18px 18px;
    padding: 1rem 1.3rem;
    font-size: 0.875rem;
    line-height: 1.78;
    color: #D0D0D0;
    flex: 1;
}

/* Tags */
.tag-row { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.65rem; }
.tag {
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 0.2rem 0.6rem;
    border-radius: 100px;
    border: 1px solid;
}
.tag-high   { color: var(--green); border-color: rgba(0,233,106,0.3); background: var(--green-dim); }
.tag-medium { color: #F5A623;      border-color: rgba(245,166,35,0.3); background: rgba(245,166,35,0.08); }
.tag-low    { color: #FF5C5C;      border-color: rgba(255,92,92,0.3);  background: rgba(255,92,92,0.08); }
.tag-intent { color: var(--text2); border-color: var(--border2); background: transparent; }
.tag-yt     { color: #FF6B6B;      border-color: rgba(255,107,107,0.3); background: rgba(255,107,107,0.06); }
.tag-web    { color: #60B4FF;      border-color: rgba(96,180,255,0.3);  background: rgba(96,180,255,0.06); }

/* Source & score cards */
.src-item {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--border);
    font-size: 0.78rem;
    color: var(--text2);
}
.src-ts {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    color: var(--green);
    min-width: 3.2rem;
}
.score-line { margin-top: 0.5rem; }
.score-row {
    display: flex;
    justify-content: space-between;
    font-size: 0.68rem;
    color: var(--text3);
    margin-bottom: 0.25rem;
}
.score-track { height: 3px; background: var(--bg3); border-radius: 2px; overflow: hidden; }
.score-fill  { height: 100%; background: var(--green); border-radius: 2px; }

/* Expanders */
[data-testid="stExpander"] {
    background: var(--bg2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    margin-top: 0.5rem !important;
}
[data-testid="stExpander"] summary {
    font-size: 0.72rem !important;
    color: var(--text2) !important;
    font-weight: 600 !important;
    letter-spacing: 0.04em !important;
}

/* Chat input */
[data-testid="stChatInput"] {
    background: var(--bg2) !important;
    border: 1.5px solid var(--border2) !important;
    border-radius: 100px !important;
    margin: 1rem 0 2rem !important;
}
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: var(--text) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.9rem !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: var(--text3) !important; }
[data-testid="stChatInput"]:focus-within {
    border-color: var(--green) !important;
    box-shadow: 0 0 0 4px var(--green-glow) !important;
}

/* Alerts */
[data-testid="stSuccess"] {
    background: var(--green-dim) !important;
    border: 1px solid rgba(0,233,106,0.25) !important;
    border-radius: 12px !important;
    color: var(--green) !important;
    font-size: 0.82rem !important;
}

/* Empty state */
.empty {
    text-align: center;
    padding: 4rem 2rem;
}
.empty-icon { font-size: 2.5rem; margin-bottom: 1rem; display: block; }
.empty-title {
    font-size: 1.4rem;
    font-weight: 800;
    color: var(--text);
    letter-spacing: -0.03em;
    margin-bottom: 0.5rem;
}
.empty-sub { font-size: 0.85rem; color: var(--text2); line-height: 1.6; }

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in [("messages", []), ("video_id", None), ("video_title", None), ("show_chat", False)]:
    if k not in st.session_state:
        st.session_state[k] = v

vid   = st.session_state.video_id
title = st.session_state.video_title

# ── NAV ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="nav">
    <div class="nav-logo">▶ VidChat<span class="dot">.</span>AI</div>
    <div class="nav-links">
        <span>How it works</span>
        <span>Features</span>
        <span>Docs</span>
    </div>
    <div class="nav-cta">Get Started Free</div>
</div>
""", unsafe_allow_html=True)

# ── HERO / INGEST ─────────────────────────────────────────────────────────────
if not vid:
    st.markdown("""
    <div class="hero">
        <div class="hero-badge"><span class="badge-dot"></span> Adaptive Multi-Source RAG · Powered by OpenAI</div>
        <div class="hero-title">Chat with any<br><span class="hl">YouTube Video</span></div>
        <div class="hero-sub">Paste a video link and ask anything. Our AI retrieves answers directly from the transcript — and searches the web when it needs more context.</div>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1, 2.5, 1])
    with col_c:
        st.markdown('<div class="input-shell">', unsafe_allow_html=True)
        url_input = st.text_input("url", placeholder="▶  Paste a YouTube video link...", label_visibility="collapsed")
        title_input = st.text_input("title", placeholder="Video title (optional)", label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("→  Analyze Video"):
            if url_input:
                with st.spinner("Fetching transcript & building index..."):
                    try:
                        r = requests.post(f"{API_BASE}/ingest", json={"url": url_input, "title": title_input or None})
                        if r.status_code == 200:
                            d = r.json()
                            st.session_state.video_id    = d["video_id"]
                            st.session_state.video_title = title_input or d["video_id"]
                            st.session_state.messages    = []
                            st.success(f"✓ {d['num_chunks']} chunks indexed — ready to chat!")
                            st.rerun()
                        else:
                            st.error(r.json().get("detail", "Failed to ingest video"))
                    except Exception as e:
                        st.error(f"Server error: {e}")
            else:
                st.error("Please paste a YouTube URL first")

    st.markdown("""
    <div class="features">
        <span class="feat"><span class="check">✓</span> Transcript retrieval</span>
        <span class="feat"><span class="check">✓</span> Live web search fallback</span>
        <span class="feat"><span class="check">✓</span> Timestamp citations</span>
        <span class="feat"><span class="check">✓</span> Self-evaluated answers</span>
    </div>
    """, unsafe_allow_html=True)

    # Show existing videos if any
    try:
        vr = requests.get(f"{API_BASE}/videos", timeout=3)
        if vr.ok and vr.json():
            videos = vr.json()
            st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
            st.markdown('<p style="text-align:center;font-size:0.75rem;color:#505050;padding:1rem 0 0.5rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase">Previously indexed</p>', unsafe_allow_html=True)
            cols = st.columns(min(len(videos), 3))
            for i, v in enumerate(videos[:3]):
                with cols[i]:
                    st.markdown(f'<div style="background:#111;border:1px solid #222;border-radius:12px;padding:1rem;text-align:center"><div style="font-size:0.8rem;font-weight:600;color:#fff;margin-bottom:0.5rem">{v["title"][:30]}</div><div style="font-family:monospace;font-size:0.65rem;color:#505050">{v["video_id"]}</div></div>', unsafe_allow_html=True)
                    if st.button(f"Load", key=f"load_{v['video_id']}"):
                        st.session_state.video_id    = v["video_id"]
                        st.session_state.video_title = v["title"]
                        st.session_state.messages    = []
                        st.rerun()
    except:
        pass

# ── CHAT VIEW ────────────────────────────────────────────────────────────────
else:
    # Chat header
    st.markdown(f"""
    <div class="chat-header">
        <div class="nav-logo">▶ VidChat<span class="dot">.</span>AI</div>
        <div class="chat-video-tag">
            <span class="live">● LIVE</span>
            {title or vid}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # New video button
    col1, col2, col3 = st.columns([1, 4, 1])
    with col3:
        if st.button("+ New Video"):
            st.session_state.video_id    = None
            st.session_state.video_title = None
            st.session_state.messages    = []
            st.rerun()

    # Chat area
    st.markdown('<div class="chat-wrap">', unsafe_allow_html=True)

    if not st.session_state.messages:
        st.markdown(f"""
        <div class="empty">
            <span class="empty-icon">💬</span>
            <div class="empty-title">Ready to answer</div>
            <div class="empty-sub">Ask anything about <strong style="color:#fff">{title or vid}</strong><br>— I'll pull answers from the transcript and the web.</div>
        </div>
        """, unsafe_allow_html=True)

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"""
            <div class="msg-user">
                <div class="msg-user-bubble">{msg["content"]}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            data       = msg.get("data", {})
            answer     = msg["content"]
            confidence = data.get("confidence", "medium")
            intent     = data.get("intent", "").replace("_", " ")
            sources    = data.get("sources", [])
            ev         = data.get("evaluation", {})
            yt_src     = [s for s in sources if s.get("type") == "youtube"]
            web_src    = [s for s in sources if s.get("type") == "web"]

            conf_icon = {"high": "●", "medium": "◑", "low": "○"}.get(confidence, "◑")
            yt_tag  = f'<span class="tag tag-yt">▶ {len(yt_src)} transcript</span>'  if yt_src  else ""
            web_tag = f'<span class="tag tag-web">⌖ {len(web_src)} web</span>'        if web_src else ""

            st.markdown(f"""
            <div class="msg-ai">
                <div class="msg-ai-icon">AI</div>
                <div style="flex:1">
                    <div class="msg-ai-bubble">{answer}</div>
                    <div class="tag-row">
                        <span class="tag tag-{confidence}">{conf_icon} {confidence}</span>
                        <span class="tag tag-intent">{intent}</span>
                        {yt_tag}{web_tag}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if sources or ev:
                c1, c2 = st.columns(2)
                with c1:
                    with st.expander(f"📎 {len(sources)} sources"):
                        for src in sources:
                            if src["type"] == "youtube":
                                ts  = src.get("timestamp", "—")
                                url = src.get("youtube_url", "#")
                                st.markdown(f'<div class="src-item"><span class="src-ts">{ts}</span><a href="{url}" target="_blank" style="color:#60B4FF;font-size:0.75rem">↗ jump to clip</a></div>', unsafe_allow_html=True)
                            else:
                                t   = (src.get("title") or "Article")[:45]
                                url = src.get("url", "#")
                                st.markdown(f'<div class="src-item"><span class="src-ts" style="color:#60B4FF">web</span><a href="{url}" target="_blank" style="color:#60B4FF;font-size:0.75rem">{t}</a></div>', unsafe_allow_html=True)
                with c2:
                    with st.expander("📊 Quality"):
                        g = ev.get("groundedness_score") or 0
                        c = ev.get("completeness_score") or 0
                        h = ev.get("hallucination_risk", "N/A")
                        st.markdown(f"""
                        <div class="score-line">
                            <div class="score-row"><span>Groundedness</span><span>{g:.0%}</span></div>
                            <div class="score-track"><div class="score-fill" style="width:{g*100:.0f}%"></div></div>
                        </div>
                        <div class="score-line" style="margin-top:0.7rem">
                            <div class="score-row"><span>Completeness</span><span>{c:.0%}</span></div>
                            <div class="score-track"><div class="score-fill" style="width:{c*100:.0f}%"></div></div>
                        </div>
                        <div style="margin-top:0.6rem;font-size:0.68rem;color:#505050">Hallucination risk · <span style="color:#fff">{h}</span></div>
                        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # Chat input
    col_l2, col_m2, col_r2 = st.columns([0.5, 5, 0.5])
    with col_m2:
        if prompt := st.chat_input("Ask anything about this video..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.spinner(""):
                try:
                    r = requests.post(f"{API_BASE}/chat", json={"video_id": vid, "question": prompt}, timeout=60)
                    if r.status_code == 200:
                        d = r.json()
                        st.session_state.messages.append({"role": "assistant", "content": d["answer"], "data": d})
                        st.rerun()
                    else:
                        st.error(r.json().get("detail", "Error"))
                except Exception as e:
                    st.error(f"Server error: {e}")