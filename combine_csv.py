import pandas as pd
from pathlib import Path
from ftfy import fix_text

data_dir = Path("data")

files = [
    data_dir / "September_October.csv",
    data_dir / "October_November.csv",
    data_dir / "November_December.csv",
    data_dir / "December_January.csv",
]

print("Archivos a combinar:")
for f in files:
    print("-", f)

def read_csv_robust(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        try:
            return pd.read_csv(path, encoding="utf-8")
        except UnicodeDecodeError:
            return pd.read_csv(path, encoding="latin1")

def parse_published_at(series: pd.Series) -> pd.Series:
    s = pd.to_datetime(series, errors="coerce")
    # fallback dayfirst si demasiados NaT
    if s.isna().mean() > 0.20:
        s2 = pd.to_datetime(series, errors="coerce", dayfirst=True)
        if s2.isna().mean() < s.isna().mean():
            return s2
    return s

dfs = []
for f in files:
    if not f.exists():
        raise FileNotFoundError(f"No existe: {f}")
    df = read_csv_robust(f)
    df["__source_file"] = f.name
    dfs.append(df)

combined = pd.concat(dfs, ignore_index=True)

# Normaliza columnas
combined.columns = [c.strip() for c in combined.columns]

# Dedup por URL (o fallback si no existe)
dedup_key = None
for candidate in ["url", "document_identifier", "id", "source_url"]:
    if candidate in combined.columns:
        dedup_key = candidate
        break
if dedup_key is None:
    raise ValueError("No encuentro columna para deduplicar (url/document_identifier/id/source_url).")

before = len(combined)
combined = combined.drop_duplicates(subset=[dedup_key]).reset_index(drop=True)
after = len(combined)
print(f"\nDeduplicación por '{dedup_key}': {before} -> {after} (eliminados {before-after})")

# published_at + date
if "published_at" in combined.columns:
    combined["published_at"] = parse_published_at(combined["published_at"])
    combined["date"] = combined["published_at"].dt.date

# Limpieza texto
for col in ["title", "plain_text"]:
    if col in combined.columns:
        combined[col] = combined[col].astype(str).apply(fix_text)

# Métricas por día
print("\nTotal filas finales:", len(combined))
if "date" in combined.columns:
    daily_counts = combined.groupby("date").size().sort_index()
    print("\nArtículos por día (primeros 15):")
    print(daily_counts.head(15))
    print("\nArtículos por día (últimos 15):")
    print(daily_counts.tail(15))
    print("\nMedia por día:", round(daily_counts.mean(), 2))

# Guardar
output_path = data_dir / "spain_4blocks_combined_fixed.csv"
combined.to_csv(output_path, index=False, encoding="utf-8-sig")
print("\nGuardado como:", output_path)