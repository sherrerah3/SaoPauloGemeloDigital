"""Movilidad (P1): líneas y paradas de bus, tren, metro y estaciones (GeoSampa), y pasajeros (F05).

Salidas en data/lago/geo/ (EPSG:31983): buses, paradas, tren, metro, estaciones.
Salida tabular: data/lago/sptrans_pasajeros.csv (una fila por línea y mes).

F05 se publica como un archivo por día y también como consolidados mensuales. La fuente
principal es la suma de los días (solo meses completos); el consolidado solo llena un mes al
que le falta algún día, y solo si el mes de su nombre coincide con el de su encabezado.
"""

from __future__ import annotations

import calendar
import re
import sys

import geopandas as gpd
import pandas as pd
import requests

from comun import a_numero, descargar, guardar_lago, guardar_lago_geo, leer_capa_geosampa, leer_excel, normalizar_nombre
from config import USER_AGENT

OPERADORES = {"METRO": "Metrô", "VIAQUATRO": "ViaQuatro", "VIAMOBILIDADE": "ViaMobilidade", "CPTM": "CPTM"}


# --- Capas (F29, F30, F31, F35, F36) ---------------------------------------


def hora(valor) -> str | None:
    """«1970-01-01T06:20:00Z» → «06:20:00». GeoSampa guarda la hora como fecha de 1970."""
    m = re.search(r"(\d{2}:\d{2}:\d{2})", str(valor))
    return m.group(1) if m else None


def buses() -> gpd.GeoDataFrame:
    g = leer_capa_geosampa("geoportal:linha_onibus", "geosampa_linha_onibus")
    return gpd.GeoDataFrame(
        {
            "codigo_linea": g["cd_linha_geometria"].astype(str),
            "nombre_recorrido": g["nm_linha_onibus_geometria"],
            "sentido": g["sentido_linha_onibus"],
            "hora_primera_salida": g["ho_primeira_viagem"].map(hora),
            "hora_ultima_salida": g["ho_ultima_viagem"].map(hora),
            "operador": g["nm_empresa_metro_trem"],
        },
        geometry=g.geometry,
        crs=g.crs,
    )


def paradas() -> gpd.GeoDataFrame:
    g = leer_capa_geosampa("geoportal:ponto_onibus", "geosampa_ponto_onibus")
    return gpd.GeoDataFrame(
        {
            "codigo_parada": g["cd_identificador_ponto_onibus"].astype(str),
            "calle_numero": g["nm_ponto_onibus"],
            "referencia_cruce": g["tx_endereco_ponto_onibus"],
        },
        geometry=g.geometry,
        crs=g.crs,
    )


def tren() -> gpd.GeoDataFrame:
    g = leer_capa_geosampa("geoportal:linha_trem", "geosampa_linha_trem")
    return gpd.GeoDataFrame(
        {
            "codigo_linea": g["cd_identificador_linha"].astype(int),
            "nombre_linea": g["nm_linha_metro_trem"],
            "operador": g["nm_empresa_metro_trem"].map(lambda v: OPERADORES.get(v, v)),
        },
        geometry=g.geometry,
        crs=g.crs,
    )


def metro() -> gpd.GeoDataFrame:
    g = leer_capa_geosampa("geoportal:linha_metro", "geosampa_linha_metro")
    return gpd.GeoDataFrame(
        {
            "codigo_linea": g["cd_identificador_linha"].astype(int),
            "nombre_linea": g["nm_linha_metro_trem"].replace({"LILAS": "LILÁS"}),
            "operador": g["nm_empresa_metro_trem"].map(lambda v: OPERADORES.get(v, v)),
            "modo": "metro",
        },
        geometry=g.geometry,
        crs=g.crs,
    )


def estaciones() -> gpd.GeoDataFrame:
    g = leer_capa_geosampa("geoportal:estacao_metro", "geosampa_estacao_metro")
    return gpd.GeoDataFrame(
        {
            "id_estacion": g["cd_identificador"].astype(int),
            "nombre_estacion": g["nm_estacao_metro_trem"],
            "codigo_linea": g["cd_identificador_linha"].astype(int),
            "situacion": g["tx_situacao_metro_trem"],
        },
        geometry=g.geometry,
        crs=g.crs,
    )


# --- Pasajeros (F05) --------------------------------------------------------

PAGINAS_F05 = {
    2025: "https://capital.sp.gov.br/web/mobilidade/w/passageiros-transportados-2025",
    2026: "https://capital.sp.gov.br/web/mobilidade/w/passageiros-transportados-2026",
}
BASE_DOCUMENTOS = "https://capital.sp.gov.br"

# Encabezado normalizado de la fuente → campo del lago.
COLUMNAS_F05 = {
    "data": "fecha",
    "grupo": "grupo",
    "linha": "linha",
    "passageiros pagantes": "pasajeros_pagantes",
    "passageiros int onibus onibus": "pasajeros_integracion",
    "passageiros com gratuidade": "gratuidad",
    "passageiros com gratuidade est": "gratuidad_est",
    "tot passageiros transportados": "pasajeros_total",
}


MESES_PT = {
    "JAN": 1,
    "FEV": 2,
    "MAR": 3,
    "ABR": 4,
    "MAI": 5,
    "JUN": 6,
    "JUL": 7,
    "AGO": 8,
    "SET": 9,
    "OUT": 10,
    "NOV": 11,
    "DEZ": 12,
}
SUMAS = ("pasajeros_pagantes", "pasajeros_integracion", "pasajeros_gratuidad", "pasajeros_total")
MESES_NOMBRE = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}


def nombre_columna(valor) -> str:
    """Encabezados de F05 a una forma común: los consolidados viejos (ene-jun 2025) agregan
    « SUM» y traen «Ônibus» dañado como «¿Nibus»."""
    nombre = re.sub(r" sum$", "", normalizar_nombre(str(valor)))
    return nombre.replace("int nibus nibus", "int onibus onibus")


def enlaces_f05() -> list[str]:
    enlaces = []
    for anio, pagina in PAGINAS_F05.items():
        html = requests.get(pagina, headers={"User-Agent": USER_AGENT}, timeout=60).text
        propios = sorted(set(re.findall(r'href="(/documents/d/mobilidade/[^"]*\d{4}[^"]*)"', html)))
        propios = [e for e in propios if str(anio) in e]
        consolidados = sum("consolidado" in e for e in propios)
        print(f"  F05 {anio}: {len(propios) - consolidados} reportes diarios y {consolidados} consolidados mensuales")
        enlaces += propios
    return enlaces


def bajar(enlace: str):
    slug = enlace.rsplit("/", 1)[-1]
    extension = "xlsx" if slug.endswith("xlsx") else "xls"
    return descargar(BASE_DOCUMENTOS + enlace, slug, extension, subcarpeta="f05", pausa_s=1)


def leer_reporte(ruta) -> pd.DataFrame:
    """Lee un reporte diario («Data: '01-OUT-2025'») o un consolidado mensual («Periodo : ...»).

    Los diarios traen la columna Data; los consolidados no, y el mes sale del encabezado.
    """
    crudo = leer_excel(ruta)
    primera = crudo[0].fillna("").astype(str).map(normalizar_nombre)
    fila = primera[primera.isin(["data", "grupo"])].index[0]
    tabla = crudo.iloc[fila + 1 :].copy()
    tabla.columns = [nombre_columna(v) for v in crudo.iloc[fila]]
    tabla = tabla[[c for c in COLUMNAS_F05 if c in tabla.columns]].rename(columns=COLUMNAS_F05)
    tabla = tabla[tabla["linha"].notna()].copy()
    for col in ("pasajeros_pagantes", "pasajeros_integracion", "gratuidad", "gratuidad_est", "pasajeros_total"):
        tabla[col] = tabla[col].map(a_numero)

    if "fecha" in tabla.columns:
        # «2025-10-01 00:00:00» en los XLSX, «01/03/2025» en los XLS.
        texto = tabla["fecha"].astype(str)
        con_barra = pd.to_datetime(texto, format="%d/%m/%Y", errors="coerce")
        tabla["fecha"] = con_barra.fillna(pd.to_datetime(texto, errors="coerce")).dt.date
        tabla["consolidado"] = False
    else:
        # El mes sale del nombre del archivo («consolidado-julho-2025») y, en los nuevos, también
        # del encabezado («Periodo : '01-DEZ-2025'»). Si no coinciden, el archivo no es confiable
        # (pasa con «consolidado-agosto-2025», que dice ser de agosto de 2024).
        mes_txt, anio = re.search(r"(" + "|".join(MESES_NOMBRE) + r")-(\d{4})", ruta.name).groups()
        fecha = pd.Timestamp(int(anio), MESES_NOMBRE[mes_txt], 1)
        titulo = " ".join(crudo.iloc[:fila].fillna("").astype(str).values.ravel()).upper()
        periodo = re.search(r"(\d{2})-([A-Z]{3})-(\d{4})", titulo)
        if periodo and (int(periodo.group(3)), MESES_PT[periodo.group(2)]) != (fecha.year, fecha.month):
            raise ValueError(f"el nombre dice {fecha:%Y-%m} y el encabezado {periodo.group(0)}")
        tabla["fecha"] = fecha.date()
        tabla["consolidado"] = True
    tabla["archivo"] = ruta.name
    return tabla


def mensual_por_linea(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.sort_values("fecha")
        .groupby(["anio", "mes", "codigo_linea"], as_index=False)
        .agg(nombre_linea=("nombre_linea", "last"), grupo=("grupo", "last"), **{c: (c, "sum") for c in SUMAS})
    )


def pasajeros() -> pd.DataFrame:
    # De a uno: el servidor responde 429 si se le piden varios a la vez.
    rutas = [bajar(e) for e in enlaces_f05()]
    reportes = []
    for ruta in rutas:
        try:
            reportes.append(leer_reporte(ruta))
        except Exception as e:  # un archivo dañado no debe tumbar el mes; se reporta
            print(f"  aviso: no se pudo leer {ruta.name}: {e}", file=sys.stderr)
    df = pd.concat(reportes, ignore_index=True)

    # «609110 - VARGEM GRANDE/TERM STO AMARO» → código y nombre.
    partes = df["linha"].astype(str).str.extract(r"^\s*([^\s]+)\s*-\s*(.*)$")
    df["codigo_linea"] = partes[0].fillna(df["linha"].astype(str).str.strip())
    df["nombre_linea"] = partes[1].fillna("").str.strip()
    df["pasajeros_gratuidad"] = df["gratuidad"].fillna(0) + df["gratuidad_est"].fillna(0)
    df["anio"] = pd.to_datetime(df["fecha"]).dt.year
    df["mes"] = pd.to_datetime(df["fecha"]).dt.month

    # Consolidados: el total mensual de SPTrans. Si un mes tiene varias versiones, la última.
    cons = df[df["consolidado"]]
    ultima = cons.groupby(["anio", "mes"])["archivo"].transform("max")
    cons = mensual_por_linea(cons[cons["archivo"] == ultima])

    # Diarios: la misma fecha puede venir en dos archivos («-1», «-2»); se deja una sola.
    dias = df[~df["consolidado"]].drop_duplicates(["fecha", "grupo", "linha"], keep="last")
    dias_por_mes = dias.groupby(["anio", "mes"])["fecha"].nunique()
    completos = {(a, m) for (a, m), n in dias_por_mes.items() if n == calendar.monthrange(a, m)[1]}
    diario = mensual_por_linea(dias[dias.set_index(["anio", "mes"]).index.isin(completos)])

    # Regla: la suma de los reportes diarios es la fuente principal (se puede contar cuántos días
    # tiene cada mes). El consolidado solo cubre meses a los que les falta algún día. Los
    # consolidados no siempre son confiables: el de mayo de 2025 trae un tercio menos que sus días.
    t_cons = cons.groupby(["anio", "mes"])["pasajeros_total"].sum()
    t_dia = diario.groupby(["anio", "mes"])["pasajeros_total"].sum()
    for a, m in t_cons.index.intersection(t_dia.index):
        dif = (t_cons[(a, m)] - t_dia[(a, m)]) / t_dia[(a, m)]
        if abs(dif) > 0.05:
            print(f"  aviso F05 {a}-{m:02d}: el consolidado difiere {dif:+.1%} de la suma diaria; se usa la diaria")
    for (a, m), n in dias_por_mes.items():
        if (a, m) in completos:
            continue
        fuente = "se usa el consolidado" if (a, m) in t_cons.index else "sin consolidado, se excluye"
        print(f"  F05 {a}-{m:02d}: {n} de {calendar.monthrange(a, m)[1]} días; {fuente}")

    faltantes = cons[
        ~cons.set_index(["anio", "mes"]).index.isin(completos)
        & cons.set_index(["anio", "mes"]).index.isin(dias_por_mes.index)
    ]
    mensual = pd.concat([diario, faltantes], ignore_index=True).sort_values(["anio", "mes", "codigo_linea"])
    for col in SUMAS:
        mensual[col] = mensual[col].round().astype("Int64")
    return mensual


def main():
    capas = {"buses": buses(), "paradas": paradas(), "tren": tren(), "metro": metro(), "estaciones": estaciones()}
    for nombre, gdf in capas.items():
        guardar_lago_geo(gdf, nombre)

    if "--sin-pasajeros" not in sys.argv:
        mensual = pasajeros()
        guardar_lago(mensual, "sptrans_pasajeros.csv")
        # Unión con F29: el código de F05 es el de F29 sin guion («1012-10» → «101210»).
        codigos_f29 = set(capas["buses"]["codigo_linea"].str.replace("-", "", regex=False))
        cruza = mensual["codigo_linea"].isin(codigos_f29)
        print(
            f"  F05 → F29: cruzan {cruza.mean():.1%} de las filas y "
            f"{mensual.loc[cruza, 'pasajeros_total'].sum() / mensual['pasajeros_total'].sum():.1%} de los pasajeros"
        )


if __name__ == "__main__":
    main()
