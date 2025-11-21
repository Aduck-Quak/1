import streamlit as st
import datetime
import json
import pandas as pd
import altair as alt

# --- 1. 全局配置 & 美化 ---
st.set_page_config(page_title="Ontario Residency Pro", page_icon="🍁", layout="wide")

# 定义及格线 (你提到的 365 天)
THRESHOLD_DAYS = 365
WINDOW_YEARS = 2

# --- 2. 核心逻辑函数 ---

def get_data_from_url():
    """从 URL 读取数据"""
    if "data" in st.query_params:
        try:
            json_str = st.query_params["data"]
            data = json.loads(json_str)
            loaded_trips = []
            for t in data:
                loaded_trips.append({
                    'start': datetime.datetime.strptime(t['s'], "%Y-%m-%d").date(),
                    'end': datetime.datetime.strptime(t['e'], "%Y-%m-%d").date()
                })
            return loaded_trips
        except Exception:
            return []
    return []

def update_url(trips):
    """更新 URL 以便分享"""
    if trips:
        trips_data = [{'s': str(t['start']), 'e': str(t['end'])} for t in trips]
        json_str = json.dumps(trips_data)
        st.query_params["data"] = json_str
    else:
        if "data" in st.query_params:
            del st.query_params["data"]

def calculate_days_for_date(target_date, trips):
    """计算特定某一天的居住状态"""
    try:
        start_window = target_date.replace(year=target_date.year - WINDOW_YEARS)
    except ValueError:
        start_window = target_date.replace(year=target_date.year - WINDOW_YEARS, day=28)

    total_window_days = (target_date - start_window).days
    days_absent = 0
    
    future_conflict_days = 0 # 记录导致超标的未来天数

    for trip in trips:
        effective_start = max(trip['start'], start_window)
        effective_end = min(trip['end'], target_date)

        if effective_start < effective_end:
            days_out = (effective_end - effective_start).days
            days_absent += days_out
            
            # 如果这个 trip 是未来的（相对于今天），记录一下它的影响
            if trip['start'] > datetime.date.today():
                future_conflict_days += days_out

    days_present = total_window_days - days_absent
    return days_present, days_absent, future_conflict_days

# --- 3. 初始化 ---
if 'trips' not in st.session_state:
    st.session_state.trips = get_data_from_url()

# --- 4. 界面布局 (Fancy UI) ---

st.title("🍁 Ontario Residency Pro")
st.markdown(f"**状态追踪** | 过去 {WINDOW_YEARS} 年窗口期 | 红线标准: **{THRESHOLD_DAYS} 天**")

# 布局：左侧输入，右侧仪表盘
left_col, right_col = st.columns([1, 2])

with left_col:
    st.subheader("1. 行程管理")
    
    # 添加行程
    with st.form("add_trip_form"):
        c1, c2 = st.columns(2)
        d_start = c1.date_input("出发 (Departure)", value=datetime.date.today())
        d_end = c2.date_input("返回 (Return)", value=datetime.date.today())
        submitted = st.form_submit_button("➕ 添加行程", use_container_width=True)
        
        if submitted:
            if d_start > d_end:
                st.error("出发日期不能晚于返回日期")
            else:
                st.session_state.trips.append({'start': d_start, 'end': d_end})
                # 按时间排序
                st.session_state.trips.sort(key=lambda x: x['start'])
                update_url(st.session_state.trips)
                st.success("行程已添加")
                st.rerun()

    # 列表显示 (区分过去和未来)
    if st.session_state.trips:
        st.write("---")
        st.markdown("### 📅 行程列表")
        today = datetime.date.today()
        
        for i, trip in enumerate(st.session_state.trips):
            # 判断是过去还是未来
            is_future = trip['start'] > today
            label_prefix = "🔮 FUTURE PLAN" if is_future else "✅ PAST TRIP"
            color = "blue" if is_future else "green"
            
            with st.expander(f"{i+1}. :{color}[{label_prefix}] {trip['start']} ➔ {trip['end']}"):
                if st.button("删除此行程", key=f"del_{i}"):
                    del st.session_state.trips[i]
                    update_url(st.session_state.trips)
                    st.rerun()
    
    # 复制链接功能
    st.info("提示：复制浏览器上方的链接，或保存下方链接以储存数据。")
    st.code(f"https://share.streamlit.io/...?data={st.query_params.get('data', '')}", language="text")

with right_col:
    st.subheader("2. 智能分析 & 趋势图")
    
    # 选择目标日期
    target_date = st.date_input("你想检查哪一天的状态？", value=datetime.date.today())
    
    # 计算选中那一天的状态
    present, absent, future_impact = calculate_days_for_date(target_date, st.session_state.trips)
    
    # --- 顶部大数字展示 ---
    m1, m2, m3 = st.columns(3)
    m1.metric("居住天数 (Days Present)", f"{present} 天", delta=f"{present - THRESHOLD_DAYS} vs 红线")
    m2.metric("离境天数 (Days Absent)", f"{absent} 天")
    status_color = "green" if present >= THRESHOLD_DAYS else "red"
    status_text = "✅ 达标 (Safe)" if present >= THRESHOLD_DAYS else "⚠️ 警告 (Warning)"
    m3.markdown(f"### :{status_color}[{status_text}]")

    # --- 智能建议 (Smart Suggestion) ---
    if present < THRESHOLD_DAYS:
        shortfall = THRESHOLD_DAYS - present
        st.error(f"🚨 注意：你在 {target_date} 将会低于红线 **{shortfall} 天**。")
        
        if future_impact > 0:
            # 如果是因为未来的旅行导致的
            st.markdown(f"""
            <div style="padding:15px; border-radius:10px; background-color:#fff3cd; border:1px solid #ffeeba; color:#856404;">
                <strong>💡 智能建议：</strong><br>
                这是因为你未来的旅行计划太长了。<br>
                建议你将未来的旅行 <b>缩短 {shortfall} 天</b> 即可达标。
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("原因：过去的离境时间太长，必须等待旧的离境记录过期。")

    st.write("---")
    
    # --- 股票走势图 (Stock Chart Logic) ---
    st.markdown("### 📈 居住趋势图 (Trend Analysis)")
    st.caption(f"展示日期：{target_date} 前后 90 天的走势")

    # 生成图表数据：目标日期 前后 90 天
    chart_data = []
    date_range = pd.date_range(start=target_date - datetime.timedelta(days=90), 
                               end=target_date + datetime.timedelta(days=90))

    for d in date_range:
        d_date = d.date()
        p, _, _ = calculate_days_for_date(d_date, st.session_state.trips)
        chart_data.append({
            "Date": d_date,
            "Days Present": p,
            "Red Line (365)": THRESHOLD_DAYS
        })
    
    df_chart = pd.DataFrame(chart_data)
    
    # 使用 Altair 画图 (Streamlit 原生支持，比 Matplotlib 更漂亮)
    # 线条1：实际天数
    line = alt.Chart(df_chart).mark_line(strokeWidth=3).encode(
        x='Date',
        y=alt.Y('Days Present', scale=alt.Scale(domain=[min(df_chart["Days Present"].min(), 300), max(740, df_chart["Days Present"].max())])),
        color=alt.value("#29b5e8"),
        tooltip=['Date', 'Days Present']
    )
    
    # 线条2：红线 (365)
    rule = alt.Chart(df_chart).mark_line(color='red', strokeDash=[5, 5]).encode(
        x='Date',
        y='Red Line (365)'
    )

    # 显示图表
    st.altair_chart(line + rule, use_container_width=True)
    
    st.caption("蓝色实线 = 你的居住天数 | 红色虚线 = 365天及格线")
