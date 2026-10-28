"""Convierte fotos a WebP en dos anchos para la web.

  python herramientas/fotos_webp.py ../fotos-saopaulo/portada.jpg portada

Escribe public/fotos/<nombre>-1600.webp y <nombre>-800.webp. El original (varios MB) no se sube:
el sitio usa solo estas versiones, y el navegador elige el ancho según la pantalla (srcset).

Con un tercer argumento se eligen otros anchos y otra subcarpeta, por ejemplo para las miniaturas
del globo del mapa:

  python herramientas/fotos_webp.py ../fotos/masp.jpg masp --anchos 480 --carpeta sitios

Escribe public/fotos/sitios/masp-480.webp.
"""

import argparse
from pathlib import Path

from PIL import Image, ImageOps

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "public" / "fotos"
ANCHOS = (1600, 800)
CALIDAD = 78


def convertir(origen: Path, nombre: str, anchos: tuple[int, ...] = ANCHOS, carpeta: str = "") -> None:
    salida = SALIDA / carpeta
    salida.mkdir(parents=True, exist_ok=True)
    with Image.open(origen) as foto:
        foto = ImageOps.exif_transpose(foto).convert("RGB")  # respeta la rotación de la cámara
        for ancho in anchos:
            copia = foto.copy()
            copia.thumbnail((ancho, ancho * 4))
            destino = salida / f"{nombre}-{ancho}.webp"
            # Sin metadatos: la foto no lleva EXIF (cámara, fecha, GPS) a la web.
            copia.save(destino, "WEBP", quality=CALIDAD, method=6)
            print(
                f"  {destino.relative_to(RAIZ).as_posix()}: {copia.width}×{copia.height}, "
                f"{destino.stat().st_size / 1024:,.0f} KB"
            )


if __name__ == "__main__":
    analizador = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analizador.add_argument("origen", type=Path)
    analizador.add_argument("nombre")
    analizador.add_argument("--anchos", default=",".join(map(str, ANCHOS)), help="anchos en px separados por coma")
    analizador.add_argument("--carpeta", default="", help="subcarpeta de public/fotos/")
    args = analizador.parse_args()
    convertir(args.origen, args.nombre, tuple(int(a) for a in args.anchos.split(",")), args.carpeta)
