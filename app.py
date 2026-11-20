"""ODTÜ Caz · Sonbaharda Caz - Mimarlık Amfisi koltuk doluluk haritası (Streamlit)."""

import base64
import json
import math
import os
import random
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import plotly.graph_objects as go
import streamlit as st

HERE = Path(__file__).parent

# ---------------------------------------------------------------------------
# Etkinlik bilgileri (afişten)
# ---------------------------------------------------------------------------
EVENT = {
    "title": "Sonbaharda Caz",
    "date": "27 Kasım",
    "time": "19.00",
    "doors": "18.45",
    "venue": "Mimarlık Amfisi",
    "program": [("19.00", "Levent Demirci Quartet"), ("20.30", "Meriç Çalışan Quartet")],
}

# ---------------------------------------------------------------------------
# Renkler
# ---------------------------------------------------------------------------
C = {
    "bg": "#24170f",        # espresso
    "panel": "#33231a",     # koyu ahşap
    "panel2": "#3d2a1f",
    "cream": "#f4e7cf",
    "muted": "#c4ab8c",
    "red": "#e0312f",       # ODTÜ Caz kırmızısı
    "mustard": "#e9a93b",   # trompet sarısı
    "green": "#2f6b3a",     # tente yeşili
    "chalk": "#1d1f1c",
    "free": "#4fae5f",
    "taken": "#e0312f",
    "aisle": "#5a4436",
}

# ---------------------------------------------------------------------------
# Salon düzeni
# A–D: kesintisiz sıralar. E–J: iki koridorla sol / orta / sağ bloklara bölünür,
# yan bloklar = (toplam − orta) / 2.
# ---------------------------------------------------------------------------
FRONT = [("A", 31), ("B", 35), ("C", 38), ("D", 42)]
BACK = [("E", 42, 8), ("F", 39, 9), ("G", 38, 10), ("H", 37, 11), ("I", 35, 11), ("J", 26, 12)]

ROWS = [{"id": r, "parts": [n]} for r, n in FRONT]
for r, total, mid in BACK:
    side = (total - mid) // 2
    ROWS.append({"id": r, "parts": [side, mid, side]})

PITCH, AISLE, R0, STEP, CROSS = 26, 64, 1150, 50, 22
TZ = ZoneInfo("Europe/Istanbul")
DATA_FILE = HERE / "doluluk.json"


def polar(radius, arc):
    th = arc / radius
    return radius * math.sin(th), -radius * math.cos(th), math.degrees(th)


@st.cache_data
def build_layout():
    seats, rows, r = [], [], R0
    for i, row in enumerate(ROWS):
        if i == 4:
            r -= CROSS
        n = sum(row["parts"])
        length = n * PITCH + (len(row["parts"]) - 1) * AISLE
        s, num, aisles = -length / 2, 0, []
        for pi, cnt in enumerate(row["parts"]):
            for _ in range(cnt):
                num += 1
                x, y, deg = polar(r, s + PITCH / 2)
                section = None if len(row["parts"]) == 1 else ["Sol", "Orta", "Sağ"][pi]
                seats.append({"row": row["id"], "num": num, "section": section, "x": x, "y": y, "deg": deg})
                s += PITCH
            if pi < len(row["parts"]) - 1:
                aisles.append(s + AISLE / 2)
                s += AISLE
        rows.append({"id": row["id"], "r": r, "length": length, "aisles": aisles, "parts": row["parts"]})
        r -= STEP
    return seats, rows


SEATS, ROW_GEO = build_layout()
N = len(SEATS)


# ---------------------------------------------------------------------------
# Paylaşılan durum (tüm ziyaretçiler aynı dosyayı okur)
# ---------------------------------------------------------------------------
def sample_state():
    rnd = random.Random(2026)
    order = {g["id"]: i for i, g in enumerate(ROW_GEO)}
    return [rnd.random() < 0.78 - order[s["row"]] * 0.045 for s in SEATS]


def load_state():
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        taken = data.get("taken", "")
        if len(taken) == N:
            return [c == "1" for c in taken], data.get("updated"), bool(data.get("real"))
    except (FileNotFoundError, ValueError):
        pass
    return sample_state(), None, False


def save_state(taken):
    payload = {
        "real": True,
        "updated": datetime.now(TZ).isoformat(timespec="seconds"),
        "taken": "".join("1" if t else "0" for t in taken),
    }
    fd, tmp = tempfile.mkstemp(dir=DATA_FILE.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    os.replace(tmp, DATA_FILE)


def admin_password():
    try:
        return st.secrets["ADMIN_PASSWORD"]
    except Exception:
        return os.environ.get("ADMIN_PASSWORD", "odtu1956")


def logo_data_uri():
    p = HERE / "logo.png"
    if p.exists():
        return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()
    return None


# ---------------------------------------------------------------------------
# Görsel tema (CSS)
# ---------------------------------------------------------------------------
def leaf_svg(color):
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'>"
        f"<path d='M20 2 L24 12 L34 9 L29 19 L38 23 L27 26 L28 37 L20 30 L12 37 L13 26 L2 23 L11 19 L6 9 L16 12 Z' fill='{color}'/>"
        "<path d='M20 30 L20 40' stroke='%235a3a22' stroke-width='2'/></svg>"
    )
    return "data:image/svg+xml;utf8," + svg.replace("#", "%23").replace("<", "%3C").replace(">", "%3E")


LEAF_COLORS = ["#d9582b", "#e9a93b", "#b8342a", "#c97a2c", "#8c4a24"]

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Jost:wght@400;500;600;700&display=swap');

:root {{
  --bg:{C['bg']}; --panel:{C['panel']}; --panel2:{C['panel2']}; --cream:{C['cream']};
  --muted:{C['muted']}; --red:{C['red']}; --mustard:{C['mustard']}; --green:{C['green']};
  --chalk:{C['chalk']}; --free:{C['free']}; --taken:{C['taken']};
}}
html, body, .stApp {{ background: var(--bg) !important; color: var(--cream); font-family: 'Jost', sans-serif; }}
.stApp {{
  background:
    radial-gradient(1200px 500px at 50% -10%, rgba(233,169,59,.10), transparent 60%),
    radial-gradient(900px 600px at 100% 100%, rgba(224,49,47,.08), transparent 60%),
    var(--bg) !important;
}}
header[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 0 !important; max-width: 1150px; }}
h1,h2,h3,h4 {{ font-family: 'DM Serif Display', serif !important; color: var(--cream) !important; letter-spacing:.01em; }}
p, li, label, span, div {{ font-family: 'Jost', sans-serif; }}

/* Tente */
.awning {{
  height: 54px; margin: 0 -4rem 0; position: relative;
  background: repeating-linear-gradient(90deg, var(--green) 0 46px, #3d7f47 46px 92px);
  box-shadow: 0 6px 14px rgba(0,0,0,.35);
}}
.awning::after {{
  content:""; position:absolute; left:0; right:0; bottom:-14px; height:14px;
  background: radial-gradient(circle at 23px -2px, var(--green) 22px, transparent 23px) 0 0/46px 14px repeat-x;
}}

/* Başlık */
.hero {{ display:flex; gap:22px; align-items:center; padding: 38px 0 6px; flex-wrap: wrap; }}
.hero img {{ width: 92px; height: 92px; border-radius: 18px; box-shadow: 0 8px 22px rgba(0,0,0,.45); }}
.hero .t {{ display:flex; flex-direction:column; gap:2px; }}
.eyebrow {{ color: var(--mustard); font-weight:600; letter-spacing:.18em; font-size:.78rem; text-transform:uppercase; }}
.hero h1 {{ font-size: clamp(2.3rem, 6vw, 3.6rem); line-height:1; margin:0; padding:0; }}
.hero h1 em {{ color: var(--mustard); font-style: italic; }}
.hero .sub {{ color: var(--muted); font-size: 1.02rem; }}
.rule {{ display:flex; align-items:center; gap:12px; color: var(--mustard); margin: 14px 0 18px; }}
.rule::before, .rule::after {{ content:""; flex:1; height:1px; background: linear-gradient(90deg, transparent, rgba(233,169,59,.6), transparent); }}

/* Kara tahta + istatistik */
.top {{ display:grid; grid-template-columns: minmax(260px, 1fr) 1.4fr; gap: 18px; }}
@media (max-width: 760px) {{ .top {{ grid-template-columns: 1fr; }} }}
.chalk {{
  background: linear-gradient(160deg, #262825, var(--chalk));
  border: 10px solid #6b4a2f; border-radius: 10px; padding: 18px 20px;
  box-shadow: inset 0 0 40px rgba(255,255,255,.04), 0 10px 24px rgba(0,0,0,.4);
  color: #ecebe4; position: relative;
}}
.chalk .when {{ font-family:'DM Serif Display',serif; font-size:1.55rem; color:#fff; }}
.chalk .where {{ color:#cfcabd; margin-bottom: 10px; }}
.chalk .act {{ display:flex; justify-content:space-between; gap:10px; border-top:1px dashed rgba(255,255,255,.25); padding:9px 0; }}
.chalk .act b {{ font-family:'DM Serif Display',serif; font-weight:400; font-size:1.15rem; }}
.chalk .act span {{ color: var(--mustard); font-weight:600; }}
.chalk .doors {{ font-size:.85rem; color:#bdb8aa; margin-top:4px; }}

.stats {{ background: var(--panel); border:1px solid rgba(244,231,207,.08); border-radius: 16px; padding: 18px 20px;
  display:grid; grid-template-columns: repeat(3, 1fr); gap: 12px; align-content: start; }}
.stat .n {{ font-family:'DM Serif Display',serif; font-size: clamp(2rem, 6vw, 2.8rem); line-height:1; font-variant-numeric: tabular-nums; }}
.stat .l {{ color: var(--muted); font-size:.9rem; display:flex; gap:7px; align-items:center; margin-top:4px; }}
.sw {{ width:11px; height:11px; border-radius:3px; display:inline-block; }}
.sw.f {{ background: var(--free); }} .sw.t {{ background: var(--taken); }}
.bar {{ grid-column: 1/-1; height: 12px; background: var(--free); border-radius: 99px; overflow:hidden; display:flex; }}
.bar i {{ background: var(--taken); display:block; height:100%; }}
.pct {{ grid-column:1/-1; color: var(--muted); font-size:.92rem; }}
.pct b {{ color: var(--cream); }}
.note {{ grid-column:1/-1; font-size:.8rem; color: var(--mustard); }}

/* Harita kartı */
.maphead {{ display:flex; justify-content:space-between; align-items:end; flex-wrap:wrap; gap:8px; margin: 26px 0 4px; }}
.maphead h2 {{ margin:0 !important; padding:0 !important; font-size: 1.8rem; }}
.legend {{ display:flex; gap:16px; color: var(--muted); font-size:.92rem; }}
.legend span {{ display:flex; align-items:center; gap:7px; }}
div[data-testid="stPlotlyChart"] {{
  background: var(--panel); border-radius: 18px; border: 1px solid rgba(244,231,207,.08);
  padding: 6px; box-shadow: 0 12px 30px rgba(0,0,0,.35);
}}

/* Sıra tablosu */
.rows {{ display:grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 10px 26px;
  background: var(--panel); border-radius: 16px; padding: 18px 20px; border:1px solid rgba(244,231,207,.08); }}
.r {{ display:grid; grid-template-columns: 26px 1fr 58px; gap: 10px; align-items:center; }}
.r .id {{ font-family:'DM Serif Display',serif; font-size:1.3rem; color: var(--mustard); }}
.r .mini {{ height: 8px; background: var(--free); border-radius: 99px; overflow:hidden; }}
.r .mini i {{ display:block; height:100%; background: var(--taken); }}
.r .c {{ text-align:right; color: var(--muted); font-variant-numeric: tabular-nums; }}
.r .split {{ grid-column: 2/-1; font-size: .78rem; color: #9c8670; margin-top:-7px; }}

.foot {{ text-align:center; color:#8f7760; font-size:.85rem; margin: 30px 0 10px; }}

/* Düğmeler, girişler, kenar çubuğu */
section[data-testid="stSidebar"] {{ background: #1b110b !important; border-right: 1px solid rgba(233,169,59,.2); }}
section[data-testid="stSidebar"] * {{ color: var(--cream); }}
.stButton > button {{
  background: transparent; color: var(--cream); border: 1px solid rgba(233,169,59,.55);
  border-radius: 999px; font-weight: 600;
}}
.stButton > button:hover {{ background: var(--mustard); color: #24170f; border-color: var(--mustard); }}
.stButton > button:focus-visible {{ outline: 3px solid var(--mustard); outline-offset: 2px; }}
.stTextInput input {{ background: #2c1e15 !important; color: var(--cream) !important; border-color: rgba(233,169,59,.35) !important; }}

/* Süzülen yapraklar */
.leaves {{ position: fixed; inset: 0; pointer-events: none; z-index: 0; overflow: hidden; }}
.leaves i {{ position:absolute; top:-50px; width: 26px; height: 26px; background-size: contain; background-repeat:no-repeat;
  opacity:.55; animation: fall linear infinite; }}
@keyframes fall {{
  0% {{ transform: translate(0, -60px) rotate(0deg); }}
  50% {{ transform: translate(60px, 50vh) rotate(200deg); }}
  100% {{ transform: translate(-30px, 110vh) rotate(400deg); }}
}}
@media (prefers-reduced-motion: reduce) {{ .leaves {{ display:none; }} }}
.block-container {{ position: relative; z-index: 1; }}
</style>
"""


def leaves_html():
    rnd = random.Random(7)
    items = []
    for k in range(14):
        left = rnd.uniform(0, 100)
        dur = rnd.uniform(14, 28)
        delay = -rnd.uniform(0, dur)
        size = rnd.uniform(16, 30)
        img = leaf_svg(LEAF_COLORS[k % len(LEAF_COLORS)])
        items.append(
            f"<i style=\"left:{left:.1f}%;width:{size:.0f}px;height:{size:.0f}px;"
            f"animation-duration:{dur:.1f}s;animation-delay:{delay:.1f}s;background-image:url(&quot;{img}&quot;)\"></i>"
        )
    return "<div class='leaves'>" + "".join(items) + "</div>"


# ---------------------------------------------------------------------------
# Harita
# ---------------------------------------------------------------------------
def build_figure(taken, editing):
    fig = go.Figure()

    # Sahne
    sr, half = R0 + 95, 330
    pts = []
    for rad in (sr + 30, sr - 30):
        arc = [polar(rad, a * rad / sr)[:2] for a in [-half + k * (2 * half) / 40 for k in range(41)]]
        pts += arc if rad > sr else arc[::-1]
    fig.add_trace(go.Scatter(
        x=[p[0] for p in pts] + [pts[0][0]], y=[p[1] for p in pts] + [pts[0][1]],
        fill="toself", fillcolor=C["red"], line=dict(width=0), hoverinfo="skip", showlegend=False))
    fig.add_annotation(x=0, y=-sr, text="♪  S A H N E  ♪", showarrow=False,
                       font=dict(color=C["cream"], size=17, family="DM Serif Display, serif"))

    # Koridor merdivenleri
    ax, ay, aa = [], [], []
    for g in ROW_GEO:
        for a in g["aisles"]:
            x, y, d = polar(g["r"], a)
            ax.append(x); ay.append(y); aa.append(d)
    fig.add_trace(go.Scatter(
        x=ax, y=ay, mode="markers", hoverinfo="skip", showlegend=False,
        marker=dict(symbol="square", size=22, color=C["aisle"], angle=aa)))

    # Sıra harfleri
    lx, ly, lt = [], [], []
    for g in ROW_GEO:
        for sign in (-1, 1):
            x, y, _ = polar(g["r"], sign * (g["length"] / 2 + 28))
            lx.append(x); ly.append(y); lt.append(g["id"])
    fig.add_trace(go.Scatter(
        x=lx, y=ly, mode="text", text=lt, hoverinfo="skip", showlegend=False,
        textfont=dict(size=16, color=C["mustard"], family="DM Serif Display, serif")))

    # Koltuklar
    hover = [
        f"Sıra {s['row']} · Koltuk {s['num']}" + (f" · {s['section']} blok" if s["section"] else "")
        + f"<br><b>{'Dolu' if t else 'Boş'}</b>"
        for s, t in zip(SEATS, taken)
    ]
    fig.add_trace(go.Scatter(
        x=[s["x"] for s in SEATS], y=[s["y"] for s in SEATS],
        mode="markers", customdata=list(range(N)), text=hover,
        hovertemplate="%{text}<extra></extra>", showlegend=False, name="seats",
        marker=dict(
            symbol="square", size=13, angle=[s["deg"] for s in SEATS],
            color=[C["taken"] if t else C["free"] for t in taken],
            line=dict(width=1.2, color=C["panel"]),
        ),
        selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=1)),
    ))

    fig.update_xaxes(visible=False, fixedrange=True)
    fig.update_yaxes(visible=False, scaleanchor="x", scaleratio=1, fixedrange=True, autorange="reversed")
    fig.update_layout(
        height=600, margin=dict(l=8, r=8, t=8, b=8),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        dragmode=False, clickmode="event+select" if editing else "none",
        hoverlabel=dict(bgcolor=C["bg"], bordercolor=C["mustard"], font=dict(color=C["cream"], size=14, family="Jost, sans-serif")),
    )
    return fig


# ---------------------------------------------------------------------------
# Sayfa
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Sonbaharda Caz · Koltuk Doluluk", page_icon=str(HERE / "logo.png") if (HERE / "logo.png").exists() else "🎷", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
st.markdown(leaves_html(), unsafe_allow_html=True)

ss = st.session_state
ss.setdefault("is_admin", False)
ss.setdefault("map_key", 0)

taken, updated, real = load_state()
n_taken = sum(taken)
pct = round(n_taken / N * 100)

logo = logo_data_uri()
logo_tag = f"<img src='{logo}' alt='ODTÜ Caz logosu'>" if logo else ""
st.markdown(
    f"""
<div class="awning"></div>
<div class="hero">
  {logo_tag}
  <div class="t">
    <span class="eyebrow">ODTÜ Caz Topluluğu</span>
    <h1>Sonbaharda <em>Caz</em></h1>
    <span class="sub">Mimarlık Amfisi · canlı koltuk doluluğu</span>
  </div>
</div>
<div class="rule">✦</div>
""",
    unsafe_allow_html=True,
)

status_note = (
    f"Son güncelleme {datetime.fromisoformat(updated).strftime('%d.%m.%Y %H:%M')}"
    if real and updated else "Şu an örnek doluluk gösteriliyor"
)
acts = "".join(f"<div class='act'><b>{name}</b><span>{t}</span></div>" for t, name in EVENT["program"])
st.markdown(
    f"""
<div class="top">
  <div class="chalk">
    <div class="when">{EVENT['date']} · {EVENT['time']}</div>
    <div class="where">{EVENT['venue']}</div>
    {acts}
    <div class="doors">Kapı açılışı {EVENT['doors']}</div>
  </div>
  <div class="stats">
    <div class="stat"><div class="n">{N - n_taken}</div><div class="l"><i class="sw f"></i>Boş koltuk</div></div>
    <div class="stat"><div class="n">{n_taken}</div><div class="l"><i class="sw t"></i>Dolu koltuk</div></div>
    <div class="stat"><div class="n">{N}</div><div class="l">Toplam</div></div>
    <div class="bar"><i style="width:{n_taken / N * 100:.1f}%"></i></div>
    <div class="pct">Salon <b>%{pct}</b> dolu</div>
    <div class="note">{status_note}</div>
  </div>
</div>
<div class="maphead">
  <h2>Koltuk haritası</h2>
  <div class="legend"><span><i class="sw f"></i>Boş</span><span><i class="sw t"></i>Dolu</span></div>
</div>
""",
    unsafe_allow_html=True,
)

# Yönetici girişi (kenar çubuğu)
with st.sidebar:
    st.subheader("Yönetici")
    if not ss.is_admin:
        pw = st.text_input("Şifre", type="password")
        if st.button("Giriş yap", width="stretch"):
            if pw == admin_password():
                ss.is_admin = True
                st.rerun()
            else:
                st.error("Şifre yanlış.")
        st.caption("Koltukları değiştirmek için giriş yapın. Ziyaretçiler haritayı sadece görür.")
    else:
        st.success("Düzenleme açık. Haritada bir koltuğa tıklayınca boş/dolu değişir.")
        if st.button("Hepsini boşalt", width="stretch"):
            save_state([False] * N); st.rerun()
        if st.button("Hepsini doldur", width="stretch"):
            save_state([True] * N); st.rerun()
        st.divider()
        st.write("**Toplu işaretle**")
        codes = st.text_input("Koltuk kodları", placeholder="Örn: A1, A2, E5-E9")
        b1, b2 = st.columns(2)

        def parse(text):
            idx = {f"{s['row']}{s['num']}": i for i, s in enumerate(SEATS)}
            out, bad = set(), []
            for part in text.upper().replace(" ", "").split(","):
                if not part:
                    continue
                if "-" in part:
                    a, b = part.split("-", 1)
                    if a[:1] == b[:1] and a[1:].isdigit() and b[1:].isdigit():
                        for k in range(int(a[1:]), int(b[1:]) + 1):
                            code = f"{a[0]}{k}"
                            (out.add(idx[code]) if code in idx else bad.append(code))
                        continue
                (out.add(idx[part]) if part in idx else bad.append(part))
            return out, bad

        for col, label, value in ((b1, "Dolu yap", True), (b2, "Boş yap", False)):
            if col.button(label, width="stretch"):
                sel, bad = parse(codes)
                if bad:
                    st.error("Bulunamayan koltuk: " + ", ".join(bad))
                elif sel:
                    for i in sel:
                        taken[i] = value
                    save_state(taken); st.rerun()
        st.divider()
        if st.button("Çıkış yap", width="stretch"):
            ss.is_admin = False; st.rerun()

# Harita
editing = ss.is_admin
event = st.plotly_chart(
    build_figure(taken, editing),
    width="stretch",
    key=f"map{ss.map_key}",
    on_select="rerun" if editing else "ignore",
    selection_mode="points",
    config={"displayModeBar": False, "scrollZoom": False},
)
if editing and event and event.selection and event.selection.points:
    for p in event.selection.points:
        i = p.get("customdata")
        if isinstance(i, list):
            i = i[0]
        if i is not None:
            taken[int(i)] = not taken[int(i)]
    save_state(taken)
    ss.map_key += 1  # seçimi temizle ki aynı tıklama tekrar işlenmesin
    st.rerun()

if not editing:
    if st.button("↻ Doluluğu yenile"):
        st.rerun()

# Sıralara göre doluluk
rows_html = []
for g in ROW_GEO:
    idx = [i for i, s in enumerate(SEATS) if s["row"] == g["id"]]
    t = sum(taken[i] for i in idx)
    split = "" if len(g["parts"]) == 1 else f"<div class='split'>Sol {g['parts'][0]} · Orta {g['parts'][1]} · Sağ {g['parts'][2]}</div>"
    rows_html.append(
        f"<div class='r'><span class='id'>{g['id']}</span><div class='mini'><i style='width:{t / len(idx) * 100:.1f}%'></i></div>"
        f"<span class='c'>{t}/{len(idx)}</span>{split}</div>"
    )
st.markdown("<h2 style='margin-top:26px;font-size:1.8rem'>Sıralara göre doluluk</h2>", unsafe_allow_html=True)
st.markdown(f"<div class='rows'>{''.join(rows_html)}</div>", unsafe_allow_html=True)
st.markdown("<div class='foot'>ODTÜ Caz Topluluğu · Sonbaharda Caz · Mimarlık Amfisi</div>", unsafe_allow_html=True)
