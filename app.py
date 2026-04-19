import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import os

# ==========================================
# 0. Marsriva Executive BI UI 
# ==========================================
st.set_page_config(page_title="Iraq Sell Through Performance", layout="wide", initial_sidebar_state="collapsed")

# 修复了导致重叠的 CSS，去除了全局 * 选择器，并保留了核心的高级配色
st.markdown("""
<style>
    .stApp { font-family: 'Times New Roman', Times, serif; background-color: #f1f5f9; }
    .stButton>button { background-color: #00B2A9; color: white; border-radius: 6px; border: none; font-weight: bold; transition: all 0.3s ease; }
    .stButton>button:hover { background-color: #008f87; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,178,169,0.3); }
    
    .filter-card { background-color: white; padding: 20px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 20px; }
    
    /* Advanced KPI Cards */
    .kpi-container { display: flex; gap: 15px; margin-bottom: 25px; }
    .kpi-card { flex: 1; background-color: white; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); border-top: 4px solid #00B2A9; transition: 0.3s; }
    .kpi-card:hover { transform: translateY(-4px); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }
    .kpi-title { font-size: 0.95rem; color: #64748b; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 5px; }
    .kpi-value { font-size: 2.2rem; color: #1e293b; font-weight: 800; }
    
    /* 增长为品牌青色，下降为高级石板灰 */
    .kpi-trend-up { color: #00B2A9; font-weight: bold; font-size: 1rem; margin-top: 5px; }
    .kpi-trend-down { color: #475569; font-weight: bold; font-size: 1rem; margin-top: 5px; } 
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
    # 彻底移除了 power_segment 字段
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
    'sold_qty': 'sold_qty', 'Quantity': 'sold_qty', '销量': 'sold_qty'
}

# ==========================================
# 1. Navigation & Data Loading
# ==========================================
if os.path.exists("Logo-2a.jpg"):
    st.sidebar.image("Logo-2a.jpg", use_container_width=True)
st.sidebar.markdown("---")
menu = st.sidebar.radio("Module", ["📈 Performance Dashboard", "📤 Data Terminal"])

conn = get_db_connection()
raw_df = pd.read_sql("SELECT * FROM sell_through", conn)
conn.close()

# ==========================================
# 2. Performance Dashboard
# ==========================================
if menu == "📈 Performance Dashboard":
    # 替换为原生标题，彻底解决重叠问题
    st.title("📈 Iraq Reseller Sell Through Performance")
    
    if raw_df.empty:
        st.warning("Data terminal is empty. Please navigate to the 'Data Terminal' to upload source files.")
    else:
        raw_df['sale_date'] = pd.to_datetime(raw_df['sale_date'])
        
        # --- Filters ---
        st.markdown('<div class="filter-card">', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            all_cats = sorted(raw_df['category'].dropna().unique())
            sel_cats = st.multiselect("Category", all_cats, default=all_cats)
        with c2:
            all_clients = sorted(raw_df['client_name'].dropna().unique())
            sel_clients = st.multiselect("Clients", all_clients, default=all_clients)
        with c3:
            time_gran = st.selectbox("Resolution", ["Monthly", "Quarterly"])
            res_code = 'M' if time_gran == "Monthly" else 'Q'
        with c4:
            all_sources = raw_df['source_tag'].dropna().unique().tolist()
            sel_sources = st.multiselect("Data Batches", all_sources, default=all_sources)
        st.markdown('</div>', unsafe_allow_html=True)

        f_df = raw_df[raw_df['category'].isin(sel_cats) & raw_df['client_name'].isin(sel_clients) & raw_df['source_tag'].isin(sel_sources)].copy()

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
                <div class="kpi-card"><div class="kpi-title">Total Volume</div><div class="kpi-value">{format_number(f_df['sold_qty'].sum())}</div></div>
                <div class="kpi-card"><div class="kpi-title">Active Resellers</div><div class="kpi-value">{f_df['client_name'].nunique()}</div></div>
                <div class="kpi-card"><div class="kpi-title">Avg Monthly Volume</div><div class="kpi-value">{format_number(avg_monthly_sales)}</div></div>
                <div class="kpi-card"><div class="kpi-title">Latest MoM Trend</div><div class="kpi-value">{format_number(abs(mo_diff))}</div><div class="{d_class}">{d_arrow} {abs(diff_pct):.1f}% vs Prev</div></div>
            </div>
            """, unsafe_allow_html=True)

            # --- Analysis Modules ---
            tab1, tab2, tab3, tab4 = st.tabs(["🌍 Market Overview", "📊 Growth Variance", "📈 Product Trend Deep-Dive", "🏆 Reseller Performance & Remarks"])
            
            # --- TAB 1: Macro Market Overview ---
            with tab1:
                col_m1, col_m2 = st.columns([2.5, 1])
                with col_m1:
                    st.markdown(f"### Market Trajectory ({time_gran})")
                    trend_df = f_df.groupby([f_df['sale_date'].dt.to_period(res_code).astype(str), 'category'])['sold_qty'].sum().reset_index()
                    fig_line = px.line(trend_df, x='sale_date', y='sold_qty', color='category', markers=True,
                                       color_discrete_sequence=['#00B2A9', '#1e293b', '#64748b', '#cbd5e1'])
                    fig_line.update_traces(line_shape='spline', line=dict(width=3), marker=dict(size=8))
                    fig_line.update_layout(template="plotly_white", hovermode="x unified", xaxis_title="", yaxis_title="Volume Sold", legend_title="", font=dict(family="Times New Roman"))
                    st.plotly_chart(fig_line, use_container_width=True)
                
                with col_m2:
                    st.markdown("### Market Share")
                    share_df = f_df.groupby('category')['sold_qty'].sum().reset_index()
                    fig_pie = px.pie(share_df, values='sold_qty', names='category', hole=0.5,
                                     color_discrete_sequence=['#00B2A9', '#1e293b', '#475569', '#94a3b8'])
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    fig_pie.update_layout(showlegend=False, margin=dict(t=30, b=0, l=0, r=0), font=dict(family="Times New Roman"))
                    st.plotly_chart(fig_pie, use_container_width=True)

            # --- TAB 2: Growth & Decline ---
            with tab2:
                st.markdown(f"### Performance Variance ({time_gran})")
                
                g_df = f_df.groupby(['client_name', 'category', f_df['sale_date'].dt.to_period(res_code).astype(str)])['sold_qty'].sum().reset_index()
                g_df.columns = ['Client', 'Category', 'Period', 'Qty']
                g_df['Prev_Qty'] = g_df.groupby(['Client', 'Category'])['Qty'].shift(1)
                g_df['Net Change'] = g_df['Qty'] - g_df['Prev_Qty'].fillna(0)
                g_df = g_df.dropna(subset=['Prev_Qty'])
                
                if not g_df.empty:
                    latest_p = g_df['Period'].max()
                    g_latest = g_df[g_df['Period'] == latest_p].copy()
                    
                    c_v1, c_v2 = st.columns([1, 1.2])
                    with c_v1:
                        st.caption(f"Top Movers for **{latest_p}**")
                        if not g_latest.empty:
                            g_latest['Color'] = g_latest['Net Change'].apply(lambda x: '#475569' if x < 0 else '#00B2A9')
                            top_movers = g_latest.assign(Abs=g_latest['Net Change'].abs()).nlargest(15, 'Abs')
                            fig_bar = px.bar(top_movers, x='Net Change', y='Client', color='Color', orientation='h',
                                             hover_data=['Category', 'Qty'], color_discrete_map="identity")
                            fig_bar.update_layout(template="plotly_white", showlegend=False, yaxis={'categoryorder':'total ascending'}, xaxis_title="Net Gain/Loss", font=dict(family="Times New Roman"))
                            st.plotly_chart(fig_bar, use_container_width=True)
                    
                    with c_v2:
                        st.caption("Full Variance Ledger")
                        def highlight_variance(val):
                            if isinstance(val, (int, float)):
                                if val < 0: return 'color: #475569; font-weight: bold;'
                                elif val > 0: return 'color: #0f172a;'
                            return ''
                        
                        s_df = (g_df.sort_values(['Period', 'Net Change'], ascending=[False, True])
                                .style.map(highlight_variance, subset=['Net Change'])
                                .format({'Qty': '{:,.0f}', 'Prev_Qty': '{:,.0f}', 'Net Change': '{:,.0f}'}))
                        st.dataframe(s_df, height=450, use_container_width=True)
                else:
                    st.info("Not enough data periods to calculate growth/decline variance.")

            # --- TAB 3: Product Trend Deep-Dive ---
            with tab3:
                st.markdown("### Product Growth Trajectory")
                st.caption("Select specific dimensions to view their overall growth trend.")
                
                # 去除了功率段筛选器，只保留类目和型号
                c_t1, c_t2 = st.columns(2)
                with c_t1:
                    t_cat = st.selectbox("Select Category", ["All"] + sorted(f_df['category'].unique().tolist()))
                with c_t2:
                    t_mod = st.selectbox("Select Model", ["All"] + sorted(f_df['model'].dropna().unique().tolist()))
                
                dd_df = f_df.copy()
                if t_cat != "All": dd_df = dd_df[dd_df['category'] == t_cat]
                if t_mod != "All": dd_df = dd_df[dd_df['model'] == t_mod]
                
                if not dd_df.empty:
                    trend_line = dd_df.groupby(dd_df['sale_date'].dt.to_period(res_code).astype(str))['sold_qty'].sum().reset_index()
                    trend_line.columns = ['Time Period', 'Total Volume']
                    fig_trend = px.area(trend_line, x='Time Period', y='Total Volume', markers=True, color_discrete_sequence=['#00B2A9'])
                    fig_trend.update_layout(template="plotly_white", hovermode="x unified", font=dict(family="Times New Roman"))
                    st.plotly_chart(fig_trend, use_container_width=True)
                else:
                    st.info("No data available for this specific combination.")

            # --- TAB 4: Reseller Performance & Remarks ---
            with tab4:
                st.markdown("### Inverter & Battery Sales Ranking")
                st.caption("Double-click the 'Remark' column to add notes for specific clients.")
                
                target_cats = ['Inverter', 'Solar Inverter', 'Battery']
                bi_df = f_df[f_df['category'].isin(target_cats)].copy()
                
                if not bi_df.empty:
                    # 1. 客户排行与编辑
                    client_rank = bi_df.groupby('client_name')['sold_qty'].sum().sort_values(ascending=False).reset_index()
                    client_rank.columns = ['Client Name', 'Total Volume (Inv & Bat)']
                    client_rank['Remark (Editable)'] = "" 
                    
                    st.data_editor(
                        client_rank, 
                        use_container_width=True, 
                        num_rows="dynamic",
                        column_config={
                            "Remark (Editable)": st.column_config.TextColumn("Enter remarks here...", max_chars=150)
                        }
                    )
                    
                    st.markdown("---")
                    st.markdown("### Detailed Monthly Purchase Log")
                    st.caption("Month-by-month breakdown of Battery and Inverter purchases per client.")
                    
                    # 2. 客户明细透视表
                    monthly_detail = bi_df.groupby(['client_name', bi_df['sale_date'].dt.to_period('M').astype(str), 'category'])['sold_qty'].sum().unstack(fill_value=0).reset_index()
                    monthly_detail.rename(columns={'client_name': 'Client', 'sale_date': 'Month'}, inplace=True)
                    monthly_detail = monthly_detail.sort_values(by=['Client', 'Month'])
                    
                    format_dict = {col: '{:,.0f}' for col in monthly_detail.columns if col not in ['Client', 'Month']}
                    st.dataframe(monthly_detail.style.format(format_dict), use_container_width=True, height=500)
                else:
                    st.info("No Inverter or Battery data found based on current filters.")

# ==========================================
# 3. Data Terminal
# ==========================================
elif menu == "📤 Data Terminal":
    # 替换为原生标题，彻底解决重叠问题
    st.title("📤 Data Terminal")
    
    # --- 唯一的清除按钮（无多余折叠面板） ---
    if st.button("🗑️ Clear All Database Data (一键清空数据)", type="primary"):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("DELETE FROM sell_through")
        conn.commit()
        conn.close()
        st.success("All data has been successfully cleared! 数据库已彻底清空！")
        st.rerun()
            
    st.markdown("---")
    
    with st.container():
        st.markdown('<div class="filter-card">', unsafe_allow_html=True)
        col_u1, col_u2 = st.columns([1, 2])
        with col_u1:
            source_tag = st.text_input("Data Batch Tag", placeholder="e.g., 2026_Q2_Import")
        with col_u2:
            uploaded_file = st.file_uploader("Upload Excel/CSV", type=["xlsx", "csv"])
        st.markdown('</div>', unsafe_allow_html=True)
    
    if uploaded_file and source_tag:
        try:
            temp_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            temp_df = temp_df.rename(columns=COLUMN_MAP)
            
            # 容错：如果上传表格没有 model 列，自动填充
            for col in ['model']:
                if col not in temp_df.columns: 
                    temp_df[col] = "Unknown"
            
            # 必须字段的检查
            req_cols = ['sale_date', 'client_name', 'category', 'sold_qty']
            missing_reqs = [c for c in req_cols if c not in temp_df.columns]
            
            if missing_reqs:
                st.error(f"Upload failed. Missing required columns: {missing_reqs}")
                st.warning("Please ensure your Excel has headers like: sale_date, client_name, category, sold_qty.")
            else:
                temp_df['sale_date'] = pd.to_datetime(temp_df['sale_date']).dt.strftime('%Y-%m-%d')
                st.success("Data ready for processing.")
                st.dataframe(temp_df.head(3))
                
                if st.button("Initialize & Append to Database", use_container_width=True):
                    temp_df['source_tag'] = source_tag
                    conn = get_db_connection()
                    
                    # 容错提取：只保存数据库需要的列，彻底去除了 power_segment
                    db_cols = ['sale_date', 'client_name', 'category', 'model', 'sold_qty', 'source_tag']
                    cols_to_save = [c for c in db_cols if c in temp_df.columns]
                    
                    temp_df[cols_to_save].to_sql("sell_through", conn, if_exists='append', index=False)
                    conn.close()
                    st.balloons()
                    st.rerun()
        except Exception as e:
            st.error(f"System Error: {e}")
