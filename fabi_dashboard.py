"""
FABI SALES DASHBOARD — Streamlit App
Cách dùng:
  1. Mở Google Colab
  2. Upload file này + file XLS từ Fabi
  3. Chạy: !pip install streamlit beautifulsoup4 plotly openpyxl xlrd && streamlit run fabi_dashboard.py
  4. Hoặc dùng ngrok/localtunnel để share link
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re
import json
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from bs4 import BeautifulSoup
import io

# ──────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────
st.set_page_config(
    page_title="Fabi Dashboard",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────
# NAVY THEME
# ──────────────────────────────────────────
NAVY   = "#0D1B2A"
NAVY2  = "#1B2A3B"
NAVY3  = "#243447"
TEAL   = "#2EC4B6"
GOLD   = "#FFD166"
WHITE  = "#F0F4F8"
GRAY   = "#8FA0B2"
RED    = "#E63946"
GREEN  = "#06D6A0"

CSS = f"""
<style>
html, body, [data-testid="stAppViewContainer"] {{
    background-color: {NAVY};
    color: {WHITE};
}}
[data-testid="stSidebar"] {{
    background-color: {NAVY2};
}}
[data-testid="stSidebar"] * {{
    color: {WHITE} !important;
}}
h1, h2, h3 {{
    color: {WHITE};
}}
.metric-card {{
    background: {NAVY2};
    border: 1px solid {NAVY3};
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 8px;
}}
.metric-label {{
    font-size: 12px;
    color: {GRAY};
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}}
.metric-value {{
    font-size: 32px;
    font-weight: 800;
    color: {WHITE};
    letter-spacing: -1px;
    margin: 4px 0 2px;
}}
.metric-sub {{
    font-size: 13px;
    color: {GRAY};
}}
.metric-accent .metric-value {{
    color: {TEAL};
}}
.section-title {{
    font-size: 15px;
    font-weight: 700;
    color: {WHITE};
    border-left: 3px solid {TEAL};
    padding-left: 10px;
    margin: 24px 0 12px;
}}
.stSelectbox > div > div {{
    background-color: {NAVY2} !important;
    color: {WHITE} !important;
    border: 1px solid {NAVY3} !important;
}}
.stButton > button {{
    background-color: {TEAL};
    color: {NAVY};
    font-weight: 700;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
}}
.stButton > button:hover {{
    background-color: #26a89e;
}}
div[data-testid="stFileUploader"] {{
    background: {NAVY2};
    border: 2px dashed {NAVY3};
    border-radius: 12px;
    padding: 16px;
}}
.tag-green {{ color: {GREEN}; font-weight: 600; }}
.tag-red   {{ color: {RED};   font-weight: 600; }}
.tag-gold  {{ color: {GOLD};  font-weight: 600; }}
.stDataFrame {{ background: {NAVY2}; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ──────────────────────────────────────────
# DATA PARSING
# ──────────────────────────────────────────
@st.cache_data(show_spinner=False)
def parse_fabi_file(file_bytes: bytes) -> list[dict]:
    """Parse XLS/HTML file xuất từ Fabi, trả về list hóa đơn."""
    try:
        content = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        content = file_bytes.decode("latin-1")

    soup = BeautifulSoup(content, "html.parser")
    table = soup.find("table")
    if table is None:
        raise ValueError("Không tìm thấy dữ liệu trong file. Hãy đảm bảo file XLS xuất từ Fabi.")

    rows = table.find_all("tr")
    invoices = []
    i = 5  # skip header rows

    while i < len(rows):
        cells = [td.get_text(strip=True) for td in rows[i].find_all("td")]

        if len(cells) == 40 and cells[0].isdigit():
            inv = {
                "stt":          cells[0],
                "ngay":         cells[6],
                "gio":          cells[7],
                "ban":          cells[11],
                "trang_thai":   cells[12],
                "tong_tien":    _to_int(cells[19]),
                "giam_gia":     _to_int(cells[20]),
                "tong_hoa_don": _to_int(cells[33]),
                "pttt":         cells[36],
            }

            items = []
            j = i + 1
            while j < len(rows):
                ic = [td.get_text(strip=True) for td in rows[j].find_all("td")]
                if len(ic) == 26 and ic[0] and not ic[0].isdigit():
                    don_gia = _to_int(ic[3])
                    sl      = _to_int(ic[1])
                    items.append({
                        "ten_hang":   ic[0].strip(),
                        "so_luong":   sl,
                        "don_gia":    don_gia,
                        "thanh_tien": don_gia * sl,
                    })
                    j += 1
                elif len(ic) == 40 and ic[0].isdigit():
                    break
                else:
                    j += 1
                    if j - i > 30:
                        break

            inv["items"] = items
            inv["so_mon"] = sum(it["so_luong"] for it in items)

            # Parse datetime
            dt = _parse_dt(inv["ngay"], inv["gio"])
            if dt:
                inv["datetime"]         = dt
                inv["ngay_fmt"]         = dt.strftime("%d/%m/%Y")
                inv["thu"]              = ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"][dt.weekday()]
                inv["thu_idx"]          = dt.weekday()
                inv["tuan_trong_thang"] = (dt.day - 1) // 7 + 1
                inv["thang"]            = dt.strftime("%m/%Y")
                inv["nam"]              = dt.year
                inv["hour"]             = dt.hour
                # ISO week
                inv["tuan_iso"]         = f"Tuần {dt.isocalendar()[1]} ({dt.year})"
                inv["date_only"]        = dt.date()

            invoices.append(inv)
            i = j
        else:
            i += 1

    return invoices


def _to_int(s):
    try:
        return int(str(s).replace(",", "").strip())
    except:
        return 0


def _parse_dt(ngay, gio):
    try:
        d, m, y = ngay.split("/")
        h, mi   = gio.split(":")
        return datetime(int(y), int(m), int(d), int(h), int(mi))
    except:
        return None


def normalize_name(name: str) -> str:
    """Chuẩn hoá tên món để gom nhóm."""
    n = name.strip().lower()
    n = re.sub(r"\s+", " ", n)
    return n


# ──────────────────────────────────────────
# CHART HELPERS
# ──────────────────────────────────────────
CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=WHITE, size=12),
    margin=dict(l=8, r=8, t=32, b=8),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=WHITE)),
    xaxis=dict(gridcolor=NAVY3, linecolor=NAVY3),
    yaxis=dict(gridcolor=NAVY3, linecolor=NAVY3),
)

def fmt_vnd(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.0f}k"
    return str(n)

def fmt_full(n):
    return f"{n:,.0f}đ"


# ──────────────────────────────────────────
# METRIC CARD
# ──────────────────────────────────────────
def metric_card(label, value, sub="", accent=False):
    cls = "metric-card metric-accent" if accent else "metric-card"
    return f"""
    <div class="{cls}">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-sub">{sub}</div>
    </div>
    """

def section_title(text):
    st.markdown(f'<div class="section-title">{text}</div>', unsafe_allow_html=True)


# ──────────────────────────────────────────
# SIDEBAR — UPLOAD & FILTER
# ──────────────────────────────────────────
with st.sidebar:
    st.markdown(f"<h2 style='color:{TEAL};margin-bottom:4px'>☕ Fabi Dashboard</h2>", unsafe_allow_html=True)
    st.caption("Phân tích doanh thu từ dữ liệu Fabi")
    st.divider()

    uploaded = st.file_uploader(
        "📂 Tải file dữ liệu (.xls từ Fabi)",
        type=["xls", "xlsx", "csv"],
        help="Xuất file từ Fabi → Báo cáo → Danh sách hoá đơn → Export XLS",
    )

    st.divider()
    st.markdown("**📅 Khung thời gian**")
    timeframe_opt = st.selectbox(
        "Xem theo",
        ["Tất cả", "Theo ngày", "Theo tuần", "Theo tháng", "Tuỳ chọn ngày"],
        label_visibility="collapsed",
    )


# ──────────────────────────────────────────
# MAIN CONTENT
# ──────────────────────────────────────────
if not uploaded:
    st.markdown(f"""
    <div style="text-align:center; padding: 80px 0;">
        <div style="font-size:60px">☕</div>
        <h1 style="color:{WHITE}; margin:16px 0 8px">Fabi Sales Dashboard</h1>
        <p style="color:{GRAY}; font-size:16px">Tải file XLS từ Fabi lên để bắt đầu phân tích</p>
        <p style="color:{NAVY3}; font-size:13px; margin-top:24px">
        Fabi → Quản lý → Báo cáo → Danh sách hoá đơn → Xuất Excel
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ── PARSE ──
with st.spinner("Đang đọc dữ liệu..."):
    try:
        invoices = parse_fabi_file(uploaded.getvalue())
    except Exception as e:
        st.error(f"Lỗi đọc file: {e}")
        st.stop()

if not invoices:
    st.error("Không tìm thấy dữ liệu hợp lệ trong file.")
    st.stop()

# Only keep invoices with datetime
invoices_dt = [inv for inv in invoices if "datetime" in inv]
all_dates    = sorted(set(inv["date_only"] for inv in invoices_dt))
min_date     = all_dates[0]
max_date     = all_dates[-1]


# ── DATE FILTER ──
with st.sidebar:
    if timeframe_opt == "Tuỳ chọn ngày":
        d_from = st.date_input("Từ ngày", value=min_date, min_value=min_date, max_value=max_date)
        d_to   = st.date_input("Đến ngày", value=max_date, min_value=min_date, max_value=max_date)
        filtered = [inv for inv in invoices_dt if d_from <= inv["date_only"] <= d_to]
    elif timeframe_opt == "Theo ngày":
        sel_date = st.date_input("Chọn ngày", value=max_date, min_value=min_date, max_value=max_date)
        filtered = [inv for inv in invoices_dt if inv["date_only"] == sel_date]
    else:
        filtered = invoices_dt
        st.caption(f"Dữ liệu: {min_date.strftime('%d/%m/%Y')} → {max_date.strftime('%d/%m/%Y')}")

    st.divider()
    st.caption(f"📊 {len(filtered):,} hóa đơn")

    # Export buttons
    st.markdown("**📥 Xuất file**")
    if st.button("🌐 Xuất HTML Dashboard", use_container_width=True):
        st.session_state["export_html"] = True
    if st.button("📊 Xuất Excel báo cáo", use_container_width=True):
        st.session_state["export_excel"] = True


if not filtered:
    st.warning("Không có dữ liệu trong khoảng thời gian đã chọn.")
    st.stop()


# ──────────────────────────────────────────
# SECTION 1 — TỔNG QUAN
# ──────────────────────────────────────────
st.markdown(f"<h2 style='color:{WHITE};margin:24px 0 0'>📊 Tổng quan kinh doanh</h2>", unsafe_allow_html=True)

total_rev      = sum(inv["tong_hoa_don"] for inv in filtered)
total_inv      = len(filtered)
total_items    = sum(inv["so_mon"] for inv in filtered)
avg_order      = total_rev // total_inv if total_inv else 0
num_days       = len(set(inv["date_only"] for inv in filtered))
rev_per_day    = total_rev // num_days if num_days else 0
multi_orders   = [inv for inv in filtered if inv["so_mon"] >= 2]
pct_multi      = len(multi_orders) / total_inv * 100 if total_inv else 0
avg_items_ord  = total_items / total_inv if total_inv else 0

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(metric_card("Doanh thu", fmt_vnd(total_rev), fmt_full(total_rev), accent=True), unsafe_allow_html=True)
with c2:
    st.markdown(metric_card("Số hóa đơn", f"{total_inv:,}", f"{num_days} ngày"), unsafe_allow_html=True)
with c3:
    st.markdown(metric_card("AOV trung bình", fmt_vnd(avg_order), fmt_full(avg_order)), unsafe_allow_html=True)
with c4:
    st.markdown(metric_card("Số món bán ra", f"{total_items:,}", f"{avg_items_ord:.1f} món/đơn"), unsafe_allow_html=True)
with c5:
    st.markdown(metric_card("Doanh thu / ngày", fmt_vnd(rev_per_day), fmt_full(rev_per_day)), unsafe_allow_html=True)


# ──────────────────────────────────────────
# SECTION 2 — DOANH THU THEO THỜI GIAN
# ──────────────────────────────────────────
section_title("📈 Doanh thu theo thời gian")

# Aggregate by timeframe
if timeframe_opt in ["Tất cả", "Tuỳ chọn ngày", "Theo tuần", "Theo tháng"]:
    if timeframe_opt == "Theo tháng":
        group_key = lambda inv: inv["thang"]
        group_label = "Tháng"
        sort_key = lambda x: datetime.strptime(x, "%m/%Y")
    elif timeframe_opt == "Theo tuần":
        group_key = lambda inv: inv["tuan_iso"]
        group_label = "Tuần"
        sort_key = lambda x: x
    else:
        group_key = lambda inv: inv["date_only"].strftime("%d/%m")
        group_label = "Ngày"
        sort_key = lambda x: datetime.strptime(x, "%d/%m")

    rev_by_time   = defaultdict(int)
    inv_by_time   = defaultdict(int)
    items_by_time = defaultdict(int)
    for inv in filtered:
        k = group_key(inv)
        rev_by_time[k]   += inv["tong_hoa_don"]
        inv_by_time[k]   += 1
        items_by_time[k] += inv["so_mon"]

    try:
        sorted_keys = sorted(rev_by_time.keys(), key=sort_key)
    except:
        sorted_keys = sorted(rev_by_time.keys())

    df_time = pd.DataFrame({
        group_label:     sorted_keys,
        "Doanh thu (đ)": [rev_by_time[k] for k in sorted_keys],
        "Số đơn":        [inv_by_time[k] for k in sorted_keys],
        "Số món":        [items_by_time[k] for k in sorted_keys],
        "AOV":           [rev_by_time[k] // max(inv_by_time[k], 1) for k in sorted_keys],
    })

    tab1, tab2, tab3 = st.tabs(["💰 Doanh thu", "📋 Số đơn", "🍹 AOV"])
    
    with tab1:
        fig = px.bar(df_time, x=group_label, y="Doanh thu (đ)",
                     color_discrete_sequence=[TEAL],
                     text=df_time["Doanh thu (đ)"].apply(fmt_vnd))
        fig.update_traces(textposition="outside", textfont=dict(color=WHITE, size=11))
        fig.update_layout(**CHART_LAYOUT, height=320)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        fig2 = px.bar(df_time, x=group_label, y="Số đơn",
                      color_discrete_sequence=[GOLD],
                      text="Số đơn")
        fig2.update_traces(textposition="outside", textfont=dict(color=WHITE, size=11))
        fig2.update_layout(**CHART_LAYOUT, height=320)
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        fig3 = px.line(df_time, x=group_label, y="AOV",
                       markers=True, color_discrete_sequence=[GREEN])
        fig3.update_traces(line=dict(width=2.5), marker=dict(size=8))
        fig3.update_layout(**CHART_LAYOUT, height=320)
        st.plotly_chart(fig3, use_container_width=True)

else:
    # Single day — show hourly
    hourly_rev = defaultdict(int)
    hourly_inv = defaultdict(int)
    for inv in filtered:
        h = inv["hour"]
        hourly_rev[h] += inv["tong_hoa_don"]
        hourly_inv[h] += 1

    df_hour = pd.DataFrame({
        "Giờ":   [f"{h:02d}:00" for h in range(24)],
        "Doanh thu": [hourly_rev.get(h, 0) for h in range(24)],
        "Số đơn":    [hourly_inv.get(h, 0) for h in range(24)],
    })
    fig = px.bar(df_hour, x="Giờ", y="Doanh thu",
                 color_discrete_sequence=[TEAL],
                 text=df_hour["Doanh thu"].apply(fmt_vnd))
    fig.update_traces(textposition="outside", textfont=dict(color=WHITE, size=10))
    fig.update_layout(**CHART_LAYOUT, height=280, title="Doanh thu theo giờ trong ngày")
    st.plotly_chart(fig, use_container_width=True)


# ──────────────────────────────────────────
# SECTION 3 — AOV PHÂN TÍCH SÂU
# ──────────────────────────────────────────
section_title("🧮 AOV — Phân tích trung bình đơn hàng")

col_left, col_right = st.columns(2)

with col_left:
    # AOV theo thứ
    aov_thu = defaultdict(list)
    for inv in filtered:
        aov_thu[inv["thu"]].append(inv["tong_hoa_don"])

    thu_order = ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"]
    df_aov_thu = pd.DataFrame({
        "Thứ":     [t for t in thu_order if t in aov_thu],
        "AOV":     [sum(aov_thu[t])//len(aov_thu[t]) for t in thu_order if t in aov_thu],
        "Số đơn":  [len(aov_thu[t]) for t in thu_order if t in aov_thu],
    })
    fig_aov = px.bar(df_aov_thu, x="Thứ", y="AOV",
                     color="AOV", color_continuous_scale=[[0, NAVY3],[0.5, TEAL],[1, GOLD]],
                     text=df_aov_thu["AOV"].apply(fmt_vnd),
                     title="AOV theo thứ trong tuần")
    fig_aov.update_traces(textposition="outside", textfont=dict(color=WHITE, size=11))
    fig_aov.update_coloraxes(showscale=False)
    fig_aov.update_layout(**CHART_LAYOUT, height=280)
    st.plotly_chart(fig_aov, use_container_width=True)

with col_right:
    # AOV theo tuần trong tháng
    aov_tuan = defaultdict(list)
    for inv in filtered:
        k = f"Tuần {inv['tuan_trong_thang']}"
        aov_tuan[k].append(inv["tong_hoa_don"])

    df_aov_tuan = pd.DataFrame({
        "Tuần":   sorted(aov_tuan.keys()),
        "AOV":    [sum(aov_tuan[k])//len(aov_tuan[k]) for k in sorted(aov_tuan.keys())],
        "Số đơn": [len(aov_tuan[k]) for k in sorted(aov_tuan.keys())],
    })
    fig_tuan = px.bar(df_aov_tuan, x="Tuần", y="AOV",
                      color_discrete_sequence=[GOLD],
                      text=df_aov_tuan["AOV"].apply(fmt_vnd),
                      title="AOV theo tuần trong tháng")
    fig_tuan.update_traces(textposition="outside", textfont=dict(color=WHITE, size=11))
    fig_tuan.update_layout(**CHART_LAYOUT, height=280)
    st.plotly_chart(fig_tuan, use_container_width=True)


# ──────────────────────────────────────────
# SECTION 4 — PHÂN TÍCH ĐƠN NHÓM (2+ MÓN)
# ──────────────────────────────────────────
section_title("👥 Phân tích đơn nhóm — khách đi đôi / đi nhóm")

single_orders = [inv for inv in filtered if inv["so_mon"] == 1]
pair_orders   = [inv for inv in filtered if inv["so_mon"] == 2]
group_orders  = [inv for inv in filtered if inv["so_mon"] >= 3]

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(metric_card("Đơn 1 món", f"{len(single_orders):,}",
                f"{len(single_orders)/total_inv*100:.0f}% tổng đơn"), unsafe_allow_html=True)
with c2:
    st.markdown(metric_card("Đơn 2 món (đôi)", f"{len(pair_orders):,}",
                f"{len(pair_orders)/total_inv*100:.0f}% tổng đơn", accent=True), unsafe_allow_html=True)
with c3:
    st.markdown(metric_card("Đơn 3+ món (nhóm)", f"{len(group_orders):,}",
                f"{len(group_orders)/total_inv*100:.0f}% tổng đơn"), unsafe_allow_html=True)
with c4:
    avg_multi_rev = sum(inv["tong_hoa_don"] for inv in multi_orders) // len(multi_orders) if multi_orders else 0
    st.markdown(metric_card("AOV đơn nhóm", fmt_vnd(avg_multi_rev),
                "AOV cao hơn đơn lẻ"), unsafe_allow_html=True)

# Giờ cao điểm khách nhóm
col_l, col_r = st.columns(2)

with col_l:
    hour_multi = defaultdict(int)
    hour_single = defaultdict(int)
    for inv in filtered:
        if inv["so_mon"] >= 2:
            hour_multi[inv["hour"]] += 1
        else:
            hour_single[inv["hour"]] += 1

    df_hour_type = pd.DataFrame({
        "Giờ":         [f"{h:02d}:00" for h in range(24)],
        "Đơn nhóm (2+)": [hour_multi.get(h, 0) for h in range(24)],
        "Đơn lẻ (1 món)": [hour_single.get(h, 0) for h in range(24)],
    })
    fig_hr = px.bar(df_hour_type, x="Giờ",
                    y=["Đơn nhóm (2+)", "Đơn lẻ (1 món)"],
                    color_discrete_map={"Đơn nhóm (2+)": TEAL, "Đơn lẻ (1 món)": NAVY3},
                    barmode="stack",
                    title="Phân bố đơn theo giờ")
    fig_hr.update_layout(**CHART_LAYOUT, height=280)
    st.plotly_chart(fig_hr, use_container_width=True)

with col_r:
    # Pie chart tỉ lệ đơn
    fig_pie = px.pie(
        values=[len(single_orders), len(pair_orders), len(group_orders)],
        names=["1 món", "2 món", "3+ món"],
        color_discrete_sequence=[NAVY3, TEAL, GOLD],
        title="Tỉ lệ cỡ đơn",
        hole=0.5,
    )
    fig_pie.update_layout(**CHART_LAYOUT, height=280)
    fig_pie.update_traces(textfont=dict(color=WHITE))
    st.plotly_chart(fig_pie, use_container_width=True)

# Thứ nào nhiều đơn nhóm
thu_multi_pct = {}
for t in ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"]:
    inv_thu = [inv for inv in filtered if inv["thu"] == t]
    if inv_thu:
        multi_thu = [inv for inv in inv_thu if inv["so_mon"] >= 2]
        thu_multi_pct[t] = len(multi_thu) / len(inv_thu) * 100

df_thu_multi = pd.DataFrame({
    "Thứ": list(thu_multi_pct.keys()),
    "% đơn nhóm": [round(v, 1) for v in thu_multi_pct.values()],
})
fig_thu_m = px.bar(df_thu_multi, x="Thứ", y="% đơn nhóm",
                   color_discrete_sequence=[GREEN],
                   text=df_thu_multi["% đơn nhóm"].apply(lambda x: f"{x:.0f}%"),
                   title="% đơn nhóm (2+ món) theo thứ")
fig_thu_m.update_traces(textposition="outside", textfont=dict(color=WHITE, size=11))
fig_thu_m.update_layout(**CHART_LAYOUT, height=240,
                         yaxis=dict(range=[0, 100], gridcolor=NAVY3))
st.plotly_chart(fig_thu_m, use_container_width=True)


# ──────────────────────────────────────────
# SECTION 5 — TOP MÓN BÁN CHẠY
# ──────────────────────────────────────────
section_title("🏆 Top 10 món bán chạy nhất")

item_map = {}
for inv in filtered:
    for it in inv["items"]:
        nm = normalize_name(it["ten_hang"])
        if not nm:
            continue
        if nm not in item_map:
            item_map[nm] = {"ten_hang": it["ten_hang"], "so_luong": 0, "doanh_thu": 0}
        item_map[nm]["so_luong"]  += it["so_luong"]
        item_map[nm]["doanh_thu"] += it["thanh_tien"]

top10 = sorted(item_map.values(), key=lambda x: x["so_luong"], reverse=True)[:10]
total_qty = sum(it["so_luong"] for it in top10)

col_chart, col_table = st.columns([1.2, 0.8])

with col_chart:
    df_top = pd.DataFrame(top10)
    df_top["Tỉ lệ %"] = (df_top["so_luong"] / sum(it["so_luong"] for it in item_map.values()) * 100).round(1)
    fig_top = px.bar(df_top.sort_values("so_luong"), x="so_luong", y="ten_hang",
                     orientation="h",
                     color="so_luong",
                     color_continuous_scale=[[0, NAVY3],[0.5, TEAL],[1, GOLD]],
                     text=df_top.sort_values("so_luong")["so_luong"],
                     labels={"so_luong": "Số lượng", "ten_hang": ""})
    fig_top.update_coloraxes(showscale=False)
    fig_top.update_traces(textposition="outside", textfont=dict(color=WHITE, size=11))
    fig_top.update_layout(**CHART_LAYOUT, height=360)
    st.plotly_chart(fig_top, use_container_width=True)

with col_table:
    st.markdown(f"""
    <table style="width:100%; font-size:13px; border-collapse:collapse">
    <thead>
      <tr style="border-bottom:1px solid {NAVY3}; color:{GRAY}">
        <th style="padding:8px 6px; text-align:left">#</th>
        <th style="padding:8px 6px; text-align:left">Món</th>
        <th style="padding:8px 6px; text-align:right">SL</th>
        <th style="padding:8px 6px; text-align:right">Rev</th>
        <th style="padding:8px 6px; text-align:right">%</th>
      </tr>
    </thead>
    <tbody>
    {"".join(f'''
      <tr style="border-bottom:1px solid {NAVY3}22">
        <td style="padding:6px; color:{GRAY}">{i+1}</td>
        <td style="padding:6px; color:{WHITE}">{it["ten_hang"]}</td>
        <td style="padding:6px; text-align:right; font-weight:700; color:{TEAL}">{it["so_luong"]}</td>
        <td style="padding:6px; text-align:right; color:{GRAY}">{fmt_vnd(it["doanh_thu"])}</td>
        <td style="padding:6px; text-align:right; color:{GOLD}">{it["so_luong"]/sum(x["so_luong"] for x in item_map.values())*100:.0f}%</td>
      </tr>
    ''' for i, it in enumerate(top10))}
    </tbody>
    </table>
    """, unsafe_allow_html=True)


# ──────────────────────────────────────────
# SECTION 6 — GIỜ CAO ĐIỂM
# ──────────────────────────────────────────
section_title("⏰ Phân tích giờ cao điểm")

hourly_all = defaultdict(lambda: {"rev": 0, "inv": 0})
for inv in filtered:
    h = inv["hour"]
    hourly_all[h]["rev"] += inv["tong_hoa_don"]
    hourly_all[h]["inv"] += 1

df_hourly = pd.DataFrame({
    "Giờ":        [f"{h:02d}:00" for h in range(24)],
    "Doanh thu":  [hourly_all[h]["rev"] for h in range(24)],
    "Số đơn":     [hourly_all[h]["inv"] for h in range(24)],
    "AOV":        [hourly_all[h]["rev"]//hourly_all[h]["inv"] if hourly_all[h]["inv"] else 0 for h in range(24)],
})
peak_h = df_hourly["Số đơn"].idxmax()

fig_h2 = make_subplots(specs=[[{"secondary_y": True}]])
fig_h2.add_trace(
    go.Bar(x=df_hourly["Giờ"], y=df_hourly["Số đơn"],
           name="Số đơn", marker_color=TEAL, opacity=0.8),
    secondary_y=False,
)
fig_h2.add_trace(
    go.Scatter(x=df_hourly["Giờ"], y=df_hourly["AOV"],
               name="AOV", line=dict(color=GOLD, width=2.5), mode="lines+markers",
               marker=dict(size=6)),
    secondary_y=True,
)
fig_h2.update_layout(
    **CHART_LAYOUT,
    height=300,
    title=f"Số đơn & AOV theo giờ — Peak: {peak_h:02d}:00 ({df_hourly.iloc[peak_h]['Số đơn']} đơn)",
    legend=dict(bgcolor="rgba(0,0,0,0)"),
)
fig_h2.update_yaxes(gridcolor=NAVY3, linecolor=NAVY3)
st.plotly_chart(fig_h2, use_container_width=True)


# ──────────────────────────────────────────
# SECTION 7 — THANH TOÁN & CHI TIẾT
# ──────────────────────────────────────────
section_title("💳 Phương thức thanh toán")

transfer_rev = sum(inv["tong_hoa_don"] for inv in filtered if "TRANSFER" in inv["pttt"])
cod_rev      = sum(inv["tong_hoa_don"] for inv in filtered if "COD" in inv["pttt"])
transfer_cnt = sum(1 for inv in filtered if "TRANSFER" in inv["pttt"])
cod_cnt      = sum(1 for inv in filtered if "COD" in inv["pttt"])

c1, c2 = st.columns(2)
with c1:
    fig_pttt_rev = px.pie(
        values=[transfer_rev, cod_rev],
        names=[f"Chuyển khoản ({fmt_vnd(transfer_rev)})", f"Tiền mặt ({fmt_vnd(cod_rev)})"],
        color_discrete_sequence=[TEAL, GOLD],
        title="Tỉ lệ doanh thu", hole=0.5,
    )
    fig_pttt_rev.update_layout(**CHART_LAYOUT, height=260)
    fig_pttt_rev.update_traces(textfont=dict(color=WHITE))
    st.plotly_chart(fig_pttt_rev, use_container_width=True)

with c2:
    fig_pttt_cnt = px.pie(
        values=[transfer_cnt, cod_cnt],
        names=[f"Chuyển khoản ({transfer_cnt} đơn)", f"Tiền mặt ({cod_cnt} đơn)"],
        color_discrete_sequence=[TEAL, GOLD],
        title="Tỉ lệ số đơn", hole=0.5,
    )
    fig_pttt_cnt.update_layout(**CHART_LAYOUT, height=260)
    fig_pttt_cnt.update_traces(textfont=dict(color=WHITE))
    st.plotly_chart(fig_pttt_cnt, use_container_width=True)


# ──────────────────────────────────────────
# SECTION 8 — BẢNG CHI TIẾT
# ──────────────────────────────────────────
section_title("📋 Bảng chi tiết theo ngày")

day_detail = defaultdict(lambda: {"rev": 0, "inv": 0, "items": 0, "multi": 0})
for inv in filtered:
    dk = inv["date_only"]
    day_detail[dk]["rev"]   += inv["tong_hoa_don"]
    day_detail[dk]["inv"]   += 1
    day_detail[dk]["items"] += inv["so_mon"]
    if inv["so_mon"] >= 2:
        day_detail[dk]["multi"] += 1

df_detail = pd.DataFrame([
    {
        "Ngày":          k.strftime("%d/%m/%Y"),
        "Doanh thu":     fmt_full(v["rev"]),
        "Số đơn":        v["inv"],
        "Số món":        v["items"],
        "AOV":           fmt_vnd(v["rev"] // v["inv"]) if v["inv"] else "0",
        "Đơn nhóm":      v["multi"],
        "% Đơn nhóm":    f"{v['multi']/v['inv']*100:.0f}%" if v["inv"] else "0%",
    }
    for k, v in sorted(day_detail.items())
])

st.dataframe(
    df_detail,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Ngày": st.column_config.TextColumn(width=120),
        "Doanh thu": st.column_config.TextColumn(width=130),
    }
)


# ──────────────────────────────────────────
# EXPORT HTML
# ──────────────────────────────────────────
def build_html_export(filtered_data: list) -> str:
    """Build standalone HTML dashboard từ data đã lọc."""
    # Prepare data for JS
    days_sorted = sorted(set(inv["date_only"].strftime("%d/%m") for inv in filtered_data))
    
    rev_by_day   = defaultdict(int)
    inv_by_day   = defaultdict(int)
    for inv in filtered_data:
        k = inv["date_only"].strftime("%d/%m")
        rev_by_day[k]   += inv["tong_hoa_don"]
        inv_by_day[k]   += 1
    
    item_map_html = {}
    for inv in filtered_data:
        for it in inv["items"]:
            nm = normalize_name(it["ten_hang"])
            if not nm: continue
            if nm not in item_map_html:
                item_map_html[nm] = {"name": it["ten_hang"], "qty": 0, "rev": 0}
            item_map_html[nm]["qty"] += it["so_luong"]
            item_map_html[nm]["rev"] += it["thanh_tien"]
    top10_html = sorted(item_map_html.values(), key=lambda x: x["qty"], reverse=True)[:10]

    hour_data = defaultdict(int)
    for inv in filtered_data:
        hour_data[inv["hour"]] += 1

    total_rev_html  = sum(inv["tong_hoa_don"] for inv in filtered_data)
    total_inv_html  = len(filtered_data)
    total_items_html = sum(inv["so_mon"] for inv in filtered_data)
    avg_html        = total_rev_html // total_inv_html if total_inv_html else 0
    pct_multi_html  = len([inv for inv in filtered_data if inv["so_mon"] >= 2]) / total_inv_html * 100 if total_inv_html else 0
    transfer_r = sum(inv["tong_hoa_don"] for inv in filtered_data if "TRANSFER" in inv["pttt"])
    cod_r      = total_rev_html - transfer_r

    days_js  = json.dumps(days_sorted)
    revs_js  = json.dumps([rev_by_day[d] for d in days_sorted])
    invs_js  = json.dumps([inv_by_day[d] for d in days_sorted])
    top_js   = json.dumps(top10_html)
    hours_js = json.dumps([hour_data.get(h, 0) for h in range(24)])
    
    period_start = min(inv["date_only"] for inv in filtered_data).strftime("%d/%m/%Y")
    period_end   = max(inv["date_only"] for inv in filtered_data).strftime("%d/%m/%Y")

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Fabi Dashboard — {period_start} đến {period_end}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:system-ui,sans-serif;background:#0D1B2A;color:#F0F4F8;min-height:100vh}}
.header{{background:#1B2A3B;padding:20px 28px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #243447}}
.logo{{font-size:22px;font-weight:800;color:#2EC4B6}}
.period{{font-size:13px;color:#8FA0B2}}
.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;padding:20px 28px}}
.card{{background:#1B2A3B;border:1px solid #243447;border-radius:12px;padding:16px 20px}}
.card-label{{font-size:11px;color:#8FA0B2;text-transform:uppercase;letter-spacing:.8px;font-weight:600}}
.card-value{{font-size:26px;font-weight:800;margin:4px 0 2px;letter-spacing:-1px}}
.card-sub{{font-size:12px;color:#8FA0B2}}
.accent .card-value{{color:#2EC4B6}}
.section{{padding:0 28px 20px}}
.section h3{{font-size:14px;font-weight:700;color:#F0F4F8;border-left:3px solid #2EC4B6;padding-left:10px;margin-bottom:14px}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.chart-box{{background:#1B2A3B;border:1px solid #243447;border-radius:12px;padding:16px}}
.chart-box h4{{font-size:13px;color:#8FA0B2;margin-bottom:12px}}
.chart-wrap{{position:relative}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{text-align:left;padding:8px 10px;font-size:11px;color:#8FA0B2;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid #243447}}
td{{padding:7px 10px;border-bottom:1px solid #24344722}}
.teal{{color:#2EC4B6;font-weight:700}}
.gold{{color:#FFD166}}
.gray{{color:#8FA0B2}}
@media(max-width:600px){{
  .metrics{{grid-template-columns:repeat(2,1fr)}}
  .grid2{{grid-template-columns:1fr}}
}}
</style>
</head>
<body>
<div class="header">
  <div>
    <div class="logo">fabi</div>
    <div class="period">RU:TINE TRẦN PHÚ</div>
  </div>
  <div class="period">{period_start} — {period_end}</div>
</div>

<div class="metrics">
  <div class="card accent">
    <div class="card-label">Doanh thu</div>
    <div class="card-value">{fmt_vnd(total_rev_html)}</div>
    <div class="card-sub">{fmt_full(total_rev_html)}</div>
  </div>
  <div class="card">
    <div class="card-label">Số hóa đơn</div>
    <div class="card-value">{total_inv_html:,}</div>
    <div class="card-sub">&nbsp;</div>
  </div>
  <div class="card">
    <div class="card-label">AOV trung bình</div>
    <div class="card-value">{fmt_vnd(avg_html)}</div>
    <div class="card-sub">{fmt_full(avg_html)}</div>
  </div>
  <div class="card">
    <div class="card-label">Số món bán</div>
    <div class="card-value">{total_items_html:,}</div>
    <div class="card-sub">{total_items_html/total_inv_html:.1f} món/đơn</div>
  </div>
  <div class="card">
    <div class="card-label">Đơn nhóm 2+</div>
    <div class="card-value">{pct_multi_html:.0f}%</div>
    <div class="card-sub">{len([i for i in filtered_data if i["so_mon"]>=2])} đơn</div>
  </div>
</div>

<div class="section">
  <h3>📈 Doanh thu theo ngày</h3>
  <div class="chart-box">
    <div class="chart-wrap" style="height:220px">
      <canvas id="c1" role="img" aria-label="Doanh thu theo ngày"></canvas>
    </div>
  </div>
</div>

<div class="section">
  <h3>🏆 Top 10 món bán chạy</h3>
  <div class="chart-box">
    <table>
      <thead><tr><th>#</th><th>Tên món</th><th>SL</th><th>Doanh thu</th><th>Tỉ lệ</th></tr></thead>
      <tbody id="top-table"></tbody>
    </table>
  </div>
</div>

<div class="section">
  <div class="grid2">
    <div class="chart-box">
      <h4>⏰ Giờ cao điểm</h4>
      <div class="chart-wrap" style="height:180px">
        <canvas id="c2" role="img" aria-label="Giờ cao điểm"></canvas>
      </div>
    </div>
    <div class="chart-box">
      <h4>💳 Phương thức thanh toán</h4>
      <div class="chart-wrap" style="height:180px">
        <canvas id="c3" role="img" aria-label="Phương thức thanh toán"></canvas>
      </div>
    </div>
  </div>
</div>

<script>
const DAYS   = {days_js};
const REVS   = {revs_js};
const INVS   = {invs_js};
const TOP10  = {top_js};
const HOURS  = {hours_js};
const TRANS  = {transfer_r};
const COD    = {cod_r};
const TOTAL_QTY = TOP10.reduce((s,x)=>s+x.qty,0);

function fmtV(n){{
  if(n>=1e6) return (n/1e6).toFixed(1)+'M';
  if(n>=1e3) return (n/1e3).toFixed(0)+'k';
  return n;
}}

// Chart 1 — Revenue bar
const maxRev = Math.max(...REVS);
new Chart(document.getElementById('c1'), {{
  type:'bar',
  data:{{
    labels:DAYS,
    datasets:[{{
      label:'Doanh thu',
      data:REVS.map(v=>Math.round(v/1000)),
      backgroundColor: REVS.map(v=>v===maxRev?'#2EC4B6':'#243447'),
      borderRadius:6,borderSkipped:false
    }}]
  }},
  options:{{
    responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{display:false}}}},
    scales:{{
      x:{{grid:{{display:false}},ticks:{{color:'#8FA0B2',font:{{size:11}}}}}},
      y:{{grid:{{color:'#24344744'}},ticks:{{color:'#8FA0B2',callback:v=>v+'k',font:{{size:11}}}}}}
    }}
  }}
}});

// Top table
const tbody = document.getElementById('top-table');
TOP10.forEach((item,i)=>{{
  const pct = (item.qty/TOTAL_QTY*100).toFixed(0);
  tbody.innerHTML += `<tr>
    <td class="gray">${{i+1}}</td>
    <td>${{item.name}}</td>
    <td class="teal">${{item.qty}}</td>
    <td class="gray">${{fmtV(item.rev)}}</td>
    <td><div style="display:flex;align-items:center;gap:6px">
      <div style="width:${{Math.round(item.qty/TOP10[0].qty*60)}}px;height:5px;background:#2EC4B6;border-radius:3px"></div>
      <span class="gold">${{pct}}%</span>
    </div></td>
  </tr>`;
}});

// Chart 2 — Hourly
const peakH = HOURS.indexOf(Math.max(...HOURS));
new Chart(document.getElementById('c2'), {{
  type:'bar',
  data:{{
    labels:Array.from({{length:24}},(_,i)=>i.toString().padStart(2,'0')),
    datasets:[{{
      data:HOURS,
      backgroundColor:HOURS.map((v,i)=>i===peakH?'#FFD166':'#243447'),
      borderRadius:4,borderSkipped:false
    }}]
  }},
  options:{{
    responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{display:false}}}},
    scales:{{
      x:{{grid:{{display:false}},ticks:{{color:'#8FA0B2',font:{{size:9}}}}}},
      y:{{grid:{{color:'#24344744'}},ticks:{{color:'#8FA0B2',font:{{size:10}}}}}}
    }}
  }}
}});

// Chart 3 — PTTT
new Chart(document.getElementById('c3'), {{
  type:'doughnut',
  data:{{
    labels:[`Chuyển khoản (${{Math.round(TRANS/(TRANS+COD)*100)}}%)`,`Tiền mặt (${{Math.round(COD/(TRANS+COD)*100)}}%)`],
    datasets:[{{data:[TRANS,COD],backgroundColor:['#2EC4B6','#FFD166'],borderWidth:0}}]
  }},
  options:{{
    responsive:true,maintainAspectRatio:false,
    cutout:'55%',
    plugins:{{legend:{{position:'bottom',labels:{{color:'#F0F4F8',font:{{size:11}},padding:10}}}}}}
  }}
}});
</script>
</body>
</html>"""
    return html


# ── EXPORT BUTTONS ──
if st.session_state.get("export_html"):
    html_content = build_html_export(filtered)
    st.download_button(
        label="⬇️ Tải HTML Dashboard",
        data=html_content.encode("utf-8"),
        file_name=f"fabi_dashboard_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
        mime="text/html",
        use_container_width=True,
    )
    st.session_state["export_html"] = False

if st.session_state.get("export_excel"):
    # Build Excel report
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Sheet 1: Chi tiết ngày
        df_detail.to_excel(writer, sheet_name="Tổng quan theo ngày", index=False)
        # Sheet 2: Top sản phẩm
        df_top_full = pd.DataFrame(sorted(item_map.values(), key=lambda x: x["so_luong"], reverse=True))
        df_top_full.columns = ["Tên món", "Số lượng", "Doanh thu"]
        df_top_full.to_excel(writer, sheet_name="Top sản phẩm", index=False)
        # Sheet 3: Raw filtered
        df_raw = pd.DataFrame([{
            "Ngày": inv["ngay_fmt"],
            "Giờ": inv["gio"],
            "Bàn": inv["ban"],
            "Tổng hóa đơn": inv["tong_hoa_don"],
            "Giảm giá": inv["giam_gia"],
            "PTTT": "Chuyển khoản" if "TRANSFER" in inv["pttt"] else "Tiền mặt",
            "Số món": inv["so_mon"],
        } for inv in filtered])
        df_raw.to_excel(writer, sheet_name="Chi tiết hóa đơn", index=False)

    st.download_button(
        label="⬇️ Tải Excel Báo cáo",
        data=output.getvalue(),
        file_name=f"fabi_report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    st.session_state["export_excel"] = False


# ── FOOTER ──
st.markdown(f"""
<div style="text-align:center; padding:32px 0 16px; color:{GRAY}; font-size:12px">
  Fabi Dashboard · Data: {min_date.strftime('%d/%m/%Y')} → {max_date.strftime('%d/%m/%Y')} · {len(invoices_dt):,} hóa đơn
</div>
""", unsafe_allow_html=True)
