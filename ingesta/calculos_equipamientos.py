"""P1 (equipamientos) y Gente (favelas): conteos por distrito.

Los puntos de GeoSampa se asignan al distrito que los contiene; las tablas de Infocidade
(F21, F22) ya vienen por distrito. Todo se mide en EPSG:31983.
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from calculos_p1 import DERIVADOS, capa
from comun import unir_distritos
from config import LAGO, LAGO_GEO


def distritos() -> gpd.GeoDataFrame:
    return gpd.read_file(LAGO_GEO / "distritos.gpkg")[["codigo_distrito", "area_km2", "geometry"]]


def contar_puntos(nombre: str, columna: str, dist: gpd.GeoDataFrame) -> pd.Series:
    j = gpd.sjoin(capa(nombre), dist, predicate="within", how="inner")
    return j.groupby("codigo_distrito")[columna].nunique()


def ultimo_anio(df: pd.DataFrame) -> int:
    return int(df["anio"].max())


def equipamientos_por_distrito() -> tuple[pd.DataFrame, dict]:
    """Una fila por distrito (y MSP) y las vigencias de las tablas de Infocidade."""
    dist = distritos()
    res = dist.drop(columns="geometry").set_index("codigo_distrito")
    poblacion = capa("densidad_sectores").groupby("codigo_distrito")["poblacion"].sum()

    res["escuelas_infantil"] = contar_puntos("escuelas_infantil", "codigo_equipamento", dist)
    res["escuelas_basica"] = contar_puntos("escuelas_basica", "codigo_equipamento", dist)
    res["centros_deportivos"] = contar_puntos("centros_deportivos", "id_equipamiento", dist)
    res["estadios"] = contar_puntos("estadios", "id_equipamiento", dist)

    ferias = pd.read_csv(LAGO / "ferias_mercados.csv")
    anio_ferias = ultimo_anio(ferias)
    ferias = unir_distritos(ferias[(ferias.anio == anio_ferias) & (ferias.nivel == "distrito")])
    por_tipo = ferias.pivot_table(index="codigo_distrito", columns="tipo_equipamiento", values="cantidad")
    res["ferias"] = por_tipo["feira_livre"]
    res["mercados"] = por_tipo["mercado"] + por_tipo["sacolao"]

    shoppings = pd.read_csv(LAGO / "shoppings.csv")
    anio_shoppings = ultimo_anio(shoppings)
    shoppings = unir_distritos(shoppings[shoppings.anio == anio_shoppings].assign(nivel="distrito"), "distrito")
    res["shoppings"] = shoppings.groupby("codigo_distrito")["id_shopping"].nunique()
    res["abl_shoppings_m2"] = shoppings.groupby("codigo_distrito")["abl_m2"].sum()

    res["poblacion"] = poblacion
    res = res.fillna(0)
    total = res.sum()
    res.loc["MSP"] = total
    por_10mil = res["poblacion"] / 10_000
    for columna in ("escuelas_infantil", "escuelas_basica", "ferias"):
        res[f"{columna}_por_10mil"] = res[columna] / por_10mil

    DERIVADOS.mkdir(parents=True, exist_ok=True)
    res.round(4).to_csv(DERIVADOS / "equipamientos_distrito.csv")
    return res, {"F21": str(anio_ferias), "F22": str(anio_shoppings)}


def favelas_por_distrito() -> pd.DataFrame:
    """Favelas (F32) por distrito. Un polígono que cruza un límite se reparte por área."""
    dist = distritos()
    sectores = capa("densidad_sectores")
    fav = capa("favelas")[["id_favela", "domicilios", "geometry"]]
    fav["area_total"] = fav.area
    partes = gpd.overlay(fav, dist, how="intersection", keep_geom_type=True)
    partes["fraccion"] = partes.area / partes["area_total"]
    partes["domicilios_parte"] = partes["domicilios"].fillna(0) * partes["fraccion"]
    partes["area_parte_km2"] = partes.area / 1e6

    res = dist.drop(columns="geometry").set_index("codigo_distrito")
    # Cada favela cuenta en el distrito donde está la mayor parte de su área.
    principal = partes.sort_values("fraccion").drop_duplicates("id_favela", keep="last")
    res["favelas"] = principal.groupby("codigo_distrito")["id_favela"].nunique()
    res["domicilios_favela"] = partes.groupby("codigo_distrito")["domicilios_parte"].sum()
    res["area_favela_km2"] = partes.groupby("codigo_distrito")["area_parte_km2"].sum()
    res["domicilios"] = sectores.groupby("codigo_distrito")["domicilios"].sum()
    res = res.fillna(0)
    res.loc["MSP"] = res.sum()
    res["domicilios_favela_pct"] = 100 * res["domicilios_favela"] / res["domicilios"]
    res["area_favela_pct"] = 100 * res["area_favela_km2"] / res["area_km2"]

    res.round(4).to_csv(DERIVADOS / "favelas_distrito.csv")
    return res


if __name__ == "__main__":
    print(equipamientos_por_distrito()[0].loc["MSP"])
    print(favelas_por_distrito().loc["MSP"])
