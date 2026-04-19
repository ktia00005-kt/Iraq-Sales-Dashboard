import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# ==========================================
# 0. 页面配置与 UI 样式 (Marsriva 品牌色定制)
# ==========================================
st.set_page_config(page_title="Iraq Executive BI & CRM", layout="wide", initial_sidebar_state="expanded")

# 品牌色定义：Logo 青色 (#00B2A9), 深色 (#0f172a)
BRAND_COLOR = "#00B2A9"
DARK_COLOR = "#0f172a"

st.markdown(f"""
<style>
    .stApp {{ font-family: 'Times New Roman', Times, serif; background-color: #f8fafc; }}
    .stButton>button {{ background-color: {DARK_COLOR}; color: white; border-radius: 6px; border: none; font-weight: bold; }}
    .stButton>button:hover {{ background-color: #334155; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(15,23,42,0.3); }}
    .filter-card {{ background-color: white; padding: 20px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 25px; }}
    .kpi-card {{ background-color: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); border-top: 4px solid {BRAND_COLOR}; text-align: center; }}
    .kpi-title {{ font-size: 0.9rem; color: #64748b; font-weight: bold; text-transform: uppercase; }}
    .kpi-value {{ font-size: 2rem; color: {DARK_COLOR}; font-weight: 800; }}
</style>
""", unsafe_allow_html=True)

DB_NAME = 'marsriva_iraq_v11_master.db'

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

COLUMN_MAP = {
    'Date': 'sale_date', 'sale_date': 'sale_date', '日期': 'sale_date',
    'Customer / Supplier en': 'client_name', 'Client': 'client_name', 'client_name': 'client_name', 'Customer / Supplier': 'client_name', '客户': 'client_name',
    'category': 'category', 'Category': 'category', '类目': 'category',
    'Item Name': 'model', 'Model': 'model', 'model': 'model', '型号': 'model',
    'Sales Quantity': 'sold_qty', 'Quantity': 'sold_qty', 'sold_qty': 'sold_qty', 'Qty': 'sold_qty', '销量': 'sold_qty'
}

# ==========================================
# 1. 全局侧边栏 (管理中心)
# ==========================================
st.sidebar.markdown("## ⚙️ Management")

if st.sidebar.button("🗑️ Clear All Data (Reset System)", type="primary", use_container_width=True):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM sell_through")
    conn.commit()
    conn.close()
    st.sidebar.success("Database Cleared!")
    st.rerun()

st.sidebar.markdown("---")

with st.sidebar.form("data_import_form", clear_on_submit=True):
    st.markdown("### 📥 Import Data")
    source_tag = st.text_input("Batch Name", placeholder="e.g., Iraq_April_Sales")
    uploaded_file = st.file_uploader("Upload Excel/CSV", type=["xlsx", "csv"])
    submit_btn = st.form_submit_button("Confirm Import ✔️")

    if submit_btn and uploaded_file:
        try:
            temp_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            temp_df = temp_df.rename(columns=COLUMN_MAP)
            if 'model' not in temp_df.columns: temp_df['model'] = "Unknown"
            req_cols = ['sale_date', 'client_name', 'category', 'sold_qty']
            if all(c in temp_df.columns for c in req_cols):
                temp_df['sale_date'] = pd.to_datetime(temp_df['sale_date'], errors='coerce').dt.strftime('%Y-%m-%d')
                conn = get_db_connection()
                temp_df[['sale_date', 'client_name', 'category', 'model', 'sold_qty', 'source_tag']].to_sql("sell_through", conn, if_exists='append', index=False)
                conn.close()
                st.success("Success!")
                st.rerun()
            else: st.error("Missing columns!")
        except Exception as e: st.error(f"Error: {e}")

# ==========================================
# 2. 主看板逻辑
# ==========================================
st.title("📈 Iraq Executive BI & CRM Radar")

conn = get_db_connection()
raw_df = pd.read_sql("SELECT * FROM sell_through", conn)
conn.close()

if raw_df.empty:
    st.info("👈 Please upload data to begin.")
else:
    raw_df['sale_date'] = pd.to_datetime(raw_df['sale_date'], errors='coerce')
    raw_df = raw_df.dropna(subset=['sale_date'])
    
    st.markdown('<div class="filter-card">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    sel_cats = c1.multiselect("Category Filter", sorted(raw_df['category'].unique()), default=raw_df['category'].unique())
    sel_clients = c2.multiselect("Client Filter", sorted(raw_df['client_name'].unique()), default=raw_df['client_name'].unique())
    time_gran = c3.selectbox("Time Resolution", ["Monthly", "Quarterly"])
    res_code = 'M' if time_gran == "Monthly" else 'Q'
    st.markdown('</div>', unsafe_allow_html=True)

    f_df = raw_df[raw_df['category'].isin(sel_cats) & raw_df['client_name'].isin(sel_clients)].copy()

    if not f_df.empty:
        # KPI 展示
        total_vol = f_df['sold_qty'].sum()
        active_c = f_df['client_name'].nunique()
        mom_df = f_df.groupby(f_df['sale_date'].dt.to_period('M'))['sold_qty'].sum()
        curr_qty = mom_df.iloc[-1] if not mom_df.empty else 0
        
        k1, k2, k3 = st.columns(3)
        k1.markdown(f'<div class="kpi-card"><div class="kpi-title">Market Total Volume</div><div class="kpi-value">{total_vol:,.0f}</div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="kpi-card"><div class="kpi-title">Active Resellers</div><div class="kpi-value">{active_c}</div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="kpi-card"><div class="kpi-title">Latest Mo. Volume</div><div class="kpi-value">{curr_qty:,.0f}</div></div>', unsafe_allow_html=True)

        tab1, tab2, tab3 = st.tabs(["🌍 Market Review", "📋 Advanced CRM Matrix", "⚠️ Decline Alert"])

        # ==========================================
        # TAB 1: Market Review 
        # ==========================================
        with tab1:
            col_m1, col_m2 = st.columns([1.5, 1])
            
            # 1. 总体配比饼图 (💡 这里加了防崩溃保护罩)
            with col_m2:
                st.markdown("#### Overall Purchase Ratio")
                market_crm = f_df[f_df['category'].str.contains('Inverter|Battery', case=False, na=False)].copy()
                if not market_crm.empty:
                    market_crm['Macro Type'] = market_crm['category'].apply(lambda x: 'Inverter' if 'inv' in str(x).lower() else 'Battery')
                    pie_data = market_crm.groupby('Macro Type')['sold_qty'].sum().reset_index()
                    fig_pie = px.pie(pie_data, values='sold_qty', names='Macro Type', hole=0.6, 
                                     color='Macro Type', color_discrete_map={'Inverter': DARK_COLOR, 'Battery': BRAND_COLOR})
                    fig_pie.update_layout(showlegend=True, height=350, margin=dict(t=20, b=20, l=0, r=0))
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("No Inverter or Battery data available for pie chart.")

            # 2. 趋势线 (增加了超多备选颜色，防止多类目崩溃)
            with col_m1:
                st.markdown(f"#### Sales Trajectory ({time_gran})")
                trend_df = f_df.groupby([f_df['sale_date'].dt.to_period(res_code).astype(str), 'category'])['sold_qty'].sum().reset_index()
                color_seq = [BRAND_COLOR, DARK_COLOR, "#64748b", "#cbd5e1", "#38bdf8", "#fbbf24", "#f87171", "#a78bfa"]
                fig_line = px.line(trend_df, x='sale_date', y='sold_qty', color='category', markers=True, 
                                   color_discrete_sequence=color_seq)
                fig_line.update_layout(template="plotly_white", height=350, xaxis_title="", yaxis_title="Units Sold")
                st.plotly_chart(fig_line, use_container_width=True)

            # 3. 月度采购量明细表
            st.divider()
            st.markdown("#### Monthly Sales Volume Data Table")
            monthly_table = f_df.groupby([f_df['sale_date'].dt.to_period('M').astype(str), 'category'])['sold_qty'].sum().unstack(fill_value=0)
            monthly_table['Total'] = monthly_table.sum(axis=1)
            try:
                st.dataframe(monthly_table.style.format('{:,.0f}').background_gradient(cmap='GnBu', axis=0), use_container_width=True)
            except Exception:
                st.dataframe(monthly_table.style.format('{:,.0f}'), use_container_width=True)

        # ==========================================
        # TAB 2: CRM Matrix
        # ==========================================
        with tab2:
            st.markdown("### 📋 Executive CRM: Client Analysis")
            crm_df = f_df[f_df['category'].str.contains('Inverter|Battery', case=False, na=False)].copy()
            
            if not crm_df.empty:
                crm_df['Type'] = crm_df['category'].apply(lambda x: 'Inverter' if 'inv' in str(x).lower() else 'Battery')
                client_pivot = crm_df.groupby(['client_name', 'Type'])['sold_qty'].sum().unstack(fill_value=0)
                if 'Inverter' not in client_pivot.columns: client_pivot['Inverter'] = 0
                if 'Battery' not in client_pivot.columns: client_pivot['Battery'] = 0
                client_pivot['Total'] = client_pivot['Inverter'] + client_pivot['Battery']
                client_pivot = client_pivot.sort_values('Total', ascending=False)
                
                st.dataframe(client_pivot.style.format('{:,.0f}'), use_container_width=True)
                
                st.divider()
                st.markdown("#### 🔍 Client Deep-Dive (Model vs Time Period)")
                for client in client_pivot.index[:12]: 
                    with st.expander(f"🏢 {client} | Detailed Purchase Matrix"):
                        c_detail = crm_df[crm_df['client_name'] == client].copy()
                        c_detail['Period'] = c_detail['sale_date'].dt.to_period(res_code).astype(str)
                        
                        model_matrix = c_detail.pivot_table(index='model', columns='Period', values='sold_qty', aggfunc='sum', fill_value=0)
                        try:
                            st.dataframe(model_matrix.style.format('{:,.0f}').background_gradient(cmap='GnBu', axis=1), use_container_width=True)
                        except Exception:
                            st.dataframe(model_matrix.style.format('{:,.0f}'), use_container_width=True)
            else:
                st.info("No data for Inverter/Battery.")

        # ==========================================
        # TAB 3: Decline Alert
        # ==========================================
        with tab3:
            st.markdown("### 🚨 Churn & Decline Radar")
            p_df = f_df.groupby(['client_name', f_df['sale_date'].dt.to_period(res_code).astype(str)])['sold_qty'].sum().unstack(fill_value=0)
            if len(p_df.columns) >= 2:
                curr, prev = p_df.columns[-1], p_df.columns[-2]
                p_df['Drop'] = p_df[curr] - p_df[prev]
                decline = p_df[p_df['Drop'] < 0].sort_values('Drop')
                if not decline.empty:
                    st.error(f"Clients with decreased volume in {curr} compared to {prev}")
                    st.dataframe(decline[['Drop']].style.format('{:,.0f}'), use_container_width=True)
                    st.plotly_chart(px.bar(decline.reset_index().head(10), x='Drop', y='client_name', orientation='h', color_discrete_sequence=['#ef4444']), use_container_width=True)
            else: st.info("Need more data periods.")
