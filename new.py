import streamlit as st
import datetime
import json
import pandas as pd
import altair as alt

# --- 1. 全局配置 ---
st.set_page_config(page_title="Ontario Residency Pro", page_icon="🍁", layout="wide")

# 常量定义
THRESHOLD_DAYS = 365
WINDOW_YEARS = 2

# --- 2. 核心逻辑 ---

def get_data_from_url():
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
    if trips:
        trips_data = [{'s': str(t['start']), 'e': str(t['end'])} for t in trips]
        json_str = json.dumps(trips_data)
        st.query_params["data"] = json_str
    else:
        if "data" in st.query_params:
            del st.query_params["data"]

def calculate_days_for_date(target_date, trips):
    try:
        start_window = target_date.replace(year=target_date.year - WINDOW_YEARS)
    except ValueError:
        start_window = target_date.replace(year=target_date.year - WINDOW_YEARS, day=28)

    total_window_days = (target_date - start_window).days
    days_absent = 0
    future_conflict_days = 0

    for trip in trips:
        effective_start = max(trip['start'], start_window)
        effective_end = min(trip['end'], target_date)

        if effective_start < effective_end:
            days_out = (effective_end - effective_start).days
            days_absent += days_out
            if trip['start'] > datetime.date.today():
                future_conflict_days += days_out

    days_present = total_window_days - days_absent
    return days_present, days_absent, future_conflict_days

# --- 3. 初始化 ---
if 'trips' not in st.session_state:
    st.session_state.trips = get_data_from_url()

# --- 4. 界面布局 ---

st.title("🍁 Ontario Residency Pro")
st.markdown(f"**状态追踪** | 过去 {WINDOW_YEARS} 年窗口期 | 红线标准: **{THRESHOLD_DAYS} 天**")

left_col, right_col = st.columns([1, 2])

with left_col:
    st.subheader("1. 行程管理")
    with st.form("add_trip_form"):
        c1, c2 = st.columns(2)
        d_start = c1.date_input("出发", value=datetime.date.today())
        d_end = c2.date_input("返回", value=datetime.date.today())
        submitted = st.form_submit_button("➕ 添加行程", use_container_width=True)
        
        if submitted:
            if d_start > d_end:
                st.error("日期错误")
            else:
                st.session_state.trips.append({'start': d_start, 'end': d_end})
                st.session_state.trips.sort(key=lambda x: x['start'])
                update_url(st.session_state.trips)
                st.rerun()

    if st.session_state.trips:
        st.write("---")
        st.markdown("### 📅 行程列表")
        today = datetime.date.today()
        for i, trip in enumerate(st.session_state.trips):
            is_future = trip['start'] > today
            label = "🔮 FUTURE" if is_future else "✅ PAST"
            color = "blue" if is_future else "green"
            with st.expander(f"{i+1}. :{color}[{label}] {trip['start']} ➔ {trip['end']}"):
                if st.button("删除", key=f"del_{i}"):
                    del st.session_state.trips[i]
                    update_url(st.session_state.trips)
                    st.rerun()
    
    st.info("💡 提示：复制上方浏览器链接即可保存当前数据。")

with right_col:
    st.subheader("2. 智能分析 & 趋势图")
    target_date = st.date_input("选择检查日期 (Target Date)", value=datetime.date.today())
    
    present, absent, future_impact = calculate_days_for_date(target_date, st.session_state.trips)
    
    # 顶部指标
    m1, m2, m3 = st.columns(3)
    m1.metric("居住天数", f"{present} 天", delta=f"{present - THRESHOLD_DAYS}")
    m2.metric("离境天数", f"{absent} 天")
    status = "✅ 达标" if present >= THRESHOLD_DAYS else "⚠️ 警告"
    m3.markdown(f"### {status}")

    # 智能建议
    if present < THRESHOLD_DAYS:
        shortfall = THRESHOLD_DAYS - present
        if future_impact > 0:
            st.warning(f"💡 建议：将未来的旅行缩短 **{shortfall} 天** 即可达标。")
        else:
            st.error(f"🚨 警报：过去离境时间过长，需等待离境记录过期。")

    st.write("---")
    st.markdown("### 📈 关键节点图 (Critical Points)")

    # --- 生成图表数据 ---
    # 为了看清交叉点，我们将范围设为前后 120 天
    days_range = 120
    date_range = pd.date_range(start=target_date - datetime.timedelta(days=days_range), 
                               end=target_date + datetime.timedelta(days=days_range))

    chart_data = []
    cross_points = [] # 用于存储交叉点

    # 预计算第一个点
    prev_present, _, _ = calculate_days_for_date(date_range[0].date(), st.session_state.trips)

    for d in date_range:
        d_date = d.date()
        curr_present, _, _ = calculate_days_for_date(d_date, st.session_state.trips)
        
        chart_data.append({
            "Date": d_date,
            "Days Present": curr_present,
            "Safe Line": THRESHOLD_DAYS
        })

        # --- 核心逻辑：检测交叉点 ---
        # 如果昨天及格，今天不及格 (跌破) OR 昨天不及格，今天及格 (回升)
        if (prev_present >= THRESHOLD_DAYS and curr_present < THRESHOLD_DAYS) or \
           (prev_present < THRESHOLD_DAYS and curr_present >= THRESHOLD_DAYS):
            cross_points.append({
                "Date": d_date,
                "Days Present": 365, # 强制钉在线上，视觉更好看
                "Label": str(d_date) # 标签内容就是日期
            })
        
        prev_present = curr_present
    
    df_chart = pd.DataFrame(chart_data)
    df_cross = pd.DataFrame(cross_points)

    # --- 动态设置 Y 轴范围 (300 - 600) ---
    # 如果数据极其极端（比如只有10天），才打破这个规则，否则默认聚焦 300-600
    min_y = max(200, min(df_chart["Days Present"].min() - 10, 300))
    max_y = min(730, max(df_chart["Days Present"].max() + 10, 500))

    # 1. 基础线 (蓝色)
    line = alt.Chart(df_chart).mark_line(strokeWidth=3).encode(
        x='Date',
        y=alt.Y('Days Present', scale=alt.Scale(domain=[min_y, max_y])),
        color=alt.value("#29b5e8"),
        tooltip=['Date', 'Days Present']
    )
    
    # 2. 红线 (365)
    rule = alt.Chart(df_chart).mark_rule(color='red', strokeDash=[5, 5]).encode(
        y='Safe Line'
    )

    # 3. 交叉点 (红色圆点)
    if not df_cross.empty:
        points = alt.Chart(df_cross).mark_point(filled=True, color="red", size=100).encode(
            x='Date',
            y='Days Present',
            tooltip=['Date']
        )
        
        # 4. 交叉点标签 (直接显示日期)
        text = alt.Chart(df_cross).mark_text(
            align='left',
            baseline='bottom',
            dx=5,  # 向右偏移
            dy=-5, # 向上偏移
            color='red',
            fontSize=12
        ).encode(
            x='Date',
            y='Days Present',
            text='Label'
        )
        
        final_chart = (line + rule + points + text)
    else:
        final_chart = (line + rule)

    st.altair_chart(final_chart, use_container_width=True)
    
    if not df_cross.empty:
        st.caption(f"🔴 红色日期标注：状态发生改变（达标/不达标）的关键日期。")
