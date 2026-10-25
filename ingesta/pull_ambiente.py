"""Ambiente: F25-F27 cobertura vegetal por subprefeitura (2020, 2015 y 2010).

Salida: data/lago/cobertura_vegetal.csv, una fila por unidad y año:
anio, unidad_territorial, nivel, cobertura_vegetal_m2, poblacion, metodo_cobertura.

Cada año se midió con un método distinto (notas de la fuente): no se comparan entre sí.
"""

import pandas as pd

from comun import (
    columna_numerica,
    descargar,
    guardar_lago,
    leer_tabla_unidades,
    limpiar_anio,
    unir_subprefeituras,
)

URL = "https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/"

FUENTES = {
    "F25": (f"{URL}chamadas/2_cobertura_vegetal_2020_60_1679319826.xls", "fotointerpretacion_aerea_2017_2018"),
    "F26": (f"{URL}licenciamento/2_cobertura_vegetal_2015_60.xls", "rapideye_2015"),
    "F27": (f"{URL}licenciamento/2_cobertura_vegetal_2010_60.xls", "spot_2010"),
}


def cobertura(fuente: str, url: str, metodo: str) -> pd.DataFrame:
    ruta = descargar(url, f"{fuente.lower()}_cobertura_vegetal", "xls")
    tabla = leer_tabla_unidades(ruta)
    # Las notas al pie siguen sin fila vacía: se quedan solo las filas con cifra.
    cobertura_col = next(c for c in tabla.columns if c.startswith("Cobertura Vegetal (m2)"))
    tabla = tabla[pd.to_numeric(tabla[cobertura_col], errors="coerce").notna()]
    # Aquí todas las filas, salvo el total, son subprefeituras (sin prefijo en la fuente).
    tabla["nivel"] = tabla["nivel"].where(tabla["nivel"] == "municipio", "subprefeitura")
    poblacion_col = next(c for c in tabla.columns if c.startswith("População"))
    return pd.DataFrame(
        {
            "anio": limpiar_anio(pd.read_excel(ruta, header=None, nrows=3).iloc[2, 0]),
            "unidad_territorial": tabla["unidad_territorial"],
            "nivel": tabla["nivel"],
            "cobertura_vegetal_m2": columna_numerica(tabla[cobertura_col]),
            "poblacion": columna_numerica(tabla[poblacion_col]),
            "metodo_cobertura": metodo,
        }
    )


def main():
    df = pd.concat([cobertura(f, *datos) for f, datos in FUENTES.items()], ignore_index=True)
    unir_subprefeituras(df)  # falla si alguna subprefeitura no cruza
    guardar_lago(df.sort_values(["anio", "nivel", "unidad_territorial"]), "cobertura_vegetal.csv")


if __name__ == "__main__":
    main()
