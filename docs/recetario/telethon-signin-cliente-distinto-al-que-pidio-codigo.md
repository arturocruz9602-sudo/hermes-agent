---
fecha: 2026-07-27
autor: claude-code
sintoma_corto: Telethon rechaza un código de verificación real y recién enviado con PhoneCodeExpiredError
componente: tools/telegram_userbot.py (login MTProto con Telethon)
---

## Síntoma

Al hacer login de una cuenta de Telegram vía Telethon en dos pasos
(`send_code_request` en una llamada, `sign_in` en otra), el segundo
paso falla con:

```
telethon.errors.rpcerrorlist.PhoneCodeExpiredError: The confirmation
code has expired (caused by SignInRequest)
```

...incluso con un código recién llegado (segundos de diferencia),
reloj del sistema sincronizado (`timedatectl status` → `System clock
synchronized: yes`), y repitiéndolo varias veces con códigos nuevos
cada vez.

## Diagnóstico

Causa raíz real: `send_code_request()` y `sign_in()` se llamaban desde
**dos objetos `TelegramClient` distintos** — cada uno con su propia
`StringSession()` anónima nueva, conectando y desconectando por
separado. Telegram invalida el `phone_code_hash` cuando el `sign_in`
llega desde una sesión/conexión distinta a la que pidió el código,
aunque no haya pasado el tiempo real de expiración.

Confirmado contra un reporte real idéntico en la comunidad de
Telethon: [issue #799](https://github.com/LonamiWebs/Telethon/issues/799)
("the confirmation code has expired when using two different
clients").

**Descartado, con evidencia, antes de encontrar la causa real:**
- Reloj desincronizado — `timedatectl status` confirmó sincronizado.
- Contraseña de la bóveda equivocada — leyendo el código, `sign_in()`
  corre ANTES de que se toque la contraseña de la bóveda; imposible
  que sea la causa de este error específico.
- Demora humana en relayar el código — se probó con un script que
  pre-cargaba el `phone_code_hash` y ejecutaba `sign_in` al instante
  de recibir el código por parámetro; falló igual.

## Solución paso a paso

Mantener la MISMA conexión/cliente entre pedir y confirmar el código,
en vez de crear una nueva para cada paso:

```python
client = TelegramClient(StringSession(), api_id, api_hash)
await client.connect()
sent = await client.send_code_request(phone_number)
# ... esperar el código (puede ser un input(), un poll de archivo, etc.
#     -- lo que NO puede pasar es reconectar con un client nuevo) ...
await client.sign_in(phone=phone_number, code=code,
                      phone_code_hash=sent.phone_code_hash)
session_string = client.session.save()
await client.disconnect()
```

Si el flujo necesita partirse en dos llamadas de función separadas
(p.ej. para no bloquear con `input()` en una llamada de herramienta
automatizada), guardar el cliente conectado en una variable a nivel de
módulo entre ambas llamadas, en vez de reconectar. Ver la
implementación real en `tools/telegram_userbot.py`
(`_pending_login_client`, funciones `start_login`/`complete_login`).

## Verificación

Login real completado: sesión guardada en la bóveda
(`vault_list_services` la lista), reconexión real con esa sesión y
`await client.get_me()` devolvió la identidad esperada (id, nombre,
teléfono reales de la cuenta).

## Cuándo NO aplica

Si el error aparece con un código que de verdad tiene minutos de
antigüedad (no segundos), sí puede ser expiración real por tiempo —
esta receta es específica al patrón "dos clientes distintos", no una
expiración genuina.
