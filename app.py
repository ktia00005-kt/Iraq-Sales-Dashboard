import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# ==========================================
# 0. UI 配置 (IRAQ ST CRM ANALYSIS)
# ==========================================
st.set_page_config(page_title="IRAQ ST CRM ANALYSIS", layout="wide", initial_sidebar_state="expanded")

BRAND_COLOR = "#00B2A9"
DARK_COLOR = "#0f172a"

st.markdown(f"""
<style>
    .stApp {{ font-family: 'Times New Roman', Times, serif; background-color: #f8fafc; }}
    .stButton>button {{ background-color: {DARK_COLOR}; color: white; border-radius: 6px; font-weight: bold; }}
    .stButton>button:hover {{ background-color: #334155; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(15,23,42,0.3); }}
    .filter-card {{ background-color: white; padding: 20px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 25px; }}
    .kpi-card {{ background-color: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); border-top: 4px solid {BRAND_COLOR}; text-align: center; }}
    .kpi-title {{ font-size: 0.9rem; color: #64748b; font-weight: bold; }}
    .kpi-value {{ font-size: 2rem; color: {DARK_COLOR}; font-weight: 800; }}
</style>
""", unsafe_allow_html=True)

# 强制换用 v14 数据库，摆脱所有缓存干扰
DB_NAME = 'marsriva_iraq_v14_bulletproof.db'

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

# 暴力表头清洗字典
COLUMN_MAP = {
    'date': 'sale_date', 'sale_date': 'sale_date', '日期': 'sale_date',
    'customer / supplier en': 'client_name', 'client': 'client_name', 'client_name': 'client_name', 'customer / supplier': 'client_name', '客户名称': 'client_name',
    'category': 'category', 'category ': 'category', '类目': 'category',
    'item name': 'model', 'model': 'model', '型号': 'model',
    'sales quantity': 'sold_qty', 'quantity': 'sold_qty', 'sold_qty': 'sold_qty', 'qty': 'sold_qty', '销量': 'sold_qty'
}

# ==========================================
# 1. 侧边栏管理
# ==========================================
st.sidebar.markdown("## ⚙️ Management")

if st.sidebar.button("🗑️ Reset Database", type="primary", use_container_width=True):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM sell_through")
    conn.commit()
    conn.close()
    st.sidebar.success("Database Reset Successful!")
    st.rerun()

st.sidebar.markdown("---")

with st.sidebar.form("import_form", clear_on_submit=True):
    st.markdown("### 📥 Import Data")
    source_tag = st.text_input("Batch Tag", placeholder="e.g., April_2026")
    uploaded_file = st.file_uploader("Upload Excel/CSV", type=["xlsx", "csv"])
    submit_btn = st.form_submit_button("Upload ✔️")

    if submit_btn and uploaded_file:
        try:
            temp_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            
            # 清除所有空格和换行
            temp_df.columns = temp_df.columns.astype(str).str.strip().str.lower().str.replace('\n', '').str.replace('\r', '')
            temp_df = temp_df.rename(columns=COLUMN_MAP)
            
            req_cols = ['sale_date', 'client_name', 'category', 'sold_qty']
            if all(c in temp_df.columns for c in req_cols):
                temp_df['sale_date'] = pd.to_datetime(temp_df['sale_date'], errors='coerce').dt.strftime('%Y-%m-%d')
                if 'model' not in temp_df.columns: temp_df['model'] = "Unknown"
                temp_df['source_tag'] = source_tag if source_tag else "New_Batch"
                
                conn = get_db_connection()
                temp_df[['sale_date', 'client_name', 'category', 'model', 'sold_qty', 'source_tag']].to_sql("sell_through", conn, if_exists='append', index=False)
                conn.close()
                st.sidebar.success("Data Uploaded!")
                st.rerun()
            else:
                missing = [c for c in req_cols if c not in temp_df.columns]
                st.sidebar.error(f"Mismatch! Missing columns: {missing}")
        except Exception as e: 
            st.sidebar.error(f"Error: {e}")

# ==========================================
# 2. 核心分析逻辑
# ==========================================
st.title("📈 IRAQ ST CRM ANALYSIS")

conn = get_db_connection()
raw_df = pd.read_sql("SELECT * FROM sell_through", conn)
conn.close()

if raw_df.empty:
    st.info("👈 Please upload data to activate the analysis.")
else:
    raw_df['sale_date'] = pd.to_datetime(raw_df['sale_date'], errors='coerce')
    raw_df = raw_df.dropna(subset=['sale_date'])
    
    st.markdown('<div class="filter-card">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    sel_cats = c1.multiselect("Category", sorted(raw_df['category'].fillna('Unknown').unique()), default=raw_df['category'].fillna('Unknown').unique())
    sel_clients = c2.multiselect("Clients", sorted(raw_df['client_name'].fillna('Unknown').unique()), default=raw_df['client_name'].fillna('Unknown').unique())
    time_gran = c3.selectbox("Time Granularity", ["Monthly", "Quarterly"])
    res_code = 'M' if time_gran == "Monthly" else 'Q'
    st.markdown('</div>', unsafe_allow_html=True)

    f_df = raw_df[raw_df['category'].isin(sel_cats) & raw_df['client_name'].isin(sel_clients)].copy()

    if not f_df.empty:
        # KPI 展示
        k1, k2, k3 = st.columns(3)
        k1.markdown(f'<div class="kpi-card"><div class="kpi-title">Total Volume</div><div class="kpi-value">{f_df["sold_qty"].sum():,.0f}</div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="kpi-card"><div class="kpi-title">Active Resellers</div><div class="kpi-value">{f_df["client_name"].nunique()}</div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="kpi-card"><div class="kpi-title">Order Count</div><div class="kpi-value">{len(f_df):,.0f}</div></div>', unsafe_allow_html=True)

        tab1, tab2, tab3 = st.tabs(["🌍 Market Review", "📋 Advanced CRM Matrix", "⚠️ Decline Alert"])

        with tab1:
            col_l, col_r = st.columns([1.5, 1])
            with col_l:
                st.markdown("#### Market Sales Trend")
                trend = f_df.groupby([f_df['sale_date'].dt.to_period(res_code).astype(str), 'category'])['sold_qty'].sum().reset_index()
                st.plotly_chart(px.line(trend, x='sale_date', y='sold_qty', color='category', markers=True, color_discrete_sequence=[BRAND_COLOR, DARK_COLOR, "#94a3b8"]), use_container_width=True)
            
            with col_r:
                st.markdown("#### Overall Mix (Inv vs Bat)")
                # 💡 核物理级防崩溃：全新且绝对安全的饼图生成方式
                market_source = f_df[f_df['category'].fillna('').str.contains('Inverter|Battery', case=False)].copy()
                
                if len(market_source) > 0:
                    # 使用纯 Python 列表，绝对不会触发 DataFrame 列报错
                    clean_types = ['Inverter' if 'inv' in str(c).lower() else 'Battery' for c in market_source['category']]
                    
                    # 凭空捏造一个干净的数据框来画图，彻底断绝联系
                    safe_pie_df = pd.DataFrame({
                        'Product_Type': clean_types,
                        'Qty': market_source['sold_qty'].values
                    })
                    pie_summary = safe_pie_df.groupby('Product_Type', as_index=False)['Qty'].sum()
                    
                    st.plotly_chart(px.pie(pie_summary, values='Qty', names='Product_Type', hole=0.5, color='Product_Type', color_discrete_map={'Inverter': DARK_COLOR, 'Battery': BRAND_COLOR}), use_container_width=True)
                else:
                    st.info("No Inv/Bat data found for ratio chart.")
            
            st.divider()
            st.markdown("#### Monthly Detailed Performance Table")
            monthly_tbl = f_df.groupby([f_df['sale_date'].dt.to_period('M').astype(str), 'category'])['sold_qty'].sum().unstack(fill_value=0)
            monthly_tbl['Total'] = monthly_tbl.sum(axis=1)
            try:
                st.dataframe(monthly_tbl.style.format('{:,.0f}').background_gradient(cmap='GnBu', axis=0), use_container_width=True)
            except Exception:
                st.dataframe(monthly_tbl.style.format('{:,.0f}'), use_container_width=True)

        with tab2:
            st.markdown("### 📋 Executive CRM: Model-Time Matrix")
            crm_df = f_df[f_df['category'].fillna('').str.contains('Inverter|Battery', case=False)].copy()
            
            if not crm_df.empty:
                # 极度安全的重命名和配比逻辑
                crm_df['Product_Type'] = ['Inverter' if 'inv' in str(c).lower() else 'Battery' for c in crm_df['category']]
                
                # 总体排名
                client_rank = crm_df.groupby('client_name')['sold_qty'].sum().sort_values(ascending=False).reset_index()
                client_rank.columns = ['Client', 'Total Inv & Bat Volume']
                st.dataframe(client_rank.style.format({'Total Inv & Bat Volume': '{:,.0f}'}), use_container_width=True)
                
                st.markdown("---")
                for client in client_rank['Client'].unique()[:15]:
                    with st.expander(f"🏢 {client} | Deep-Dive Model Purchase History"):
                        c_detail = crm_df[crm_df['client_name'] == client].copy()
                        c_detail['Period'] = c_detail['sale_date'].dt.to_period(res_code).astype(str)
                        # 确保 Model 在左侧，Period 在上方
                        matrix = c_detail.pivot_table(index='model', columns='Period', values='sold_qty', aggfunc='sum', fill_value=0)
                        try:
                            st.dataframe(matrix.style.format('{:,.0f}').background_gradient(cmap='GnBu', axis=1), use_container_width=True)
                        except Exception:
                            st.dataframe(matrix.style.format('{:,.0f}'), use_container_width=True)
            else:
                st.info("No CRM data found.")

        with tab3:
            st.markdown("### 🚨 Churn & Decline Alert")
            p_df = f_df.groupby(['client_name', f_df['sale_date'].dt.to_period(res_code).astype(str)])['sold_qty'].sum().unstack(fill_value=0)
            if len(p_df.columns) >= 2:
                curr, prev = p_df.columns[-1], p_df.columns[-2]
                p_df['Drop'] = p_df[curr] - p_df[prev]
                decline = p_df[p_df['Drop'] < 0].sort_values('Drop')
                if not decline.empty:
                    st.error(f"Decline Alert: Volume drop in {curr} vs {prev}")
                    st.dataframe(decline[['Drop']].style.format('{:,.0f}'), use_container_width=True)
            else: st.info("Need at least 2 time periods for churn radar.")
