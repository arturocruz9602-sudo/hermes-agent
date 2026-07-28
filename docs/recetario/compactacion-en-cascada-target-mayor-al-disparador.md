---
fecha: 2026-07-27
autor: claude-code
sintoma_corto: la conversación se compacta 2, 3+ veces seguidas y nunca llega a responder
componente: agent/turn_context.py (preflight de compresión de contexto)
---

## Síntoma

Un turno entra en compactaciones repetidas ("Sesión comprimida 2
veces", "3 veces", ...) sin nunca completar y responder. En logs
(`agent/conversation_compression.py`) se ve el contador
`compression_count` subiendo cada turno sin bajar nunca de cierto
umbral.

## Diagnóstico

Causa raíz, confirmada leyendo `agent/turn_context.py`: cuando la
compresión se dispara por un umbral SECUNDARIO más bajo que el
principal (en este proyecto, `ESCALATION_SAFE_TRIGGER_TOKENS` — un
umbral absoluto para proteger al proveedor de respaldo más chico de la
escalera, no relacionado con el contexto del modelo primario), el
TARGET real de la compresión seguía calculándose sobre el umbral
PRIMARIO (`threshold_tokens * summary_target_ratio`), que da un número
muy por ENCIMA del umbral secundario que disparó la compresión. Cada
pasada "tenía éxito" (reducía tokens de forma material) pero nunca
bajaba lo suficiente para dejar de disparar el umbral secundario en el
turno siguiente — bucle de baja intensidad, para siempre, mientras la
sesión se mantuviera sobre ese umbral (que es justo lo que la propia
compresión producía).

Patrón general confirmado como conocido en la comunidad (aunque con un
mecanismo distinto, no idéntico): [Telethon-equivalente para
Telegram-agent frameworks] — issue real
[#53008 de NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent/issues/53008)
("Context Compression Infinite Loop"): modelo auxiliar de compresión
más chico que el umbral causa el mismo síntoma general (compresión que
nunca reduce lo suficiente, se repite sin parar), aunque ahí la causa
es el tamaño del modelo auxiliar, no un umbral secundario propio.

## Solución paso a paso

Cuando el disparo de compresión es por el umbral secundario/de
escalera (no por el del modelo primario), sobreescribir temporalmente
el target real de esa pasada para que apunte por debajo del umbral que
disparó la compresión — no al 20%/N% del umbral primario:

```python
# antes de la(s) pasada(s) de compresión de este turno:
_orig_threshold = compressor.threshold_tokens
if disparo_por_umbral_secundario:
    compressor.threshold_tokens = int(
        TARGET_DESEADO / max(compressor.summary_target_ratio, 0.01)
    )
# ... correr la(s) pasada(s) de compresión ...
# inmediatamente después, SIEMPRE restaurar:
compressor.threshold_tokens = _orig_threshold
```

Restaurar el valor original es obligatorio incluso si algo falla en
medio — un valor de threshold pisado y nunca restaurado afecta a
CUALQUIER otro llamador que comparta el mismo objeto compresor, no
solo a este turno.

## Verificación

Con el fix, la misma sesión de prueba que antes cascadeaba sin fin
completó en una sola pasada de preflight (sin repetir "Sesión
comprimida N veces"), y el turno llegó a intentar la llamada real al
proveedor.

## Cuándo NO aplica

Si la conversación tiene contenido genuinamente enorme dentro de la
ventana protegida reciente (un resultado de herramienta gigante, por
ejemplo) que la compresión normal no toca, el síntoma puede parecerse
pero la causa es distinta — ver el mecanismo de recorte agresivo de
último recurso (`protect_last_n` reducido temporalmente) para ese caso.
