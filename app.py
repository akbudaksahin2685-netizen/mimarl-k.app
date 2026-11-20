"""ODTÜ Mimarlık Amfisi - koltuk doluluk haritası (Streamlit)."""

import json
import math
import os
import random
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

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
DATA_FILE = Path(__file__).with_name("doluluk.json")

GREEN, RED = "#1f9d55", "#d23f3f"


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
        rows.append({"id": row["id"], "r": r, "length": length, "aisles": aisles, "parts": row["parts"], "total": n})
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
        fill="toself", fillcolor="#28302d", line=dict(width=0), hoverinfo="skip", showlegend=False))
    fig.add_annotation(x=0, y=-sr, text="<b>S A H N E</b>", showarrow=False, font=dict(color="white", size=18))

    # Koridor merdivenleri
    ax, ay, aa = [], [], []
    for g in ROW_GEO:
        for a in g["aisles"]:
            x, y, d = polar(g["r"], a)
            ax.append(x); ay.append(y); aa.append(d)
    fig.add_trace(go.Scatter(
        x=ax, y=ay, mode="markers", hoverinfo="skip", showlegend=False,
        marker=dict(symbol="square", size=26, color="#c9cfcc", angle=aa)))

    # Sıra harfleri
    lx, ly, lt = [], [], []
    for g in ROW_GEO:
        for sign in (-1, 1):
            x, y, _ = polar(g["r"], sign * (g["length"] / 2 + 26))
            lx.append(x); ly.append(y); lt.append(g["id"])
    fig.add_trace(go.Scatter(
        x=lx, y=ly, mode="text", text=lt, hoverinfo="skip", showlegend=False,
        textfont=dict(size=15, color="#5d6763", family="Arial Black")))

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
            color=[RED if t else GREEN for t in taken],
            line=dict(width=1, color="rgba(0,0,0,.25)"),
        ),
        selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=1)),
    ))

    fig.update_xaxes(visible=False, fixedrange=True)
    fig.update_yaxes(visible=False, scaleanchor="x", scaleratio=1, fixedrange=True, autorange="reversed")
    fig.update_layout(
        height=620, margin=dict(l=0, r=0, t=0, b=0),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        dragmode=False, clickmode="event+select" if editing else "none",
        hoverlabel=dict(font_size=14),
    )
    return fig


# ---------------------------------------------------------------------------
# Sayfa
# ---------------------------------------------------------------------------
st.set_page_config(page_title="ODTÜ Mimarlık Amfisi Doluluk", page_icon="🎭", layout="wide")
st.markdown(
    """<style>
    .block-container{padding-top:2rem;max-width:1150px}
    div[data-testid="stMetricValue"]{font-size:2.2rem}
    </style>""",
    unsafe_allow_html=True,
)

ss = st.session_state
ss.setdefault("is_admin", False)
ss.setdefault("map_key", 0)

taken, updated, real = load_state()

st.caption("ODTÜ MİMARLIK FAKÜLTESİ")
st.title("Mimarlık Amfisi Doluluk Haritası")
st.write("10 sıra, 363 koltuk. 🟩 Yeşil koltuklar boş, 🟥 kırmızı koltuklar dolu.")
if real and updated:
    st.caption(f"Son güncelleme: {datetime.fromisoformat(updated).strftime('%d.%m.%Y %H:%M')}")
else:
    st.caption("Şu an örnek doluluk verisi gösteriliyor.")

# Özet
n_taken = sum(taken)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Boş", N - n_taken)
c2.metric("Dolu", n_taken)
c3.metric("Toplam", N)
c4.metric("Doluluk", f"%{round(n_taken / N * 100)}")
st.progress(n_taken / N)

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
                            (out.add(idx[f"{a[0]}{k}"]) if f"{a[0]}{k}" in idx else bad.append(f"{a[0]}{k}"))
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
st.subheader("Koltuk haritası")
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
    if st.button("🔄 Yenile"):
        st.rerun()

# Sıralara göre doluluk
st.subheader("Sıralara göre doluluk")
records = []
for g in ROW_GEO:
    idx = [i for i, s in enumerate(SEATS) if s["row"] == g["id"]]
    t = sum(taken[i] for i in idx)
    blocks = "Kesintisiz" if len(g["parts"]) == 1 else f"Sol {g['parts'][0]} · Orta {g['parts'][1]} · Sağ {g['parts'][2]}"
    records.append({"Sıra": g["id"], "Düzen": blocks, "Dolu": t, "Boş": len(idx) - t, "Toplam": len(idx), "Doluluk": t / len(idx)})
st.dataframe(
    pd.DataFrame(records),
    hide_index=True, width="stretch",
    column_config={"Doluluk": st.column_config.ProgressColumn("Doluluk", format="percent", min_value=0, max_value=1)},
)
