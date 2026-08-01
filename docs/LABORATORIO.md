# EL LABORATORIO DE HERMES — manual operativo

**Regla que lo obliga: `docs/HAS.md` §F11 (separación de entornos).**
**Por qué existe: `docs/HAS.md` §B12 (los tres problemas concretos).**
**Creado 31 jul 2026. Consumidor principal: Claude Code / Hermes. Arturo lo lee si quiere.**

---

## En una frase

Un Hermes gemelo dentro de un contenedor Docker, con datos falsos o restaurados,
donde se puede **romper todo** sin que la vida real de Arturo se entere.

## Los tres trabajos que hace (HAS §B12)

1. **Probar que los respaldos de verdad restauran.** Un respaldo sin restaurar es
   una promesa, no un respaldo.
2. **Simular semanas completas de la vida de Arturo** — los cinco roles del
   mandato — sin ensuciar sus finanzas, su memoria ni su agenda reales.
3. **Ensayar cambios peligrosos** (migraciones, dependencias, arquitectura) antes
   de que toquen producción.

---

## ESTADO REAL HOY (31 jul 2026, 18:40) — leer antes de creer que esto ya funciona

Verificado con `docker images` / `docker ps -a` / `docker volume ls`:

```
IMAGE      ID   DISK USAGE   CONTENT SIZE   EXTRA      <- vacío
CONTAINER ID   IMAGE   ...   NAMES                      <- vacío
DRIVER    VOLUME NAME                                   <- vacío
```

- **Docker: instalado y funcionando.** v29.1.3, compose v2.40.3, buildx 0.30.1,
  grupo `docker` activo para el usuario `arturo` (verificado 31 jul 15:06).
- **La imagen NUNCA se ha construido.** No hay imagen, ni contenedor, ni volumen.
- **`docker-compose.lab.yml`: escrito, nunca ejecutado.** Es el diseño correcto
  del laboratorio, pero todavía no ha corrido ni una vez.
- **Espacio en `/`: 46 GB libres de 109 GB.** Suficiente para construir, pero la
  construcción es pesada (imagen con s6-overlay, Playwright, Node y el venv de
  Python). Revisar `df -h /` antes de construir.

**Nada de lo de abajo está probado todavía.** Los comandos son el plan; la
primera corrida real es la que los valida (HAS §F8: sin evidencia pegada, esto
está `en curso`, no `cerrado`).

---

## Cómo se usa

### Construir la imagen (una vez, o tras cambiar el `Dockerfile`)

```bash
cd ~/.hermes/hermes-agent
docker compose -f docker-compose.lab.yml build
```

Tarda. Es normal la primera vez.

### Entrar al laboratorio

```bash
HERMES_UID=$(id -u) HERMES_GID=$(id -g) \
  docker compose -f docker-compose.lab.yml run --rm lab
```

Deja una shell dentro del contenedor. `HERMES_HOME` es `/opt/data`, que vive en
el volumen aislado `hermes-lab-data` — **no** en `~/.hermes`.

### Destruir el laboratorio (contenedor + volumen + datos falsos)

```bash
docker compose -f docker-compose.lab.yml down -v
```

La `-v` es la que importa: borra el volumen. **Sin `-v` los datos simulados
sobreviven a la siguiente corrida** y contaminan la prueba de mañana con la
basura de la de hoy.

---

## Trabajo 1 — Verificar un respaldo (HAS §F11-b4)

Un respaldo se declara válido **solo** si sobrevive a esto.

1. Descomentar en `docker-compose.lab.yml` el montaje de respaldos en solo
   lectura (`/mnt/seagate/hermes_backups:/respaldos:ro`).
2. Laboratorio limpio: `down -v`, luego entrar.
3. Restaurar dentro del contenedor, desde `/respaldos/<fecha>` hacia `/opt/data`
   (el script de referencia es `scripts/restaurar_hermes.sh`; el respaldo más
   reciente al escribir esto es `/mnt/seagate/hermes_backups/20260731_040925`).
4. **Verificar, no suponer:**
   - `integrity_check` de `state.db` y de `memoria_semantica.db` → debe dar `ok`.
   - Contar filas de las tablas que importan y comparar contra el origen.
   - Arrancar Hermes dentro del contenedor y correr el arnés de humo de
     `docs/GUION_PRUEBAS.md`.
5. Pegar la evidencia real en `ESTADO.md` (F8) y destruir el laboratorio.

**Lo que hace válida la prueba:** el respaldo se monta `:ro`. El laboratorio
puede leerlo, nunca escribirlo ni corromperlo.

---

## Trabajo 2 — Simular semanas de la vida de Arturo (HAS §F11-b3, §F11-d)

El más importante, y el que el mandato exige explícitamente
(`MANDATO_ARTURO.md §6`, `VIDA_DE_ARTURO.md`).

**Los cinco roles que hay que encarnar:** estudiante universitario · creador de
contenido · trabajador · inversionista · usuario cotidiano.

**Materia prima de la simulación** (toda inventada, toda desechable): decenas de
correos, documentos, imágenes, tareas escolares, pagos, gastos, ingresos,
recordatorios, eventos inesperados, sesiones de trading, generación de contenido,
cambios de horario. Sus ejemplos textuales: salir al cine, dejar a Hermes en
trading mientras trabaja, llegar y reportar *"hoy gané esto pero gasté 300 pesos"*.

**Base realista, no inventada de la nada:** la semana real de Arturo está en
`VIDA_DE_ARTURO.md` ("Plan de Batalla Romano") — escuela, gym con rutina partida
de 6 días, trabajo 18:00–22:30, grabación los martes 20:00–22:00, planeación
jueves tarde y domingo mañana. Una simulación que ignore esa estructura no prueba
nada útil.

**Reloj virtual:** `HERMES_FECHA_SIMULADA` (mismo mecanismo que ya usa
`scripts/libreta.py`) permite correr un mes simulado en una tarde. Sin él, "una
semana completa" tardaría una semana.

**Al terminar: `down -v`, siempre.** Un solo gasto inventado que llegue a las
finanzas reales de Arturo es un incidente de F9, no un descuido.

**Ojo con las llaves (HAS §F11-b6):** una simulación de meses con las credenciales
reales puede quemar cuota o presupuesto sin que nadie lo note, y el techo
operativo declarado es de $20 MXN/mes de uso real. El laboratorio arranca sin el
`.env` de producción a propósito.

---

## Trabajo 3 — Ensayar cambios peligrosos (HAS §F11-b1)

**El caso concreto que viene: las Fases 12-14.**

`VIDA_DE_ARTURO.md` documenta el cuello de botella real — *"manuales sin
libreta"*: Hermes tiene las skills de finanzas, salud y YouTube, pero en las 27
tablas de `state.db` no existe ninguna de `gastos`, `ingresos`, `ahorro`, `peso`,
`entrenamientos`, `horario`, `guiones`, `citas`.

Crear esas tablas es una **migración de esquema sobre la base que guarda su
vida**. Secuencia obligatoria (F11-b1 + F7.2 juntas):

1. Migración numerada en `~/.hermes/migrations/`, solo aditiva.
2. **Aplicarla en el laboratorio**, sobre una copia restaurada del `state.db`
   real.
3. **Cargarle encima meses de datos simulados** — el punto no es que la migración
   corra, es ver si el esquema aguanta el uso antes de tener datos reales que ya
   no se pueden tirar.
4. Verificar: `integrity_check`, consultas reales, y las skills de finanzas/salud
   leyendo y escribiendo de verdad contra las tablas nuevas.
5. Solo entonces, producción — con aprobación de Arturo (F7.2) y evidencia pegada.

Mismo procedimiento para: dependencias nuevas, actualizaciones, cambios de
arquitectura, y cualquier cosa que en producción no se pueda deshacer.

---

## Las trampas (cada una es un error que ya casi se comete)

| Trampa | Por qué duele | Qué hacer |
|---|---|---|
| Usar `docker-compose.yml` para probar | Monta `~/.hermes:/opt/data` — las pruebas correrían **sobre los datos reales de Arturo**. Es exactamente lo que el laboratorio evita. | Usar siempre `-f docker-compose.lab.yml` |
| `down` sin `-v` | El volumen sobrevive; los datos falsos de hoy contaminan la prueba de mañana | `down -v`, siempre |
| Conectar el bot token real de Telegram | Dos procesos peleando por `getUpdates` **tumban el gateway real de Arturo** | Cuenta QA, o el arnés interno |
| `network_mode: host` | Colisiona con el gateway real que ya escucha en esta laptop | Red bridge (lo que ya trae el compose del lab) |
| Montar el `.env` de producción | Llaves reales = dinero real quemándose en un bucle de simulación | `.env.lab` con llaves de prueba o modelos gratuitos |
| Dar por buena una restauración porque "corrió sin error" | Correr no es restaurar bien | `integrity_check` + conteo de filas + arnés de humo |

---

## Lo que el laboratorio NO reemplaza

- **Los tests unitarios y el arnés interno** siguen corriendo en desarrollo, sin
  contenedor. El laboratorio es para lo que necesita un Hermes *completo* vivo.
- **La evidencia final de cierre de un bloque** sigue siendo Telegram real (F9,
  operación de rutina) — el laboratorio valida antes, no sustituye la prueba
  final en producción.
- **El laboratorio de trading (B4/OT-10)** es otra cosa: ese usa el testnet de
  Binance (dinero falso, mercado real) para la estrategia. Mismo principio, dos
  laboratorios distintos.
