"""Convierte fotos a WebP en dos anchos para la web.

  python herramientas/fotos_webp.py ../fotos-saopaulo/portada.jpg portada

Escribe public/fotos/<nombre>-1600.webp y <nombre>-800.webp. El original (varios MB) no se sube:
el sitio usa solo estas versiones, y el navegador elige el ancho según la pantalla (srcset).
"""

import sys
from pathlib import Path

from PIL import Image, ImageOps

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "public" / "fotos"
ANCHOS = (1600, 800)
CALIDAD = 78


def convertir(origen: Path, nombre: str) -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    with Image.open(origen) as foto:
        foto = ImageOps.exif_transpose(foto).convert("RGB")  # respeta la rotación de la cámara
        for ancho in ANCHOS:
            copia = foto.copy()
            copia.thumbnail((ancho, ancho * 4))
            destino = SALIDA / f"{nombre}-{ancho}.webp"
            # Sin metadatos: la foto no lleva EXIF (cámara, fecha, GPS) a la web.
            copia.save(destino, "WEBP", quality=CALIDAD, method=6)
            print(f"  public/fotos/{destino.name}: {copia.width}×{copia.height}, {destino.stat().st_size / 1024:,.0f} KB")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    convertir(Path(sys.argv[1]), sys.argv[2])
