# Bitácora para Arturo

Un registro pensado para TI, no para desarrolladores: por cada arreglo o
mejora real, qué cambia en tu día a día concreto, con un mensaje que
puedes mandar literal para probarlo tú mismo. Se actualiza al cerrar
cada sesión (regla permanente en `CLAUDE.md`).

---

## 26-27 Jul 2026 — Terminé de blindar la actualización a la versión nueva, y encontré 4 fallas reales en el camino

**Qué era esto:** el programa base sobre el que corre Hermes llevaba
más de dos años de mejoras sin que las tuviéramos (2,489 cambios de
distancia). Actualizarlo sin romper nada suyo (la bóveda, el aviso de
DeepSeek, la memoria separada de la cuenta QA) es el "Bloque 1" del
plan de blindaje. Se hizo en una copia aparte de la laptop, sin tocar
nunca el Hermes real que usted usa por Telegram.

**Lo que encontré y arreglé, con evidencia real, no solo "se ve bien":**
1. Un bug real de gasto doble en la parte que resume conversaciones
   largas para que no se saturen — no perdía datos, pero gastaba más
   de la cuenta cuando no debía.
2. Tres pruebas automáticas que se quedaban colgadas para siempre en
   vez de fallar rápido, porque intentaban conectarse a internet real
   (a npm, a GitHub) en una máquina de pruebas sin esa conexión. Ya
   fallan rápido y claro si vuelve a pasar, en vez de trabarse.
3. Una fuga en el registro de eventos de una prueba que contaminaba
   miles de líneas de log de pruebas sin relación — explicaba casi
   todos los "fallos fantasma" que parecían más graves de lo que eran.

**Cómo lo verifiqué:** corrí las casi 10,000 pruebas automáticas que ya
existían, por bloques chicos (para no repetir el incidente del disco
lleno), confirmando cada fallo real contra el código de antes con
`git stash` — no me quedé con el primer número que salió.

**Resultado final:** de 9,576 pruebas, 9,526 pasan, 19 quedan sin
relación con esto (áreas sueltas, documentadas, sin investigar todavía),
y cero cuelgues. Todo respaldado en GitHub.

**Pendiente real antes de mover esto a producción:** copiar ahí el
arreglo del login de la cuenta QA de Telegram (solo existe en el
Hermes real, no en esta copia del rebase) — nada urgente, ya está
anotado.

**Notas de Arturo:**

---

## 24-25 Jul 2026 (noche) — Se me trabó la terminal casi 3 horas; ya está resuelto, y sé qué hacer si vuelve a pasar

**Qué pasó:** de repente no pude correr NINGÚN comando tuyo -- ni algo
tan simple como saludar. Probamos de todo juntos: cambiar de versión
del programa, revisar el "candado" de seguridad, cerrar y abrir
sesiones, entrar por control remoto, reinstalar. Nada servía, y a ti te
tocó hacer un montón de pasos técnicos (SSH, tmux, terminal nueva) que
al final no eran la causa real. Perdimos casi 3 horas.

**Qué era en realidad:** la laptop se quedó sin espacio en una carpeta
temporal (no tu disco duro grande, uno chiquito de trabajo interno) por
2.4 GB de basura acumulada de pruebas viejas que nunca se limpiaron
solas. Sin espacio ahí, yo no podía "anotar" el resultado de ningún
comando -- así que todo se veía roto, aunque el programa en sí estaba
bien.

**Ya está arreglado:** borré esa basura y la terminal volvió a
funcionar de inmediato, sin reiniciar nada. Además dejé dos cambios
para que esto no se repita -- uno ya lo hice yo (un limpiador
automático que corre solo, borra basura de pruebas de más de 2 días,
nunca toca nada en uso), y otro te lo dejé a ti porque necesita tu
contraseña de administrador (agrandar ese espacio temporal) -- los
comandos exactos te los pasé arriba en el chat, cópialos y pégalos tal
cual.

**Cómo lo vas a notar:** en nada de tu uso diario de Hermes por
Telegram -- esto era yo trabajando en la laptop, no una función que tú
uses. Lo único que cambia es que si la terminal se vuelve a trabar así
de raro alguna otra vez, ahora tengo la regla de buscar en internet
primero en vez de perder horas adivinando a ciegas.

**Notas de Arturo:**

---

## 24 Jul 2026 (mediodía) — Arreglé el login de la cuenta QA de Telegram, que se quedaba trabado

**Qué pasó:** cuando se intentaba conectar la cuenta QA de Telegram
(la de pruebas, separada de la tuya), el código se quedaba esperando
que alguien escribiera el código de verificación directo en un teclado
-- algo que no existe cuando lo dispara una herramienta automatizada,
así que simplemente se colgaba sin avisar nada.

**Ya está arreglado:** ahora el login se hace en dos pasos separados
(se pide el código, y luego se completa aparte cuando llega), igual que
ya funciona el emparejamiento por mensaje directo. También reconoce
cuando la cuenta tiene verificación en dos pasos (2FA) en vez de
tronar con un error confuso.

**Nota honesta:** este arreglo se hizo en una sesión anterior y no
alcancé a probarlo contra Telegram real en ese momento (la sesión se
interrumpió). Sí confirmé ahora que las 4 pruebas automatizadas del
código pasan limpio. La próxima vez que se configure la cuenta QA es
cuando se confirma de verdad en vivo -- no es algo que tú actives con
un mensaje, es infraestructura interna para esa cuenta de pruebas.

**Notas de Arturo:**

---

## 24 Jul 2026 (mañana) — Encontré y arreglé un bug real: conversaciones largas duplicaban mensajes

**Qué pasó:** me pediste seguir el plan y arreglar lo que encontrara mal,
no solo reportarlo. Al intentar probar el aviso de DeepSeek, algo no
cuadró — y siguiendo el rastro encontré un bug real: cuando una
conversación se compacta varias veces seguidas (charla larga, mucho uso
seguido), el sistema podía guardar el mismo mensaje tuyo y la misma
respuesta de Hermes **repetidos varias veces** en la base de datos.

**Cómo te afectaba, aunque no lo hubieras notado directamente:** además
de ensuciar el historial, esto podía hacer que una oferta real de
"¿quieres que use DeepSeek para esto?" se cancelara sola, sin que
llegaras a contestarla, porque el sistema de seguridad que evita
despachos accidentales (el mismo que se hizo después del incidente de
julio) confundía esos mensajes duplicados con mensajes nuevos de por
medio.

**Ya está arreglado y probado** (no solo "se ve bien en el código"):
confirmé con evidencia real que antes del arreglo el mismo mensaje
aparecía repetido con el timestamp idéntico, y después del arreglo ya
no. 3 pruebas nuevas más 446 pruebas existentes de todo el sistema de
compactación, todas en verde.

**Actualización — ya se probó con dinero real, tú lo pediste
directamente.** Confirmé de punta a punta que cuando Hermes va a usar
DeepSeek (el modelo de pago), te avisa ANTES de gastar, y te avisa el
costo real DESPUÉS — con una llamada real, no simulada. Costo total de
la prueba: siete diezmilésimas de dólar (básicamente nada). Con esto,
las 4 cosas que faltaban de la Fase 1 original ya están confirmadas.

**Notas de Arturo:**

---

## 24 Jul 2026 (mañana) — Opción 3: la cuenta QA ya tiene su propia memoria, separada de la tuya de verdad

**Qué se arregló:** el hallazgo de esta madrugada (tu memoria y la de la
cuenta QA mezcladas) ya está resuelto. Hablamos las opciones juntos
(hasta preguntaste si no era doble trabajo -- buena pregunta, la
respuesta quedó documentada abajo) y decidimos la más completa: la
cuenta QA ahora escribe a su propio cajón, separado del tuyo de verdad
a nivel de base de datos, no solo con una etiqueta.

**Cómo se ve en tu día a día:** nada cambia para ti -- tu memoria sigue
funcionando exactamente igual que siempre, en los mismos archivos de
siempre. Lo que cambia es que ahora la cuenta QA SÍ puede pedirle a
Hermes que recuerde cosas (antes te hubiera dicho que no lo hicieras)
sin ningún riesgo de que se mezcle contigo.

**Probado en vivo, dos veces, con evidencia real (no solo "se ve
bien"):** desde la cuenta QA le pedí a Hermes que recordara algo,
confirmé con matemática exacta (hash del archivo) que tu `MEMORY.md` y
`USER.md` NO cambiaron ni un byte, y confirmé que sí quedó guardado en
su propio lugar. Luego, en una conversación nueva, le pregunté "¿qué
guardaste hace un momento?" con otras palabras -- lo recordó bien.
También probé al revés: escribí como tú, y confirmé que siguió yendo a
tu archivo de siempre, no al de QA.

**Pruébalo tú:** desde la cuenta QA, dile "Hermes, guarda que mi color
favorito de prueba es tal" y luego, en otro mensaje, pregúntale "¿de qué
color dije que era mi favorito?" -- debe recordarlo bien. Y desde tu
cuenta normal, nada debería sentirse distinto.

**Notas de Arturo:**

---

## 24 Jul 2026 (madrugada) — Bloque AF: arreglado el bug de "Hermes inventa que guardó algo" (L13)

**Qué se arregló:** el hallazgo de ayer (Hermes diciendo "he guardado tu
contraseña" sin haberlo hecho de verdad) ya tiene causa raíz confirmada
Y arreglo aplicado, probado en vivo dos veces esta noche. Eran en
realidad DOS problemas: (1) cuando le mandas dos cosas seguidas y la
primera se queda sin respuesta, Hermes puede mezclar ambas y actuar
sobre la vieja; (2) uno más grave que encontré sin buscarlo: cuando el
filtro de seguridad SÍ corregía una invención a tiempo, lo que te
llegaba a ti era el mensaje correcto, pero lo que quedaba GUARDADO en su
memoria de esa conversación seguía siendo la versión inventada. Ambos
quedan corregidos.

**Cómo se ve en tu día a día:** si le pides algo que sí puede fallar
(guardar una contraseña, crear una tarea) y por lo que sea no puede
hacerlo, ahora Hermes te lo dice claro en vez de inventar que sí lo
hizo — y esa aclaración es lo que de verdad queda en su historial, no
la invención.

**Pruébalo tú:** no hay una forma segura de "probar a propósito" que
invente algo (sería pedirle que falle adrede), pero si alguna vez ves
que dice "ya lo hice" y tú sabes que no pasó nada, dímelo de inmediato
-- eso significaría que el arreglo tiene un hueco nuevo, no que volvió
el de antes.

**Notas de Arturo:**

---

## 24 Jul 2026 (madrugada) — HALLAZGO, nuevo: tu memoria real y la cuenta de prueba (QA) NO están separadas todavía — **RESUELTO el mismo día, ver entrada más abajo "Opción 3"**

**Esto NO fue un arreglo cuando lo escribí -- era un riesgo real que
encontré probando el arreglo de arriba, sin buscarlo. Ya se resolvió
esa misma mañana, hablándolo contigo -- ver la entrada "Opción 3" más
abajo para el detalle completo.**

**Qué pasó:** al probar en vivo que el arreglo de arriba funcionaba, sin
querer quedó guardada una frase de prueba ("mi color favorito de prueba
Bloque AF es azul-verificacion") en tu archivo de memoria REAL -- el
mismo que Hermes usa contigo todos los días. Me di cuenta y la borré de
inmediato, de la forma correcta (no a mano). Pero esto confirma algo que
todavía no está resuelto: **la forma en que Hermes realmente guarda lo
que le pides recordar (no la base de datos, el archivo de memoria) no
tiene ninguna manera de distinguir "esto lo dijo Arturo de verdad" de
"esto fue una prueba" -- ni con tu cuenta de prueba (QA) ni con la mía
de hoy.**

**Qué significa para ti, mientras se resuelve:** si usas la cuenta QA
(la nueva, para pruebas) y le pides a Hermes que "recuerde" algo aunque
sea en broma, ese dato puede terminar mezclado con tu memoria real,
igual que me pasó a mí ahorita. Por ahora, evita pedirle a Hermes que
guarde o recuerde cosas desde la cuenta QA -- para chatear normal, hacer
preguntas, o simplemente entretenerte no hay ningún riesgo; el riesgo es
específicamente con lo que Hermes decide "recordar".

**Qué sigue:** esto necesita una decisión tuya sobre cómo separar de
verdad la memoria de la cuenta QA de la tuya (no es algo que deba
resolver solo, toca el sistema de permisos) -- lo dejo listo para
hablarlo cuando quieras, con las opciones ya pensadas.

**Notas de Arturo:**

---

## 22-23 Jul 2026 — Bloque Q: Hermes ya no inventa evidencia de incidentes

**Qué se arregló:** el mecanismo que inyecta evidencia real de logs antes
de que Hermes responda tenía un bug de índice que hacía que esa
evidencia NUNCA llegara al modelo, aunque el código decía que sí.

**Cómo se ve en tu día a día:** antes, cuando le pedías "revisa qué
falló", Hermes inventaba timestamps y líneas de log que sonaban
creíbles pero eran falsas. Ahora debería citar líneas reales de
`journalctl` (o decir honestamente "no encontré evidencia" si no hay
nada).

**Pruébalo tú:** manda "Revisa qué error hubo hace un momento" justo
después de que algo falle (o después de que yo reinicie el servicio).

**Notas de Arturo:**


---

## 22-23 Jul 2026 — Bloque S: conversaciones largas ya no rompen todo

**Qué se arregló:** el sistema que resume conversaciones viejas para no
saturar al modelo solo consideraba el límite de Gemini (~1 millón de
tokens) -- nunca consideraba que Groq (el respaldo) solo aguanta 128 mil.
Una conversación larga podía romper TODA la cadena de respaldo sin que
nadie la comprimiera a tiempo.

**Cómo se ve en tu día a día:** antes, después de mucho uso seguido, un
mensaje nuevo podía tronar con "rate limit" o quedarse pegado sin
respuesta, sin aviso. Ahora, cuando la charla se pone larga, Hermes te
avisa UNA vez ("esta charla ya está larga, jefe; compacté lo viejo...")
y sigue funcionando -- tu historial completo queda guardado igual, solo
se resume lo que se manda al modelo.

**Pruébalo tú:** no hay un mensaje simple para esto (es automático con
el uso). Si ves el aviso de "charla larga" y la respuesta sigue
llegando bien después, funcionó.

**Extra en este mismo bloque:** `/new` y `/reset` ahora responden en
español (antes decían "Session reset! Starting fresh." en inglés), y
el mensaje explica que tu historial NO se borra, solo se abre una
ventana nueva.

**Pruébalo tú:** manda `/new` y revisa que el mensaje y los 3 botones
("Permitir una vez" / "Siempre" / "Cancelar") estén en español.

**Notas de Arturo:**


---

## 23 Jul 2026 — Bloque T: bóveda de contraseñas cifrada

**Qué se arregló/agregó:** una forma nueva y separada de guardar
contraseñas o API keys que le pidas a Hermes que recuerde -- cifrada
con una passphrase que solo tú sabes (nunca se guarda en ningún lado).
Completamente distinta de la memoria normal.

**Cómo se ve en tu día a día:** puedes decir "Hermes, guarda mi
contraseña de [servicio]: [valor], la palabra clave es [tu passphrase]"
y después "Hermes, dame mi contraseña de [servicio], la palabra clave
es [tu passphrase]".

**Pruébalo tú:** `Hermes, guarda una contraseña de prueba llamada test:
el valor es abc123, la palabra clave es miclave` y luego `Hermes, dame
la contraseña de test, la palabra clave es miclave`.

**Importante que sepas:** hay UNA sola passphrase para TODA la bóveda
(no una distinta por cada contraseña que guardes) -- la primera que uses
se vuelve la maestra para todo lo que guardes después.

**Hallazgo de seguridad que se corrigió en el camino:** al principio, si
escribías mal la passphrase, Hermes te decía cuál era la correcta -- ya
no lo hace, y además esa passphrase se borra automáticamente del
historial que Hermes puede releer en el futuro (aunque tú la sigas
viendo en tu propio Telegram, eso es normal).

**Notas de Arturo:**


---

## 23 Jul 2026 — Bloque W: confirmación antes de guardar por voz

**Qué se agregó:** si le pides guardar una contraseña por nota de voz,
Hermes ahora está obligado a repetirte EXACTAMENTE lo que entendió y
preguntarte "¿guardo esto? sí/no" antes de escribir nada a disco --
nunca guarda directo desde audio.

**Por qué importa:** la transcripción de voz se puede equivocar, y sin
este paso no tenías forma de corregir un error antes de que quedara
guardado.

**Pruébalo tú (con audio real):** manda una nota de voz diciendo algo
como "guarda mi contraseña de prueba, el valor es 123, la clave es
abc" -- Hermes debe repetírtelo y preguntar antes de guardar, nunca
guardar directo.

**Notas de Arturo:**


---

## 23 Jul 2026 — Escáner de secretos reforzado (menos posibilidad de que Hermes repita una API key)

**Qué se arregló:** el filtro que debía impedir que Hermes repitiera una
API key real en el chat solo detectaba el patrón cuando aparecía la
palabra "api_key" pegada al valor. El incidente real del 4-jul (donde
Hermes repitió una key diciendo "la clave es: ...") NO lo hubiera
detectado. Ahora reconoce el FORMATO real de las llaves de cada
proveedor (Gemini, Google, Groq, OpenRouter, DeepSeek), sin importar
qué palabra esté cerca.

**Cómo se ve en tu día a día:** si Hermes está a punto de mandarte algo
que parece una credencial real, debería bloquear su propia respuesta y
avisarte, en vez de mandarla.

**Notas de Arturo:**


---

## 23 Jul 2026 — HALLAZGO SIN ARREGLAR: Hermes puede inventar que hizo algo cuando en realidad no

**Esto NO es un arreglo -- es un problema real encontrado hoy, todavía
sin resolver, que debes saber.**

**Qué pasó:** en una prueba interna, le mandé un mensaje simple ("hola,
esto es una prueba") justo después de que la conversación se compactara
(se resumiera por ser muy larga). Hermes respondió como si estuviera
completando una tarea VIEJA que estaba en el resumen (dijo "he guardado
tu contraseña...") sin haber llamado a ninguna herramienta real -- lo
inventó por completo. El sistema que debería bloquear justo este tipo
de invención (decir "ya lo hice" sin una acción real) lo detectó
correctamente en el texto, pero por alguna razón NO lo bloqueó a
tiempo -- necesita una sesión de diagnóstico dedicada, no un parche
rápido sobre un mecanismo de confianza.

**Qué significa para ti, mientras se arregla:** si notas que Hermes
dice haber hecho algo (guardado, enviado, programado, etc.) justo
después de que la conversación se compactó o cambió de tema
abruptamente, no confíes en esa afirmación sin verificarla -- pregunta
"¿de verdad llamaste a la herramienta para eso?" o revisa tú mismo.

**Notas de Arturo:**


---

## 23 Jul 2026 — Diagnóstico del hallazgo anterior (Bloque AE): la causa real NO era la compactación

**Actualización del hallazgo de arriba, todavía SIN ARREGLAR.** Investigué
a fondo qué pasó exactamente. Dos cosas importantes:

**1. No fue la conversación compactándose.** Lo que realmente pasó: le
mandaste a Hermes un mensaje de voz pidiendo guardar la contraseña de
Cisco, luego una corrección por texto -- y Hermes nunca te contestó a
ninguna de las dos (se quedaron "atoradas"). Más de una hora después,
llegó el mensaje de prueba del arnés interno, y como las 3 cosas
llegaron sin que Hermes respondiera entre medio, el sistema las juntó en
un solo turno -- Hermes respondió a lo más importante (la contraseña) e
ignoró el mensaje trivial que sí acababa de llegar. Dicho simple: si le
mandas dos cosas seguidas y la primera se queda sin respuesta, Hermes
puede "recordarla" y actuar sobre ella cuando le mandes algo más, aunque
para ti sean mensajes separados.

**2. Encontré algo más grave, sin buscarlo:** cuando Hermes SÍ corrige un
error justo antes de contestarte (el filtro anti-invención funcionando
bien), lo que te llega a ti puede ser el mensaje correcto y seguro -- pero
lo que queda GUARDADO en su memoria de esa conversación es la versión
ORIGINAL, la incorrecta. Es decir: Hermes puede "recordar" haber dicho
algo que en realidad nunca te llegó a decir. Esto no es solo el problema
de las contraseñas -- afecta también al filtro que fuerza español y a
cualquier plugin que corrija una respuesta.

**Qué significa para ti, mientras se arregla:** lo mismo que ya te dije
arriba sigue aplicando (verifica antes de confiar). Además: si mandas dos
mensajes seguidos y el primero no recibe respuesta antes de que mandes el
segundo, trata la conversación con más cuidado -- pregúntale explícitamente
qué entendió antes de asumir que hizo lo que dijiste en el primero.

**Probé en vivo (arnés interno, sin usar tu Telegram real) y confirmé
ambas cosas con pruebas reales**, no solo con "se ve bien en el código".
Tres opciones de arreglo quedaron documentadas para que las decidamos
juntos -- ninguna aplicada todavía, tal como pediste.

**Notas de Arturo:**


---
