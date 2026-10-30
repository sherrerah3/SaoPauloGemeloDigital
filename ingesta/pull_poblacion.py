"""Población y vivienda: F41 densidad 2022 por sector censal (GeoSampa), F28 área construida
residencial del municipio 1995-2025, F01 población histórica 1872-2022, F07 IDH municipal
2000 y 2010 y F18-F20 nacimientos 2023-2025 (Infocidade).

Pendiente en este script: F08 (estimación IBGE 2021; la API de servicodados.ibge.gov.br no
respondía al probarla).

Salidas:
  data/lago/geo/densidad_sectores.geojson (EPSG:31983)
  data/lago/area_construida_residencial.csv: anio, area_residencial_m2
  data/lago/poblacion_historica.csv: anio, poblacion_brasil, poblacion_estado_sp, poblacion_rm_sp,
      poblacion_municipio_sp
  data/lago/idhm.csv: anio, prefeitura_regional, idhm, idhm_renda
  data/lago/nacimientos_tipo_parto.csv: anio, unidad_territorial, nivel, tipo_parto, nacidos_vivos
      (tipo_parto es Sensible: el archivo no se sube al repositorio)
El codigo_distrito sale de los dígitos 8 y 9 del código del sector; verificar.py
comprueba que coincide con el distrito que contiene al sector.
"""

import geopandas as gpd
import pandas as pd

from comun import (
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
    unir_distritos,
)

URL_F28 = "https://prefeitura.sp.gov.br/documents/d/licenciamento/area_construida_residencial_1995_2025-1-"
URL_F01 = (
    "https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/chamadas/"
    "312_censo_br-rm-uf-msp_pop-abs_1872-2022_final_1715804989.xlsx"
)
URL_F07 = (
    "https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/urbanismo/infocidade/tabelas/"
    "7_Indice_de_desenvolvimento_humano_municip_2000_10962.xls"
)
# fuente → (URL, año, extensión del archivo). El año también está en el título de cada tabla y se compara.
NACIMIENTOS = {
    "F18": (
        "https://prefeitura.sp.gov.br/documents/d/licenciamento/tabela-nascidos-vivos-e-tipo-de-parto-2025-1",
        2025,
        "xlsx",
    ),
    "F19": ("https://prefeitura.sp.gov.br/documents/d/licenciamento/nascidos-vivos-e-tipo-de-parto-2024", 2024, "xls"),
    "F20": (
        "https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/"
        "tabela%20nascidos%20vivos%20tipo%20de%20parto%202023.xlsx",
        2023,
        "xlsx",
    ),
}
TIPOS_PARTO = {"Vaginal": "vaginal", "Cesário": "cesarea", "Ignorado": "ignorado"}
# Las dos formas en que la fuente nombra a los nacimientos sin distrito.
SIN_UBICACION = {"endereco ignorado", "nao localizado"}


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


def poblacion_historica() -> pd.DataFrame:
    """F01: población de cada censo en Brasil, el Estado, la Región Metropolitana y el municipio.

    Antes de 1980 la RM no tiene cifra («-» en la fuente, pasa a vacío): se creó en 1973.
    """
    crudo = leer_excel(descargar(URL_F01, "f01_poblacion_historica", "xlsx"))
    inicio = crudo.index[crudo[0].fillna("").str.strip() == "Ano"][0]
    tabla = crudo.iloc[inicio + 1 :, :5]
    # Solo las filas cuyo primer dato es un año solo: así se descartan las notas («2022: Censo…»).
    tabla = tabla[tabla[0].fillna("").str.fullmatch(r"\s*\d{4}\s*")]
    lago = pd.DataFrame(
        {
            "anio": tabla[0].map(limpiar_anio),
            "poblacion_brasil": columna_numerica(tabla[1]).astype("Int64"),
            "poblacion_estado_sp": columna_numerica(tabla[2]).astype("Int64"),
            "poblacion_rm_sp": columna_numerica(tabla[3]).astype("Int64"),
            "poblacion_municipio_sp": columna_numerica(tabla[4]).astype("Int64"),
        }
    )
    return lago.sort_values("anio").reset_index(drop=True)


def decimal_con_punto(valor) -> float | None:
    """Los índices de F07 vienen con punto decimal («0.733»), no con coma ni con punto de miles.

    No sirve comun.a_numero: ve «0.733» como el número 733 con punto de miles.
    """
    if es_vacio(valor):
        return None
    numero = float(str(valor).strip())
    if not 0 <= numero <= 1:
        raise ValueError(f"Un índice del IDHM debe estar entre 0 y 1, y llegó {valor!r}")
    return numero


def idhm() -> pd.DataFrame:
    """F07: IDHM total y de renta por Prefeitura Regional (equivale a la subprefeitura) y la fila «MSP».

    La hoja tiene dos años en bloques de cuatro columnas (IDHM, Renda, Longevidad, Educación). Solo se guardan
    IDHM e IDHM Renda, que son los campos del Diccionario.
    """
    crudo = leer_excel(descargar(URL_F07, "f07_idhm", "xls"))
    fila_enc = crudo.index[crudo[0].fillna("").str.strip() == "Prefeituras Regionais"][0]
    # El año solo está en la primera columna de su bloque: se arrastra a las demás.
    anios = crudo.iloc[fila_enc].ffill()
    indices = crudo.iloc[fila_enc + 1].fillna("").str.strip()
    cuerpo = crudo.iloc[fila_enc + 2 :]
    vacias = cuerpo[cuerpo[0].fillna("").str.strip() == ""].index
    if len(vacias):
        cuerpo = cuerpo.loc[: vacias[0] - 1]

    partes = []
    for col in range(1, crudo.shape[1]):
        if indices[col] != "IDHM":
            continue
        # La columna siguiente del mismo bloque es «IDHM Renda».
        if indices[col + 1] != "IDHM Renda":
            raise ValueError(f"F07: se esperaba «IDHM Renda» junto a la columna {col}, hay {indices[col + 1]!r}")
        partes.append(
            pd.DataFrame(
                {
                    "anio": limpiar_anio(anios[col]),
                    "prefeitura_regional": cuerpo[0].map(limpiar_espacios),
                    "idhm": cuerpo[col].map(decimal_con_punto),
                    "idhm_renda": cuerpo[col + 1].map(decimal_con_punto),
                }
            )
        )
    lago = pd.concat(partes, ignore_index=True).sort_values(["anio", "prefeitura_regional"])
    return lago.reset_index(drop=True)


def niveles_de_nacimientos(nombres: list[str]) -> list[str]:
    """El nivel de cada fila de F18-F20, por posición: no hay prefijo que lo diga.

    La tabla empieza con «MSP», sigue con cada subprefeitura y, debajo, sus distritos, y termina con los
    nacimientos sin distrito. Una subprefeitura y su distrito pueden llamarse igual («Butantã», «Mooca»),
    así que se cuenta cuántos distritos tiene cada subprefeitura en la tabla de equivalencias.
    """
    eq = cargar_equivalencias()
    distritos_por_subprefeitura = eq.groupby("subprefeitura_normalizada").size().to_dict()
    if normalizar_nombre(nombres[0]) != "msp":
        raise ValueError(f"Nacimientos: la primera fila debía ser MSP y es {nombres[0]!r}")
    niveles = ["municipio"]
    i = 1
    while i < len(nombres):
        nombre = nombres[i]
        if normalizar_nombre(nombre) in SIN_UBICACION:
            niveles.append("sin_ubicacion")
            i += 1
            continue
        clave = normalizar_subprefeitura(nombre)
        if clave not in distritos_por_subprefeitura:
            raise ValueError(f"Nacimientos: se esperaba una subprefeitura en la fila {i} y llegó {nombre!r}")
        cuantos = distritos_por_subprefeitura[clave]
        niveles += ["subprefeitura", *["distrito"] * cuantos]
        i += 1 + cuantos
    if len(niveles) != len(nombres):
        raise ValueError("Nacimientos: la tabla termina a mitad de una subprefeitura")
    return niveles


def leer_nacimientos(fuente: str, url: str, anio: int, extension: str) -> pd.DataFrame:
    crudo = leer_excel(descargar(url, f"{fuente.lower()}_nacimientos_{anio}", extension))
    anio_titulo = limpiar_anio(crudo.iloc[2, 0])
    if anio_titulo != anio:
        raise ValueError(f"{fuente}: se esperaba el año {anio} y el título dice {anio_titulo}")
    inicio = crudo.index[crudo[0].fillna("").str.strip() == "Unidades Territoriais"][0]
    # Dos filas de encabezado (Tipo de Parto; Vaginal, Cesário, Ignorado, Total); las notas finales no tienen cifras.
    cuerpo = crudo.iloc[inicio + 2 :, :5]
    cuerpo = cuerpo[cuerpo[4].notna()].reset_index(drop=True)
    encabezado = crudo.iloc[inicio + 1, 1:5].fillna("").str.strip().tolist()
    if encabezado != [*TIPOS_PARTO, "Total"]:
        raise ValueError(f"{fuente}: columnas inesperadas {encabezado}")

    nombres = cuerpo[0].map(limpiar_espacios).str.replace("Moóca", "Mooca").tolist()
    niveles = niveles_de_nacimientos(nombres)
    cifras = cuerpo.iloc[:, 1:5].apply(columna_numerica).astype("Int64")
    if not (cifras.iloc[:, :3].sum(axis=1) == cifras.iloc[:, 3]).all():
        raise ValueError(f"{fuente}: en alguna fila los tres tipos de parto no suman el total")

    base = pd.DataFrame({"anio": anio, "unidad_territorial": nombres, "nivel": niveles})
    largo = [
        base.assign(tipo_parto=tipo, nacidos_vivos=cifras.iloc[:, k].to_numpy())
        for k, tipo in enumerate(TIPOS_PARTO.values())
    ]
    return pd.concat(largo, ignore_index=True)


def nacimientos() -> pd.DataFrame:
    lago = pd.concat([leer_nacimientos(f, *datos) for f, datos in NACIMIENTOS.items()], ignore_index=True)
    # Todo distrito debe encontrar su código; si no, falla aquí y no en la web.
    unir_distritos(lago.drop_duplicates(["unidad_territorial", "nivel"]))
    lago["nacidos_vivos"] = lago["nacidos_vivos"].astype("Int64")
    return lago.sort_values(["anio", "nivel", "unidad_territorial", "tipo_parto"]).reset_index(drop=True)


def main():
    guardar_lago_geo(densidad(), "densidad_sectores")
    guardar_lago(area_construida(), "area_construida_residencial.csv")
    guardar_lago(poblacion_historica(), "poblacion_historica.csv")
    guardar_lago(idhm(), "idhm.csv")
    guardar_lago(nacimientos(), "nacimientos_tipo_parto.csv")


if __name__ == "__main__":
    main()
