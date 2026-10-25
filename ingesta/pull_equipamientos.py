"""Equipamientos (P1) y favelas: tablas de Infocidade y capas de GeoSampa.

Salidas en data/lago/:
  ferias_mercados.csv   F21: anio, unidad_territorial, nivel, tipo_equipamiento, cantidad
  shoppings.csv         F22-F24: anio, id_shopping, nombre, subprefeitura, distrito, abl_m2, tiendas,
                        fecha_inauguracion
Salidas en data/lago/geo/ (EPSG:31983):
  centros_deportivos (F33), estadios (F34), escuelas_infantil (F39), escuelas_basica (F40)
  favelas (F32; trae nombre y ubicación, que son Sensibles: no se sube al repo)
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from comun import (
    a_numero,
    cargar_equivalencias,
    columna_numerica,
    como_texto_codigo,
    descargar,
    es_vacio,
    guardar_lago,
    guardar_lago_geo,
    leer_capa_geosampa,
    leer_excel,
    limpiar_anio,
    limpiar_espacios,
    normalizar_nombre,
    normalizar_subprefeitura,
    reparar_codificacion,
    unir_distritos,
)

URL_INFOCIDADE = "https://prefeitura.sp.gov.br/documents/d/licenciamento/"
URL_INFOCIDADE_ANTIGUA = "https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/"

URL_F21 = f"{URL_INFOCIDADE}feiras_livres_mercados_e_sacoloes_munici_2003_2025"
TIPOS_F21 = {"Feiras": "feira_livre", "Mercados": "mercado", "Sacolões": "sacolao"}

SHOPPINGS = {
    "F22": (f"{URL_INFOCIDADE}shoppings-sp-2025_tabela-1-", "xlsx"),
    "F23": (f"{URL_INFOCIDADE_ANTIGUA}16_shopping_centers__localizacao_2021.xls", "xls"),
    "F24": (f"{URL_INFOCIDADE_ANTIGUA}16_shopping_centers__localizacao_2017.xls", "xls"),
}


# --- F21: ferias, mercados y sacolões por distrito ---------------------------


def ferias_mercados() -> pd.DataFrame:
    """La tabla trae subprefeituras y distritos sin prefijo, y algunos se llaman igual (Butantã).

    El nivel se deduce del orden: cada subprefeitura va seguida de todos sus distritos.
    """
    crudo = leer_excel(descargar(URL_F21, "f21_ferias_mercados", "xlsx"))
    fila_anios = crudo.index[crudo[0].fillna("").str.strip() == "Unidades Territoriais"][0]
    anios = crudo.iloc[fila_anios].ffill()
    tipos = crudo.iloc[fila_anios + 1]

    eq = cargar_equivalencias()
    distritos_de = eq.groupby("subprefeitura_normalizada")["nombre_normalizado"].apply(set).to_dict()

    filas = []
    pendientes: set[str] = set()
    for _, fila in crudo.iloc[fila_anios + 2 :].iterrows():
        nombre = fila[0]
        if es_vacio(nombre) or str(nombre).startswith(("Fonte", "Elabora", "Nota")):
            continue
        nombre = limpiar_espacios(str(nombre))
        if normalizar_nombre(nombre) == "msp":
            nivel = "municipio"
        elif not pendientes:
            nivel = "subprefeitura"
            pendientes = set(distritos_de[normalizar_subprefeitura(nombre)])
        else:
            nivel = "distrito"
            pendientes.discard(normalizar_nombre(nombre))
        for col in crudo.columns[1:]:
            if es_vacio(anios[col]) or tipos[col] not in TIPOS_F21:
                continue
            filas.append(
                {
                    "anio": limpiar_anio(anios[col]),
                    "unidad_territorial": nombre,
                    "nivel": nivel,
                    "tipo_equipamiento": TIPOS_F21[tipos[col]],
                    # El «-» de la fuente significa que no hay ninguno.
                    "cantidad": a_numero(fila[col], vacio_como_cero=True),
                }
            )
    df = pd.DataFrame(filas)
    df["cantidad"] = df["cantidad"].astype("Int64")
    return df


# --- F22-F24: shoppings -----------------------------------------------------


def columna(tabla: pd.DataFrame, empieza: str) -> pd.Series:
    """Las tablas de cada año nombran distinto la misma columna («ABL- Área…», «ABL (área…»)."""
    return tabla[next(c for c in tabla.columns if str(c).strip().lower().startswith(empieza.lower()))]


def fecha(valor) -> str | None:
    if es_vacio(valor):
        return None
    valor = str(valor).strip()
    dia_primero = "/" in valor  # 2017 viene como 28/03/2008; 2021 y 2025, como 2008-03-28
    f = pd.to_datetime(valor, dayfirst=dia_primero, errors="coerce")
    return None if pd.isna(f) else f.date().isoformat()


def shoppings() -> pd.DataFrame:
    partes = []
    for fuente, (url, extension) in SHOPPINGS.items():
        ruta = descargar(url, f"{fuente.lower()}_shoppings", extension)
        crudo = leer_excel(ruta)
        anio = limpiar_anio(crudo.iloc[2, 0])
        fila_enc = crudo.index[crudo[0].fillna("").str.strip() == "Nome"][0]
        tabla = crudo.iloc[fila_enc + 1 :].copy()
        tabla.columns = [limpiar_espacios(str(c)) for c in crudo.iloc[fila_enc]]
        tabla = tabla[tabla["Distrito"].notna() & tabla["Nome"].notna()]
        texto = lambda s: s.map(reparar_codificacion).map(limpiar_espacios)  # noqa: E731
        partes.append(
            pd.DataFrame(
                {
                    "anio": anio,
                    "nombre": texto(tabla["Nome"]),
                    "subprefeitura": texto(tabla["Subprefeitura"]),
                    "distrito": texto(tabla["Distrito"]),
                    "abl_m2": columna_numerica(columna(tabla, "ABL")),
                    "tiendas": columna_numerica(tabla["Lojas"]).astype("Int64"),
                    "fecha_inauguracion": columna(tabla, "Data de inaugura").map(fecha),
                }
            )
        )
    df = pd.concat(partes, ignore_index=True)
    # El mismo shopping entre años: por nombre normalizado (2021 viene en mayúsculas y sin tildes).
    df["id_shopping"] = df["nombre"].map(normalizar_nombre).str.replace(" ", "_")
    # 2021 trae filas repetidas (el Diccionario lo anota).
    df = df.drop_duplicates(["anio", "id_shopping"])
    # Prueba de unión: todo shopping cae en un distrito conocido (falla si no).
    unir_distritos(df.assign(nivel="distrito"), columna="distrito")
    return df[
        ["anio", "id_shopping", "nombre", "subprefeitura", "distrito", "abl_m2", "tiendas", "fecha_inauguracion"]
    ].sort_values(["anio", "id_shopping"])


# --- Capas de GeoSampa ------------------------------------------------------


def equipamientos(capa: str, nombre_raw: str) -> gpd.GeoDataFrame:
    """F33 y F34: el mismo esquema de equipamientos de GeoSampa."""
    g = leer_capa_geosampa(capa, nombre_raw)
    return gpd.GeoDataFrame(
        {
            "id_equipamiento": g["cd_identificador"].astype(int),
            "nombre": g["nm_equipamento"],
            "tipo": g["nm_tipo_equipamento"],
            "esfera_administrativa": g["nm_esfera_administrativa_equipamento"],
            "direccion": g["tx_endereco_equipamento"],
            "cep": g["cd_cep_equipamento"].map(como_texto_codigo),
        },
        geometry=g.geometry,
        crs=g.crs,
    )


def escuelas(capa: str, nombre_raw: str) -> gpd.GeoDataFrame:
    g = leer_capa_geosampa(capa, nombre_raw)
    return gpd.GeoDataFrame(
        {
            "codigo_equipamento": g["cd_equipamento"].map(como_texto_codigo),
            "nombre": g["nm_equipamento"],
            "direccion": g["tx_endereco_equipamento"],
            "barrio": g["nm_bairro_equipamento"],
            "cep": g["cd_cep_equipamento"].map(como_texto_codigo),
        },
        geometry=g.geometry,
        crs=g.crs,
    )


def favelas() -> gpd.GeoDataFrame:
    g = leer_capa_geosampa("geoportal:habita2geosampa_habi_favela2geosampa", "geosampa_favelas")
    return gpd.GeoDataFrame(
        {
            "id_favela": g["uuid_id"],
            # Sensibles: se quedan en el lago, build_web.py no los publica.
            "nombre": g["nome"],
            "ubicacion_texto": g["localizacao"],
            "propiedad_terreno": g["propriedade_area"],
            "domicilios": g["tot_domicilio"].astype("Int64"),
            "area_m2": g["areageo_m2"].astype(float),
            "anio_implantacion": g["anoimplant"].astype("Int64"),
        },
        geometry=g.geometry,
        crs=g.crs,
    )


def main():
    guardar_lago(ferias_mercados(), "ferias_mercados.csv")
    guardar_lago(shoppings(), "shoppings.csv")
    capas = {
        "centros_deportivos": equipamientos(
            "geoportal:equipamento_esporte_centro_esportivo", "geosampa_centros_esportivos"
        ),
        "estadios": equipamientos("geoportal:equipamento_esporte_estadios", "geosampa_estadios"),
        "escuelas_infantil": escuelas(
            "geoportal:equipamento_educacao_infantil_rede_publica", "geosampa_educacao_infantil"
        ),
        "escuelas_basica": escuelas("geoportal:equipamento_educacao_rede_publica", "geosampa_educacao_rede_publica"),
        "favelas": favelas(),
    }
    for nombre, gdf in capas.items():
        guardar_lago_geo(gdf, nombre)


if __name__ == "__main__":
    main()
