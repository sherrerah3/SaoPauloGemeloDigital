"""Eje territorial: capas Distrito y Subprefeitura de GeoSampa y tabla de equivalencias.

Se descargan por el servicio WFS de GeoSampa (no hace falta bajarlas a mano).
Salidas:
  data/lago/geo/distritos.gpkg, subprefeituras.gpkg   (EPSG:31983, para medir)
  data/lago/geo/distritos.geojson, subprefeituras.geojson (EPSG:4326)
  data/lago/territorio_equivalencias.csv
"""
import geopandas as gpd

from comun import leer_capa_geosampa, normalizar_nombre
from config import CRS_TRABAJO, CRS_WEB, EQUIVALENCIAS, LAGO_GEO


def main():
    LAGO_GEO.mkdir(parents=True, exist_ok=True)
    dist = leer_capa_geosampa("geoportal:distrito_municipal", "geosampa_distritos")
    sub = leer_capa_geosampa("geoportal:subprefeitura", "geosampa_subprefeituras")

    distritos = gpd.GeoDataFrame({
        "codigo_distrito": dist["cd_distrito_municipal"].astype(str).str.zfill(2),
        "nombre": dist["nm_distrito_municipal"],
        "sigla": dist["sg_distrito_municipal"],
        "codigo_subprefeitura": dist["cd_identificador_subprefeitura"].map(
            # El distrito trae el id interno de la subprefeitura; se publica el código oficial.
            dict(zip(sub["cd_identificador_subprefeitura"], sub["cd_subprefeitura"].astype(str).str.zfill(2)))
        ),
        "area_km2": dist.geometry.area / 1e6,
    }, geometry=dist.geometry, crs=CRS_TRABAJO)

    subprefeituras = gpd.GeoDataFrame({
        "codigo_subprefeitura": sub["cd_subprefeitura"].astype(str).str.zfill(2),
        "nombre": sub["nm_subprefeitura"],
        "sigla": sub["sg_subprefeitura"],
        "area_km2": sub.geometry.area / 1e6,
    }, geometry=sub.geometry, crs=CRS_TRABAJO)

    eq = distritos.drop(columns="geometry").merge(
        subprefeituras[["codigo_subprefeitura", "nombre"]].rename(columns={"nombre": "subprefeitura"}),
        on="codigo_subprefeitura", how="left",
    )
    if eq["subprefeitura"].isna().any():
        raise ValueError("Hay distritos cuyo código de subprefeitura no está en la capa Subprefeitura")
    eq["nombre_normalizado"] = eq["nombre"].map(normalizar_nombre)
    eq["subprefeitura_normalizada"] = eq["subprefeitura"].map(normalizar_nombre)
    eq = eq.rename(columns={"nombre": "nombre_oficial"})[[
        "codigo_distrito", "nombre_oficial", "nombre_normalizado", "sigla",
        "codigo_subprefeitura", "subprefeitura", "subprefeitura_normalizada", "area_km2",
    ]].sort_values("codigo_distrito")
    if eq["nombre_normalizado"].duplicated().any():
        raise ValueError("Dos distritos quedan con el mismo nombre normalizado")
    eq.to_csv(EQUIVALENCIAS, index=False)

    for nombre, gdf in (("distritos", distritos), ("subprefeituras", subprefeituras)):
        gdf.to_file(LAGO_GEO / f"{nombre}.gpkg", driver="GPKG")
        gdf.to_crs(CRS_WEB).to_file(LAGO_GEO / f"{nombre}.geojson", driver="GeoJSON")
    print(f"  {len(distritos)} distritos, {len(subprefeituras)} subprefeituras")
    print(f"  lago/territorio_equivalencias.csv: {len(eq)} filas")


if __name__ == "__main__":
    main()
