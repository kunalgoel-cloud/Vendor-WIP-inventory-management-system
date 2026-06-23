import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import date
import base64

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

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

section[data-testid="stSidebar"] {
    background: #0f172a;
    border-right: 1px solid #1e293b;
}
section[data-testid="stSidebar"] * { color: #94a3b8 !important; }
section[data-testid="stSidebar"] .stRadio label {
    font-size: 0.85rem; font-weight: 500; letter-spacing: 0.02em;
}

.main { background: #f8fafc; }

.kpi-card {
    background: white; border: 1px solid #e2e8f0;
    border-radius: 10px; padding: 1.2rem 1.4rem; margin-bottom: 0.5rem;
}
.kpi-label {
    font-size: 0.7rem; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: #64748b; margin-bottom: 0.3rem;
}
.kpi-value {
    font-size: 1.8rem; font-weight: 700; color: #0f172a;
    font-family: 'JetBrains Mono', monospace;
}
.kpi-sub { font-size: 0.75rem; color: #94a3b8; margin-top: 0.2rem; }

.section-title { font-size: 1.25rem; font-weight: 700; color: #0f172a; margin-bottom: 0.25rem; }
.section-sub   { font-size: 0.82rem; color: #64748b; margin-bottom: 1.5rem; }

.badge-ok   { background:#dcfce7; color:#166534; padding:2px 10px; border-radius:20px; font-size:0.72rem; font-weight:600; }
.badge-warn { background:#fef9c3; color:#854d0e; padding:2px 10px; border-radius:20px; font-size:0.72rem; font-weight:600; }
.badge-low  { background:#fee2e2; color:#991b1b; padding:2px 10px; border-radius:20px; font-size:0.72rem; font-weight:600; }

.stDataFrame { border-radius: 8px; overflow: hidden; }

.alert-box   { padding: 0.75rem 1rem; border-radius: 8px; font-size: 0.82rem; margin-bottom: 1rem; }
.alert-warn  { background:#fefce8; border-left: 3px solid #eab308; color:#713f12; }
.alert-info  { background:#eff6ff; border-left: 3px solid #3b82f6; color:#1e40af; }
.alert-danger{ background:#fef2f2; border-left: 3px solid #ef4444; color:#991b1b; }

.logo-wrap  { padding: 1.5rem 1.5rem 1rem; border-bottom: 1px solid #1e293b; margin-bottom: 1rem; }
.logo-title { font-size: 1.1rem; font-weight: 700; color: #f1f5f9 !important; letter-spacing: -0.01em; }
.logo-sub   { font-size: 0.7rem; color: #475569 !important; text-transform: uppercase; letter-spacing: 0.08em; }

.nav-section {
    font-size: 0.65rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: #334155 !important; padding: 0.5rem 1rem 0.25rem;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SUPABASE CLIENT
# ─────────────────────────────────────────────
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

sb = get_supabase()

# ─────────────────────────────────────────────
# DATA HELPERS
# ─────────────────────────────────────────────
def to_df(response) -> pd.DataFrame:
    data = response.data if hasattr(response, "data") else response
    return pd.DataFrame(data) if data else pd.DataFrame()

def get_items(item_type=None) -> pd.DataFrame:
    q = sb.table("item_codes").select("*").order("item_code")
    if item_type:
        q = q.eq("item_type", item_type)
    return to_df(q.execute())

def get_child_stock() -> pd.DataFrame:
    return to_df(sb.rpc("get_child_stock", {}).execute())

def get_parent_stock() -> pd.DataFrame:
    return to_df(sb.rpc("get_parent_stock", {}).execute())

def get_stock():
    return get_child_stock(), get_parent_stock()

def get_bom_full() -> pd.DataFrame:
    return to_df(sb.rpc("get_bom_full", {}).execute())

def get_bom_for_parent(parent_code: str) -> pd.DataFrame:
    return to_df(sb.table("bom").select("child_code, qty_per, item_codes(item_name, uom)").eq("parent_code", parent_code).execute())

def to_csv_download(df: pd.DataFrame, filename: str) -> str:
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    return (
        f'<a href="data:file/csv;base64,{b64}" download="{filename}" style="text-decoration:none">'
        f'<button style="background:#0f172a;color:white;border:none;padding:6px 14px;border-radius:6px;'
        f'font-size:0.78rem;cursor:pointer;font-family:Inter,sans-serif;">⬇ Download CSV</button></a>'
    )

def stock_badge(on_hand, safety) -> str:
    if on_hand <= 0:
        return '<span class="badge-low">OUT</span>'
    elif on_hand <= safety:
        return '<span class="badge-warn">LOW</span>'
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
    page1 = st.radio("", ["🏷 Item Codes", "🔗 BOM"], key="nav1", label_visibility="collapsed")

    st.markdown('<div class="nav-section">Transactions</div>', unsafe_allow_html=True)
    page2 = st.radio("", ["📥 Inbound", "🔧 Assembly", "📤 Outbound"], key="nav2", label_visibility="collapsed")

    st.markdown('<div class="nav-section">Intelligence</div>', unsafe_allow_html=True)
    page3 = st.radio("", ["📊 Stock", "🔮 Forecast", "📋 Ledger"], key="nav3", label_visibility="collapsed")

    st.markdown("---")
    st.markdown('<div class="nav-section">Global Filters</div>', unsafe_allow_html=True)
    filter_date_from = st.date_input("From Date", value=date.today().replace(day=1))
    filter_date_to   = st.date_input("To Date",   value=date.today())

    all_items_df = get_items()
    item_filter_options = ["All Items"] + (all_items_df["item_code"].tolist() if not all_items_df.empty else [])
    filter_item = st.selectbox("Item Filter", item_filter_options)

# Track which nav group was last used
for key, val in {"nav1": page1, "nav2": page2, "nav3": page3}.items():
    if val != st.session_state.get(f"prev_{key}"):
        st.session_state["last_page"] = val
        st.session_state[f"prev_{key}"] = val

if "last_page" not in st.session_state:
    st.session_state["last_page"] = "📊 Stock"

active = st.session_state["last_page"]

# ══════════════════════════════════════════════
# PAGE: ITEM CODES
# ══════════════════════════════════════════════
if active == "🏷 Item Codes":
    st.markdown('<div class="section-title">Item Codes</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Define all items — parent (finished goods) and child (components)</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["➕ Create Item", "📋 View All"])

    with tab1:
        with st.form("item_form"):
            c1, c2 = st.columns(2)
            with c1:
                item_code = st.text_input("Item Code *", placeholder="e.g. FG-001")
                item_name = st.text_input("Item Name *", placeholder="e.g. Gift Box Assembly")
                item_type = st.selectbox("Classification *", ["parent", "child"])
            with c2:
                uom = st.selectbox("Unit of Measure", ["PCS", "KG", "MTR", "BOX", "SET", "ROLL", "LTR"])
                safety_stock = st.number_input("Safety Stock Qty", min_value=0.0, step=1.0)
            if st.form_submit_button("Save Item Code", type="primary"):
                if not item_code or not item_name:
                    st.error("Item Code and Name are required.")
                else:
                    try:
                        sb.table("item_codes").upsert({
                            "item_code": item_code.strip().upper(),
                            "item_name": item_name.strip(),
                            "item_type": item_type,
                            "uom": uom,
                            "safety_stock": safety_stock,
                        }, on_conflict="item_code").execute()
                        st.success(f"✅ Item '{item_code.upper()}' saved.")
                    except Exception as e:
                        st.error(f"Error: {e}")

    with tab2:
        df = get_items()
        if not df.empty:
            if filter_item != "All Items":
                df = df[df["item_code"] == filter_item]
            c1, c2 = st.columns(2)
            with c1: st.markdown(f"**Parents (FG):** {len(df[df['item_type']=='parent'])}")
            with c2: st.markdown(f"**Children (Components):** {len(df[df['item_type']=='child'])}")
            st.dataframe(df[["item_code","item_name","item_type","uom","safety_stock","created_at"]], use_container_width=True, hide_index=True)
            st.markdown(to_csv_download(df, "item_codes.csv"), unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("**Edit Safety Stock**")
            e_code = st.selectbox("Select Item", df["item_code"].tolist(), key="edit_ss_sel")
            e_ss   = st.number_input("New Safety Stock", min_value=0.0, step=1.0, key="edit_ss_val")
            if st.button("Update Safety Stock"):
                sb.table("item_codes").update({"safety_stock": e_ss}).eq("item_code", e_code).execute()
                st.success("Updated.")
                st.rerun()
        else:
            st.markdown('<div class="alert-info alert-box">No items yet. Create one above.</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
# PAGE: BOM
# ══════════════════════════════════════════════
elif active == "🔗 BOM":
    st.markdown('<div class="section-title">Bill of Materials</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Define how many child components make one parent unit</div>', unsafe_allow_html=True)

    parents_df  = get_items("parent")
    children_df = get_items("child")

    if parents_df.empty or children_df.empty:
        st.markdown('<div class="alert-warn alert-box">⚠ Need at least one parent and one child item first.</div>', unsafe_allow_html=True)
    else:
        tab1, tab2 = st.tabs(["➕ Add BOM Line", "📋 View BOM"])

        with tab1:
            with st.form("bom_form"):
                c1, c2, c3 = st.columns(3)
                with c1: parent_sel = st.selectbox("Parent Item (FG)", parents_df["item_code"].tolist())
                with c2: child_sel  = st.selectbox("Child Component",  children_df["item_code"].tolist())
                with c3: qty_per   = st.number_input("Qty per Parent", min_value=0.01, step=0.5, value=1.0)
                if st.form_submit_button("Add BOM Line", type="primary"):
                    try:
                        sb.table("bom").upsert(
                            {"parent_code": parent_sel, "child_code": child_sel, "qty_per": qty_per},
                            on_conflict="parent_code,child_code"
                        ).execute()
                        st.success(f"✅ {parent_sel} → {child_sel} × {qty_per}")
                    except Exception as e:
                        st.error(f"Error: {e}")

        with tab2:
            bom_df = get_bom_full()
            if not bom_df.empty:
                if filter_item != "All Items":
                    bom_df = bom_df[(bom_df["parent_code"]==filter_item)|(bom_df["child_code"]==filter_item)]
                for parent in bom_df["parent_code"].unique():
                    sub = bom_df[bom_df["parent_code"]==parent]
                    st.markdown(f"**{parent} — {sub.iloc[0]['parent_name']}**")
                    st.dataframe(
                        sub[["child_code","child_name","qty_per","uom"]].rename(columns={
                            "child_code":"Component","child_name":"Name","qty_per":"Qty/Parent","uom":"UOM"
                        }),
                        use_container_width=True, hide_index=True
                    )
                st.markdown(to_csv_download(bom_df, "bom.csv"), unsafe_allow_html=True)
            else:
                st.markdown('<div class="alert-info alert-box">No BOM entries yet.</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
# PAGE: INBOUND
# ══════════════════════════════════════════════
elif active == "📥 Inbound":
    st.markdown('<div class="section-title">Inbound Stock</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Record child components received at the vendor facility</div>', unsafe_allow_html=True)

    children_df = get_items("child")
    if children_df.empty:
        st.markdown('<div class="alert-warn alert-box">⚠ No child items defined yet.</div>', unsafe_allow_html=True)
    else:
        tab1, tab2, tab3 = st.tabs(["➕ Manual Entry", "📤 Bulk CSV Upload", "📋 History"])

        with tab1:
            with st.form("inbound_form"):
                c1, c2 = st.columns(2)
                with c1:
                    txn_date = st.date_input("Date *", value=date.today())
                    item_sel = st.selectbox("Component Item *", children_df["item_code"].tolist())
                    qty      = st.number_input("Quantity *", min_value=0.01, step=1.0)
                with c2:
                    invoice_no = st.text_input("Invoice No.")
                    supplier   = st.text_input("Supplier Name")
                    remarks    = st.text_area("Remarks", height=68)
                inv_file = st.file_uploader("Attach Invoice (PDF/Image)", type=["pdf","png","jpg","jpeg"])
                if st.form_submit_button("Record Inbound", type="primary"):
                    payload = {
                        "txn_date":    str(txn_date),
                        "item_code":   item_sel,
                        "qty":         qty,
                        "invoice_no":  invoice_no,
                        "supplier":    supplier,
                        "remarks":     remarks,
                        "invoice_filename": inv_file.name if inv_file else None,
                    }
                    try:
                        sb.table("inbound").insert(payload).execute()
                        st.success(f"✅ Inbound recorded: {qty} × {item_sel}")
                    except Exception as e:
                        st.error(f"Error: {e}")

        with tab2:
            st.markdown("**CSV columns:** `date` (YYYY-MM-DD), `item_code`, `qty`, `invoice_no`, `supplier`")
            uploaded = st.file_uploader("Choose CSV", type=["csv"], key="inb_bulk")
            if uploaded:
                udf = pd.read_csv(uploaded)
                st.dataframe(udf.head(10), use_container_width=True)
                if st.button("Import All Rows"):
                    rows = [
                        {
                            "txn_date":   str(r.get("date","")),
                            "item_code":  str(r.get("item_code","")),
                            "qty":        float(r.get("qty", 0)),
                            "invoice_no": str(r.get("invoice_no","")),
                            "supplier":   str(r.get("supplier","")),
                        }
                        for _, r in udf.iterrows()
                    ]
                    try:
                        sb.table("inbound").insert(rows).execute()
                        st.success(f"✅ {len(rows)} rows imported.")
                    except Exception as e:
                        st.error(f"Error: {e}")

        with tab3:
            resp = (sb.table("inbound")
                      .select("txn_date, item_code, qty, invoice_no, supplier, invoice_filename, remarks, created_at")
                      .gte("txn_date", str(filter_date_from))
                      .lte("txn_date", str(filter_date_to))
                      .order("txn_date", desc=True)
                      .execute())
            df = to_df(resp)
            if not df.empty:
                if filter_item != "All Items":
                    df = df[df["item_code"]==filter_item]
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.markdown(to_csv_download(df, "inbound_history.csv"), unsafe_allow_html=True)
            else:
                st.markdown('<div class="alert-info alert-box">No inbound records in selected date range.</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
# PAGE: ASSEMBLY
# ══════════════════════════════════════════════
elif active == "🔧 Assembly":
    st.markdown('<div class="section-title">Assembly Log</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Record FG assembled at the vendor — auto-deducts child components</div>', unsafe_allow_html=True)

    parents_df = get_items("parent")
    if parents_df.empty:
        st.markdown('<div class="alert-warn alert-box">⚠ No parent items defined.</div>', unsafe_allow_html=True)
    else:
        tab1, tab2 = st.tabs(["➕ Record Assembly", "📋 History"])

        with tab1:
            c1, c2 = st.columns([2,1])
            with c1: parent_sel      = st.selectbox("Parent Item (FG)", parents_df["item_code"].tolist())
            with c2: qty_to_assemble = st.number_input("Qty to Assemble", min_value=1.0, step=1.0, value=1.0)

            # BOM consumption preview
            bom_resp = (sb.table("bom")
                          .select("child_code, qty_per, item_codes!bom_child_code_fkey(item_name, uom)")
                          .eq("parent_code", parent_sel)
                          .execute())
            bom_rows = bom_resp.data or []

            child_stock = get_child_stock()
            can_assemble = True

            if bom_rows:
                st.markdown("**Component Consumption Preview**")
                preview = []
                for r in bom_rows:
                    ic = r.get("item_codes") or {}
                    needed = r["qty_per"] * qty_to_assemble
                    avail  = 0
                    if not child_stock.empty:
                        m = child_stock[child_stock["item_code"]==r["child_code"]]
                        avail = float(m["stock_on_hand"].iloc[0]) if not m.empty else 0
                    status = "✅" if avail >= needed else "❌ SHORT"
                    if avail < needed:
                        can_assemble = False
                    preview.append({
                        "Component": r["child_code"],
                        "Name":      ic.get("item_name",""),
                        "Qty/Unit":  r["qty_per"],
                        "Total Needed": needed,
                        "In Stock":  avail,
                        "Status":    status,
                    })
                st.dataframe(pd.DataFrame(preview), use_container_width=True, hide_index=True)
                if not can_assemble:
                    st.markdown('<div class="alert-danger alert-box">❌ Insufficient stock for one or more components.</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="alert-warn alert-box">⚠ No BOM defined for this item.</div>', unsafe_allow_html=True)

            with st.form("asm_form"):
                txn_date = st.date_input("Assembly Date", value=date.today())
                remarks  = st.text_area("Remarks", height=60)
                if st.form_submit_button("Record Assembly", type="primary"):
                    if not bom_rows:
                        st.error("Cannot record — no BOM defined.")
                    else:
                        try:
                            sb.table("assembly").insert({
                                "txn_date":     str(txn_date),
                                "parent_code":  parent_sel,
                                "qty_assembled": qty_to_assemble,
                                "remarks":      remarks,
                            }).execute()
                            st.success(f"✅ Assembly recorded: {qty_to_assemble} × {parent_sel}")
                        except Exception as e:
                            st.error(f"Error: {e}")

        with tab2:
            resp = sb.rpc("get_assembly_history", {
                "date_from": str(filter_date_from),
                "date_to":   str(filter_date_to),
            }).execute()
            df = to_df(resp)
            if not df.empty:
                if filter_item != "All Items":
                    df = df[df["parent_code"]==filter_item]
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.markdown(to_csv_download(df, "assembly_history.csv"), unsafe_allow_html=True)
            else:
                st.markdown('<div class="alert-info alert-box">No assembly records in selected date range.</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
# PAGE: OUTBOUND
# ══════════════════════════════════════════════
elif active == "📤 Outbound":
    st.markdown('<div class="section-title">Outbound Dispatch</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Record finished goods dispatched to customers from the vendor</div>', unsafe_allow_html=True)

    parents_df = get_items("parent")
    if parents_df.empty:
        st.markdown('<div class="alert-warn alert-box">⚠ No parent items defined.</div>', unsafe_allow_html=True)
    else:
        tab1, tab2 = st.tabs(["➕ Record Dispatch", "📋 History"])

        with tab1:
            with st.form("outbound_form"):
                c1, c2 = st.columns(2)
                with c1:
                    txn_date   = st.date_input("Dispatch Date *", value=date.today())
                    parent_sel = st.selectbox("FG Item *", parents_df["item_code"].tolist())
                    qty        = st.number_input("Qty Dispatched *", min_value=0.01, step=1.0)
                with c2:
                    customer    = st.text_input("Customer Name")
                    gate_pass_no= st.text_input("Gate Pass No.")
                    remarks     = st.text_area("Remarks", height=68)
                gp_file = st.file_uploader("Attach Gate Pass (PDF/Image)", type=["pdf","png","jpg","jpeg"])
                if st.form_submit_button("Record Outbound", type="primary"):
                    # Stock check
                    _, parent_stock = get_stock()
                    avail = 0
                    if not parent_stock.empty:
                        m = parent_stock[parent_stock["item_code"]==parent_sel]
                        avail = float(m["stock_on_hand"].iloc[0]) if not m.empty else 0
                    if qty > avail:
                        st.error(f"❌ Insufficient FG stock. Available: {avail:,.0f}")
                    else:
                        try:
                            sb.table("outbound").insert({
                                "txn_date":         str(txn_date),
                                "parent_code":      parent_sel,
                                "qty":              qty,
                                "customer":         customer,
                                "gate_pass_no":     gate_pass_no,
                                "gate_pass_filename": gp_file.name if gp_file else None,
                                "remarks":          remarks,
                            }).execute()
                            st.success(f"✅ Outbound recorded: {qty} × {parent_sel} → {customer}")
                        except Exception as e:
                            st.error(f"Error: {e}")

        with tab2:
            resp = sb.rpc("get_outbound_history", {
                "date_from": str(filter_date_from),
                "date_to":   str(filter_date_to),
            }).execute()
            df = to_df(resp)
            if not df.empty:
                if filter_item != "All Items":
                    df = df[df["parent_code"]==filter_item]
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.markdown(to_csv_download(df, "outbound_history.csv"), unsafe_allow_html=True)
            else:
                st.markdown('<div class="alert-info alert-box">No outbound records in selected date range.</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
# PAGE: STOCK
# ══════════════════════════════════════════════
elif active == "📊 Stock":
    st.markdown('<div class="section-title">Live Stock Position</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Real-time inventory across all items at the vendor facility</div>', unsafe_allow_html=True)

    child_stock, parent_stock = get_stock()

    total_child = len(child_stock) if not child_stock.empty else 0
    low_child   = len(child_stock[child_stock["stock_on_hand"] <= child_stock["safety_stock"]]) if not child_stock.empty else 0
    out_child   = len(child_stock[child_stock["stock_on_hand"] <= 0]) if not child_stock.empty else 0
    total_fg    = float(parent_stock["stock_on_hand"].sum()) if not parent_stock.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Component SKUs</div><div class="kpi-value">{total_child}</div><div class="kpi-sub">tracked items</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Below Safety Stock</div><div class="kpi-value" style="color:#d97706">{low_child}</div><div class="kpi-sub">need reorder</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Out of Stock</div><div class="kpi-value" style="color:#dc2626">{out_child}</div><div class="kpi-sub">zero inventory</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="kpi-card"><div class="kpi-label">FG Ready to Ship</div><div class="kpi-value" style="color:#16a34a">{total_fg:,.0f}</div><div class="kpi-sub">assembled units</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("**Child Components (Raw / WIP)**")
        if not child_stock.empty:
            df = child_stock.copy()
            if filter_item != "All Items":
                df = df[df["item_code"]==filter_item]
            df["Status"] = df.apply(lambda r: stock_badge(r["stock_on_hand"], r["safety_stock"]), axis=1)
            cols = ["item_code","item_name","uom","total_inbound","total_consumed","stock_on_hand","safety_stock","Status"]
            st.markdown(df[cols].to_html(index=False, escape=False), unsafe_allow_html=True)
            st.markdown(to_csv_download(df[cols], "child_stock.csv"), unsafe_allow_html=True)
        else:
            st.markdown('<div class="alert-info alert-box">No component data yet.</div>', unsafe_allow_html=True)

    with col_r:
        st.markdown("**Parent Items (Finished Goods)**")
        if not parent_stock.empty:
            df = parent_stock.copy()
            if filter_item != "All Items":
                df = df[df["item_code"]==filter_item]
            df["Status"] = df.apply(lambda r: stock_badge(r["stock_on_hand"], r["safety_stock"]), axis=1)
            cols = ["item_code","item_name","uom","total_assembled","total_dispatched","stock_on_hand","safety_stock","Status"]
            st.markdown(df[cols].to_html(index=False, escape=False), unsafe_allow_html=True)
            st.markdown(to_csv_download(df[cols], "parent_stock.csv"), unsafe_allow_html=True)
        else:
            st.markdown('<div class="alert-info alert-box">No FG data yet.</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
# PAGE: FORECAST
# ══════════════════════════════════════════════
elif active == "🔮 Forecast":
    st.markdown('<div class="section-title">Production Forecast</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Set target FG quantities — see component gaps and max producible units today</div>', unsafe_allow_html=True)

    parents_df = get_items("parent")
    if parents_df.empty:
        st.markdown('<div class="alert-warn alert-box">⚠ No parent items available.</div>', unsafe_allow_html=True)
    else:
        parent_list = parents_df["item_code"].tolist()
        num_items = st.number_input("How many FG items to plan?", min_value=1, max_value=10, value=1, step=1)

        targets = {}
        cols = st.columns(min(int(num_items), 3))
        for i in range(int(num_items)):
            with cols[i % 3]:
                p = st.selectbox(f"FG Item {i+1}", parent_list, key=f"fc_p_{i}")
                q = st.number_input("Target Qty", min_value=0.0, step=1.0, value=100.0, key=f"fc_q_{i}")
                targets[p] = targets.get(p, 0) + q

        if st.button("Run Forecast", type="primary"):
            child_stock, _ = get_stock()
            bom_df = get_bom_full()

            req_map = {}
            for parent, target_qty in targets.items():
                sub = bom_df[bom_df["parent_code"]==parent] if not bom_df.empty else pd.DataFrame()
                for _, r in sub.iterrows():
                    cc = r["child_code"]
                    req_map[cc] = req_map.get(cc, 0) + r["qty_per"] * target_qty

            st.markdown("---")
            st.markdown("### Forecast Results")

            if not req_map:
                st.markdown('<div class="alert-warn alert-box">⚠ No BOM defined for selected items.</div>', unsafe_allow_html=True)
            else:
                results, max_producible, limiting = [], float("inf"), None
                for cc, total_req in req_map.items():
                    avail = safety = 0
                    if not child_stock.empty:
                        m = child_stock[child_stock["item_code"]==cc]
                        if not m.empty:
                            avail  = float(m["stock_on_hand"].iloc[0])
                            safety = float(m["safety_stock"].iloc[0])
                    shortfall = max(0, total_req - avail)
                    if total_req > 0:
                        ratio = avail / total_req
                        if ratio < max_producible:
                            max_producible, limiting = ratio, cc
                    results.append({
                        "Component": cc, "Required": total_req,
                        "In Stock": avail, "Safety Stock": safety,
                        "Shortfall": shortfall, "To Order": shortfall,
                        "Status": "✅ OK" if avail >= total_req else "❌ SHORT"
                    })

                st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
                st.markdown(to_csv_download(pd.DataFrame(results), "forecast_plan.csv"), unsafe_allow_html=True)

                total_targets = sum(targets.values())
                producible = int(min(max_producible, 1.0) * total_targets) if max_producible < float("inf") else int(total_targets)
                producible = max(0, producible)
                gap = max(0, int(total_targets) - producible)

                st.markdown("---")
                c1, c2, c3 = st.columns(3)
                color = "#16a34a" if producible >= total_targets else "#d97706"
                with c1: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Target Production</div><div class="kpi-value">{int(total_targets):,}</div><div class="kpi-sub">units planned</div></div>', unsafe_allow_html=True)
                with c2: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Can Produce Now</div><div class="kpi-value" style="color:{color}">{producible:,}</div><div class="kpi-sub">with current stock</div></div>', unsafe_allow_html=True)
                with c3: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Production Gap</div><div class="kpi-value" style="color:#dc2626">{gap:,}</div><div class="kpi-sub">units blocked</div></div>', unsafe_allow_html=True)

                if limiting and producible < total_targets:
                    st.markdown(f'<div class="alert-danger alert-box">🔴 Bottleneck: <b>{limiting}</b> — order this first to unblock production.</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
# PAGE: LEDGER
# ══════════════════════════════════════════════
elif active == "📋 Ledger":
    st.markdown('<div class="section-title">Transaction Ledger</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Complete movement log — tally against the vendor</div>', unsafe_allow_html=True)

    resp = sb.rpc("get_ledger", {
        "date_from": str(filter_date_from),
        "date_to":   str(filter_date_to),
    }).execute()
    df = to_df(resp)

    if not df.empty:
        if filter_item != "All Items":
            df = df[df["item_code"]==filter_item]

        total_inb = df[df["txn_type"]=="Inbound"]["qty_in"].sum()
        total_asm = df[df["txn_type"]=="Assembly"]["qty_in"].sum()
        total_out = df[df["txn_type"]=="Outbound"]["qty_out"].sum()

        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Total Transactions</div><div class="kpi-value">{len(df)}</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Components In</div><div class="kpi-value">{total_inb:,.0f}</div></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="kpi-card"><div class="kpi-label">FG Assembled</div><div class="kpi-value">{total_asm:,.0f}</div></div>', unsafe_allow_html=True)
        with c4: st.markdown(f'<div class="kpi-card"><div class="kpi-label">FG Dispatched</div><div class="kpi-value">{total_out:,.0f}</div></div>', unsafe_allow_html=True)

        st.markdown("---")
        txn_filter = st.multiselect("Filter by Type", ["Inbound","Assembly","Outbound"], default=["Inbound","Assembly","Outbound"])
        df_f = df[df["txn_type"].isin(txn_filter)]
        st.dataframe(df_f, use_container_width=True, hide_index=True)
        st.markdown(to_csv_download(df_f, "ledger.csv"), unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**Running Stock Tally (by Item)**")
        tally = []
        for item in df["item_code"].unique():
            sub = df[df["item_code"]==item]
            tally.append({"Item Code": item, "Total In": sub["qty_in"].sum(), "Total Out": sub["qty_out"].sum(), "Net": sub["qty_in"].sum()-sub["qty_out"].sum()})
        st.dataframe(pd.DataFrame(tally).sort_values("Item Code"), use_container_width=True, hide_index=True)
    else:
        st.markdown('<div class="alert-info alert-box">No transactions in selected date range.</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<div style="text-align:center;font-size:0.72rem;color:#94a3b8;padding:0.5rem 0;">'
    'VendorLens WIP Manager · Streamlit + Supabase · Operations Control Tower</div>',
    unsafe_allow_html=True
)
