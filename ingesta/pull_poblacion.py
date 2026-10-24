"""Población: F41 densidad 2022 por sector censal (GeoSampa).

Pendiente en este script: F01 (población histórica) y F08 (estimación IBGE 2021).

Salida: data/lago/geo/densidad_sectores.geojson (EPSG:31983).
El codigo_distrito sale de los dígitos 8 y 9 del código del sector; verificar.py
comprueba que coincide con el distrito que contiene al sector.
"""

import geopandas as gpd

from comun import como_texto_codigo, guardar_lago_geo, leer_capa_geosampa


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


def main():
    guardar_lago_geo(densidad(), "densidad_sectores")


if __name__ == "__main__":
    main()
