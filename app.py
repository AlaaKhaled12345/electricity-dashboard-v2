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

    .card-company { border-right-color: #2980b9; }
    .card-private { border-right-color: #c0392b; }
    .card-total { border-right-color: #f39c12; }
    .card-unknown { border-right-color: #e74c3c; background: linear-gradient(135deg, #ffffff 0%, #fdedec 100%); }
    
    h3 { color: #2E86C1; border-bottom: 2px solid #eee; padding-bottom: 10px; }
    .table-header { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-right: 5px solid #2E86C1; margin-bottom: 15px; color: #2c3e50; font-weight: bold; font-size: 1.1rem; }
</style>
""", unsafe_allow_html=True)

COLOR_MAP = {'كشك': '#2980b9', 'غرفة': '#c0392b', 'معلق': '#f1c40f', 'هوائي': '#8e44ad', 'أخرى': '#7f8c8d', 'غير محدد': '#bdc3c7'}

# ==========================================
# 2. دوال المعالجة والتحميل (Backend Logic)
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

# --- دالة الرسم الآمنة لتجنب انهيار التطبيق ---
def render_safe_sunburst(df, path_cols, **kwargs):
    df_clean = df.copy()
    # تنظيف صارم للنصوص لمنع مشاكل Plotly
    for col in path_cols:
        df_clean[col] = df_clean[col].astype(str).replace(['nan', 'None', 'NaN', 'NaT', ''], 'غير محدد')
        df_clean[col] = df_clean[col].apply(lambda x: 'غير محدد' if not x.strip() else x.strip())
        
    try:
        fig = px.sunburst(df_clean, path=path_cols, **kwargs)
        # تعديل الهوامش للرسومات الصغيرة
        if 'height' in kwargs and kwargs['height'] <= 400:
            fig.update_layout(margin=dict(t=0, l=0, r=0, b=0))
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        # إذا فشل الرسم، لا نوقف التطبيق، بل نعرض رسالة خطأ صغيرة
        st.warning("⚠️ لا يمكن عرض المخطط الهرمي لهذه البيانات المحددة بسبب تداخل في المسميات.")

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
        df = df.ffill()
        df['القطاع'] = df['القطاع'].apply(clean_sector_name)
        
        eng_counts = df.groupby('القطاع')['الهندسة'].nunique()
        df['قطاع_للرسم'] = df['القطاع'].apply(lambda x: f"{x} (هندسات: {eng_counts.get(x, 0)})")
        summary = df.groupby('القطاع').agg({'الهندسة': 'nunique', 'الموزع': 'count'}).reset_index()
        summary.columns = ['القطاع', 'عدد الهندسات', 'عدد الموزعات']
        return df, summary
    except: return None, None

@st.cache_data
def load_all_transformers():
    file_name = 'Transformers_All.xlsx'
    if not os.path.exists(file_name): return pd.DataFrame()
    
    try:
        all_sheets = pd.read_excel(file_name, sheet_name=None)
        df = pd.concat(all_sheets.values(), ignore_index=True)
        
        if 'نوع المبني' in df.columns:
            df['النوع'] = df['نوع المبني'].astype(str).str.strip()
        else:
            df['النوع'] = 'غير محدد'
            
        # تعديل بسيط هنا لضمان قراءة الخانات الفاضية كـ "غير محدد"
        df['النوع'] = df['النوع'].apply(lambda x: 'غير محدد' if x in ['nan', 'None', ''] else ('معلق' if 'معلق' in x or 'هوائي' in x else ('كشك' if 'كشك' in x else ('غرفة' if 'غرف' in x else 'أخرى'))))
        
        df['القطاع'] = df['القطاع'].apply(clean_sector_name)
        df['الملكية'] = df['الملكية'].astype(str).apply(lambda x: 'ملك الشركة' if 'شركة' in x else ('ملك الغير' if 'غير' in x else 'غير محدد'))
        
        if 'الهندسة' not in df.columns:
            df['الهندسة'] = 'هندسة غير محددة'
        else:
            df['الهندسة'] = df['الهندسة'].fillna('هندسة غير محددة').astype(str)
            
        if 'القدرة' not in df.columns:
            df['القدرة'] = 0.0
            
        # 🔥 التعديل هنا لتقليل استهلاك الـ RAM بشكل كبير 🔥
        cols_to_category = ['القطاع', 'الهندسة', 'النوع', 'الملكية']
        for col in cols_to_category:
            if col in df.columns:
                df[col] = df[col].astype('category')
                
        return df
    except Exception as e:
        return pd.DataFrame()

# ==========================================
# 3. واجهة التطبيق
# ==========================================

st.title("⚡ منظومة إدارة الكهرباء - Dashboard")

df_st = load_stations()
df_dst, df_dst_summ = load_distributors()
df_trans = load_all_transformers()

# ----------------- التعديل هنا: مسحنا تاب القطاعات -----------------
tab_home, tab_stations, tab_dist, tab_all_trans = st.tabs([
    "🏠 الرئيسية (Dashboard)", 
    "🏭 المحطات العامة",
    "🔌 الموزعات (517)", 
    "⚡ المحولات الشاملة"
])

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

        # ------- إضافة كروت النواقص اللي طلبتيها في الرئيسية -------
        st.markdown("#### ⚠️ بيانات غير محددة (نواقص الإكسيل)")
        u1, u2 = st.columns(2)
        with u1: metric_card("ملكية غير محددة", len(df_trans[df_trans['الملكية'] == 'غير محدد']), "خلايا فارغة", "card-unknown")
        with u2: metric_card("نوع مبنى غير محدد", len(df_trans[df_trans['النوع'] == 'غير محدد']), "خلايا فارغة", "card-unknown")

    st.markdown("---")
    st.markdown("### 📈 الرسوم التوضيحية المجمعة")
    row3_c1, row3_c2, row3_c3 = st.columns(3)
    with row3_c1:
        if df_st is not None: 
            render_safe_sunburst(df_st, ['القطاع', 'المحطة'], title="المحطات العامة")
    with row3_c2:
        if df_dst is not None: 
            render_safe_sunburst(df_dst, ['القطاع', 'الهندسة'], title="الموزعات")
    with row3_c3:
        if not df_trans.empty: 
            render_safe_sunburst(df_trans, ['الملكية', 'النوع'], title="المحولات", color='النوع', color_discrete_map=COLOR_MAP)

# -----------------------------------------------------------------------------
# TAB 2 & 3
# -----------------------------------------------------------------------------
with tab_stations:
    if df_st is not None:
        cs1, cs2 = st.columns([3, 1])
        with cs1: 
            render_safe_sunburst(df_st, ['القطاع', 'المحطة'], values='العدد', height=700)
        with cs2:
            cnt_sec = df_st['القطاع'].value_counts().reset_index()
            cnt_sec.columns = ['القطاع', 'العدد']
            st.plotly_chart(px.bar(cnt_sec, x='القطاع', y='العدد', color='القطاع'), use_container_width=True)
        st.dataframe(df_st, use_container_width=True)

with tab_dist:
    if df_dst is not None:
        cd1, cd2 = st.columns([1, 2])
        with cd1: 
            render_safe_sunburst(df_dst, ['قطاع_للرسم', 'الهندسة', 'الموزع'], color='القطاع', height=700)
        with cd2:
            cnt_dst = df_dst.groupby(['القطاع', 'الهندسة']).size().reset_index(name='العدد').sort_values('العدد', ascending=False)
            fig_d_bar = px.bar(cnt_dst, x='الهندسة', y='العدد', color='القطاع', text='العدد')
            fig_d_bar.update_layout(xaxis=dict(tickangle=-90))
            st.plotly_chart(fig_d_bar, use_container_width=True)
        st.dataframe(df_dst_summ, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 4: المحولات الشاملة (الديناميكية بالقطاع)
# -----------------------------------------------------------------------------
with tab_all_trans:
    if not df_trans.empty:
        st.markdown("### 🎯 استعلام ديناميكي لمحولات القطاعات")
        
        all_sectors = sorted([s for s in df_trans['القطاع'].unique() if s != "قطاع غير محدد" and str(s) != 'nan'])
        selected_sec = st.selectbox("📌 اختر القطاع لعرض محولاته:", ["الكل"] + all_sectors)
        
        df_view = df_trans if selected_sec == "الكل" else df_trans[df_trans['القطاع'] == selected_sec]
        
        if not df_view.empty:
            num_engs = df_view['الهندسة'].nunique()
            num_total_trans = len(df_view)
            num_company = len(df_view[df_view['الملكية'] == 'ملك الشركة'])
            num_private = len(df_view[df_view['الملكية'] == 'ملك الغير'])
            
            # حساب النواقص
            num_unspecified_own = len(df_view[df_view['الملكية'] == 'غير محدد'])
            num_unspecified_type = len(df_view[df_view['النوع'] == 'غير محدد'])
            
            c_v1, c_v2, c_v3, c_v4 = st.columns(4)
            with c_v1: metric_card("عدد الهندسات", num_engs, "هندسة بالقطاع")
            with c_v2: metric_card("إجمالي المحولات", num_total_trans, "محول")
            with c_v3: metric_card("ملك الشركة", num_company, "محول", "card-company")
            with c_v4: metric_card("ملك الغير", num_private, "محول", "card-private")
            
            # ------- إضافة كروت النواقص اللي طلبتيها في القطاعات -------
            c_v5, c_v6 = st.columns(2)
            with c_v5: metric_card("ملكية غير محددة", num_unspecified_own, "محولات بدون ملكية", "card-unknown")
            with c_v6: metric_card("نوع غير محدد", num_unspecified_type, "محولات بدون نوع مبنى", "card-unknown")
            
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
