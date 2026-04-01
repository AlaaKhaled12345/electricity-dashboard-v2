import streamlit as st
import pandas as pd
import plotly.express as px
import os

# ==========================================
# 1. إعداد الصفحة والتصميم (CSS)
# ==========================================
st.set_page_config(layout="wide", page_title="Dashboard Electricity", page_icon="⚡")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; direction: rtl; }
    
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: #ffffff; padding: 10px; border-radius: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f8f9fa; border-radius: 10px; color: #4a4a4a; font-weight: bold; border: 1px solid #e9ecef; }
    .stTabs [aria-selected="true"] { background-color: #2E86C1; color: white; border: none; }

    .metric-card { background: linear-gradient(135deg, #ffffff 0%, #f9f9f9 100%); border-right: 5px solid #2E86C1; border-radius: 12px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); text-align: center; margin-bottom: 20px; transition: transform 0.3s ease; }
    .metric-card:hover { transform: translateY(-5px); }
    .metric-title { color: #7f8c8d; font-size: 1.1rem; margin-bottom: 10px; font-weight: 600; }
    .metric-value { color: #2c3e50; font-size: 2.2rem; font-weight: 800; }
    .metric-sub { font-size: 0.9rem; color: #95a5a6; }

    .card-company { border-right-color: #5FA8D3; }
    .card-private { border-right-color: #E07A5F; }
    .card-total { border-right-color: #F4A261; }
    .card-unknown { border-right-color: #B5838D; background: linear-gradient(135deg, #ffffff 0%, #F8EDEB 100%); }
    
    h3 { color: #2E86C1; border-bottom: 2px solid #eee; padding-bottom: 10px; }
    .table-header { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-right: 5px solid #2E86C1; margin-bottom: 15px; color: #2c3e50; font-weight: bold; font-size: 1.1rem; }
</style>
""", unsafe_allow_html=True)

# ألوان مريحة وهادية جداً لأنواع المحولات
COLOR_MAP = {
    'كشك': '#5DADE2',         
    'غرفة': '#F1948A',        
    'معلق': '#F7DC6F',        
    'هوائي': '#BB8FCE',       
    'أخرى': '#AAB7B8',        
    'غير محدد النوع': '#E5E7E9' 
}

# ==========================================
# 2. دوال المعالجة والتحميل
# ==========================================

def clean_sector_name(name):
    if pd.isna(name): return "قطاع غير محدد"
    s = str(name).strip().replace('أ', 'ا').replace('ة', 'ه').replace('قطاعى', '').replace('قطاع', '').strip()
    return f"قطاع {' '.join(s.split())}"

def metric_card(title, value, subtitle="", style_class=""):
    st.markdown(f"""
    <div class="metric-card {style_class}">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-sub">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

def render_safe_sunburst(df, path_cols, **kwargs):
    df_clean = df.copy()
    for col in path_cols:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].astype(str).replace(['nan', 'None', 'NaN', 'NaT', ''], 'غير محدد')
            df_clean[col] = df_clean[col].apply(lambda x: 'غير محدد' if not x.strip() else x.strip())
        
    try:
        fig = px.sunburst(df_clean, path=path_cols, **kwargs)
        if 'height' in kwargs and kwargs['height'] <= 400:
            fig.update_layout(margin=dict(t=0, l=0, r=0, b=0))
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning("⚠️ لا يمكن عرض المخطط الهرمي لهذه البيانات المحددة لوجود نقص في بعض التصنيفات.")

@st.cache_data
def load_stations():
    if os.path.exists('Electricity_Stations_Final_Cleaned.xlsx'):
        df = pd.read_excel('Electricity_Stations_Final_Cleaned.xlsx')
        df['القطاع'] = df['القطاع'].apply(clean_sector_name)
        col_name = 'المحطة' if 'المحطة' in df.columns else df.columns[1]
        df = df.dropna(subset=[col_name]) 
        df['العدد'] = 1
        return df
    return None

@st.cache_data
def load_distributors():
    files = [f for f in os.listdir('.') if "517" in f and f.endswith('.xlsx')]
    if not files: return None, None
    try:
        df = pd.read_excel(files[0]).iloc[:, [1, 2, 3, 4]]
        df.columns = ['القطاع', 'الهندسة', 'مسلسل', 'الموزع']
        
        mask_total = df.astype(str).apply(lambda x: x.str.contains('إجمالي|اجمالي|الإجمالي|الاجمالي|الموزع', na=False)).any(axis=1)
        df = df[~mask_total]
        
        df[['القطاع', 'الهندسة']] = df[['القطاع', 'الهندسة']].ffill()
        
        df['الموزع'] = df['الموزع'].astype(str).str.strip()
        df = df[~df['الموزع'].isin(['nan', 'None', '', 'NaN'])]
        df = df.dropna(subset=['الموزع'])
        
        df['القطاع'] = df['القطاع'].apply(clean_sector_name)
        
        eng_counts = df.groupby('القطاع')['الهندسة'].nunique()
        df['قطاع_للرسم'] = df['القطاع'].apply(lambda x: f"{x} (هندسات: {eng_counts.get(x, 0)})")
        summary = df.groupby('القطاع').agg({'الهندسة': 'nunique', 'الموزع': 'count'}).reset_index()
        summary.columns = ['القطاع', 'عدد الهندسات', 'عدد الموزعات']
        
        return df, summary
    except Exception as e: 
        return None, None

@st.cache_data
def load_all_transformers():
    file_name = 'Transformers_All.xlsx'
    if not os.path.exists(file_name): 
        return pd.DataFrame()
    
    try:
        all_sheets = pd.read_excel(file_name, sheet_name=None)
        df = pd.concat(all_sheets.values(), ignore_index=True)
        
        # 1. تنظيف أسماء الأعمدة من أي مسافات زائدة
        df.columns = df.columns.astype(str).str.strip()
        
        # 2. معالجة عمود النوع (بطريقة آمنة جداً تمنع خطأ الـ float)
        if 'نوع المبني' in df.columns:
            df['النوع'] = df['نوع المبني']
        elif 'النوع' not in df.columns:
            df['النوع'] = 'غير محدد النوع'
            
        def safe_get_type(val):
            val_str = str(val).strip()
            if val_str in ['nan', 'None', '', 'NaT', 'غير محدد النوع']:
                return 'غير محدد النوع'
            if 'معلق' in val_str or 'هوائي' in val_str:
                return 'معلق'
            if 'كشك' in val_str:
                return 'كشك'
            if 'غرف' in val_str:
                return 'غرفة'
            return 'أخرى'
            
        df['النوع'] = df['النوع'].apply(safe_get_type)
        
        # 3. معالجة القطاع
        if 'القطاع' in df.columns:
            df['القطاع'] = df['القطاع'].apply(clean_sector_name)
        else:
            df['القطاع'] = 'قطاع غير محدد'
            
        # 4. معالجة الملكية (بطريقة آمنة جداً)
        if 'الملكية' not in df.columns:
            df['الملكية'] = 'غير محدد الملكية'
            
        def safe_get_owner(val):
            val_str = str(val).strip()
            if val_str in ['nan', 'None', '', 'NaT', 'غير محدد الملكية']:
                return 'غير محدد الملكية'
            if 'شركة' in val_str:
                return 'ملك الشركة'
            if 'غير' in val_str:
                return 'ملك الغير'
            return 'غير محدد الملكية'
            
        df['الملكية'] = df['الملكية'].apply(safe_get_owner)
            
        # 5. معالجة الهندسة
        if 'الهندسة' not in df.columns:
            df['الهندسة'] = 'هندسة غير محددة'
        else:
            df['الهندسة'] = df['الهندسة'].fillna('هندسة غير محددة').astype(str)
            
        # 6. معالجة القدرة
        if 'القدرة' not in df.columns:
            df['القدرة'] = 0.0
            
        cols_to_category = ['القطاع', 'الهندسة', 'النوع', 'الملكية']
        for col in cols_to_category:
            if col in df.columns:
                df[col] = df[col].astype('category')
                
        return df
    except Exception as e:
        # لو حصل أي مشكلة هيظهر إيرور أحمر صريح بدل ما يخفي البيانات
        st.error(f"⚠️ حدث خطأ داخلي أثناء قراءة بيانات المحولات: {e}")
        return pd.DataFrame()

# ==========================================
# 3. واجهة التطبيق
# ==========================================

st.title("⚡ منظومة إدارة الكهرباء - Dashboard")

df_st = load_stations()
df_dst, df_dst_summ = load_distributors()
df_trans = load_all_transformers()

# ألوان القطاعات
all_sectors = set()
if df_st is not None: all_sectors.update(df_st['القطاع'].dropna().unique())
if df_dst is not None: all_sectors.update(df_dst['القطاع'].dropna().unique())
if not df_trans.empty: all_sectors.update(df_trans['القطاع'].dropna().unique())

comfortable_palette = [
    '#457B9D', '#A8DADC', '#F4A261', '#E76F51', '#2A9D8F', 
    '#E9C46A', '#8AB17D', '#B5838D', '#E5989B', '#6D6875', 
    '#5FA8D3', '#F2CC8F', '#81B29A', '#E07A5F', '#3D5A80',
    '#98C1D9', '#EE6C4D', '#293241', '#C6AC8F', '#5E548E'
]
SECTOR_COLOR_MAP = {sector: comfortable_palette[i % len(comfortable_palette)] for i, sector in enumerate(sorted(all_sectors))}

tab_home, tab_stations, tab_dist, tab_all_trans = st.tabs([
    "🏠 الرئيسية (Dashboard)", 
    "🏭 المحطات العامة",
    "🔌 الموزعات (517)", 
    "⚡ المحولات الشاملة"
])

def get_columns_to_display(df, exclude_cols):
    keywords = ['كود', 'رقم', 'اسم', 'محول']
    id_columns = [col for col in df.columns if any(kw in str(col) for kw in keywords) and col not in exclude_cols]
    return id_columns

# -----------------------------------------------------------------------------
# TAB 1: الرئيسية
# -----------------------------------------------------------------------------
with tab_home:
    st.markdown("### 📊 ملخص بيانات الشركة")
    count_st = len(df_st) if df_st is not None else 0
    count_dst = len(df_dst) if df_dst is not None else 0
    count_trans = len(df_trans) if not df_trans.empty else 0
    
    c1, c2, c3 = st.columns(3)
    with c1: metric_card("المحطات العامة", count_st, "إجمالي المحطات")
    with c2: metric_card("الموزعات", count_dst, "إجمالي الموزعات (517)")
    with c3: metric_card("المحولات (كل القطاعات)", count_trans, "إجمالي محولات الشركة", "card-total")

    if not df_trans.empty:
        st.markdown("---")
        st.markdown("### 🧬 تفاصيل المحولات (على مستوى الشركة)")
        
        st.markdown("#### 🔹 الإجمالي الكلي للمحولات")
        t1, t2, t3 = st.columns(3)
        with t1: metric_card("إجمالي الأكشاك", len(df_trans[df_trans['النوع']=='كشك']), style_class="card-total")
        with t2: metric_card("إجمالي الغرف", len(df_trans[df_trans['النوع']=='غرفة']), style_class="card-total")
        with t3: metric_card("إجمالي المعلقات", len(df_trans[df_trans['النوع']=='معلق']), style_class="card-total")

        df_co = df_trans[df_trans['الملكية'] == 'ملك الشركة']
        df_pr = df_trans[df_trans['الملكية'] == 'ملك الغير']
        
        col_co, col_pr = st.columns(2)
        with col_co:
            st.info("🏢 **ملك الشركة**")
            k1, k2, k3 = st.columns(3)
            with k1: metric_card("أكشاك", len(df_co[df_co['النوع']=='كشك']), style_class="card-company")
            with k2: metric_card("غرف", len(df_co[df_co['النوع']=='غرفة']), style_class="card-company")
            with k3: metric_card("معلقات", len(df_co[df_co['النوع']=='معلق']), style_class="card-company")
        with col_pr:
            st.warning("👤 **ملك الغير**")
            p1, p2, p3 = st.columns(3)
            with p1: metric_card("أكشاك", len(df_pr[df_pr['النوع']=='كشك']), style_class="card-private")
            with p2: metric_card("غرف", len(df_pr[df_pr['النوع']=='غرفة']), style_class="card-private")
            with p3: metric_card("معلقات", len(df_pr[df_pr['النوع']=='معلق']), style_class="card-private")

        st.markdown("#### ⚠️ بيانات غير محددة (نواقص الإكسيل)")
        u1, u2 = st.columns(2)
        
        with u1: 
            df_missing_own = df_trans[df_trans['الملكية'] == 'غير محدد الملكية']
            metric_card("ملكية غير محددة", len(df_missing_own), "خلايا فارغة", "card-unknown")
            if not df_missing_own.empty:
                with st.expander("🔍 عرض تفاصيل النواقص في الملكية فقط"):
                    id_cols = get_columns_to_display(df_missing_own, ['القطاع', 'الهندسة', 'الملكية', 'النوع', 'القدرة'])
                    display_cols = [col for col in (['القطاع', 'الهندسة'] + id_cols + ['الملكية']) if col in df_missing_own.columns]
                    st.dataframe(df_missing_own[display_cols], use_container_width=True)

        with u2: 
            df_missing_type = df_trans[df_trans['النوع'] == 'غير محدد النوع']
            metric_card("نوع مبنى غير محدد", len(df_missing_type), "خلايا فارغة", "card-unknown")
            if not df_missing_type.empty:
                with st.expander("🔍 عرض تفاصيل النواقص في نوع المبنى فقط"):
                    id_cols = get_columns_to_display(df_missing_type, ['القطاع', 'الهندسة', 'الملكية', 'النوع', 'القدرة'])
                    display_cols = [col for col in (['القطاع', 'الهندسة'] + id_cols + ['النوع']) if col in df_missing_type.columns]
                    st.dataframe(df_missing_type[display_cols], use_container_width=True)

    st.markdown("---")
    st.markdown("### 🍩 الهياكل التنظيمية (Sunburst Charts)")
    row3_c1, row3_c2, row3_c3 = st.columns(3)
    with row3_c1:
        if df_st is not None: 
            render_safe_sunburst(df_st, ['القطاع', 'المحطة'], color='القطاع', color_discrete_map=SECTOR_COLOR_MAP, title="المحطات العامة")
    with row3_c2:
        if df_dst is not None: 
            render_safe_sunburst(df_dst, ['القطاع', 'الهندسة'], color='القطاع', color_discrete_map=SECTOR_COLOR_MAP, title="الموزعات")
    with row3_c3:
        if not df_trans.empty: 
            render_safe_sunburst(df_trans, ['الملكية', 'النوع'], title="المحولات", color='النوع', color_discrete_map=COLOR_MAP)

    st.markdown("---")
    st.markdown("### 📈 توزيع أصول الشركة على مستوى القطاعات")
    
    summary_list = []
    if df_st is not None:
        summary_list.append(df_st['القطاع'].value_counts().rename('المحطات'))
    if df_dst is not None:
        summary_list.append(df_dst['القطاع'].value_counts().rename('الموزعات'))
    if not df_trans.empty:
        summary_list.append(df_trans['القطاع'].value_counts().rename('المحولات'))
        
    if summary_list:
        df_summary_all = pd.concat(summary_list, axis=1).fillna(0).reset_index()
        df_summary_all.rename(columns={'index': 'القطاع'}, inplace=True)
        df_melted = df_summary_all.melt(id_vars='القطاع', var_name='نوع الأصل', value_name='العدد')
        
        asset_colors = {'المحطات': '#457B9D', 'الموزعات': '#F4A261', 'المحولات': '#2A9D8F'}
        
        fig_bar_main = px.bar(
            df_melted, 
            x='القطاع', 
            y='العدد', 
            color='نوع الأصل', 
            barmode='group', 
            color_discrete_map=asset_colors,
            text='العدد'
        )
        fig_bar_main.update_traces(textposition='outside')
        fig_bar_main.update_layout(
            xaxis_tickangle=-45, 
            xaxis_title="", 
            yaxis_title="عدد الأصول",
            legend_title="نوع الأصل",
            height=450,
            margin=dict(t=20, b=100)
        )
        st.plotly_chart(fig_bar_main, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 2 & 3
# -----------------------------------------------------------------------------
with tab_stations:
    if df_st is not None:
        cs1, cs2 = st.columns([3, 1])
        with cs1: 
            render_safe_sunburst(df_st, ['القطاع', 'المحطة'], values='العدد', color='القطاع', color_discrete_map=SECTOR_COLOR_MAP, height=700)
        with cs2:
            cnt_sec = df_st['القطاع'].value_counts().reset_index()
            cnt_sec.columns = ['القطاع', 'العدد']
            fig_st_bar = px.bar(cnt_sec, x='القطاع', y='العدد', color='القطاع', color_discrete_map=SECTOR_COLOR_MAP)
            st.plotly_chart(fig_st_bar, use_container_width=True)
        st.dataframe(df_st, use_container_width=True)

with tab_dist:
    if df_dst is not None:
        cd1, cd2 = st.columns([1, 2])
        with cd1: 
            render_safe_sunburst(df_dst, ['قطاع_للرسم', 'الهندسة', 'الموزع'], color='القطاع', color_discrete_map=SECTOR_COLOR_MAP, height=700)
        with cd2:
            cnt_dst = df_dst.groupby(['القطاع', 'الهندسة']).size().reset_index(name='العدد').sort_values('العدد', ascending=False)
            fig_d_bar = px.bar(cnt_dst, x='الهندسة', y='العدد', color='القطاع', color_discrete_map=SECTOR_COLOR_MAP, text='العدد')
            fig_d_bar.update_layout(xaxis=dict(tickangle=-90))
            st.plotly_chart(fig_d_bar, use_container_width=True)
        st.dataframe(df_dst_summ, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 4: المحولات الشاملة
# -----------------------------------------------------------------------------
with tab_all_trans:
    if not df_trans.empty:
        st.markdown("### 🎯 استعلام ديناميكي لمحولات القطاعات")
        
        all_sectors_list = sorted([s for s in df_trans['القطاع'].unique() if s != "قطاع غير محدد" and str(s) != 'nan'])
        selected_sec = st.selectbox("📌 اختر القطاع لعرض محولاته:", ["الكل"] + all_sectors_list)
        
        df_view = df_trans if selected_sec == "الكل" else df_trans[df_trans['القطاع'] == selected_sec]
        
        if not df_view.empty:
            num_engs = df_view['الهندسة'].nunique()
            num_total_trans = len(df_view)
            num_company = len(df_view[df_view['الملكية'] == 'ملك الشركة'])
            num_private = len(df_view[df_view['الملكية'] == 'ملك الغير'])
            
            c_v1, c_v2, c_v3, c_v4 = st.columns(4)
            with c_v1: metric_card("عدد الهندسات", num_engs, "هندسة بالقطاع")
            with c_v2: metric_card("إجمالي المحولات", num_total_trans, "محول")
            with c_v3: metric_card("ملك الشركة", num_company, "محول", "card-company")
            with c_v4: metric_card("ملك الغير", num_private, "محول", "card-private")
            
            c_v5, c_v6 = st.columns(2)
            
            with c_v5: 
                df_view_miss_own = df_view[df_view['الملكية'] == 'غير محدد الملكية']
                metric_card("ملكية غير محددة", len(df_view_miss_own), "محولات بدون ملكية", "card-unknown")
                if not df_view_miss_own.empty:
                    with st.expander(f"🔍 عرض تفاصيل النواقص في الملكية بـ {selected_sec}"):
                        id_cols = get_columns_to_display(df_view_miss_own, ['القطاع', 'الهندسة', 'الملكية', 'النوع', 'القدرة'])
                        display_cols = [col for col in (['الهندسة'] + id_cols + ['الملكية']) if col in df_view_miss_own.columns]
                        st.dataframe(df_view_miss_own[display_cols], use_container_width=True)
            
            with c_v6: 
                df_view_miss_type = df_view[df_view['النوع'] == 'غير محدد النوع']
                metric_card("نوع غير محدد", len(df_view_miss_type), "محولات بدون نوع مبنى", "card-unknown")
                if not df_view_miss_type.empty:
                    with st.expander(f"🔍 عرض تفاصيل النواقص في نوع المبنى بـ {selected_sec}"):
                        id_cols = get_columns_to_display(df_view_miss_type, ['القطاع', 'الهندسة', 'الملكية', 'النوع', 'القدرة'])
                        display_cols = [col for col in (['الهندسة'] + id_cols + ['النوع']) if col in df_view_miss_type.columns]
                        st.dataframe(df_view_miss_type[display_cols], use_container_width=True)
            
            st.markdown("---")
            
            col_data, col_charts = st.columns([1.2, 1])
            
            with col_data:
                st.markdown("<div class='table-header'>📋 تفاصيل المحولات (النوع والملكية)</div>", unsafe_allow_html=True)
                trans_grouped = df_view.groupby(['الهندسة', 'الملكية', 'النوع']).size().reset_index(name='العدد')
                if not trans_grouped.empty:
                    pivot_trans = trans_grouped.pivot_table(index='الهندسة', columns=['الملكية', 'النوع'], values='العدد', fill_value=0).astype(int)
                    st.dataframe(pivot_trans, use_container_width=True, height=400)
                
            with col_charts:
                st.markdown("<div class='table-header'>📊 تحليل مرئي للقطاع</div>", unsafe_allow_html=True)
                
                render_safe_sunburst(df_view, ['الهندسة', 'الملكية', 'النوع'], color='النوع', color_discrete_map=COLOR_MAP, height=350)
                
                cnt_type_dyn = df_view['النوع'].value_counts().reset_index()
                cnt_type_dyn.columns = ['النوع', 'العدد']
                fig_bar_dyn = px.bar(cnt_type_dyn, x='النوع', y='العدد', color='النوع', color_discrete_map=COLOR_MAP, text='العدد', height=300)
                st.plotly_chart(fig_bar_dyn, use_container_width=True)
        else:
            st.info("لا توجد بيانات متاحة لهذا القطاع.")
            
    else:
        st.warning("⚠️ يرجى التأكد من رفع ملف 'Transformers_All.xlsx' لظهور بيانات المحولات.")
