"""Empleo formal (P2): F11 establecimientos y F12 empleos (2011-2024), F13-F15 por sexo
(2022-2024) y F16-F17 por raza o color (2023-2024).

Salidas en data/lago/, una fila por unidad territorial y año (y categoría, en raza):
  establecimientos_empleos.csv  anio, unidad_territorial, nivel, establecimientos_formales, empleos_formales
  empleo_sexo.csv               anio, unidad_territorial, nivel, empleos_masculino, empleos_femenino
  empleo_raza.csv               anio, unidad_territorial, nivel, raza_color, empleos (Sensible: no se sube al repo)
"""

import pandas as pd

from comun import (
    ancho_a_largo,
    columna_numerica,
    descargar,
    guardar_lago,
    leer_tabla_unidades,
    limpiar_anio,
    unir_distritos,
    unir_subprefeituras,
)

URL_INFOCIDADE = "https://prefeitura.sp.gov.br/documents/d/licenciamento/"

FUENTES = {
    "F11": (
        f"{URL_INFOCIDADE}2026-06-08_a_estabelecimentos_2011_2024-1-",
        "f11_establecimientos",
        "establecimientos_formales",
    ),
    "F12": (f"{URL_INFOCIDADE}2026-06-08_b_empregos_2011_2024-1-", "f12_empleos", "empleos_formales"),
}

# Una tabla por año; el año solo aparece en el título (fila 3 de la hoja).
SEXO = {
    "F13": f"{URL_INFOCIDADE}2026-06-08_10_empregos_sexo_2024-1-",
    "F14": f"{URL_INFOCIDADE}2026-02-12_10_empregos_sexo_2023-1",
    "F15": f"{URL_INFOCIDADE}2026-02-12_10_empregos_sexo_2022-1",
}
RAZA = {
    "F16": f"{URL_INFOCIDADE}2026-06-08_11_empregos_raca_2024",
    "F17": f"{URL_INFOCIDADE}2026-06-08_11_empregos_raca_2023-1-",
}
CATEGORIAS_RAZA = {
    "Amarela": "amarela",
    "Branca": "branca",
    "Indígena": "indigena",
    "Parda": "parda",
    "Preta": "preta",
    "Não identificada": "nao_identificada",
}
CLAVES = ["anio", "unidad_territorial", "nivel"]


def leer_serie_anual(url: str, nombre_raw: str, campo: str) -> pd.DataFrame:
    tabla = leer_tabla_unidades(descargar(url, nombre_raw, "xlsx"))
    columnas_anio = [c for c in tabla.columns if c[:4].isdigit()]
    largo = ancho_a_largo(
        tabla[["unidad_territorial", "nivel", *columnas_anio]], ["unidad_territorial", "nivel"], "anio", campo
    )
    largo["anio"] = largo["anio"].map(limpiar_anio)
    largo[campo] = columna_numerica(largo[campo]).astype("Int64")
    return largo


def leer_tabla_anio(url: str, nombre_raw: str) -> pd.DataFrame:
    """Tabla de un solo año: el año sale del título, porque las columnas son categorías."""
    ruta = descargar(url, nombre_raw, "xlsx")
    tabla = leer_tabla_unidades(ruta)
    tabla["anio"] = limpiar_anio(pd.read_excel(ruta, header=None, nrows=3).iloc[2, 0])
    return tabla


def empleo_sexo() -> pd.DataFrame:
    partes = []
    for fuente, url in SEXO.items():
        t = leer_tabla_anio(url, f"{fuente.lower()}_empleos_sexo")
        partes.append(
            pd.DataFrame(
                {
                    **{c: t[c] for c in CLAVES},
                    "empleos_masculino": columna_numerica(t["Masculino"]).astype("Int64"),
                    "empleos_femenino": columna_numerica(t["Feminino"]).astype("Int64"),
                }
            )
        )
    return pd.concat(partes, ignore_index=True)


def empleo_raza() -> pd.DataFrame:
    partes = []
    for fuente, url in RAZA.items():
        t = leer_tabla_anio(url, f"{fuente.lower()}_empleos_raza").rename(columns=CATEGORIAS_RAZA)
        largo = ancho_a_largo(t[[*CLAVES, *CATEGORIAS_RAZA.values()]], CLAVES, "raza_color", "empleos")
        largo["empleos"] = columna_numerica(largo["empleos"]).astype("Int64")
        partes.append(largo)
    return pd.concat(partes, ignore_index=True)


def comprobar_union(df: pd.DataFrame) -> None:
    """Todo distrito y subprefeitura debe encontrar su código (falla si no)."""
    unir_subprefeituras(unir_distritos(df.drop_duplicates(["unidad_territorial", "nivel"])))


def main():
    f11 = leer_serie_anual(*FUENTES["F11"])
    f12 = leer_serie_anual(*FUENTES["F12"])
    lago = f11.merge(f12, on=CLAVES, how="outer", validate="one_to_one")
    comprobar_union(lago)
    lago = lago.sort_values(["anio", "nivel", "unidad_territorial"])
    guardar_lago(lago[[*CLAVES, "establecimientos_formales", "empleos_formales"]], "establecimientos_empleos.csv")

    sexo = empleo_sexo()
    comprobar_union(sexo)
    guardar_lago(sexo.sort_values(["anio", "nivel", "unidad_territorial"]), "empleo_sexo.csv")

    raza = empleo_raza()
    comprobar_union(raza)
    guardar_lago(raza.sort_values(["anio", "nivel", "unidad_territorial", "raza_color"]), "empleo_raza.csv")


if __name__ == "__main__":
    main()
