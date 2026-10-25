"""Población y vivienda: F41 densidad 2022 por sector censal (GeoSampa) y F28 área
construida residencial del municipio, 1995-2025 (Infocidade).

Pendiente en este script: F01 (población histórica) y F08 (estimación IBGE 2021; la API
de servicodados.ibge.gov.br no respondía al probarla).

Salidas:
  data/lago/geo/densidad_sectores.geojson (EPSG:31983)
  data/lago/area_construida_residencial.csv: anio, area_residencial_m2
El codigo_distrito sale de los dígitos 8 y 9 del código del sector; verificar.py
comprueba que coincide con el distrito que contiene al sector.
"""

import geopandas as gpd
import pandas as pd

from comun import (
    columna_numerica,
    como_texto_codigo,
    descargar,
    guardar_lago,
    guardar_lago_geo,
    leer_capa_geosampa,
    leer_excel,
    limpiar_anio,
)

URL_F28 = "https://prefeitura.sp.gov.br/documents/d/licenciamento/area_construida_residencial_1995_2025-1-"


def densidad() -> gpd.GeoDataFrame:
    g = leer_capa_geosampa("geoportal:densidade_demografica", "geosampa_densidade_demografica")
    codigo = g["cd_setor_censitario_densidade"].map(como_texto_codigo)
    if not codigo.str.fullmatch(r"3550308\d{8}").all():
        raise ValueError("Hay sectores cuyo código no es de 15 dígitos del municipio 3550308")
    return gpd.GeoDataFrame(
        {
            "codigo_sector": codigo,
            "codigo_distrito": codigo.str[7:9],
            "domicilios": g["qt_domicilio"].astype("Int64"),
            "poblacion": g["qt_populacao"].astype("Int64"),
            "area_m2": g["qt_area_setor_censitario"].astype(float),
            # Sensible: se queda en el lago, build_web.py no lo publica.
            "indice_vulnerabilidad": g["cd_indice_vulnerabilidade_social"].astype("Int64"),
        },
        geometry=g.geometry,
        crs=g.crs,
    )


def area_construida() -> pd.DataFrame:
    crudo = leer_excel(descargar(URL_F28, "f28_area_construida_residencial", "xlsx"))
    inicio = crudo.index[crudo[0].fillna("").str.strip() == "ANO"][0]
    tabla = crudo.iloc[inicio + 1 :, :2]
    tabla = tabla[tabla[0].fillna("").str.match(r"\s*(19|20)\d{2}")]
    # El AUMENTO (%) de la fuente no se guarda: se calcula del área.
    return pd.DataFrame(
        {
            "anio": tabla[0].map(limpiar_anio),
            "area_residencial_m2": columna_numerica(tabla[1]).astype("Int64"),
        }
    )


def main():
    guardar_lago_geo(densidad(), "densidad_sectores")
    guardar_lago(area_construida(), "area_construida_residencial.csv")


if __name__ == "__main__":
    main()
