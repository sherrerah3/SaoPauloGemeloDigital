"""Copia de los crudos de data/raw/ en un release de GitHub.

  python ingesta/crudos.py descargar     baja el .zip del release y lo descomprime en data/raw/
  python ingesta/crudos.py empaquetar    arma data/crudos.zip con lo que hay en data/raw/ (para subirlo)

Son los archivos oficiales tal como los publica cada fuente, con la fecha en que se bajaron. Con ellos
el pipeline corre sin depender de que GeoSampa, Infocidade o SPTrans respondan ese día: descargar()
reutiliza lo que ya está en data/raw/. Los campos Sensibles los filtra build_web.py al publicar, no aquí.
"""

import io
import sys
import zipfile

import requests

from config import DATA, RAW, USER_AGENT

REPOSITORIO = "sherrerah3/SaoPauloGemeloDigital"
# Para usar otra copia: cambiar la etiqueta y subir el nuevo crudos.zip a un release con ese nombre.
ETIQUETA = "crudos-2026-10-27"
URL = f"https://github.com/{REPOSITORIO}/releases/download/{ETIQUETA}/crudos.zip"
ZIP = DATA / "crudos.zip"


def descargar() -> None:
    print(f"Bajando {URL}")
    r = requests.get(URL, headers={"User-Agent": USER_AGENT}, timeout=600)
    r.raise_for_status()
    nuevos = existentes = 0
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        for nombre in z.namelist():
            destino = (RAW / nombre).resolve()
            if not destino.is_relative_to(RAW.resolve()):
                raise ValueError(f"ruta fuera de data/raw/ en el zip: {nombre}")
            if nombre.endswith("/"):
                continue
            # No se pisa un crudo local: puede ser más nuevo que el del release.
            if destino.exists():
                existentes += 1
                continue
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(z.read(nombre))
            nuevos += 1
    print(f"  {nuevos} archivos nuevos en data/raw/; {existentes} ya estaban y no se tocaron")


def empaquetar() -> None:
    archivos = sorted(p for p in RAW.rglob("*") if p.is_file() and p.name != ".gitkeep")
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for ruta in archivos:
            z.write(ruta, ruta.relative_to(RAW).as_posix())
    print(f"  data/crudos.zip: {len(archivos)} archivos, {ZIP.stat().st_size / 1e6:,.0f} MB")
    print(f"  Súbelo a un release con la etiqueta {ETIQUETA} y el nombre crudos.zip")


if __name__ == "__main__":
    acciones = {"descargar": descargar, "empaquetar": empaquetar}
    if len(sys.argv) != 2 or sys.argv[1] not in acciones:
        sys.exit(__doc__)
    acciones[sys.argv[1]]()
