import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# ==========================================
# 0. 页面配置与 UI 样式
# ==========================================
st.set_page_config(page_title="Iraq Executive CRM & BI", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { font-family: 'Times New Roman', Times, serif; background-color: #f8fafc; }
    .stButton>button { background-color: #0f172a; color: white; border-radius: 6px; border: none; font-weight: bold; }
    .stButton>button:hover { background-color: #334155; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(15,23,42,0.3); }
    .filter-card { background-color: white; padding: 20px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 25px; }
    .kpi-card { background-color: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); border-top: 4px solid #0f172a; text-align: center; }
    .kpi-title { font-size: 0.9rem; color: #64748b; font-weight: bold; text-transform: uppercase; }
    .kpi-value { font-size: 2rem; color: #0f172a; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

# 💡 防崩溃升级 4：更换全新数据库名，彻底避开云端缓存
DB_NAME = 'marsriva_iraq_final_secure_v1.db'

def get_db_connection():
    return sqlite3.connect(DB_NAME, timeout=10, check_same_thread=False)

def init_db():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS sell_through (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     sale_date DATE, client_name TEXT, category TEXT, model TEXT, sold_qty REAL, source_tag TEXT)''')
        conn.commit()
    except Exception as e:
        st.error(f"Database Initialization Error: {e}")
    finally:
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

# 💡 防崩溃升级 1：绝对安全的清空逻辑 (只删数据不删表，杜绝 no such table)
if st.sidebar.button("🗑️ Clear All Data (Reset System)", type="primary", use_container_width=True):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("DELETE FROM sell_through")
        conn.commit()
        conn.close()
        st.sidebar.success("System Reset & Database Cleared!")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Clear Error: {e}")

st.sidebar.markdown("---")

# 💡 防崩溃升级 3：专属表单导入 (防止网络延迟导致按钮状态消失)
with st.sidebar.form("data_import_form", clear_on_submit=True):
    st.markdown("### 📥 Import Data")
    source_tag = st.text_input("Batch Name", placeholder="e.g., Q2_Sales")
    uploaded_file = st.file_uploader("Upload Excel/CSV", type=["xlsx", "csv"])
    submit_btn = st.form_submit_button("Confirm Import ✔️")

    if submit_btn and uploaded_file:
        try:
            temp_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            temp_df = temp_df.rename(columns=COLUMN_MAP)

            if 'model' not in temp_df.columns: temp_df['model'] = "Unknown"

            req_cols = ['sale_date', 'client_name', 'category', 'sold_qty']
            missing_cols = [c for c in req_cols if c not in temp_df.columns]

            if not missing_cols:
                # 容错：遇到乱码日期不报错，直接跳过
                temp_df['sale_date'] = pd.to_datetime(temp_df['sale_date'], errors='coerce').dt.strftime('%Y-%m-%d')
                temp_df['source_tag'] = source_tag if source_tag else "Batch"
                
                conn = get_db_connection()
                temp_df[['sale_date', 'client_name', 'category', 'model', 'sold_qty', 'source_tag']].to_sql("sell_through", conn, if_exists='append', index=False)
                conn.close()
                st.success("Data Imported Successfully!")
                st.rerun()
            else:
                st.error(f"Missing columns! Ensure your file has: {req_cols}")
        except Exception as e:
            st.error(f"Error during file processing: {e}")

# ==========================================
# 2. 核心分析逻辑
# ==========================================
st.title("📈 Iraq Executive BI & CRM Radar")

# 读取数据库 (加入终极异常兜底)
try:
    conn = get_db_connection()
    raw_df = pd.read_sql("SELECT * FROM sell_through", conn)
    conn.close()
except Exception as e:
    st.error(f"Failed to read database: {e}")
    raw_df = pd.DataFrame() 

if raw_df.empty:
    st.info("👈 System is ready. Please upload your sales data via the sidebar to activate the dashboard.")
else:
    raw_df['sale_date'] = pd.to_datetime(raw_df['sale_date'], errors='coerce')
    raw_df = raw_df.dropna(subset=['sale_date']) # 自动剔除损坏的日期
    
    st.markdown('<div class="filter-card">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    sel_cats = c1.multiselect("Category Filter", sorted(raw_df['category'].dropna().unique()), default=raw_df['category'].dropna().unique())
    sel_clients = c2.multiselect("Client Filter", sorted(raw_df['client_name'].dropna().unique()), default=raw_df['client_name'].dropna().unique())
    time_gran = c3.selectbox("Time Resolution", ["Monthly", "Quarterly"])
    res_code = 'M' if time_gran == "Monthly" else 'Q'
    st.markdown('</div>', unsafe_allow_html=True)

    f_df = raw_df[raw_df['category'].isin(sel_cats) & raw_df['client_name'].isin(sel_clients)].copy()

    if not f_df.empty:
        total_vol = f_df['sold_qty'].sum()
        active_c = f_df['client_name'].nunique()
        mom_df = f_df.groupby(f_df['sale_date'].dt.to_period('M'))['sold_qty'].sum()
        curr_qty = mom_df.iloc[-1] if not mom_df.empty else 0
        prev_qty = mom_df.iloc[-2] if len(mom_df) > 1 else 0
        diff = curr_qty - prev_qty
        
        k1, k2, k3, k4 = st.columns(4)
        k1.markdown(f'<div class="kpi-card"><div class="kpi-title">Total Volume</div><div class="kpi-value">{total_vol:,.0f}</div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="kpi-card"><div class="kpi-title">Active Clients</div><div class="kpi-value">{active_c}</div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="kpi-card"><div class="kpi-title">Latest Vol.</div><div class="kpi-value">{curr_qty:,.0f}</div></div>', unsafe_allow_html=True)
        k4.markdown(f'<div class="kpi-card"><div class="kpi-title">MoM Change</div><div class="kpi-value">{diff:+,.0f}</div></div>', unsafe_allow_html=True)

        tab1, tab2, tab3, tab4 = st.tabs(["🌍 Market Overview", "📋 Advanced CRM Matrix", "⚠️ Decline Alert", "📈 Product Analysis"])

        with tab1:
            trend_df = f_df.groupby([f_df['sale_date'].dt.to_period(res_code).astype(str), 'category'])['sold_qty'].sum().reset_index()
            fig = px.line(trend_df, x='sale_date', y='sold_qty', color='category', markers=True, template="plotly_white")
            fig.update_layout(xaxis_title="Time", yaxis_title="Volume Sold")
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.markdown("### 📊 Client Deployment Matrix (Inv vs Bat)")
            crm_df = f_df[f_df['category'].str.contains('Inverter|Battery', case=False, na=False)].copy()
            
            if not crm_df.empty:
                crm_df['Type'] = crm_df['category'].apply(lambda x: 'Inverter' if 'inv' in str(x).lower() else 'Battery')
                
                client_pivot = crm_df.groupby(['client_name', 'Type'])['sold_qty'].sum().unstack(fill_value=0)
                if 'Inverter' not in client_pivot.columns: client_pivot['Inverter'] = 0
                if 'Battery' not in client_pivot.columns: client_pivot['Battery'] = 0
                
                client_pivot['Total'] = client_pivot['Inverter'] + client_pivot['Battery']
                client_pivot = client_pivot.sort_values('Total', ascending=False)
                client_pivot['Ratio (1:X)'] = client_pivot.apply(lambda r: f"1:{round(r['Battery']/r['Inverter'],1)}" if r['Inverter']>0 else "N/A", axis=1)
                
                # 💡 防崩溃升级 2：绝对安全的渐变色护盾。如果没有包，自动降级为白底黑字，绝不报错
                try:
                    st.dataframe(client_pivot.style.format('{:,.0f}', subset=['Inverter', 'Battery', 'Total']).background_gradient(cmap='Blues', subset=['Total']), use_container_width=True)
                except Exception:
                    st.dataframe(client_pivot.style.format('{:,.0f}', subset=['Inverter', 'Battery', 'Total']), use_container_width=True)
                
                st.divider()
                st.markdown("#### 🔍 Double-click expander for Client Deep-Dive")
                for client in client_pivot.index[:15]: 
                    with st.expander(f"Detail: {client} (Total: {client_pivot.loc[client, 'Total']:,.0f})"):
                        c_detail = crm_df[crm_df['client_name'] == client].copy()
                        c_detail['Period'] = c_detail['sale_date'].dt.to_period(res_code).astype(str)
                        
                        col_p, col_t = st.columns([1, 2])
                        with col_p:
                            pie_data = c_detail.groupby('Type')['sold_qty'].sum().reset_index()
                            pie = px.pie(pie_data, values='sold_qty', names='Type', color='Type', hole=0.5, color_discrete_map={'Inverter':'#0f172a','Battery':'#00B2A9'})
                            pie.update_layout(showlegend=False, height=200, margin=dict(t=0,b=0,l=0,r=0))
                            st.plotly_chart(pie, use_container_width=True, key=f"pie_{client}")
                        with col_t:
                            model_pv = c_detail.pivot_table(index='Period', columns='model', values='sold_qty', aggfunc='sum', fill_value=0)
                            try:
                                st.dataframe(model_pv.style.format('{:,.0f}').background_gradient(cmap='Blues'), use_container_width=True)
                            except Exception:
                                st.dataframe(model_pv.style.format('{:,.0f}'), use_container_width=True)
            else:
                st.info("No Inverter or Battery sales data found in the current selection.")

        with tab3:
            st.markdown("### 🚨 Churn & Decline Radar")
            p_df = f_df.groupby(['client_name', f_df['sale_date'].dt.to_period(res_code).astype(str)])['sold_qty'].sum().unstack(fill_value=0)
            if len(p_df.columns) >= 2:
                curr, prev = p_df.columns[-1], p_df.columns[-2]
                p_df['Drop'] = p_df[curr] - p_df[prev]
                decline = p_df[p_df['Drop'] < 0].sort_values('Drop')
                
                if not decline.empty:
                    st.markdown(f"Comparing **{curr}** against **{prev}**")
                    st.dataframe(decline[['Drop']].style.format('{:,.0f}').map(lambda x: 'color: red; font-weight: bold;'), use_container_width=True)
                    fig_alert = px.bar(decline.reset_index().head(10), x='Drop', y='client_name', orientation='h', color_discrete_sequence=['#ef4444'])
                    fig_alert.update_layout(xaxis_title="Volume Drop", yaxis_title="Client")
                    st.plotly_chart(fig_alert, use_container_width=True)
                else:
                    st.success("Great news! No clients showed a decline in volume.")
            else: 
                st.info("Need at least 2 time periods to calculate decline.")

        with tab4:
            st.markdown("### 🏆 Top 20 Models Overall")
            top_models = f_df.groupby('model')['sold_qty'].sum().nlargest(20).reset_index()
            fig_bar = px.bar(top_models, x='sold_qty', y='model', orientation='h', text_auto='.2s', color_discrete_sequence=['#0f172a'])
            fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Total Quantity", yaxis_title="Model")
            st.plotly_chart(fig_bar, use_container_width=True)
