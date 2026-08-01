# LIBRETA_SEED — datos reales de Arturo, estructurados por tabla
**Fuente: CUESTIONARIO_MAESTRO respondido (01 ago 2026). Campo sin dato = NULL documentado, no se inventa.
Referencia (r.N) = número de respuesta del cuestionario.**

**⚠️ CORRECCIÓN (Bloque AR, 01 ago): la libreta vive en `libreta.db` (NO `state.db` — ese es del proyecto
original). La reconciliación de estos datos se aplicó como migración v4 (`scripts/libreta_migrar.py`),
validada en laboratorio y aplicada a producción con respaldo previo. Los datos ya NO son "por cargar":
gastos/meta/peso/hábitos ya viven en `libreta.db`. Lo que resta es captura continua vía la clase `Libreta`.**

## tabla: ingresos_fuentes
| fuente | monto | frecuencia | notas |
|---|---|---|---|
| taqueria | 200 MXN/día trabajado | diario, día trabajado día pagado (r.13) | días variables — NO asumir 26/mes (r.14); martes descanso; sin propinas (r.15) |
| refrescos | variable (r.16) | por venta | costo caja 328 MXN/24 pzas (~13.67/pza, sube anual); venta 20 MXN/pza; margen ~6.33/pza (~152/caja); sabores: Coca-Cola y Yoli; **patrón desconocido → Hermes lo mide y reporta** |
| trading | 0 (aún en papel) | — | solo cuentan ganancias realizadas y transferidas (E10 sigue vigente aquí) |
| youtube/redes | 0 (pre-monetización) | — | riel futuro; canal @ArturoRMN1, ~120 subs |

Captura de ingresos/gastos (r.17, r.24): voz si hay prisa · texto para detalle · foto en viajes ·
**PDF de estado de cuenta de débito → Hermes extrae movimientos**. TODOS los gastos, sin monto mínimo.
Reporte de rieles: SEMANAL (r.18, domingo por la mañana — su ventana).

## tabla: gastos_fijos
| concepto | monto | fecha | notas |
|---|---|---|---|
| recarga_telefono | 230 MXN | mensual | "el de ley" — contradicción resuelta a favor de 230 (r.19) |
| gym | 500 MXN | mensual, día variable | Hermes detecta el patrón de pago |
| deepseek | 100 MXN | ~día 28, puede variar | él recarga 100 fijo; Hermes observa el gasto promedio real |
| servicio_moto | 550 MXN | **bimestral** (corrige el ~300/trimestre de E10, r.19) | monitoreo arranca cuando él avise el primer servicio (r.121); solo por fecha, no km |
| gasolina | ~200 MXN | mensual variable | casi siempre misma gasolinera; sin control km/l (r.122) |
| claude_code | variable | cuando él decida (r.19, r.23) | no es recurrente fijo; decisión suya cada vez |

Sin deudas (r.34). Comida y vivienda cubiertas fuera del flujo (r.21 — el SUPUESTO de E10 queda confirmado).
Sin otros gastos de moto: no paga seguro/tenencia (r.22). No paga ElevenLabs (r.23 — **cancelar/retirar la llave**).
DaVinci Studio fue pago único (r.23). Gastos intocables: NINGUNO — acepta sugerencias sobre todo (r.26).
Motor de evaluación: sugerencias apenas se detecten + consolidado dominical (r.25). Efectivo y tarjeta, más efectivo (r.27).

## tabla: ahorro_metas
| meta | monto | fecha objetivo | estado |
|---|---|---|---|
| capital_principal | 100,000 MXN (piso 90,000) | 31 de Diciembre 2027 (r.28: "finales del año que viene") | **saldo actual: 0 MXN** — no hay dinero guardado hoy |
| mac_studio | 55,000-65,000 MXN | sin fecha — se compra DESDE el capital cuando él decida | **Mac Mini DESCARTADA (r.30)**; Hermes rastrea precio/promos y avisa oportunidades (r.35) |
| moto_nueva | sin monto | futuro | "el enfoque prefiero que siga siendo el dinero" (r.31) |

Depósito mensual objetivo: 3,500 MXN provisional (r.29: "si todo apunta, esa cantidad está bien" — Hermes
recalcula con datos reales del primer mes). Sin fondo de emergencia separado: el capital ES el fondo (r.35).
CETES (r.32-33): SÍ va a invertir · tiene CURP/RFC/INE/CLABE · cuenta de cetesdirecto POR ABRIR (guiarlo
paso a paso — la abre ÉL, Hermes nunca toca el trámite) · estrategia escalera 28 días confirmada ·
reinversión manual con recordatorio mensual ("con unos clicks se vuelve a invertir").

## tabla: horario (base — el detalle llega en septiembre)
- Cuatrimestre actual: termina ~15 ago — **NO cargar su horario** (r.3, r.61). Nuevo: septiembre-diciembre;
  Arturo manda el horario/PDF de comunicados y Hermes lo estructura (r.61, r.120).
- Carrera: Tecnologías de la Información · duración 3 años 4 meses · en septiembre inicia 2.º año (r.60).
- Escuela: lunes a viernes "de ley"; sábado y domingo no hay (r.1). Semanas irregulares: festivos,
  vacaciones, maestros que faltan — Hermes se acopla, jamás asume semana perfecta (r.1).
- Trabajo taquería: 18:00-22:30, a veces hasta 23:00; todos los días excepto martes; negocio familiar =
  puede haber descansos imprevistos (r.5-6).
- Gym: lunes a sábado ideal, rutina partida confirmada (r.7); si la semana falla, domingo es comodín de
  reposición (r.1: "si hoy lunes no voy al gym, me sugiera o reprograme para el domingo").
- Sueño: meta acostarse 00:00, despertar 06:00 (r.2, r.8). Hermes observa y sugiere mejoras de sueño.
  Puede escribirle hasta las 24:00; después solo si Arturo lo activa (r.8).
- Ventanas de decisiones/reportes: domingo por la mañana y martes (día de descanso) (r.9).
- Silencio: martes 20:00-22:00 grabación (r.10). Salidas improvistas: él avisa ("el martes tengo reunión")
  y Hermes reajusta agenda y protege metas (r.10).
- Huecos imprevistos: Hermes analiza, hace él las tareas que pueda, propone con estimaciones de tiempo;
  Arturo decide (r.12). Certificaciones en línea: si hay 15 min libres y un curso en la lista, sugerirlo (r.1).

## tabla: habitos (registro diario, cierre nocturno POR VOZ — r.73)
entrenar · estudiar · comer_limpio (detallado, registro de comidas — r.70) · trabajo_profundo · cero_chelas ·
descanso_estrategico · sueño_horas (r.77) · + los que promuevan salud/automejora (r.72, abierto).
- cero_chelas en situación de riesgo (r.71): explicar el trabajo que se echa a perder Y las ventajas de no ir de farra.
- Gym: asistencia + pesos/series si él los da; mínimo garantizado: asistencia + cardio 30 min (r.74). Sin lesiones (r.75).
- Peso: dato real actual 111.5 kg (r.68 confirma) · meta y ritmo: NULL (no definidos) · protocolo de pesaje: NULL (r.69).
- Autoevaluación dominical: preguntas que lo hagan cuestionarse, ligadas a las metas del proyecto (r.76).

## tabla: comunicacion (config)
- Trato: "jefe"/"señor", español; estilo secretaria inteligente eficiente, tipo Viernes de Tony Stark (r.84).
- Brief 6:30 (r.86, r.98): panorama del día + clima CRUZADO con agenda (lluvia vs gym/trabajo) + noticias
  de trading + todo lo que deba saber. Cierre nocturno: TODO el día resumido, EN AUDIO, a la hora en que
  él va a descansar (r.90).
- Recordatorios: default 2 horas antes; si no da señales de vida, insistir por otra vía (r.80). Pagos: 1 día antes (r.81).
- Captura espontánea: SIEMPRE preguntar "¿lo agendo?" antes de crear recordatorio (r.89) + regla de
  simulación r.20 (en pruebas todo es simulado salvo marca explícita).
- En horario de taquería: Hermes manda lo que considere; Arturo contesta tarde o al día siguiente — no insistir (r.85).
- Proactividad: sin número fijo aún (r.87) — empezar conservador, medir, ajustar. Voz en respuestas: sí, a veces (r.88).
- Emergencias (r.11): caída de producción y anomalías se REPORTAN siempre; ARTURO decide qué es urgente. Hermes reporta, no resuelve solo lo crítico.

## tabla: youtube_contenido
- Canal: https://www.youtube.com/@ArturoRMN1 (r.44). Nichos: biografías/historia + análisis + monólogos
  reflexivos — dirección la marca él, Hermes propone desde Obsidian (r.53, r.57). Sin temas vetados (r.58).
- Cadencia: 1 video largo/semana + TODOS los clips valiosos ≤2 min que salgan (10, 20, los que sean),
  programados en los mejores horarios de la semana (r.46, r.48).
- Guion: formato con gancho de inicio, cierre, y análisis de retención estilo podcast; mejorar iterando
  contra métricas (r.47 — las 5,000 palabras NO son estándar fijo).
- Distribución: shorts también a TikTok e Instagram; TikTok tendrá además videos propios; Facebook si se
  puede monetizar — "a todas las plataformas" (r.45, r.54, r.55). TikTok arranca junto con YouTube este año.
- Métricas semanales: todo lo que sirva para mejorar y avanzar a monetización (r.56).
- Thumbnails/títulos: Hermes propone, Arturo decide (r.51).
- Edición (r.49-50, materia prima de la skill DaVinci): graba con teleprompter → IA de DaVinci corta
  silencios → revisión manual de palabras recortadas → quita párrafos repetidos (elige mejor toma) → sube.
  DOLORES: hacer el video dinámico/profesional · música de fondo (niveles, dónde van drama/suspenso/emotivo) ·
  B-roll e imágenes de contexto (personajes, batallas, stock) · TIEMPO de sentarse a editar.
  Límite duro: render calienta la M1 base → investigar pipeline eficiente sin deteriorar el equipo (pidió
  investigación exhaustiva). Material: disco externo SSD 500 GB (r.52).

## tabla: correo (config F6, no encender aún)
- 2 cuentas: escuela y redes — direcciones exactas: NULL (Arturo las pasa; Claude Code tiene acceso, Hermes no — r.63).
- Prioritario al momento: banco, compras, invitaciones/eventos, y TODO lo escolar con entregas/tareas (r.108).
- Ruido: "alguien comentó/compartió" de redes sociales (r.108).
- Flujo tareas (r.62, r.64): Hermes analiza correos → sugiere qué hacer → arma la tarea → recordatorio
  escalonado ("faltan estos detalles, súbelo antes de las 12") → confirma después que se entregó.
- JAMÁS entrega tareas (r.67). Respuestas de correo: solo BORRADOR + ejemplo + autorización explícita, futuro F6 (r.67, r.107).
- WhatsApp: no; solo Telegram (r.109).

## tabla: equipo_fisico
- HP: 24/7, poco calor ambiente, hay ruido (por eso alertas van al iPhone, no a la HP) · **monitorear
  temperatura; Claude Code pausa pruebas si se calienta** (r.103).
- MacBook M1 base: PRESTADA — puede trabajar de noche (render) pero toda config se revierte antes de las
  06:00 y queda como estaba (r.102). Proyectos en SSD externo 500 GB.
- iPhone: canal de alertas/alarmas; investigar notificaciones críticas vía Telegram que vibren como
  llamada para emergencias y olvidos (gym no reportado, día de grabación sin señales) (r.99).
- Zona horaria: America/Mexico_City (Iguala de la Independencia, Guerrero). Si viaja (España, Guadalajara…),
  Hermes contextualiza la zona del jefe; el servidor siempre opera desde Iguala (r.116).

## formato_salida
Dinero: "1,500 MXN" · Fechas: "27 de Abril 2026" (r.118). Nombre en documentos: él lo indica al momento (r.117).

## extras aprobados (backlog, baja prioridad)
- Coaching social (r.123): sugerencias de interacción antes de reuniones (pésames, saludos formales/informales,
  salidas elegantes de una reunión — incluida la llamada simulada de rescate).
- Cumpleaños: tabla lista pero vacía; Hermes preparado para cuando lleguen (r.82).
- Agenda: Notion + evaluar Apple Calendar/ecosistema iPhone-Mac (r.83).
- Home Assistant: congelado, "después lo resolvemos" (r.101).
- Sección 105 (qué espera a diciembre): SIN RESPUESTA — se define al cierre de la ventana con lo que falte.
