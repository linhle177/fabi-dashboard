import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re
from datetime import datetime
from collections import defaultdict
from bs4 import BeautifulSoup
import io

# ─────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="Fabi Dashboard",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Colors
NAVY_BG   = "#0B1929"
NAVY_CARD = "#112033"
NAVY_LINE = "#1C3045"
NAVY_HOVER= "#1A3050"
BLUE_ACT  = "#1D4E8F"   # active/accent navy blue
WHITE     = "#FFFFFF"
OFF_WHITE = "#E8EDF2"
GRAY_TEXT = "#7A90A8"
GRAY_SOFT = "#B0C0D0"
GOLD      = "#F5C842"
GREEN     = "#3DD68C"
RED_SOFT  = "#E05C6A"

# Chart base layout
CL = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=OFF_WHITE, family="Inter, system-ui, sans-serif", size=12),
    margin=dict(l=4, r=4, t=28, b=4),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=GRAY_SOFT, size=11)),
    xaxis=dict(gridcolor=NAVY_LINE, linecolor=NAVY_LINE, tickfont=dict(color=GRAY_TEXT, size=11)),
    yaxis=dict(gridcolor=NAVY_LINE, linecolor=NAVY_LINE, tickfont=dict(color=GRAY_TEXT, size=11)),
)

# ─────────────────────────────────────────────────────
# GLOBAL CSS — follow Image 2 layout & clean navy UI
# ─────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

*, html, body {{
    font-family: 'Inter', system-ui, sans-serif !important;
    box-sizing: border-box;
}}

/* App background */
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.main {{
    background: {NAVY_BG} !important;
}}
[data-testid="stAppViewContainer"] > .main > div {{
    padding-top: 0 !important;
}}

/* Sidebar */
[data-testid="stSidebar"] {{
    background: {NAVY_CARD} !important;
    border-right: 1px solid {NAVY_LINE};
}}
[data-testid="stSidebar"] section {{
    padding: 20px 16px;
}}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div {{
    color: {OFF_WHITE} !important;
}}
[data-testid="stSidebar"] .stSelectbox > div > div {{
    background: {NAVY_HOVER} !important;
    border: 1px solid {NAVY_LINE} !important;
    color: {WHITE} !important;
    border-radius: 8px;
}}

/* Buttons */
.stButton > button {{
    background: {BLUE_ACT} !important;
    color: {WHITE} !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    padding: 9px 16px !important;
    width: 100%;
    transition: opacity .15s;
}}
.stButton > button:hover {{ opacity: .85 !important; }}

/* File uploader */
[data-testid="stFileUploader"] {{
    background: {NAVY_HOVER} !important;
    border: 1.5px dashed {NAVY_LINE} !important;
    border-radius: 10px !important;
    padding: 12px !important;
}}
[data-testid="stFileUploader"] * {{ color: {GRAY_SOFT} !important; }}

/* Remove default streamlit padding */
.block-container {{ padding: 16px 24px 40px !important; }}

/* Top header bar */
.top-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 0 20px;
    border-bottom: 1px solid {NAVY_LINE};
    margin-bottom: 20px;
}}
.logo-text {{
    font-size: 22px;
    font-weight: 800;
    color: {WHITE};
    letter-spacing: -0.5px;
}}
.logo-sub {{
    font-size: 12px;
    color: {GRAY_TEXT};
    margin-top: 2px;
}}
.period-badge {{
    font-size: 12px;
    color: {GRAY_SOFT};
    background: {NAVY_CARD};
    border: 1px solid {NAVY_LINE};
    border-radius: 20px;
    padding: 5px 14px;
}}

/* Metric cards */
.metric-row {{ display: flex; gap: 12px; margin-bottom: 16px; }}
.mcard {{
    flex: 1;
    background: {NAVY_CARD};
    border: 1px solid {NAVY_LINE};
    border-radius: 12px;
    padding: 16px 18px;
}}
.mcard.accent {{ background: {BLUE_ACT}; border-color: {BLUE_ACT}; }}
.mcard .ml {{
    font-size: 11px;
    font-weight: 600;
    color: {GRAY_TEXT};
    text-transform: uppercase;
    letter-spacing: .8px;
}}
.mcard.accent .ml {{ color: rgba(255,255,255,.65); }}
.mcard .mv {{
    font-size: 28px;
    font-weight: 800;
    color: {WHITE};
    letter-spacing: -1px;
    margin: 4px 0 2px;
    line-height: 1.1;
}}
.mcard .ms {{
    font-size: 12px;
    color: {GRAY_TEXT};
}}
.mcard.accent .ms {{ color: rgba(255,255,255,.6); }}

/* Section headers */
.sec-head {{
    font-size: 13px;
    font-weight: 700;
    color: {OFF_WHITE};
    text-transform: uppercase;
    letter-spacing: .6px;
    margin: 20px 0 10px;
    display: flex;
    align-items: center;
    gap: 8px;
}}
.sec-head::after {{
    content: '';
    flex: 1;
    height: 1px;
    background: {NAVY_LINE};
}}

/* Chart cards */
.chart-card {{
    background: {NAVY_CARD};
    border: 1px solid {NAVY_LINE};
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
}}
.chart-title {{
    font-size: 13px;
    font-weight: 600;
    color: {GRAY_SOFT};
    margin-bottom: 12px;
}}

/* Table */
.data-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}}
.data-table th {{
    font-size: 10px;
    font-weight: 700;
    color: {GRAY_TEXT};
    text-transform: uppercase;
    letter-spacing: .6px;
    padding: 6px 10px;
    border-bottom: 1px solid {NAVY_LINE};
    text-align: left;
}}
.data-table td {{
    padding: 8px 10px;
    border-bottom: 1px solid {NAVY_LINE}44;
    color: {OFF_WHITE};
}}
.data-table tr:last-child td {{ border-bottom: none; }}
.data-table .num {{ font-weight: 700; color: {WHITE}; }}
.data-table .sub {{ color: {GRAY_TEXT}; font-size: 11px; }}
.rank-num {{ color: {GRAY_TEXT}; font-size: 12px; }}

/* Pill bar */
.pill-bar {{ display: inline-flex; gap: 6px; margin-bottom: 16px; }}
.pill {{
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
    border: 1.5px solid {NAVY_LINE};
    color: {GRAY_SOFT};
    cursor: pointer;
    background: transparent;
}}
.pill.on {{
    background: {BLUE_ACT};
    border-color: {BLUE_ACT};
    color: {WHITE};
    font-weight: 600;
}}

/* Tabs override */
[data-testid="stTabs"] [role="tablist"] {{
    background: transparent;
    border-bottom: 1px solid {NAVY_LINE};
    gap: 0;
}}
[data-testid="stTabs"] button[role="tab"] {{
    color: {GRAY_TEXT} !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 8px 16px !important;
    border-radius: 0 !important;
    background: transparent !important;
}}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
    color: {WHITE} !important;
    font-weight: 700 !important;
    border-bottom: 2px solid {BLUE_ACT} !important;
}}
[data-testid="stTabs"] [data-testid="stTabContent"] {{
    padding-top: 14px;
}}

/* Scrollbar */
::-webkit-scrollbar {{ width: 4px; height: 4px; }}
::-webkit-scrollbar-track {{ background: {NAVY_BG}; }}
::-webkit-scrollbar-thumb {{ background: {NAVY_LINE}; border-radius: 4px; }}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
# DATA PARSING
# ─────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def parse_fabi(file_bytes: bytes) -> list:
    try:
        content = file_bytes.decode("utf-8")
    except:
        content = file_bytes.decode("latin-1")

    soup  = BeautifulSoup(content, "html.parser")
    table = soup.find("table")
    if not table:
        raise ValueError("Không tìm thấy dữ liệu — hãy dùng file XLS xuất từ Fabi.")

    rows     = table.find_all("tr")
    invoices = []
    i        = 5

    while i < len(rows):
        cells = [td.get_text(strip=True) for td in rows[i].find_all("td")]
        if len(cells) == 40 and cells[0].isdigit():
            inv = dict(
                ngay=cells[6], gio=cells[7],
                ban=cells[11], trang_thai=cells[12],
                tong_tien=_int(cells[19]), giam_gia=_int(cells[20]),
                tong_hoa_don=_int(cells[33]), pttt=cells[36],
            )
            items, j = [], i + 1
            while j < len(rows):
                ic = [td.get_text(strip=True) for td in rows[j].find_all("td")]
                if len(ic) == 26 and ic[0] and not ic[0].isdigit():
                    dg, sl = _int(ic[3]), _int(ic[1])
                    items.append(dict(ten_hang=ic[0].strip(), so_luong=sl, don_gia=dg, thanh_tien=dg*sl))
                    j += 1
                elif len(ic) == 40 and ic[0].isdigit():
                    break
                else:
                    j += 1
                    if j - i > 30: break
            inv["items"]   = items
            inv["so_mon"]  = sum(x["so_luong"] for x in items)
            dt = _dt(inv["ngay"], inv["gio"])
            if dt:
                inv.update(
                    datetime=dt, date_only=dt.date(),
                    ngay_fmt=dt.strftime("%d/%m/%Y"),
                    thu=["T2","T3","T4","T5","T6","T7","CN"][dt.weekday()],
                    thu_full=["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"][dt.weekday()],
                    thu_idx=dt.weekday(),
                    tuan=f"Tuần {dt.isocalendar()[1]}",
                    tuan_trong_thang=(dt.day-1)//7+1,
                    thang=dt.strftime("%m/%Y"),
                    hour=dt.hour,
                )
            invoices.append(inv)
            i = j
        else:
            i += 1
    return invoices

def _int(s):
    try: return int(str(s).replace(",","").strip())
    except: return 0

def _dt(ngay, gio):
    try:
        d,m,y = ngay.split("/"); h,mi = gio.split(":")
        return datetime(int(y),int(m),int(d),int(h),int(mi))
    except: return None

def nn(name): return re.sub(r"\s+"," ", name.strip().lower())

def fv(n):
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000:     return f"{n/1_000:.0f}k"
    return str(n)

def ff(n): return f"{n:,.0f}đ"


# ─────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style='padding:4px 0 16px'>
        <div style='font-size:20px;font-weight:800;color:{WHITE}'>☕ Fabi</div>
        <div style='font-size:11px;color:{GRAY_TEXT};margin-top:2px'>Sales Dashboard</div>
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Tải file XLS từ Fabi",
        type=["xls","xlsx"],
        help="Fabi → Báo cáo → Danh sách hoá đơn → Xuất Excel",
    )

    st.markdown(f"<div style='height:1px;background:{NAVY_LINE};margin:16px 0'></div>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:12px;font-weight:600;color:{GRAY_SOFT};margin-bottom:8px'>Xem theo</div>", unsafe_allow_html=True)

    time_mode = st.selectbox("Xem theo", ["Tất cả dữ liệu","Chọn 1 ngày","Theo tuần","Theo tháng","Tuỳ chọn khoảng"], label_visibility="collapsed")

    # Date pickers based on mode
    date_from = date_to = single_day = None
    if time_mode == "Chọn 1 ngày":
        single_day = st.date_input("Ngày", label_visibility="collapsed")
    elif time_mode == "Tuỳ chọn khoảng":
        date_from = st.date_input("Từ ngày")
        date_to   = st.date_input("Đến ngày")

    st.markdown(f"<div style='height:1px;background:{NAVY_LINE};margin:16px 0'></div>", unsafe_allow_html=True)

    export_html  = st.button("⬇️  Xuất HTML Dashboard")
    export_excel = st.button("📊  Xuất Excel Báo cáo")


# ─────────────────────────────────────────────────────
# EMPTY STATE
# ─────────────────────────────────────────────────────
if not uploaded:
    st.markdown(f"""
    <div style='display:flex;flex-direction:column;align-items:center;justify-content:center;
                min-height:75vh;text-align:center;gap:12px'>
        <div style='font-size:52px'>☕</div>
        <div style='font-size:24px;font-weight:800;color:{WHITE}'>Fabi Sales Dashboard</div>
        <div style='font-size:14px;color:{GRAY_TEXT};max-width:340px;line-height:1.6'>
            Tải file <b style='color:{GRAY_SOFT}'>.xls</b> xuất từ Fabi lên thanh bên trái để bắt đầu phân tích doanh thu
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ─────────────────────────────────────────────────────
# PARSE + FILTER
# ─────────────────────────────────────────────────────
with st.spinner("Đang đọc dữ liệu..."):
    try:
        all_inv = parse_fabi(uploaded.getvalue())
    except Exception as e:
        st.error(f"Lỗi đọc file: {e}")
        st.stop()

inv_dt = [x for x in all_inv if "datetime" in x]
if not inv_dt:
    st.error("Không tìm thấy dữ liệu hợp lệ.")
    st.stop()

all_dates = sorted(set(x["date_only"] for x in inv_dt))
d_min, d_max = all_dates[0], all_dates[-1]

# Apply filter
if time_mode == "Chọn 1 ngày" and single_day:
    data = [x for x in inv_dt if x["date_only"] == single_day]
elif time_mode == "Tuỳ chọn khoảng" and date_from and date_to:
    data = [x for x in inv_dt if date_from <= x["date_only"] <= date_to]
else:
    data = inv_dt

if not data:
    st.warning("Không có dữ liệu trong khoảng đã chọn.")
    st.stop()

active_dates = sorted(set(x["date_only"] for x in data))
period_str   = f"{active_dates[0].strftime('%d/%m/%Y')} → {active_dates[-1].strftime('%d/%m/%Y')}"


# ─────────────────────────────────────────────────────
# COMPUTE METRICS
# ─────────────────────────────────────────────────────
total_rev    = sum(x["tong_hoa_don"] for x in data)
total_inv    = len(data)
total_items  = sum(x["so_mon"] for x in data)
aov          = total_rev // total_inv if total_inv else 0
num_days     = len(active_dates)
rev_per_day  = total_rev // num_days if num_days else 0
multi        = [x for x in data if x["so_mon"] >= 2]
pct_multi    = len(multi)/total_inv*100 if total_inv else 0
avg_items    = total_items/total_inv if total_inv else 0

# Product map
pmap = {}
for inv in data:
    for it in inv["items"]:
        k = nn(it["ten_hang"])
        if not k: continue
        if k not in pmap: pmap[k] = {"name": it["ten_hang"], "qty": 0, "rev": 0}
        pmap[k]["qty"] += it["so_luong"]
        pmap[k]["rev"] += it["thanh_tien"]
top10 = sorted(pmap.values(), key=lambda x: x["qty"], reverse=True)[:10]
total_qty_all = sum(x["so_luong"] for x in pmap.values())


# ─────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────
st.markdown(f"""
<div class="top-header">
    <div>
        <div class="logo-text">Fabi — RU:TINE TRẦN PHÚ</div>
        <div class="logo-sub">Sales Dashboard</div>
    </div>
    <div class="period-badge">{period_str}</div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
# METRICS ROW
# ─────────────────────────────────────────────────────
c1,c2,c3,c4,c5 = st.columns(5)
cards = [
    (c1, "Doanh thu",         fv(total_rev),           ff(total_rev),                  True),
    (c2, "Số hóa đơn",        f"{total_inv:,}",         f"{num_days} ngày",             False),
    (c3, "AOV trung bình",    fv(aov),                  ff(aov),                        False),
    (c4, "Số món bán",        f"{total_items:,}",       f"{avg_items:.1f} món / đơn",   False),
    (c5, "Đơn nhóm 2+ món",   f"{pct_multi:.0f}%",     f"{len(multi):,} đơn",          False),
]
for col, label, val, sub, accent in cards:
    acc = "accent" if accent else ""
    col.markdown(f"""
    <div class="mcard {acc}">
        <div class="ml">{label}</div>
        <div class="mv">{val}</div>
        <div class="ms">{sub}</div>
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
# SECTION: DOANH THU THEO THỜI GIAN
# ─────────────────────────────────────────────────────
st.markdown('<div class="sec-head">📈 Doanh thu theo thời gian</div>', unsafe_allow_html=True)

# Group key by mode
if time_mode in ["Tất cả dữ liệu","Tuỳ chọn khoảng"]:
    def gk(x): return x["date_only"].strftime("%d/%m")
    gkeys = [d.strftime("%d/%m") for d in active_dates]
    xlabel = "Ngày"
elif time_mode == "Theo tuần":
    def gk(x): return x["tuan"]
    gkeys = sorted(set(gk(x) for x in data))
    xlabel = "Tuần"
elif time_mode == "Theo tháng":
    def gk(x): return x["thang"]
    gkeys = sorted(set(gk(x) for x in data), key=lambda s: datetime.strptime(s,"%m/%Y"))
    xlabel = "Tháng"
else:
    def gk(x): return f"{x['hour']:02d}:00"
    gkeys = [f"{h:02d}:00" for h in range(24)]
    xlabel = "Giờ"

rev_g  = defaultdict(int)
inv_g  = defaultdict(int)
item_g = defaultdict(int)
for x in data:
    k = gk(x)
    rev_g[k]  += x["tong_hoa_don"]
    inv_g[k]  += 1
    item_g[k] += x["so_mon"]

aov_g = {k: rev_g[k]//inv_g[k] if inv_g[k] else 0 for k in gkeys}

t1,t2,t3 = st.tabs(["💰 Doanh thu","📋 Số đơn","📊 AOV theo ngày"])

with t1:
    max_rev = max((rev_g.get(k,0) for k in gkeys), default=1)
    fig = go.Figure(go.Bar(
        x=gkeys,
        y=[round(rev_g.get(k,0)/1000) for k in gkeys],
        marker_color=[BLUE_ACT if rev_g.get(k,0)==max_rev else NAVY_LINE for k in gkeys],
        marker_line_width=0,
        hovertemplate="%{x}<br><b>%{customdata}</b><extra></extra>",
        customdata=[ff(rev_g.get(k,0)) for k in gkeys],
    ))
    fig.update_layout(**CL, height=240, bargap=0.3,
        yaxis=dict(ticksuffix="k", gridcolor=NAVY_LINE, linecolor=NAVY_LINE, tickfont=dict(color=GRAY_TEXT,size=11)),
        xaxis=dict(gridcolor="rgba(0,0,0,0)", linecolor=NAVY_LINE, tickfont=dict(color=GRAY_TEXT,size=11)),
    )
    fig.update_traces(marker_cornerradius=4)
    st.plotly_chart(fig, use_container_width=True)

with t2:
    fig2 = go.Figure(go.Bar(
        x=gkeys, y=[inv_g.get(k,0) for k in gkeys],
        marker_color=BLUE_ACT, marker_line_width=0,
        hovertemplate="%{x}<br><b>%{y} đơn</b><extra></extra>",
    ))
    fig2.update_layout(**CL, height=240, bargap=0.3,
        yaxis=dict(gridcolor=NAVY_LINE, linecolor=NAVY_LINE, tickfont=dict(color=GRAY_TEXT,size=11)),
        xaxis=dict(gridcolor="rgba(0,0,0,0)", linecolor=NAVY_LINE, tickfont=dict(color=GRAY_TEXT,size=11)),
    )
    fig2.update_traces(marker_cornerradius=4)
    st.plotly_chart(fig2, use_container_width=True)

with t3:
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=gkeys, y=[aov_g.get(k,0) for k in gkeys],
        mode="lines+markers",
        line=dict(color=GOLD, width=2.5),
        marker=dict(size=7, color=GOLD),
        hovertemplate="%{x}<br>AOV: <b>%{customdata}</b><extra></extra>",
        customdata=[ff(aov_g.get(k,0)) for k in gkeys],
    ))
    fig3.update_layout(**CL, height=240,
        yaxis=dict(gridcolor=NAVY_LINE, linecolor=NAVY_LINE, tickfont=dict(color=GRAY_TEXT,size=11)),
        xaxis=dict(gridcolor="rgba(0,0,0,0)", linecolor=NAVY_LINE, tickfont=dict(color=GRAY_TEXT,size=11)),
    )
    st.plotly_chart(fig3, use_container_width=True)


# ─────────────────────────────────────────────────────
# SECTION: AOV PHÂN TÍCH SÂU  +  TOP MÓN
# ─────────────────────────────────────────────────────
st.markdown('<div class="sec-head">🧮 AOV & Top món</div>', unsafe_allow_html=True)

left, right = st.columns([1, 1])

with left:
    # AOV theo thứ
    aov_thu = defaultdict(list)
    for x in data: aov_thu[x["thu_full"]].append(x["tong_hoa_don"])
    thu_order = ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"]
    labels_t  = [t for t in thu_order if t in aov_thu]
    vals_t    = [sum(aov_thu[t])//len(aov_thu[t]) for t in labels_t]
    max_v = max(vals_t) if vals_t else 1

    fig_t = go.Figure(go.Bar(
        x=labels_t, y=vals_t,
        marker_color=[BLUE_ACT if v==max_v else NAVY_LINE for v in vals_t],
        marker_line_width=0,
        hovertemplate="%{x}<br>AOV: <b>%{customdata}</b><extra></extra>",
        customdata=[ff(v) for v in vals_t],
    ))
    fig_t.update_layout(**CL, height=220, title=dict(text="AOV theo thứ", font=dict(color=GRAY_SOFT,size=12)),
        bargap=0.35, bargroupgap=0,
        yaxis=dict(gridcolor=NAVY_LINE, linecolor=NAVY_LINE, tickfont=dict(color=GRAY_TEXT,size=10)),
        xaxis=dict(gridcolor="rgba(0,0,0,0)", linecolor=NAVY_LINE, tickfont=dict(color=GRAY_TEXT,size=10)),
    )
    fig_t.update_traces(marker_cornerradius=4)
    st.plotly_chart(fig_t, use_container_width=True)

with right:
    # Top 10 horizontal bar
    names  = [x["name"] for x in reversed(top10)]
    qtys   = [x["qty"]  for x in reversed(top10)]
    colors = [BLUE_ACT if q == max(qtys) else NAVY_HOVER for q in qtys]

    fig_top = go.Figure(go.Bar(
        x=qtys, y=names, orientation="h",
        marker_color=colors, marker_line_width=0,
        hovertemplate="%{y}<br>Số lượng: <b>%{x}</b><extra></extra>",
    ))
    fig_top.update_layout(**CL, height=300,
        title=dict(text="Top 10 món bán chạy", font=dict(color=GRAY_SOFT,size=12)),
        xaxis=dict(gridcolor=NAVY_LINE, linecolor=NAVY_LINE, tickfont=dict(color=GRAY_TEXT,size=10)),
        yaxis=dict(gridcolor="rgba(0,0,0,0)", linecolor="rgba(0,0,0,0)", tickfont=dict(color=OFF_WHITE,size=11)),
    )
    fig_top.update_traces(marker_cornerradius=4)
    st.plotly_chart(fig_top, use_container_width=True)


# ─────────────────────────────────────────────────────
# SECTION: ĐƠN NHÓM + GIỜ CAO ĐIỂM
# ─────────────────────────────────────────────────────
st.markdown('<div class="sec-head">👥 Đơn nhóm & Giờ cao điểm</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([1,1,1])

with col1:
    # Pie đơn nhóm
    s1 = len([x for x in data if x["so_mon"]==1])
    s2 = len([x for x in data if x["so_mon"]==2])
    s3 = len([x for x in data if x["so_mon"]>=3])
    fig_pie = go.Figure(go.Pie(
        labels=["1 món","2 món","3+ món"],
        values=[s1,s2,s3],
        hole=0.58,
        marker_colors=[NAVY_LINE, BLUE_ACT, GOLD],
        textfont=dict(color=WHITE, size=11),
        hovertemplate="%{label}: <b>%{value}</b> đơn (%{percent})<extra></extra>",
    ))
    fig_pie.update_layout(**CL, height=220,
        title=dict(text="Tỉ lệ cỡ đơn", font=dict(color=GRAY_SOFT,size=12)),
        legend=dict(font=dict(color=GRAY_SOFT,size=11), bgcolor="rgba(0,0,0,0)"),
        showlegend=True,
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    # % đơn nhóm theo thứ
    thu_pct = {}
    for t in ["T2","T3","T4","T5","T6","T7","CN"]:
        inv_t = [x for x in data if x["thu"]==t]
        if inv_t:
            multi_t = [x for x in inv_t if x["so_mon"]>=2]
            thu_pct[t] = round(len(multi_t)/len(inv_t)*100,1)
    if thu_pct:
        fig_tp = go.Figure(go.Bar(
            x=list(thu_pct.keys()), y=list(thu_pct.values()),
            marker_color=GREEN, marker_line_width=0,
            hovertemplate="%{x}: <b>%{y}%</b> đơn nhóm<extra></extra>",
        ))
        fig_tp.update_layout(**CL, height=220,
            title=dict(text="% đơn nhóm theo thứ", font=dict(color=GRAY_SOFT,size=12)),
            bargap=0.35,
            yaxis=dict(range=[0,100], ticksuffix="%", gridcolor=NAVY_LINE, linecolor=NAVY_LINE, tickfont=dict(color=GRAY_TEXT,size=10)),
            xaxis=dict(gridcolor="rgba(0,0,0,0)", linecolor=NAVY_LINE, tickfont=dict(color=GRAY_TEXT,size=10)),
        )
        fig_tp.update_traces(marker_cornerradius=4)
        st.plotly_chart(fig_tp, use_container_width=True)

with col3:
    # Hourly
    h_cnt   = defaultdict(int)
    h_multi = defaultdict(int)
    for x in data:
        h_cnt[x["hour"]] += 1
        if x["so_mon"] >= 2: h_multi[x["hour"]] += 1
    peak = max(h_cnt, key=h_cnt.get, default=12)

    fig_h = go.Figure()
    fig_h.add_trace(go.Bar(
        x=[f"{h:02d}" for h in range(24)],
        y=[h_cnt.get(h,0) for h in range(24)],
        marker_color=[GOLD if h==peak else NAVY_LINE for h in range(24)],
        marker_line_width=0,
        name="Tổng đơn",
        hovertemplate="%{x}:00 — <b>%{y} đơn</b><extra></extra>",
    ))
    fig_h.update_layout(**CL, height=220,
        title=dict(text=f"Giờ cao điểm — peak {peak:02d}:00", font=dict(color=GRAY_SOFT,size=12)),
        bargap=0.2, showlegend=False,
        xaxis=dict(gridcolor="rgba(0,0,0,0)", linecolor=NAVY_LINE, tickfont=dict(color=GRAY_TEXT,size=9)),
        yaxis=dict(gridcolor=NAVY_LINE, linecolor=NAVY_LINE, tickfont=dict(color=GRAY_TEXT,size=10)),
    )
    fig_h.update_traces(marker_cornerradius=3)
    st.plotly_chart(fig_h, use_container_width=True)


# ─────────────────────────────────────────────────────
# SECTION: THANH TOÁN + TOP TABLE
# ─────────────────────────────────────────────────────
st.markdown('<div class="sec-head">💳 Thanh toán & Chi tiết sản phẩm</div>', unsafe_allow_html=True)

p1, p2 = st.columns([1, 2])

with p1:
    tr_r = sum(x["tong_hoa_don"] for x in data if "TRANSFER" in x["pttt"])
    cd_r = total_rev - tr_r
    tr_n = sum(1 for x in data if "TRANSFER" in x["pttt"])
    cd_n = total_inv - tr_n

    fig_pt = go.Figure(go.Pie(
        labels=[f"Chuyển khoản","Tiền mặt"],
        values=[tr_r, cd_r],
        hole=0.58,
        marker_colors=[BLUE_ACT, NAVY_LINE],
        textfont=dict(color=WHITE, size=11),
        hovertemplate="%{label}<br>Doanh thu: <b>%{customdata}</b><extra></extra>",
        customdata=[ff(tr_r), ff(cd_r)],
    ))
    fig_pt.update_layout(**CL, height=200,
        title=dict(text="Phương thức thanh toán", font=dict(color=GRAY_SOFT,size=12)),
        legend=dict(font=dict(color=GRAY_SOFT,size=11), bgcolor="rgba(0,0,0,0)"),
        annotations=[dict(
            text=f"<b>{round(tr_r/total_rev*100) if total_rev else 0}%</b><br><span style='font-size:10px'>CK</span>",
            x=0.5, y=0.5, font=dict(color=WHITE, size=14), showarrow=False
        )]
    )
    st.plotly_chart(fig_pt, use_container_width=True)

    st.markdown(f"""
    <div style='font-size:12px;color:{GRAY_TEXT};line-height:1.8;padding:4px 0'>
        <span style='color:{OFF_WHITE};font-weight:600'>Chuyển khoản:</span> {tr_n:,} đơn · {fv(tr_r)}<br>
        <span style='color:{OFF_WHITE};font-weight:600'>Tiền mặt:</span> {cd_n:,} đơn · {fv(cd_r)}
    </div>""", unsafe_allow_html=True)

with p2:
    # Top products table
    rows_html = ""
    for i, it in enumerate(top10):
        pct = it["qty"]/total_qty_all*100 if total_qty_all else 0
        bar_w = round(it["qty"]/top10[0]["qty"]*80) if top10 else 0
        rows_html += f"""
        <tr>
            <td class='rank-num'>{i+1}</td>
            <td>{it['name']}</td>
            <td class='num'>{it['qty']}</td>
            <td class='sub'>{fv(it['rev'])}</td>
            <td>
                <div style='display:flex;align-items:center;gap:6px'>
                    <div style='width:{bar_w}px;height:4px;background:{BLUE_ACT};border-radius:2px'></div>
                    <span style='color:{GRAY_TEXT};font-size:11px'>{pct:.0f}%</span>
                </div>
            </td>
        </tr>"""
    st.markdown(f"""
    <div style='font-size:12px;font-weight:600;color:{GRAY_SOFT};margin-bottom:10px'>Top 10 món bán chạy</div>
    <table class='data-table'>
        <thead><tr><th>#</th><th>Tên món</th><th>SL</th><th>Doanh thu</th><th>Tỉ lệ</th></tr></thead>
        <tbody>{rows_html}</tbody>
    </table>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
# SECTION: BẢNG CHI TIẾT
# ─────────────────────────────────────────────────────
st.markdown('<div class="sec-head">📋 Chi tiết theo ngày</div>', unsafe_allow_html=True)

day_agg = defaultdict(lambda: dict(rev=0, inv=0, items=0, multi=0))
for x in data:
    d = x["date_only"]
    day_agg[d]["rev"]   += x["tong_hoa_don"]
    day_agg[d]["inv"]   += 1
    day_agg[d]["items"] += x["so_mon"]
    if x["so_mon"] >= 2: day_agg[d]["multi"] += 1

df_det = pd.DataFrame([{
    "Ngày":        k.strftime("%d/%m/%Y"),
    "Doanh thu":   ff(v["rev"]),
    "Số đơn":      v["inv"],
    "Số món":      v["items"],
    "AOV":         fv(v["rev"]//v["inv"]) if v["inv"] else "—",
    "Đơn 2+ món":  v["multi"],
    "% Đơn nhóm":  f"{v['multi']/v['inv']*100:.0f}%" if v["inv"] else "—",
} for k,v in sorted(day_agg.items())])

st.dataframe(
    df_det, use_container_width=True, hide_index=True,
    column_config={
        "Ngày":       st.column_config.TextColumn(width=110),
        "Doanh thu":  st.column_config.TextColumn(width=130),
        "AOV":        st.column_config.TextColumn(width=80),
    }
)


# ─────────────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────────────
if export_excel:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df_det.to_excel(w, sheet_name="Theo ngày", index=False)
        pd.DataFrame(top10).rename(columns={"name":"Món","qty":"SL","rev":"Doanh thu"}).to_excel(w, sheet_name="Top sản phẩm", index=False)
        pd.DataFrame([{
            "Ngày": x["ngay_fmt"], "Giờ": x["gio"], "Bàn": x["ban"],
            "Tổng": x["tong_hoa_don"], "Giảm": x["giam_gia"],
            "PTTT": "Chuyển khoản" if "TRANSFER" in x["pttt"] else "Tiền mặt",
            "Số món": x["so_mon"],
        } for x in data]).to_excel(w, sheet_name="Chi tiết hóa đơn", index=False)
    st.download_button("⬇️ Tải Excel", data=buf.getvalue(),
        file_name=f"fabi_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# Footer
st.markdown(f"""
<div style='text-align:center;padding:32px 0 8px;font-size:11px;color:{NAVY_LINE}'>
    Fabi Dashboard · {d_min.strftime('%d/%m/%Y')} – {d_max.strftime('%d/%m/%Y')} · {len(inv_dt):,} hóa đơn
</div>""", unsafe_allow_html=True)
