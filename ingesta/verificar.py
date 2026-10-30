"""Pruebas del lago y de public/data/. Sale con código 1 si alguna falla.

Cada script de ingesta registra aquí su prueba (fase 2 del plan).
"""

from __future__ import annotations

import json
import sys

import geopandas as gpd
import pandas as pd
import pyogrio

from comun import cargar_equivalencias, unir_distritos, unir_subprefeituras
from config import (
    CAMPOS_SENSIBLES,
    DATA,
    DICCIONARIO_CSV,
    FUENTES_CSV,
    LAGO,
    LAGO_GEO,
    MAX_MB_ARCHIVO_PUBLICO,
    PUBLIC_DATA,
    PUBLICACION_AUTORIZADA,
    PUBLICACION_TRANSFORMADA,
)

# Archivo del lago → fuentes cuyos campos puede tener (según el Diccionario).
ARCHIVOS_LAGO = {
    "establecimientos_empleos.csv": ["F11", "F12"],
    "sptrans_pasajeros.csv": ["F05"],
    "geo/buses.geojson": ["F29"],
    "geo/paradas.geojson": ["F30"],
    "geo/tren.geojson": ["F31"],
    "geo/metro.geojson": ["F35"],
    "geo/estaciones.geojson": ["F36"],
    "geo/densidad_sectores.geojson": ["F41"],
    "empleo_sexo.csv": ["F13", "F14", "F15"],
    "empleo_raza.csv": ["F16", "F17"],
    "ferias_mercados.csv": ["F21"],
    "shoppings.csv": ["F22", "F23", "F24"],
    "cobertura_vegetal.csv": ["F25", "F26", "F27"],
    "temperatura_minima.csv": ["F06"],
    "area_construida_residencial.csv": ["F28"],
    "poblacion_historica.csv": ["F01"],
    "idhm.csv": ["F07"],
    "nacimientos_tipo_parto.csv": ["F18", "F19", "F20"],
    "geo/favelas.geojson": ["F32"],
    "geo/centros_deportivos.geojson": ["F33"],
    "geo/estadios.geojson": ["F34"],
    "geo/escuelas_infantil.geojson": ["F39"],
    "geo/escuelas_basica.geojson": ["F40"],
}
CAMPOS_CONTRATO = {"id", "campo_lago", "valor", "unidad", "nivel", "fuente_id", "vigencia", "tipo", "advertencia"}
ADVERTENCIA_OBLIGATORIA = {
    "F01",
    "F05",
    "F06",
    "F07",
    "F08",
    "F11",
    "F12",
    "F16",
    "F17",
    "F18",
    "F19",
    "F20",
    "F25",
    "F26",
    "F27",
}

fallas: list[str] = []
avisos: list[str] = []


def prueba(nombre: str, condicion: bool, detalle: str = "") -> None:
    print(f"  {'ok   ' if condicion else 'FALLA'} {nombre}" + (f" — {detalle}" if detalle and not condicion else ""))
    if not condicion:
        fallas.append(nombre)


def diccionario() -> pd.DataFrame:
    return pd.read_csv(DICCIONARIO_CSV, dtype=str).fillna("")


# --- Catálogo ---------------------------------------------------------------


def verificar_catalogo():
    print("Catálogo")
    dicc = diccionario()
    sensibles = dicc[dicc.clasificacion.str.lower() == "sensible"].groupby("fuente_id")["campo"].apply(set).to_dict()
    prueba(
        "config.CAMPOS_SENSIBLES coincide con el Diccionario",
        sensibles == CAMPOS_SENSIBLES,
        f"Diccionario: {sensibles}",
    )


# --- Lago -------------------------------------------------------------------


def verificar_lago():
    print("Lago")
    dicc = diccionario()
    for archivo, fuentes in ARCHIVOS_LAGO.items():
        ruta = LAGO / archivo
        if not ruta.exists():
            prueba(f"{archivo} existe", False, "corre el pull_*.py correspondiente")
            continue
        if ruta.suffix == ".geojson":
            info = pyogrio.read_info(ruta)
            columnas = set(info["fields"])
            prueba(f"{archivo}: EPSG:31983", info["crs"] == "EPSG:31983", f"llegó {info['crs']}")
        else:
            columnas = set(pd.read_csv(ruta, nrows=0).columns)
        permitidas = set(dicc[dicc.fuente_id.isin(fuentes)]["campo"])
        extra = columnas - permitidas
        prueba(f"{archivo}: todas las columnas están en el Diccionario", not extra, f"sobran {sorted(extra)}")


def verificar_territorio():
    print("Eje territorial")
    eq = cargar_equivalencias()
    prueba("96 distritos", len(eq) == 96, f"hay {len(eq)}")
    prueba("32 subprefeituras", eq.codigo_subprefeitura.nunique() == 32, f"hay {eq.codigo_subprefeitura.nunique()}")
    prueba("códigos de distrito únicos", eq.codigo_distrito.is_unique)


def verificar_empleo():
    print("Empleo (F11, F12)")
    df = pd.read_csv(LAGO / "establecimientos_empleos.csv")
    try:
        unir_subprefeituras(unir_distritos(df))
        prueba("toda unidad cruza con la tabla de equivalencias", True)
    except ValueError as e:
        prueba("toda unidad cruza con la tabla de equivalencias", False, str(e))
    por_anio = df.groupby(["anio", "nivel"]).size().unstack()
    prueba(
        "96 distritos y 32 subprefeituras en cada año",
        (por_anio["distrito"] == 96).all() and (por_anio["subprefeitura"] == 32).all(),
    )
    for campo in ("establecimientos_formales", "empleos_formales"):
        t = df.pivot_table(index="anio", columns="nivel", values=campo, aggfunc="sum").fillna(0)
        cuadra = (t["distrito"] + t["invalidos"] + t["no_localizados"] - t["municipio"]).abs().max() == 0
        prueba(f"{campo}: distritos + inválidos + no localizados = municipio", cuadra)
        prueba(
            f"{campo}: subprefeituras = suma de sus distritos", (t["subprefeitura"] - t["distrito"]).abs().max() == 0
        )


def verificar_composicion_empleo():
    print("Empleo por sexo y raza (F13-F17)")
    base = pd.read_csv(LAGO / "establecimientos_empleos.csv")
    claves = ["anio", "unidad_territorial", "nivel"]
    sexo = pd.read_csv(LAGO / "empleo_sexo.csv")
    raza = pd.read_csv(LAGO / "empleo_raza.csv").groupby(claves, as_index=False)["empleos"].sum()
    for nombre, df, columnas in (
        ("sexo", sexo, ["empleos_masculino", "empleos_femenino"]),
        ("raza", raza, ["empleos"]),
    ):
        unido = df.merge(base, on=claves, how="left")
        diferencia = (unido[columnas].sum(axis=1) - unido["empleos_formales"]).abs()
        # Sexo deja fuera la columna «Inválido» (casi siempre 0): se tolera una diferencia mínima.
        prueba(
            f"{nombre}: la suma de categorías = empleos_formales (F12) en ≥ 99 % de las filas",
            (diferencia <= 0.001 * unido["empleos_formales"]).mean() >= 0.99,
        )


def verificar_equipamientos():
    print("Equipamientos (F21, F22, F33, F34, F39, F40) y favelas (F32)")
    ferias = pd.read_csv(LAGO / "ferias_mercados.csv")
    t = ferias.pivot_table(index=["anio", "tipo_equipamiento"], columns="nivel", values="cantidad", aggfunc="sum")
    # La fuente no cuadra en algunos años viejos; el año que se publica (el último) sí debe cuadrar.
    cuadra = t.nunique(axis=1) == 1
    ultimo = ferias["anio"].max()
    prueba(f"F21 {ultimo}: distritos = subprefeituras = municipio en cada tipo", cuadra.loc[ultimo].all())
    descuadrados = sorted({anio for anio, _ in cuadra[~cuadra].index})
    if descuadrados:
        avisos.append(f"F21: en {', '.join(map(str, descuadrados))} los distritos no suman el total de la fuente")
    eq = pd.read_csv(DATA / "derivados" / "equipamientos_distrito.csv", dtype={"codigo_distrito": str})
    total = eq.set_index("codigo_distrito").loc["MSP"]
    for capa, columna in (("escuelas_infantil", "escuelas_infantil"), ("escuelas_basica", "escuelas_basica")):
        en_capa = pyogrio.read_info(LAGO_GEO / f"{capa}.geojson")["features"]
        if en_capa != total[columna]:
            avisos.append(f"{en_capa - total[columna]:.0f} puntos de {capa} caen fuera de los 96 distritos")
    fav = pd.read_csv(DATA / "derivados" / "favelas_distrito.csv", dtype={"codigo_distrito": str})
    pct = fav.loc[fav.codigo_distrito != "MSP", "domicilios_favela_pct"]
    prueba("F32: domicilios en favela entre 0 y 100 % del distrito", ((pct >= 0) & (pct <= 100)).all())


def verificar_poblacion():
    print("Población (F41)")
    sectores = gpd.read_file(LAGO_GEO / "densidad_sectores.geojson")
    distritos = gpd.read_file(LAGO_GEO / "distritos.gpkg")[["codigo_distrito", "geometry"]]
    centros = sectores[["codigo_sector", "codigo_distrito", "geometry"]].copy()
    centros["geometry"] = sectores.geometry.representative_point()
    j = gpd.sjoin(centros, distritos.rename(columns={"codigo_distrito": "espacial"}), predicate="within")
    coincide = (j["codigo_distrito"] == j["espacial"]).mean()
    # La hipótesis del Diccionario («dígitos 8 y 9 = distrito, por verificar»), medida.
    prueba(
        "codigo_distrito (dígitos 8-9) = distrito que contiene al sector, en ≥ 99,5 %",
        coincide >= 0.995,
        f"coincide {coincide:.2%}",
    )
    prueba("los 96 distritos tienen sectores", sectores["codigo_distrito"].nunique() == 96)
    prueba("códigos de sector únicos", sectores["codigo_sector"].is_unique)


def verificar_poblacion_historica():
    print("Población histórica (F01)")
    h = pd.read_csv(LAGO / "poblacion_historica.csv")
    prueba(
        "F01: un censo por año, de 1872 a 2022",
        h["anio"].is_unique and (h["anio"].min(), h["anio"].max()) == (1872, 2022),
    )
    prueba("F01: 13 censos", len(h) == 13, f"hay {len(h)}")
    prueba(
        "F01: Brasil > Estado > Municipio en cada censo",
        (
            (h["poblacion_brasil"] > h["poblacion_estado_sp"])
            & (h["poblacion_estado_sp"] > h["poblacion_municipio_sp"])
        ).all(),
    )
    rm = h.dropna(subset=["poblacion_rm_sp"])
    prueba(
        "F01: Estado > RM > Municipio cuando la RM tiene cifra",
        (
            (rm["poblacion_estado_sp"] > rm["poblacion_rm_sp"]) & (rm["poblacion_rm_sp"] > rm["poblacion_municipio_sp"])
        ).all(),
    )
    prueba("F01: la RM no tiene cifra antes de 1980", h[h["anio"] < 1980]["poblacion_rm_sp"].isna().all())
    prueba(
        "F01: el municipio crece de un censo al siguiente",
        h.sort_values("anio")["poblacion_municipio_sp"].is_monotonic_increasing,
    )
    # El censo 2022 de F01 y los sectores de F41 vienen del mismo censo: deben dar casi lo mismo.
    sectores = gpd.read_file(LAGO_GEO / "densidad_sectores.geojson", columns=["poblacion"], ignore_geometry=True)
    censo = int(h.loc[h["anio"] == 2022, "poblacion_municipio_sp"].iloc[0])
    diferencia = abs(sectores["poblacion"].sum() - censo) / censo
    prueba("F01 2022 coincide con la suma de sectores de F41 (±0,5 %)", diferencia < 0.005, f"difiere {diferencia:.2%}")


def verificar_idhm():
    print("IDH municipal (F07)")
    df = pd.read_csv(LAGO / "idhm.csv")
    prueba("F07: 32 filas (31 prefeituras y MSP) en 2000 y en 2010", (df.groupby("anio").size() == 32).all())
    prueba(
        "F07: IDHM e IDHM Renda entre 0 y 1", df[["idhm", "idhm_renda"]].apply(lambda c: c.between(0, 1)).all().all()
    )
    # Un punto decimal mal leído (0.733 → 733) se vería aquí; la cifra de la ciudad la publica SMUL.
    msp = df[df["prefeitura_regional"] == "MSP"].set_index("anio")["idhm"]
    prueba(
        "F07: el IDHM de MSP es 0,733 en 2000 y 0,805 en 2010, como publica la Prefeitura",
        msp.round(3).to_dict() == {2000: 0.733, 2010: 0.805},
    )
    ancho = df.pivot(index="prefeitura_regional", columns="anio", values="idhm")
    prueba("F07: el IDHM sube entre 2000 y 2010 en cada zona", (ancho[2010] > ancho[2000]).all())

    zonas = df[df["prefeitura_regional"] != "MSP"].drop_duplicates("prefeitura_regional").assign(nivel="subprefeitura")
    try:
        cruzadas = unir_subprefeituras(zonas, "prefeitura_regional")
        prueba("F07: toda Prefeitura Regional cruza con una subprefeitura", True)
    except ValueError as e:
        prueba("F07: toda Prefeitura Regional cruza con una subprefeitura", False, str(e))
        return
    prueba("F07: ninguna subprefeitura se repite", cruzadas["codigo_subprefeitura"].is_unique)
    sin_cifra = set(cargar_equivalencias()["codigo_subprefeitura"]) - set(cruzadas["codigo_subprefeitura"])
    # El Atlas es de 2013 y Sapopemba se separó de Vila Prudente ese año: queda sin cifra propia.
    prueba(
        "F07: la única subprefeitura sin cifra es Sapopemba (código 32)",
        sin_cifra == {"32"},
        f"faltan {sorted(sin_cifra)}",
    )


def verificar_nacimientos():
    print("Nacimientos (F18-F20)")
    n = pd.read_csv(LAGO / "nacimientos_tipo_parto.csv")
    claves = ["anio", "nivel", "unidad_territorial"]
    prueba("F18-F20: tres tipos de parto por unidad", (n.groupby(claves).size() == 3).all())
    total = n.groupby(claves, as_index=False)["nacidos_vivos"].sum()
    por_nivel = total.groupby(["anio", "nivel"]).size().unstack()
    prueba(
        "F18-F20: 96 distritos, 32 subprefeituras, MSP y una fila sin ubicación por año",
        (por_nivel["distrito"] == 96).all()
        and (por_nivel["subprefeitura"] == 32).all()
        and (por_nivel["municipio"] == 1).all()
        and (por_nivel["sin_ubicacion"] == 1).all(),
    )
    suma = total.pivot_table(index="anio", columns="nivel", values="nacidos_vivos", aggfunc="sum")
    prueba(
        "F18-F20: distritos + sin ubicación = municipio",
        (suma["distrito"] + suma["sin_ubicacion"] - suma["municipio"]).abs().max() == 0,
    )
    prueba("F18-F20: subprefeituras = distritos", (suma["subprefeitura"] - suma["distrito"]).abs().max() == 0)

    # La posición de las filas decide el nivel: cada subprefeitura debe sumar exactamente sus distritos.
    eq = cargar_equivalencias()[["codigo_distrito", "codigo_subprefeitura"]]
    distritos = unir_distritos(total[total["nivel"] == "distrito"]).merge(eq, on="codigo_distrito")
    de_distritos = distritos.groupby(["anio", "codigo_subprefeitura"])["nacidos_vivos"].sum()
    subprefeituras = unir_subprefeituras(total[total["nivel"] == "subprefeitura"])
    de_subprefeituras = subprefeituras.set_index(["anio", "codigo_subprefeitura"])["nacidos_vivos"]
    prueba(
        "F18-F20: cada subprefeitura = suma de sus distritos",
        len(de_distritos) == len(de_subprefeituras) and (de_distritos - de_subprefeituras).abs().max() == 0,
    )
    for anio, fila in suma.iterrows():
        pct = 100 * fila["sin_ubicacion"] / fila["municipio"]
        if pct >= 1:
            avisos.append(f"F18-F20 {anio}: {pct:.1f} % de los nacimientos no tiene distrito")


def verificar_temperatura():
    print("Temperatura mínima (F06)")
    t = pd.read_csv(LAGO / "temperatura_minima.csv")
    prueba("F06: una fila por año y mes", not t.duplicated(["anio", "mes"]).any())
    prueba("F06: meses entre 1 y 12", t["mes"].between(1, 12).all())
    prueba("F06: doce meses en cada año", (t.groupby("anio").size() == 12).all())
    anios = sorted(t["anio"].unique())
    prueba("F06: años seguidos, sin huecos", anios == list(range(anios[0], anios[-1] + 1)), f"{anios[0]} a {anios[-1]}")
    # Un punto decimal mal leído (17.975 → 17 975) se vería aquí como un valor imposible.
    prueba("F06: temperaturas mínimas entre 0 y 30 °C", t["temp_min_media_c"].between(0, 30).all())
    # La fuente publica la normal 1991-2020 (15,32 °C al año): recalcularla valida la tabla pivotada.
    normal = t[t["anio"].between(1991, 2020)].groupby("mes")["temp_min_media_c"].mean().mean()
    prueba("F06: la normal 1991-2020 recalculada coincide con la de la fuente (15,32 °C)", abs(normal - 15.32) < 0.01)


def verificar_transporte():
    print("Transporte (F05, F29-F31, F35, F36)")
    cob = pd.read_csv(DATA / "derivados" / "cobertura_transporte_distrito.csv", dtype={"codigo_distrito": str})
    pct = cob[[c for c in cob.columns if c.endswith("_pct")]]
    prueba("coberturas entre 0 y 100 %", ((pct >= 0) & (pct <= 100.0001)).all().all())
    distritos = cob[cob.codigo_distrito != "MSP"]
    prueba("96 distritos con cobertura calculada", len(distritos) == 96)
    total = cob.set_index("codigo_distrito").loc["MSP"]
    prueba("población de distritos = total del municipio", abs(distritos["poblacion"].sum() - total["poblacion"]) < 1)
    en_capa = pyogrio.read_info(LAGO_GEO / "paradas.geojson")["features"]
    fuera = en_capa - total["paradas_bus"]
    if fuera:
        avisos.append(f"{fuera:.0f} paradas de bus (F30) caen fuera de los 96 distritos")

    ruta = LAGO / "sptrans_pasajeros.csv"
    if not ruta.exists():
        avisos.append("Falta lago/sptrans_pasajeros.csv (F05)")
        return
    f05 = pd.read_csv(ruta, dtype={"codigo_linea": str})
    prueba("F05: una fila por línea y mes", not f05.duplicated(["anio", "mes", "codigo_linea"]).any())
    periodos = pd.PeriodIndex(sorted({f"{a}-{m:02d}" for a, m in zip(f05.anio, f05.mes, strict=True)}), freq="M")
    seguidos = len(periodos) == (periodos.max() - periodos.min()).n + 1
    prueba(
        "F05: meses seguidos, sin huecos",
        seguidos,
        f"hay {len(periodos)} meses entre {periodos.min()} y {periodos.max()}",
    )
    prueba(
        "F05: sin pasajeros negativos", (f05[[c for c in f05.columns if c.startswith("pasajeros")]] >= 0).all().all()
    )
    buses = gpd.read_file(LAGO_GEO / "buses.geojson", columns=["codigo_linea"], ignore_geometry=True)
    cruza = f05["codigo_linea"].isin(set(buses["codigo_linea"].str.replace("-", "", regex=False)))
    avisos.append(
        f"F05 → F29 (código sin guion): cruzan {cruza.mean():.1%} de las filas, "
        f"{f05.loc[cruza, 'pasajeros_total'].sum() / f05['pasajeros_total'].sum():.1%} de los pasajeros"
    )


# --- public/data ------------------------------------------------------------


def verificar_publico():
    print("public/data")
    dicc = diccionario()
    campos_por_fuente = dicc.groupby("fuente_id")["campo"].apply(set).to_dict()
    fuentes = pd.read_csv(FUENTES_CSV, dtype=str).set_index("fuente_id")
    usadas: set[str] = set()
    grandes, malos_contrato, sensibles_publicados, campos_inexistentes, sin_advertencia = [], [], [], [], []

    # .json y .geojson: las capas del mapa también pasan por los chequeos de tamaño y privacidad.
    for ruta in sorted([*PUBLIC_DATA.rglob("*.json"), *PUBLIC_DATA.rglob("*.geojson")]):
        rel = ruta.relative_to(PUBLIC_DATA).as_posix()
        if ruta.stat().st_size > MAX_MB_ARCHIVO_PUBLICO * 1024 * 1024:
            grandes.append(rel)
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        if isinstance(datos, dict) and "indicadores" in datos:
            for r in datos["indicadores"]:
                usadas.add(r["fuente_id"])
                if not set(r) >= CAMPOS_CONTRATO or r["tipo"] not in {"observado", "estimado", "proxy", "declarado"}:
                    malos_contrato.append(f"{rel}:{r.get('id')}")
                if r["campo_lago"] not in campos_por_fuente.get(r["fuente_id"], set()):
                    campos_inexistentes.append(f"{r['fuente_id']}.{r['campo_lago']}")
                if (
                    r["campo_lago"] in CAMPOS_SENSIBLES.get(r["fuente_id"], set())
                    and (r["fuente_id"], r["campo_lago"]) not in PUBLICACION_TRANSFORMADA
                ):
                    sensibles_publicados.append(f"{rel}:{r['id']}")
                if r["fuente_id"] in ADVERTENCIA_OBLIGATORIA and not r.get("advertencia"):
                    sin_advertencia.append(r["id"])
        if isinstance(datos, dict) and datos.get("type") == "FeatureCollection":
            fuente = datos.get("fuente_id")
            if fuente:
                usadas.add(fuente)
            claves = set().union(*(f["properties"].keys() for f in datos["features"])) if datos["features"] else set()
            autorizados = {campo for f, campo in PUBLICACION_AUTORIZADA if f == fuente}
            if fuente and claves & (CAMPOS_SENSIBLES.get(fuente, set()) - autorizados):
                sensibles_publicados.append(rel)

    prueba("ningún archivo supera el límite", not grandes, ", ".join(grandes))
    prueba("todos los indicadores cumplen el contrato", not malos_contrato, ", ".join(malos_contrato[:5]))
    prueba(
        "todo campo_lago existe en el Diccionario para su fuente",
        not campos_inexistentes,
        ", ".join(sorted(set(campos_inexistentes))),
    )
    prueba("ningún campo Sensible llega a public/data", not sensibles_publicados, ", ".join(sensibles_publicados[:5]))
    prueba("advertencias obligatorias presentes", not sin_advertencia, ", ".join(sin_advertencia[:5]))

    pendientes = [f for f in sorted(usadas) if fuentes.loc[f, "estado"] != "Integrada al lago"]
    if pendientes:
        avisos.append(f"Fuentes publicadas que el Excel aún marca como no integradas: {', '.join(pendientes)}")


def main():
    verificar_catalogo()
    verificar_lago()
    verificar_territorio()
    verificar_empleo()
    verificar_composicion_empleo()
    verificar_poblacion()
    verificar_poblacion_historica()
    verificar_idhm()
    verificar_nacimientos()
    verificar_transporte()
    verificar_equipamientos()
    verificar_temperatura()
    verificar_publico()
    for a in avisos:
        print(f"  aviso {a}")
    print(f"\n{len(fallas)} fallas" if fallas else "\nTodo en orden")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
