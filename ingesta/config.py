"""Parámetros compartidos por todos los scripts de ingesta.

Lo que está aquí son decisiones del equipo: cambiarlas cambia lo que publica la app.
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
RAW = DATA / "raw"
LAGO = DATA / "lago"
LAGO_GEO = LAGO / "geo"
PUBLIC_DATA = RAIZ / "public" / "data"

EXCEL = DATA / "Diccionario_de_datos_TallerDatos.xlsx"
FUENTES_CSV = DATA / "fuentes.csv"
DICCIONARIO_CSV = DATA / "diccionario.csv"
EQUIVALENCIAS = LAGO / "territorio_equivalencias.csv"

# Sistemas de referencia: se mide en metros y se publica en latitud/longitud.
CRS_TRABAJO = "EPSG:31983"  # SIRGAS2000 / UTM 23S
CRS_WEB = "EPSG:4326"

# Algunos servidores de la Prefeitura devuelven 403 sin un User-Agent de navegador.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

GEOSAMPA_WFS = "https://wfs.geosampa.prefeitura.sp.gov.br/geoserver/ows"

# Código IBGE del municipio de São Paulo (para filtrar F08).
CODIGO_IBGE_SP = "3550308"

# --- Privacidad (sección 7 del plan) -------------------------------------
# Campos clasificados como «Sensible» en el Diccionario, por fuente («nombre» es
# sensible en F32 pero público en shoppings o escuelas). verificar.py comprueba que
# esta lista coincide con el Diccionario y que nada de esto llega a public/data/.
# Decisión por defecto de cada uno (el equipo debe confirmarla):
#   tipo_parto            → no se publica; solo el total de nacidos_vivos.
#   raza_color, empleos   → solo como porcentaje, con supresión bajo el umbral.
#   nombre, ubicacion_texto, propiedad_terreno (F32) → no se publican.
#   indice_vulnerabilidad → no se publica hasta conocer su escala y definición.
CAMPOS_SENSIBLES = {
    "F16": {"raza_color", "empleos"},
    "F17": {"raza_color", "empleos"},
    "F18": {"tipo_parto"},
    "F19": {"tipo_parto"},
    "F20": {"tipo_parto"},
    "F32": {"nombre", "ubicacion_texto", "propiedad_terreno"},
    "F41": {"indice_vulnerabilidad"},
}
# Excepción controlada: estos campos sensibles sí salen, pero transformados.
PUBLICACION_TRANSFORMADA = {
    ("F16", "empleos"): "porcentaje",
    ("F17", "empleos"): "porcentaje",
    ("F16", "raza_color"): "porcentaje",
    ("F17", "raza_color"): "porcentaje",
}

# Celdas con menos casos que este umbral se suprimen (pendiente de confirmar).
UMBRAL_SUPRESION = 10

# --- Decisiones analíticas -----------------------------------------------
# Radio de cobertura de transporte (P1). Es una decisión del equipo, no un estándar.
RADIO_COBERTURA_M = 500

# Tamaño máximo por archivo en public/data/ antes de que verificar.py avise.
MAX_MB_ARCHIVO_PUBLICO = 5
