import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import os

# ==========================================
# 0. Marsriva Executive BI UI (Times New Roman & Slate Grey Edition)
# ==========================================
st.set_page_config(page_title="Iraq Sell Through Performance", layout="wide", initial_sidebar_state="expanded")

# 极致专业的 CSS 样式，修复重叠问题
st.markdown("""
<style>
    .stApp { font-family: 'Times New Roman', Times, serif; background-color: #f8fafc; }
    .stButton>button { background-color: #0f172a; color: white; border-radius: 6px; border: none; font-weight: bold; transition: all 0.3s ease; }
    .stButton>button:hover { background-color: #334155; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(15,23,42,0.3); }
    
    .filter-card { background-color: white; padding: 20px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 20px; }
    
    /* Advanced KPI Cards */
    .kpi-container { display: flex; gap: 15px; margin-bottom: 25px; }
    .kpi-card { flex: 1; background-color: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); border-top: 4px solid #0f172a; transition: 0.3s; }
    .kpi-card:hover { transform: translateY(-4px); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }
    .kpi-title { font-size: 0.95rem; color: #64748b; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 5px; }
    .kpi-value { font-size: 2.2rem; color: #0f172a; font-weight: 800; }
    
    .kpi-trend-up { color: #00B2A9; font-weight: bold; font-size: 1rem; margin-top: 5px; }
    .kpi-trend-down { color: #ef4444; font-weight: bold; font-size: 1rem; margin-top: 5px; } 
</style>
""", unsafe_allow_html=True)

def format_number(num):
    if num >= 1_000_000: return f"{num/1_000_000:.1f}M"
    elif num >= 1_000: return f"{num/1_000:.1f}K"
    else: return f"{int(num)}"

def get_db_connection():
    return sqlite3.connect('marsriva_iraq_final_pro.db', check_same_thread=False)

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
    'sale_date': 'sale_date', 'Date': 'sale_date', '日期': 'sale_date',
    'client_name': 'client_name', 'Client': 'client_name', '客户': 'client_name',
    'category': 'category', 'Category': 'category', '类目': 'category',
    'model': 'model', 'Model': 'model', '型号': 'model',
    'sold_qty': 'sold_qty', 'Quantity': 'sold_qty', '销量': 'sold_qty', 'Sales Quantity': 'sold_qty'
}

# ==========================================
# 1. Global Sidebar (Data Management & Filters)
# ==========================================
st.sidebar.markdown("### 🛠️ System Control Panel")

# --- 清空数据 ---
if st.sidebar.button("🗑️ Clear All Database Data", type="primary"):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM sell_through")
    conn.commit()
    conn.close()
    st.sidebar.success("Database Cleared!")
    st.rerun()

st.sidebar.markdown("---")

# --- 上传数据 ---
st.sidebar.markdown("### 📥 Import Data")
source_tag = st.sidebar.text_input("Data Batch Tag (Optional)", placeholder="e.g., Q2_Sales")
uploaded_file = st.sidebar.file_uploader("Upload Excel/CSV", type=["xlsx", "csv"])

if uploaded_file:
    try:
        temp_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        temp_df = temp_df.rename(columns=COLUMN_MAP)
        
        for col in ['model']:
            if col not in temp_df.columns: temp_df[col] = "Unknown"
            
        req_cols = ['sale_date', 'client_name', 'category', 'sold_qty']
        missing_reqs = [c for c in req_cols if c not in temp_df.columns]
        
        if missing_reqs:
            st.sidebar.error(f"Missing columns: {missing_reqs}")
        else:
            temp_df['sale_date'] = pd.to_datetime(temp_df['sale_date']).dt.strftime('%Y-%m-%d')
            st.sidebar.success(f"{len(temp_df)} records ready.")
            if st.sidebar.button("Execute Import Data ✔️"):
                temp_df['source_tag'] = source_tag if source_tag else "Imported_Batch"
                conn = get_db_connection()
                db_cols = ['sale_date', 'client_name', 'category', 'model', 'sold_qty', 'source_tag']
                cols_to_save = [c for c in db_cols if c in temp_df.columns]
                temp_df[cols_to_save].to_sql("sell_through", conn, if_exists='append', index=False)
                conn.close()
                st.rerun()
    except Exception as e:
        st.sidebar.error(f"Error: {e}")

st.sidebar.markdown("---")

# ==========================================
# 2. Main Dashboard Layout & Logic
# ==========================================
st.title("📈 Executive Performance & CRM Dashboard")

conn = get_db_connection()
raw_df = pd.read_sql("SELECT * FROM sell_through", conn)
conn.close()

if raw_df.empty:
    st.info("👈 System is ready. Please upload your sales data via the left sidebar to begin analysis.")
else:
    raw_df['sale_date'] = pd.to_datetime(raw_df['sale_date'])
    
    # --- Global Filters (放到主页面顶部，更清晰) ---
    st.markdown('<div class="filter-card">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        all_cats = sorted(raw_df['category'].dropna().unique())
        sel_cats = st.multiselect("Category Filter", all_cats, default=all_cats)
    with c2:
        all_clients = sorted(raw_df['client_name'].dropna().unique())
        sel_clients = st.multiselect("Client Filter", all_clients, default=all_clients)
    with c3:
        time_gran = st.selectbox("Time Resolution", ["Monthly", "Quarterly"])
        res_code = 'M' if time_gran == "Monthly" else 'Q'
    st.markdown('</div>', unsafe_allow_html=True)

    f_df = raw_df[raw_df['category'].isin(sel_cats) & raw_df['client_name'].isin(sel_clients)].copy()

    # --- Executive KPIs ---
    if not f_df.empty:
        unique_months = f_df['sale_date'].dt.to_period('M').nunique()
        avg_monthly_sales = f_df['sold_qty'].sum() / unique_months if unique_months > 0 else 0
        
        mom_df = f_df.groupby(f_df['sale_date'].dt.to_period('M'))['sold_qty'].sum()
        curr_qty = mom_df.iloc[-1] if not mom_df.empty else 0
        prev_qty = mom_df.iloc[-2] if len(mom_df) > 1 else 0
        mo_diff = curr_qty - prev_qty
        diff_pct = (mo_diff / prev_qty * 100) if prev_qty > 0 else 0
        
        d_class = "kpi-trend-down" if mo_diff < 0 else "kpi-trend-up"
        d_arrow = "▼" if mo_diff < 0 else "▲"
        
        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-card"><div class="kpi-title">Total Unit Volume</div><div class="kpi-value">{format_number(f_df['sold_qty'].sum())}</div></div>
            <div class="kpi-card"><div class="kpi-title">Active Resellers</div><div class="kpi-value">{f_df['client_name'].nunique()}</div></div>
            <div class="kpi-card"><div class="kpi-title">Avg Monthly Volume</div><div class="kpi-value">{format_number(avg_monthly_sales)}</div></div>
            <div class="kpi-card"><div class="kpi-title">Latest MoM Trend</div><div class="kpi-value">{format_number(abs(mo_diff))}</div><div class="{d_class}">{d_arrow} {abs(diff_pct):.1f}% vs Prev</div></div>
        </div>
        """, unsafe_allow_html=True)

        # ==========================================
        # 3. Deep Analysis Tabs
        # ==========================================
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🌍 Market Overview", 
            "📊 Growth Variance", 
            "📈 Product Trend", 
            "📋 Advanced CRM (Inv & Bat)", 
            "⚠️ Churn & Decline Alert"
        ])
        
        # --- TAB 1 & 2 & 3 (保留基础分析) ---
        with tab1:
            st.markdown(f"### Market Trajectory ({time_gran})")
            trend_df = f_df.groupby([f_df['sale_date'].dt.to_period(res_code).astype(str), 'category'])['sold_qty'].sum().reset_index()
            fig_line = px.line(trend_df, x='sale_date', y='sold_qty', color='category', markers=True, color_discrete_sequence=px.colors.qualitative.Bold)
            fig_line.update_layout(template="plotly_white", xaxis_title="", yaxis_title="Volume", font=dict(family="Times New Roman"))
            st.plotly_chart(fig_line, use_container_width=True)
            
        with tab2:
            st.markdown(f"### Performance Variance ({time_gran})")
            g_df = f_df.groupby(['client_name', f_df['sale_date'].dt.to_period(res_code).astype(str)])['sold_qty'].sum().reset_index()
            g_df['Prev_Qty'] = g_df.groupby('client_name')['sold_qty'].shift(1)
            g_df['Net Change'] = g_df['sold_qty'] - g_df['Prev_Qty']
            if not g_df.dropna().empty:
                latest_p = g_df['sale_date'].max()
                g_latest = g_df[g_df['sale_date'] == latest_p].dropna().copy()
                g_latest['Color'] = g_latest['Net Change'].apply(lambda x: '#ef4444' if x < 0 else '#00B2A9')
                fig_bar = px.bar(g_latest.assign(Abs=g_latest['Net Change'].abs()).nlargest(15, 'Abs'), 
                                 x='Net Change', y='client_name', color='Color', orientation='h', color_discrete_map="identity")
                fig_bar.update_layout(template="plotly_white", yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("Insufficient periods for variance.")

        with tab3:
            c_t1, c_t2 = st.columns(2)
            with c_t1: t_cat = st.selectbox("Category deep-dive", ["All"] + sorted(f_df['category'].unique().tolist()))
            with c_t2: t_mod = st.selectbox("Model deep-dive", ["All"] + sorted(f_df['model'].dropna().unique().tolist()))
            dd_df = f_df.copy()
            if t_cat != "All": dd_df = dd_df[dd_df['category'] == t_cat]
            if t_mod != "All": dd_df = dd_df[dd_df['model'] == t_mod]
            if not dd_df.empty:
                trend_line = dd_df.groupby(dd_df['sale_date'].dt.to_period(res_code).astype(str))['sold_qty'].sum().reset_index()
                st.plotly_chart(px.area(trend_line, x='sale_date', y='sold_qty', markers=True, color_discrete_sequence=['#0f172a']), use_container_width=True)

        # ==========================================
        # ★ TAB 4: ADVANCED CRM (Inverter vs Battery Ratio)
        # ==========================================
        with tab4:
            st.markdown("### 📋 Executive CRM: Inverter & Battery Matrix")
            st.caption("Ranking clients by total Inverter + Battery volume, analyzing their deployment ratio and model breakdown.")
            
            # 智能提取包含 Inverter 或 Battery 的类目
            crm_df = f_df[f_df['category'].str.contains('Inverter|Battery', case=False, na=False)].copy()
            
            if not crm_df.empty:
                # 为了统一配比，把带有 Inverter 的归为 Inverter，带有 Battery 的归为 Battery
                crm_df['Macro Category'] = crm_df['category'].apply(lambda x: 'Inverter' if 'inverter' in str(x).lower() else ('Battery' if 'battery' in str(x).lower() else 'Other'))
                crm_df = crm_df[crm_df['Macro Category'] != 'Other']
                
                # 透视客户总量
                client_stats = crm_df.groupby(['client_name', 'Macro Category'])['sold_qty'].sum().unstack(fill_value=0)
                if 'Inverter' not in client_stats.columns: client_stats['Inverter'] = 0
                if 'Battery' not in client_stats.columns: client_stats['Battery'] = 0
                
                # 计算排名和比例
                client_stats['Total Volume'] = client_stats['Inverter'] + client_stats['Battery']
                client_stats = client_stats.sort_values('Total Volume', ascending=False)
                grand_total = client_stats['Total Volume'].sum()
                client_stats['Share of Total (%)'] = ((client_stats['Total Volume'] / grand_total) * 100).round(2)
                
                # 配比逻辑 (Inv : Bat)
                def calc_ratio(inv, bat):
                    if inv == 0 and bat > 0: return "0 : All Battery"
                    if bat == 0 and inv > 0: return "All Inverter : 0"
                    if inv == 0 and bat == 0: return "0 : 0"
                    return f"1 : {round(bat/inv, 1)}"
                
                client_stats['Deployment Ratio (Inv : Bat)'] = client_stats.apply(lambda row: calc_ratio(row['Inverter'], row['Battery']), axis=1)
                
                # 展示排行榜
                st.dataframe(
                    client_stats[['Inverter', 'Battery', 'Total Volume', 'Deployment Ratio (Inv : Bat)', 'Share of Total (%)']].style.format({
                        'Inverter': '{:,.0f}', 'Battery': '{:,.0f}', 'Total Volume': '{:,.0f}', 'Share of Total (%)': '{:.2f}%'
                    }), use_container_width=True
                )
                
                st.markdown("---")
                st.markdown("#### 🔍 Client Deep-Dive (Model & Time Breakdown)")
                
                # 生成展开折叠面板进行穿透分析
                for idx, row in client_stats.iterrows():
                    client = idx
                    inv_qty = row['Inverter']
                    bat_qty = row['Battery']
                    total_qty = row['Total Volume']
                    share = row['Share of Total (%)']
                    
                    with st.expander(f"🏢 {client} | Total: {total_qty:,.0f} units | Share: {share}%"):
                        col_p1, col_p2 = st.columns([1, 2.5])
                        
                        client_detail_df = crm_df[crm_df['client_name'] == client]
                        
                        with col_p1:
                            st.markdown("**Purchasing Ratio**")
                            # 画个饼状图展示比例
                            pie_df = pd.DataFrame({'Cat': ['Inverter', 'Battery'], 'Qty': [inv_qty, bat_qty]})
                            fig_pie = px.pie(pie_df, values='Qty', names='Cat', hole=0.6, color='Cat', 
                                             color_discrete_map={'Inverter':'#0f172a', 'Battery':'#00B2A9'})
                            fig_pie.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=250)
                            st.plotly_chart(fig_pie, use_container_width=True)
                            
                        with col_p2:
                            st.markdown(f"**Model Breakdown ({time_gran})**")
                            # 生成时间和型号的透视表
                            client_detail_df['Period'] = client_detail_df['sale_date'].dt.to_period(res_code).astype(str)
                            pivot_model = client_detail_df.pivot_table(index='Period', columns='model', values='sold_qty', aggfunc='sum', fill_value=0)
                            # 格式化
                            format_dict = {col: '{:,.0f}' for col in pivot_model.columns}
                            st.dataframe(pivot_model.style.format(format_dict).background_gradient(cmap='Blues'), use_container_width=True)
            else:
                st.info("No Inverter or Battery sales data found to build CRM.")

        # ==========================================
        # ★ TAB 5: CHURN & DECLINE ALERT
        # ==========================================
        with tab5:
            st.markdown("### ⚠️ Drop-off & Churn Radar")
            st.caption("Automatically detects clients with significant drop in purchase volume between the last two periods.")
            
            alert_df = f_df.copy()
            alert_df['Period'] = alert_df['sale_date'].dt.to_period(res_code).astype(str)
            
            # 按客户和周期汇总
            period_stats = alert_df.groupby(['client_name', 'Period'])['sold_qty'].sum().unstack(fill_value=0)
            
            periods = sorted(period_stats.columns.tolist())
            if len(periods) >= 2:
                current_p = periods[-1]
                previous_p = periods[-2]
                
                st.markdown(f"**Comparing Period:** `{current_p}` vs `{previous_p}`")
                
                period_stats['Drop Volume'] = period_stats[current_p] - period_stats[previous_p]
                period_stats['Drop %'] = ((period_stats['Drop Volume'] / period_stats[previous_p].replace(0, pd.NA)) * 100)
                
                # 筛选出下跌的客户 (Drop Volume < 0)
                decline_df = period_stats[period_stats['Drop Volume'] < 0].copy()
                
                if not decline_df.empty:
                    # 按照跌幅最大的排序
                    decline_df = decline_df.sort_values('Drop Volume', ascending=True)
                    
                    c_a1, c_a2 = st.columns([1, 1.5])
                    with c_a1:
                        # 用红色条形图展示掉队的客户
                        fig_alert = px.bar(decline_df.reset_index().head(10), x='Drop Volume', y='client_name', 
                                           orientation='h', color_discrete_sequence=['#ef4444'], text_auto='.0f',
                                           title="Top 10 Volume Drops")
                        fig_alert.update_layout(template="plotly_white", yaxis={'categoryorder':'total ascending'})
                        st.plotly_chart(fig_alert, use_container_width=True)
                        
                    with c_a2:
                        # 展示详细数据表
                        show_cols = [previous_p, current_p, 'Drop Volume', 'Drop %']
                        format_dict = {previous_p: '{:,.0f}', current_p: '{:,.0f}', 'Drop Volume': '{:,.0f}', 'Drop %': '{:.1f}%'}
                        
                        def highlight_red(val):
                            return 'color: #ef4444; font-weight: bold;' if (isinstance(val, (int, float)) and val < 0) else ''
                            
                        st.dataframe(decline_df[show_cols].style.map(highlight_red, subset=['Drop Volume', 'Drop %']).format(format_dict), 
                                     use_container_width=True)
                else:
                    st.success(f"Great news! No clients showed a decline in volume from {previous_p} to {current_p}. 🎉")
            else:
                st.info("Require at least two time periods to detect drop-offs.")
