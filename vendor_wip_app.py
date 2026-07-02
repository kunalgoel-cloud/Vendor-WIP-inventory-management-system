import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import date
import base64, uuid, io

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="VendorLens · WIP Manager",
    page_icon="📦",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family:'Inter',sans-serif; }

section[data-testid="stSidebar"] { background:#0f172a; border-right:1px solid #1e293b; }
section[data-testid="stSidebar"] * { color:#94a3b8 !important; }
section[data-testid="stSidebar"] .stRadio label { font-size:0.9rem; font-weight:500; padding:0.25rem 0; }

.main .block-container { padding-top:1rem; padding-bottom:2rem; max-width:760px; }

.kpi-card { background:white; border:1px solid #e2e8f0; border-radius:10px; padding:1rem 1.2rem; margin-bottom:0.5rem; }
.kpi-label { font-size:0.68rem; font-weight:600; letter-spacing:.08em; text-transform:uppercase; color:#64748b; margin-bottom:.2rem; }
.kpi-value { font-size:1.6rem; font-weight:700; color:#0f172a; font-family:'JetBrains Mono',monospace; line-height:1.1; }
.kpi-sub   { font-size:.72rem; color:#94a3b8; margin-top:.15rem; }

.section-title { font-size:1.15rem; font-weight:700; color:#0f172a; margin-bottom:.15rem; }
.section-sub   { font-size:.8rem; color:#64748b; margin-bottom:1.2rem; }

.site-banner {
    background: linear-gradient(135deg,#0f172a,#1e3a5f);
    border-radius:10px; padding:.7rem 1rem;
    display:flex; align-items:center; gap:.6rem;
    margin-bottom:1rem;
}
.site-banner-text { font-size:.78rem; color:#94a3b8; }
.site-banner-name { font-size:1rem; font-weight:700; color:#f1f5f9; }

.site-card {
    background:white; border:2px solid #e2e8f0; border-radius:12px;
    padding:1.2rem 1.4rem; margin-bottom:.6rem; cursor:pointer;
    transition:border-color .15s;
}
.site-card:hover { border-color:#3b82f6; }
.site-card-code { font-size:.7rem; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:.06em; }
.site-card-name { font-size:1.05rem; font-weight:600; color:#0f172a; }
.site-card-loc  { font-size:.78rem; color:#94a3b8; margin-top:.1rem; }

.alert-box    { padding:.7rem .9rem; border-radius:8px; font-size:.8rem; margin-bottom:.8rem; }
.alert-warn   { background:#fefce8; border-left:3px solid #eab308; color:#713f12; }
.alert-info   { background:#eff6ff; border-left:3px solid #3b82f6; color:#1e40af; }
.alert-danger { background:#fef2f2; border-left:3px solid #ef4444; color:#991b1b; }
.alert-ok     { background:#f0fdf4; border-left:3px solid #22c55e; color:#166534; }

.logo-wrap  { padding:1.2rem 1rem .8rem; border-bottom:1px solid #1e293b; margin-bottom:.8rem; }
.logo-title { font-size:1rem; font-weight:700; color:#f1f5f9 !important; }
.logo-sub   { font-size:.65rem; color:#475569 !important; text-transform:uppercase; letter-spacing:.08em; }
.nav-section { font-size:.62rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase; color:#334155 !important; padding:.5rem .8rem .2rem; }

.stButton>button, .stFormSubmitButton>button { width:100%; }
.stDataFrame { border-radius:8px; overflow-x:auto; }
.cam-label { font-size:.78rem; font-weight:600; color:#374151; margin-bottom:.3rem; margin-top:.8rem; display:block; }

.bom-level-0 { border-left:3px solid #3b82f6; padding-left:.6rem; margin-bottom:.4rem; }
.bom-level-1 { border-left:3px solid #8b5cf6; padding-left:.6rem; margin-bottom:.4rem; margin-left:1.2rem; }
.bom-level-2 { border-left:3px solid #ec4899; padding-left:.6rem; margin-bottom:.4rem; margin-left:2.4rem; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SUPABASE
# ─────────────────────────────────────────────
@st.cache_resource
def get_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
sb = get_supabase()

BUCKET = "vendorlens-docs"

def ensure_bucket():
    try:
        names = [b.name for b in sb.storage.list_buckets()]
        if BUCKET not in names:
            sb.storage.create_bucket(BUCKET, options={"public": True})
    except Exception: pass

def upload_photo(file_bytes, filename, folder):
    ensure_bucket()
    ext  = filename.rsplit(".",1)[-1].lower() if "." in filename else "jpg"
    path = f"{folder}/{uuid.uuid4().hex}.{ext}"
    mime = {"pdf":"application/pdf","png":"image/png","jpg":"image/jpeg",
            "jpeg":"image/jpeg","heic":"image/heic","webp":"image/webp"}.get(ext,"image/jpeg")
    try:
        sb.storage.from_(BUCKET).upload(path, file_bytes, file_options={"content-type":mime,"upsert":"true"})
        return sb.storage.from_(BUCKET).get_public_url(path)
    except Exception as e:
        st.warning(f"Photo upload failed: {e}")
        return None

def photo_widget(label, key, folder):
    st.markdown(f'<span class="cam-label">📎 {label}</span>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        uploaded = st.file_uploader("Upload", type=["pdf","png","jpg","jpeg","heic","webp"],
            key=f"up_{key}", label_visibility="collapsed")
    with c2:
        camera = st.camera_input("Camera", key=f"cam_{key}", label_visibility="collapsed")
    src = uploaded or camera
    if not src: return None, None
    fb = src.getvalue()
    fn = getattr(src,"name",f"photo_{key}.jpg")
    if fn.lower().split(".")[-1] in ("png","jpg","jpeg","webp"):
        st.image(fb, caption="Preview", use_container_width=True)
    url = upload_photo(fb, fn, folder)
    return url, fn

def to_df(resp) -> pd.DataFrame:
    data = resp.data if hasattr(resp,"data") else resp
    return pd.DataFrame(data) if data else pd.DataFrame()

def to_csv_dl(df, filename):
    b64 = base64.b64encode(df.to_csv(index=False).encode()).decode()
    return (f'<a href="data:file/csv;base64,{b64}" download="{filename}" style="text-decoration:none">'
            f'<button style="background:#0f172a;color:white;border:none;padding:8px 16px;border-radius:6px;'
            f'font-size:.78rem;cursor:pointer;font-family:Inter,sans-serif;width:100%;">⬇ Download CSV</button></a>')

def delete_record(table, record_id, snapshot, reason, site_id):
    try:
        sb.table(table).delete().eq("id", record_id).execute()
        sb.table("deletion_log").insert({
            "table_name": table, "record_id": record_id,
            "txn_date": str(snapshot.get("txn_date","")),
            "item_code": snapshot.get("item_code") or snapshot.get("parent_code") or "",
            "qty": float(snapshot.get("qty") or snapshot.get("qty_assembled") or 0),
            "snapshot": snapshot, "reason": reason, "site_id": site_id,
        }).execute()
        return True
    except Exception as e:
        st.error(f"Delete failed: {e}")
        return False

# ─────────────────────────────────────────────
# SITE HELPERS
# ─────────────────────────────────────────────
def get_sites():
    return to_df(sb.table("sites").select("*").eq("active", True).order("site_name").execute())

def get_site_id(): return st.session_state.get("site_id")
def get_site_name(): return st.session_state.get("site_name","")
def get_site_code(): return st.session_state.get("site_code","")

# ─────────────────────────────────────────────
# ITEM / STOCK HELPERS  (all site-scoped)
# ─────────────────────────────────────────────
def get_items(role=None):
    """role: 'parent'|'child'|'intermediate'|None=all"""
    sid = get_site_id()
    q = sb.table("item_codes").select("*").eq("site_id", sid).order("item_code")
    if role: q = q.eq("item_type", role)
    return to_df(q.execute())

def get_parents():
    """Items that appear as parent in BOM for this site."""
    sid = get_site_id()
    bom_df = to_df(sb.table("bom").select("parent_code").eq("site_id", sid).execute())
    if bom_df.empty: return pd.DataFrame()
    codes = bom_df["parent_code"].unique().tolist()
    df = to_df(sb.table("item_codes").select("*").eq("site_id", sid).in_("item_code", codes).order("item_code").execute())
    return df

def get_children():
    """Items that appear as child in BOM for this site."""
    sid = get_site_id()
    bom_df = to_df(sb.table("bom").select("child_code").eq("site_id", sid).execute())
    if bom_df.empty: return pd.DataFrame()
    codes = bom_df["child_code"].unique().tolist()
    df = to_df(sb.table("item_codes").select("*").eq("site_id", sid).in_("item_code", codes).order("item_code").execute())
    return df

def get_child_stock():
    return to_df(sb.rpc("get_child_stock", {"p_site_id": get_site_id()}).execute())

def get_parent_stock():
    return to_df(sb.rpc("get_parent_stock", {"p_site_id": get_site_id()}).execute())

def get_stock(): return get_child_stock(), get_parent_stock()

def get_bom_full():
    return to_df(sb.rpc("get_bom_full", {"p_site_id": get_site_id()}).execute())

# ─────────────────────────────────────────────────────────────────
# SITE SELECTION SCREEN — shown when no site selected
# ─────────────────────────────────────────────────────────────────
if "site_id" not in st.session_state:

    st.markdown("## 📦 VendorLens")
    st.markdown("#### Select a Project Site to continue")
    st.markdown("All stock, BOMs, and transactions are scoped to a single site.")
    st.markdown("---")

    sites_df = get_sites()

    col_new, col_space = st.columns([1,2])
    with col_new:
        if st.button("➕ Create New Site", use_container_width=True):
            st.session_state["show_new_site"] = True

    if st.session_state.get("show_new_site"):
        with st.form("new_site_form"):
            st.markdown("**New Project Site**")
            sc = st.text_input("Site Code *", placeholder="e.g. SITE-MUM-01")
            sn = st.text_input("Site Name *", placeholder="e.g. Mumbai Vendor – Andheri")
            sl = st.text_input("Location",    placeholder="e.g. Andheri East, Mumbai")
            if st.form_submit_button("Create Site", type="primary"):
                if not sc or not sn:
                    st.error("Site Code and Name are required.")
                else:
                    try:
                        r = sb.table("sites").insert({"site_code":sc.strip().upper(),"site_name":sn.strip(),"location":sl.strip()}).execute()
                        st.success(f"✅ Site '{sn}' created. Select it below.")
                        st.session_state.pop("show_new_site", None)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

    st.markdown("")
    sites_df = get_sites()
    if sites_df.empty:
        st.markdown('<div class="alert-info alert-box">No sites yet — create one above to get started.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f"**{len(sites_df)} site(s) available:**")
        for _, site in sites_df.iterrows():
            loc_text = f" · {site['location']}" if site.get("location") else ""
            if st.button(f"🏭  {site['site_name']}   ({site['site_code']}){loc_text}",
                         key=f"sel_site_{site['id']}", use_container_width=True):
                st.session_state["site_id"]   = int(site["id"])
                st.session_state["site_name"] = site["site_name"]
                st.session_state["site_code"] = site["site_code"]
                st.rerun()

    st.stop()   # Don't render anything else until a site is chosen

# ─────────────────────────────────────────────
# SIDEBAR  — only populated after site selected
# All DB calls are inside the site_id guard so
# nothing fires on the site-selection screen.
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="logo-wrap">
        <div class="logo-title">📦 VendorLens</div>
        <div class="logo-sub">WIP Stock Manager</div>
    </div>
    """, unsafe_allow_html=True)

    if "site_id" not in st.session_state:
        # Minimal sidebar on site-selection screen — no DB calls
        st.markdown('<div style="font-size:.78rem;color:#475569;padding:.6rem .8rem">Select a site to begin.</div>', unsafe_allow_html=True)
        # Dummy values so the rest of the script doesn't NameError
        page1 = "🏷 Item Codes"
        page2 = "📥 Inbound"
        page3 = "📊 Stock"
        filter_date_from = date.today().replace(day=1)
        filter_date_to   = date.today()
        filter_item      = "All Items"
    else:
        # ── Site switcher ──────────────────────────────
        st.markdown('<div style="font-size:.68rem;color:#475569;padding:.2rem .8rem 0">ACTIVE SITE</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:.85rem;font-weight:700;color:#e2e8f0;padding:.1rem .8rem .4rem">🏭 {get_site_name()}</div>', unsafe_allow_html=True)
        if st.button("⇄ Switch Site", key="switch_site", use_container_width=True):
            for k in ["site_id","site_name","site_code","last_page"]:
                st.session_state.pop(k, None)
            st.rerun()

        st.markdown("---")
        st.markdown('<div class="nav-section">Master Data</div>', unsafe_allow_html=True)
        page1 = st.radio("", ["🏷 Item Codes","🔗 BOM","🏭 Sites"], key="nav1", label_visibility="collapsed")

        st.markdown('<div class="nav-section">Transactions</div>', unsafe_allow_html=True)
        page2 = st.radio("", ["📥 Inbound","🔧 Assembly","📤 Outbound","⚖️ Adjustments"], key="nav2", label_visibility="collapsed")

        st.markdown('<div class="nav-section">Intelligence</div>', unsafe_allow_html=True)
        page3 = st.radio("", ["📊 Stock","🔮 Forecast","📋 Ledger","🗑 Audit Log"], key="nav3", label_visibility="collapsed")

        st.markdown("---")
        st.markdown('<div class="nav-section">Global Filters</div>', unsafe_allow_html=True)
        filter_date_from = st.date_input("From", value=date.today().replace(day=1))
        filter_date_to   = st.date_input("To",   value=date.today())

        _items_df   = get_items()   # DB call — safe, site_id is set
        item_opts   = ["All Items"] + (_items_df["item_code"].tolist() if not _items_df.empty else [])
        filter_item = st.selectbox("Item Filter", item_opts)

        # ── Live stock pulse ───────────────────────────
        st.markdown("---")
        st.markdown('<div class="nav-section">Stock Status</div>', unsafe_allow_html=True)
        _cs = get_child_stock()
        _ps = get_parent_stock()
        if not _cs.empty or not _ps.empty:
            _all = pd.concat([
                _cs[["item_code","stock_on_hand","safety_stock"]] if not _cs.empty else pd.DataFrame(),
                _ps[["item_code","stock_on_hand","safety_stock"]] if not _ps.empty else pd.DataFrame()
            ], ignore_index=True)
            _ok  = int((_all["stock_on_hand"] > _all["safety_stock"]).sum())
            _low = int(((_all["stock_on_hand"] > 0) & (_all["stock_on_hand"] <= _all["safety_stock"])).sum())
            _out = int((_all["stock_on_hand"] <= 0).sum())
            st.markdown(f"""
            <div style="padding:.4rem .2rem;font-size:.8rem;line-height:2.2">
                <span style="color:#22c55e">●</span> <b style="color:#f1f5f9">{_ok}</b> <span style="color:#64748b">OK</span><br>
                <span style="color:#f59e0b">●</span> <b style="color:#f1f5f9">{_low}</b> <span style="color:#64748b">LOW</span><br>
                <span style="color:#ef4444">●</span> <b style="color:#f1f5f9">{_out}</b> <span style="color:#64748b">OUT</span>
            </div>""", unsafe_allow_html=True)
            out_items = _cs[_cs["stock_on_hand"] <= 0]["item_code"].tolist() if not _cs.empty else []
            low_items = _cs[(_cs["stock_on_hand"] > 0) & (_cs["stock_on_hand"] <= _cs["safety_stock"])]["item_code"].tolist() if not _cs.empty else []
            if out_items: st.markdown(f'<div style="font-size:.68rem;color:#f87171">🔴 {", ".join(out_items[:4])}</div>', unsafe_allow_html=True)
            if low_items: st.markdown(f'<div style="font-size:.68rem;color:#fbbf24">🟡 {", ".join(low_items[:4])}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size:.74rem;color:#475569;padding:.4rem .2rem">No stock data yet.</div>', unsafe_allow_html=True)

# Track active page
for key, val in {"nav1":page1,"nav2":page2,"nav3":page3}.items():
    if val != st.session_state.get(f"prev_{key}"):
        st.session_state["last_page"] = val
        st.session_state[f"prev_{key}"] = val
if "last_page" not in st.session_state:
    st.session_state["last_page"] = "📊 Stock"
active = st.session_state["last_page"]

# Site banner shown on every page
sid  = get_site_id()
st.markdown(f"""
<div class="site-banner">
    <span style="font-size:1.3rem">🏭</span>
    <div>
        <div class="site-banner-text">Active Site</div>
        <div class="site-banner-name">{get_site_name()} &nbsp;<span style="font-size:.72rem;color:#475569;font-weight:400">({get_site_code()})</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# PAGE: SITES MANAGEMENT
# ══════════════════════════════════════════════
if active == "🏭 Sites":
    st.markdown('<div class="section-title">Project Sites</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Manage vendor locations — each site has independent stock and BOMs</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["➕ New Site", "📋 All Sites"])

    with tab1:
        with st.form("site_form"):
            sc = st.text_input("Site Code *", placeholder="e.g. SITE-DEL-02")
            sn = st.text_input("Site Name *", placeholder="e.g. Delhi Vendor – Okhla")
            sl = st.text_input("Location",    placeholder="e.g. Okhla Phase II, Delhi")
            if st.form_submit_button("Create Site", type="primary"):
                if not sc or not sn:
                    st.error("Code and Name required.")
                else:
                    try:
                        sb.table("sites").insert({"site_code":sc.strip().upper(),"site_name":sn.strip(),"location":sl}).execute()
                        st.success(f"✅ Site '{sn}' created.")
                    except Exception as e:
                        st.error(f"Error: {e}")

    with tab2:
        df = to_df(sb.table("sites").select("*").order("site_name").execute())
        if not df.empty:
            st.dataframe(df[["site_code","site_name","location","active","created_at"]],
                use_container_width=True, hide_index=True)
            st.markdown("---")
            st.markdown("**Deactivate a site**")
            active_sites = df[df["active"]==True]["site_code"].tolist()
            if active_sites:
                sel = st.selectbox("Site to deactivate", active_sites)
                if st.button("Deactivate", key="deact_btn"):
                    sb.table("sites").update({"active":False}).eq("site_code",sel).execute()
                    st.success(f"Site '{sel}' deactivated.")
                    st.rerun()
        else:
            st.markdown('<div class="alert-info alert-box">No sites yet.</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
# PAGE: ITEM CODES
# ══════════════════════════════════════════════
elif active == "🏷 Item Codes":
    st.markdown('<div class="section-title">Item Codes</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">parent = FG · child = raw component · intermediate = sub-assembly (both parent & child in BOM)</div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["➕ Create", "📋 View All", "✏️ Edit Item"])

    with tab1:
        with st.form("item_form"):
            item_code    = st.text_input("Item Code *", placeholder="e.g. FG-001")
            item_name    = st.text_input("Item Name *", placeholder="e.g. Gift Box Assembly")
            item_type    = st.selectbox("Classification *", ["parent","child","intermediate"],
                help="intermediate = sub-assembly used as child in one BOM and parent in another")
            uom          = st.selectbox("UOM", ["PCS","KG","MTR","BOX","SET","ROLL","LTR"])
            safety_stock = st.number_input("Safety Stock", min_value=0.0, step=1.0)
            if st.form_submit_button("Save Item Code", type="primary"):
                if not item_code or not item_name:
                    st.error("Code and Name required.")
                else:
                    try:
                        sb.table("item_codes").upsert({
                            "item_code":item_code.strip().upper(), "item_name":item_name.strip(),
                            "item_type":item_type, "uom":uom, "safety_stock":safety_stock,
                            "site_id":sid,
                        }, on_conflict="item_code").execute()
                        st.success(f"✅ '{item_code.upper()}' saved.")
                    except Exception as e:
                        st.error(f"Error: {e}")

    with tab2:
        df = get_items()
        if not df.empty:
            if filter_item != "All Items": df = df[df["item_code"]==filter_item]
            c1,c2,c3 = st.columns(3)
            with c1: st.markdown(f"**Parents:** {len(df[df['item_type']=='parent'])}")
            with c2: st.markdown(f"**Children:** {len(df[df['item_type']=='child'])}")
            with c3: st.markdown(f"**Intermediate:** {len(df[df['item_type']=='intermediate'])}")
            st.dataframe(df[["item_code","item_name","item_type","uom","safety_stock"]], use_container_width=True, hide_index=True)
            st.markdown(to_csv_dl(df,"item_codes.csv"), unsafe_allow_html=True)
        else:
            st.markdown('<div class="alert-info alert-box">No items for this site yet.</div>', unsafe_allow_html=True)

    with tab3:
        df = get_items()
        if df.empty:
            st.markdown('<div class="alert-info alert-box">No items for this site yet.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="alert-info alert-box">ℹ Item Code cannot be changed (it is the unique key used across all transactions). Edit name, type, UOM, or safety stock below.</div>', unsafe_allow_html=True)

            # Select item to edit — pre-populate all fields
            all_codes = df["item_code"].tolist()
            sel_code  = st.selectbox("Select Item to Edit", all_codes,
                format_func=lambda x: f"{x} — {df.set_index('item_code').loc[x,'item_name']}")

            sel_row = df[df["item_code"] == sel_code].iloc[0]

            UOM_OPTIONS  = ["PCS","KG","MTR","BOX","SET","ROLL","LTR"]
            TYPE_OPTIONS = ["parent","child","intermediate"]

            # Pre-select current values
            cur_type = sel_row["item_type"] if sel_row["item_type"] in TYPE_OPTIONS else "child"
            cur_uom  = sel_row["uom"] if sel_row["uom"] in UOM_OPTIONS else "PCS"

            with st.form("edit_item_form"):
                st.markdown(f"**Editing:** `{sel_code}`")
                new_name = st.text_input("Item Name *", value=sel_row["item_name"])
                new_type = st.selectbox("Classification *", TYPE_OPTIONS,
                    index=TYPE_OPTIONS.index(cur_type))
                new_uom  = st.selectbox("UOM", UOM_OPTIONS,
                    index=UOM_OPTIONS.index(cur_uom))
                new_ss   = st.number_input("Safety Stock", min_value=0.0, step=1.0,
                    value=float(sel_row["safety_stock"] or 0))

                if st.form_submit_button("Save Changes", type="primary"):
                    if not new_name.strip():
                        st.error("Item Name cannot be empty.")
                    else:
                        try:
                            sb.table("item_codes").update({
                                "item_name":    new_name.strip(),
                                "item_type":    new_type,
                                "uom":          new_uom,
                                "safety_stock": new_ss,
                            }).eq("item_code", sel_code).eq("site_id", sid).execute()
                            st.success(f"✅ '{sel_code}' updated successfully.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

# ══════════════════════════════════════════════
# PAGE: BOM  — multi-level
# ══════════════════════════════════════════════
elif active == "🔗 BOM":
    st.markdown('<div class="section-title">Bill of Materials</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Multi-level BOM — a parent can also be child of another parent (intermediate). Define each relationship as a line.</div>', unsafe_allow_html=True)

    all_items = get_items()

    if all_items.empty or len(all_items) < 2:
        st.markdown('<div class="alert-warn alert-box">⚠ Need at least 2 items to define a BOM.</div>', unsafe_allow_html=True)
    else:
        tab1, tab2 = st.tabs(["➕ Add BOM Line", "📋 View BOM Tree"])

        with tab1:
            item_opts_all = all_items["item_code"].tolist()
            fmt = {r["item_code"]: f"{r['item_code']} — {r['item_name']} [{r['item_type']}]" for _, r in all_items.iterrows()}

            with st.form("bom_form"):
                parent_sel = st.selectbox("Parent Item", item_opts_all,
                    format_func=lambda x: fmt.get(x, x),
                    help="The item being assembled / produced")
                child_sel  = st.selectbox("Child / Component", item_opts_all,
                    format_func=lambda x: fmt.get(x, x),
                    help="The item consumed to make the parent. Can itself be an intermediate (sub-assembly).")
                qty_per    = st.number_input("Qty of Child per 1 Parent", min_value=0.001, step=0.5, value=1.0)
                if st.form_submit_button("Add BOM Line", type="primary"):
                    if parent_sel == child_sel:
                        st.error("Parent and child cannot be the same item.")
                    else:
                        try:
                            sb.table("bom").upsert(
                                {"parent_code":parent_sel,"child_code":child_sel,"qty_per":qty_per,"site_id":sid},
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

                # Render tree grouped by parent, with level indentation
                parents = bom_df["parent_code"].unique()
                for parent in parents:
                    sub = bom_df[bom_df["parent_code"]==parent]
                    prow = sub.iloc[0]
                    ptype = prow.get("parent_type","")
                    badge_color = "#3b82f6" if ptype=="parent" else "#8b5cf6"
                    st.markdown(f"""
                    <div style="border-left:3px solid {badge_color};padding-left:.7rem;margin-bottom:.3rem">
                        <span style="font-size:.68rem;font-weight:700;color:{badge_color};text-transform:uppercase">{ptype}</span><br>
                        <span style="font-weight:700;font-size:1rem;color:#0f172a">{parent}</span>
                        <span style="color:#64748b;font-size:.85rem"> — {prow['parent_name']}</span>
                    </div>
                    """, unsafe_allow_html=True)

                    rows = []
                    for _, r in sub.iterrows():
                        ct = r.get("child_type","")
                        ct_badge = "🔵 intermediate (sub-asm)" if ct=="intermediate" else ("⬜ child" if ct=="child" else "🟡 parent")
                        rows.append({"Component Code":r["child_code"],"Component Name":r["child_name"],
                                     "Type":ct_badge,"Qty/Unit":r["qty_per"],"UOM":r["uom"]})
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                st.markdown(to_csv_dl(bom_df,"bom.csv"), unsafe_allow_html=True)

                # Delete a BOM line
                st.markdown("---")
                st.markdown("**Remove a BOM line**")
                bom_options = {f"{r['parent_code']} → {r['child_code']}": r for _, r in bom_df.iterrows()}
                sel_bom = st.selectbox("Select line to remove", list(bom_options.keys()))
                if st.button("Remove BOM Line", key="del_bom"):
                    r = bom_options[sel_bom]
                    sb.table("bom").delete().eq("parent_code",r["parent_code"]).eq("child_code",r["child_code"]).eq("site_id",sid).execute()
                    st.success("Removed."); st.rerun()
            else:
                st.markdown('<div class="alert-info alert-box">No BOM entries yet.</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
# PAGE: INBOUND
# ══════════════════════════════════════════════
elif active == "📥 Inbound":
    st.markdown('<div class="section-title">Inbound Stock</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Record components / sub-assemblies received at this site</div>', unsafe_allow_html=True)

    all_items = get_items()
    # Inbound can be any item that acts as a child in BOM, or any item if none defined yet
    children_df = get_children() if not get_bom_full().empty else all_items

    if all_items.empty:
        st.markdown('<div class="alert-warn alert-box">⚠ No items defined for this site.</div>', unsafe_allow_html=True)
    else:
        inbound_items = children_df if not children_df.empty else all_items
        tab1, tab2, tab3, tab4 = st.tabs(["➕ Entry","📤 Bulk CSV","📋 History","🗑 Delete"])

        with tab1:
            with st.form("inbound_form"):
                txn_date   = st.date_input("Date *", value=date.today())
                item_sel   = st.selectbox("Item *", inbound_items["item_code"].tolist(),
                    format_func=lambda x: f"{x} — {all_items.set_index('item_code').loc[x,'item_name']}" if x in all_items.set_index('item_code').index else x)
                qty        = st.number_input("Quantity *", min_value=0.01, step=1.0)
                invoice_no = st.text_input("Invoice No.")
                supplier   = st.text_input("Supplier Name")
                remarks    = st.text_area("Remarks", height=60)
                submitted  = st.form_submit_button("Record Inbound", type="primary")
            photo_url, photo_name = photo_widget("Attach Invoice / Photo proof","inb_photo","inbound")
            if submitted:
                try:
                    sb.table("inbound").insert({
                        "txn_date":str(txn_date),"item_code":item_sel,"qty":qty,
                        "invoice_no":invoice_no,"supplier":supplier,"remarks":remarks,
                        "invoice_filename":photo_name,"photo_url":photo_url,"site_id":sid,
                    }).execute()
                    st.success(f"✅ {qty} × {item_sel} recorded.")
                except Exception as e: st.error(f"Error: {e}")

        with tab2:
            st.markdown("**CSV:** `date, item_code, qty, invoice_no, supplier`")
            up = st.file_uploader("CSV", type=["csv"], key="inb_bulk")
            if up:
                udf = pd.read_csv(up)
                st.dataframe(udf.head(10), use_container_width=True)
                if st.button("Import"):
                    rows=[{"txn_date":str(r.get("date","")),"item_code":str(r.get("item_code","")),"qty":float(r.get("qty",0)),
                           "invoice_no":str(r.get("invoice_no","")),"supplier":str(r.get("supplier","")),"site_id":sid}
                          for _,r in udf.iterrows()]
                    try: sb.table("inbound").insert(rows).execute(); st.success(f"✅ {len(rows)} rows imported.")
                    except Exception as e: st.error(f"{e}")

        with tab3:
            resp = (sb.table("inbound").select("txn_date,item_code,qty,invoice_no,supplier,invoice_filename,photo_url,remarks,created_at")
                      .eq("site_id",sid).gte("txn_date",str(filter_date_from)).lte("txn_date",str(filter_date_to))
                      .order("txn_date",desc=True).execute())
            df = to_df(resp)
            if not df.empty:
                if filter_item!="All Items": df=df[df["item_code"]==filter_item]
                disp = df.copy()
                disp["photo"] = disp["photo_url"].apply(lambda u: f"[View]({u})" if u else "—")
                st.dataframe(disp.drop(columns=["photo_url"]), use_container_width=True, hide_index=True,
                    column_config={"photo": st.column_config.LinkColumn("Photo",width="small")})
                st.markdown(to_csv_dl(df.drop(columns=["photo_url"]),"inbound.csv"), unsafe_allow_html=True)
            else: st.markdown('<div class="alert-info alert-box">No records in date range.</div>', unsafe_allow_html=True)

        with tab4:
            st.markdown('<div class="alert-warn alert-box">⚠ Deletions are permanently logged.</div>', unsafe_allow_html=True)
            resp = (sb.table("inbound").select("id,txn_date,item_code,qty,invoice_no,supplier,remarks")
                      .eq("site_id",sid).gte("txn_date",str(filter_date_from)).lte("txn_date",str(filter_date_to))
                      .order("txn_date",desc=True).execute())
            del_df = to_df(resp)
            if not del_df.empty:
                if filter_item!="All Items": del_df=del_df[del_df["item_code"]==filter_item]
                opts = {f"ID {r['id']} | {r['txn_date']} | {r['item_code']} | {r['qty']}":r for _,r in del_df.iterrows()}
                sel = st.selectbox("Record to delete", list(opts.keys()), key="inb_del")
                rsn = st.text_input("Reason *", key="inb_del_rsn")
                if st.button("🗑 Delete", type="primary", key="inb_del_btn"):
                    if not rsn.strip(): st.error("Reason required.")
                    else:
                        if delete_record("inbound", opts[sel]["id"], dict(opts[sel]), rsn, sid):
                            st.success("Deleted & logged."); st.rerun()
            else: st.markdown('<div class="alert-info alert-box">No records.</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════
# PAGE: ASSEMBLY
# ══════════════════════════════════════════════
elif active == "🔧 Assembly":
    st.markdown('<div class="section-title">Assembly Log</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Record FG or sub-assemblies produced — auto-deducts components per BOM</div>', unsafe_allow_html=True)

    parents_df = get_parents()
    all_items  = get_items()
    if parents_df.empty:
        st.markdown('<div class="alert-warn alert-box">⚠ No BOM defined yet — add BOM lines first.</div>', unsafe_allow_html=True)
    else:
        tab1, tab2, tab3 = st.tabs(["➕ Record","📋 History","🗑 Delete"])

        with tab1:
            parent_sel      = st.selectbox("Item to Assemble (Parent)", parents_df["item_code"].tolist(),
                format_func=lambda x: f"{x} — {all_items.set_index('item_code').loc[x,'item_name']}" if x in all_items.set_index('item_code').index else x)
            qty_to_assemble = st.number_input("Qty", min_value=1.0, step=1.0, value=1.0)

            bom_resp = (sb.table("bom")
                          .select("child_code,qty_per,item_codes!bom_child_code_fkey(item_name,uom,item_type)")
                          .eq("parent_code",parent_sel).eq("site_id",sid).execute())
            bom_rows = bom_resp.data or []
            child_stock = get_child_stock()
            parent_stock = get_parent_stock()
            can_assemble = True

            if bom_rows:
                st.markdown("**Component check**")
                preview = []
                for r in bom_rows:
                    ic = r.get("item_codes") or {}
                    needed = r["qty_per"] * qty_to_assemble
                    ctype  = ic.get("item_type","")
                    # Check stock from both child_stock and parent_stock (intermediate items appear in both)
                    avail = 0
                    m = child_stock[child_stock["item_code"]==r["child_code"]] if not child_stock.empty else pd.DataFrame()
                    if not m.empty: avail = float(m["stock_on_hand"].iloc[0])
                    else:
                        m2 = parent_stock[parent_stock["item_code"]==r["child_code"]] if not parent_stock.empty else pd.DataFrame()
                        if not m2.empty: avail = float(m2["stock_on_hand"].iloc[0])
                    ok = avail >= needed
                    if not ok: can_assemble = False
                    type_label = "🔵 sub-asm" if ctype=="intermediate" else ("⬜ component" if ctype=="child" else "")
                    preview.append({"Component":r["child_code"],"Name":ic.get("item_name",""),
                                    "Type":type_label,"Need":needed,"Have":avail,"Status":"✅" if ok else "❌ SHORT"})
                st.dataframe(pd.DataFrame(preview), use_container_width=True, hide_index=True)
                if not can_assemble:
                    st.markdown('<div class="alert-danger alert-box">❌ Insufficient stock for one or more components.</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="alert-warn alert-box">⚠ No BOM defined for this item.</div>', unsafe_allow_html=True)

            with st.form("asm_form"):
                txn_date = st.date_input("Date", value=date.today())
                remarks  = st.text_area("Remarks", height=60)
                if st.form_submit_button("Record Assembly", type="primary"):
                    if not bom_rows: st.error("No BOM defined.")
                    else:
                        try:
                            sb.table("assembly").insert({
                                "txn_date":str(txn_date),"parent_code":parent_sel,
                                "qty_assembled":qty_to_assemble,"remarks":remarks,"site_id":sid,
                            }).execute()
                            st.success(f"✅ {qty_to_assemble} × {parent_sel} assembled.")
                        except Exception as e: st.error(f"Error: {e}")

        with tab2:
            resp = sb.rpc("get_assembly_history",{"date_from":str(filter_date_from),"date_to":str(filter_date_to),"p_site_id":sid}).execute()
            df = to_df(resp)
            if not df.empty:
                if filter_item!="All Items": df=df[df["parent_code"]==filter_item]
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.markdown(to_csv_dl(df,"assembly.csv"), unsafe_allow_html=True)
            else: st.markdown('<div class="alert-info alert-box">No records.</div>', unsafe_allow_html=True)

        with tab3:
            st.markdown('<div class="alert-warn alert-box">⚠ Restores component quantities. Logged permanently.</div>', unsafe_allow_html=True)
            resp=(sb.table("assembly").select("id,txn_date,parent_code,qty_assembled,remarks")
                    .eq("site_id",sid).gte("txn_date",str(filter_date_from)).lte("txn_date",str(filter_date_to))
                    .order("txn_date",desc=True).execute())
            del_df=to_df(resp)
            if not del_df.empty:
                if filter_item!="All Items": del_df=del_df[del_df["parent_code"]==filter_item]
                opts={f"ID {r['id']} | {r['txn_date']} | {r['parent_code']} | {r['qty_assembled']}":r for _,r in del_df.iterrows()}
                sel=st.selectbox("Record",list(opts.keys()),key="asm_del")
                rsn=st.text_input("Reason *",key="asm_del_rsn")
                if st.button("🗑 Delete",type="primary",key="asm_del_btn"):
                    if not rsn.strip(): st.error("Reason required.")
                    else:
                        rec=opts[sel]
                        if delete_record("assembly",rec["id"],{"txn_date":rec["txn_date"],"parent_code":rec["parent_code"],"qty_assembled":rec["qty_assembled"]},rsn,sid):
                            st.success("Deleted & logged."); st.rerun()
            else: st.markdown('<div class="alert-info alert-box">No records.</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
# PAGE: OUTBOUND
# ══════════════════════════════════════════════
elif active == "📤 Outbound":
    st.markdown('<div class="section-title">Outbound Dispatch</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Record finished goods dispatched from this site to customer</div>', unsafe_allow_html=True)

    parents_df = get_parents()
    all_items  = get_items()
    if parents_df.empty:
        st.markdown('<div class="alert-warn alert-box">⚠ No parent items defined in BOM.</div>', unsafe_allow_html=True)
    else:
        tab1, tab2, tab3 = st.tabs(["➕ Record","📋 History","🗑 Delete"])

        with tab1:
            with st.form("out_form"):
                txn_date     = st.date_input("Date *", value=date.today())
                parent_sel   = st.selectbox("FG Item *", parents_df["item_code"].tolist(),
                    format_func=lambda x: f"{x} — {all_items.set_index('item_code').loc[x,'item_name']}" if x in all_items.set_index('item_code').index else x)
                qty          = st.number_input("Qty *", min_value=0.01, step=1.0)
                customer     = st.text_input("Customer")
                gate_pass_no = st.text_input("Gate Pass No.")
                remarks      = st.text_area("Remarks", height=60)
                submitted    = st.form_submit_button("Record Outbound", type="primary")
            photo_url, photo_name = photo_widget("Gate Pass / Photo proof","out_photo","outbound")
            if submitted:
                _, ps = get_stock()
                avail = 0
                if not ps.empty:
                    m = ps[ps["item_code"]==parent_sel]
                    if not m.empty: avail = float(m["stock_on_hand"].iloc[0])
                if qty > avail:
                    st.error(f"❌ Only {avail:,.0f} in stock.")
                else:
                    try:
                        sb.table("outbound").insert({
                            "txn_date":str(txn_date),"parent_code":parent_sel,"qty":qty,
                            "customer":customer,"gate_pass_no":gate_pass_no,
                            "gate_pass_filename":photo_name,"photo_url":photo_url,
                            "remarks":remarks,"site_id":sid,
                        }).execute()
                        st.success(f"✅ {qty} × {parent_sel} dispatched to {customer}.")
                    except Exception as e: st.error(f"Error: {e}")

        with tab2:
            resp=sb.rpc("get_outbound_history",{"date_from":str(filter_date_from),"date_to":str(filter_date_to),"p_site_id":sid}).execute()
            df=to_df(resp)
            if not df.empty:
                if filter_item!="All Items": df=df[df["parent_code"]==filter_item]
                st.dataframe(df,use_container_width=True,hide_index=True)
                st.markdown(to_csv_dl(df,"outbound.csv"),unsafe_allow_html=True)
            else: st.markdown('<div class="alert-info alert-box">No records.</div>',unsafe_allow_html=True)

        with tab3:
            st.markdown('<div class="alert-warn alert-box">⚠ Restores FG stock. Logged permanently.</div>',unsafe_allow_html=True)
            resp=(sb.table("outbound").select("id,txn_date,parent_code,qty,customer,gate_pass_no,remarks")
                    .eq("site_id",sid).gte("txn_date",str(filter_date_from)).lte("txn_date",str(filter_date_to))
                    .order("txn_date",desc=True).execute())
            del_df=to_df(resp)
            if not del_df.empty:
                if filter_item!="All Items": del_df=del_df[del_df["parent_code"]==filter_item]
                opts={f"ID {r['id']} | {r['txn_date']} | {r['parent_code']} | {r['qty']} | {r.get('customer','')}":r for _,r in del_df.iterrows()}
                sel=st.selectbox("Record",list(opts.keys()),key="out_del")
                rsn=st.text_input("Reason *",key="out_del_rsn")
                if st.button("🗑 Delete",type="primary",key="out_del_btn"):
                    if not rsn.strip(): st.error("Reason required.")
                    else:
                        rec=opts[sel]
                        if delete_record("outbound",rec["id"],{"txn_date":rec["txn_date"],"parent_code":rec["parent_code"],"qty":rec["qty"]},rsn,sid):
                            st.success("Deleted & logged."); st.rerun()
            else: st.markdown('<div class="alert-info alert-box">No records.</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════
# PAGE: ADJUSTMENTS
# ══════════════════════════════════════════════
elif active == "⚖️ Adjustments":
    st.markdown('<div class="section-title">Stock Adjustments</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Expiry · Wastage · Damage · Found · Audit corrections</div>', unsafe_allow_html=True)

    all_items = get_items()
    if all_items.empty:
        st.markdown('<div class="alert-warn alert-box">⚠ No items defined.</div>', unsafe_allow_html=True)
    else:
        CATS  = ["expiry","wastage","damage","found","correction","audit","other"]
        ICONS = {"expiry":"⏰","wastage":"🗑","damage":"💥","found":"🔍","correction":"✏️","audit":"📋","other":"📝"}
        tab1, tab2, tab3 = st.tabs(["➕ New","📋 History","🗑 Delete"])

        with tab1:
            adj_type = st.radio("Direction", ["deduct","add"],
                format_func=lambda x: "➖ Deduct" if x=="deduct" else "➕ Add", horizontal=True)
            with st.form("adj_form"):
                txn_date     = st.date_input("Date *", value=date.today())
                item_sel     = st.selectbox("Item *", all_items["item_code"].tolist(),
                    format_func=lambda x: f"{x} — {all_items.set_index('item_code').loc[x,'item_name']}" if x in all_items.set_index('item_code').index else x)
                qty          = st.number_input("Quantity *", min_value=0.01, step=1.0)
                reason_cat   = st.selectbox("Reason *", CATS, format_func=lambda x: f"{ICONS.get(x,'')} {x.title()}")
                reason_notes = st.text_area("Notes", height=70)
                # Stock preview
                cs, ps = get_stock()
                all_s = pd.concat([cs[["item_code","stock_on_hand","uom"]] if not cs.empty else pd.DataFrame(),
                                   ps[["item_code","stock_on_hand","uom"]] if not ps.empty else pd.DataFrame()], ignore_index=True)
                if not all_s.empty:
                    m = all_s[all_s["item_code"]==item_sel]
                    cur = float(m["stock_on_hand"].iloc[0]) if not m.empty else 0
                    uom_v = m["uom"].iloc[0] if not m.empty else ""
                    aft = cur - qty if adj_type=="deduct" else cur + qty
                    col = "#dc2626" if aft<0 else "#16a34a"
                    st.markdown(f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:.7rem;font-size:.82rem">Now: <b>{cur:,.0f} {uom_v}</b> → After: <b style="color:{col}">{aft:,.0f} {uom_v}</b>{"&nbsp;<span style=\'color:#dc2626\'>⚠ Negative</span>" if aft<0 else ""}</div>', unsafe_allow_html=True)
                submitted = st.form_submit_button("Save Adjustment", type="primary")
            photo_url, photo_name = photo_widget("Photo evidence (damage/expiry proof)","adj_photo","adjustments")
            if submitted:
                if not reason_notes.strip() and reason_cat=="other":
                    st.error("Notes required for 'Other'.")
                else:
                    try:
                        sb.table("stock_adjustments").insert({
                            "txn_date":str(txn_date),"item_code":item_sel,"adjustment_type":adj_type,
                            "qty":qty,"reason_category":reason_cat,"reason_notes":reason_notes,
                            "photo_url":photo_url,"site_id":sid,
                        }).execute()
                        st.success(f"✅ {qty:,.0f} {'deducted from' if adj_type=='deduct' else 'added to'} {item_sel} ({reason_cat}).")
                    except Exception as e: st.error(f"Error: {e}")

        with tab2:
            resp=(sb.table("stock_adjustments").select("id,txn_date,item_code,adjustment_type,qty,reason_category,reason_notes,photo_url,created_at")
                    .eq("site_id",sid).gte("txn_date",str(filter_date_from)).lte("txn_date",str(filter_date_to))
                    .order("txn_date",desc=True).execute())
            df=to_df(resp)
            if not df.empty:
                if filter_item!="All Items": df=df[df["item_code"]==filter_item]
                c1,c2,c3=st.columns(3)
                with c1: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Total</div><div class="kpi-value">{len(df)}</div></div>',unsafe_allow_html=True)
                with c2: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Deducted</div><div class="kpi-value" style="color:#dc2626">{df[df["adjustment_type"]=="deduct"]["qty"].sum():,.0f}</div></div>',unsafe_allow_html=True)
                with c3: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Added</div><div class="kpi-value" style="color:#16a34a">{df[df["adjustment_type"]=="add"]["qty"].sum():,.0f}</div></div>',unsafe_allow_html=True)
                disp=df.copy(); disp["photo"]=disp["photo_url"].apply(lambda u:f"[View]({u})" if u else "—")
                st.dataframe(disp.drop(columns=["id","photo_url"]),use_container_width=True,hide_index=True,
                    column_config={"photo":st.column_config.LinkColumn("Photo",width="small"),
                                   "qty":st.column_config.NumberColumn("Qty",format="%.0f"),
                                   "created_at":st.column_config.DatetimeColumn("Logged",format="DD MMM YY HH:mm")})
                photos=df[df["photo_url"].notna()&(df["photo_url"]!="")]
                if not photos.empty:
                    st.markdown("**Evidence Photos**")
                    for _,row in photos.iterrows():
                        with st.expander(f"{row['txn_date']} · {row['item_code']} · {row['reason_category']}"):
                            st.image(row["photo_url"],use_container_width=True)
                            st.caption(row.get("reason_notes",""))
                st.markdown(to_csv_dl(df.drop(columns=["id","photo_url"]),"adjustments.csv"),unsafe_allow_html=True)
            else: st.markdown('<div class="alert-info alert-box">No records.</div>',unsafe_allow_html=True)

        with tab3:
            st.markdown('<div class="alert-warn alert-box">⚠ Reverses stock effect. Permanently logged.</div>',unsafe_allow_html=True)
            resp=(sb.table("stock_adjustments").select("id,txn_date,item_code,adjustment_type,qty,reason_category")
                    .eq("site_id",sid).gte("txn_date",str(filter_date_from)).lte("txn_date",str(filter_date_to))
                    .order("txn_date",desc=True).execute())
            del_df=to_df(resp)
            if not del_df.empty:
                if filter_item!="All Items": del_df=del_df[del_df["item_code"]==filter_item]
                opts={f"ID {r['id']} | {r['txn_date']} | {r['item_code']} | {r['adjustment_type'].upper()} {r['qty']} | {r['reason_category']}":r for _,r in del_df.iterrows()}
                sel=st.selectbox("Record",list(opts.keys()),key="adj_del")
                rsn=st.text_input("Reason *",key="adj_del_rsn")
                if st.button("🗑 Delete",type="primary",key="adj_del_btn"):
                    if not rsn.strip(): st.error("Reason required.")
                    else:
                        rec=opts[sel]
                        if delete_record("stock_adjustments",rec["id"],{k:rec[k] for k in ["txn_date","item_code","adjustment_type","qty","reason_category"]},rsn,sid):
                            st.success("Deleted & logged."); st.rerun()
            else: st.markdown('<div class="alert-info alert-box">No records.</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════
# PAGE: STOCK
# ══════════════════════════════════════════════
elif active == "📊 Stock":
    st.markdown('<div class="section-title">Live Stock Position</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Real-time inventory at this site — includes adjustments</div>', unsafe_allow_html=True)

    cs, ps = get_stock()

    c1,c2 = st.columns(2)
    with c1: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Component SKUs</div><div class="kpi-value">{len(cs) if not cs.empty else 0}</div></div>',unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="kpi-card"><div class="kpi-label">FG Ready to Ship</div><div class="kpi-value" style="color:#16a34a">{float(ps["stock_on_hand"].sum()) if not ps.empty else 0:,.0f}</div></div>',unsafe_allow_html=True)
    low = len(cs[(cs["stock_on_hand"]>0)&(cs["stock_on_hand"]<=cs["safety_stock"])]) if not cs.empty else 0
    out = len(cs[cs["stock_on_hand"]<=0]) if not cs.empty else 0
    c1,c2 = st.columns(2)
    with c1: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Below Safety Stock</div><div class="kpi-value" style="color:#d97706">{low}</div></div>',unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Out of Stock</div><div class="kpi-value" style="color:#dc2626">{out}</div></div>',unsafe_allow_html=True)

    def slbl(oh,ss): return "🔴 OUT" if oh<=0 else ("🟡 LOW" if oh<=ss else "🟢 OK")

    st.markdown("---")
    st.markdown("#### Components / Sub-assemblies")
    if not cs.empty:
        df=cs.copy()
        if filter_item!="All Items": df=df[df["item_code"]==filter_item]
        df["status"]=df.apply(lambda r:slbl(r["stock_on_hand"],r["safety_stock"]),axis=1)
        st.dataframe(df[["item_code","item_name","item_type","uom","total_inbound","total_consumed","total_adjusted","stock_on_hand","safety_stock","status"]],
            use_container_width=True,hide_index=True,
            column_config={
                "item_code":st.column_config.TextColumn("Code",width="small"),
                "item_name":st.column_config.TextColumn("Name",width="medium"),
                "item_type":st.column_config.TextColumn("Type",width="small"),
                "uom":st.column_config.TextColumn("UOM",width="small"),
                "total_inbound":st.column_config.NumberColumn("In",width="small",format="%.0f"),
                "total_consumed":st.column_config.NumberColumn("Used",width="small",format="%.0f"),
                "total_adjusted":st.column_config.NumberColumn("Adj",width="small",format="%.0f"),
                "stock_on_hand":st.column_config.NumberColumn("On Hand",width="small",format="%.0f"),
                "safety_stock":st.column_config.NumberColumn("Safety",width="small",format="%.0f"),
                "status":st.column_config.TextColumn("Status",width="small"),
            })
        st.markdown(to_csv_dl(df,"child_stock.csv"),unsafe_allow_html=True)
    else: st.markdown('<div class="alert-info alert-box">No component data yet.</div>',unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### Finished Goods / Top-level Parents")
    if not ps.empty:
        df=ps.copy()
        if filter_item!="All Items": df=df[df["item_code"]==filter_item]
        df["status"]=df.apply(lambda r:slbl(r["stock_on_hand"],r["safety_stock"]),axis=1)
        st.dataframe(df[["item_code","item_name","item_type","uom","total_assembled","total_dispatched","total_adjusted","stock_on_hand","safety_stock","status"]],
            use_container_width=True,hide_index=True,
            column_config={
                "item_code":st.column_config.TextColumn("Code",width="small"),
                "item_name":st.column_config.TextColumn("Name",width="medium"),
                "item_type":st.column_config.TextColumn("Type",width="small"),
                "uom":st.column_config.TextColumn("UOM",width="small"),
                "total_assembled":st.column_config.NumberColumn("Assembled",width="small",format="%.0f"),
                "total_dispatched":st.column_config.NumberColumn("Dispatched",width="small",format="%.0f"),
                "total_adjusted":st.column_config.NumberColumn("Adj",width="small",format="%.0f"),
                "stock_on_hand":st.column_config.NumberColumn("On Hand",width="small",format="%.0f"),
                "safety_stock":st.column_config.NumberColumn("Safety",width="small",format="%.0f"),
                "status":st.column_config.TextColumn("Status",width="small"),
            })
        st.markdown(to_csv_dl(df,"parent_stock.csv"),unsafe_allow_html=True)
    else: st.markdown('<div class="alert-info alert-box">No FG data yet.</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════
# PAGE: FORECAST
# ══════════════════════════════════════════════
elif active == "🔮 Forecast":
    st.markdown('<div class="section-title">Production Forecast</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Set target FG quantities — see component gaps and max producible today</div>', unsafe_allow_html=True)

    parents_df = get_parents()
    all_items  = get_items()
    if parents_df.empty:
        st.markdown('<div class="alert-warn alert-box">⚠ No BOM defined yet.</div>',unsafe_allow_html=True)
    else:
        num = int(st.number_input("FG items to plan",min_value=1,max_value=10,value=1,step=1))
        targets = {}
        for i in range(num):
            st.markdown(f"**Item {i+1}**")
            p = st.selectbox("Item",parents_df["item_code"].tolist(),key=f"fc_p_{i}",
                format_func=lambda x: f"{x} — {all_items.set_index('item_code').loc[x,'item_name']}" if x in all_items.set_index('item_code').index else x)
            q = st.number_input("Target Qty",min_value=0.0,step=1.0,value=100.0,key=f"fc_q_{i}")
            targets[p] = targets.get(p,0)+q

        if st.button("Run Forecast",type="primary"):
            cs,_ = get_stock()
            bom_df = get_bom_full()
            req_map = {}
            for parent,tq in targets.items():
                sub = bom_df[bom_df["parent_code"]==parent] if not bom_df.empty else pd.DataFrame()
                for _,r in sub.iterrows():
                    req_map[r["child_code"]] = req_map.get(r["child_code"],0)+r["qty_per"]*tq

            st.markdown("---")
            if not req_map:
                st.markdown('<div class="alert-warn alert-box">⚠ No BOM for selected items.</div>',unsafe_allow_html=True)
            else:
                results,max_prod,limiting=[],float("inf"),None
                for cc,total_req in req_map.items():
                    avail=safety=0
                    # Check both child and parent stock (for intermediates)
                    ps_all = pd.concat([cs[["item_code","stock_on_hand","safety_stock"]] if not cs.empty else pd.DataFrame(),
                                        get_parent_stock()[["item_code","stock_on_hand","safety_stock"]] if not get_parent_stock().empty else pd.DataFrame()],ignore_index=True)
                    m=ps_all[ps_all["item_code"]==cc]
                    if not m.empty: avail=float(m["stock_on_hand"].iloc[0]); safety=float(m["safety_stock"].iloc[0])
                    shortfall=max(0,total_req-avail)
                    if total_req>0:
                        ratio=avail/total_req
                        if ratio<max_prod: max_prod,limiting=ratio,cc
                    results.append({"Component":cc,"Required":total_req,"In Stock":avail,"Safety":safety,
                                    "Shortfall":shortfall,"To Order":shortfall,"Status":"✅ OK" if avail>=total_req else "❌ SHORT"})
                st.dataframe(pd.DataFrame(results),use_container_width=True,hide_index=True)
                st.markdown(to_csv_dl(pd.DataFrame(results),"forecast.csv"),unsafe_allow_html=True)
                total_t=sum(targets.values())
                prod=int(min(max_prod,1.0)*total_t) if max_prod<float("inf") else int(total_t)
                prod=max(0,prod); gap=max(0,int(total_t)-prod)
                st.markdown("---")
                c1,c2,c3=st.columns(3)
                col="#16a34a" if prod>=total_t else "#d97706"
                with c1: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Target</div><div class="kpi-value">{int(total_t):,}</div></div>',unsafe_allow_html=True)
                with c2: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Can Make Now</div><div class="kpi-value" style="color:{col}">{prod:,}</div></div>',unsafe_allow_html=True)
                with c3: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Gap</div><div class="kpi-value" style="color:#dc2626">{gap:,}</div></div>',unsafe_allow_html=True)
                if limiting and prod<total_t:
                    st.markdown(f'<div class="alert-danger alert-box">🔴 Bottleneck: <b>{limiting}</b></div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════
# PAGE: LEDGER
# ══════════════════════════════════════════════
elif active == "📋 Ledger":
    st.markdown('<div class="section-title">Transaction Ledger</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">All movements at this site — tally with vendor</div>', unsafe_allow_html=True)

    resp=sb.rpc("get_ledger",{"date_from":str(filter_date_from),"date_to":str(filter_date_to),"p_site_id":sid}).execute()
    df=to_df(resp)
    if not df.empty:
        if filter_item!="All Items": df=df[df["item_code"]==filter_item]
        c1,c2=st.columns(2)
        with c1: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Transactions</div><div class="kpi-value">{len(df)}</div></div>',unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="kpi-card"><div class="kpi-label">FG Dispatched</div><div class="kpi-value">{df[df["txn_type"]=="Outbound"]["qty_out"].sum():,.0f}</div></div>',unsafe_allow_html=True)
        c1,c2=st.columns(2)
        with c1: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Components In</div><div class="kpi-value">{df[df["txn_type"]=="Inbound"]["qty_in"].sum():,.0f}</div></div>',unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="kpi-card"><div class="kpi-label">FG Assembled</div><div class="kpi-value">{df[df["txn_type"]=="Assembly"]["qty_in"].sum():,.0f}</div></div>',unsafe_allow_html=True)
        st.markdown("---")
        all_types=df["txn_type"].unique().tolist()
        txn_f=st.multiselect("Filter by Type",all_types,default=all_types)
        st.dataframe(df[df["txn_type"].isin(txn_f)],use_container_width=True,hide_index=True)
        st.markdown(to_csv_dl(df,"ledger.csv"),unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("**Stock Tally by Item**")
        tally=[{"Item":item,"Total In":df[df["item_code"]==item]["qty_in"].sum(),
                "Total Out":df[df["item_code"]==item]["qty_out"].sum(),
                "Net":df[df["item_code"]==item]["qty_in"].sum()-df[df["item_code"]==item]["qty_out"].sum()}
               for item in df["item_code"].unique()]
        st.dataframe(pd.DataFrame(tally).sort_values("Item"),use_container_width=True,hide_index=True)
    else: st.markdown('<div class="alert-info alert-box">No transactions in selected date range.</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════
# PAGE: AUDIT LOG
# ══════════════════════════════════════════════
elif active == "🗑 Audit Log":
    st.markdown('<div class="section-title">Deletion Audit Log</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Every deletion at this site — immutable record</div>', unsafe_allow_html=True)

    resp = (sb.table("deletion_log").select("*").eq("site_id", sid)
              .gte("deleted_at", str(filter_date_from))
              .lte("deleted_at", str(filter_date_to) + "T23:59:59")
              .order("deleted_at", desc=True).execute())
    df = to_df(resp)

    if not df.empty:
        if filter_item != "All Items":
            df = df[df["item_code"] == filter_item]

        c1, c2, c3 = st.columns(3)
        inbound_count = len(df[df["table_name"] == "inbound"])
        other_count   = len(df[df["table_name"].isin(["assembly","outbound","stock_adjustments"])])
        with c1:
            st.markdown(f'<div class="kpi-card"><div class="kpi-label">Total Deletions</div><div class="kpi-value">{len(df)}</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="kpi-card"><div class="kpi-label">Inbound</div><div class="kpi-value">{inbound_count}</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="kpi-card"><div class="kpi-label">Asm / Out / Adj</div><div class="kpi-value">{other_count}</div></div>', unsafe_allow_html=True)

        st.markdown("---")
        tbl_f = st.multiselect(
            "Filter by Table",
            ["inbound", "assembly", "outbound", "stock_adjustments"],
            default=["inbound", "assembly", "outbound", "stock_adjustments"]
        )
        df_f = df[df["table_name"].isin(tbl_f)]

        st.dataframe(
            df_f[["deleted_at","table_name","record_id","txn_date","item_code","qty","reason"]],
            use_container_width=True, hide_index=True,
            column_config={
                "deleted_at":  st.column_config.DatetimeColumn("Deleted At", format="DD MMM YY HH:mm"),
                "table_name":  st.column_config.TextColumn("Table",    width="small"),
                "record_id":   st.column_config.NumberColumn("ID",     width="small", format="%d"),
                "txn_date":    st.column_config.DateColumn("Txn Date", width="small"),
                "item_code":   st.column_config.TextColumn("Item",     width="small"),
                "qty":         st.column_config.NumberColumn("Qty",    width="small", format="%.0f"),
                "reason":      st.column_config.TextColumn("Reason",   width="large"),
            }
        )
        st.markdown(to_csv_dl(df_f, "audit_log.csv"), unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**Full Snapshots**")
        for _, row in df_f.iterrows():
            with st.expander(f"{row['table_name']} · ID {row['record_id']} · {row['txn_date']} · {row['item_code']}"):
                st.json(row.get("snapshot") or {})
                st.markdown(f"**Reason:** {row.get('reason', '—')}")
    else:
        st.markdown('<div class="alert-info alert-box">No deletions in selected date range.</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<div style="text-align:center;font-size:.7rem;color:#94a3b8">VendorLens WIP Manager · Streamlit + Supabase</div>',
    unsafe_allow_html=True
)
