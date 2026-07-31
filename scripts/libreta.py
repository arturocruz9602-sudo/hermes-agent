#!/usr/bin/env python3
"""
libreta.py — La puerta de entrada a la libreta de Arturo.

Todo lo que escriba o lea datos de su vida pasa por aqui. Dos razones:

1. **Separar simulacion de realidad.** Arturo autorizo el 31 jul 2026 inventar
   datos de prueba y adelantar el reloj, con un limite textual: *"Nunca deben
   contaminar mi informacion real, mi calendario real ni mi memoria
   permanente."* Eso no se cumple con buena voluntad, se cumple con
   arquitectura: son DOS archivos distintos y el entorno decide cual se abre.

2. **Reloj virtual.** Para probar un recordatorio de diciembre no hay que
   esperar a diciembre.

ENTORNOS
    HERMES_ENTORNO=real       -> ~/.hermes/libreta.db  (default; SSD, chica, de uso diario)
    HERMES_ENTORNO=simulacion -> /mnt/seagate/hermes_backups/pruebas/libreta_sim.db
                                  (disco externo: al SSD le quedan ~46 GB)

RELOJ
    HERMES_FECHA_SIMULADA=2026-12-03T08:00  -> hoy() devuelve esa fecha.
    Solo se respeta en el entorno de simulacion: en real se ignora a
    proposito, para que un olvido de variable no escriba fechas falsas en
    los datos de verdad.

USO
    from libreta import Libreta
    with Libreta() as lib:                    # real
        lib.registrar_gasto(185.50, "comida", "tacos")
    with Libreta("simulacion") as lib:        # pruebas
        ...
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))

# El disco externo de 1 TB. Pedido de Arturo el 31 jul 2026: *"si crees que es
# mejor ocupar el disco externo para las pruebas mejor, porque la memoria de la
# HP es ya muy poca"*. Tiene razon -- al SSD del sistema le quedan ~46 GB y las
# corridas de prueba crecen sin control; al externo le sobran ~860 GB.
# Lo REAL se queda en el SSD: es chico, se consulta a diario y no debe depender
# de que el disco externo este conectado.
DISCO_EXTERNO = Path(os.environ.get("HERMES_DISCO_PRUEBAS", "/mnt/seagate"))

# Cuelga de hermes_backups/ y no de la raiz del disco porque /mnt/seagate
# pertenece a root (drwxr-xr-x root:root) y crear ahi exigiria pedirle a Arturo
# otro sudo. hermes_backups/ ya es suyo. Si algun dia la raiz se abre, mover.
DIR_PRUEBAS = DISCO_EXTERNO / "hermes_backups" / "pruebas"

RUTAS = {
    "real": HERMES_HOME / "libreta.db",
    "simulacion": DIR_PRUEBAS / "libreta_sim.db",
}


class EntornoInvalido(ValueError):
    pass


class DiscoDePruebasAusente(RuntimeError):
    pass


def _verificar_disco_de_pruebas() -> None:
    """El externo esta en fstab con 'nofail': si falla, /mnt/seagate existe
    pero vacio y escribir ahi llenaria el SSD sin que nadie se entere. Mejor
    parar en seco que degradarse en silencio (HAS L6/L14).
    """
    if not DISCO_EXTERNO.is_dir():
        raise DiscoDePruebasAusente(
            f"{DISCO_EXTERNO} no existe — el disco externo no esta conectado")
    if not os.path.ismount(str(DISCO_EXTERNO)):
        raise DiscoDePruebasAusente(
            f"{DISCO_EXTERNO} existe pero NO esta montado: escribir ahi llenaria "
            f"el disco del sistema. Conecta el disco externo o define "
            f"HERMES_DISCO_PRUEBAS a otra ruta.")


def entorno_activo(explicito: str | None = None) -> str:
    ent = (explicito or os.environ.get("HERMES_ENTORNO") or "real").strip().lower()
    if ent not in RUTAS:
        raise EntornoInvalido(
            f"entorno '{ent}' no existe; use uno de: {', '.join(sorted(RUTAS))}"
        )
    return ent


def ahora(entorno: str | None = None) -> datetime:
    """La hora actual, o la simulada si estamos en pruebas.

    En 'real' se ignora HERMES_FECHA_SIMULADA a proposito: un olvido de
    variable de entorno no debe poder escribir fechas falsas en datos reales.
    """
    ent = entorno_activo(entorno)
    if ent == "simulacion":
        crudo = os.environ.get("HERMES_FECHA_SIMULADA")
        if crudo:
            try:
                return datetime.fromisoformat(crudo.strip())
            except ValueError as exc:
                raise ValueError(
                    f"HERMES_FECHA_SIMULADA='{crudo}' no es ISO 8601 "
                    f"(ej. 2026-12-03 o 2026-12-03T08:00): {exc}"
                ) from exc
    return datetime.now()


def hoy(entorno: str | None = None) -> str:
    return ahora(entorno).strftime("%Y-%m-%d")


class Libreta:
    """Acceso a la libreta del entorno indicado."""

    def __init__(self, entorno: str | None = None, *, solo_lectura: bool = False):
        self.entorno = entorno_activo(entorno)
        self.ruta = RUTAS[self.entorno]
        self.solo_lectura = solo_lectura
        self._con: sqlite3.Connection | None = None

    # ── ciclo de vida ────────────────────────────────────────────────
    def __enter__(self) -> "Libreta":
        if self.entorno == "simulacion" and str(self.ruta).startswith(str(DISCO_EXTERNO)):
            _verificar_disco_de_pruebas()
        if not self.ruta.exists():
            raise FileNotFoundError(
                f"no existe {self.ruta} — corre: python3 libreta_migrar.py "
                f"--entorno {self.entorno}"
            )
        uri = f"file:{self.ruta}" + ("?mode=ro" if self.solo_lectura else "")
        self._con = sqlite3.connect(uri, uri=True)
        self._con.row_factory = sqlite3.Row
        self._con.execute("PRAGMA foreign_keys = ON")
        return self

    def __exit__(self, *exc) -> None:
        if self._con is not None:
            if exc[0] is None and not self.solo_lectura:
                self._con.commit()
            self._con.close()
            self._con = None

    @property
    def con(self) -> sqlite3.Connection:
        if self._con is None:
            raise RuntimeError("usa la libreta dentro de un 'with'")
        return self._con

    def ahora(self) -> datetime:
        return ahora(self.entorno)

    def hoy(self) -> str:
        return hoy(self.entorno)

    # ── dinero ───────────────────────────────────────────────────────
    def registrar_gasto(self, monto, categoria, descripcion=None, fecha=None) -> int:
        cur = self.con.execute(
            "INSERT INTO gastos (fecha, monto_mxn, categoria, descripcion) VALUES (?,?,?,?)",
            (fecha or self.hoy(), float(monto), categoria, descripcion),
        )
        return cur.lastrowid

    def registrar_ingreso(self, monto, fuente, nota=None, fecha=None) -> int:
        cur = self.con.execute(
            "INSERT INTO ingresos (fecha, monto_mxn, fuente, nota) VALUES (?,?,?,?)",
            (fecha or self.hoy(), float(monto), fuente, nota),
        )
        return cur.lastrowid

    def balance(self, desde=None, hasta=None) -> dict:
        desde = desde or self.ahora().strftime("%Y-%m-01")
        hasta = hasta or self.hoy()
        ing = self.con.execute(
            "SELECT COALESCE(SUM(monto_mxn),0) FROM ingresos WHERE fecha BETWEEN ? AND ?",
            (desde, hasta),
        ).fetchone()[0]
        gas = self.con.execute(
            "SELECT COALESCE(SUM(monto_mxn),0) FROM gastos WHERE fecha BETWEEN ? AND ?",
            (desde, hasta),
        ).fetchone()[0]
        return {"desde": desde, "hasta": hasta, "ingresos": ing,
                "gastos": gas, "saldo": ing - gas}

    def gastos_por_categoria(self, desde=None, hasta=None) -> list[sqlite3.Row]:
        desde = desde or self.ahora().strftime("%Y-%m-01")
        hasta = hasta or self.hoy()
        return self.con.execute(
            "SELECT categoria, SUM(monto_mxn) AS total, COUNT(*) AS n FROM gastos "
            "WHERE fecha BETWEEN ? AND ? GROUP BY categoria ORDER BY total DESC",
            (desde, hasta),
        ).fetchall()

    def meta_ahorro(self, nombre, objetivo=None, fecha_limite=None) -> sqlite3.Row:
        if objetivo is not None:
            self.con.execute(
                "INSERT INTO ahorro_metas (nombre, objetivo_mxn, fecha_limite) VALUES (?,?,?) "
                "ON CONFLICT(nombre) DO UPDATE SET objetivo_mxn=excluded.objetivo_mxn, "
                "fecha_limite=COALESCE(excluded.fecha_limite, fecha_limite)",
                (nombre, float(objetivo), fecha_limite),
            )
        return self.con.execute(
            "SELECT * FROM ahorro_metas WHERE nombre = ?", (nombre,)
        ).fetchone()

    def registrar_pago_recurrente(self, nombre, monto, frecuencia_meses=1,
                                  dia_del_mes=None, nota=None) -> int:
        cur = self.con.execute(
            "INSERT INTO pagos_recurrentes (nombre, monto_mxn, frecuencia_meses, "
            "dia_del_mes, nota) VALUES (?,?,?,?,?) "
            "ON CONFLICT(nombre) DO UPDATE SET monto_mxn=excluded.monto_mxn, "
            "frecuencia_meses=excluded.frecuencia_meses, "
            "dia_del_mes=COALESCE(excluded.dia_del_mes, dia_del_mes), "
            "nota=COALESCE(excluded.nota, nota)",
            (nombre, float(monto), int(frecuencia_meses), dia_del_mes, nota),
        )
        return self.con.execute(
            "SELECT id FROM pagos_recurrentes WHERE nombre = ?", (nombre,)
        ).fetchone()["id"]

    def registrar_pago_hecho(self, nombre, fecha=None) -> None:
        """Marca cuando se pago un recurrente, para calcular el proximo ciclo."""
        self.con.execute(
            "UPDATE pagos_recurrentes SET ultimo_pago = ? WHERE nombre = ?",
            (fecha or self.hoy(), nombre),
        )

    def pagos_recurrentes_por_vencer(self, dentro_de_dias=7) -> list[sqlite3.Row]:
        """Recurrentes cuyo ultimo_pago + frecuencia cae dentro de la ventana.

        Uno sin ultimo_pago registrado se reporta siempre (no hay desde donde
        contar el ciclo) para que Arturo lo confirme una vez y ya quede fijo.
        """
        hoy = self.hoy()
        return self.con.execute(
            "SELECT *, "
            "  CASE WHEN ultimo_pago IS NULL THEN NULL "
            "       ELSE date(ultimo_pago, '+' || frecuencia_meses || ' months') "
            "  END AS proximo_pago "
            "FROM pagos_recurrentes WHERE activo = 1 AND ("
            "  ultimo_pago IS NULL"
            "  OR date(ultimo_pago, '+' || frecuencia_meses || ' months') "
            "     <= date(?, '+' || ? || ' days')"
            ") ORDER BY proximo_pago IS NULL DESC, proximo_pago",
            (hoy, int(dentro_de_dias)),
        ).fetchall()

    # ── el negocio de reventa (taqueria) ────────────────────────────────
    def registrar_compra_negocio(self, costo, producto="refresco", unidad="reja",
                                 fecha=None, nota=None) -> int:
        cur = self.con.execute(
            "INSERT INTO negocio_compras (fecha, producto, unidad, costo_mxn, nota) "
            "VALUES (?,?,?,?,?)",
            (fecha or self.hoy(), producto, unidad, float(costo), nota),
        )
        return cur.lastrowid

    def registrar_venta_negocio(self, unidades, precio_unitario=20, producto="refresco",
                                fecha=None, nota=None) -> int:
        cur = self.con.execute(
            "INSERT INTO negocio_ventas (fecha, producto, unidades, "
            "precio_unitario_mxn, nota) VALUES (?,?,?,?,?)",
            (fecha or self.hoy(), producto, int(unidades), float(precio_unitario), nota),
        )
        return cur.lastrowid

    def margen_negocio(self, producto="refresco", desde=None, hasta=None) -> dict:
        """Cuanto se gasto en comprar vs. cuanto entro por vender, en el rango.

        No asume piezas por reja: el patron sale de cruzar compras y ventas
        reales en el tiempo, no de una cifra fija de entrada.
        """
        desde = desde or self.ahora().strftime("%Y-%m-01")
        hasta = hasta or self.hoy()
        gastado = self.con.execute(
            "SELECT COALESCE(SUM(costo_mxn),0), COUNT(*) FROM negocio_compras "
            "WHERE producto = ? AND fecha BETWEEN ? AND ?",
            (producto, desde, hasta),
        ).fetchone()
        vendido = self.con.execute(
            "SELECT COALESCE(SUM(unidades*precio_unitario_mxn),0), "
            "COALESCE(SUM(unidades),0) FROM negocio_ventas "
            "WHERE producto = ? AND fecha BETWEEN ? AND ?",
            (producto, desde, hasta),
        ).fetchone()
        return {
            "desde": desde, "hasta": hasta, "producto": producto,
            "invertido": gastado[0], "rejas_compradas": gastado[1],
            "ingreso": vendido[0], "unidades_vendidas": vendido[1],
            "ganancia": vendido[0] - gastado[0],
        }

    def abonar_meta(self, nombre, monto) -> sqlite3.Row:
        self.con.execute(
            "UPDATE ahorro_metas SET acumulado_mxn = acumulado_mxn + ? WHERE nombre = ?",
            (float(monto), nombre),
        )
        return self.meta_ahorro(nombre)

    # ── tiempo ───────────────────────────────────────────────────────
    def agendar_cita(self, fecha_hora, titulo, lugar=None, nota=None,
                     recordar_min_antes=60) -> int:
        cur = self.con.execute(
            "INSERT INTO citas (fecha_hora, titulo, lugar, nota, recordar_min_antes) "
            "VALUES (?,?,?,?,?)",
            (fecha_hora, titulo, lugar, nota, recordar_min_antes),
        )
        return cur.lastrowid

    def pendientes_de_avisar(self) -> list[sqlite3.Row]:
        """Citas cuya hora de recordatorio ya llego y que no se han avisado.

        Usa el reloj del entorno: en simulacion, el reloj virtual.
        """
        # Los dos lados pasan por datetime() a proposito. SQLite devuelve
        # '2026-08-03 21:00:00' (con espacio) y un ISO trae '2026-08-03T08:00'
        # (con T): comparados como texto, el espacio (0x20) siempre pierde
        # contra la T (0x54), asi que TODA cita del dia siguiente disparaba su
        # aviso hoy, a cualquier hora. Normalizar ambos lados lo arregla.
        ahora_iso = self.ahora().isoformat(timespec="minutes")
        return self.con.execute(
            "SELECT * FROM citas WHERE avisado = 0 "
            "AND datetime(fecha_hora, '-' || recordar_min_antes || ' minutes') "
            "    <= datetime(?) "
            "ORDER BY fecha_hora",
            (ahora_iso,),
        ).fetchall()

    def marcar_avisada(self, cita_id) -> None:
        self.con.execute("UPDATE citas SET avisado = 1 WHERE id = ?", (cita_id,))

    # ── escuela ──────────────────────────────────────────────────────
    def registrar_tarea(self, titulo, materia=None, maestro=None, fecha_entrega=None,
                        origen="arturo", correo_msgid=None, nota=None) -> int | None:
        """Devuelve el id, o None si ese correo ya se habia registrado."""
        try:
            cur = self.con.execute(
                "INSERT INTO tareas_escuela (titulo, materia, maestro, fecha_entrega, "
                "origen, correo_msgid, nota) VALUES (?,?,?,?,?,?,?)",
                (titulo, materia, maestro, fecha_entrega, origen, correo_msgid, nota),
            )
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None  # correo_msgid duplicado: ya estaba anotada

    def tareas_pendientes(self, dentro_de_dias=None) -> list[sqlite3.Row]:
        sql = ("SELECT * FROM tareas_escuela WHERE estado IN ('pendiente','en_curso')")
        params: list = []
        if dentro_de_dias is not None:
            sql += (" AND fecha_entrega IS NOT NULL "
                    "AND fecha_entrega <= date(?, '+' || ? || ' days')")
            params += [self.hoy(), int(dentro_de_dias)]
        sql += " ORDER BY fecha_entrega IS NULL, fecha_entrega"
        return self.con.execute(sql, params).fetchall()

    def marcar_vencidas(self) -> int:
        """Las pendientes cuya fecha ya paso. Devuelve cuantas cambio."""
        cur = self.con.execute(
            "UPDATE tareas_escuela SET estado = 'vencida' "
            "WHERE estado = 'pendiente' AND fecha_entrega IS NOT NULL "
            "AND fecha_entrega < ?",
            (self.hoy(),),
        )
        return cur.rowcount
