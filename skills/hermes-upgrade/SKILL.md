---
name: hermes-upgrade
description: "Procedimiento completo y verificado para actualizar Hermes a una version mas nueva del framework upstream (NousResearch/hermes-agent), sin perder ninguna personalizacion (Bloque S, la boveda, Tarea E, memoria QA, etc.) y sin arriesgar produccion."
version: 1.0.0
platforms: [linux]
metadata:
  hermes:
    tags: [ops, mantenimiento, actualizacion, rebase, HAS-Fase-2]
    related_skills: []
---

# hermes-upgrade: actualizar Hermes sin cirugia

## Por que existe esta skill

HAS Fase 2 (Blindaje y actualizacion) lo dice explicito: el objetivo no es
solo actualizar una vez, es que **la proxima actualizacion sea un
procedimiento, no una cirugia**. Este documento es ese procedimiento,
verificado en vivo el 26-27 jul 2026 (rebase real de 27 commits propios
sobre 2,489 commits de upstream, mas un ensayo real con 678 commits nuevos
que aparecieron DURANTE esa misma sesion).

**Regla de oro, no negociable:** todo esto pasa en un worktree aislado
(`~/hermes-019` o el que se cree la vez que toque). `~/.hermes/hermes-agent`
(produccion) nunca se toca hasta el Bloque 6 final, con Arturo presente.

## Cuando correr esto

- Cuando `has_progress.py` o una revision manual detecte que
  `upstream-main` esta a mas de ~50-100 commits de `arturo/base`.
- Antes de empezar cualquier fase nueva que dependa de una version mas
  reciente del framework.
- Como ensayo periodico (Bloque 5 de abajo) aunque no se vaya a promover
  a produccion todavia -- detecta conflictos temprano, cuando son chicos.

## BLOQUE 1 — Preparacion (aislado, sin riesgo)

```bash
cd ~/hermes-019   # o crea un worktree nuevo si este ya no existe:
# git worktree add ~/hermes-019 arturo/base

git fetch origin main
git log --oneline upstream-main..origin/main | wc -l   # cuantos commits nuevos hay
git branch -f upstream-main origin/main                # mueve el tracking, no toca arturo/base
```

Revisa `df -h /tmp` antes de arrancar si ha pasado tiempo desde la ultima
limpieza (ver Bloque AI en `docs/BLOQUES.md` — un `/tmp` lleno rompe Bash
completo, no solo las pruebas).

## BLOQUE 2 — El rebase

```bash
git checkout arturo/base
git rebase upstream-main
```

Cada conflicto, en `docs/MIGRATION_LOG.md` (formato ya establecido, ver el
del 26 jul): que commit, que archivos, que se eligio y por que. **Nunca
"tome lo que parecia mas nuevo"** — para cada conflicto hay que entender
QUE hace cada lado antes de decidir.

### Archivos "punto caliente" conocidos (based on 3 rebases reales)

- `plugins/platforms/telegram/adapter.py` — conflicto en LOS 3 rebases
  reales hechos hasta ahora. Upstream lo toca seguido (UI del picker,
  botones). Revisar con calma cada vez. **Patrón real ya visto (27
  jul): upstream reorganiza el layout de botones (2x2 vs fila única) Y
  nuestro propio commit de i18n traduce las etiquetas al español --
  NO compiten, se combinan los dos (layout de upstream + texto en
  español), nunca hay que descartar uno. Si esto vuelve a pasar, la
  prueba `tests/gateway/test_telegram_approval_buttons.py` casi
  seguro necesita que le actualices las etiquetas hardcodeadas en
  inglés a español -- no es una regresión real, es la prueba de
  upstream sin traducir.**
- `agent/turn_context.py`, `agent/turn_finalizer.py` — aqui viven Bloque S
  (compresion/escalada) y Bloque AF (persistencia). Upstream tiene su
  propio sistema de compresion/reintentos que puede chocar con supuestos
  de Bloque S de formas sutiles (ver Bloque 4 mas abajo, S4/S10 — Bloque
  S.1 tuvo un bug real de doble gasto la primera vez que se junto con el
  tope unificado de upstream).
- `tools/approval.py` — Tarea I (HARDLINE_PATTERNS) puede chocar con
  cambios de politica de seguridad de upstream. Si upstream mueve algo a
  una capa distinta, **verificar con `check_all_command_guards` real
  cual es la proteccion vigente antes de asumir regresion** (fue deuda
  tecnica, no bug, la unica vez que paso).
- `hermes_state.py` — verificar si upstream agrega tablas nuevas O SI TU
  PROPIO STATE.DB TIENE TABLAS SIN `CREATE TABLE` EN EL CODIGO (paso real
  el 26 jul: `mensajes_pendientes` existia en produccion sin ningun
  `CREATE TABLE`). Compara `sqlite_master` de produccion contra el schema
  que crea el codigo — no asumas que coinciden.

Si un conflicto se ve grande/delicado (mas de ~100 lineas, o toca
compresion/permisos/persistencia), **detente y pregunta a Arturo antes de
decidir solo** — asi se manejo el conflicto de `hermes_state.py`/
`gateway/run.py` la primera vez.

## BLOQUE 3 — Verificacion de sintaxis (rapida, antes de correr nada pesado)

```bash
find . -name "*.py" -not -path "./node_modules/*" -exec python3 -m py_compile {} \; 2>&1 | grep -v "^$"
```

0 errores esperado. Si algo no compila, es un conflicto mal resuelto —
arreglalo antes de seguir.

## BLOQUE 4 — Suite de smoke tests (`tests/smoke/`)

Ya escrita y verificada (26-27 jul 2026). Correrla:

```bash
venv/bin/python3 -m pytest tests/smoke/ -v
```

Los 10 escenarios (S1-S10), cada uno con assert real:
S1 arranque CLI, S2 arranque gateway (dry-run), S3 slash commands, S4
detector de complejidad, S5 guardias de permisos, S6 cola de mensajes,
S7 tick de curator, S8 lectura MEMORY/USER, S9 pipeline de media, S10
fallback de proveedores (mock). **Deben pasar 100% antes de seguir.**

Si alguno falla, no es "ruido de la suite grande" — son solo 10
escenarios enfocados, cualquier fallo aqui es real y bloquea continuar.

## BLOQUE 4.5 — Suite de tests completa (por bloques chicos, SIEMPRE)

**Regla permanente (ver CLAUDE.md):** nunca correr los ~10,000 tests de
golpe en esta laptop. Fragmentos de ~300 con `timeout` cada uno:

```bash
# Genera la lista de tests de un directorio:
venv/bin/python3 -m pytest tests/hermes_cli/ --collect-only -q > /tmp/collect.txt

# Corre en fragmentos de 300 con timeout automatico (detecta cuelgues
# solo, en vez de adivinar posicion). Ver tests/hermes_cli/conftest.py
# ::_no_real_network si aparecen cuelgues nuevos por llamadas de red no
# mockeadas -- extender el candado ahi, NO en tests/conftest.py (repo-
# wide saca a la luz fallos de otros directorios fuera de este alcance,
# confirmado el 26 jul).
```

Revisa fallos reales con `git stash` + re-correr contra el codigo
anterior al rebase — si fallan identico, son preexistentes, no
regresion. Aisla cada fallo sospechoso corriendolo solo antes de
concluir "contaminacion".

## BLOQUE 5 — Ensayo de la actualizacion siguiente (opcional, recomendado)

Antes de comprometerte al corte real, ensaya en una rama desechable:

```bash
git branch -f rehearsal-upgrade arturo/base
git checkout rehearsal-upgrade
git rebase upstream-main   # observa cuantos commits pasan limpio, donde truena
# ... NO resuelvas el conflicto real aqui si solo quieres el ensayo ...
git rebase --abort
git checkout arturo/base
git branch -D rehearsal-upgrade
```

Esto da una foto real de "que tan doloroso sera la proxima vez" sin
comprometerte a resolverlo ya. Ensayo real del 27 jul: 678 commits
nuevos aparecieron en upstream DURANTE la sesion misma del rebase
anterior -- el ritmo de upstream es alto, no asumas que "ya quedo al
dia" se mantiene mas de unos dias.

## BLOQUE 6 — Corte a produccion (CON ARTURO PRESENTE, nunca solo)

Este es el unico bloque que toca `~/.hermes/hermes-agent` de verdad.

```bash
# 1. Respaldo incremental (antes de tocar nada):
sudo systemctl --user stop hermes-gateway   # o el comando exacto vigente
tar -czf /mnt/seagate/backups/hermes_pre_upgrade_$(date +%Y%m%d).tar.gz ~/.hermes/hermes-agent

# 2. Documenta el rollback ANTES de cambiar nada (no despues):
#    - venv/branch actual: <anotar aqui, ej. venv viejo en ~/.hermes/hermes-agent/venv>
#    - comando exacto de rollback: <anotar>

# 3. Cambia produccion al codigo/venv nuevo (rama arturo/base ya
#    verificada). systemctl --user start hermes-gateway.

# 4. Corre los 10 smoke tests CONTRA PRODUCCION real:
venv/bin/python3 -m pytest tests/smoke/ -v

# 5. Si >=1 falla: rollback INMEDIATO al comando documentado en el paso 2.
#    No "arreglar en caliente" en produccion.

# 6. 24h de observacion real: revisar logs al dia siguiente ANTES de
#    declarar cerrada la fase. No cerrar el mismo dia solo porque los
#    smoke tests pasaron.
```

## Reportar al cerrar

Tabla archivo-por-archivo tocado (destino real vs planeado) +
resultado de los 10 smoke + resultado de la suite completa (contando
real: cuantos pasaron, cuantos preexistentes, cuantos regresion real) —
nunca "se ve bien". Actualizar `docs/ESTADO.md`/`docs/BLOQUES.md`/
`docs/BITACORA_ARTURO.md` con evidencia real, no un resumen vago.
