import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# ==========================================
# 0. UI 配置
# ==========================================
st.set_page_config(page_title="Iraq Executive BI & CRM", layout="wide", initial_sidebar_state="expanded")

# 品牌颜色
BRAND_COLOR = "#00B2A9"
DARK_COLOR = "#0f172a"

st.markdown(f"""
<style>
    .stApp {{ font-family: 'Times New Roman', Times, serif; background-color: #f8fafc; }}
    .stButton>button {{ background-color: {DARK_COLOR}; color: white; border-radius: 6px; font-weight: bold; }}
    .kpi-card {{ background-color: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); border-top: 4px solid {BRAND_COLOR}; text-align: center; }}
    .kpi-title {{ font-size: 0.9rem; color: #64748b; font-weight: bold; }}
    .kpi-value {{ font-size: 2rem; color: {DARK_COLOR}; font-weight: 800; }}
</style>
""", unsafe_allow_html=True)

DB_NAME = 'marsriva_iraq_final_v12.db'

def get_db_connection():
    return sqlite3.connect(DB_NAME, timeout=10, check_same_thread=False)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sell_through (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 sale_date DATE, client_name TEXT, category TEXT, model TEXT, sold_qty REAL, source_tag TEXT)''')
    conn.commit()
    conn.close()

init_db()

# 💡 核心升级：增加对您截图中真实表头的识别
COLUMN_MAP = {
    'Date': 'sale_date', 'sale_date': 'sale_date', '日期': 'sale_date',
    'Customer / Supplier en': 'client_name', 'Client': 'client_name', 'client_name': 'client_name', '客户': 'client_name',
    'category': 'category', 'Category': 'category', '类目': 'category',
    'Item Name': 'model', 'Model': 'model', 'model': 'model', '型号': 'model',
    'Sales Quantity': 'sold_qty', 'Quantity': 'sold_qty', 'sold_qty': 'sold_qty', 'Qty': 'sold_qty', '销量': 'sold_qty'
}

# ==========================================
# 1. 侧边栏管理
# ==========================================
st.sidebar.markdown("## ⚙️ Management")

if st.sidebar.button("🗑️ Clear All Data", type="primary", use_container_width=True):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM sell_through")
    conn.commit()
    conn.close()
    st.sidebar.success("Database Cleared!")
    st.rerun()

st.sidebar.markdown("---")

with st.sidebar.form("import_form", clear_on_submit=True):
    st.markdown("### 📥 Import Data")
    source_tag = st.text_input("Batch Name", placeholder="e.g., April_Import")
    uploaded_file = st.file_uploader("Upload Excel/CSV", type=["xlsx", "csv"])
    submit_btn = st.form_submit_button("Confirm Import ✔️")

    if submit_btn and uploaded_file:
        try:
            temp_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            temp_df = temp_df.rename(columns=COLUMN_MAP)
            
            # 检查必须列
            req_cols = ['sale_date', 'client_name', 'category', 'sold_qty']
            if all(c in temp_df.columns for c in req_cols):
                temp_df['sale_date'] = pd.to_datetime(temp_df['sale_date'], errors='coerce').dt.strftime('%Y-%m-%d')
                if 'model' not in temp_df.columns: temp_df['model'] = "Unknown"
                
                conn = get_db_connection()
                temp_df[['sale_date', 'client_name', 'category', 'model', 'sold_qty']].to_sql("sell_through", conn, if_exists='append', index=False)
                conn.close()
                st.sidebar.success("Import Success!")
                st.rerun()
            else:
                st.sidebar.error("Header mismatch! Please check your Excel headers.")
        except Exception as e: st.sidebar.error(f"Error: {e}")

# ==========================================
# 2. 报表展示 (Tab 逻辑)
# ==========================================
st.title("📈 Iraq Executive BI & CRM Dashboard")

conn = get_db_connection()
raw_df = pd.read_sql("SELECT * FROM sell_through", conn)
conn.close()

if raw_df.empty:
    st.info("👈 Please upload data to activate the dashboard.")
else:
    raw_df['sale_date'] = pd.to_datetime(raw_df['sale_date'])
    
    # 过滤器
    c1, c2, c3 = st.columns(3)
    sel_cats = c1.multiselect("Category", sorted(raw_df['category'].unique()), default=raw_df['category'].unique())
    sel_clients = c2.multiselect("Clients", sorted(raw_df['client_name'].unique()), default=raw_df['client_name'].unique())
    time_gran = c3.selectbox("Resolution", ["Monthly", "Quarterly"])
    res_code = 'M' if time_gran == "Monthly" else 'Q'

    f_df = raw_df[raw_df['category'].isin(sel_cats) & raw_df['client_name'].isin(sel_clients)].copy()

    if not f_df.empty:
        # KPI Cards
        k1, k2, k3 = st.columns(3)
        k1.markdown(f'<div class="kpi-card"><div class="kpi-title">Total Volume</div><div class="kpi-value">{f_df["sold_qty"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="kpi-card"><div class="kpi-title">Active Clients</div><div class="kpi-value">{f_df["client_name"].nunique()}</div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="kpi-card"><div class="kpi-title">Market Coverage</div><div class="kpi-value">{len(f_df):,.0f} Orders</div></div>', unsafe_allow_html=True)

        tab1, tab2, tab3 = st.tabs(["🌍 Market Review", "📋 CRM Deep-Dive", "⚠️ Churn Radar"])

        with tab1:
            col_left, col_right = st.columns([2, 1])
            with col_left:
                st.markdown("#### Sales Trajectory")
                trend = f_df.groupby([f_df['sale_date'].dt.to_period(res_code).astype(str), 'category'])['sold_qty'].sum().reset_index()
                st.plotly_chart(px.line(trend, x='sale_date', y='sold_qty', color='category', markers=True, color_discrete_sequence=[BRAND_COLOR, DARK_COLOR]), use_container_width=True)
            with col_right:
                st.markdown("#### Overall Mix")
                pie_df = f_df[f_df['category'].str.contains('Inverter|Battery', case=False, na=False)].copy()
                pie_df['Type'] = pie_df['category'].apply(lambda x: 'Inverter' if 'inv' in str(x).lower() else 'Battery')
                st.plotly_chart(px.pie(pie_df.groupby('Type')['sold_qty'].sum().reset_index(), values='sold_qty', names='Type', hole=0.5, color_discrete_map={'Inverter': DARK_COLOR, 'Battery': BRAND_COLOR}), use_container_width=True)

        with tab2:
            st.markdown("### Client Matrix (Model vs Date)")
            crm_df = f_df[f_df['category'].str.contains('Inverter|Battery', case=False, na=False)].copy()
            for client in crm_df['client_name'].unique()[:10]:
                with st.expander(f"🏢 {client}"):
                    c_detail = crm_df[crm_df['client_name'] == client]
                    c_detail['Period'] = c_detail['sale_date'].dt.to_period(res_code).astype(str)
                    matrix = c_detail.pivot_table(index='model', columns='Period', values='sold_qty', aggfunc='sum', fill_value=0)
                    st.dataframe(matrix.style.format('{:,.0f}'), use_container_width=True)

        with tab3:
            st.markdown("### Churn Radar")
            # 简易流失分析逻辑
            st.info("Analyzing client purchase gaps...")
