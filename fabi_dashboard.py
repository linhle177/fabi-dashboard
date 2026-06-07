import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
from datetime import datetime
from collections import defaultdict
from bs4 import BeautifulSoup
import io

st.set_page_config(
    page_title="Fabi Dashboard",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Colors
BG      = "#F5F3EF"
CARD    = "#FFFFFF"
DARK    = "#1A1A1A"
BORDER  = "#E8E4DC"
TEXT    = "#1A1A1A"
SUB     = "#888888"
NAVY    = "#1D3557"
NAVY_LT = "#DDE4EE"
GOLD    = "#F5C518"

# CSS — chỉ style những gì cần, không dùng * selector
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

html, body {{
    font-family: 'Inter', sans-serif !important;
    background: {BG} !important;
}}
[data-testid="stAppViewContainer"] > section > div {{
    background: {BG};
}}
[data-testid="stMain"] {{
    background: {BG} !important;
}}
.block-container {{
    padding: 0 32px 48px !important;
}}
[data-testid="stSidebar"] {{
    background: {CARD} !important;
    border-right: 1px solid {BORDER} !important;
}}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label {{
    color: {TEXT} !important;
}}
/* Tabs */
[data-testid="stTabs"] [role="tablist"] {{
    border-bottom: 1.5px solid {BORDER} !important;
    background: transparent;
}}
[data-testid="stTabs"] button[role="tab"] {{
    color: {SUB} !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    background: transparent !important;
    border-radius: 0 !important;
    padding: 8px 18px !important;
}}
[data-testid="stTabs"] button[aria-selected="true"] {{
    color: {TEXT} !important;
    font-weight: 700 !important;
    border-bottom: 2px solid {TEXT} !important;
}}
/* Metric cards */
.mc {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 14px;
    padding: 18px 20px;
}}
.mc.dk {{ background: {DARK}; border-color: {DARK}; }}
.mc .lb {{
    font-size: 10px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .8px;
    color: {SUB}; font-family: 'Inter', sans-serif;
}}
.mc.dk .lb {{ color: rgba(255,255,255,.45); }}
.mc .vl {{
    font-size: 30px; font-weight: 800; letter-spacing: -1.5px;
    color: {TEXT}; margin: 4px 0 2px; line-height: 1.1;
    font-family: 'Inter', sans-serif;
}}
.mc.dk .vl {{ color: #fff; }}
.mc .sb {{ font-size: 12px; color: {SUB}; font-family: 'Inter', sans-serif; }}
.mc.dk .sb {{ color: rgba(255,255,255,.4); }}
/* Header */
.hdr {{
    display: flex; align-items: center;
    justify-content: space-between;
    padding: 20px 0 18px;
    border-bottom: 1.5px solid {BORDER};
    margin-bottom: 24px;
}}
.hdr-logo {{
    font-size: 22px; font-weight: 900;
    color: {TEXT}; letter-spacing: -1px;
    font-family: 'Inter', sans-serif;
}}
.hdr-sub {{ font-size: 12px; color: {SUB}; margin-top: 1px; }}
.hdr-badge {{
    font-size: 12px; color: {SUB};
    background: {CARD}; border: 1px solid {BORDER};
    border-radius: 20px; padding: 5px 14px;
}}
/* Section title */
.sec {{
    font-size: 16px; font-weight: 700;
    color: {TEXT}; margin: 28px 0 14px;
    font-family: 'Inter', sans-serif;
}}
/* Table */
.ft {{ width:100%; border-collapse:collapse; font-size:13px; font-family:'Inter',sans-serif; }}
.ft th {{
    font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing:.6px; color:{SUB}; padding: 6px 10px;
    border-bottom: 1.5px solid {BORDER}; text-align:left;
}}
.ft td {{ padding: 9px 10px; border-bottom: 1px solid {BORDER}; color:{TEXT}; }}
.ft tr:last-child td {{ border-bottom: none; }}
.ft .n {{ font-weight: 700; }}
.ft .g {{ color: {SUB}; font-size: 11px; }}
.ft .rk {{ color: #ccc; font-size: 11px; }}
</style>
""", unsafe_allow_html=True)


# ── PARSE ────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def parse_fabi(fb: bytes):
    try: c = fb.decode("utf-8")
    except: c = fb.decode("latin-1")
    soup = BeautifulSoup(c, "html.parser")
    tbl  = soup.find("table")
    if not tbl: raise ValueError("Không tìm thấy dữ liệu trong file.")
    rows = tbl.find_all("tr")
    invs = []
    i    = 5
    while i < len(rows):
        cells = [td.get_text(strip=True) for td in rows[i].find_all("td")]
        if len(cells) == 40 and cells[0].isdigit():
            inv = dict(
                ngay=cells[6], gio=cells[7], ban=cells[11],
                tong_tien=_i(cells[19]), giam_gia=_i(cells[20]),
                tong_hoa_don=_i(cells[33]), pttt=cells[36]
            )
            items, j = [], i + 1
            while j < len(rows):
                ic = [td.get_text(strip=True) for td in rows[j].find_all("td")]
                if len(ic) == 26 and ic[0] and not ic[0].isdigit():
                    dg, sl = _i(ic[3]), _i(ic[1])
                    items.append(dict(ten_hang=ic[0].strip(), so_luong=sl, thanh_tien=dg*sl))
                    j += 1
                elif len(ic) == 40 and ic[0].isdigit(): break
                else:
                    j += 1
                    if j - i > 30: break
            inv["items"]  = items
            inv["so_mon"] = sum(x["so_luong"] for x in items)
            dt = _dt(inv["ngay"], inv["gio"])
            if dt:
                inv.update(
                    dt=dt, date_only=dt.date(),
                    ngay_fmt=dt.strftime("%d/%m/%Y"),
                    thu=["T2","T3","T4","T5","T6","T7","CN"][dt.weekday()],
                    thu_full=["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"][dt.weekday()],
                    tuan=f"Tuần {dt.isocalendar()[1]}",
                    tuan_trong_thang=(dt.day-1)//7+1,
                    thang=dt.strftime("%m/%Y"),
                    hour=dt.hour
                )
            invs.append(inv)
            i = j
        else:
            i += 1
    return invs

def _i(s):
    try: return int(str(s).replace(",","").strip())
    except: return 0

def _dt(ngay, gio):
    try:
        d,m,y = ngay.split("/"); h,mi = gio.split(":")
        return datetime(int(y),int(m),int(d),int(h),int(mi))
    except: return None

def nn(n): return re.sub(r"\s+"," ", n.strip().lower())
def fv(n):
    if n >= 1e9: return f"{n/1e9:.1f}tỷ"
    if n >= 1e6: return f"{n/1e6:.1f}tr"
    if n >= 1e3: return f"{n/1e3:.0f}k"
    return str(n)
def ff(n): return f"{n:,.0f}đ"

CL = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TEXT, family="Inter, sans-serif", size=12),
    margin=dict(l=4, r=4, t=8, b=4),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=SUB, size=11)),
)

def bar(x_vals, y_vals, hover, ticksuffix="", peak=True, height=260):
    mx = max(y_vals) if y_vals else 1
    fig = go.Figure(go.Bar(
        x=x_vals, y=y_vals, marker_line_width=0,
        marker_color=[NAVY if (v==mx and peak) else NAVY_LT for v in y_vals],
        hovertemplate="%{x}<br><b>%{customdata}</b><extra></extra>",
        customdata=hover,
    ))
    fig.update_layout(**CL, height=height, bargap=0.35,
        yaxis=dict(ticksuffix=ticksuffix, gridcolor=BORDER, linecolor=BORDER, tickfont=dict(color=SUB,size=11)),
        xaxis=dict(gridcolor="rgba(0,0,0,0)", linecolor=BORDER, tickfont=dict(color=SUB,size=11)),
    )
    fig.update_traces(marker_cornerradius=5)
    return fig


# ── SIDEBAR ──────────────────────────────────────────
with st.sidebar:
    st.markdown(f"<p style='font-size:20px;font-weight:900;margin:0;color:{TEXT}'>☕ Fabi</p>", unsafe_allow_html=True)
    st.caption("Sales Dashboard")
    st.divider()

    uploaded = st.file_uploader(
        "Tải file XLS từ Fabi",
        type=["xls", "xlsx"],
        help="Fabi → Báo cáo → Danh sách hoá đơn → Xuất Excel"
    )
    st.divider()

    st.markdown(f"<p style='font-size:12px;font-weight:600;margin-bottom:6px;color:{TEXT}'>Xem theo</p>", unsafe_allow_html=True)
    time_mode = st.selectbox(
        "mode", ["Tất cả dữ liệu","Chọn 1 ngày","Theo tuần","Theo tháng","Tuỳ chọn khoảng"],
        label_visibility="collapsed"
    )

    single_day = date_from = date_to = None
    if time_mode == "Chọn 1 ngày":
        single_day = st.date_input("Chọn ngày", label_visibility="visible")
    elif time_mode == "Tuỳ chọn khoảng":
        date_from = st.date_input("Từ ngày")
        date_to   = st.date_input("Đến ngày")

    st.divider()
    export_excel = st.button("📊 Xuất Excel Báo cáo")


# ── EMPTY STATE ───────────────────────────────────────
if not uploaded:
    st.markdown(f"""
    <div style='display:flex;flex-direction:column;align-items:center;
                justify-content:center;min-height:75vh;text-align:center;gap:12px'>
        <div style='font-size:52px'>☕</div>
        <div style='font-size:24px;font-weight:800;color:{TEXT};font-family:Inter,sans-serif'>
            Fabi Sales Dashboard
        </div>
        <div style='font-size:14px;color:{SUB};max-width:300px;line-height:1.7'>
            Tải file <b>.xls</b> xuất từ Fabi lên thanh bên trái để bắt đầu phân tích
        </div>
    </div>""", unsafe_allow_html=True)
    st.stop()


# ── PARSE + FILTER ────────────────────────────────────
with st.spinner("Đang đọc dữ liệu..."):
    try: all_inv = parse_fabi(uploaded.getvalue())
    except Exception as e:
        st.error(f"Lỗi đọc file: {e}"); st.stop()

inv_dt = [x for x in all_inv if "dt" in x]
if not inv_dt:
    st.error("Không tìm thấy dữ liệu hợp lệ."); st.stop()

all_dates = sorted(set(x["date_only"] for x in inv_dt))
d_min, d_max = all_dates[0], all_dates[-1]

if time_mode == "Chọn 1 ngày" and single_day:
    data = [x for x in inv_dt if x["date_only"] == single_day]
elif time_mode == "Tuỳ chọn khoảng" and date_from and date_to:
    data = [x for x in inv_dt if date_from <= x["date_only"] <= date_to]
else:
    data = inv_dt

if not data:
    st.warning("Không có dữ liệu trong khoảng đã chọn."); st.stop()

active_dates = sorted(set(x["date_only"] for x in data))
period_str   = f"{active_dates[0].strftime('%d/%m/%Y')} → {active_dates[-1].strftime('%d/%m/%Y')}"


# ── COMPUTE ───────────────────────────────────────────
total_rev   = sum(x["tong_hoa_don"] for x in data)
total_inv_n = len(data)
total_items = sum(x["so_mon"] for x in data)
aov         = total_rev // total_inv_n if total_inv_n else 0
num_days    = len(active_dates)
multi       = [x for x in data if x["so_mon"] >= 2]
pct_multi   = len(multi)/total_inv_n*100 if total_inv_n else 0
avg_items   = total_items/total_inv_n if total_inv_n else 0

pmap = {}
for inv in data:
    for it in inv["items"]:
        k = nn(it["ten_hang"])
        if not k: continue
        if k not in pmap: pmap[k] = {"name": it["ten_hang"], "qty": 0, "rev": 0}
        pmap[k]["qty"] += it["so_luong"]
        pmap[k]["rev"] += it["thanh_tien"]
top10         = sorted(pmap.values(), key=lambda x: x["qty"], reverse=True)[:10]
total_qty_all = sum(x["qty"] for x in pmap.values())


# ── HEADER ────────────────────────────────────────────
st.markdown(f"""
<div class="hdr">
    <div>
        <div class="hdr-logo">fabi</div>
        <div class="hdr-sub">RU:TINE TRẦN PHÚ — Sales Analytics</div>
    </div>
    <div class="hdr-badge">{period_str}</div>
</div>""", unsafe_allow_html=True)


# ── METRICS ───────────────────────────────────────────
c1,c2,c3,c4,c5 = st.columns(5)
for col, lbl, val, sub, dark in [
    (c1, "Doanh thu",      fv(total_rev),       ff(total_rev),              True),
    (c2, "Số hoá đơn",     f"{total_inv_n:,}",  f"{num_days} ngày",         False),
    (c3, "AOV trung bình", fv(aov),             ff(aov),                    False),
    (c4, "Số món bán",     f"{total_items:,}",  f"{avg_items:.1f} món/đơn", False),
    (c5, "Đơn 2+ món",     f"{pct_multi:.0f}%", f"{len(multi):,} đơn",      False),
]:
    col.markdown(f"""
    <div class="mc {'dk' if dark else ''}">
        <div class="lb">{lbl}</div>
        <div class="vl">{val}</div>
        <div class="sb">{sub}</div>
    </div>""", unsafe_allow_html=True)


# ── DOANH THU THEO THỜI GIAN ──────────────────────────
st.markdown('<div class="sec">Doanh thu theo thời gian</div>', unsafe_allow_html=True)

if time_mode in ["Tất cả dữ liệu","Tuỳ chọn khoảng"]:
    gkeys = [d.strftime("%d/%m") for d in active_dates]
    def gk(x): return x["date_only"].strftime("%d/%m")
elif time_mode == "Theo tuần":
    def gk(x): return x["tuan"]
    gkeys = sorted(set(gk(x) for x in data))
elif time_mode == "Theo tháng":
    def gk(x): return x["thang"]
    gkeys = sorted(set(gk(x) for x in data), key=lambda s: datetime.strptime(s,"%m/%Y"))
else:
    def gk(x): return f"{x['hour']:02d}:00"
    gkeys = [f"{h:02d}:00" for h in range(24)]

rev_g = defaultdict(int); inv_g = defaultdict(int)
for x in data:
    k = gk(x); rev_g[k] += x["tong_hoa_don"]; inv_g[k] += 1
aov_g = {k: rev_g[k]//inv_g[k] if inv_g[k] else 0 for k in gkeys}

t1, t2, t3 = st.tabs(["💰 Doanh thu", "📋 Số đơn", "📊 AOV theo ngày"])
with t1:
    st.plotly_chart(bar(gkeys, [round(rev_g.get(k,0)/1000) for k in gkeys],
        [ff(rev_g.get(k,0)) for k in gkeys], ticksuffix="k"), use_container_width=True)
with t2:
    y2 = [inv_g.get(k,0) for k in gkeys]
    st.plotly_chart(bar(gkeys, y2, [f"{v} đơn" for v in y2], peak=False), use_container_width=True)
with t3:
    y3 = [aov_g.get(k,0) for k in gkeys]
    fig3 = go.Figure(go.Scatter(
        x=gkeys, y=y3, mode="lines+markers",
        line=dict(color=NAVY, width=2.5), marker=dict(size=7, color=NAVY),
        hovertemplate="%{x}<br>AOV: <b>%{customdata}</b><extra></extra>",
        customdata=[ff(v) for v in y3],
    ))
    fig3.update_layout(**CL, height=260,
        yaxis=dict(gridcolor=BORDER, linecolor=BORDER, tickfont=dict(color=SUB,size=11)),
        xaxis=dict(gridcolor="rgba(0,0,0,0)", linecolor=BORDER, tickfont=dict(color=SUB,size=11)),
    )
    st.plotly_chart(fig3, use_container_width=True)


# ── AOV + TOP MÓN ─────────────────────────────────────
st.markdown('<div class="sec">Phân tích AOV & Top sản phẩm</div>', unsafe_allow_html=True)
L, R = st.columns(2)

with L:
    aov_thu = defaultdict(list)
    for x in data: aov_thu[x["thu_full"]].append(x["tong_hoa_don"])
    tord = ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"]
    tl   = [t for t in tord if t in aov_thu]
    tv   = [sum(aov_thu[t])//len(aov_thu[t]) for t in tl]
    mx   = max(tv) if tv else 1
    fig_t = go.Figure(go.Bar(
        x=tl, y=tv, marker_line_width=0,
        marker_color=[NAVY if v==mx else NAVY_LT for v in tv],
        hovertemplate="%{x}<br>AOV: <b>%{customdata}</b><extra></extra>",
        customdata=[ff(v) for v in tv],
    ))
    fig_t.update_layout(**CL, height=250, bargap=0.4,
        title=dict(text="AOV theo thứ trong tuần", font=dict(size=13,color=TEXT), x=0),
        yaxis=dict(gridcolor=BORDER, linecolor=BORDER, tickfont=dict(color=SUB,size=10)),
        xaxis=dict(gridcolor="rgba(0,0,0,0)", linecolor=BORDER, tickfont=dict(color=SUB,size=10)),
    )
    fig_t.update_traces(marker_cornerradius=5)
    st.plotly_chart(fig_t, use_container_width=True)

with R:
    names = [x["name"] for x in reversed(top10)]
    qtys  = [x["qty"]  for x in reversed(top10)]
    fig_h = go.Figure(go.Bar(
        x=qtys, y=names, orientation="h", marker_line_width=0,
        marker_color=[NAVY if q==max(qtys) else NAVY_LT for q in qtys],
        hovertemplate="%{y}<br>SL: <b>%{x}</b><extra></extra>",
    ))
    fig_h.update_layout(**CL, height=310, bargap=0.3,
        title=dict(text="Top 10 món bán chạy", font=dict(size=13,color=TEXT), x=0),
        xaxis=dict(gridcolor=BORDER, linecolor=BORDER, tickfont=dict(color=SUB,size=10)),
        yaxis=dict(gridcolor="rgba(0,0,0,0)", linecolor="rgba(0,0,0,0)", tickfont=dict(color=TEXT,size=11)),
    )
    fig_h.update_traces(marker_cornerradius=5)
    st.plotly_chart(fig_h, use_container_width=True)


# ── ĐƠN NHÓM + GIỜ ───────────────────────────────────
st.markdown('<div class="sec">Đơn nhóm & Giờ cao điểm</div>', unsafe_allow_html=True)
ca, cb, cc = st.columns(3)

with ca:
    s1 = len([x for x in data if x["so_mon"]==1])
    s2 = len([x for x in data if x["so_mon"]==2])
    s3 = len([x for x in data if x["so_mon"]>=3])
    fig_p = go.Figure(go.Pie(
        labels=["1 món","2 món","3+ món"], values=[s1,s2,s3],
        hole=0.55, marker_colors=[NAVY_LT, NAVY, GOLD],
        textfont=dict(color=TEXT, size=11),
        hovertemplate="%{label}: <b>%{value} đơn</b> (%{percent})<extra></extra>",
    ))
    fig_p.update_layout(**CL, height=250,
        title=dict(text="Tỉ lệ cỡ đơn", font=dict(size=13,color=TEXT), x=0),
        legend=dict(font=dict(color=SUB,size=11), bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig_p, use_container_width=True)

with cb:
    thu_pct = {}
    for t in ["T2","T3","T4","T5","T6","T7","CN"]:
        inv_t = [x for x in data if x["thu"]==t]
        if inv_t:
            thu_pct[t] = round(len([x for x in inv_t if x["so_mon"]>=2])/len(inv_t)*100,1)
    fig_tp = go.Figure(go.Bar(
        x=list(thu_pct.keys()), y=list(thu_pct.values()),
        marker_color=NAVY, marker_line_width=0,
        hovertemplate="%{x}: <b>%{y:.0f}%</b> đơn nhóm<extra></extra>",
    ))
    fig_tp.update_layout(**CL, height=250, bargap=0.35,
        title=dict(text="% đơn nhóm theo thứ", font=dict(size=13,color=TEXT), x=0),
        yaxis=dict(range=[0,100], ticksuffix="%", gridcolor=BORDER, linecolor=BORDER, tickfont=dict(color=SUB,size=10)),
        xaxis=dict(gridcolor="rgba(0,0,0,0)", linecolor=BORDER, tickfont=dict(color=SUB,size=10)),
    )
    fig_tp.update_traces(marker_cornerradius=5)
    st.plotly_chart(fig_tp, use_container_width=True)

with cc:
    h_cnt = defaultdict(int)
    for x in data: h_cnt[x["hour"]] += 1
    peak = max(h_cnt, key=h_cnt.get, default=14)
    fig_hr = go.Figure(go.Bar(
        x=[f"{h:02d}" for h in range(24)],
        y=[h_cnt.get(h,0) for h in range(24)],
        marker_color=[NAVY if h==peak else NAVY_LT for h in range(24)],
        marker_line_width=0,
        hovertemplate="%{x}:00 — <b>%{y} đơn</b><extra></extra>",
    ))
    fig_hr.update_layout(**CL, height=250, bargap=0.2,
        title=dict(text=f"Giờ cao điểm (peak {peak:02d}:00)", font=dict(size=13,color=TEXT), x=0),
        xaxis=dict(gridcolor="rgba(0,0,0,0)", linecolor=BORDER, tickfont=dict(color=SUB,size=9)),
        yaxis=dict(gridcolor=BORDER, linecolor=BORDER, tickfont=dict(color=SUB,size=10)),
    )
    fig_hr.update_traces(marker_cornerradius=3)
    st.plotly_chart(fig_hr, use_container_width=True)


# ── TABLE + THANH TOÁN ────────────────────────────────
st.markdown('<div class="sec">Chi tiết sản phẩm & Thanh toán</div>', unsafe_allow_html=True)
tl2, tr2 = st.columns([1.6, 1])

with tl2:
    rows_html = "".join(f"""
    <tr>
        <td class='rk'>{i+1}</td>
        <td>{it['name']}</td>
        <td class='n'>{it['qty']}</td>
        <td class='g'>{fv(it['rev'])}</td>
        <td>
            <div style='display:flex;align-items:center;gap:7px'>
                <div style='width:{round(it["qty"]/top10[0]["qty"]*70) if top10 else 0}px;height:4px;background:{NAVY};border-radius:2px'></div>
                <span class='g'>{it['qty']/total_qty_all*100:.0f}%</span>
            </div>
        </td>
    </tr>""" for i,it in enumerate(top10))
    st.markdown(f"""
    <p style='font-size:13px;font-weight:600;color:{TEXT};margin-bottom:10px;font-family:Inter,sans-serif'>Top 10 món bán chạy</p>
    <table class='ft'>
        <thead><tr><th>#</th><th>Tên món</th><th>SL</th><th>Doanh thu</th><th>Tỉ lệ</th></tr></thead>
        <tbody>{rows_html}</tbody>
    </table>""", unsafe_allow_html=True)

with tr2:
    tr_r = sum(x["tong_hoa_don"] for x in data if "TRANSFER" in x["pttt"])
    cd_r = total_rev - tr_r
    tr_n = sum(1 for x in data if "TRANSFER" in x["pttt"])
    cd_n = total_inv_n - tr_n
    fig_pt = go.Figure(go.Pie(
        labels=["Chuyển khoản","Tiền mặt"], values=[tr_r, cd_r],
        hole=0.55, marker_colors=[NAVY, NAVY_LT],
        textfont=dict(color=TEXT, size=12),
        hovertemplate="%{label}<br><b>%{customdata}</b><extra></extra>",
        customdata=[ff(tr_r), ff(cd_r)],
    ))
    fig_pt.update_layout(**CL, height=230,
        title=dict(text="Phương thức thanh toán", font=dict(size=13,color=TEXT), x=0),
        legend=dict(font=dict(color=SUB,size=11), bgcolor="rgba(0,0,0,0)",
                    orientation="h", yanchor="bottom", y=-0.18),
    )
    st.plotly_chart(fig_pt, use_container_width=True)
    st.markdown(f"""
    <div style='font-size:12px;color:{SUB};line-height:2;font-family:Inter,sans-serif'>
        <b style='color:{TEXT}'>Chuyển khoản:</b> {tr_n:,} đơn · {fv(tr_r)}<br>
        <b style='color:{TEXT}'>Tiền mặt:</b> {cd_n:,} đơn · {fv(cd_r)}
    </div>""", unsafe_allow_html=True)


# ── BẢNG CHI TIẾT ─────────────────────────────────────
st.markdown('<div class="sec">Chi tiết theo ngày</div>', unsafe_allow_html=True)

day_agg = defaultdict(lambda: dict(rev=0,inv=0,items=0,multi=0))
for x in data:
    d = x["date_only"]
    day_agg[d]["rev"]   += x["tong_hoa_don"]
    day_agg[d]["inv"]   += 1
    day_agg[d]["items"] += x["so_mon"]
    if x["so_mon"] >= 2: day_agg[d]["multi"] += 1

df_det = pd.DataFrame([{
    "Ngày":       k.strftime("%d/%m/%Y"),
    "Doanh thu":  ff(v["rev"]),
    "Số đơn":     v["inv"],
    "Số món":     v["items"],
    "AOV":        fv(v["rev"]//v["inv"]) if v["inv"] else "—",
    "Đơn 2+ món": v["multi"],
    "% Đơn nhóm": f"{v['multi']/v['inv']*100:.0f}%" if v["inv"] else "—",
} for k,v in sorted(day_agg.items())])

st.dataframe(df_det, use_container_width=True, hide_index=True,
    column_config={
        "Ngày":       st.column_config.TextColumn(width=110),
        "Doanh thu":  st.column_config.TextColumn(width=130),
    })


# ── EXPORT ───────────────────────────────────────────
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
        } for x in data]).to_excel(w, sheet_name="Chi tiết", index=False)
    st.download_button("⬇️ Tải Excel", data=buf.getvalue(),
        file_name=f"fabi_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
