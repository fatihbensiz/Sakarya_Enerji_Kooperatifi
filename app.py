# ============================================================
# SAU ENERJİ KOOPERATİFİ — P2P ENERJİ TİCARET PANELİ
# app.py | v5.0 — Gerçek Veri + Revize Finansal Mantık
# ============================================================

from __future__ import annotations

import datetime as dt
import html
import re
import unicodedata
import warnings
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ─────────────────────────────────────────────
# SAYFA AYARLARI
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="SAU Enerji Kooperatifi",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# SABİTLER
# ─────────────────────────────────────────────
# EPDK tarife dosyası bulunamazsa kullanılan güvenli varsayılan.
# Bu değer: OG Çift Terim Kamu/Özel Hizmetler aktif enerji + dağıtım bedeli, vergiler hariç.
SEBEKE_ALIS_FIYATI_FALLBACK_TL = 4.930369

# Üretici şebekeye satış bedeli tek bir EPDK tüketici tarifesinden türetilemez.
# Bu nedenle finansal panelde manuel girilir. 0.0 = karşılaştırma yapılmaz.
URETICI_SEBEKE_SATIS_REFERANS_VARSAYILAN_TL = 0.0

USD_TO_TL = 32.5

TR_AYLAR = {
    1: "Oca", 2: "Şub", 3: "Mar", 4: "Nis", 5: "May", 6: "Haz",
    7: "Tem", 8: "Ağu", 9: "Eyl", 10: "Eki", 11: "Kas", 12: "Ara",
}
TR_GUNLER = {
    0: "Pazartesi", 1: "Salı", 2: "Çarşamba", 3: "Perşembe",
    4: "Cuma", 5: "Cumartesi", 6: "Pazar",
}
TR_GUNLER_KISA = {0: "Pzt", 1: "Sal", 2: "Çar", 3: "Per", 4: "Cum", 5: "Cmt", 6: "Paz"}

RENK_URETIM = "#2ecc71"
RENK_TUKETIM = "#f39c12"
RENK_SEBEKE = "#95a5a6"
RENK_MAVI = "#2980b9"
RENK_KIRMIZI = "#e74c3c"
RENK_MOR = "#8e44ad"
RENK_LACIVERT = "#0d3b22"

PROSUMER_META = {
    "fef": {"ad": "FEF", "col": "FEF", "kwp": 592, "tilt": 17, "azimuth": 0.5, "pr": 81.84},
    "fefcblok": {"ad": "FEF C Blok", "col": "FEF_C_Blok", "kwp": 277, "tilt": 17, "azimuth": 33.2, "pr": 80.71},
    "hukuk": {"ad": "Hukuk / SBF", "col": "SBF", "kwp": 617, "tilt": 17, "azimuth": -2.4, "pr": 81.73},
    "sbf": {"ad": "SBF", "col": "SBF", "kwp": 617, "tilt": 17, "azimuth": -2.4, "pr": 81.73},
    "t1": {"ad": "T1", "col": "T1", "kwp": 413, "tilt": 17, "azimuth": 31.8, "pr": 81.16},
    "eemkongre": {"ad": "EEM Kongre", "col": "EEM_Kongre", "kwp": 837, "tilt": 17, "azimuth": -10.6, "pr": 81.41},
    "konservatuar": {"ad": "Konservatuar", "col": "Konservatuar", "kwp": 139, "tilt": 17, "azimuth": 27.8, "pr": 81.18},
    "kutuphane": {"ad": "Kütüphane", "col": "Kutuphane", "kwp": 203, "tilt": 17, "azimuth": 30.8, "pr": 80.83},
    "mimarlik": {"ad": "Mimarlık", "col": "Mimarlik", "kwp": 361, "tilt": 17, "azimuth": 4.1, "pr": 82.04},
    "rektorluk": {"ad": "Rektörlük", "col": "Rektorluk", "kwp": 363, "tilt": 17, "azimuth": -1.1, "pr": 82.06},
    "suburektorluk": {"ad": "SUBÜ Rektörlük", "col": "SubuRektorluk", "kwp": 186, "tilt": 17, "azimuth": 32.0, "pr": 80.73},
}

HARDWARE_SPECS = {
    "panel": "Pekintaş SPE-132GGT 630W — Vmpp: 41.39 V, Impp: 15.23 A",
    "inverter": "Huawei SUN2000-100KTL-M2 — 100 kW, MPPT: 200–1000 V, Maks. verim: %98.8",
}

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown(
    """
<style>
#MainMenu { visibility: hidden !important; }
header[data-testid="stHeader"] { display: none !important; }
footer { visibility: hidden !important; }
.stDeployButton { display: none !important; }

html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background-color: #f6faf7 !important;
    color: #111827 !important;
    font-family: "Segoe UI", Arial, sans-serif !important;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d3b22 0%, #145a32 58%, #1a7a43 100%) !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div {
    color: #eafaf0 !important;
}
[data-testid="stSidebar"] label p {
    color: #ffffff !important;
    font-weight: 700 !important;
}
[data-testid="stSidebar"] .stTextInput input {
    background: #ffffff !important;
    color: #102318 !important;
    border: 1.6px solid rgba(46, 204, 113, 0.55) !important;
    border-radius: 11px !important;
    font-weight: 700 !important;
    caret-color: #102318 !important;
}
[data-testid="stSidebar"] .stTextInput input::placeholder {
    color: #667085 !important;
    opacity: 1 !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: #ff4b4b !important;
    color: #ffffff !important;
    border: 0 !important;
    border-radius: 12px !important;
    font-weight: 900 !important;
    min-height: 45px !important;
}
[data-testid="stSidebar"] .stButton > button:hover { filter: brightness(0.95) !important; }

.kpi-card {
    background: linear-gradient(135deg, #ffffff 0%, #edfaf3 100%);
    border: 1.5px solid #a8e6c0;
    border-radius: 18px;
    padding: 18px 20px;
    text-align: center;
    box-shadow: 0 3px 16px rgba(20, 90, 50, 0.09);
    margin-bottom: 8px;
}
.kpi-label {
    font-size: 0.74rem;
    font-weight: 900;
    color: #145a32;
    text-transform: uppercase;
    letter-spacing: 0.065em;
    margin-bottom: 6px;
}
.kpi-value {
    font-size: 1.75rem;
    font-weight: 950;
    color: #145a32;
    line-height: 1.1;
}
.kpi-unit {
    font-size: 0.75rem;
    color: #20864d;
    font-weight: 700;
    margin-top: 5px;
}
.sec-hdr {
    font-size: 1.22rem;
    font-weight: 950;
    color: #145a32;
    border-left: 6px solid #2ecc71;
    padding-left: 12px;
    margin: 20px 0 12px 0;
}
.status-bar {
    background: linear-gradient(90deg, #145a32, #1a7a43);
    border-radius: 12px;
    padding: 9px 18px;
    margin-bottom: 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
}
.status-bar span { font-size: 0.86rem; font-weight: 800; color: #eafaf0; }
.status-bar b { color: #bbffd2; }
.ticker-wrap {
    background: #0d3b22;
    border-radius: 12px;
    padding: 13px 20px;
    margin-bottom: 18px;
    display: flex;
    align-items: center;
    gap: 22px;
    flex-wrap: wrap;
}
.ticker-item { font-size: 0.92rem; font-weight: 900; color: #f1fff6; }
.ticker-green { color: #35e884; }
.ticker-red { color: #ff6565; }
.hero {
    background: radial-gradient(circle at 20% 20%, rgba(46,204,113,.25), transparent 30%),
                linear-gradient(135deg, #0d3b22 0%, #145a32 48%, #071f13 100%);
    border-radius: 20px;
    padding: 44px 24px;
    color: white;
    text-align: center;
    box-shadow: 0 10px 30px rgba(13, 59, 34, 0.18);
    margin-bottom: 22px;
}
.hero-title { font-size: 2.15rem; font-weight: 950; margin-bottom: 8px; }
.hero-subtitle { color: #bdf5d1; font-weight: 800; font-size: 1rem; }
.badge-p, .badge-c, .badge-a {
    border-radius: 999px;
    padding: 5px 16px;
    font-size: 0.78rem;
    font-weight: 900;
    display: inline-block;
    margin-top: 6px;
}
.badge-p { background:#d5f5e3; color:#145a32 !important; }
.badge-c { background:#fdebd0; color:#784212 !important; }
.badge-a { background:#e8f1ff; color:#123b7a !important; }
.hw-card, .note-card {
    background: #ffffff;
    border: 1.4px solid #cfe9d8;
    border-radius: 15px;
    padding: 16px 18px;
    box-shadow: 0 3px 14px rgba(20, 90, 50, 0.06);
    margin-bottom: 12px;
    color: #111827;
    line-height: 1.65;
}
.note-card strong, .hw-card strong { color: #145a32; }
.stTabs [data-baseweb="tab-list"] {
    gap: 8px !important;
    background: #e8f5ee !important;
    padding: 7px 9px !important;
    border-radius: 15px !important;
    border: 1.5px solid #a8d8ba !important;
}
.stTabs [data-baseweb="tab"] {
    font-weight: 850 !important;
    border-radius: 11px !important;
    color: #145a32 !important;
    padding: 8px 18px !important;
}
.stTabs [aria-selected="true"] {
    background: #145a32 !important;
    color: #ffffff !important;
    box-shadow: 0 5px 14px rgba(20,90,50,0.22) !important;
}
.stDataFrame { border-radius: 14px !important; }
</style>
""",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# DOSYA VE VERİ YÜKLEME
# ─────────────────────────────────────────────
def module_dir() -> Path:
    try:
        return Path(__file__).resolve().parent
    except NameError:
        return Path.cwd()


def resolve_path(primary_name: str, fallback_names: Optional[list[str]] = None) -> Path:
    fallback_names = fallback_names or []
    names = [primary_name, *fallback_names]
    base_dirs = [Path.cwd(), module_dir(), Path.cwd() / "data", module_dir() / "data"]

    checked: list[Path] = []
    for name in names:
        p = Path(name)
        if p.is_absolute():
            checked.append(p)
            if p.exists():
                return p
            continue
        for base in base_dirs:
            candidate = base / p
            checked.append(candidate)
            if candidate.exists():
                return candidate.resolve()

    checked_text = "\n".join(f"- {x}" for x in checked)
    raise FileNotFoundError(f"Dosya bulunamadı: {primary_name}\nKontrol edilen yollar:\n{checked_text}")


def resolve_optional_epdk_path() -> Optional[Path]:
    candidates = []
    base_dirs = [Path.cwd(), module_dir(), Path.cwd() / "data", module_dir() / "data"]
    explicit_names = [
        "EPDK_Tarifeleri.xlsx",
        "Elektrik_Tarifeleri.xlsx",
        "_PortalAdmin_Uploads_Content_FastAccess_0bd2da5220923 (1).xlsx",
    ]
    for base in base_dirs:
        for name in explicit_names:
            candidates.append(base / name)
        candidates.extend(base.glob("*Tarife*.xlsx"))
        candidates.extend(base.glob("*FastAccess*.xlsx"))

    excluded = {"tuketim_verileri.xlsx", "tuketim_verileri_2.xlsx", "uretim_verileri.xlsx"}
    for path in candidates:
        if not path.exists() or path.name.lower() in excluded:
            continue
        try:
            xl = pd.ExcelFile(path)
            if "Tarife Tablosu" in xl.sheet_names:
                return path.resolve()
        except Exception:
            continue
    return None


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]
    return df


def standardize_datetime_index(df: pd.DataFrame, source_name: str, drop_hour_col: bool = True) -> pd.DataFrame:
    df = clean_column_names(df)
    if "Tarih_Saat" not in df.columns:
        raise ValueError(f"{source_name}: 'Tarih_Saat' kolonu bulunamadı.")

    timestamps = pd.to_datetime(df["Tarih_Saat"], errors="coerce").dt.round("h")
    if timestamps.isna().any():
        raise ValueError(f"{source_name}: Tarih_Saat içinde okunamayan kayıt var.")

    df = df.drop(columns=["Tarih_Saat"])
    if drop_hour_col and "Saat" in df.columns:
        df = df.drop(columns=["Saat"])

    df.index = pd.DatetimeIndex(timestamps, name="Tarih_Saat")
    df = df.sort_index()

    if not df.index.is_unique:
        raise ValueError(f"{source_name}: Tarih_Saat indeksinde tekrar eden kayıt var.")

    return df


def validate_hourly_index(index: pd.DatetimeIndex, source_name: str) -> None:
    if len(index) != 8760:
        raise ValueError(f"{source_name}: 8760 satır bekleniyordu, {len(index)} satır geldi.")

    expected = pd.date_range(start=index[0], periods=len(index), freq="h", name=index.name)
    if not index.equals(expected):
        raise ValueError(f"{source_name}: Tarih_Saat indeksi kesintisiz saatlik seri değil.")


def read_csv_safely(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8", "utf-8-sig", "cp1254", "latin1"):
        try:
            return pd.read_csv(path, encoding=encoding, low_memory=False)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, low_memory=False)


def file_signature(paths: list[Path]) -> tuple[tuple[str, int, int], ...]:
    return tuple((str(p), p.stat().st_size, p.stat().st_mtime_ns) for p in paths if p and p.exists())


@st.cache_data(show_spinner="EPDK tarife bilgileri okunuyor...")
def load_epdk_tariff_cached(path_str: Optional[str], file_sig: tuple[tuple[str, int, int], ...]) -> dict:
    _ = file_sig
    result = {
        "source": "fallback",
        "consumer_grid_price_tl": SEBEKE_ALIS_FIYATI_FALLBACK_TL,
        "consumer_active_energy_tl": None,
        "consumer_distribution_tl": None,
        "producer_distribution_fee_lu1_tl": None,
        "producer_distribution_fee_lu2_tl": None,
    }
    if not path_str:
        return result

    try:
        raw = pd.read_excel(path_str, sheet_name="Tarife Tablosu", header=None, engine="openpyxl")
        table = raw.copy()
        table[[1, 2]] = table[[1, 2]].ffill()

        consumer_mask = (
            table[1].astype(str).str.contains("Dağıtım Sistemi Kullanıcıları", na=False)
            & table[2].astype(str).str.contains("OG Çift Terim", na=False)
            & table[3].astype(str).str.contains("Kamu ve Özel Hizmetler Sektörü ile Diğer", na=False)
        )
        consumer_rows = table[consumer_mask]
        if not consumer_rows.empty:
            row = consumer_rows.iloc[0]
            active_energy_tl = float(row[4]) / 100
            distribution_tl = float(row[8]) / 100
            result["consumer_active_energy_tl"] = active_energy_tl
            result["consumer_distribution_tl"] = distribution_tl
            result["consumer_grid_price_tl"] = active_energy_tl + distribution_tl
            result["source"] = Path(path_str).name

        lu1 = table[table[3].astype(str).str.contains("Lisanssız Üretici 1", na=False)]
        lu2 = table[table[3].astype(str).str.contains("Lisanssız Üretici 2", na=False)]
        if not lu1.empty and pd.notna(lu1.iloc[0, 8]):
            result["producer_distribution_fee_lu1_tl"] = float(lu1.iloc[0, 8]) / 100
        if not lu2.empty and pd.notna(lu2.iloc[0, 8]):
            result["producer_distribution_fee_lu2_tl"] = float(lu2.iloc[0, 8]) / 100
    except Exception:
        pass

    return result


def load_epdk_tariff() -> dict:
    epdk_path = resolve_optional_epdk_path()
    signature = file_signature([epdk_path]) if epdk_path else tuple()
    return load_epdk_tariff_cached(str(epdk_path) if epdk_path else None, signature)


@st.cache_data(show_spinner="Gerçek kampüs verileri yükleniyor ve senkronize ediliyor...")
def load_data_cached(
    tuketim_path: str,
    uretim_path: str,
    p2p_path: str,
    file_sig: tuple[tuple[str, int, int], ...],
) -> pd.DataFrame:
    _ = file_sig
    tuketim = pd.read_excel(tuketim_path, sheet_name="Veriler", engine="openpyxl")
    tuketim = standardize_datetime_index(tuketim, "Tuketim_Verileri", drop_hour_col=True)
    validate_hourly_index(tuketim.index, "Tuketim_Verileri")

    uretim = pd.read_excel(uretim_path, sheet_name="Sayfa1", engine="openpyxl")
    uretim = standardize_datetime_index(uretim, "Uretim_Verileri", drop_hour_col=True)
    validate_hourly_index(uretim.index, "Uretim_Verileri")

    if not tuketim.index.equals(uretim.index):
        raise ValueError("Tüketim ve üretim Tarih_Saat indeksleri birebir aynı değil.")

    p2p = read_csv_safely(Path(p2p_path))
    p2p = clean_column_names(p2p)
    p2p = p2p.loc[:, ~p2p.columns.str.startswith("Unnamed")]

    if "Tarih_Saat" in p2p.columns:
        p2p = standardize_datetime_index(p2p, "P2P_Borsa_Sonuclari", drop_hour_col=True)
        p2p = p2p.reindex(tuketim.index)
        if p2p.isna().all(axis=1).any():
            raise ValueError("P2P dosyasındaki Tarih_Saat verisi ana indeksle eşleşmedi.")
    else:
        if len(p2p) == len(tuketim) + 1:
            warnings.warn(
                "P2P CSV 8761 satır geldi. Tarih_Saat kolonu olmadığı için son fazla satır kırpıldı.",
                UserWarning,
            )
            p2p = p2p.iloc[: len(tuketim)].copy()
        elif len(p2p) != len(tuketim):
            raise ValueError(f"P2P satır sayısı uyumsuz. Beklenen: {len(tuketim)}, gelen: {len(p2p)}")
        p2p.index = tuketim.index.copy()
        p2p.index.name = "Tarih_Saat"

    if "Borsa_Fiyati" in p2p.columns and "P2P_Borsa_Fiyati" not in p2p.columns:
        p2p = p2p.rename(columns={"Borsa_Fiyati": "P2P_Borsa_Fiyati"})

    for frame in (tuketim, uretim, p2p):
        for col in frame.columns:
            if col != "Kampus_Modu":
                frame[col] = pd.to_numeric(frame[col], errors="coerce")

    uretim_cols = [c for c in uretim.columns if c.startswith("Uretim_")]
    tuketim_cols = [c for c in tuketim.columns if c.startswith("Tuketim_") or c.startswith("Tuketici_")]

    uretim[uretim_cols] = uretim[uretim_cols].clip(lower=0)

    df = pd.concat([tuketim, uretim, p2p], axis=1, join="inner", copy=False)
    df.index.name = "Tarih_Saat"

    df["Toplam_Uretim"] = df[uretim_cols].sum(axis=1).clip(lower=0)
    df["Toplam_Tuketim"] = df[tuketim_cols].sum(axis=1).clip(lower=0)
    df["Net_Enerji"] = df["Toplam_Uretim"] - df["Toplam_Tuketim"]

    for col in df.select_dtypes(include=["float64"]).columns:
        df[col] = pd.to_numeric(df[col], downcast="float")

    return df


def load_data() -> pd.DataFrame:
    tuketim_path = resolve_path("Tuketim_Verileri_2.xlsx", ["Tuketim_Verileri.xlsx"])
    uretim_path = resolve_path("Uretim_Verileri.xlsx")
    p2p_path = resolve_path("P2P_Borsa_Sonuclari_2.csv", ["P2P_Borsa_Sonuclari.csv"])
    paths = [tuketim_path, uretim_path, p2p_path]
    return load_data_cached(str(tuketim_path), str(uretim_path), str(p2p_path), file_signature(paths))

# ─────────────────────────────────────────────
# YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────────
def normalize_key(value: str) -> str:
    text = str(value).strip().lower().replace("i̇", "i")
    replace_map = str.maketrans({
        "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
        "Ç": "c", "Ğ": "g", "İ": "i", "I": "i", "Ö": "o", "Ş": "s", "Ü": "u",
    })
    text = text.translate(replace_map)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", text)


def safe(text: object) -> str:
    return html.escape(str(text), quote=True)


def format_number(value: float, digits: int = 1) -> str:
    return f"{value:,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def format_money(value: float, digits: int = 0) -> str:
    return f"₺{format_number(value, digits)}"


def get_price_col(df: pd.DataFrame) -> str:
    candidates = ["P2P_Borsa_Fiyati", "Borsa_Fiyati", "P2P_Fiyat", "P2P_Fiyati"]
    for col in candidates:
        if col in df.columns:
            return col
    raise ValueError("P2P fiyat kolonu bulunamadı. Beklenen: P2P_Borsa_Fiyati veya Borsa_Fiyati")


def get_columns(df: pd.DataFrame) -> tuple[list[str], list[str], list[str]]:
    uretim_cols = [c for c in df.columns if c.startswith("Uretim_")]
    prosumer_tuketim_cols = [c for c in df.columns if c.startswith("Tuketim_")]
    consumer_cols = [c for c in df.columns if c.startswith("Tuketici_")]
    return uretim_cols, prosumer_tuketim_cols, consumer_cols


def display_building_name_from_col(col: str) -> str:
    name = col
    for prefix in ("Tuketici_", "Tuketim_", "Uretim_"):
        name = name.replace(prefix, "")
    name = name.replace("_", " ")
    replacements = {
        "Carsi": "Çarşı",
        "Carsı": "Çarşı",
        "SaglikOcagi": "Sağlık Ocağı",
        "SaglıkOcagı": "Sağlık Ocağı",
        "OgrenciIsleri": "Öğrenci İşleri",
        "Ogrenciisleri": "Öğrenci İşleri",
        "OgrenciDekanligi": "Öğrenci Dekanlığı",
        "IsletmeF": "İşletme Fakültesi",
        "IletisimF": "İletişim Fakültesi",
        "BilMuh": "Bilgisayar Mühendisliği",
        "SporSalonu": "Spor Salonu",
        "FEFD Blok": "FEF D Blok",
        "FEFC Blok": "FEF C Blok",
        "EEMKongre": "EEM Kongre",
        "SubuRektorluk": "SUBÜ Rektörlük",
        "Kutuphane": "Kütüphane",
        "Rektorluk": "Rektörlük",
        "Mimarlik": "Mimarlık",
    }
    compact = name.replace(" ", "")
    return replacements.get(compact, name.title())


def build_user_maps(df: pd.DataFrame) -> tuple[dict[str, dict], dict[str, dict]]:
    prosumer_users: dict[str, dict] = {}
    for key, meta in PROSUMER_META.items():
        col_u = f"Uretim_{meta['col']}"
        col_t = f"Tuketim_{meta['col']}"
        if col_u in df.columns and col_t in df.columns:
            prosumer_users[key] = {**meta, "col_u": col_u, "col_t": col_t}

    consumer_users: dict[str, dict] = {}
    _, _, consumer_cols = get_columns(df)
    for col in consumer_cols:
        display = display_building_name_from_col(col)
        key = normalize_key(col.replace("Tuketici_", ""))
        consumer_users[key] = {"ad": display, "col_t": col}

    return prosumer_users, consumer_users


def authenticate(username: str, password: str, prosumer_users: dict[str, dict], consumer_users: dict[str, dict]) -> tuple[Optional[str], Optional[str]]:
    key = normalize_key(username)
    pw = str(password).strip()
    if key == "admin" and pw == "admin1234":
        return "admin", "admin"
    if key in prosumer_users and pw == f"{key}1234":
        return "prosumer", key
    if key in consumer_users and pw == f"{key}1234":
        return "consumer", key
    return None, None


def snapshot_timestamp(df: pd.DataFrame) -> pd.Timestamp:
    now = dt.datetime.now()
    data_year = int(df.index.min().year)
    try:
        target = pd.Timestamp(year=data_year, month=now.month, day=now.day, hour=now.hour)
    except ValueError:
        target = pd.Timestamp(year=data_year, month=now.month, day=28, hour=now.hour)

    if target < df.index.min():
        target = df.index.min()
    if target > df.index.max():
        target = df.index.max()

    pos = df.index.get_indexer([target], method="nearest")[0]
    return pd.Timestamp(df.index[pos])


def tr_datetime(ts: pd.Timestamp) -> str:
    return f"{ts.day} {TR_AYLAR[ts.month]} {ts.year}, {TR_GUNLER[ts.weekday()]}"


def kpi_card(label: str, value: str, unit: str = "", color: str = RENK_LACIVERT) -> None:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{safe(label)}</div>
            <div class="kpi-value" style="color:{color};">{safe(value)}</div>
            <div class="kpi-unit">{safe(unit)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(text: str) -> None:
    st.markdown(f'<div class="sec-hdr">{safe(text)}</div>', unsafe_allow_html=True)


def base_layout(title: str, height: int = 380, legend_orientation: str = "h") -> dict:
    legend = dict(
        orientation=legend_orientation,
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        bgcolor="rgba(255,255,255,0.82)",
        font=dict(size=12, color="#111827"),
    )
    if legend_orientation == "v":
        legend = dict(x=1.02, y=1, bgcolor="rgba(255,255,255,0.82)", font=dict(size=12, color="#111827"))

    return dict(
        title=dict(text=title, font=dict(size=16, color="#111827")),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#111827", size=13, family="Segoe UI"),
        margin=dict(t=70, b=72, l=70, r=35),
        hovermode="x unified",
        height=height,
        legend=legend,
    )


def style_axes(fig: go.Figure, x_title: str, y_title: str, tickangle: int = 0, dtick: Optional[int] = None) -> None:
    x_axis = dict(
        title_text=x_title,
        title_font=dict(size=14, color="#111827"),
        tickfont=dict(size=11, color="#111827"),
        showgrid=True,
        gridcolor="#e8ecea",
        linecolor="#cfd8d3",
        linewidth=1,
        tickangle=tickangle,
    )
    if dtick is not None:
        x_axis["dtick"] = dtick
    fig.update_xaxes(**x_axis)
    fig.update_yaxes(
        title_text=y_title,
        title_font=dict(size=14, color="#111827"),
        tickfont=dict(size=11, color="#111827"),
        showgrid=True,
        gridcolor="#e8ecea",
        linecolor="#cfd8d3",
        linewidth=1,
        rangemode="tozero",
    )


def price_series(df: pd.DataFrame, col: str, freq: str) -> pd.Series:
    return df[col].resample(freq).mean()


def energy_series(df: pd.DataFrame, col: str, freq: str) -> pd.Series:
    return df[col].resample(freq).sum()


def daily_slice(df: pd.DataFrame, day: dt.date) -> pd.DataFrame:
    start = pd.Timestamp(day)
    end = start + pd.Timedelta(hours=23)
    return df.loc[start:end].copy()


def coverage_ratio(df: pd.DataFrame) -> pd.Series:
    ratio = df["Toplam_Uretim"] / df["Toplam_Tuketim"].replace(0, pd.NA)
    ratio = ratio.fillna(0).clip(lower=0, upper=1)
    return ratio


def consumer_energy_split(df: pd.DataFrame, col_t: str) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    out["Tuketim"] = df[col_t].clip(lower=0)
    ratio = coverage_ratio(df)
    out["P2P_Karsilanan"] = (out["Tuketim"] * ratio).clip(lower=0)
    out["Sebeke_Karsilanan"] = (out["Tuketim"] - out["P2P_Karsilanan"]).clip(lower=0)
    return out


def monthly_consumer_billing(df: pd.DataFrame, col_t: str, price_col: str, grid_price_tl: float) -> pd.DataFrame:
    split = consumer_energy_split(df, col_t)
    calc = split.copy()
    calc["P2P_Maliyet"] = calc["P2P_Karsilanan"] * df[price_col]
    calc["Sebeke_Tamamlayici_Maliyet"] = calc["Sebeke_Karsilanan"] * grid_price_tl
    calc["P2P_Destekli_Maliyet"] = calc["P2P_Maliyet"] + calc["Sebeke_Tamamlayici_Maliyet"]
    calc["Tam_Sebeke_Senaryosu"] = calc["Tuketim"] * grid_price_tl

    monthly = calc.resample("ME").sum()
    monthly["Maliyet_Avantaji"] = monthly["Tam_Sebeke_Senaryosu"] - monthly["P2P_Destekli_Maliyet"]
    monthly["Avantaj_Orani_%"] = (monthly["Maliyet_Avantaji"] / monthly["Tam_Sebeke_Senaryosu"].replace(0, pd.NA) * 100).fillna(0)
    monthly["Ay"] = [TR_AYLAR[d.month] for d in monthly.index]
    return monthly


def prosumer_sales_split(df: pd.DataFrame, col_u: str, col_t: str) -> pd.DataFrame:
    """Prosumer fazla üretimini kooperatife satılan ve şebekeye kalan kısım olarak ayırır."""
    out = pd.DataFrame(index=df.index)
    out["Fazla_Uretim"] = (df[col_u] - df[col_t]).clip(lower=0)

    total_surplus = pd.Series(0.0, index=df.index)
    seen_cols: set[str] = set()
    for meta in PROSUMER_META.values():
        u_col = f"Uretim_{meta['col']}"
        t_col = f"Tuketim_{meta['col']}"
        pair_key = f"{u_col}|{t_col}"
        if pair_key in seen_cols:
            continue
        seen_cols.add(pair_key)
        if u_col in df.columns and t_col in df.columns:
            total_surplus += (df[u_col] - df[t_col]).clip(lower=0)

    if "Sebekeye_Satis" in df.columns:
        total_grid_export = df["Sebekeye_Satis"].clip(lower=0)
        matched_total = (total_surplus - total_grid_export).clip(lower=0)
        match_ratio = (matched_total / total_surplus.where(total_surplus != 0)).fillna(0).clip(lower=0, upper=1)
    else:
        remaining_demand = (df["Toplam_Tuketim"] - df["Toplam_Uretim"]).clip(lower=0)
        match_ratio = (remaining_demand / total_surplus.where(total_surplus != 0)).fillna(0).clip(lower=0, upper=1)

    out["Kooperatife_Satilan"] = (out["Fazla_Uretim"] * match_ratio).clip(lower=0)
    out["Sebekeye_Kalan"] = (out["Fazla_Uretim"] - out["Kooperatife_Satilan"]).clip(lower=0)
    return out

# ─────────────────────────────────────────────
# SIDEBAR VE ÜST BAR
# ─────────────────────────────────────────────
def sidebar_login(prosumer_users: dict[str, dict], consumer_users: dict[str, dict]) -> None:
    with st.sidebar:
        st.markdown(
            """
            <div style="text-align:center;padding:18px 0 22px 0;">
                <div style="font-size:2.4rem;line-height:1;">⚡🌿</div>
                <div style="font-size:1.12rem;font-weight:950;margin-top:9px;">SAU Enerji Kooperatifi</div>
                <div style="font-size:0.75rem;opacity:0.72;margin-top:5px;">P2P İzleme Platformu v5.0</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if "rol" not in st.session_state:
            st.session_state.rol = None
            st.session_state.kullanici = None

        if st.session_state.rol is None:
            st.markdown("### 🔐 Giriş Yap")
            username = st.text_input("Kullanıcı Adı", placeholder="Kullanıcı Adı", key="login_username")
            password = st.text_input("Şifre", placeholder="Şifre", type="password", key="login_password")
            if st.button("Giriş Yap", use_container_width=True, type="primary"):
                rol, kullanici = authenticate(username, password, prosumer_users, consumer_users)
                if rol:
                    st.session_state.rol = rol
                    st.session_state.kullanici = kullanici
                    st.rerun()
                else:
                    st.error("Kullanıcı adı veya şifre hatalı.")
        else:
            rol = st.session_state.rol
            key = st.session_state.kullanici
            if rol == "prosumer":
                display = prosumer_users[key]["ad"]
                badge = "Üretici / Prosümer"
                cls = "badge-p"
            elif rol == "consumer":
                display = consumer_users[key]["ad"]
                badge = "Tüketici"
                cls = "badge-c"
            else:
                display = "Admin"
                badge = "Sistem Yöneticisi"
                cls = "badge-a"

            st.markdown(
                f"""
                <div style="text-align:center;margin-bottom:18px;">
                    <div style="font-size:1.05rem;font-weight:950;color:#ffffff !important;">👤 {safe(display)}</div>
                    <span class="{cls}">{safe(badge)}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("🚪 Çıkış Yap", use_container_width=True):
                st.session_state.rol = None
                st.session_state.kullanici = None
                st.rerun()

        st.markdown("---")
        st.markdown(
            """
            <div style="font-size:0.72rem;opacity:0.62;text-align:center;line-height:1.55;">
            Sakarya Üniversitesi<br>Enerji Kooperatifi İzleme Sistemi<br>© 2026
            </div>
            """,
            unsafe_allow_html=True,
        )


def status_and_ticker(df: pd.DataFrame, price_col: str, snap: pd.Timestamp, grid_price_tl: float) -> None:
    last_24 = df.loc[snap - pd.Timedelta(hours=23):snap]
    p2p_anlik = float(last_24[price_col].mean())
    current_prod = float(df.loc[snap, "Toplam_Uretim"])
    temp_text = "Veri yok"
    if "Sicaklik_C" in df.columns and pd.notna(df.loc[snap, "Sicaklik_C"]):
        temp_text = f"{float(df.loc[snap, 'Sicaklik_C']):.1f} °C"

    st.markdown(
        f"""
        <div class="status-bar">
            <span>📅 <b>{safe(tr_datetime(snap))}</b></span>
            <span>🌡️ Kampüs Sıcaklığı: <b>{safe(temp_text)}</b></span>
            <span>⏱️ Veri Saati: <b>{snap.strftime('%H:%M')}</b></span>
        </div>
        <div class="ticker-wrap">
            <span class="ticker-item">📊 CANLI ENERJİ BORSASI</span>
            <span class="ticker-item">🟢 Kooperatif P2P: <span class="ticker-green">{p2p_anlik:.4f} ₺/kWh</span></span>
            <span class="ticker-item">🔴 EPDK Şebeke Alış: <span class="ticker-red">{grid_price_tl:.2f} ₺/kWh</span></span>
            <span class="ticker-item">⚡ Anlık Üretim: <span class="ticker-green">{current_prod:.2f} kWh</span></span>
            <span class="ticker-item">🏭 Prosümer: <b>10 bina</b></span>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────
# GRAFİKLER
# ─────────────────────────────────────────────
def chart_monthly_campus_balance(df: pd.DataFrame) -> go.Figure:
    monthly = df[["Toplam_Uretim", "Toplam_Tuketim"]].resample("ME").sum()
    x = [TR_AYLAR[d.month] for d in monthly.index]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=monthly["Toplam_Uretim"], name="Toplam Üretim", marker_color=RENK_URETIM))
    fig.add_trace(go.Bar(x=x, y=monthly["Toplam_Tuketim"], name="Toplam Tüketim", marker_color=RENK_TUKETIM))
    fig.update_layout(**base_layout("Aylık Yerleşke Arz-Talep Dengesi", height=405))
    fig.update_layout(barmode="group")
    style_axes(fig, "Ay", "Enerji (kWh)")
    return fig


def chart_price(df: pd.DataFrame, price_col: str, snap: pd.Timestamp, grid_price_tl: float) -> None:
    section_header("💹 Kooperatif P2P Fiyatı ve EPDK Şebeke Referansı")
    mode = st.radio(
        "Fiyat grafiği görünümü",
        ["Günlük", "Haftalık", "Aylık"],
        horizontal=True,
        key="price_mode",
        label_visibility="collapsed",
    )

    if mode == "Günlük":
        selected_day = st.date_input(
            "Fiyat grafiği günü",
            value=snap.date(),
            min_value=df.index.min().date(),
            max_value=df.index.max().date(),
            key="price_day",
        )
        data = daily_slice(df, selected_day)
        x = data.index
        y = data[price_col]
        title = "Günlük Saatlik P2P Fiyat Profili"
        x_title = "Saat"
        tickangle = -90
        dtick = 3600000

    elif mode == "Haftalık":
        start_default = max(df.index.min().date(), (snap - pd.Timedelta(days=6)).date())
        date_range = st.date_input(
            "Haftalık fiyat aralığı — en fazla 7 gün",
            value=(start_default, snap.date()),
            min_value=df.index.min().date(),
            max_value=df.index.max().date(),
            key="price_week_range",
        )
        if not isinstance(date_range, tuple) or len(date_range) != 2:
            st.warning("Haftalık görünüm için başlangıç ve bitiş tarihi seçin.")
            return
        start_day, end_day = date_range
        day_count = (pd.Timestamp(end_day) - pd.Timestamp(start_day)).days + 1
        if day_count > 7:
            st.warning("Haftalık görünüm için en fazla 7 gün seçebilirsiniz.")
            return
        data = df.loc[pd.Timestamp(start_day): pd.Timestamp(end_day) + pd.Timedelta(hours=23)]
        daily_avg = data[price_col].resample("D").mean()
        x = [f"{TR_GUNLER_KISA[d.weekday()]}<br>{d.day} {TR_AYLAR[d.month]}" for d in daily_avg.index]
        y = daily_avg.values
        title = "Haftalık Günlük Ortalama P2P Fiyatı"
        x_title = "Gün"
        tickangle = 0
        dtick = None

    else:
        monthly = price_series(df, price_col, "ME")
        x = [TR_AYLAR[d.month] for d in monthly.index]
        y = monthly.values
        title = "Aylık Ortalama P2P Fiyatı"
        x_title = "Ay"
        tickangle = 0
        dtick = None

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x,
        y=y,
        name="Kooperatif P2P Fiyatı",
        mode="lines+markers",
        line=dict(color=RENK_URETIM, width=3),
        marker=dict(size=7),
    ))
    fig.add_hline(
        y=grid_price_tl,
        line_dash="dot",
        line_color=RENK_KIRMIZI,
        annotation_text=f"EPDK Şebeke Alış {grid_price_tl:.2f} ₺/kWh",
        annotation_font_color=RENK_KIRMIZI,
    )
    fig.update_layout(**base_layout(title, height=405))
    style_axes(fig, x_title, "Fiyat (₺/kWh)", tickangle=tickangle, dtick=dtick)
    st.plotly_chart(fig, use_container_width=True)


def chart_consumer_24h(df: pd.DataFrame, col_t: str) -> go.Figure:
    split = consumer_energy_split(df, col_t)
    hourly = split.groupby(split.index.hour)[["P2P_Karsilanan", "Sebeke_Karsilanan"]].mean()
    x = [f"{h:02d}:00" for h in hourly.index]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=hourly["P2P_Karsilanan"], name="Kooperatiften Alınan Enerji", marker_color=RENK_URETIM))
    fig.add_trace(go.Bar(x=x, y=hourly["Sebeke_Karsilanan"], name="Şebekeden Alınan Enerji", marker_color=RENK_SEBEKE))
    fig.update_layout(**base_layout("24 Saatlik Ortalama Tüketim Dağılımı", height=395))
    fig.update_layout(barmode="stack")
    style_axes(fig, "Saat", "Ortalama Enerji (kWh)", tickangle=-90)
    return fig


def chart_consumer_time_series(df: pd.DataFrame, col_t: str, snap: pd.Timestamp, bina_adi: str) -> None:
    section_header(f"📅 {bina_adi} Tüketim Zaman Serisi")
    mode = st.radio(
        "Tüketim zaman serisi görünümü",
        ["Günlük", "Haftalık", "Aylık"],
        horizontal=True,
        key=f"ts_mode_{col_t}",
        label_visibility="collapsed",
    )

    if mode == "Günlük":
        selected_day = st.date_input(
            "Tüketim günü",
            value=snap.date(),
            min_value=df.index.min().date(),
            max_value=df.index.max().date(),
            key=f"ts_day_{col_t}",
        )
        data = daily_slice(df, selected_day)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=data.index, y=data[col_t], name="Tüketim", marker_color=RENK_TUKETIM))
        fig.update_layout(**base_layout("Günlük Saatlik Tüketim", height=370))
        style_axes(fig, "Saat", "Enerji (kWh)", tickangle=-90, dtick=3600000)

    elif mode == "Haftalık":
        start_default = max(df.index.min().date(), (snap - pd.Timedelta(days=6)).date())
        date_range = st.date_input(
            "Haftalık tüketim aralığı — en fazla 7 gün",
            value=(start_default, snap.date()),
            min_value=df.index.min().date(),
            max_value=df.index.max().date(),
            key=f"ts_week_{col_t}",
        )
        if not isinstance(date_range, tuple) or len(date_range) != 2:
            st.warning("Haftalık görünüm için başlangıç ve bitiş tarihi seçin.")
            return
        start_day, end_day = date_range
        day_count = (pd.Timestamp(end_day) - pd.Timestamp(start_day)).days + 1
        if day_count > 7:
            st.warning("Haftalık görünüm için en fazla 7 gün seçebilirsiniz.")
            return
        data = df.loc[pd.Timestamp(start_day): pd.Timestamp(end_day) + pd.Timedelta(hours=23), col_t]
        weekly = data.resample("D").sum()
        x = [f"{TR_GUNLER_KISA[d.weekday()]}<br>{d.day} {TR_AYLAR[d.month]}" for d in weekly.index]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=x, y=weekly.values, name="Günlük Toplam Tüketim", marker_color=RENK_TUKETIM))
        fig.update_layout(**base_layout("Haftalık Tüketim — Günlük Toplamlar", height=370))
        style_axes(fig, "Gün", "Enerji (kWh)")

    else:
        monthly = energy_series(df, col_t, "ME")
        x = [TR_AYLAR[d.month] for d in monthly.index]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=x, y=monthly.values, name="Aylık Toplam Tüketim", marker_color=RENK_TUKETIM))
        fig.update_layout(**base_layout("Aylık Toplam Tüketim", height=370))
        style_axes(fig, "Ay", "Enerji (kWh)")

    st.plotly_chart(fig, use_container_width=True)


def chart_prosumer_flow(df: pd.DataFrame, col_u: str, col_t: str, snap: pd.Timestamp, bina_adi: str) -> None:
    section_header(f"📈 {bina_adi} Günlük Üretim-Tüketim Akışı")
    selected_day = st.date_input(
        "Gün seçimi",
        value=snap.date(),
        min_value=df.index.min().date(),
        max_value=df.index.max().date(),
        key=f"prosumer_day_{col_u}",
    )
    data = daily_slice(df, selected_day)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=data.index, y=data[col_u], name="Üretim", marker_color=RENK_URETIM))
    fig.add_trace(go.Bar(x=data.index, y=data[col_t], name="Tüketim", marker_color=RENK_TUKETIM))
    fig.update_layout(**base_layout("Seçili Gün Saatlik Üretim ve Tüketim", height=410))
    fig.update_layout(barmode="group")
    style_axes(fig, "Saat", "Enerji (kWh)", tickangle=-90, dtick=3600000)
    st.plotly_chart(fig, use_container_width=True)


def chart_daily_pv_profile(df: pd.DataFrame, col_u: str, snap: pd.Timestamp, bina_adi: str) -> None:
    section_header(f"☀️ {bina_adi} Günlük PV Üretim Profili")
    selected_day = st.date_input(
        "PV üretim günü",
        value=snap.date(),
        min_value=df.index.min().date(),
        max_value=df.index.max().date(),
        key=f"pv_day_{col_u}",
    )
    day_data = daily_slice(df, selected_day)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=day_data.index,
        y=day_data[col_u],
        name="PV Üretim",
        mode="lines+markers",
        line=dict(color=RENK_URETIM, width=3),
        fill="tozeroy",
    ))
    fig.update_layout(**base_layout("Seçili Gün Saatlik PV Üretimi", height=360))
    style_axes(fig, "Saat", "Üretim (kWh)", tickangle=-90, dtick=3600000)
    st.plotly_chart(fig, use_container_width=True)


def chart_monthly_self_consumption(df: pd.DataFrame, col_u: str, col_t: str) -> go.Figure:
    sales = prosumer_sales_split(df, col_u, col_t)
    local = pd.DataFrame(index=df.index)
    local["Oz_Tuketim"] = pd.concat([df[col_u], df[col_t]], axis=1).min(axis=1)
    local["Kooperatife_Satilan"] = sales["Kooperatife_Satilan"]
    local["Sebekeye_Kalan"] = sales["Sebekeye_Kalan"]
    local["Sebekeden_Alis"] = (df[col_t] - df[col_u]).clip(lower=0)
    monthly = local.resample("ME").sum()
    x = [TR_AYLAR[d.month] for d in monthly.index]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=monthly["Oz_Tuketim"], name="Öz Tüketim", marker_color=RENK_URETIM))
    fig.add_trace(go.Bar(x=x, y=monthly["Kooperatife_Satilan"], name="Kooperatife Satılan", marker_color=RENK_MAVI))
    fig.add_trace(go.Bar(x=x, y=monthly["Sebekeye_Kalan"], name="Şebekeye Kalan", marker_color=RENK_SEBEKE))
    fig.add_trace(go.Bar(x=x, y=monthly["Sebekeden_Alis"], name="Şebekeden Alış", marker_color=RENK_TUKETIM))
    fig.update_layout(**base_layout("Aylık Enerji Kullanım Dağılımı", height=385))
    fig.update_layout(barmode="stack")
    style_axes(fig, "Ay", "Enerji (kWh)")
    return fig

# ─────────────────────────────────────────────
# SAYFALAR
# ─────────────────────────────────────────────
def public_page(df: pd.DataFrame, price_col: str, snap: pd.Timestamp, grid_price_tl: float) -> None:
    st.markdown(
        """
        <div class="hero">
            <div class="hero-title">⚡ SAU Enerji Kooperatifi</div>
            <div class="hero-subtitle">Merkezi İzleme ve P2P Enerji Ticaret Portalı</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    toplam_u_gwh = float(df["Toplam_Uretim"].sum()) / 1_000_000
    toplam_t_gwh = float(df["Toplam_Tuketim"].sum()) / 1_000_000
    p2p_ort = float(df[price_col].mean())
    indirim_pct = (grid_price_tl - p2p_ort) / grid_price_tl * 100

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Toplam Tüketim", f"{toplam_t_gwh:.2f}", "GWh / Yıl", RENK_TUKETIM)
    with c2:
        kpi_card("Toplam Üretim", f"{toplam_u_gwh:.2f}", "GWh / Yıl", RENK_URETIM)
    with c3:
        kpi_card("P2P Ortalama Fiyat", f"{p2p_ort:.3f}", "₺/kWh", RENK_MAVI)
    with c4:
        kpi_card("Şebekeye Kıyasla", f"-{indirim_pct:.1f}%", "Kooperatif Avantajı", RENK_MOR)

    section_header("📊 Yerleşke Arz-Talep Dengesi")
    st.plotly_chart(chart_monthly_campus_balance(df), use_container_width=True)

    chart_price(df, price_col, snap, grid_price_tl)

    st.info("🔐 Kişisel üretim/tüketim verilerine erişmek için sol panelden giriş yapın.")


def consumer_page(df: pd.DataFrame, price_col: str, user_meta: dict, snap: pd.Timestamp, tariff: dict) -> None:
    grid_price_tl = float(tariff["consumer_grid_price_tl"])
    bina_adi = user_meta["ad"]
    col_t = user_meta["col_t"]
    split = consumer_energy_split(df, col_t)

    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:14px;margin-bottom:16px;">
            <div style="font-size:2.1rem;">🏢</div>
            <div>
                <div style="font-size:1.55rem;font-weight:950;color:#145a32;">Tüketici Paneli — {safe(bina_adi)}</div>
                <span class="badge-c">Saf Tüketici</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab1, tab2 = st.tabs(["📉 Tüketim Geçmişi", "🧾 Fatura Analizi"])

    with tab1:
        toplam_t_kwh = float(split["Tuketim"].sum())
        ort_saat = float(split["Tuketim"].mean())
        p2p_ratio = float(split["P2P_Karsilanan"].sum() / toplam_t_kwh * 100) if toplam_t_kwh else 0

        k1, k2, k3 = st.columns(3)
        with k1:
            kpi_card("Yıllık Tüketim", f"{toplam_t_kwh / 1000:.1f}", "MWh / Yıl", RENK_TUKETIM)
        with k2:
            kpi_card("Saatlik Ortalama", f"{ort_saat:.2f}", "kWh / Saat", RENK_SEBEKE)
        with k3:
            kpi_card("Kooperatif Kapsama", f"{p2p_ratio:.1f}%", "Yıllık Enerji Payı", RENK_URETIM)

        section_header("🕐 24 Saatlik Ortalama Tüketim Profili")
        st.plotly_chart(chart_consumer_24h(df, col_t), use_container_width=True)

        chart_consumer_time_series(df, col_t, snap, bina_adi)

    with tab2:
        monthly = monthly_consumer_billing(df, col_t, price_col, grid_price_tl)
        tam_sebeke_toplam = float(monthly["Tam_Sebeke_Senaryosu"].sum())
        p2p_destekli_toplam = float(monthly["P2P_Destekli_Maliyet"].sum())
        toplam_avantaj = float(monthly["Maliyet_Avantaji"].sum())

        c1, c2, c3 = st.columns(3)
        with c1:
            kpi_card("Tam Şebeke Senaryosu", format_money(tam_sebeke_toplam), "Yıllık Maliyet", RENK_KIRMIZI)
        with c2:
            kpi_card("P2P Destekli Senaryo", format_money(p2p_destekli_toplam), "Kooperatif + Şebeke", RENK_URETIM)
        with c3:
            kpi_card("Maliyet Avantajı", format_money(toplam_avantaj), "Yıllık Kazanım", RENK_MAVI)

        section_header("📊 Aylık Fatura Karşılaştırması")
        fig_fatura = go.Figure()
        fig_fatura.add_trace(go.Bar(x=monthly["Ay"], y=monthly["Tam_Sebeke_Senaryosu"], name="Tam Şebeke Senaryosu", marker_color=RENK_KIRMIZI))
        fig_fatura.add_trace(go.Bar(x=monthly["Ay"], y=monthly["P2P_Destekli_Maliyet"], name="P2P Destekli Senaryo", marker_color=RENK_URETIM))
        fig_fatura.update_layout(**base_layout("Aylık Maliyet — Tam Şebeke vs P2P Destekli Senaryo", height=385))
        fig_fatura.update_layout(barmode="group")
        style_axes(fig_fatura, "Ay", "Maliyet (₺)")
        st.plotly_chart(fig_fatura, use_container_width=True)

        left, right = st.columns([2, 1])
        with left:
            section_header("💰 Aylık Maliyet Avantajı")
            fig_tas = go.Figure()
            fig_tas.add_trace(go.Bar(x=monthly["Ay"], y=monthly["Maliyet_Avantaji"], name="Maliyet Avantajı", marker_color=RENK_MAVI))
            fig_tas.add_trace(go.Scatter(x=monthly["Ay"], y=monthly["Avantaj_Orani_%"], name="Avantaj Oranı (%)", mode="lines+markers", yaxis="y2", line=dict(color=RENK_MOR, width=3)))
            fig_tas.update_layout(**base_layout("Aylık Maliyet Avantajı ve Oranı", height=330))
            fig_tas.update_layout(
                yaxis=dict(title="Avantaj (₺)", showgrid=True, gridcolor="#e8ecea"),
                yaxis2=dict(title="Avantaj (%)", overlaying="y", side="right", showgrid=False, rangemode="tozero"),
            )
            st.plotly_chart(fig_tas, use_container_width=True)

        with right:
            section_header("🧾 Veri Seti Özeti")
            inferred_freq = pd.infer_freq(df.index) or "Saatlik"
            st.markdown(
                f"""
                <div class="hw-card">
                    <strong>Kayıt Sayısı:</strong> {len(df):,} saat<br>
                    <strong>İlk Veri:</strong> {df.index.min().strftime('%d.%m.%Y %H:%M')}<br>
                    <strong>Son Veri:</strong> {df.index.max().strftime('%d.%m.%Y %H:%M')}<br>
                    <strong>Veri Frekansı:</strong> {safe(inferred_freq)}<br>
                    <strong>P2P Fiyat Kolonu:</strong> {safe(price_col)}<br>
                    <strong>Şebeke Alış Referansı:</strong> {grid_price_tl:.4f} ₺/kWh<br>
                    <strong>Tarife Kaynağı:</strong> {safe(tariff['source'])}
                </div>
                """,
                unsafe_allow_html=True,
            )

        with st.expander("📋 Aylık Detay Tablosu", expanded=False):
            table = monthly[[
                "Ay",
                "Tuketim",
                "P2P_Karsilanan",
                "Sebeke_Karsilanan",
                "P2P_Maliyet",
                "Sebeke_Tamamlayici_Maliyet",
                "P2P_Destekli_Maliyet",
                "Tam_Sebeke_Senaryosu",
                "Maliyet_Avantaji",
                "Avantaj_Orani_%",
            ]].copy()
            table = table.rename(columns={
                "Tuketim": "Toplam Talep (kWh)",
                "P2P_Karsilanan": "Kooperatiften Alınan Enerji (kWh)",
                "Sebeke_Karsilanan": "Şebekeden Alınan Enerji (kWh)",
                "P2P_Maliyet": "Kooperatif Enerji Bedeli (₺)",
                "Sebeke_Tamamlayici_Maliyet": "Şebeke Enerji Bedeli (₺)",
                "P2P_Destekli_Maliyet": "P2P Destekli Toplam Maliyet (₺)",
                "Tam_Sebeke_Senaryosu": "Tam Şebeke Senaryosu (₺)",
                "Maliyet_Avantaji": "Aylık Maliyet Avantajı (₺)",
                "Avantaj_Orani_%": "Avantaj Oranı (%)",
            })
            numeric_cols = table.select_dtypes(include="number").columns
            table[numeric_cols] = table[numeric_cols].round(2)
            st.dataframe(table, use_container_width=True, hide_index=True)


def prosumer_page(df: pd.DataFrame, price_col: str, user_meta: dict, snap: pd.Timestamp, tariff: dict) -> None:
    bina_adi = user_meta["ad"]
    col_u = user_meta["col_u"]
    col_t = user_meta["col_t"]
    kwp = user_meta["kwp"]

    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:14px;margin-bottom:16px;">
            <div style="font-size:2.1rem;">🏭</div>
            <div>
                <div style="font-size:1.55rem;font-weight:950;color:#145a32;">Üretici Paneli — {safe(bina_adi)}</div>
                <span class="badge-p">Prosümer · {kwp} kWp</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab1, tab2, tab3 = st.tabs(["📈 Genel Özet", "💰 Satış Geliri Analizi", "🔧 Donanım"])

    with tab1:
        total_u = float(df[col_u].sum())
        total_t = float(df[col_t].sum())
        self_cons = float(pd.concat([df[col_u], df[col_t]], axis=1).min(axis=1).sum())
        sales_split = prosumer_sales_split(df, col_u, col_t)
        coop_sales_energy = float(sales_split["Kooperatife_Satilan"].sum())

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            kpi_card("Yıllık Üretim", f"{total_u / 1000:.1f}", "MWh", RENK_URETIM)
        with c2:
            kpi_card("Yıllık Tüketim", f"{total_t / 1000:.1f}", "MWh", RENK_TUKETIM)
        with c3:
            kpi_card("Öz Tüketim", f"{self_cons / 1000:.1f}", "MWh", RENK_MOR)
        with c4:
            kpi_card("Kooperatife Satılan", f"{coop_sales_energy / 1000:.1f}", "MWh / Yıl", RENK_MAVI)

        chart_prosumer_flow(df, col_u, col_t, snap, bina_adi)
        chart_daily_pv_profile(df, col_u, snap, bina_adi)

        section_header("📊 Aylık Öz Tüketim ve Enerji Akışı")
        st.plotly_chart(chart_monthly_self_consumption(df, col_u, col_t), use_container_width=True)

    with tab2:
        sales = prosumer_sales_split(df, col_u, col_t)
        sales["P2P_Gelir"] = sales["Kooperatife_Satilan"] * df[price_col]
        coop_energy = float(sales["Kooperatife_Satilan"].sum())
        grid_remaining_energy = float(sales["Sebekeye_Kalan"].sum())
        p2p_income = float(sales["P2P_Gelir"].sum())
        weighted_p2p_price = p2p_income / coop_energy if coop_energy > 0 else float(df[price_col].mean())

        st.markdown(
            """
            <div class="note-card">
                Bu bölüm, prosumer binanın kendi tüketimini karşıladıktan sonra kalan fazla üretimin
                kooperatif üyeleriyle eşleşen kısmından elde ettiği satış gelirini gösterir. Öz tüketim gelir değil,
                binanın kendi şebeke alımını azaltan enerji olarak değerlendirilir.
            </div>
            """,
            unsafe_allow_html=True,
        )

        reference_price = st.number_input(
            "Şebekeye satış referans bedeli (₺/kWh) — gerçek sözleşme/YEKDEM/mahsuplaşma bedeli biliniyorsa girin",
            min_value=0.0,
            value=float(URETICI_SEBEKE_SATIS_REFERANS_VARSAYILAN_TL),
            step=0.01,
            format="%.4f",
            key=f"producer_reference_price_{col_u}",
            help="Bu değer EPDK tüketici alış tarifesi değildir. Tesisin lisanssız üretim statüsüne, mahsuplaşma yapısına ve ilgili görevli tedarik/market referansına göre ayrıca belirlenmelidir.",
        )

        reference_income = coop_energy * reference_price if reference_price > 0 else 0.0
        additional_gain = p2p_income - reference_income if reference_price > 0 else None

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            kpi_card("Kooperatife Satılan Enerji", f"{coop_energy / 1000:.1f}", "MWh / Yıl", RENK_MAVI)
        with c2:
            kpi_card("P2P Satış Geliri", format_money(p2p_income), "Yıllık", RENK_URETIM)
        with c3:
            kpi_card("Ortalama P2P Satış", f"{weighted_p2p_price:.3f}", "₺/kWh", RENK_MOR)
        with c4:
            if additional_gain is None:
                kpi_card("Referans Ek Gelir", "—", "Referans bedel girilmedi", RENK_SEBEKE)
            else:
                kpi_card("Referansa Göre Ek Gelir", format_money(additional_gain), "Yıllık", RENK_TUKETIM if additional_gain < 0 else RENK_URETIM)

        section_header("📈 Aylık Kooperatif Satış Geliri")
        monthly = sales[["Kooperatife_Satilan", "Sebekeye_Kalan", "P2P_Gelir"]].resample("ME").sum()
        x = [TR_AYLAR[d.month] for d in monthly.index]

        fig = go.Figure()
        fig.add_trace(go.Bar(x=x, y=monthly["P2P_Gelir"], name="P2P Satış Geliri", marker_color=RENK_URETIM))
        fig.add_trace(go.Scatter(x=x, y=monthly["Kooperatife_Satilan"], name="Kooperatife Satılan Enerji (kWh)", yaxis="y2", mode="lines+markers", line=dict(color=RENK_MAVI, width=3)))
        fig.update_layout(**base_layout("Aylık P2P Satış Geliri ve Satılan Enerji", height=390))
        fig.update_layout(
            yaxis=dict(title="Gelir (₺)", showgrid=True, gridcolor="#e8ecea"),
            yaxis2=dict(title="Enerji (kWh)", overlaying="y", side="right", showgrid=False),
        )
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📋 Satış Geliri Detayı", expanded=False):
            rows = [
                {
                    "Satış Kanalı": "Kooperatif üyelerine satış",
                    "Enerji (kWh)": round(coop_energy, 2),
                    "Birim Bedel (₺/kWh)": round(weighted_p2p_price, 4),
                    "Yıllık Gelir (₺)": round(p2p_income, 2),
                    "Açıklama": "Fazla üretimin kampüs içi talep ile eşleşen kısmı",
                },
                {
                    "Satış Kanalı": "Şebekeye kalan fazla enerji",
                    "Enerji (kWh)": round(grid_remaining_energy, 2),
                    "Birim Bedel (₺/kWh)": "—",
                    "Yıllık Gelir (₺)": "—",
                    "Açıklama": "Kooperatif içinde eşleşmeyen fazla üretim",
                },
            ]
            if reference_price > 0:
                rows.append({
                    "Satış Kanalı": "Aynı enerji şebekeye satılsaydı",
                    "Enerji (kWh)": round(coop_energy, 2),
                    "Birim Bedel (₺/kWh)": round(reference_price, 4),
                    "Yıllık Gelir (₺)": round(reference_income, 2),
                    "Açıklama": "Manuel girilen üretici satış referansına göre karşılaştırma",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with tab3:
        left, right = st.columns([1, 1])
        with left:
            section_header("⚙️ PVsyst Sistem Parametreleri")
            st.markdown(
                f"""
                <div class="hw-card">
                    <strong>Bina:</strong> {safe(bina_adi)}<br>
                    <strong>Kurulu Güç:</strong> {kwp} kWp<br>
                    <strong>Panel Eğimi:</strong> {user_meta['tilt']}°<br>
                    <strong>Azimut:</strong> {user_meta['azimuth']}°<br>
                    <strong>Performans Oranı:</strong> {user_meta['pr']}%<br>
                    <strong>Veri Kolonu:</strong> {safe(col_u)}
                </div>
                <div class="hw-card">
                    <strong>Panel:</strong> {safe(HARDWARE_SPECS['panel'])}<br>
                    <strong>İnverter:</strong> {safe(HARDWARE_SPECS['inverter'])}
                </div>
                """,
                unsafe_allow_html=True,
            )

        with right:
            section_header("🔌 İnverter Durumu")
            current_prod = float(df.loc[snap, col_u])
            capacity_factor = current_prod / kwp * 100 if kwp else 0
            producer_fee_1 = tariff.get("producer_distribution_fee_lu1_tl")
            producer_fee_2 = tariff.get("producer_distribution_fee_lu2_tl")
            fee_text = "Veri yok"
            if producer_fee_1 is not None or producer_fee_2 is not None:
                parts = []
                if producer_fee_1 is not None:
                    parts.append(f"LÜ1: {producer_fee_1:.4f} ₺/kWh")
                if producer_fee_2 is not None:
                    parts.append(f"LÜ2: {producer_fee_2:.4f} ₺/kWh")
                fee_text = " | ".join(parts)
            st.markdown(
                f"""
                <div class="hw-card">
                    <strong>İnverter Modeli:</strong> Huawei SUN2000-100KTL-M2<br>
                    <strong>Nominal AC Çıkış:</strong> 100 kW<br>
                    <strong>MPPT Aralığı:</strong> 200–1000 V<br>
                    <strong>Soğutma:</strong> Akıllı fan + doğal konveksiyon<br>
                    <strong>Anlık Üretim:</strong> {current_prod:.2f} kWh<br>
                    <strong>Anlık Kapasite Kullanımı:</strong> {capacity_factor:.1f}%<br>
                    <strong>Veriş Yönlü Dağıtım Bedeli:</strong> {safe(fee_text)}
                </div>
                """,
                unsafe_allow_html=True,
            )


def admin_page(df: pd.DataFrame, price_col: str, prosumer_users: dict[str, dict], grid_price_tl: float) -> None:
    st.markdown(
        """
        <div style="font-size:1.55rem;font-weight:950;color:#145a32;margin-bottom:14px;">
        🛡️ Admin Paneli — Tüm Yerleşke Özeti
        </div>
        """,
        unsafe_allow_html=True,
    )

    total_u = float(df["Toplam_Uretim"].sum()) / 1_000_000
    total_t = float(df["Toplam_Tuketim"].sum()) / 1_000_000
    p2p_avg = float(df[price_col].mean())
    saving = float((grid_price_tl - p2p_avg) * df["Toplam_Tuketim"].sum())

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Toplam Üretim", f"{total_u:.2f}", "GWh / Yıl", RENK_URETIM)
    with c2:
        kpi_card("Toplam Tüketim", f"{total_t:.2f}", "GWh / Yıl", RENK_TUKETIM)
    with c3:
        kpi_card("P2P Ortalama", f"{p2p_avg:.3f}", "₺/kWh", RENK_MAVI)
    with c4:
        kpi_card("Teorik Maliyet Avantajı", format_money(saving), "Tam şebeke referansına göre", RENK_MOR)

    section_header("🏭 Prosümer Üretim Özeti")
    rows = []
    for meta in prosumer_users.values():
        col_u = meta["col_u"]
        col_t = meta["col_t"]
        u = float(df[col_u].sum())
        t = float(df[col_t].sum())
        sales = prosumer_sales_split(df, col_u, col_t)
        rows.append({
            "Bina": meta["ad"],
            "Kurulu Güç (kWp)": meta["kwp"],
            "PR (%)": meta["pr"],
            "Üretim (MWh)": round(u / 1000, 2),
            "Tüketim (MWh)": round(t / 1000, 2),
            "Kooperatife Satılan (MWh)": round(float(sales["Kooperatife_Satilan"].sum()) / 1000, 2),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    section_header("📊 Tüm Yerleşke Arz-Talep Dengesi")
    st.plotly_chart(chart_monthly_campus_balance(df), use_container_width=True)

# ─────────────────────────────────────────────
# UYGULAMA AKIŞI
# ─────────────────────────────────────────────
try:
    df = load_data()
    tariff = load_epdk_tariff()
except Exception as exc:
    st.error("Veri dosyaları yüklenirken hata oluştu.")
    st.exception(exc)
    st.stop()

price_col = get_price_col(df)
grid_price_tl = float(tariff["consumer_grid_price_tl"])
snap = snapshot_timestamp(df)
prosumer_users, consumer_users = build_user_maps(df)

sidebar_login(prosumer_users, consumer_users)
status_and_ticker(df, price_col, snap, grid_price_tl)

rol = st.session_state.get("rol")
kullanici = st.session_state.get("kullanici")

if rol is None:
    public_page(df, price_col, snap, grid_price_tl)
elif rol == "consumer" and kullanici in consumer_users:
    consumer_page(df, price_col, consumer_users[kullanici], snap, tariff)
elif rol == "prosumer" and kullanici in prosumer_users:
    prosumer_page(df, price_col, prosumer_users[kullanici], snap, tariff)
elif rol == "admin":
    admin_page(df, price_col, prosumer_users, grid_price_tl)
else:
    st.error("Oturum bilgisi geçersiz. Lütfen çıkış yapıp tekrar giriş yapın.")
