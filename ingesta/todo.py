"""Corre todo el pipeline en orden: Excel → descargas → lago → public/data → verificación.

  python ingesta/todo.py                  todo
  python ingesta/todo.py --sin-pasajeros  sin bajar los ~670 archivos diarios de F05
  python ingesta/todo.py --solo-web       solo build_web.py y verificar.py (sin descargar)
  python ingesta/todo.py --actualizar     además busca reportes nuevos de F05 en la Prefeitura

Los datos están congelados en los crudos del release (crudos.py): si data/raw/ está vacío, se bajan
primero. Las demás fuentes ya reutilizan sus crudos; F05 también, salvo con --actualizar.

Funciona igual en local (.venv) y en Docker: usa el mismo Python que lo ejecuta.
"""

import subprocess
import sys
from pathlib import Path

INGESTA = Path(__file__).resolve().parent
RAW = INGESTA.parent / "data" / "raw"

PASOS = [
    ["exportar_excel.py"],
    ["pull_territorio.py"],
    ["pull_empleo.py"],
    ["pull_poblacion.py"],
    ["pull_movilidad.py"],
    ["pull_equipamientos.py"],
    ["pull_ambiente.py"],
    ["build_web.py"],
    ["verificar.py"],
]


def main():
    args = sys.argv[1:]
    pasos = PASOS[-2:] if "--solo-web" in args else PASOS
    if "--solo-web" not in args and not any(p.name != ".gitkeep" for p in RAW.iterdir()):
        pasos = [["crudos.py", "descargar"], *pasos]
    for paso in pasos:
        if paso[0] == "pull_movilidad.py":
            paso = [*paso, *(a for a in ("--sin-pasajeros", "--actualizar") if a in args)]
        print(f"\n▶ {' '.join(paso)}", flush=True)
        r = subprocess.run([sys.executable, "-W", "ignore", *paso], cwd=INGESTA)
        if r.returncode:
            sys.exit(f"Falló {paso[0]} (código {r.returncode})")


if __name__ == "__main__":
    main()
