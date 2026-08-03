"""Pruebas de archivo_biblioteca.py (F7-1, OT-7 Bloque 1).

Clava lo que dice el HAS:
  E1 -- el destino (caché vs biblioteca, y dentro de biblioteca, la carpeta)
        lo decide SIEMPRE la categoría del clasificador, nunca el tiempo del
        archivo ni cuándo se procesa.
  E2 -- el árbol de carpetas de biblioteca/ se crea completo y es idempotente.
  OT-7 paso 2 -- un ticket clasificado inserta un gasto con `evidencia_id`
        apuntando a la foto archivada.
  OT-7 paso 4 -- fotos familiares generan el mensaje de confirmación
        explícita antes de que Arturo borre nada de su iPhone.
  r.20 -- "nada permanente se borra por cron": este módulo solo AGREGA
        (archivar_foto nunca borra el original ni sobrescribe un hash ya
        indexado).

Con SQLite real en tmp_path (no en memoria: archivar_foto también escribe al
disco) y el clasificador de vision INYECTADO -- nada de red.
"""

from __future__ import annotations

import importlib
import sqlite3
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

import libreta as libreta_mod  # noqa: E402


@pytest.fixture
def modulo(tmp_path, monkeypatch):
    """archivo_biblioteca reimportado con HERMES_HOME/HERMES_DISCO_PRUEBAS en
    tmp_path -- mismo patrón que test_libreta.py: los caminos son constantes
    de módulo, así que hay que recargar tras fijar las variables de entorno.
    """
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_DISCO_PRUEBAS", str(tmp_path / "externo"))
    monkeypatch.delenv("HERMES_ENTORNO", raising=False)
    (tmp_path / "externo").mkdir(parents=True, exist_ok=True)
    importlib.reload(libreta_mod)
    monkeypatch.setattr(libreta_mod, "_verificar_disco_de_pruebas", lambda: None)

    import archivo_biblioteca as mod
    importlib.reload(mod)
    monkeypatch.setattr(mod, "_verificar_disco_de_pruebas", lambda: None)
    yield mod
    importlib.reload(libreta_mod)


@pytest.fixture
def conn(tmp_path):
    ruta = tmp_path / "libreta_test.db"
    c = sqlite3.connect(str(ruta))
    c.execute("PRAGMA foreign_keys = ON")
    c.execute("""
        CREATE TABLE gastos (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha         TEXT    NOT NULL,
            monto_mxn     REAL    NOT NULL CHECK (monto_mxn > 0),
            categoria     TEXT    NOT NULL,
            descripcion   TEXT,
            recurrente_id INTEGER,
            comercio      TEXT,
            evidencia_id  INTEGER REFERENCES archivos(id)
        )
    """)
    c.execute("""
        CREATE TABLE archivos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria       TEXT NOT NULL CHECK (categoria IN
                                ('ticket','familiar','escuela','contenido','otro')),
            filepath        TEXT NOT NULL UNIQUE,
            hash_sha256     TEXT NOT NULL,
            retention_class TEXT NOT NULL DEFAULT 'permanent'
                                CHECK (retention_class IN ('cache','permanent')),
            origen_nombre   TEXT,
            nota            TEXT,
            creado_en       TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)
    yield c
    c.close()


def _foto(tmp_path, nombre="ticket.jpg", contenido=b"contenido de prueba"):
    p = tmp_path / nombre
    p.write_bytes(contenido)
    return p


# ── clasificar() ──────────────────────────────────────────────────────────

def test_clasificar_ticket_valido(modulo):
    c = modulo.clasificar({
        "categoria": "ticket", "fecha": "2026-08-03",
        "comercio": "Gasolinera Pemex", "monto_mxn": "450.50",
        "categoria_gasto": "gasolina",
    })
    assert c.categoria == "ticket"
    assert c.monto_mxn == 450.50
    assert c.comercio == "Gasolinera Pemex"
    assert c.categoria_gasto == "gasolina"


@pytest.mark.parametrize("categoria", ["familiar", "escuela", "contenido", "otro"])
def test_clasificar_categorias_no_ticket(modulo, categoria):
    c = modulo.clasificar({"categoria": categoria})
    assert c.categoria == categoria
    assert c.monto_mxn is None


def test_clasificar_categoria_desconocida(modulo):
    with pytest.raises(modulo.ClasificacionInvalida):
        modulo.clasificar({"categoria": "factura_marciana"})


def test_clasificar_ticket_sin_monto(modulo):
    with pytest.raises(modulo.ClasificacionInvalida):
        modulo.clasificar({"categoria": "ticket"})


@pytest.mark.parametrize("monto", [0, -10, "no es numero"])
def test_clasificar_ticket_monto_invalido(modulo, monto):
    with pytest.raises(modulo.ClasificacionInvalida):
        modulo.clasificar({"categoria": "ticket", "monto_mxn": monto})


def test_clasificar_ticket_fecha_no_iso(modulo):
    with pytest.raises(modulo.ClasificacionInvalida):
        modulo.clasificar({"categoria": "ticket", "monto_mxn": 100, "fecha": "3-ago-2026"})


def test_clasificar_ticket_categoria_gasto_por_defecto(modulo):
    c = modulo.clasificar({"categoria": "ticket", "monto_mxn": 50})
    assert c.categoria_gasto == "otro"


def test_clasificar_escuela_sin_materia(modulo):
    c = modulo.clasificar({"categoria": "escuela"})
    assert c.materia is None


# ── ruta_destino() -- E1: la categoría manda, nunca el tiempo ─────────────

def test_ruta_destino_ticket_usa_mes_del_ticket_no_de_hoy(modulo):
    from datetime import datetime
    raiz = Path("/biblioteca")
    c = modulo.clasificar({"categoria": "ticket", "monto_mxn": 1, "fecha": "2026-01-15"})
    dest = modulo.ruta_destino(c, raiz, ahora=datetime(2026, 8, 3))
    assert dest == raiz / "finanzas" / "2026-01"


def test_ruta_destino_ticket_sin_fecha_usa_hoy(modulo):
    from datetime import datetime
    raiz = Path("/biblioteca")
    c = modulo.clasificar({"categoria": "ticket", "monto_mxn": 1})
    dest = modulo.ruta_destino(c, raiz, ahora=datetime(2026, 8, 3))
    assert dest == raiz / "finanzas" / "2026-08"


def test_ruta_destino_familiar(modulo):
    from datetime import datetime
    raiz = Path("/biblioteca")
    c = modulo.clasificar({"categoria": "familiar"})
    assert modulo.ruta_destino(c, raiz, datetime(2026, 8, 3)) == raiz / "familia" / "2026"


def test_ruta_destino_escuela_con_materia_hace_slug(modulo):
    from datetime import datetime
    raiz = Path("/biblioteca")
    c = modulo.clasificar({"categoria": "escuela", "materia": "Bases de Datos II"})
    dest = modulo.ruta_destino(c, raiz, datetime(2026, 8, 3))
    assert dest == raiz / "escuela" / "bases_de_datos_ii"


def test_ruta_destino_escuela_sin_materia(modulo):
    from datetime import datetime
    raiz = Path("/biblioteca")
    c = modulo.clasificar({"categoria": "escuela"})
    dest = modulo.ruta_destino(c, raiz, datetime(2026, 8, 3))
    assert dest == raiz / "escuela" / "sin_materia"


def test_ruta_destino_otro_va_a_inbox(modulo):
    from datetime import datetime
    raiz = Path("/biblioteca")
    c = modulo.clasificar({"categoria": "otro"})
    assert modulo.ruta_destino(c, raiz, datetime(2026, 8, 3)) == raiz / "inbox"


# ── crear_arbol_biblioteca() -- E2 ─────────────────────────────────────────

def test_crear_arbol_biblioteca_crea_todas_las_carpetas_fijas(modulo):
    raiz = modulo.crear_arbol_biblioteca("simulacion")
    for sub in modulo._SUBCARPETAS_FIJAS:
        assert (raiz / sub).is_dir(), f"falta {sub}"


def test_crear_arbol_biblioteca_es_idempotente(modulo):
    modulo.crear_arbol_biblioteca("simulacion")
    raiz2 = modulo.crear_arbol_biblioteca("simulacion")  # no debe tronar
    assert raiz2.is_dir()


def test_biblioteca_real_y_simulacion_no_se_mezclan(modulo):
    real = modulo.raiz_biblioteca("real")
    sim = modulo.raiz_biblioteca("simulacion")
    assert real != sim
    assert "externo" in str(sim)


# ── archivar_foto() -- copia, indexa, y ticket registra gasto con evidencia ─

def test_archivar_foto_ticket_registra_gasto_con_evidencia(modulo, conn, tmp_path):
    foto = _foto(tmp_path)
    c = modulo.clasificar({
        "categoria": "ticket", "fecha": "2026-08-03",
        "comercio": "Gasolinera Pemex", "monto_mxn": 450, "categoria_gasto": "gasolina",
    })
    resultado = modulo.archivar_foto(conn, foto, c, "simulacion")

    assert resultado["duplicado"] is False
    assert Path(resultado["filepath"]).is_file()
    assert "finanzas/2026-08" in resultado["filepath"].replace("\\", "/")

    fila = conn.execute(
        "SELECT monto_mxn, categoria, comercio, evidencia_id FROM gastos WHERE id=?",
        (resultado["gasto_id"],),
    ).fetchone()
    assert fila == (450.0, "gasolina", "Gasolinera Pemex", resultado["id"])


def test_archivar_foto_no_ticket_no_toca_gastos(modulo, conn, tmp_path):
    foto = _foto(tmp_path, "familia.jpg")
    c = modulo.clasificar({"categoria": "familiar"})
    resultado = modulo.archivar_foto(conn, foto, c, "simulacion")
    assert "gasto_id" not in resultado
    assert conn.execute("SELECT COUNT(*) FROM gastos").fetchone()[0] == 0


def test_archivar_foto_nunca_borra_el_original(modulo, conn, tmp_path):
    foto = _foto(tmp_path)
    c = modulo.clasificar({"categoria": "familiar"})
    modulo.archivar_foto(conn, foto, c, "simulacion")
    assert foto.is_file()


def test_archivar_foto_duplicado_por_hash_no_duplica(modulo, conn, tmp_path):
    foto = _foto(tmp_path, contenido=b"misma foto, dos veces")
    c = modulo.clasificar({"categoria": "otro"})
    r1 = modulo.archivar_foto(conn, foto, c, "simulacion")
    r2 = modulo.archivar_foto(conn, foto, c, "simulacion")

    assert r1["duplicado"] is False
    assert r2["duplicado"] is True
    assert r2["id"] == r1["id"]
    assert conn.execute("SELECT COUNT(*) FROM archivos").fetchone()[0] == 1


def test_archivar_foto_inexistente_truena_claro(modulo, conn, tmp_path):
    c = modulo.clasificar({"categoria": "otro"})
    with pytest.raises(FileNotFoundError):
        modulo.archivar_foto(conn, tmp_path / "no_existe.jpg", c, "simulacion")


def test_archivar_foto_nunca_pisa_el_hash_de_otra_permanente(modulo, conn, tmp_path):
    """r.20 / regla de E1: nada permanente se borra ni se pisa por cron ni
    por reprocesar -- reintentar el mismo archivo es idempotente."""
    foto = _foto(tmp_path, contenido=b"contenido unico")
    c = modulo.clasificar({"categoria": "ticket", "monto_mxn": 10})
    modulo.archivar_foto(conn, foto, c, "simulacion")
    n_antes = conn.execute("SELECT COUNT(*) FROM gastos").fetchone()[0]
    modulo.archivar_foto(conn, foto, c, "simulacion")  # reintento
    n_despues = conn.execute("SELECT COUNT(*) FROM gastos").fetchone()[0]
    assert n_antes == n_despues == 1


# ── mensaje_confirmacion_familiar() -- OT-7 paso 4 ─────────────────────────

def test_mensaje_confirmacion_familiar_singular(modulo):
    assert "1 foto " in modulo.mensaje_confirmacion_familiar(1)


def test_mensaje_confirmacion_familiar_plural(modulo):
    msg = modulo.mensaje_confirmacion_familiar(5)
    assert "5 fotos" in msg
    assert "borrarlas del iPhone" in msg
