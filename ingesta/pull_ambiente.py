"""Ambiente: F25-F27 cobertura vegetal por subprefeitura (2020, 2015 y 2010) y F06 temperatura mínima.

Salidas:
  data/lago/cobertura_vegetal.csv, una fila por unidad y año:
    anio, unidad_territorial, nivel, cobertura_vegetal_m2, poblacion, metodo_cobertura.
  data/lago/temperatura_minima.csv, una fila por año y mes:
    anio, mes, temp_min_media_c.

La cobertura vegetal se midió con un método distinto cada año (notas de la fuente): no se compara
entre años. La temperatura sale de una sola estación (IAG Água Funda, USP): no es de toda la ciudad.
"""

import pandas as pd

from comun import (
    columna_numerica,
    descargar,
    guardar_lago,
    leer_excel,
    leer_tabla_unidades,
    limpiar_anio,
    unir_subprefeituras,
)

URL = "https://www.prefeitura.sp.gov.br/cidade/secretarias/upload/"
URL_F06 = "https://prefeitura.sp.gov.br/documents/d/licenciamento/2025_temp_media_minima_1933_2025"
MESES_F06 = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]

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


def temperatura_minima() -> pd.DataFrame:
    """F06: promedio mensual de las temperaturas mínimas del aire, 1933-2025, pasado de ancho a largo.

    La tabla trae primero las «normales» climatológicas (promedios de 30 años) y después una fila por año,
    con una columna por mes y una columna ANUAL. Solo se guardan las filas de año y los doce meses: las
    normales y el promedio anual se recalculan en build_web.py a partir de estos meses.
    """
    crudo = leer_excel(descargar(URL_F06, "f06_temperatura_minima", "xls"))  # primera hoja: Planilha1
    inicio = crudo.index[crudo[0].fillna("").str.strip() == "Anos/Meses"]
    if inicio.empty:
        raise ValueError("F06: no se encontró el encabezado «Anos/Meses»")
    fila = inicio[0]
    meses = [str(v).strip().rstrip(".").upper() for v in crudo.iloc[fila, 1:13]]
    if meses != MESES_F06:
        raise ValueError(f"F06: los meses del encabezado cambiaron: {meses}")
    cuerpo = crudo.iloc[fila + 1 :, :13]
    # Solo filas cuya primera celda es un año («1933»); «Normal1 (1991-2020)» y las notas quedan fuera.
    cuerpo = cuerpo[cuerpo[0].fillna("").str.strip().str.fullmatch(r"(19|20)\d{2}")]
    cuerpo = cuerpo.set_axis(["anio", *range(1, 13)], axis=1)
    largo = cuerpo.melt(id_vars="anio", var_name="mes", value_name="temp_min_media_c")
    largo["anio"] = largo["anio"].str.strip().astype(int)
    largo["mes"] = largo["mes"].astype(int)
    # No se usa a_numero(): en estas celdas el punto es decimal, y una cifra como «17.975» la leería
    # como 17 975 (separador de miles).
    largo["temp_min_media_c"] = pd.to_numeric(largo["temp_min_media_c"], errors="raise")
    largo = largo.dropna(subset=["temp_min_media_c"])
    return largo.sort_values(["anio", "mes"]).reset_index(drop=True)


def main():
    df = pd.concat([cobertura(f, *datos) for f, datos in FUENTES.items()], ignore_index=True)
    unir_subprefeituras(df)  # falla si alguna subprefeitura no cruza
    guardar_lago(df.sort_values(["anio", "nivel", "unidad_territorial"]), "cobertura_vegetal.csv")
    guardar_lago(temperatura_minima(), "temperatura_minima.csv")


if __name__ == "__main__":
    main()
