#!/usr/bin/env python3
"""
archivo_biblioteca.py -- BLOQUE 1 de OT-7 (archivo y finanzas, F7-1): foto
que entra -> ¿caché efímera o biblioteca permanente? -> si es ticket, gasto
con evidencia.

E1 (HAS): la decisión caché-vs-biblioteca la toma el CLASIFICADOR de
entrada, nunca el tiempo -- nada se "promueve" por viejo, y nada permanente
se borra por cron. Este módulo solo archiva lo permanente (categoria !=
"cache"); la caché efímera (`~/.hermes/cache/images`, ya existente) sigue
su vida aparte y este módulo no la toca.

Clasificador de vision INYECTABLE (mismo patrón que el extractor de
horario_por_foto.py y el transcriptor de corte_silencios.py): este módulo
NUNCA llama red por su cuenta. El cableado real (Gemini Vision de paga
verificado, u Ollama local) sigue pendiente de la misma decisión anotada en
ESTADO.md para horario_por_foto.py (r.91: nombres/salud nunca a API
gratis) -- fotos "familiar"/"escuela" pueden traer caras o nombres, así que
tampoco se cablean aquí a ciegas. Los montos de tickets SÍ están resueltos
como aptos para API gratis (ESTADO.md, decisión de privacidad), pero el
extractor real de todas formas se cablea aparte, no en este bloque.

E2 (HAS): árbol de biblioteca permanente, siempre bajo el disco externo (la
Seagate es el hogar; la HP solo cachea) --

    biblioteca/escuela/<materia>/
    biblioteca/finanzas/AAAA-MM/  y  biblioteca/finanzas/reportes/
    biblioteca/familia/AAAA/
    biblioteca/contenido/{guiones,material,publicados}/
    biblioteca/proyectos/<nombre>/
    biblioteca/inbox/            -- categoria "otro", revisar mensual

En entorno "simulacion" (r.20) la biblioteca vive aparte, dentro del mismo
directorio de pruebas que libreta_sim.db -- nunca mezclada con la real.

USO (CLI de prueba, no toca la libreta real salvo --aplicar):
  python3 archivo_biblioteca.py --simular              -> clasifica un
                                                            ticket sintético,
                                                            no escribe
  python3 archivo_biblioteca.py --simular --aplicar     -> además archiva
                                                            en biblioteca_sim
                                                            y libreta_sim.db
"""

import hashlib
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from libreta import (  # noqa: E402
    DIR_PRUEBAS,
    DISCO_EXTERNO,
    RUTAS,
    _verificar_disco_de_pruebas,
    entorno_activo,
)

CATEGORIAS = {"ticket", "familiar", "escuela", "contenido", "otro"}

# Carpetas fijas del árbol E2 (las que no dependen de datos de la foto; las
# dinámicas -- finanzas/AAAA-MM, familia/AAAA, escuela/<materia>,
# contenido/material/<slug>, proyectos/<nombre> -- se crean sobre la marcha).
_SUBCARPETAS_FIJAS = [
    "escuela", "finanzas", "finanzas/reportes", "familia", "contenido",
    "contenido/guiones", "contenido/publicados", "proyectos", "inbox",
]

BIBLIOTECA_ROOT = {
    "real": DISCO_EXTERNO / "biblioteca",
    "simulacion": DIR_PRUEBAS / "biblioteca_sim",
}


class ClasificacionInvalida(ValueError):
    """Los datos crudos del clasificador no se pudieron normalizar."""


@dataclass
class Clasificacion:
    categoria: str
    fecha: Optional[str] = None
    comercio: Optional[str] = None
    monto_mxn: Optional[float] = None
    categoria_gasto: Optional[str] = None
    materia: Optional[str] = None
    nota: Optional[str] = None


# Firma del puerto inyectable: foto (bytes) -> dict crudo del clasificador
# de vision. La implementación real está PENDIENTE -- ver docstring arriba.
ExtractorClasificador = Callable[[bytes], dict]


def _validar_fecha_iso(texto: str) -> None:
    try:
        datetime.strptime(texto, "%Y-%m-%d")
    except ValueError as exc:
        raise ClasificacionInvalida(
            f"fecha no es ISO 8601 (AAAA-MM-DD): {texto!r}"
        ) from exc


def clasificar(datos: dict) -> Clasificacion:
    """dict crudo del clasificador de vision -> Clasificacion normalizada.

    Pura (sin red, sin disco): valida y separa por categoría para que el
    resto del pipeline decida el destino sin volver a interpretar nada.
    """
    categoria = str(datos.get("categoria", "")).strip().lower()
    if categoria not in CATEGORIAS:
        raise ClasificacionInvalida(
            f"categoría no reconocida: {categoria!r} (válidas: {sorted(CATEGORIAS)})"
        )
    if categoria == "ticket":
        monto_raw = datos.get("monto_mxn")
        if monto_raw is None:
            raise ClasificacionInvalida("ticket sin monto_mxn")
        try:
            monto = float(monto_raw)
        except (TypeError, ValueError) as exc:
            raise ClasificacionInvalida(f"monto_mxn inválido: {monto_raw!r}") from exc
        if monto <= 0:
            raise ClasificacionInvalida(f"monto_mxn debe ser > 0: {monto}")
        fecha = (str(datos.get("fecha") or "")).strip() or None
        if fecha:
            _validar_fecha_iso(fecha)
        return Clasificacion(
            categoria=categoria,
            fecha=fecha,
            comercio=(str(datos.get("comercio") or "")).strip() or None,
            monto_mxn=monto,
            categoria_gasto=(str(datos.get("categoria_gasto") or "")).strip() or "otro",
        )
    if categoria == "escuela":
        return Clasificacion(
            categoria=categoria,
            materia=(str(datos.get("materia") or "")).strip() or None,
        )
    return Clasificacion(
        categoria=categoria,
        nota=(str(datos.get("nota") or "")).strip() or None,
    )


def _slug(texto: str) -> str:
    normal = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    normal = re.sub(r"[^a-zA-Z0-9]+", "_", normal).strip("_").lower()
    return normal or "sin_nombre"


def raiz_biblioteca(entorno: Optional[str] = None) -> Path:
    ent = entorno_activo(entorno)
    return BIBLIOTECA_ROOT[ent]


def crear_arbol_biblioteca(entorno: Optional[str] = None) -> Path:
    """mkdir -p de las carpetas fijas de E2. Idempotente."""
    ent = entorno_activo(entorno)
    raiz = BIBLIOTECA_ROOT[ent]
    if str(raiz).startswith(str(DISCO_EXTERNO)):
        _verificar_disco_de_pruebas()
    for sub in _SUBCARPETAS_FIJAS:
        (raiz / sub).mkdir(parents=True, exist_ok=True)
    return raiz


def ruta_destino(clasificacion: Clasificacion, raiz: Path, ahora: datetime) -> Path:
    """Carpeta del árbol E2 que le toca a esta clasificación.

    E1: el destino depende SOLO de `clasificacion.categoria` (lo que dijo el
    clasificador de entrada) y, para tickets, de la fecha del ticket -- nunca
    de cuándo se procesa ni de la edad del archivo.
    """
    cat = clasificacion.categoria
    if cat == "ticket":
        mes = (clasificacion.fecha or ahora.strftime("%Y-%m-%d"))[:7]
        return raiz / "finanzas" / mes
    if cat == "familiar":
        return raiz / "familia" / ahora.strftime("%Y")
    if cat == "escuela":
        materia = _slug(clasificacion.materia) if clasificacion.materia else "sin_materia"
        return raiz / "escuela" / materia
    if cat == "contenido":
        return raiz / "contenido" / "material"
    return raiz / "inbox"


def _hash_archivo(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


def _nombre_archivo(ruta_origen: Path, hash_: str, ahora: datetime) -> str:
    ts = ahora.strftime("%Y%m%dT%H%M%S")
    ext = ruta_origen.suffix.lower() or ".bin"
    return f"{ts}_{hash_[:8]}{ext}"


def archivar_foto(
    conn: sqlite3.Connection,
    ruta_origen: Path,
    clasificacion: Clasificacion,
    entorno: Optional[str] = None,
    *,
    ahora: Optional[datetime] = None,
) -> dict:
    """Copia `ruta_origen` a la biblioteca permanente y la indexa.

    Nunca borra el original -- para fotos familiares, Arturo las borra del
    iPhone él mismo cuando Hermes confirma que ya quedaron guardadas (ver
    `mensaje_confirmacion_familiar`). Si el hash ya existe, no duplica.
    Si la categoría es "ticket", además registra el gasto en `gastos` con
    `evidencia_id` apuntando a esta foto (OT-7 paso 2).
    """
    ruta_origen = Path(ruta_origen)
    if not ruta_origen.is_file():
        raise FileNotFoundError(f"no existe: {ruta_origen}")
    ent = entorno_activo(entorno)
    raiz = crear_arbol_biblioteca(ent)
    ahora = ahora or datetime.now()
    hash_ = _hash_archivo(ruta_origen)

    existente = conn.execute(
        "SELECT id, filepath FROM archivos WHERE hash_sha256 = ?", (hash_,)
    ).fetchone()
    if existente:
        return {"duplicado": True, "id": existente[0], "filepath": existente[1]}

    carpeta = ruta_destino(clasificacion, raiz, ahora)
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / _nombre_archivo(ruta_origen, hash_, ahora)
    shutil.copy2(ruta_origen, destino)

    with conn:
        cur = conn.execute(
            "INSERT INTO archivos "
            "(categoria, filepath, hash_sha256, retention_class, origen_nombre, nota) "
            "VALUES (?,?,?,?,?,?)",
            (clasificacion.categoria, str(destino), hash_, "permanent",
             ruta_origen.name, clasificacion.nota),
        )
        archivo_id = cur.lastrowid

        resultado = {
            "duplicado": False, "id": archivo_id, "filepath": str(destino),
            "categoria": clasificacion.categoria,
        }

        if clasificacion.categoria == "ticket":
            fecha = clasificacion.fecha or ahora.strftime("%Y-%m-%d")
            cur2 = conn.execute(
                "INSERT INTO gastos "
                "(fecha, monto_mxn, categoria, descripcion, comercio, evidencia_id) "
                "VALUES (?,?,?,?,?,?)",
                (fecha, clasificacion.monto_mxn, clasificacion.categoria_gasto,
                 f"ticket {clasificacion.comercio or 'sin comercio'}",
                 clasificacion.comercio, archivo_id),
            )
            resultado["gasto_id"] = cur2.lastrowid

    return resultado


def mensaje_confirmacion_familiar(n: int) -> str:
    """OT-7 paso 4: confirmación explícita para que Arturo sepa que ya
    puede borrar del iPhone -- nunca se asume, siempre se le dice."""
    plural = "foto" if n == 1 else "fotos"
    return f"📸 Guardadas {n} {plural} en la biblioteca familiar. Ya puedes borrarlas del iPhone."


def _extractor_simulado_ticket() -> dict:
    """Dato de PRUEBA (r.20: escenario simulado, solo laboratorio)."""
    return {
        "categoria": "ticket", "fecha": "2026-08-03", "comercio": "Gasolinera Pemex",
        "monto_mxn": 450.00, "categoria_gasto": "gasolina",
    }


def main():
    if "--simular" not in sys.argv:
        print("uso: python3 archivo_biblioteca.py --simular [--aplicar]")
        sys.exit(2)
    entorno = entorno_activo("simulacion")
    datos = _extractor_simulado_ticket()
    clasif = clasificar(datos)
    print(f"Clasificado como: {clasif.categoria} — ${clasif.monto_mxn} MXN "
          f"en {clasif.comercio} ({clasif.categoria_gasto}) — dato SIMULADO (r.20)")

    if "--aplicar" in sys.argv:
        ruta_foto = Path(tempfile.gettempdir()) / "archivo_biblioteca_ticket_simulado.jpg"
        ruta_foto.write_bytes(b"FOTO SIMULADA DE TICKET -- r.20, no es una foto real")
        conn = sqlite3.connect(str(RUTAS[entorno]))
        conn.execute("PRAGMA foreign_keys = ON")
        resultado = archivar_foto(conn, ruta_foto, clasif, entorno)
        conn.close()
        print(f"\n✅ archivado en {resultado['filepath']} "
              f"(id={resultado['id']}, gasto_id={resultado.get('gasto_id')}, "
              f"duplicado={resultado['duplicado']})")


if __name__ == "__main__":
    main()
