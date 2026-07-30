"""Limpieza puntual (30 jul 2026, Bloque 3 nocturno): borra las 10 filas
duplicadas de reflexión del 30 de julio en memoria_semantica.db, dejando
solo las 5 del source_ref correcto ('...:1d:N'). Uso único -- no es una
herramienta de propósito general para borrar chunks."""

import sqlite3
import sys

sys.path.insert(0, "agent")
import sqlite_vec  # noqa: E402

DB_PATH = "/home/arturo/.hermes/memoria_semantica.db"
IDS_A_BORRAR = list(range(1001, 1011))  # 2 tandas viejas, 5 filas cada una


def main() -> None:
    con = sqlite3.connect(DB_PATH)
    con.enable_load_extension(True)
    sqlite_vec.load(con)
    con.enable_load_extension(False)

    cur = con.execute(
        "SELECT id, source_ref FROM chunks WHERE id IN (%s) ORDER BY id"
        % ",".join("?" * len(IDS_A_BORRAR)),
        IDS_A_BORRAR,
    )
    rows = cur.fetchall()
    if len(rows) != len(IDS_A_BORRAR):
        raise SystemExit(f"Esperaba {len(IDS_A_BORRAR)} filas, encontré {len(rows)} -- abortando sin tocar nada.")
    for row_id, source_ref in rows:
        indice = (row_id - 1001) % 5
        if source_ref != f"diario_reflexion:2026-07-30:{indice}":
            raise SystemExit(f"id={row_id} tiene source_ref inesperado ({source_ref!r}) -- abortando sin tocar nada.")

    for table in ("chunks_vec", "chunks_fts", "chunks"):
        con.execute(
            f"DELETE FROM {table} WHERE rowid IN (%s)" % ",".join("?" * len(IDS_A_BORRAR)),
            IDS_A_BORRAR,
        )
    con.commit()

    restantes = con.execute(
        "SELECT COUNT(*) FROM chunks WHERE source='reflexion' AND created_at LIKE '2026-07-30%'"
    ).fetchone()[0]
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.close()

    print(f"Borradas {len(IDS_A_BORRAR)} filas. Quedan {restantes} filas de reflexión del 30 jul (esperado: 5).")
    print(f"integrity_check: {integrity}")
    if restantes != 5 or integrity != "ok":
        raise SystemExit("Algo no cuadra -- revisar antes de dar por cerrado.")


if __name__ == "__main__":
    main()
