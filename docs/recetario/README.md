# Recetario — biblioteca de soluciones

Creado por HAS v1.5, sección F10. Una receta = un problema real ya
resuelto, en formato reusable — para que la próxima vez que aparezca
algo parecido (a Hermes o a Claude) no haya que razonarlo desde cero.

## Reglas (F10 del HAS, resumen — ver `docs/HAS.md` para el texto completo)

- **Claude Code tiene obligación de cierre**: todo problema no trivial
  que resuelva genera su receta en la MISMA sesión donde se resolvió.
- **Hermes consulta el recetario** (vía el índice semántico, cuando la
  Fase 4 lo conecte) antes de razonar un problema desde cero, y puede
  aplicar recetas cuyos pasos estén dentro de sus permisos.
- **Si Hermes resuelve algo nuevo por su cuenta**, también escribe su
  receta — el recetario aprende de los dos agentes, no solo de Claude.
- Métrica mensual: % de problemas resueltos por receta/Hermes sin
  tocar a Claude — la medida real de "necesitar cada vez menos ayuda
  externa".

## Formato de una receta

Un archivo `.md` por receta, nombre descriptivo en kebab-case
(`telethon-signin-dos-clientes-distintos.md`, no `receta-1.md`).
Front-matter YAML + cuerpo:

```yaml
---
fecha: 2026-07-27
autor: claude-code | hermes
sintoma_corto: una línea, lo que se ve desde afuera
componente: ruta o módulo principal afectado
---
```

Cuerpo, en este orden:

1. **Síntoma** — qué se observó, tal cual (mensaje de error real, log
   real, comportamiento real). Nunca parafrasear un error citando su
   texto exacto.
2. **Diagnóstico** — la causa raíz real, cómo se confirmó (comando,
   evidencia), y qué NO era (hipótesis descartadas con su evidencia,
   si las hubo — ahorra tiempo la próxima vez).
3. **Solución paso a paso** — reproducible, con comandos/código real,
   no descripciones vagas.
4. **Verificación** — cómo se confirmó que sí quedó resuelto (no "se
   ve bien").
5. **Cuándo NO aplica** — si la causa raíz tiene condiciones
   específicas, decirlas explícitas para que no se aplique la receta a
   un síntoma parecido pero de causa distinta.

## Herramienta: `scripts/recetario.py`

No hay que grepear el directorio a mano ni escribir el front-matter de
memoria — el módulo hace las tres operaciones del ciclo de F10:

```bash
# consultar ANTES de razonar un problema desde cero (F10-b)
python3 scripts/recetario.py buscar "telethon phone code expired"

# validar el formato (candado que usa nueva_receta() y la prueba de humo)
python3 scripts/recetario.py validar

# crear una receta nueva ya validada (F10-a/c) — nunca escribe un
# archivo que no cumpla el formato de arriba
python3 scripts/recetario.py nueva --nombre mi-problema-nuevo \
  --autor claude-code --sintoma-corto "..." --componente "..." \
  --sintoma-archivo /tmp/sintoma.txt --diagnostico-archivo /tmp/diag.txt \
  --solucion-archivo /tmp/sol.txt --verificacion-archivo /tmp/ver.txt \
  --cuando-no-aplica-archivo /tmp/na.txt
```

Igual de importable desde Python (`from recetario import buscar,
nueva_receta, validar_todas`) para Hermes o para cualquier script que
quiera consultar el recetario antes de escalar a Claude/DeepSeek.
Pruebas: `tests/scripts/test_recetario.py`.
