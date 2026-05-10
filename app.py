import streamlit as st
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import base64
from PIL import Image
import io
import time

from database import init_db
from db_helper import (
    register_user,
    login_user,
    get_user,
    add_transaction,
    get_user_transactions,
    get_transactions_df,
    get_or_create_default_categories,
    save_chat_message,
    get_chat_history,
    clear_chat_history,
    generate_spending_summary,
    get_dashboard_stats,
    get_user_categories,
    create_category,
    get_spending_by_category,
    get_total_spending,
)
from gemini_utils import (
    categorize_transaction,
    chat_with_gemini,
    analyze_spending,
    generate_budget_recommendation,
    extract_receipt_data,
)

load_dotenv()

# ============== PAGE CONFIG ==============
st.set_page_config(
    page_title="Finance Chatbot",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    /* ── Fonts ── */
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    /* ── CSS variables: light mode defaults ── */
    :root {
        --bg-card:               #ffffff;
        --bg-subtle:             #f8f9fc;
        --bg-muted:              #f1f3f9;
        --border:                #e4e7f0;
        --text-primary:          #111827;
        --text-secondary:        #6b7280;
        --text-muted:            #9ca3af;
        --prog-track:            #eef0f6;
        --upload-border:         #d1d5db;
        --receipt-bg:            #f0fdf4;
        --receipt-border:        #bbf7d0;
        --receipt-row-border:    #d1fae5;
        --badge-green-bg:        #dcfce7;
        --badge-green-fg:        #15803d;
        --badge-yellow-bg:       #fef9c3;
        --badge-yellow-fg:       #a16207;
        --badge-red-bg:          #fee2e2;
        --badge-red-fg:          #b91c1c;
        --divider:               #f1f3f9;
        --chart-text:            #6b7280;
    }

    /* ── Dark mode via media query ── */
    @media (prefers-color-scheme: dark) {
        :root {
            --bg-card:            #1e2130;
            --bg-subtle:          #161923;
            --bg-muted:           #252a3a;
            --border:             #2d3348;
            --text-primary:       #e8ecf8;
            --text-secondary:     #9ca3c4;
            --text-muted:         #6b7280;
            --prog-track:         #2d3348;
            --upload-border:      #374151;
            --receipt-bg:         #0d2618;
            --receipt-border:     #1a4731;
            --receipt-row-border: #1f5235;
            --badge-green-bg:     #14532d;
            --badge-green-fg:     #86efac;
            --badge-yellow-bg:    #451a03;
            --badge-yellow-fg:    #fcd34d;
            --badge-red-bg:       #450a0a;
            --badge-red-fg:       #fca5a5;
            --divider:            #252a3a;
            --chart-text:         #9ca3c4;
        }
    }

    /* ── Dark mode via Streamlit's data-theme attribute ── */
    [data-theme="dark"] {
        --bg-card:            #1e2130;
        --bg-subtle:          #161923;
        --bg-muted:           #252a3a;
        --border:             #2d3348;
        --text-primary:       #e8ecf8;
        --text-secondary:     #9ca3c4;
        --text-muted:         #6b7280;
        --prog-track:         #2d3348;
        --upload-border:      #374151;
        --receipt-bg:         #0d2618;
        --receipt-border:     #1a4731;
        --receipt-row-border: #1f5235;
        --badge-green-bg:     #14532d;
        --badge-green-fg:     #86efac;
        --badge-yellow-bg:    #451a03;
        --badge-yellow-fg:    #fcd34d;
        --badge-red-bg:       #450a0a;
        --badge-red-fg:       #fca5a5;
        --divider:            #252a3a;
        --chart-text:         #9ca3c4;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: #0f1117 !important;
        border-right: 1px solid #1e2130;
    }
    [data-testid="stSidebar"] * {
        color: #e0e4f0 !important;
    }
    [data-testid="stSidebar"] .stRadio label {
        padding: 6px 10px;
        border-radius: 6px;
        transition: background 0.15s;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        background: #1e2130;
    }

    /* ── Metric cards ── */
    [data-testid="metric-container"] {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 16px 20px !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }
    [data-testid="metric-container"] [data-testid="stMetricLabel"] {
        font-size: 0.78rem;
        font-weight: 500;
        color: var(--text-secondary) !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-family: 'DM Mono', monospace;
        font-size: 1.45rem;
        font-weight: 500;
        color: var(--text-primary) !important;
    }
    [data-testid="stMetricDelta"] svg { display: none; }

    /* ── Category card ── */
    .cat-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .cat-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    .cat-name {
        font-weight: 600;
        font-size: 0.95rem;
        color: var(--text-primary);
    }
    .cat-amounts {
        font-size: 0.78rem;
        color: var(--text-secondary);
        margin-top: 4px;
    }

    /* Progress bar */
    .prog-wrap {
        background: var(--prog-track);
        border-radius: 99px;
        height: 6px;
        overflow: hidden;
    }
    .prog-fill {
        height: 100%;
        border-radius: 99px;
        transition: width 0.4s ease;
    }

    /* ── Upload zone ── */
    .upload-zone {
        border: 2px dashed var(--upload-border);
        border-radius: 12px;
        padding: 48px 24px;
        text-align: center;
        background: var(--bg-subtle);
        color: var(--text-muted);
    }
    .upload-zone-icon { font-size: 3rem; margin-bottom: 12px; }
    .upload-zone h4 {
        color: var(--text-primary);
        font-size: 1rem;
        font-weight: 600;
        margin: 0 0 6px;
    }
    .upload-zone p { font-size: 0.82rem; margin: 0; color: var(--text-secondary); }

    /* ── Receipt result card ── */
    .receipt-card {
        background: var(--receipt-bg);
        border: 1px solid var(--receipt-border);
        border-radius: 10px;
        padding: 16px 20px;
    }
    .receipt-row {
        display: flex;
        justify-content: space-between;
        padding: 5px 0;
        border-bottom: 1px solid var(--receipt-row-border);
        font-size: 0.88rem;
    }
    .receipt-row:last-child { border-bottom: none; }
    .receipt-label { color: var(--text-secondary); font-weight: 500; }
    .receipt-value { color: var(--text-primary); font-weight: 600; font-family: 'DM Mono', monospace; }

    /* ── Chat ── */
    .stChatMessage { border-radius: 10px; }

    /* ── Table ── */
    [data-testid="stDataFrame"] {
        border: 1px solid var(--border);
        border-radius: 10px;
        overflow: hidden;
    }

    /* ── Tabs — pill toggle style ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: var(--bg-muted);
        padding: 4px;
        border-radius: 10px;
        border: 1px solid var(--border);
        width: fit-content;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 7px !important;
        font-weight: 500;
        font-size: 0.88rem;
        color: var(--text-secondary) !important;
        padding: 7px 22px !important;
        border: none !important;
        background: transparent !important;
        transition: all 0.15s ease;
        white-space: nowrap;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: var(--text-primary) !important;
    }
    .stTabs [aria-selected="true"] {
        color: var(--text-primary) !important;
        background: var(--bg-card) !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.12) !important;
        font-weight: 600 !important;
    }
    .stTabs [data-baseweb="tab-border"] { display: none !important; }
    .stTabs [data-baseweb="tab-highlight"] { display: none !important; }

    /* ── Dividers ── */
    hr { border-color: var(--divider) !important; }

    /* ── Auth hero ── */
    .auth-hero {
        text-align: center;
        padding: 40px 0 24px;
    }
    .auth-hero h1 {
        font-size: 2rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 6px;
    }
    .auth-hero p { color: var(--text-secondary); font-size: 0.95rem; }

    /* ── Section titles ── */
    .section-title {
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin: 0 0 12px;
    }

    /* ── Status badges ── */
    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 99px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-green  { background: var(--badge-green-bg);  color: var(--badge-green-fg); }
    .badge-yellow { background: var(--badge-yellow-bg); color: var(--badge-yellow-fg); }
    .badge-red    { background: var(--badge-red-bg);    color: var(--badge-red-fg); }

    /* ── Hide Streamlit chrome ── */
    footer     { visibility: hidden; }
</style>
""",
    unsafe_allow_html=True,
)

# ============== INITIALIZE ==============

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    st.error("❌ GEMINI_API_KEY not found in .env file!")
    st.stop()

init_db()

for key, default in {
    "logged_in": False,
    "user_id": None,
    "user_obj": None,
    "chat_history": [],
    "extracted_receipt": None,
    "auth_tab": "login",
    "dashboard_days": 30,
    "pending_save": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Process any pending save BEFORE rendering UI
# This survives the file_uploader reset on rerun
if st.session_state.get("pending_save") is not None and st.session_state.get(
    "logged_in"
):
    ps = st.session_state.pending_save
    add_transaction(
        user_id=ps["user_id"],
        amount=ps["amount"],
        description=ps["description"],
        category=ps["category"],
        merchant=ps["merchant"],
        transaction_date=ps["transaction_date"],
    )
    st.session_state.pending_save = None
    st.session_state.extracted_receipt = None


# ============== HELPERS ==============


def category_progress_card(cat_name, spent, budget, color):
    pct = (spent / budget * 100) if budget > 0 else 0
    pct_clamped = min(pct, 100)

    if pct >= 100:
        bar_color, badge_cls, badge_txt = "#ef4444", "badge-red", "Over budget"
    elif pct >= 80:
        bar_color, badge_cls, badge_txt = "#f59e0b", "badge-yellow", f"{pct:.0f}% used"
    else:
        bar_color, badge_cls, badge_txt = "#10b981", "badge-green", f"{pct:.0f}% used"

    st.markdown(
        f"""
    <div class="cat-card">
        <div class="cat-card-header">
            <span class="cat-name">
                <span style="color:{color}; margin-right:6px;">●</span>{cat_name}
            </span>
            <span class="badge {badge_cls}">{badge_txt}</span>
        </div>
        <div class="prog-wrap">
            <div class="prog-fill" style="width:{pct_clamped}%; background:{bar_color};"></div>
        </div>
        <div class="cat-amounts">
            Rp {spent:,.0f} &nbsp;/&nbsp; Rp {budget:,.0f} budget
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def trend_delta(current: float, previous: float):
    if previous <= 0:
        return None, "normal"
    diff_pct = (current - previous) / previous * 100
    sign = "↑" if diff_pct > 0 else "↓"
    return f"{sign} {abs(diff_pct):.1f}% vs previous period", "inverse"


# ============== AUTH PAGE ==============


def show_auth():
    col = st.columns([1, 1.6, 1])[1]
    with col:
        st.markdown(
            """
        <div class="auth-hero">
            <h1>💰 Finance Chatbot</h1>
            <p>Manage your personal finances with AI assistance</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        tab_login, tab_register = st.tabs(["  Sign In  ", "  Register  "])

        with tab_login:
            st.write("")
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button(
                    "Sign In", use_container_width=True, type="primary"
                )

            if submitted:
                if not username or not password:
                    st.error("Please enter your username and password.")
                else:
                    ok, result = login_user(username, password)
                    if ok:
                        st.session_state.logged_in = True
                        st.session_state.user_id = result.user_id
                        st.session_state.user_obj = result
                        st.session_state.chat_history = []
                        get_or_create_default_categories(result.user_id)
                        st.rerun()
                    else:
                        st.error(f"❌ {result}")

        with tab_register:
            st.write("")
            with st.form("register_form"):
                reg_name = st.text_input("Full Name")
                reg_username = st.text_input("Username")
                reg_email = st.text_input("Email")
                reg_password = st.text_input("Password", type="password")
                reg_password2 = st.text_input("Confirm Password", type="password")
                submitted = st.form_submit_button(
                    "Create Account", use_container_width=True, type="primary"
                )

            if submitted:
                if not all(
                    [reg_name, reg_username, reg_email, reg_password, reg_password2]
                ):
                    st.error("All fields are required.")
                elif reg_password != reg_password2:
                    st.error("❌ Passwords do not match.")
                elif len(reg_password) < 6:
                    st.error("❌ Password must be at least 6 characters.")
                else:
                    ok, result = register_user(
                        reg_username, reg_name, reg_email, reg_password
                    )
                    if ok:
                        get_or_create_default_categories(result.user_id)
                        st.success("✅ Account created! Please sign in.")
                    else:
                        st.error(f"❌ {result}")


# ============== MAIN APP ==============


def show_app():
    user = st.session_state.user_obj

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(
            f"""
        <div style="padding: 8px 0 16px;">
            <div style="font-size:1.15rem; font-weight:600; letter-spacing:-0.01em;">💰 Finance</div>
            <div style="font-size:0.88rem; color:#9ca3af; margin-top:2px;">{user.name}</div>
            <div style="font-size:0.78rem; color:#6b7280;">@{user.username}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.divider()

        page = st.radio(
            "Navigation",
            ["Dashboard", "Chatbot", "Add Transaction", "Categories"],
            label_visibility="collapsed",
        )

        st.divider()

        if st.button("Sign Out", use_container_width=True):
            for key in [
                "logged_in",
                "user_id",
                "user_obj",
                "chat_history",
                "extracted_receipt",
            ]:
                st.session_state[key] = (
                    None
                    if key in ["user_id", "user_obj"]
                    else False if key == "logged_in" else []
                )
            st.session_state.extracted_receipt = None
            st.rerun()

        st.markdown("<div style='height:1px'></div>", unsafe_allow_html=True)
        st.caption("Powered by Gemini AI")

    # ── Dashboard ─────────────────────────────────────────────────────────────
    if page == "Dashboard":
        st.markdown("## Dashboard")

        col_flt1, _, _, _ = st.columns([1, 1, 2, 1])
        with col_flt1:
            view_label = st.selectbox(
                "Period",
                ["7 Days", "30 Days", "90 Days"],
                index=1,
                label_visibility="collapsed",
            )
        days_map = {"7 Days": 7, "30 Days": 30, "90 Days": 90}
        days = days_map[view_label]

        # Semua statistik dihitung dinamis berdasarkan filter yang dipilih
        uid = st.session_state.user_id
        current_spending = get_total_spending(uid, days)
        prev_spending = get_total_spending(uid, days * 2) - current_spending
        current_txs = get_user_transactions(uid, days)
        tx_count = len(current_txs)
        avg_per_tx = current_spending / tx_count if tx_count > 0 else 0

        # Top category untuk periode ini
        spending_by_cat = get_spending_by_category(uid, days)
        top_cat = (
            max(spending_by_cat, key=spending_by_cat.get) if spending_by_cat else "-"
        )
        top_cat_amt = spending_by_cat.get(top_cat, 0)

        delta_label, _ = trend_delta(current_spending, prev_spending)

        # Label metrik menyesuaikan filter yang dipilih
        period_label = view_label.replace(" Days", "-Day").replace(" ", "-")

        st.write("")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                f"{period_label} Spending",
                f"Rp {current_spending:,.0f}",
                delta=delta_label,
                delta_color="inverse",
                help=f"Total pengeluaran {days} hari terakhir. Delta vs {days} hari sebelumnya.",
            )
        with col2:
            st.metric(
                "Total Transactions",
                f"{tx_count}",
                help=f"Jumlah transaksi dalam {days} hari terakhir.",
            )
        with col3:
            st.metric(
                "Avg per Transaction",
                f"Rp {avg_per_tx:,.0f}",
                help=f"Rata-rata pengeluaran per transaksi dalam {days} hari terakhir.",
            )
        with col4:
            st.metric(
                "Top Category",
                top_cat,
                delta=f"Rp {top_cat_amt:,.0f}",
                delta_color="off",
                help=f"Kategori terbesar dalam {days} hari terakhir.",
            )

        st.write("")
        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(
                '<div class="section-title">Spending by Category</div>',
                unsafe_allow_html=True,
            )
            spending = get_spending_by_category(st.session_state.user_id, days)
            if spending:
                fig = go.Figure(
                    data=[
                        go.Pie(
                            labels=list(spending.keys()),
                            values=list(spending.values()),
                            hole=0.45,
                            hovertemplate="<b>%{label}</b><br>Rp %{value:,.0f}<br>%{percent}<extra></extra>",
                            textfont_size=13,
                            marker=dict(
                                colors=[
                                    "#3b82f6",
                                    "#10b981",
                                    "#f59e0b",
                                    "#ef4444",
                                    "#8b5cf6",
                                    "#06b6d4",
                                    "#f97316",
                                    "#ec4899",
                                ],
                                line=dict(color="rgba(0,0,0,0.15)", width=2),
                            ),
                        )
                    ]
                )
                fig.update_layout(
                    margin=dict(t=10, b=10, l=10, r=10),
                    height=280,
                    showlegend=True,
                    legend=dict(
                        orientation="v", x=1, y=0.5, font_size=12, font_color="#9ca3af"
                    ),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#9ca3af"),
                )
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("No transaction data available.")

        with col2:
            st.markdown(
                '<div class="section-title">Top Merchants</div>', unsafe_allow_html=True
            )
            transactions = get_user_transactions(st.session_state.user_id, days)
            if transactions:
                merchants = {}
                for t in transactions:
                    merchants[t.merchant] = merchants.get(t.merchant, 0) + t.amount
                top = dict(
                    sorted(merchants.items(), key=lambda x: x[1], reverse=True)[:6]
                )
                fig = go.Figure(
                    go.Bar(
                        x=list(top.values()),
                        y=list(top.keys()),
                        orientation="h",
                        marker_color="#3b82f6",
                        hovertemplate="<b>%{y}</b><br>Rp %{x:,.0f}<extra></extra>",
                    )
                )
                fig.update_layout(
                    margin=dict(t=10, b=10, l=0, r=10),
                    height=280,
                    xaxis=dict(
                        title="",
                        tickformat=",.0f",
                        showgrid=True,
                        gridcolor="rgba(150,150,150,0.12)",
                        color="#9ca3af",
                    ),
                    yaxis=dict(title="", autorange="reversed", color="#9ca3af"),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#9ca3af"),
                )
                st.plotly_chart(fig, width="stretch")
            else:
                st.info("No transaction data available.")

        st.divider()

        st.markdown(
            f'<div class="section-title">Budget Status — {view_label}</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            f"Pengeluaran per kategori dalam {days} hari terakhir dibandingkan budget bulanan."
        )
        cats = get_user_categories(st.session_state.user_id)
        spending_now = get_spending_by_category(st.session_state.user_id, days)

        if cats:
            cols = st.columns(2)
            for i, cat in enumerate(cats):
                spent = spending_now.get(cat.category_name, 0)
                with cols[i % 2]:
                    category_progress_card(
                        cat.category_name, spent, cat.monthly_budget, cat.color_code
                    )
        else:
            st.info("No categories found.")

        st.divider()
        st.markdown(
            '<div class="section-title">Recent Transactions</div>',
            unsafe_allow_html=True,
        )
        df = get_transactions_df(st.session_state.user_id, days)
        if not df.empty:
            df.columns = ["Date", "Merchant", "Description", "Category", "Amount (Rp)"]
            st.dataframe(df, width="stretch", hide_index=True)
        else:
            st.info("No transactions yet. Add one via the 'Add Transaction' menu.")

    # ── Chat Bot ──────────────────────────────────────────────────────────────
    elif page == "Chatbot":
        st.markdown("## AI Finance Assistant")
        st.caption("Ask anything about your finances.")

        st.session_state.chat_history = get_chat_history(
            st.session_state.user_id, limit=20
        )

        with st.container():
            if not st.session_state.chat_history:
                st.markdown(
                    """
                <div style="text-align:center; padding:48px 0;">
                    <div style="font-size:2.5rem; margin-bottom:12px;">💬</div>
                    <div style="font-size:0.95rem; color:var(--text-secondary);">
                        No conversation yet.<br>Type a question or use the quick actions below.
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            else:
                for msg in st.session_state.chat_history:
                    role = "user" if msg["role"] == "user" else "assistant"
                    with st.chat_message(role):
                        st.write(msg["content"])

        st.divider()

        col1, col2 = st.columns([5, 1])
        with col1:
            user_input = st.text_input(
                "Message",
                placeholder="e.g. What is my total spending this month?",
                label_visibility="collapsed",
            )
        with col2:
            send_button = st.button("Send", use_container_width=True, type="primary")

        if send_button and user_input:
            save_chat_message(st.session_state.user_id, "user", user_input)
            spending_summary = generate_spending_summary(st.session_state.user_id)
            enhanced = f"{user_input}\n\n[Financial Context]\n{spending_summary}"
            response, st.session_state.chat_history = chat_with_gemini(
                enhanced, st.session_state.chat_history
            )
            save_chat_message(st.session_state.user_id, "assistant", response)
            st.rerun()

        st.markdown(
            '<div class="section-title" style="margin-top:8px;">Quick Actions</div>',
            unsafe_allow_html=True,
        )
        col1, col2, col3, col4 = st.columns(4)

        def quick_chat(label_user, prompt_ai):
            save_chat_message(st.session_state.user_id, "user", label_user)
            spending_summary = generate_spending_summary(st.session_state.user_id)
            response, st.session_state.chat_history = chat_with_gemini(
                f"{prompt_ai}\n\n{spending_summary}", st.session_state.chat_history
            )
            save_chat_message(st.session_state.user_id, "assistant", response)
            st.rerun()

        with col1:
            if st.button("📊 Analyze Spending", use_container_width=True):
                quick_chat(
                    "Analyze my spending", "Provide a detailed analysis of my spending:"
                )
        with col2:
            if st.button("💡 Saving Tips", use_container_width=True):
                quick_chat(
                    "Saving tips",
                    "Give me the 3 best tips to save money based on my spending habits:",
                )
        with col3:
            if st.button("🎯 Budget Advice", use_container_width=True):
                quick_chat(
                    "Budget advice",
                    "Provide budget recommendations based on my spending:",
                )
        with col4:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                clear_chat_history(st.session_state.user_id)
                st.session_state.chat_history = []
                st.rerun()

    # ── Add Transaction ───────────────────────────────────────────────────────
    elif page == "Add Transaction":
        st.markdown("## Add Transaction")

        tab1, tab2 = st.tabs(["  ✏️ Manual Entry  ", "  📷 Upload Receipt  "])

        cats_db = get_user_categories(st.session_state.user_id)
        categories = (
            [c.category_name for c in cats_db]
            if cats_db
            else [
                "Food & Beverages",
                "Transport",
                "Entertainment",
                "Bills & Utilities",
                "Shopping",
                "Health",
                "Education",
                "Other",
            ]
        )

        with tab1:
            prefill = st.session_state.extracted_receipt or {}
            if prefill:
                st.info(
                    "💡 Form auto-filled from receipt. Review and correct if needed."
                )

            with st.form("add_transaction_form"):
                col_a, col_b = st.columns(2)
                with col_a:
                    merchant = st.text_input(
                        "Merchant / Store",
                        value=prefill.get("merchant", ""),
                        help="Name of the store or place of purchase",
                    )
                    amount = st.number_input(
                        "Amount (Rp)",
                        min_value=0,
                        value=int(prefill.get("amount", 0)),
                        help="Amount spent",
                    )
                with col_b:
                    default_cat = prefill.get("category", "Other")
                    default_idx = (
                        categories.index(default_cat)
                        if default_cat in categories
                        else 0
                    )
                    category = st.selectbox("Category", categories, index=default_idx)
                    transaction_date = st.date_input("Date", datetime.now())

                description = st.text_input(
                    "Description (optional)",
                    value=prefill.get("description", ""),
                    help="Additional notes",
                )
                submitted = st.form_submit_button(
                    "Save Transaction", type="primary", use_container_width=True
                )

                # ✅ FIX: logika harus di DALAM with st.form() agar nilai widget terbaca benar
                if submitted and merchant and amount > 0:
                    add_transaction(
                        user_id=st.session_state.user_id,
                        amount=amount,
                        description=description,
                        category=category,
                        merchant=merchant,
                        transaction_date=datetime.combine(
                            transaction_date, datetime.min.time()
                        ),
                    )
                    st.session_state.extracted_receipt = None
                    st.success(f"✅ Saved: **{merchant}** — Rp {amount:,.0f}")
                    time.sleep(0.8)
                    st.rerun()
                elif submitted:
                    st.error("❌ Merchant and Amount are required.")

        with tab2:
            st.caption(
                "Upload a receipt photo — AI will read it and you can save it directly."
            )

            uploaded_file = st.file_uploader(
                "Choose file",
                type=["jpg", "jpeg", "png", "webp"],
                label_visibility="collapsed",
                help="Formats: JPG, PNG, WEBP. Ensure the photo is clear and text is legible.",
            )

            if uploaded_file is not None:
                img_bytes = uploaded_file.getvalue()
                image = Image.open(io.BytesIO(img_bytes))

                col_img, col_info = st.columns([0.4, 0.6])
                with col_img:
                    st.image(image, caption="Receipt Preview", width="stretch")
                with col_info:
                    st.caption(
                        f"📄 {uploaded_file.name}  ·  {uploaded_file.size / 1024:.1f} KB  ·  {image.size[0]}×{image.size[1]} px"
                    )
                    st.write("")
                    if st.button(
                        "🔍 Read Receipt with AI",
                        type="primary",
                        use_container_width=True,
                    ):
                        with st.spinner("AI is reading the receipt…"):
                            try:
                                suffix = uploaded_file.name.split(".")[-1].lower()
                                mime_map = {
                                    "jpg": "image/jpeg",
                                    "jpeg": "image/jpeg",
                                    "png": "image/png",
                                    "webp": "image/webp",
                                }
                                mime_type = mime_map.get(suffix, "image/jpeg")
                                img_base64 = base64.b64encode(img_bytes).decode("utf-8")
                                result = extract_receipt_data(img_base64, mime_type)
                            except Exception as e:
                                result = None
                                if "quota_exceeded" in str(e):
                                    st.error(
                                        "⚠️ Gemini API quota exceeded. Please try again in a few minutes."
                                    )
                                else:
                                    st.error(f"❌ Error: {e}")
                            else:
                                if result:
                                    st.session_state.extracted_receipt = result
                                else:
                                    st.error(
                                        "❌ Could not read receipt. Make sure the photo is clear and try again."
                                    )

                if st.session_state.extracted_receipt:
                    r = st.session_state.extracted_receipt
                    st.divider()
                    st.success("✅ Receipt read successfully!")

                    st.markdown(
                        f"""
                    <div class="receipt-card">
                        <div class="receipt-row">
                            <span class="receipt-label">🏪 Merchant</span>
                            <span class="receipt-value">{r.get('merchant', '-')}</span>
                        </div>
                        <div class="receipt-row">
                            <span class="receipt-label">📝 Description</span>
                            <span class="receipt-value">{r.get('description', '-')}</span>
                        </div>
                        <div class="receipt-row">
                            <span class="receipt-label">💰 Amount</span>
                            <span class="receipt-value">Rp {int(r.get('amount', 0)):,}</span>
                        </div>
                        <div class="receipt-row">
                            <span class="receipt-label">🏷️ Category</span>
                            <span class="receipt-value">{r.get('category', '-')}</span>
                        </div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                    st.write("")
                    st.markdown("**Confirm & Save**")
                    st.caption("Correct if needed, then click Save.")

                    with st.form("save_receipt_form"):
                        col_r1, col_r2 = st.columns(2)
                        with col_r1:
                            r_merchant = st.text_input(
                                "Merchant / Store", value=r.get("merchant", "")
                            )
                            r_amount = st.number_input(
                                "Amount (Rp)",
                                min_value=0,
                                value=int(r.get("amount", 0)),
                            )
                        with col_r2:
                            default_cat = r.get("category", "Other")
                            default_idx = (
                                categories.index(default_cat)
                                if default_cat in categories
                                else 0
                            )
                            r_category = st.selectbox(
                                "Category", categories, index=default_idx
                            )
                            r_date = st.date_input("Date", datetime.now())

                        r_desc = st.text_input(
                            "Description", value=r.get("description", "")
                        )

                        col_s, col_c = st.columns(2)
                        with col_s:
                            save_btn = st.form_submit_button(
                                "✅ Save Transaction",
                                type="primary",
                                use_container_width=True,
                            )
                        with col_c:
                            reset_btn = st.form_submit_button(
                                "Cancel", use_container_width=True
                            )

                        # ✅ FIX: semua logika harus di DALAM blok with st.form()
                        # agar nilai widget (r_merchant, r_amount, dll) terbaca dengan benar saat submit
                        if save_btn and r_merchant and r_amount > 0:
                            # Normalize category: match to user's category list (case-insensitive)
                            matched_cat = r_category
                            for c in categories:
                                if c.lower() == r_category.lower():
                                    matched_cat = c
                                    break
                            # Store in pending_save so it survives file_uploader reset on rerun
                            st.session_state.pending_save = {
                                "user_id": st.session_state.user_id,
                                "amount": float(r_amount),
                                "description": r_desc,
                                "category": matched_cat,
                                "merchant": r_merchant,
                                "transaction_date": datetime.combine(
                                    r_date, datetime.min.time()
                                ),
                            }
                            st.toast(
                                f"✅ Saved: {r_merchant} — Rp {r_amount:,.0f}",
                                icon="✅",
                            )
                            st.rerun()
                        elif save_btn:
                            st.error("❌ Merchant and Amount are required.")

                        if reset_btn:
                            st.session_state.extracted_receipt = None
                            st.rerun()

            else:
                st.markdown(
                    """
                <div class="upload-zone">
                    <div class="upload-zone-icon">📷</div>
                    <h4>Upload Receipt Photo</h4>
                    <p>Formats: JPG, PNG, or WEBP</p>
                    <p style="margin-top:6px; opacity:0.6;">
                        Tip: Top-down angle, good lighting, text clearly readable
                    </p>
                </div>
                """,
                    unsafe_allow_html=True,
                )

    # ── Categories ────────────────────────────────────────────────────────────
    elif page == "Categories":
        st.markdown("## Manage Categories")

        # Filter periode khusus untuk halaman Categories
        col_cat_flt, _, _ = st.columns([1, 2, 2])
        with col_cat_flt:
            cat_period_label = st.selectbox(
                "Periode",
                ["7 Days", "30 Days", "90 Days"],
                index=1,
                label_visibility="collapsed",
                key="cat_period",
            )
        cat_days_map = {"7 Days": 7, "30 Days": 30, "90 Days": 90}
        cat_days = cat_days_map[cat_period_label]

        spending_now = get_spending_by_category(st.session_state.user_id, cat_days)
        col1, col2 = st.columns([3, 2])

        with col1:
            st.markdown(
                f'<div class="section-title">Active Categories — {cat_period_label}</div>',
                unsafe_allow_html=True,
            )
            cats = get_user_categories(st.session_state.user_id)
            if cats:
                for cat in cats:
                    spent = spending_now.get(cat.category_name, 0)
                    category_progress_card(
                        cat.category_name, spent, cat.monthly_budget, cat.color_code
                    )
            else:
                st.info("No categories yet.")

        with col2:
            st.markdown(
                '<div class="section-title">Add New Category</div>',
                unsafe_allow_html=True,
            )
            with st.form("add_category_form"):
                cat_name = st.text_input("Category Name")
                cat_budget = st.number_input(
                    "Monthly Budget (Rp)", min_value=0, value=0
                )
                submitted = st.form_submit_button(
                    "Add Category", type="primary", use_container_width=True
                )

            if submitted and cat_name:
                create_category(st.session_state.user_id, cat_name, cat_budget)
                st.success(f"✅ Category '{cat_name}' added!")
                st.rerun()
            elif submitted:
                st.error("Category name cannot be empty.")

    # Footer
    st.divider()
    st.caption("Finance Chatbot · Powered by Gemini AI & Streamlit")


# ============== ROUTER ==============

if not st.session_state.logged_in:
    show_auth()
else:
    show_app()
