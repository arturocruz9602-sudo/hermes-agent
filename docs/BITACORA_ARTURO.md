# Bitácora para Arturo

Un registro pensado para TI, no para desarrolladores: por cada arreglo o
mejora real, qué cambia en tu día a día concreto, con un mensaje que
puedes mandar literal para probarlo tú mismo. Se actualiza al cerrar
cada sesión (regla permanente en `CLAUDE.md`).

---

## 28 Jul 2026 (mediodía) — Confirmé que el cambio de motor de ayer quedó estable, y arrancamos la limpieza de las 136 skills

**Qué pasó:** ayer se cambió Hermes al código nuevo (`arturo/base`, la
versión ya probada del rebase) directo en producción -- el último paso
pendiente de ese cambio era dejarlo funcionando 24 horas sin tocarlo y
revisar los logs completos, para descartar cualquier problema que solo
aparezca con el tiempo (no en la prueba del momento). Hoy revisé esas
24 horas: encontré solo 4 avisos menores de reconexión de Telegram (se
cae la conexión un instante y se reconecta sola en 5 segundos, algo que
ya pasaba antes y no tiene que ver con el cambio), cero errores reales.
Con esto, el cambio de ayer queda confirmado como estable -- no es solo
"parece que funciona", ya se vigiló de verdad.

**Qué sigue, y ya avancé de verdad (28 Jul, tarde):** empezamos la
limpieza de las 136 skills. Primer bloque cerrado hoy mismo:

1. Borré 2 "skills" que en realidad nunca tuvieron contenido -- alguna
   vez que se intentaron descargar del catálogo público, se guardó por
   error la página de "no encontrado" del sitio en vez de la
   instrucción real. Puro peso muerto.

2. Encontré algo más importante: 3 instrucciones centrales que Hermes
   usa constantemente para programar bien (cómo depurar un error paso a
   paso, cómo probar código antes de darlo por bueno, cómo pedir una
   revisión antes de aceptar un cambio) estaban duplicadas -- una copia
   genérica bajada de internet y una copia adaptada específicamente
   para Hermes, con el mismo nombre las dos. Cuando Hermes necesitaba
   usar una de ellas por nombre, el sistema literalmente se negaba
   ("hay 2, no sé cuál usar") en vez de improvisar cuál usar -- lo
   comprobé contra el código real, no solo lo supuse. Investigué en
   internet si la versión pública tenía mejoras que valiera la pena
   traer, rescaté 2 técnicas reales que sí valían la pena, y dejé una
   sola versión de cada una (la adaptada para Hermes, que ya era mejor
   en 2 de los 3 casos).

**Qué significa para usted, en concreto:** esto no es algo que note
hablando con Hermes en el día a día -- es la calidad del trabajo que
hace por dentro cuando programa o se corrige a sí mismo. Antes de hoy,
si Hermes necesitaba consultar "cómo depuro esto bien" podía fallar en
silencio o tropezar con el error de duplicado; ahora no.

**Pendiente real, todavía sin tocar:** faltan las otras 4 partes de
esta limpieza (reparar 2 skills con piezas rotas, el contador de uso
que sigue mal indexado internamente, ponerle información completa a
las 136, y un comando que audite todo esto solo). Le aviso conforme
avance.

**Notas de Arturo:**

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

## 27 Jul 2026 (noche) — Corregí cómo entendía el plan: usted sí quiere que Hermes edite sus propias herramientas

**Qué pasó:** le expliqué mal una parte del plan grande -- dije que solo
yo (Claude) podía mejorar las "skills" (las herramientas que Hermes usa).
Usted me corrigió: nunca dijo eso, y de hecho el plan ya apuntaba a que
Hermes hiciera más, no menos, sobre todo porque a mí solo me tiene
disponible un mes cada ~4 meses.

**Lo verifiqué de verdad** (no le di la razón porque sí) contra los 4
documentos que gobiernan el proyecto, y encontré que el documento del
plan (HAS) SÍ se contradecía a sí mismo en esto -- una parte decía "solo
Claude toca código", otra parte (más reciente) decía "Hermes debe ser
autosuficiente casi todo el año". No podían ser ciertas las dos.

**Su decisión, ya aplicada:** Hermes ahora SÍ puede mejorar sus propias
herramientas solo, pero con reglas duras para que nunca empeore nada:
tiene que probar la herramienta en su versión vieja y la nueva, y solo
se queda con el cambio si la nueva es igual o mejor -- si no, se
revierte sola. Las herramientas más delicadas (seguridad, dinero,
credenciales) siguen pasando por usted o por mí. Y arrancamos un
"recetario": cada problema real que resolvemos (yo o Hermes) queda
guardado paso a paso, para que la próxima vez no haya que pensarlo
desde cero -- ya escribí las primeras 2 recetas de hoy mismo.

**Importante:** usted pidió explícito que la Fase 3 (donde se aplica
todo esto) NO arranque sola -- se queda lista, esperando que usted diga
que sí.

---

## 27 Jul 2026 (tarde, continuación 3) — Fase 2 del plan queda cerrada de verdad, ya vamos a la Fase 3

**Qué era esto:** el plan grande de Hermes tiene 12 fases. Íbamos por la
Fase 2 (dejar la actualización del programa base como un procedimiento
repetible, no una cirugía cada vez) desde hace días, y faltaba probar
una última cosa: simular la SIGUIENTE actualización futura y confirmar
que el procedimiento ya escrito la resuelve solo, sin que yo tenga que
improvisar.

**Lo hice hoy, completo:** tomé 47 cambios nuevos reales que ya subió el
equipo que mantiene el programa base, y los apliqué encima de lo suyo
-- en una copia aparte, sin tocar su Hermes real en ningún momento.
Salió un solo choque real (un botón de aprobación que ellos rediseñaron
Y que nosotros ya habíamos traducido al español) -- lo resolví
combinando los dos arreglos, no descartando ninguno. Verificado con
las pruebas automáticas: todo en verde.

**Qué significa para usted:** el plan de 12 fases ya tiene las
primeras 4 cerradas de verdad (caja fuerte, emergencia de credenciales,
fugas urgentes, blindaje/actualización). Sigue la Fase 3: poner en
orden las 136 "skills" (las herramientas que Hermes puede usar) --
borrar las rotas, arreglar duplicados, etc. Estimado 2 semanas de
trabajo. Falta bastante del plan completo (~25 semanas más, sin contar
lo que depende de que compre la Mac Mini), pero ya no vamos empezando
desde cero -- la base ya quedó sólida.

---

## 27 Jul 2026 (tarde, continuación 2) — La cuenta de pruebas de Telegram ya quedó conectada de verdad

**Qué era esto:** llevábamos días atorados con la cuenta de Telegram
separada para hacer pruebas (la que no es la suya, para no mezclar
pruebas con sus conversaciones reales). Telegram rechazaba el login una
y otra vez.

**Lo que de verdad lo resolvió:** su idea de sacar una llave de API
desde su cuenta personal (la de años) en vez de seguir peleando con la
cuenta nueva -- funcionó a la primera. Confirma que el problema real
era que Telegram pone bajo vigilancia automática a las apps/cuentas
nuevas por default (no algo que hiciéramos mal).

**Un bug real más en el camino, ya arreglado:** el código intentaba
confirmar el código de verificación abriendo una conexión nueva en vez
de seguir usando la misma -- eso hacía que Telegram rechazara el código
aunque estuviera recién llegado. Ya no debería volver a pasar si algún
día hay que loguear esa cuenta de nuevo.

**Verificado de verdad, no solo "ya quedó":** me reconecté con la
sesión guardada y le pregunté a Telegram quién es -- contestó "Hermes
QA", el número correcto, la cuenta correcta.

**Qué cambia para usted:** ahora si se quiere probar algo con Hermes
por Telegram de verdad (no solo pruebas internas mías), ya hay una
cuenta separada lista para eso, sin arriesgar mezclar nada con su
cuenta real.

---

## 27 Jul 2026 (tarde, continuación) — Cerré el bug más grave y viejo: Hermes ya NO inventa cuando le pide revisar un error

**Qué era esto:** desde el 22 de julio había un hallazgo marcado como el
más grave sin resolver -- a veces, cuando usted le pide "revisa qué
falló", Hermes se inventaba detalles (horas, causas) en vez de decir la
verdad. Ya se habían puesto 3 capas de protección antes y el problema
seguía apareciendo.

**Lo que encontré, probándolo en vivo hasta atraparlo con las manos en
la masa:** Hermes SÍ tenía la evidencia real correcta enfrente (gracias
al arreglo de la ventana de hoy más temprano), pero la ignoraba por
completo -- se iba por su cuenta a leer un archivo de registro VIEJO
(de hace casi un mes) y presentaba eso como si fuera lo que acababa de
pasar ahorita. Le reforcé la instrucción de "no hagas eso" y AUN ASÍ lo
volvió a hacer -- confirma que pedirle con palabras no basta.

**El arreglo real:** en vez de pedirle que no lo haga, durante esas
preguntas específicas le quito la posibilidad misma de irse a leer
otros archivos -- no puede desobedecer una herramienta que no tiene
disponible. Probado en vivo 3 veces seguidas: cero veces se fue a
buscar en otro lado (antes, siempre lo hacía).

**Verificado con 353 pruebas automáticas** (0 rotas por este cambio) y
ya puesto en el Hermes real.

**Mensaje que puede mandarle para probarlo** (después de que algo
realmente haya fallado, para que tenga algo real que revisar):
"Hermes, revisa qué pasó hace un momento" -- debe o bien citarle líneas
reales y recientes, o decirle honestamente que no encontró evidencia.
Lo que YA NO debería pasar: que le hable de algo de hace semanas como
si fuera de ahorita.

**Con esto se cierra el hallazgo crítico que llevaba abierto desde el
22 de julio.**

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
2. ~~Al apagar el Hermes viejo para hacer el cambio, no cerró
   limpio~~ -- **investigado después: no era un bug.** Es a propósito:
   cuando se para con el comando directo del sistema (en vez del
   comando propio de Hermes), el programa se comporta como si alguien
   lo hubiera matado sin avisar, para que se vuelva a prender solo.
   Nada que arreglar.

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
