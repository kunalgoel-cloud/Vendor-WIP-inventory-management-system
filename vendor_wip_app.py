import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime, date, timedelta
import io
import base64
import hashlib
import os

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="VendorLens · WIP Manager",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# STYLING
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0f172a;
    border-right: 1px solid #1e293b;
}
section[data-testid="stSidebar"] * {
    color: #94a3b8 !important;
}
section[data-testid="stSidebar"] .stRadio label {
    font-size: 0.85rem;
    font-weight: 500;
    letter-spacing: 0.02em;
}

/* Main background */
.main { background: #f8fafc; }

/* Cards */
.kpi-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 0.5rem;
}
.kpi-label {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #64748b;
    margin-bottom: 0.3rem;
}
.kpi-value {
    font-size: 1.8rem;
    font-weight: 700;
    color: #0f172a;
    font-family: 'JetBrains Mono', monospace;
}
.kpi-sub {
    font-size: 0.75rem;
    color: #94a3b8;
    margin-top: 0.2rem;
}

/* Section headers */
.section-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 0.25rem;
}
.section-sub {
    font-size: 0.82rem;
    color: #64748b;
    margin-bottom: 1.5rem;
}

/* Status badges */
.badge-ok { background:#dcfce7; color:#166534; padding:2px 10px; border-radius:20px; font-size:0.72rem; font-weight:600; }
.badge-warn { background:#fef9c3; color:#854d0e; padding:2px 10px; border-radius:20px; font-size:0.72rem; font-weight:600; }
.badge-low { background:#fee2e2; color:#991b1b; padding:2px 10px; border-radius:20px; font-size:0.72rem; font-weight:600; }

/* Table tweaks */
.stDataFrame { border-radius: 8px; overflow: hidden; }

/* Alert boxes */
.alert-box {
    padding: 0.75rem 1rem;
    border-radius: 8px;
    font-size: 0.82rem;
    margin-bottom: 1rem;
}
.alert-warn { background:#fefce8; border-left: 3px solid #eab308; color:#713f12; }
.alert-info { background:#eff6ff; border-left: 3px solid #3b82f6; color:#1e40af; }
.alert-danger { background:#fef2f2; border-left: 3px solid #ef4444; color:#991b1b; }

/* Logo area */
.logo-wrap {
    padding: 1.5rem 1.5rem 1rem;
    border-bottom: 1px solid #1e293b;
    margin-bottom: 1rem;
}
.logo-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #f1f5f9 !important;
    letter-spacing: -0.01em;
}
.logo-sub {
    font-size: 0.7rem;
    color: #475569 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

/* Divider */
.divider { border:none; border-top:1px solid #e2e8f0; margin: 1.5rem 0; }

/* Nav items */
.nav-section {
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #334155 !important;
    padding: 0.5rem 1rem 0.25rem;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DB CONNECTION
# ─────────────────────────────────────────────
@st.cache_resource
def get_connection():
    db_url = st.secrets.get("DATABASE_URL", os.environ.get("DATABASE_URL", ""))
    if not db_url:
        st.error("DATABASE_URL not set in Streamlit secrets.")
        st.stop()
    conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    conn.autocommit = True
    return conn

def run_query(sql, params=None, fetch=True):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            if fetch:
                return cur.fetchall()
    except Exception as e:
        conn.rollback()
        st.error(f"DB Error: {e}")
        return []

def run_execute(sql, params=None):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"DB Error: {e}")
        return False

# ─────────────────────────────────────────────
# SCHEMA INIT
# ─────────────────────────────────────────────
def init_schema():
    ddl = """
    CREATE TABLE IF NOT EXISTS item_codes (
        id SERIAL PRIMARY KEY,
        item_code TEXT UNIQUE NOT NULL,
        item_name TEXT NOT NULL,
        item_type TEXT NOT NULL CHECK (item_type IN ('parent','child')),
        uom TEXT NOT NULL DEFAULT 'PCS',
        safety_stock NUMERIC DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS bom (
        id SERIAL PRIMARY KEY,
        parent_code TEXT NOT NULL REFERENCES item_codes(item_code) ON DELETE CASCADE,
        child_code TEXT NOT NULL REFERENCES item_codes(item_code) ON DELETE CASCADE,
        qty_per NUMERIC NOT NULL,
        UNIQUE(parent_code, child_code)
    );

    CREATE TABLE IF NOT EXISTS inbound (
        id SERIAL PRIMARY KEY,
        txn_date DATE NOT NULL,
        item_code TEXT NOT NULL REFERENCES item_codes(item_code),
        qty NUMERIC NOT NULL,
        invoice_no TEXT,
        supplier TEXT,
        invoice_file BYTEA,
        invoice_filename TEXT,
        remarks TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS assembly (
        id SERIAL PRIMARY KEY,
        txn_date DATE NOT NULL,
        parent_code TEXT NOT NULL REFERENCES item_codes(item_code),
        qty_assembled NUMERIC NOT NULL,
        remarks TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS outbound (
        id SERIAL PRIMARY KEY,
        txn_date DATE NOT NULL,
        parent_code TEXT NOT NULL REFERENCES item_codes(item_code),
        qty NUMERIC NOT NULL,
        customer TEXT,
        gate_pass_no TEXT,
        gate_pass_file BYTEA,
        gate_pass_filename TEXT,
        remarks TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def get_items(item_type=None):
    if item_type:
        rows = run_query("SELECT * FROM item_codes WHERE item_type=%s ORDER BY item_code", (item_type,))
    else:
        rows = run_query("SELECT * FROM item_codes ORDER BY item_type, item_code")
    return pd.DataFrame(rows) if rows else pd.DataFrame()

def get_stock():
    """Compute current stock for all items"""
    # Child stock: inbound - consumed in assembly
    child_stock_sql = """
    WITH inb AS (
        SELECT item_code, COALESCE(SUM(qty),0) AS total_in
        FROM inbound GROUP BY item_code
    ),
    consumed AS (
        SELECT b.child_code AS item_code, COALESCE(SUM(a.qty_assembled * b.qty_per),0) AS total_used
        FROM assembly a
        JOIN bom b ON a.parent_code = b.parent_code
        GROUP BY b.child_code
    )
    SELECT ic.item_code, ic.item_name, ic.item_type, ic.uom, ic.safety_stock,
           COALESCE(i.total_in,0) AS total_inbound,
           COALESCE(c.total_used,0) AS total_consumed,
           COALESCE(i.total_in,0) - COALESCE(c.total_used,0) AS stock_on_hand
    FROM item_codes ic
    LEFT JOIN inb i ON i.item_code = ic.item_code
    LEFT JOIN consumed c ON c.item_code = ic.item_code
    WHERE ic.item_type = 'child'
    """

    parent_stock_sql = """
    WITH asm AS (
        SELECT parent_code, COALESCE(SUM(qty_assembled),0) AS total_asm
        FROM assembly GROUP BY parent_code
    ),
    out AS (
        SELECT parent_code, COALESCE(SUM(qty),0) AS total_out
        FROM outbound GROUP BY parent_code
    )
    SELECT ic.item_code, ic.item_name, ic.item_type, ic.uom, ic.safety_stock,
           COALESCE(a.total_asm,0) AS total_assembled,
           COALESCE(o.total_out,0) AS total_dispatched,
           COALESCE(a.total_asm,0) - COALESCE(o.total_out,0) AS stock_on_hand
    FROM item_codes ic
    LEFT JOIN asm a ON a.parent_code = ic.item_code
    LEFT JOIN out o ON o.parent_code = ic.item_code
    WHERE ic.item_type = 'parent'
    """
    child_rows = run_query(child_stock_sql)
    parent_rows = run_query(parent_stock_sql)
    child_df = pd.DataFrame(child_rows) if child_rows else pd.DataFrame()
    parent_df = pd.DataFrame(parent_rows) if parent_rows else pd.DataFrame()
    return child_df, parent_df

def to_csv_download(df, filename):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    return f'<a href="data:file/csv;base64,{b64}" download="{filename}" style="text-decoration:none"><button style="background:#0f172a;color:white;border:none;padding:6px 14px;border-radius:6px;font-size:0.78rem;cursor:pointer;font-family:Inter,sans-serif;">⬇ Download CSV</button></a>'

def stock_badge(on_hand, safety):
    if on_hand <= 0:
        return '<span class="badge-low">OUT</span>'
    elif on_hand <= safety:
        return '<span class="badge-warn">LOW</span>'
    else:
        return '<span class="badge-ok">OK</span>'

# ─────────────────────────────────────────────
# SIDEBAR NAV
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="logo-wrap">
        <div class="logo-title">📦 VendorLens</div>
        <div class="logo-sub">WIP Stock Manager</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="nav-section">Master Data</div>', unsafe_allow_html=True)
    page = st.radio("", [
        "🏷 Item Codes",
        "🔗 BOM",
    ], key="nav1", label_visibility="collapsed")

    st.markdown('<div class="nav-section">Transactions</div>', unsafe_allow_html=True)
    page2 = st.radio("", [
        "📥 Inbound",
        "🔧 Assembly",
        "📤 Outbound",
    ], key="nav2", label_visibility="collapsed")

    st.markdown('<div class="nav-section">Intelligence</div>', unsafe_allow_html=True)
    page3 = st.radio("", [
        "📊 Stock",
        "🔮 Forecast",
        "📋 Ledger",
    ], key="nav3", label_visibility="collapsed")

    st.markdown("---")
    st.markdown('<div class="nav-section">Global Filters</div>', unsafe_allow_html=True)

    filter_date_from = st.date_input("From Date", value=date.today().replace(day=1))
    filter_date_to = st.date_input("To Date", value=date.today())

    all_items_df = get_items()
    item_filter_options = ["All Items"]
    if not all_items_df.empty:
        item_filter_options += all_items_df["item_code"].tolist()
    filter_item = st.selectbox("Item Filter", item_filter_options)

    # Determine active page
    active_pages = {
        "nav1": page, "nav2": page2, "nav3": page3
    }
    # Track which radio was last changed via session state
    if "last_page" not in st.session_state:
        st.session_state.last_page = "📊 Stock"

    for key, val in active_pages.items():
        if val != st.session_state.get(f"prev_{key}"):
            st.session_state.last_page = val
            st.session_state[f"prev_{key}"] = val

active = st.session_state.last_page

# Init schema
init_schema()

# ─────────────────────────────────────────────
# PAGE: ITEM CODES
# ─────────────────────────────────────────────
if active == "🏷 Item Codes":
    st.markdown('<div class="section-title">Item Codes</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Define all items in the system — parent (finished goods) and child (components)</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["➕ Create Item", "📋 View All"])

    with tab1:
        with st.form("item_form"):
            col1, col2 = st.columns(2)
            with col1:
                item_code = st.text_input("Item Code *", placeholder="e.g. FG-001")
                item_name = st.text_input("Item Name *", placeholder="e.g. Gift Box Assembly")
                item_type = st.selectbox("Classification *", ["parent", "child"])
            with col2:
                uom = st.selectbox("Unit of Measure", ["PCS", "KG", "MTR", "BOX", "SET", "ROLL", "LTR"])
                safety_stock = st.number_input("Safety Stock Qty", min_value=0.0, step=1.0)
            submitted = st.form_submit_button("Create Item Code", type="primary")
            if submitted:
                if not item_code or not item_name:
                    st.error("Item Code and Name are required.")
                else:
                    ok = run_execute(
                        "INSERT INTO item_codes (item_code, item_name, item_type, uom, safety_stock) VALUES (%s,%s,%s,%s,%s) ON CONFLICT (item_code) DO UPDATE SET item_name=%s, item_type=%s, uom=%s, safety_stock=%s",
                        (item_code, item_name, item_type, uom, safety_stock, item_name, item_type, uom, safety_stock)
                    )
                    if ok:
                        st.success(f"✅ Item '{item_code}' saved.")

    with tab2:
        df = get_items()
        if not df.empty:
            # Apply item filter
            if filter_item != "All Items":
                df = df[df["item_code"] == filter_item]

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Parents (FG):** {len(df[df['item_type']=='parent'])}")
            with col2:
                st.markdown(f"**Children (Components):** {len(df[df['item_type']=='child'])}")

            st.dataframe(df[["item_code","item_name","item_type","uom","safety_stock","created_at"]], use_container_width=True, hide_index=True)
            st.markdown(to_csv_download(df, "item_codes.csv"), unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("**Edit Safety Stock**")
            edit_items = df["item_code"].tolist()
            e_code = st.selectbox("Select Item", edit_items, key="edit_ss")
            e_ss = st.number_input("New Safety Stock", min_value=0.0, step=1.0, key="edit_ss_val")
            if st.button("Update Safety Stock"):
                run_execute("UPDATE item_codes SET safety_stock=%s WHERE item_code=%s", (e_ss, e_code))
                st.success("Updated.")
                st.rerun()
        else:
            st.markdown('<div class="alert-info alert-box">No items created yet. Use the form above to add items.</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PAGE: BOM
# ─────────────────────────────────────────────
elif active == "🔗 BOM":
    st.markdown('<div class="section-title">Bill of Materials</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Define how many child components are needed to assemble one parent item</div>', unsafe_allow_html=True)

    parents_df = get_items("parent")
    children_df = get_items("child")

    if parents_df.empty or children_df.empty:
        st.markdown('<div class="alert-warn alert-box">⚠ You need at least one parent and one child item before defining BOMs.</div>', unsafe_allow_html=True)
    else:
        tab1, tab2 = st.tabs(["➕ Add BOM Line", "📋 View BOM"])

        with tab1:
            with st.form("bom_form"):
                parent_opts = parents_df["item_code"].tolist()
                child_opts = children_df["item_code"].tolist()
                col1, col2, col3 = st.columns(3)
                with col1:
                    parent_sel = st.selectbox("Parent Item (FG)", parent_opts)
                with col2:
                    child_sel = st.selectbox("Child Component", child_opts)
                with col3:
                    qty_per = st.number_input("Qty per Parent", min_value=0.01, step=0.5, value=1.0)
                if st.form_submit_button("Add BOM Line", type="primary"):
                    ok = run_execute(
                        "INSERT INTO bom (parent_code, child_code, qty_per) VALUES (%s,%s,%s) ON CONFLICT (parent_code, child_code) DO UPDATE SET qty_per=%s",
                        (parent_sel, child_sel, qty_per, qty_per)
                    )
                    if ok:
                        st.success(f"✅ BOM line added: {parent_sel} → {child_sel} × {qty_per}")

        with tab2:
            bom_rows = run_query("""
                SELECT b.parent_code, p.item_name AS parent_name,
                       b.child_code, c.item_name AS child_name,
                       b.qty_per, c.uom
                FROM bom b
                JOIN item_codes p ON p.item_code = b.parent_code
                JOIN item_codes c ON c.item_code = b.child_code
                ORDER BY b.parent_code, b.child_code
            """)
            if bom_rows:
                bom_df = pd.DataFrame(bom_rows)
                if filter_item != "All Items":
                    bom_df = bom_df[(bom_df["parent_code"] == filter_item) | (bom_df["child_code"] == filter_item)]
                for parent in bom_df["parent_code"].unique():
                    sub = bom_df[bom_df["parent_code"] == parent]
                    pname = sub.iloc[0]["parent_name"]
                    st.markdown(f"**{parent} — {pname}**")
                    st.dataframe(sub[["child_code","child_name","qty_per","uom"]].rename(
                        columns={"child_code":"Component","child_name":"Name","qty_per":"Qty/Parent","uom":"UOM"}
                    ), use_container_width=True, hide_index=True)
                st.markdown(to_csv_download(bom_df, "bom.csv"), unsafe_allow_html=True)
            else:
                st.markdown('<div class="alert-info alert-box">No BOM entries yet.</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PAGE: INBOUND
# ─────────────────────────────────────────────
elif active == "📥 Inbound":
    st.markdown('<div class="section-title">Inbound Stock</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Record child components received at the vendor facility</div>', unsafe_allow_html=True)

    children_df = get_items("child")
    if children_df.empty:
        st.markdown('<div class="alert-warn alert-box">⚠ No child items defined. Please create items first.</div>', unsafe_allow_html=True)
    else:
        tab1, tab2, tab3 = st.tabs(["➕ Manual Entry", "📤 Bulk Upload", "📋 History"])

        with tab1:
            with st.form("inbound_form"):
                col1, col2 = st.columns(2)
                with col1:
                    txn_date = st.date_input("Date *", value=date.today())
                    item_sel = st.selectbox("Item (Child Component) *", children_df["item_code"].tolist())
                    qty = st.number_input("Quantity *", min_value=0.01, step=1.0)
                with col2:
                    invoice_no = st.text_input("Invoice No.")
                    supplier = st.text_input("Supplier Name")
                    remarks = st.text_area("Remarks", height=68)
                invoice_file = st.file_uploader("Attach Invoice (PDF/Image)", type=["pdf","png","jpg","jpeg"])
                if st.form_submit_button("Record Inbound", type="primary"):
                    file_data = invoice_file.read() if invoice_file else None
                    file_name = invoice_file.name if invoice_file else None
                    ok = run_execute(
                        "INSERT INTO inbound (txn_date, item_code, qty, invoice_no, supplier, invoice_file, invoice_filename, remarks) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                        (txn_date, item_sel, qty, invoice_no, supplier, file_data, file_name, remarks)
                    )
                    if ok:
                        st.success(f"✅ Inbound recorded: {qty} × {item_sel}")

        with tab2:
            st.markdown("**Upload CSV** — columns: `date (YYYY-MM-DD)`, `item_code`, `qty`, `invoice_no`, `supplier`")
            uploaded = st.file_uploader("Choose CSV", type=["csv"], key="inb_upload")
            if uploaded:
                try:
                    udf = pd.read_csv(uploaded)
                    st.dataframe(udf.head(10), use_container_width=True)
                    if st.button("Import All Rows"):
                        errors = []
                        for _, row in udf.iterrows():
                            ok = run_execute(
                                "INSERT INTO inbound (txn_date, item_code, qty, invoice_no, supplier) VALUES (%s,%s,%s,%s,%s)",
                                (row.get("date"), row.get("item_code"), row.get("qty"), row.get("invoice_no",""), row.get("supplier",""))
                            )
                            if not ok:
                                errors.append(row.get("item_code"))
                        if errors:
                            st.error(f"Failed rows: {errors}")
                        else:
                            st.success("All rows imported.")
                except Exception as e:
                    st.error(f"Parse error: {e}")

        with tab3:
            rows = run_query(
                "SELECT id, txn_date, item_code, qty, invoice_no, supplier, invoice_filename, remarks, created_at FROM inbound WHERE txn_date BETWEEN %s AND %s ORDER BY txn_date DESC",
                (filter_date_from, filter_date_to)
            )
            if rows:
                df = pd.DataFrame(rows)
                if filter_item != "All Items":
                    df = df[df["item_code"] == filter_item]
                st.dataframe(df.drop(columns=["id"]), use_container_width=True, hide_index=True)
                st.markdown(to_csv_download(df.drop(columns=["id"]), "inbound_history.csv"), unsafe_allow_html=True)
            else:
                st.markdown('<div class="alert-info alert-box">No inbound records in selected date range.</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PAGE: ASSEMBLY
# ─────────────────────────────────────────────
elif active == "🔧 Assembly":
    st.markdown('<div class="section-title">Assembly Log</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Record finished goods assembled at the vendor facility — automatically deducts child components</div>', unsafe_allow_html=True)

    parents_df = get_items("parent")
    if parents_df.empty:
        st.markdown('<div class="alert-warn alert-box">⚠ No parent items defined.</div>', unsafe_allow_html=True)
    else:
        tab1, tab2 = st.tabs(["➕ Record Assembly", "📋 History"])

        with tab1:
            col1, col2 = st.columns([2, 1])
            with col1:
                parent_sel = st.selectbox("Parent Item (FG to be assembled)", parents_df["item_code"].tolist())
            with col2:
                qty_to_assemble = st.number_input("Qty to Assemble", min_value=1.0, step=1.0, value=1.0)

            # Preview BOM consumption
            bom_preview = run_query(
                "SELECT b.child_code, ic.item_name, b.qty_per, ic.uom FROM bom b JOIN item_codes ic ON ic.item_code=b.child_code WHERE b.parent_code=%s",
                (parent_sel,)
            )
            if bom_preview:
                st.markdown("**Component Consumption Preview**")
                prev_df = pd.DataFrame(bom_preview)
                prev_df["Total Required"] = prev_df["qty_per"] * qty_to_assemble

                # Check stock availability
                child_stock, _ = get_stock()
                rows_display = []
                can_assemble = True
                for _, r in prev_df.iterrows():
                    available = 0
                    if not child_stock.empty:
                        match = child_stock[child_stock["item_code"] == r["child_code"]]
                        available = float(match["stock_on_hand"].iloc[0]) if not match.empty else 0
                    status = "✅" if available >= r["Total Required"] else "❌ SHORT"
                    if available < r["Total Required"]:
                        can_assemble = False
                    rows_display.append({
                        "Component": r["child_code"],
                        "Name": r["item_name"],
                        "Qty/Unit": r["qty_per"],
                        "Total Needed": r["Total Required"],
                        "In Stock": available,
                        "Status": status
                    })
                st.dataframe(pd.DataFrame(rows_display), use_container_width=True, hide_index=True)
                if not can_assemble:
                    st.markdown('<div class="alert-danger alert-box">❌ Insufficient stock for one or more components.</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="alert-warn alert-box">⚠ No BOM defined for this parent. Please add BOM first.</div>', unsafe_allow_html=True)

            with st.form("asm_form"):
                txn_date = st.date_input("Assembly Date", value=date.today())
                remarks = st.text_area("Remarks", height=60)
                submitted = st.form_submit_button("Record Assembly", type="primary")
                if submitted:
                    if not bom_preview:
                        st.error("Cannot record assembly without BOM.")
                    else:
                        ok = run_execute(
                            "INSERT INTO assembly (txn_date, parent_code, qty_assembled, remarks) VALUES (%s,%s,%s,%s)",
                            (txn_date, parent_sel, qty_to_assemble, remarks)
                        )
                        if ok:
                            st.success(f"✅ Assembly recorded: {qty_to_assemble} × {parent_sel}")

        with tab2:
            rows = run_query(
                "SELECT a.id, a.txn_date, a.parent_code, ic.item_name, a.qty_assembled, a.remarks, a.created_at FROM assembly a JOIN item_codes ic ON ic.item_code=a.parent_code WHERE a.txn_date BETWEEN %s AND %s ORDER BY a.txn_date DESC",
                (filter_date_from, filter_date_to)
            )
            if rows:
                df = pd.DataFrame(rows)
                if filter_item != "All Items":
                    df = df[df["parent_code"] == filter_item]
                st.dataframe(df.drop(columns=["id"]), use_container_width=True, hide_index=True)
                st.markdown(to_csv_download(df.drop(columns=["id"]), "assembly_history.csv"), unsafe_allow_html=True)
            else:
                st.markdown('<div class="alert-info alert-box">No assembly records in selected date range.</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PAGE: OUTBOUND
# ─────────────────────────────────────────────
elif active == "📤 Outbound":
    st.markdown('<div class="section-title">Outbound Dispatch</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Record finished goods dispatched to customers from the vendor facility</div>', unsafe_allow_html=True)

    parents_df = get_items("parent")
    if parents_df.empty:
        st.markdown('<div class="alert-warn alert-box">⚠ No parent items defined.</div>', unsafe_allow_html=True)
    else:
        tab1, tab2 = st.tabs(["➕ Record Dispatch", "📋 History"])

        with tab1:
            with st.form("outbound_form"):
                col1, col2 = st.columns(2)
                with col1:
                    txn_date = st.date_input("Dispatch Date *", value=date.today())
                    parent_sel = st.selectbox("Parent Item (FG) *", parents_df["item_code"].tolist())
                    qty = st.number_input("Qty Dispatched *", min_value=0.01, step=1.0)
                with col2:
                    customer = st.text_input("Customer Name")
                    gate_pass_no = st.text_input("Gate Pass No.")
                    remarks = st.text_area("Remarks", height=68)
                gate_pass_file = st.file_uploader("Attach Gate Pass (PDF/Image)", type=["pdf","png","jpg","jpeg"])

                submitted = st.form_submit_button("Record Outbound", type="primary")
                if submitted:
                    # Check FG stock
                    _, parent_stock = get_stock()
                    avail_fg = 0
                    if not parent_stock.empty:
                        match = parent_stock[parent_stock["item_code"] == parent_sel]
                        avail_fg = float(match["stock_on_hand"].iloc[0]) if not match.empty else 0
                    if qty > avail_fg:
                        st.error(f"❌ Insufficient FG stock. Available: {avail_fg}")
                    else:
                        file_data = gate_pass_file.read() if gate_pass_file else None
                        file_name = gate_pass_file.name if gate_pass_file else None
                        ok = run_execute(
                            "INSERT INTO outbound (txn_date, parent_code, qty, customer, gate_pass_no, gate_pass_file, gate_pass_filename, remarks) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                            (txn_date, parent_sel, qty, customer, gate_pass_no, file_data, file_name, remarks)
                        )
                        if ok:
                            st.success(f"✅ Outbound recorded: {qty} × {parent_sel} → {customer}")

        with tab2:
            rows = run_query(
                "SELECT o.txn_date, o.parent_code, ic.item_name, o.qty, o.customer, o.gate_pass_no, o.gate_pass_filename, o.remarks, o.created_at FROM outbound o JOIN item_codes ic ON ic.item_code=o.parent_code WHERE o.txn_date BETWEEN %s AND %s ORDER BY o.txn_date DESC",
                (filter_date_from, filter_date_to)
            )
            if rows:
                df = pd.DataFrame(rows)
                if filter_item != "All Items":
                    df = df[df["parent_code"] == filter_item]
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.markdown(to_csv_download(df, "outbound_history.csv"), unsafe_allow_html=True)
            else:
                st.markdown('<div class="alert-info alert-box">No outbound records in selected date range.</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PAGE: STOCK
# ─────────────────────────────────────────────
elif active == "📊 Stock":
    st.markdown('<div class="section-title">Live Stock Position</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Real-time inventory across all items at the vendor facility</div>', unsafe_allow_html=True)

    child_stock, parent_stock = get_stock()

    # KPI row
    total_child_items = len(child_stock) if not child_stock.empty else 0
    low_child = len(child_stock[child_stock["stock_on_hand"] <= child_stock["safety_stock"]]) if not child_stock.empty else 0
    out_child = len(child_stock[child_stock["stock_on_hand"] <= 0]) if not child_stock.empty else 0
    total_fg = float(parent_stock["stock_on_hand"].sum()) if not parent_stock.empty else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Component SKUs</div><div class="kpi-value">{total_child_items}</div><div class="kpi-sub">tracked items</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Below Safety Stock</div><div class="kpi-value" style="color:#d97706">{low_child}</div><div class="kpi-sub">need reorder</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Out of Stock</div><div class="kpi-value" style="color:#dc2626">{out_child}</div><div class="kpi-sub">zero inventory</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">FG Ready to Ship</div><div class="kpi-value" style="color:#16a34a">{total_fg:,.0f}</div><div class="kpi-sub">assembled units</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("**Child Components (Raw / WIP)**")
        if not child_stock.empty:
            df = child_stock.copy()
            if filter_item != "All Items":
                df = df[df["item_code"] == filter_item]
            df["Status"] = df.apply(lambda r: stock_badge(r["stock_on_hand"], r["safety_stock"]), axis=1)
            display_cols = ["item_code","item_name","uom","total_inbound","total_consumed","stock_on_hand","safety_stock","Status"]
            html_table = df[display_cols].to_html(index=False, escape=False, classes="")
            st.markdown(html_table, unsafe_allow_html=True)
            st.markdown(to_csv_download(df[display_cols], "child_stock.csv"), unsafe_allow_html=True)
        else:
            st.markdown('<div class="alert-info alert-box">No component data yet.</div>', unsafe_allow_html=True)

    with col_r:
        st.markdown("**Parent Items (Finished Goods)**")
        if not parent_stock.empty:
            df = parent_stock.copy()
            if filter_item != "All Items":
                df = df[df["item_code"] == filter_item]
            df["Status"] = df.apply(lambda r: stock_badge(r["stock_on_hand"], r["safety_stock"]), axis=1)
            display_cols = ["item_code","item_name","uom","total_assembled","total_dispatched","stock_on_hand","safety_stock","Status"]
            html_table = df[display_cols].to_html(index=False, escape=False, classes="")
            st.markdown(html_table, unsafe_allow_html=True)
            st.markdown(to_csv_download(df[display_cols], "parent_stock.csv"), unsafe_allow_html=True)
        else:
            st.markdown('<div class="alert-info alert-box">No FG data yet.</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PAGE: FORECAST
# ─────────────────────────────────────────────
elif active == "🔮 Forecast":
    st.markdown('<div class="section-title">Production Forecast</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Enter target FG quantities — system calculates component gaps and what can be made today</div>', unsafe_allow_html=True)

    parents_df = get_items("parent")
    if parents_df.empty:
        st.markdown('<div class="alert-warn alert-box">⚠ No parent items available.</div>', unsafe_allow_html=True)
    else:
        st.markdown("**Set Production Targets**")
        parent_list = parents_df["item_code"].tolist()

        # Multi-item forecast
        num_items = st.number_input("How many FG items to plan?", min_value=1, max_value=10, value=1, step=1)
        targets = {}
        cols = st.columns(min(num_items, 3))
        for i in range(num_items):
            with cols[i % 3]:
                p = st.selectbox(f"FG Item {i+1}", parent_list, key=f"fc_p_{i}")
                q = st.number_input(f"Target Qty", min_value=0.0, step=1.0, key=f"fc_q_{i}", value=100.0)
                targets[p] = targets.get(p, 0) + q

        if st.button("Run Forecast", type="primary"):
            child_stock, parent_stock = get_stock()
            st.markdown("---")
            st.markdown("### Forecast Results")

            # Aggregate child requirements across all targets
            req_map = {}  # child_code -> total required
            for parent, target_qty in targets.items():
                bom_rows = run_query(
                    "SELECT b.child_code, b.qty_per FROM bom b WHERE b.parent_code=%s", (parent,)
                )
                for r in bom_rows:
                    cc = r["child_code"]
                    req_map[cc] = req_map.get(cc, 0) + r["qty_per"] * target_qty

            if not req_map:
                st.markdown('<div class="alert-warn alert-box">⚠ No BOM defined for selected items.</div>', unsafe_allow_html=True)
            else:
                results = []
                limiting_factor = None
                max_producible = float("inf")

                for child_code, total_req in req_map.items():
                    stock_val = 0
                    safety_val = 0
                    if not child_stock.empty:
                        match = child_stock[child_stock["item_code"] == child_code]
                        if not match.empty:
                            stock_val = float(match["stock_on_hand"].iloc[0])
                            safety_val = float(match["safety_stock"].iloc[0])
                    shortfall = max(0, total_req - stock_val)
                    to_order = max(0, shortfall)
                    status = "✅ OK" if stock_val >= total_req else "❌ SHORT"
                    # How many can we make with current stock?
                    if total_req > 0:
                        ratio = stock_val / total_req
                        if ratio < max_producible:
                            max_producible = ratio
                            limiting_factor = child_code
                    results.append({
                        "Component": child_code,
                        "Required": total_req,
                        "In Stock": stock_val,
                        "Safety Stock": safety_val,
                        "Shortfall": shortfall,
                        "To Order": to_order,
                        "Status": status
                    })

                res_df = pd.DataFrame(results)
                st.dataframe(res_df, use_container_width=True, hide_index=True)
                st.markdown(to_csv_download(res_df, "forecast_plan.csv"), unsafe_allow_html=True)

                # Summary
                total_targets = sum(targets.values())
                producible = int(max_producible * total_targets) if max_producible < float("inf") else int(total_targets)
                producible = max(0, min(producible, int(total_targets)))

                st.markdown("---")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f'<div class="kpi-card"><div class="kpi-label">Target Production</div><div class="kpi-value">{int(total_targets):,}</div><div class="kpi-sub">units planned</div></div>', unsafe_allow_html=True)
                with col2:
                    color = "#16a34a" if producible >= total_targets else "#d97706"
                    st.markdown(f'<div class="kpi-card"><div class="kpi-label">Can Produce Now</div><div class="kpi-value" style="color:{color}">{producible:,}</div><div class="kpi-sub">with current stock</div></div>', unsafe_allow_html=True)
                with col3:
                    gap = int(total_targets) - producible
                    st.markdown(f'<div class="kpi-card"><div class="kpi-label">Production Gap</div><div class="kpi-value" style="color:#dc2626">{max(0,gap):,}</div><div class="kpi-sub">units need stock top-up</div></div>', unsafe_allow_html=True)

                if limiting_factor and producible < total_targets:
                    st.markdown(f'<div class="alert-danger alert-box">🔴 Bottleneck component: <b>{limiting_factor}</b> — order this first to unblock production.</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PAGE: LEDGER
# ─────────────────────────────────────────────
elif active == "📋 Ledger":
    st.markdown('<div class="section-title">Transaction Ledger</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Complete tabular log of all movements — use this to tally with the vendor</div>', unsafe_allow_html=True)

    ledger_sql = """
    SELECT 
        txn_date,
        'Inbound' AS txn_type,
        item_code,
        'child' AS item_class,
        qty AS qty_in,
        0 AS qty_out,
        invoice_no AS reference,
        supplier AS party,
        remarks
    FROM inbound
    WHERE txn_date BETWEEN %s AND %s

    UNION ALL

    SELECT 
        txn_date,
        'Assembly' AS txn_type,
        parent_code AS item_code,
        'parent' AS item_class,
        qty_assembled AS qty_in,
        0 AS qty_out,
        '' AS reference,
        '' AS party,
        remarks
    FROM assembly
    WHERE txn_date BETWEEN %s AND %s

    UNION ALL

    SELECT 
        txn_date,
        'Outbound' AS txn_type,
        parent_code AS item_code,
        'parent' AS item_class,
        0 AS qty_in,
        qty AS qty_out,
        gate_pass_no AS reference,
        customer AS party,
        remarks
    FROM outbound
    WHERE txn_date BETWEEN %s AND %s

    ORDER BY txn_date DESC, txn_type
    """

    rows = run_query(ledger_sql, (
        filter_date_from, filter_date_to,
        filter_date_from, filter_date_to,
        filter_date_from, filter_date_to,
    ))

    if rows:
        df = pd.DataFrame(rows)
        if filter_item != "All Items":
            df = df[df["item_code"] == filter_item]

        # Summary KPIs
        col1, col2, col3, col4 = st.columns(4)
        total_inb = df[df["txn_type"]=="Inbound"]["qty_in"].sum()
        total_asm = df[df["txn_type"]=="Assembly"]["qty_in"].sum()
        total_out = df[df["txn_type"]=="Outbound"]["qty_out"].sum()
        total_txn = len(df)

        with col1:
            st.markdown(f'<div class="kpi-card"><div class="kpi-label">Total Transactions</div><div class="kpi-value">{total_txn}</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="kpi-card"><div class="kpi-label">Components In</div><div class="kpi-value">{total_inb:,.0f}</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="kpi-card"><div class="kpi-label">FG Assembled</div><div class="kpi-value">{total_asm:,.0f}</div></div>', unsafe_allow_html=True)
        with col4:
            st.markdown(f'<div class="kpi-card"><div class="kpi-label">FG Dispatched</div><div class="kpi-value">{total_out:,.0f}</div></div>', unsafe_allow_html=True)

        st.markdown("---")

        # Filter by type
        txn_filter = st.multiselect("Filter by Transaction Type", ["Inbound","Assembly","Outbound"], default=["Inbound","Assembly","Outbound"])
        df_filtered = df[df["txn_type"].isin(txn_filter)]

        st.dataframe(df_filtered, use_container_width=True, hide_index=True)
        st.markdown(to_csv_download(df_filtered, "ledger.csv"), unsafe_allow_html=True)

        # Running balance per item
        st.markdown("---")
        st.markdown("**Running Stock Tally (by Item)**")
        tally = []
        for item in df["item_code"].unique():
            item_df = df[df["item_code"] == item]
            total_in = item_df["qty_in"].sum()
            total_out_val = item_df["qty_out"].sum()
            tally.append({
                "Item Code": item,
                "Total In": total_in,
                "Total Out": total_out_val,
                "Net": total_in - total_out_val
            })
        tally_df = pd.DataFrame(tally).sort_values("Item Code")
        st.dataframe(tally_df, use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="alert-info alert-box">No transactions found in selected date range.</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<div style="text-align:center;font-size:0.72rem;color:#94a3b8;padding:0.5rem 0;">VendorLens WIP Manager · Built on Streamlit + Supabase · All data stored securely in PostgreSQL</div>',
    unsafe_allow_html=True
)
