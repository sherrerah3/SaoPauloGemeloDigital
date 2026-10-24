"""Empleo formal (P2): F11 establecimientos y F12 empleos, 2011-2024.

Pendiente en este script: F13-F17 (sexo, raza o color), F22-F24 (shoppings), F28.

Salida: data/lago/establecimientos_empleos.csv, una fila por unidad territorial y año,
con los campos del Diccionario: anio, unidad_territorial, nivel,
establecimientos_formales, empleos_formales.
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

FUENTES = {
    "F11": (
        "https://prefeitura.sp.gov.br/documents/d/licenciamento/2026-06-08_a_estabelecimentos_2011_2024-1-",
        "f11_establecimientos",
        "establecimientos_formales",
    ),
    "F12": (
        "https://prefeitura.sp.gov.br/documents/d/licenciamento/2026-06-08_b_empregos_2011_2024-1-",
        "f12_empleos",
        "empleos_formales",
    ),
}


def leer_serie_anual(url: str, nombre_raw: str, campo: str) -> pd.DataFrame:
    tabla = leer_tabla_unidades(descargar(url, nombre_raw, "xlsx"))
    columnas_anio = [c for c in tabla.columns if c[:4].isdigit()]
    largo = ancho_a_largo(
        tabla[["unidad_territorial", "nivel", *columnas_anio]], ["unidad_territorial", "nivel"], "anio", campo
    )
    largo["anio"] = largo["anio"].map(limpiar_anio)
    largo[campo] = columna_numerica(largo[campo]).astype("Int64")
    return largo


def main():
    claves = ["anio", "unidad_territorial", "nivel"]
    f11 = leer_serie_anual(*FUENTES["F11"])
    f12 = leer_serie_anual(*FUENTES["F12"])
    lago = f11.merge(f12, on=claves, how="outer", validate="one_to_one")

    # Prueba de unión: todo distrito y subprefeitura debe encontrar su código (falla si no).
    unir_subprefeituras(unir_distritos(lago))
    lago = lago.sort_values(["anio", "nivel", "unidad_territorial"])
    guardar_lago(lago[[*claves, "establecimientos_formales", "empleos_formales"]], "establecimientos_empleos.csv")


if __name__ == "__main__":
    main()
