import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Page Configuration
st.set_page_config(page_title="Retail Sales Intelligence", layout="wide")

# App Title and Header
st.title("📊 Retail Sales Intelligence Dashboard")
st.markdown("Upload your weekly sales and store master data to generate insights.")

# --- STEP 1: DATA INTEGRATION (File Uploads) ---
with st.sidebar:
    st.header("Upload Data")
    sales_file = st.file_uploader("Upload Weekly Sales (xlsx)", type=["xlsx"])
    store_file = st.file_uploader("Upload Store Master (xlsx)", type=["xlsx"])
    
    st.info("Required columns in Sales: week, store_id, net_sales, target, transactions, returns_amount, discount_amount, stockouts, product_category")
    st.info("Required columns in Store Master: store_id, region, city, store_format")

# --- UPDATED DATA LOADING FUNCTION ---
@st.cache_data
def load_data(sales_path, store_path):
    df_sales = pd.read_excel(sales_path)
    df_stores = pd.read_excel(store_path)
    
    # Normalize column names: remove spaces and make lowercase
    df_sales.columns = df_sales.columns.str.strip().str.lower()
    df_stores.columns = df_stores.columns.str.strip().str.lower()
    
    # Ensure store_id is the same type (string) to avoid merge errors
    df_sales['store_id'] = df_sales['store_id'].astype(str)
    df_stores['store_id'] = df_stores['store_id'].astype(str)
    
    # Merge datasets
    df = pd.merge(df_sales, df_stores, on=["store_id","store_name","region","city","store_format"], how="left")
    return df

if sales_file and store_file:
    df = load_data(sales_file, store_file)
    
    # --- VALIDATION CHECK ---
    # List of columns we absolutely need
    required_cols = ['region', 'product_category', 'store_format', 'net_sales', 'sales_target']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        st.error(f"❌ Missing columns in uploaded files: {', '.join(missing_cols)}")
        st.info(f"Available columns found: {list(df.columns)}")
        st.stop() # Stops the app from running further and crashing

    # --- STEP 2: FILTERS (Now safe to run) ---
    st.sidebar.header("Filters")
    
    region_filter = st.sidebar.multiselect(
        "Select Region", 
        options=df['region'].unique(), 
        default=df['region'].unique()
    )
    
    category_filter = st.sidebar.multiselect(
        "Select Category", 
        options=df['product_category'].unique(), 
        default=df['product_category'].unique()
    )
    
    format_filter = st.sidebar.multiselect(
        "Store Format", 
        options=df['store_format'].unique(), 
        default=df['store_format'].unique()
    )
    
    # Filtered Data
    mask = df['region'].isin(region_filter) & df['product_category'].isin(category_filter) & df['store_format'].isin(format_filter)
    filtered_df = df[mask]

    # --- STEP 3: BUSINESS LOGIC (KPI Calculations) ---
    total_net_sales = filtered_df['net_sales'].sum()
    total_target = filtered_df['sales_target'].sum()
    target_achievement = (total_net_sales / total_target) * 100 if total_target != 0 else 0
    atv = total_net_sales / filtered_df['transactions'].sum() if filtered_df['transactions'].sum() != 0 else 0
    return_rate = (filtered_df['returns_amount'].sum() / total_net_sales) * 100 if total_net_sales != 0 else 0
    discount_rate = (filtered_df['discount_amount'].sum() / (total_net_sales + filtered_df['discount_amount'].sum())) * 100

    # --- STEP 4: KPI CARDS ---
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Net Sales", f"${total_net_sales:,.0f}")
    col2.metric("Target Achievement", f"{target_achievement:.1f}%", delta=f"{target_achievement-100:.1f}%")
    col3.metric("Avg Transaction (ATV)", f"${atv:.2f}")
    col4.metric("Return Rate", f"{return_rate:.1f}%", delta_color="inverse")
    col5.metric("Discount Rate", f"{discount_rate:.1f}%")

    # --- STEP 5: CHARTS & VISUALS ---
    row1_col1, row1_col2 = st.columns(2)

    with row1_col1:
        st.subheader("Weekly Sales Trend")
        weekly_trend = filtered_df.groupby('week_start_date')['net_sales'].sum().reset_index()
        fig_trend = px.line(weekly_trend, x='week_start_date', y='net_sales', markers=True, template="plotly_white")
        st.plotly_chart(fig_trend, use_container_width=True)

    with row1_col2:
        st.subheader("Sales by Region")
        reg_sales = filtered_df.groupby('region')['net_sales'].sum().reset_index()
        fig_reg = px.pie(reg_sales, values='net_sales', names='region', hole=0.4)
        st.plotly_chart(fig_reg, use_container_width=True)

    row2_col1, row2_col2 = st.columns(2)

    with row2_col1:
        st.subheader("Category Performance")
        cat_perf = filtered_df.groupby('product_category')['net_sales'].sum().sort_values(ascending=True)
        fig_cat = px.bar(cat_perf, orientation='h', color_continuous_scale='Viridis')
        st.plotly_chart(fig_cat, use_container_width=True)

    with row2_col2:
        st.subheader("Stockout Risk (Low Stock vs Sales)")
        # Logic: Low stock (< 20 units) in high selling categories
        fig_stock = px.scatter(filtered_df, x="net_sales", y="stockouts", color="product_category", 
                               hover_data=['store_id'], title="Stock Level vs Sales")
        fig_stock.add_hline(y=20, line_dash="dash", line_color="red", annotation_text="Risk Zone")
        st.plotly_chart(fig_stock, use_container_width=True)

    # Store Leaderboard
    st.subheader("Store Leaderboard (Top 10)")
    leaderboard = filtered_df.groupby(['store_id', 'city'])['net_sales'].sum().reset_index().sort_values(by='net_sales', ascending=False).head(10)
    st.table(leaderboard)

    # --- STEP 6: BUSINESS INSIGHT SUMMARY ---
    st.divider()
    st.header("💡 Automated Business Insights")
    
    best_region = reg_sales.loc[reg_sales['net_sales'].idxmax()]['region']
    worst_region = reg_sales.loc[reg_sales['net_sales'].idxmin()]['region']
    high_return_cat = filtered_df.groupby('product_category')['returns_amount'].sum().idxmax()
    stores_missing_target = filtered_df[filtered_df['net_sales'] < filtered_df['sales_target']]['store_id'].nunique()

    ins_col1, ins_col2 = st.columns(2)
    with ins_col1:
        st.write(f"✅ **Top Performer:** {best_region} region is leading sales.")
        st.write(f"⚠️ **Focus Area:** {worst_region} region is currently the lowest performer.")
    with ins_col2:
        st.write(f"🔄 **High Returns:** {high_return_cat} has the highest return volume. Inspect quality.")
        st.write(f"🎯 **Target Alert:** {stores_missing_target} stores are currently below their weekly target.")

    # --- STEP 7: EXPORT ---
    st.sidebar.divider()
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button("📥 Download Filtered Data", data=csv, file_name="filtered_retail_data.csv", mime="text/csv")

else:
    st.warning("Please upload both the Weekly Sales and Store Master files to begin.")
    # Show dummy image or placeholder
    st.image("https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&q=80&w=1000", caption="Upload data to see insights")