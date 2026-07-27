# Bitácora para Arturo

Un registro pensado para TI, no para desarrolladores: por cada arreglo o
mejora real, qué cambia en tu día a día concreto, con un mensaje que
puedes mandar literal para probarlo tú mismo. Se actualiza al cerrar
cada sesión (regla permanente en `CLAUDE.md`).

---

## 27 Jul 2026 (tarde) — Arreglé un bug real que hacía que Hermes se quedara "pensando" sin nunca responder

**Qué encontré, sin buscarlo:** estaba diagnosticando por qué a veces Hermes
inventa detalles cuando le pide "revisa qué falló" -- en el camino, una
conversación de prueba se quedó atorada compactándose una y otra vez sin
nunca llegar a responderle de verdad. Investigué y encontré que es un bug
real: una vez que una conversación cruza cierto tamaño, Hermes intenta
resumirla para que quepa en los proveedores de respaldo (Groq), pero el
resumen que produce siempre queda un poco más grande de lo que necesitaba
-- así que en el SIGUIENTE mensaje, vuelve a intentar resumir, y otra vez,
y otra vez, sin parar nunca. Si esto le llegó a pasar alguna vez en una
conversación suya real y muy larga, así se hubiera visto: mensajes de
"compactando..." repetidos sin que Hermes le conteste lo que preguntó.

**Cómo lo confirmé:** busqué en el repositorio real del programa base en
GitHub (como me pidió, antes de seguir adivinando) y encontré que otros
usuarios ya habían reportado un problema parecido -- confirma que no es
que "se me ocurrió", es un patrón real conocido. Reproduje el bug en vivo
con una conversación de prueba, arreglé el código, y volví a probar la
MISMA conversación que antes se quedaba atorada: ahora responde en un
solo intento.

**De paso, mejoré también el "revisa qué falló":** el mecanismo que busca
evidencia real de un incidente solo miraba 10 minutos hacia atrás desde el
momento en que usted pregunta. Si pregunta un ratito después de que algo
pasó (no en el segundo exacto), se le escapaba el incidente real. Ya lo
subí a 45 minutos -- probado en vivo con un error real que tuvimos hoy
mismo (16 minutos antes), y ahora sí lo encuentra.

**Verificado con 273 pruebas automáticas, todas en verde**, y ya puesto en
el Hermes real (no solo en la copia de pruebas) -- reinicié el servicio
con la evidencia de que funciona antes y después.

**Mensaje que puede mandarle a Hermes para probar el segundo arreglo:**
"Hermes, revisa qué falló hace un rato" (después de que algo realmente
haya fallado) -- debería citar líneas reales de los últimos ~45 minutos,
nunca inventar una hora o una causa que no esté ahí.

**Pendiente real, pequeño:** para probar el primer arreglo (que ya no se
atore compactando) necesitaría una conversación suya real que haya
crecido mucho -- no fue posible forzar esa prueba hoy sin gastar más de
la cuenta en llamadas de prueba, así que quedó verificado con una
conversación de prueba interna, no con una suya. Si alguna vez nota que
Hermes se queda repitiendo "compactando..." sin responder, avíseme de
inmediato -- sería señal de que el arreglo no cubrió todos los casos.

---

## 27 Jul 2026 — El programa base ya está actualizado en el Hermes real (no solo en la copia de pruebas), y no se perdió nada

**Qué era esto:** el "Bloque 6", el último paso del blindaje que empezó
hace días -- pasar la actualización de la copia de pruebas al Hermes
real que usted usa por Telegram. Es el único paso que sí tocó
producción de verdad, por eso se hizo con usted presente, siguiendo el
plan al pie de la letra.

**Antes de tocar nada, encontré algo que pudo haber salido mal:** el
plan original decía "copia el código nuevo a producción", pero antes de
hacerlo comparé, línea por línea, todo lo que usted tiene funcionando
hoy contra la versión nueva. Buena noticia: las mejoras reales de los
últimos días (Tarea E, la bóveda, la memoria separada de la cuenta de
pruebas, el aviso de DeepSeek, etc.) SÍ estaban todas incluidas en la
versión nueva -- verificado una por una, no de un vistazo. Lo único que
sí se habría perdido si no revisaba: el propio archivo donde llevo el
registro de todo esto (este archivo, y sus hermanos ESTADO/BLOQUES).
Los rescaté antes de que se perdieran.

**Dos cosas reales que encontré en el camino, sin buscarlas:**
1. **El disco duro Seagate se desconectó solo esta mañana** (8:22 am)
   por un error real de conexión/energía -- no algo que yo causara.
   Se quedó desconectado sin que nada avisara hasta que lo detecté
   ahorita, antes de usarlo para el respaldo. Ya lo reconecté, pero le
   pediría que corra este comando en su terminal para descartar que el
   disco esté fallando (y no solo un cable flojo):
   ```
   sudo smartctl -a /dev/sda
   ```
2. **Al apagar el Hermes viejo para hacer el cambio, no cerró limpio**
   (tardó 8 segundos y salió con error en vez de cerrar bien). No
   afectó el corte, pero es un bug real que hay que revisar aparte.

**Cómo lo verifiqué:** respaldo completo del Hermes viejo guardado en
el disco Seagate (700 MB, revisado que no esté corrupto) antes de
tocar nada, con un punto de regreso marcado por si algo salía mal. Ya
con el código nuevo puesto, corrí las 10 pruebas rápidas de siempre
contra el Hermes REAL (no la copia) -- las 10 pasaron. Confirmé que un
bug real que encontramos esta semana (una tabla que le faltaba a la
base de datos en una instalación nueva) ya viene arreglado en el
Hermes real.

**Todavía NO está cerrado del todo a propósito:** falta revisar mañana
los registros de 24 horas reales de uso antes de decir que quedó
perfecto -- así lo pide el propio plan, no se cierra el mismo día solo
porque las pruebas pasaron.

**Mensaje que puede mandarle a Hermes para probarlo usted mismo:**
"Hermes, ¿qué hora es y desde cuándo está corriendo el gateway?" --
debería contestar con la hora real y decir que lleva corriendo desde
hoy poco antes del mediodía (el reinicio del corte).

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
