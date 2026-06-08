# backend.py

from pathlib import Path
from typing import Iterable, Optional, Union
import warnings

import pandas as pd
import streamlit as st


PathLike = Union[str, Path]


# ---------------------------------------------------------------------
# Dosya bulma yardımcıları
# ---------------------------------------------------------------------
def _module_dir() -> Path:
    """backend.py dosyasının bulunduğu klasörü güvenli şekilde döndürür."""
    try:
        return Path(__file__).resolve().parent
    except NameError:
        return Path.cwd()


def _unique_paths(paths: Iterable[Path]) -> list[Path]:
    """Tekrarlı path adaylarını temizler."""
    seen = set()
    result = []

    for path in paths:
        key = str(path)
        if key not in seen:
            seen.add(key)
            result.append(path)

    return result


def _resolve_path(
    primary_name: PathLike,
    fallback_names: Optional[list[PathLike]] = None,
    data_dir: PathLike = ".",
) -> Path:
    """
    Dosyayı proje kökü, backend.py klasörü ve data/ klasörü içinde arar.

    Örnek:
        P2P_Borsa_Sonuclari_2.csv bulunamazsa P2P_Borsa_Sonuclari.csv denenir.
    """
    fallback_names = fallback_names or []

    names = [Path(primary_name), *[Path(name) for name in fallback_names]]

    base_dirs = _unique_paths(
        [
            Path(data_dir),
            Path.cwd(),
            _module_dir(),
            Path(data_dir) / "data",
            Path.cwd() / "data",
            _module_dir() / "data",
        ]
    )

    checked_paths: list[Path] = []

    for name in names:
        if name.is_absolute():
            checked_paths.append(name)
            if name.exists():
                return name.resolve()
            continue

        for base_dir in base_dirs:
            candidate = base_dir / name
            checked_paths.append(candidate)

            if candidate.exists():
                return candidate.resolve()

    checked_text = "\n".join(f" - {path}" for path in checked_paths)
    raise FileNotFoundError(
        f"Dosya bulunamadı: {primary_name}\n"
        f"Kontrol edilen yollar:\n{checked_text}"
    )


def _file_signature(paths: list[Path]) -> tuple[tuple[str, int, int], ...]:
    """
    Streamlit cache'in dosya değişince otomatik yenilenmesi için
    dosya boyutu ve son değişiklik zamanını cache anahtarına ekler.
    """
    return tuple(
        (str(path.resolve()), path.stat().st_size, path.stat().st_mtime_ns)
        for path in paths
    )


# ---------------------------------------------------------------------
# Veri temizleme ve senkronizasyon yardımcıları
# ---------------------------------------------------------------------
def _clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Kolon adlarındaki gereksiz boşlukları temizler."""
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]
    return df


def _drop_auto_index_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    CSV/Excel kaynaklı boş veya otomatik oluşmuş 'Unnamed' indeks kolonlarını temizler.
    Veri içeren anlamlı kolonlara dokunmaz.
    """
    df = df.copy()

    columns_to_drop = []

    for col in df.columns:
        col_name = str(col)

        if not col_name.startswith("Unnamed"):
            continue

        series = df[col]

        if series.isna().all():
            columns_to_drop.append(col)
            continue

        numeric_series = pd.to_numeric(series, errors="coerce")
        expected_range = pd.Series(range(len(df)), index=df.index, dtype="float64")

        if numeric_series.notna().all() and numeric_series.astype("float64").equals(expected_range):
            columns_to_drop.append(col)

    if columns_to_drop:
        df = df.drop(columns=columns_to_drop)

    return df


def _standardize_datetime_index(
    df: pd.DataFrame,
    source_name: str,
    datetime_col: str = "Tarih_Saat",
    drop_hour_column: bool = True,
) -> pd.DataFrame:
    """
    Tarih_Saat kolonunu temiz DatetimeIndex'e çevirir.

    Not:
        Excel kaynaklı 22:59:59.998 gibi milisaniye sapmaları saatlik indekse
        zarar vermemesi için en yakın saate yuvarlanır.
    """
    df = _clean_column_names(df)

    if datetime_col not in df.columns:
        raise ValueError(f"{source_name}: '{datetime_col}' kolonu bulunamadı.")

    timestamps = pd.to_datetime(df[datetime_col], errors="coerce")

    if timestamps.isna().any():
        bad_count = int(timestamps.isna().sum())
        raise ValueError(
            f"{source_name}: '{datetime_col}' içinde parse edilemeyen {bad_count} satır var."
        )

    timestamps = timestamps.dt.round("h")

    df = df.drop(columns=[datetime_col])

    if drop_hour_column and "Saat" in df.columns:
        df = df.drop(columns=["Saat"])

    df.index = pd.DatetimeIndex(timestamps, name=datetime_col)
    df = df.sort_index()

    if not df.index.is_unique:
        duplicated_values = df.index[df.index.duplicated()].unique()[:5]
        raise ValueError(
            f"{source_name}: '{datetime_col}' indeksinde tekrar eden zaman damgaları var. "
            f"İlk örnekler: {list(duplicated_values)}"
        )

    return df


def _validate_hourly_index(
    index: pd.DatetimeIndex,
    source_name: str,
    expected_rows: Optional[int] = 8760,
) -> None:
    """
    İndeksin eksiksiz, sıralı ve saatlik olduğunu doğrular.
    """
    if expected_rows is not None and len(index) != expected_rows:
        raise ValueError(
            f"{source_name}: Beklenen satır sayısı {expected_rows}, gelen satır sayısı {len(index)}."
        )

    if len(index) == 0:
        raise ValueError(f"{source_name}: Tarih_Saat indeksi boş.")

    expected_index = pd.date_range(
        start=index[0],
        periods=len(index),
        freq="h",
        name=index.name,
    )

    if not index.equals(expected_index):
        missing_count = len(expected_index.difference(index))
        extra_count = len(index.difference(expected_index))

        raise ValueError(
            f"{source_name}: Tarih_Saat indeksi kesintisiz saatlik seri değil. "
            f"Eksik zaman sayısı: {missing_count}, fazla/uyumsuz zaman sayısı: {extra_count}."
        )


def _optimize_memory(df: pd.DataFrame) -> pd.DataFrame:
    """
    Dashboard performansı için sayısal kolonları daha küçük dtype'lara indirger.
    """
    df = df.copy()

    float_cols = df.select_dtypes(include=["float64"]).columns
    int_cols = df.select_dtypes(include=["int64", "int32"]).columns

    for col in float_cols:
        df[col] = pd.to_numeric(df[col], downcast="float")

    for col in int_cols:
        df[col] = pd.to_numeric(df[col], downcast="integer")

    return df


def _read_consumption(path: Path, sheet_name: str) -> pd.DataFrame:
    """Tüketim Excel dosyasını okur ve Tarih_Saat indeksine alır."""
    df = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")
    df = _standardize_datetime_index(
        df=df,
        source_name="Tuketim_Verileri",
        datetime_col="Tarih_Saat",
        drop_hour_column=True,
    )
    _validate_hourly_index(df.index, source_name="Tuketim_Verileri")
    return df


def _read_production(path: Path, sheet_name: str) -> pd.DataFrame:
    """Üretim Excel dosyasını okur ve Tarih_Saat indeksine alır."""
    df = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")
    df = _standardize_datetime_index(
        df=df,
        source_name="Uretim_Verileri",
        datetime_col="Tarih_Saat",
        drop_hour_column=True,
    )
    _validate_hourly_index(df.index, source_name="Uretim_Verileri")
    return df


def _read_p2p_results(
    path: Path,
    master_index: pd.DatetimeIndex,
    allow_single_extra_tail_row: bool = True,
) -> pd.DataFrame:
    """
    P2P CSV dosyasını okur ve tüketim/üretim dosyalarından gelen ana Tarih_Saat
    indeksiyle birebir hizalar.

    P2P CSV içinde Tarih_Saat olmadığı için hizalama pozisyon bazlı yapılır.
    Bu nedenle satır sayısı kontrolü kritik önemdedir.
    """
    df = pd.read_csv(path, low_memory=False)
    df = _clean_column_names(df)
    df = _drop_auto_index_columns(df)

    if "Tarih_Saat" in df.columns:
        df = _standardize_datetime_index(
            df=df,
            source_name="P2P_Borsa_Sonuclari",
            datetime_col="Tarih_Saat",
            drop_hour_column=True,
        )

        if not df.index.equals(master_index):
            df = df.reindex(master_index)

            if df.isna().any().any():
                raise ValueError(
                    "P2P_Borsa_Sonuclari: Tarih_Saat kolonuyla hizalama yapıldı ancak "
                    "ana indeksle eşleşmeyen satırlar bulundu."
                )

        return df

    master_len = len(master_index)
    p2p_len = len(df)

    if p2p_len == master_len:
        aligned_df = df.copy()

    elif p2p_len == master_len + 1 and allow_single_extra_tail_row:
        warnings.warn(
            "P2P_Borsa_Sonuclari CSV dosyasında 8760 yerine 8761 satır bulundu. "
            "Tarih_Saat kolonu olmadığı için zaman kayması oluşmaması adına yalnızca "
            "sondaki tek fazla satır kontrollü olarak kırpıldı.",
            UserWarning,
        )
        aligned_df = df.iloc[:master_len].copy()

    else:
        raise ValueError(
            "P2P_Borsa_Sonuclari: Satır sayısı ana Tarih_Saat indeksiyle uyumsuz. "
            f"P2P satır sayısı: {p2p_len}, beklenen satır sayısı: {master_len}. "
            "Bu durumda otomatik eşleştirme yapılmadı; veri kayması riski var."
        )

    aligned_df.index = master_index.copy()
    aligned_df.index.name = "Tarih_Saat"

    return aligned_df


def _validate_column_collisions(*dataframes: pd.DataFrame) -> None:
    """Birleştirme öncesi çakışan kolon adlarını kontrol eder."""
    seen_columns = set()

    for df in dataframes:
        current_columns = set(df.columns)
        collision_columns = seen_columns.intersection(current_columns)

        if collision_columns:
            raise ValueError(
                "Birleştirme sırasında çakışan kolon adları bulundu: "
                f"{sorted(collision_columns)}"
            )

        seen_columns.update(current_columns)


# ---------------------------------------------------------------------
# Cache'li ana yükleme fonksiyonu
# ---------------------------------------------------------------------
def load_data(
    data_dir: PathLike = ".",
    p2p_file: PathLike = "P2P_Borsa_Sonuclari_2.csv",
    tuketim_file: PathLike = "Tuketim_Verileri_2.xlsx",
    uretim_file: PathLike = "Uretim_Verileri.xlsx",
    tuketim_sheet: str = "Veriler",
    uretim_sheet: str = "Sayfa1",
) -> pd.DataFrame:
    """
    Streamlit arayüzü için tüketim, üretim ve P2P borsa sonuçlarını tek,
    temiz ve senkronize DataFrame olarak döndürür.

    Dönen DataFrame:
        - Index: Tarih_Saat
        - Satır sayısı: 8760
        - Tüketim + üretim + P2P kolonları aynı saat ekseninde hizalıdır.
    """
    p2p_path = _resolve_path(
        primary_name=p2p_file,
        fallback_names=["P2P_Borsa_Sonuclari.csv"],
        data_dir=data_dir,
    )

    tuketim_path = _resolve_path(
        primary_name=tuketim_file,
        fallback_names=["Tuketim_Verileri.xlsx"],
        data_dir=data_dir,
    )

    uretim_path = _resolve_path(
        primary_name=uretim_file,
        fallback_names=[],
        data_dir=data_dir,
    )

    source_paths = [p2p_path, tuketim_path, uretim_path]

    return _load_data_cached(
        p2p_path=str(p2p_path),
        tuketim_path=str(tuketim_path),
        uretim_path=str(uretim_path),
        tuketim_sheet=tuketim_sheet,
        uretim_sheet=uretim_sheet,
        file_signature=_file_signature(source_paths),
    )


@st.cache_data(show_spinner="Veri setleri yükleniyor ve senkronize ediliyor...")
def _load_data_cached(
    p2p_path: str,
    tuketim_path: str,
    uretim_path: str,
    tuketim_sheet: str,
    uretim_sheet: str,
    file_signature: tuple[tuple[str, int, int], ...],
) -> pd.DataFrame:
    """
    Asıl cache'lenen veri yükleme katmanı.

    file_signature parametresi doğrudan kullanılmaz; dosya boyutu veya son
    değiştirilme zamanı değişirse Streamlit cache otomatik yenilensin diye
    cache anahtarına dahil edilir.
    """
    _ = file_signature

    tuketim_df = _read_consumption(
        path=Path(tuketim_path),
        sheet_name=tuketim_sheet,
    )

    uretim_df = _read_production(
        path=Path(uretim_path),
        sheet_name=uretim_sheet,
    )

    if not tuketim_df.index.equals(uretim_df.index):
        raise ValueError(
            "Tüketim ve üretim dosyalarının Tarih_Saat indeksleri birebir aynı değil. "
            "Zaman kayması riski nedeniyle birleştirme durduruldu."
        )

    p2p_df = _read_p2p_results(
        path=Path(p2p_path),
        master_index=tuketim_df.index,
        allow_single_extra_tail_row=True,
    )

    _validate_column_collisions(tuketim_df, uretim_df, p2p_df)

    combined_df = pd.concat(
        [tuketim_df, uretim_df, p2p_df],
        axis=1,
        join="inner",
        copy=False,
    )

    combined_df.index.name = "Tarih_Saat"

    if len(combined_df) != 8760:
        raise ValueError(
            f"Birleşik DataFrame satır sayısı 8760 olmalıydı; gelen satır sayısı: {len(combined_df)}."
        )

    if not combined_df.index.equals(tuketim_df.index):
        raise ValueError(
            "Birleşik DataFrame indeksi ana Tarih_Saat indeksiyle uyuşmuyor."
        )

    if combined_df.columns.duplicated().any():
        duplicated_cols = combined_df.columns[combined_df.columns.duplicated()].tolist()
        raise ValueError(f"Birleşik DataFrame içinde tekrar eden kolonlar var: {duplicated_cols}")

    combined_df = _optimize_memory(combined_df)

    combined_df.insert(0, "Saat", combined_df.index.strftime("%H:%M"))

    return combined_df


# ---------------------------------------------------------------------
# Lokal test
# ---------------------------------------------------------------------
if __name__ == "__main__":
    df = load_data()

    print("\n--- Birleşik DataFrame Bilgisi ---")
    df.info(memory_usage="deep")

    print("\n--- İlk 5 Satır ---")
    print(df.head())