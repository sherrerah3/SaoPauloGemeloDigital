"""Copia las hojas Fuentes y Diccionario del Excel a data/fuentes.csv y data/diccionario.csv.

El Excel sigue siendo la fuente de verdad del catálogo; los CSV son lo que leen los
scripts y la página «Fuentes y método». Correr de nuevo cada vez que se edite el Excel.
"""
import openpyxl
import pandas as pd

from config import DICCIONARIO_CSV, EXCEL, FUENTES_CSV

COLUMNAS_FUENTES = {
    "ID fuente": "fuente_id",
    "Nombre del conjunto de datos": "nombre",
    "Entidad que lo publica": "entidad",
    "Tipo de publicador": "tipo_publicador",
    "URL exacta (descarga o API)": "url",
    "Formato": "formato",
    "Cómo se obtiene": "como_se_obtiene",
    "Licencia (tal como aparece)": "licencia",
    "¿Trae datos de personas?": "datos_personas",
    "Cobertura geográfica": "cobertura",
    "Periodo que cubre": "periodo",
    "Frecuencia de actualización": "frecuencia",
    "Fecha en que la probaron (AAAA-MM-DD)": "fecha_prueba",
    "Estado": "estado",
    "Cómo la encontraron (IA o búsqueda)": "como_la_encontraron",
    "Observaciones": "observaciones",
}

COLUMNAS_DICCIONARIO = {
    "ID fuente": "fuente_id",
    "Archivo o tabla en el lago": "archivo",
    "Nombre del campo en el lago": "campo",
    "Nombre original en la fuente": "nombre_original",
    "Qué significa (en una frase)": "significado",
    "Tipo de dato": "tipo_dato",
    "Unidad de medida": "unidad",
    "Ejemplo de valor": "ejemplo",
    "¿Puede venir vacío?": "puede_vacio",
    "Valores permitidos o rango": "rango",
    "Clasificación": "clasificacion",
    "Transformación que le hicieron": "transformacion",
    "Pregunta del sistema que ayuda a responder": "pregunta",
}


def leer_hoja(nombre_hoja: str, columnas: dict) -> pd.DataFrame:
    hoja = openpyxl.load_workbook(EXCEL, data_only=True)[nombre_hoja]
    filas = list(hoja.iter_rows(values_only=True))
    # Fila 3: encabezados; fila 4: ejemplo gris del profesor (no cuenta).
    encabezado = [str(v).strip() if v else None for v in filas[2]]
    datos = [f for f in filas[4:] if f[0] and any(v not in (None, "") for v in f[1:])]
    df = pd.DataFrame(datos, columns=encabezado).loc[:, list(columnas)]
    df = df.rename(columns=columnas)
    for col in df.columns:
        df[col] = df[col].map(lambda v: str(v).strip() if v is not None else "")
    return df


def main():
    fuentes = leer_hoja("1. Fuentes", COLUMNAS_FUENTES)
    fuentes["fecha_prueba"] = fuentes["fecha_prueba"].str.slice(0, 10)
    fuentes.to_csv(FUENTES_CSV, index=False)
    print(f"data/fuentes.csv: {len(fuentes)} fuentes")

    dicc = leer_hoja("2. Diccionario", COLUMNAS_DICCIONARIO)
    # «F13, F14, F15» → una fila por fuente, para poder buscar por ID.
    dicc["fuente_id"] = dicc["fuente_id"].str.split(r"\s*,\s*")
    dicc = dicc.explode("fuente_id")
    # «anio, mes» (F05) son dos campos.
    dicc["campo"] = dicc["campo"].str.split(r"\s*,\s*")
    dicc = dicc.explode("campo").reset_index(drop=True)
    dicc.to_csv(DICCIONARIO_CSV, index=False)
    print(f"data/diccionario.csv: {len(dicc)} filas (fuente × campo)")


if __name__ == "__main__":
    main()
