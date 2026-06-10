"""
app.py  ─  Streamlit UI for the Refund Request AI Agent
Run:  streamlit run app.py
"""

import os
import streamlit as st
from datetime import date

# ── Page config ────────────────────────────────
st.set_page_config(
    page_title="Refund Request AI Agent",
    page_icon="↩️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono&display=swap');

    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

    .stApp { background: #0f1117; color: #e2e8f0; }

    /* Sidebar */
    [data-testid="stSidebar"] { background: #161b27 !important; border-right: 1px solid #2d3748; }

    /* Cards */
    .card {
        background: #161b27;
        border: 1px solid #2d3748;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
    }
    .card-green  { border-left: 4px solid #38a169; }
    .card-red    { border-left: 4px solid #e53e3e; }
    .card-yellow { border-left: 4px solid #d69e2e; }
    .card-blue   { border-left: 4px solid #3182ce; }
    .card-gray   { border-left: 4px solid #718096; }

    .decision-badge {
        display: inline-block;
        padding: 4px 14px;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.05em;
    }
    .badge-APPROVE  { background:#276749; color:#9ae6b4; }
    .badge-PARTIAL  { background:#744210; color:#fbd38d; }
    .badge-DENY     { background:#742a2a; color:#feb2b2; }
    .badge-ESCALATE { background:#2a4365; color:#90cdf4; }
    .badge-NOT_FOUND{ background:#2d3748; color:#a0aec0; }
    .badge-PENDING  { background:#2d3748; color:#a0aec0; }

    .section-title {
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #718096;
        margin-bottom: 0.5rem;
    }

    /* Chat bubbles */
    .chat-user {
        background: #1a365d;
        border-radius: 12px 12px 2px 12px;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        max-width: 80%;
        margin-left: auto;
    }
    .chat-agent {
        background: #1c2333;
        border: 1px solid #2d3748;
        border-radius: 12px 12px 12px 2px;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        max-width: 85%;
    }

    /* Input */
    .stTextArea textarea {
        background: #161b27 !important;
        border: 1px solid #2d3748 !important;
        border-radius: 8px !important;
        color: #e2e8f0 !important;
        font-family: 'DM Sans', sans-serif !important;
    }
    .stButton button {
        background: linear-gradient(135deg, #3182ce, #2b6cb0) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1.5rem !important;
        transition: all 0.2s !important;
    }
    .stButton button:hover { opacity: 0.9 !important; transform: translateY(-1px) !important; }

    .stSelectbox select, .stSelectbox > div > div {
        background: #161b27 !important;
        color: #e2e8f0 !important;
    }

    /* Metrics */
    [data-testid="metric-container"] {
        background: #161b27;
        border: 1px solid #2d3748;
        border-radius: 10px;
        padding: 1rem;
    }

    /* Hide Streamlit branding */
    #MainMenu, footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Session State Init ──────────────────────────
def init_state():
    defaults = {
        "api_key_set": False,
        "conversation_history": [],
        "last_result": None,
        "total_requests": 0,
        "approved": 0,
        "denied": 0,
        "escalated": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


# ── Sidebar ──────────────────────────────────────
with st.sidebar:
    st.markdown("## ↩️ Refund Agent")
    st.markdown("---")

    # API Key
    st.markdown('<p class="section-title">Configuration</p>', unsafe_allow_html=True)
    api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        placeholder="sk-...",
        help="Your OpenAI API key for GPT-4o-mini and embeddings",
    )
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
        st.session_state["api_key_set"] = True
        st.success("✓ API key set")
    else:
        st.warning("⚠ Enter your OpenAI API key to start")

    st.markdown("---")

    # Sample Orders Panel
    st.markdown('<p class="section-title">Sample Test Orders</p>', unsafe_allow_html=True)
    sample_cases = {
        "ORD-1001 · Headphones (10 days, opened)": "I want to return my headphones from order ORD-1001. I changed my mind about the purchase.",
        "ORD-1002 · Shoes (45 days, standard)": "Please process a refund for my Nike shoes, order ORD-1002. They don't fit properly.",
        "ORD-1003 · Software License": "I need a refund for my Adobe Photoshop license, order ORD-1003.",
        "ORD-1004 · Laptop (unopened, 3 days)": "I'd like to return my Dell laptop order ORD-1004, still unopened.",
        "ORD-1005 · Custom Watch": "I want to return my custom engraved watch, order ORD-1005.",
        "ORD-1006 · TV (defective)": "My Samsung TV from order ORD-1006 is defective — it won't turn on!",
        "ORD-1007 · Winter Jacket (premium)": "I'd like to return the winter jacket from order ORD-1007, tags still attached.",
    }
    selected_sample = st.selectbox("Load a test case:", ["— select —"] + list(sample_cases.keys()))

    st.markdown("---")

    # Stats
    st.markdown('<p class="section-title">Session Stats</p>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.metric("Total", st.session_state["total_requests"])
    c2.metric("Approved", st.session_state["approved"])
    c3, c4 = st.columns(2)
    c3.metric("Denied", st.session_state["denied"])
    c4.metric("Escalated", st.session_state["escalated"])

    if st.button("🗑 Clear History"):
        st.session_state["conversation_history"] = []
        st.session_state["last_result"] = None
        st.rerun()


# ── Main Layout ────────────────────────────────
st.markdown("# Refund Request AI Agent")
st.markdown(
    "Powered by **LangGraph** + **FAISS** · Intelligent policy-grounded refund decisions"
)
st.markdown("---")

col_chat, col_detail = st.columns([3, 2], gap="large")

# ── Left: Chat Interface ───────────────────────
with col_chat:
    st.markdown("### Customer Request")

    # Pre-fill from sample selector
    default_text = ""
    if selected_sample and selected_sample != "— select —":
        default_text = sample_cases[selected_sample]

    user_input = st.text_area(
        "Describe your refund request:",
        value=default_text,
        height=100,
        placeholder="E.g., I'd like to return my order ORD-1001. The product arrived damaged.",
        label_visibility="collapsed",
    )

    submit_col, _, tip_col = st.columns([2, 1, 3])
    with submit_col:
        submitted = st.button("🚀 Submit Request", use_container_width=True)
    with tip_col:
        st.markdown(
            "<small style='color:#718096'>Include your order ID (e.g. ORD-1001) for best results.</small>",
            unsafe_allow_html=True,
        )

    # ── Process Request ──────────────────────────
    if submitted:
        if not st.session_state["api_key_set"]:
            st.error("Please enter your OpenAI API key in the sidebar first.")
        elif not user_input.strip():
            st.warning("Please describe your refund request.")
        else:
            with st.spinner("🤖 Processing your request through the AI agent..."):
                try:
                    from refund_agent import process_refund_request

                    result = process_refund_request(user_input.strip())

                    # Update stats
                    st.session_state["total_requests"] += 1
                    d = result.get("decision", "PENDING")
                    if d == "APPROVE":
                        st.session_state["approved"] += 1
                    elif d == "DENY":
                        st.session_state["denied"] += 1
                    elif d in ("ESCALATE",):
                        st.session_state["escalated"] += 1

                    # Store in history
                    st.session_state["conversation_history"].append(
                        {"user": user_input.strip(), "result": result}
                    )
                    st.session_state["last_result"] = result
                    st.rerun()

                except ImportError:
                    st.error(
                        "Could not import `refund_agent`. Make sure all dependencies are installed:\n"
                        "```\npip install -r requirements.txt\n```"
                    )
                except Exception as e:
                    st.error(f"Agent error: {e}")

    # ── Conversation History ──────────────────────
    if st.session_state["conversation_history"]:
        st.markdown("### Conversation History")
        for i, entry in enumerate(reversed(st.session_state["conversation_history"])):
            r = entry["result"]
            dec = r.get("decision", "PENDING")

            with st.expander(
                f"{'✅' if dec=='APPROVE' else '❌' if dec=='DENY' else '⚡' if dec=='ESCALATE' else '⚠️'} "
                f"Request #{st.session_state['total_requests'] - i}  ·  {r.get('order_id','N/A')}  ·  {dec}",
                expanded=(i == 0),
            ):
                st.markdown(
                    f'<div class="chat-user"><small style="color:#90cdf4">Customer</small><br>{entry["user"]}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="chat-agent"><small style="color:#68d391">Agent</small><br>{r.get("final_response","")}</div>',
                    unsafe_allow_html=True,
                )


# ── Right: Decision Details ────────────────────
with col_detail:
    st.markdown("### Decision Details")

    if not st.session_state["last_result"]:
        st.markdown(
            '<div class="card card-gray"><p style="color:#718096;text-align:center;margin:2rem 0">Submit a refund request to see the agent\'s decision details here.</p></div>',
            unsafe_allow_html=True,
        )
    else:
        r = st.session_state["last_result"]
        dec = r.get("decision", "PENDING")
        order = r.get("order_details") or {}

        # Decision badge
        color_map = {
            "APPROVE": "card-green",
            "PARTIAL": "card-yellow",
            "DENY": "card-red",
            "ESCALATE": "card-blue",
            "NOT_FOUND": "card-gray",
        }
        emoji_map = {
            "APPROVE": "✅",
            "PARTIAL": "⚡",
            "DENY": "❌",
            "ESCALATE": "🔁",
            "NOT_FOUND": "🔍",
        }
        card_cls = color_map.get(dec, "card-gray")
        emoji = emoji_map.get(dec, "❓")

        st.markdown(
            f"""
            <div class="card {card_cls}">
                <p class="section-title">Decision</p>
                <h2 style="margin:0">{emoji} {dec}</h2>
                {f'<p style="margin-top:0.5rem;font-size:1.1rem;color:#9ae6b4"><strong>Refund: ${r["refund_amount"]:.2f}</strong></p>' if r.get("refund_amount") else ''}
                {f'<p style="margin-top:0.5rem;font-size:1.1rem;color:#9ae6b4"><strong>Full Refund: ${order.get("price", 0):.2f}</strong></p>' if dec == "APPROVE" and not r.get("refund_amount") else ''}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Order Info
        if order:
            st.markdown(
                f"""
                <div class="card">
                    <p class="section-title">Order Details</p>
                    <table style="width:100%;border-collapse:collapse;font-size:0.88rem">
                        <tr><td style="color:#718096;padding:3px 0">Order ID</td><td><strong>{order.get("order_id","—")}</strong></td></tr>
                        <tr><td style="color:#718096;padding:3px 0">Product</td><td>{order.get("product","—")}</td></tr>
                        <tr><td style="color:#718096;padding:3px 0">Category</td><td>{order.get("category","—").title()}</td></tr>
                        <tr><td style="color:#718096;padding:3px 0">Price</td><td>${order.get("price",0):.2f}</td></tr>
                        <tr><td style="color:#718096;padding:3px 0">Days Since Purchase</td><td>{r.get("days_since_purchase","—")}</td></tr>
                        <tr><td style="color:#718096;padding:3px 0">Membership</td><td>{"⭐ " if order.get("membership")=="premium" else ""}{order.get("membership","—").title()}</td></tr>
                        <tr><td style="color:#718096;padding:3px 0">Item Opened</td><td>{"Yes" if order.get("opened") else "No"}</td></tr>
                    </table>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Reasoning
        if r.get("decision_reasoning"):
            st.markdown(
                f"""
                <div class="card">
                    <p class="section-title">Agent Reasoning</p>
                    <p style="font-size:0.88rem;color:#a0aec0;line-height:1.6">{r["decision_reasoning"]}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Policies Retrieved
        if r.get("relevant_policies"):
            with st.expander("📚 Retrieved Policies (FAISS)", expanded=False):
                st.markdown(
                    f'<div style="font-size:0.8rem;font-family:\'DM Mono\',monospace;color:#a0aec0;line-height:1.7">{r["relevant_policies"].replace(chr(10),"<br>")}</div>',
                    unsafe_allow_html=True,
                )

    # ── Graph Architecture Diagram ─────────────
    st.markdown("---")
    st.markdown("### Agent Graph")
    st.markdown(
        """
        <div class="card" style="font-family:'DM Mono',monospace;font-size:0.78rem;line-height:1.9;color:#a0aec0">
        START<br>
        &nbsp;│<br>
        &nbsp;▼<br>
        <span style="color:#63b3ed">extract_info</span> &nbsp;← Parse order ID + reason<br>
        &nbsp;│<br>
        &nbsp;▼<br>
        <span style="color:#63b3ed">validate_order</span> &nbsp;← DB lookup<br>
        &nbsp;├─ NOT_FOUND ──► generate_response<br>
        &nbsp;▼<br>
        <span style="color:#63b3ed">retrieve_policy</span> &nbsp;← FAISS similarity<br>
        &nbsp;│<br>
        &nbsp;▼<br>
        <span style="color:#63b3ed">evaluate_eligibility</span> &nbsp;← LLM decision<br>
        &nbsp;├─ ESCALATE ──► escalate_handler<br>
        &nbsp;▼<br>
        <span style="color:#63b3ed">generate_response</span> &nbsp;← Final reply<br>
        &nbsp;│<br>
        END
        </div>
        """,
        unsafe_allow_html=True,
    )
