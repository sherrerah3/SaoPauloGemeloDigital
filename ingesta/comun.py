"""Reglas de limpieza compartidas (sección 5 del plan).

Cada regla sale de la columna «Transformación» del Diccionario. Se implementan una
sola vez aquí y todos los scripts pull_*.py las usan.
"""

from __future__ import annotations

import datetime as dt
import re
import time
from pathlib import Path
from urllib.parse import urlencode

import geopandas as gpd
import pandas as pd
import requests
from unidecode import unidecode

from config import CRS_TRABAJO, EQUIVALENCIAS, GEOSAMPA_WFS, LAGO, LAGO_GEO, RAW, USER_AGENT

VACIOS = {"", "-", "–", "...", "…", "NI", "nan", "None"}


# --- Descarga ---------------------------------------------------------------


def descargar(
    url: str, nombre: str, extension: str, forzar: bool = False, subcarpeta: str | None = None, pausa_s: float = 0
) -> Path:
    """Guarda el crudo en data/raw/[subcarpeta/]AAAA-MM-DD_<nombre>.<ext>.

    Si ya hay un crudo con ese nombre (de cualquier fecha) se reutiliza el más
    reciente, salvo que forzar=True. pausa_s espera antes de pedir (para servidores
    que limitan la frecuencia, como el de la Prefeitura con F05).
    """
    carpeta = RAW / subcarpeta if subcarpeta else RAW
    carpeta.mkdir(parents=True, exist_ok=True)
    existentes = sorted(carpeta.glob(f"*_{nombre}.{extension}"))
    if existentes and not forzar:
        return existentes[-1]
    destino = carpeta / f"{dt.date.today().isoformat()}_{nombre}.{extension}"
    time.sleep(pausa_s)
    for intento in range(6):
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=600)
        if r.status_code not in (429, 502, 503, 504):
            break
        espera = int(r.headers.get("Retry-After", 0) or 0) or 15 * 2**intento
        print(f"  {r.status_code} en {url}; reintento en {espera} s")
        time.sleep(espera)
    r.raise_for_status()
    if r.headers.get("content-type", "").startswith("text/html"):
        raise RuntimeError(f"{url} devolvió HTML en lugar del archivo")
    destino.write_bytes(r.content)
    return destino


def url_wfs(capa: str) -> str:
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": capa,
        "outputFormat": "application/json",
    }
    return f"{GEOSAMPA_WFS}?{urlencode(params)}"


def leer_capa_geosampa(capa: str, nombre_raw: str) -> gpd.GeoDataFrame:
    """Descarga una capa por WFS (o reutiliza el crudo), comprueba EPSG:31983 y repara el texto."""
    ruta = descargar(url_wfs(capa), nombre_raw, "geojson")
    gdf = gpd.read_file(ruta)
    if gdf.empty:
        # Sin features GeoSampa no manda el CRS; se borra el crudo para no reutilizar un archivo vacío.
        ruta.unlink()
        raise ValueError(
            f"{capa}: GeoSampa devolvió la capa vacía. Es un problema del servidor: reintenta más tarde "
            "o baja la copia de los crudos con `python ingesta/crudos.py descargar`."
        )
    if gdf.crs is None or gdf.crs.to_epsg() != 31983:
        raise ValueError(f"{capa}: se esperaba EPSG:31983 y llegó {gdf.crs}")
    for col in gdf.columns.drop("geometry"):
        if pd.api.types.is_string_dtype(gdf[col]):
            gdf[col] = gdf[col].map(reparar_codificacion).map(limpiar_espacios)
    return gdf


def leer_excel(ruta: Path, **kwargs) -> pd.DataFrame:
    """Lee XLS antiguo con xlrd y XLSX con openpyxl, mirando los bytes y no la extensión."""
    cabecera = ruta.read_bytes()[:8]
    if cabecera.startswith(b"PK"):
        motor = "openpyxl"
    elif cabecera.startswith(b"\xd0\xcf\x11\xe0"):
        motor = "xlrd"
    else:
        raise ValueError(f"{ruta.name} no parece un Excel")
    return pd.read_excel(ruta, engine=motor, header=None, dtype=str, **kwargs)


# --- Valores ----------------------------------------------------------------


def es_vacio(valor) -> bool:
    return valor is None or (isinstance(valor, float) and pd.isna(valor)) or str(valor).strip() in VACIOS


def a_numero(valor, vacio_como_cero: bool = False) -> float | None:
    """«1.234,5» → 1234.5; «-», «...», «NI» → vacío (o 0 si la fuente lo indica, como F21)."""
    if es_vacio(valor):
        return 0.0 if vacio_como_cero else None
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip().replace(" ", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", texto):
        texto = texto.replace(".", "")
    return float(texto)


def columna_numerica(serie: pd.Series, vacio_como_cero: bool = False) -> pd.Series:
    return serie.map(lambda v: a_numero(v, vacio_como_cero)).astype("Float64")


def limpiar_anio(valor) -> int:
    """Quita marcas de nota pegadas al año: «2019²» → 2019."""
    m = re.search(r"(1[89]|20)\d{2}", str(valor))
    if not m:
        raise ValueError(f"No hay año en {valor!r}")
    return int(m.group(0))


def como_texto_codigo(valor, digitos: int | None = None) -> str | None:
    """Códigos con ceros iniciales (CEP, escuelas, sectores) se guardan como texto."""
    if es_vacio(valor):
        return None
    texto = str(valor).strip()
    if re.fullmatch(r"\d+\.0", texto):
        texto = texto[:-2]
    return texto.zfill(digitos) if digitos else texto


# --- Texto ------------------------------------------------------------------


def reparar_codificacion(texto):
    """Texto de GeoSampa leído con la codificación equivocada («SÃƒO» → «SÃO»)."""
    if not isinstance(texto, str) or not re.search(r"[ÃÂ]", texto):
        return texto
    try:
        return texto.encode("latin1").decode("utf8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return texto


def limpiar_espacios(texto):
    if not isinstance(texto, str):
        return texto
    return re.sub(r"\s+", " ", texto).strip()


def quitar_prefijo_subprefeitura(texto: str) -> str:
    return re.sub(r"^\s*subprefeitura\s+", "", texto, flags=re.IGNORECASE).strip()


def normalizar_nombre(texto: str) -> str:
    """Llave de unión por texto: sin acentos, minúsculas, sin signos ni espacios sobrantes.

    «Moóca» → «mooca», «M'Boi Mirim» → «m boi mirim», «Aricanduva/Formosa/Carrão» →
    «aricanduva formosa carrao».
    """
    texto = unidecode(quitar_prefijo_subprefeitura(str(texto))).lower()
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return texto.strip()


# Nombres viejos o cortos de subprefeitura que usan las tablas de Infocidade → nombre
# normalizado de la capa de GeoSampa. Agregar aquí cada caso nuevo, nunca en el script.
ALIAS_SUBPREFEITURA = {
    "casa verde cachoeirinha": "casa verde limao cachoeirinha",
    "perus": "perus anhanguera",
    "pirituba": "pirituba jaragua",
    "sao miguel paulista": "sao miguel",
    # Nombres de las «Prefeituras Regionais» del IDHM (F07).
    "aricanduva vila formosa": "aricanduva formosa carrao",
    "casa verde": "casa verde limao cachoeirinha",
    "freguesia do o brasilandia": "freguesia brasilandia",
}


def normalizar_subprefeitura(texto: str) -> str:
    clave = normalizar_nombre(texto)
    return ALIAS_SUBPREFEITURA.get(clave, clave)


# --- Tablas de Infocidade ---------------------------------------------------

ESPECIALES = {
    "msp": "municipio",
    "pmsp": "municipio",
    "total": "municipio",
    "invalidos": "invalidos",
    "nao localizados": "no_localizados",
    "sem localizacao": "sin_ubicacion",
}


def nivel_de_fila(nombre_original: str) -> str:
    clave = normalizar_nombre(nombre_original)
    if clave in ESPECIALES:
        return ESPECIALES[clave]
    if nombre_original.strip().lower().startswith("subprefeitura"):
        return "subprefeitura"
    return "distrito"


def leer_tabla_unidades(ruta: Path, hoja=0) -> pd.DataFrame:
    """Lee las tablas «Unidades Territoriais» de Infocidade (MSP, subprefeituras, distritos).

    Devuelve una fila por unidad con las columnas de la fuente, más:
    unidad_territorial (sin prefijo), nivel y subprefeitura (la del bloque en que va la fila).
    Descarta títulos, notas y la fila vacía del final.
    """
    crudo = leer_excel(ruta, sheet_name=hoja)
    primera = crudo[0].fillna("").astype(str).str.strip()
    inicio = primera[primera.str.lower() == "unidades territoriais"].index
    if inicio.empty:
        raise ValueError(f"{ruta.name}: no se encontró el encabezado «Unidades Territoriais»")
    fila_enc = inicio[0]
    encabezado = [
        limpiar_espacios(str(v)) if not es_vacio(v) else f"col{i}" for i, v in enumerate(crudo.iloc[fila_enc])
    ]
    cuerpo = crudo.iloc[fila_enc + 1 :].copy()
    cuerpo.columns = encabezado
    nombres = cuerpo[encabezado[0]].fillna("").astype(str)
    fin = nombres[nombres.str.strip() == ""].index
    if len(fin):
        cuerpo = cuerpo.loc[: fin[0] - 1]
    cuerpo = cuerpo.rename(columns={encabezado[0]: "original"})
    cuerpo["original"] = cuerpo["original"].map(limpiar_espacios)
    cuerpo["nivel"] = cuerpo["original"].map(nivel_de_fila)
    cuerpo["unidad_territorial"] = cuerpo["original"].map(quitar_prefijo_subprefeitura)

    subpref_actual = None
    padres = []
    for nivel, nombre in zip(cuerpo["nivel"], cuerpo["unidad_territorial"], strict=True):
        if nivel == "subprefeitura":
            subpref_actual = nombre
        padres.append(subpref_actual if nivel in ("subprefeitura", "distrito") else None)
    cuerpo["subprefeitura"] = padres
    return cuerpo.reset_index(drop=True)


def ancho_a_largo(df: pd.DataFrame, id_cols: list[str], var: str, valor: str) -> pd.DataFrame:
    """Año (u otra categoría) como encabezado de columna → una fila por año."""
    largo = df.melt(id_vars=id_cols, var_name=var, value_name=valor)
    return largo


# --- Territorio -------------------------------------------------------------


def cargar_equivalencias() -> pd.DataFrame:
    if not EQUIVALENCIAS.exists():
        raise FileNotFoundError("Falta la tabla de equivalencias: corre pull_territorio.py primero")
    return pd.read_csv(EQUIVALENCIAS, dtype=str)


def unir_distritos(df: pd.DataFrame, columna: str = "unidad_territorial") -> pd.DataFrame:
    """Agrega codigo_distrito a las filas de nivel distrito. Falla si alguna no encuentra pareja."""
    eq = cargar_equivalencias()[["codigo_distrito", "nombre_normalizado"]]
    df = df.copy()
    df["_clave"] = df[columna].map(normalizar_nombre)
    df = df.merge(eq, how="left", left_on="_clave", right_on="nombre_normalizado")
    huerfanas = df[(df["nivel"] == "distrito") & df["codigo_distrito"].isna()][columna].unique()
    if len(huerfanas):
        raise ValueError(f"Distritos sin pareja en la tabla de equivalencias: {sorted(huerfanas)}")
    return df.drop(columns=["_clave", "nombre_normalizado"])


def unir_subprefeituras(df: pd.DataFrame, columna: str = "unidad_territorial") -> pd.DataFrame:
    eq = cargar_equivalencias()[["codigo_subprefeitura", "subprefeitura_normalizada"]].drop_duplicates()
    df = df.copy()
    df["_clave"] = df[columna].map(normalizar_subprefeitura)
    df = df.merge(eq, how="left", left_on="_clave", right_on="subprefeitura_normalizada")
    huerfanas = df[(df["nivel"] == "subprefeitura") & df["codigo_subprefeitura"].isna()][columna].unique()
    if len(huerfanas):
        raise ValueError(f"Subprefeituras sin pareja en la tabla de equivalencias: {sorted(huerfanas)}")
    return df.drop(columns=["_clave", "subprefeitura_normalizada"])


# --- Salida -----------------------------------------------------------------


def guardar_lago_geo(gdf: gpd.GeoDataFrame, nombre: str) -> Path:
    """Capas del lago: GeoJSON en EPSG:31983, igual que las entrega GeoSampa, para medir en metros."""
    LAGO_GEO.mkdir(parents=True, exist_ok=True)
    ruta = LAGO_GEO / f"{nombre}.geojson"
    gdf.to_crs(CRS_TRABAJO).to_file(ruta, driver="GeoJSON")
    print(f"  lago/geo/{nombre}.geojson: {len(gdf):,} elementos")
    return ruta


def guardar_lago(df: pd.DataFrame, nombre: str) -> Path:
    LAGO.mkdir(parents=True, exist_ok=True)
    ruta = LAGO / nombre
    df.to_csv(ruta, index=False, encoding="utf-8")
    print(f"  lago/{nombre}: {len(df):,} filas")
    return ruta
