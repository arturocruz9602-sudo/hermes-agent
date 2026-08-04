# ESTADO — actualizado: 03 ago 2026 (F7-2 COMPLETO: analizador refrescos)
**Se SOBREESCRIBE cada sesión, máx 80 líneas (gate). Histórico: `docs/archivo/`. Voz de Arturo: `CUESTIONARIO_MAESTRO.md` = misma jerarquía que MANDATO.**

## Fases HAS
F0-F4 ✅ | F5 🔄 ~50% | F6 🔄 en curso | F7 🔄 BLOQUES 1+2 hecho | F8-F14 ⬜ | **F11 laboratorio VALIDADO (AQ)**. **E10 → v1.7** (meta capital $100k/31-dic-2027).

## REGLA QUE CAMBIA TODO (r.20, permanente — ya en CLAUDE.md, regla 6)
Todo dato de fechas/pagos/citas mencionado en pruebas = **SIMULADO** salvo que Arturo marque "dato real". Inventar escenarios y adelantar el reloj: SOLO en el laboratorio Docker. Producción jamás.

## ✅ F7-2 HECHO (03 ago, loop autónomo) — analizador refrescos (Fase 7/OT-6, HAS §E10)
`scripts/analizador_refrescos.py`: detecta patrón real de venta de refrescos (r.16).
- Calcula ganancia neta = (precio_venta - costo_unitario) × unidades
- Entrada: cajas a $328 c/24 pzas, venta $20/pza individual
- Salida: promedio diario, desviación, rango, desglose por semana, proyección mensual/anual
- **8/8 pruebas pasan**: inicialización, cálculo unitario, persistencia, simulación 30d realista, desglose semanal, reportes (sin/con datos), proyección
- Reporte legible con estadísticas de rentabilidad; corre sin datos reales (simulación)
- Arreglado: import de Libreta + precisión decimal

## ✅ F7-1 BLOQUE 1 HECHO (03 ago, sesión anterior) — archivo/biblioteca permanente
`scripts/archivo_biblioteca.py`: clasificación, archivo, dedup, gastos con evidencia. Migración v6 aplicada. 30/30 pruebas. Real verificado intacto. Vision extractor inyectable pero PENDIENTE r.91 (gratis/local/pago).
F7-1 bloques 2/3 (reporte PDF, limpieza) NO empezados.

## Bloques recientes CERRADOS
AQ/AR: Docker validado + libreta v4 prod. · AS: brief+cierre audio+STT. · F5-1: Notion Finanzas 2/6. · F5-2: cola v2 11/11 pruebas. · AT: trading testnet 17/17. · AU: 75/75 pruebas motor+pipeline. · F6-1: correo vigilado+deployed. · F6-2: horario_por_foto 29/29 (vision pendiente).

## Decisiones pendientes ARTURO (actualizado 03 ago)
1. Vision: tier pago/local/gratis? Bloquea 2 extractores (r.91).
2. YouTube: SE OCUPAN LAS DOS llaves (confirmado) — guía en `docs/YOUTUBE_LLAVES_GUIA.md`.
3. Telegram QA: `chat_id=8727618189` verificado; falta `TELEGRAM_QA_CHANNEL` en `.env`.
4. Binance testnet: llaves en guía `docs/BINANCE_TESTNET_GUIA.md`.
5. Horario escuela (r.61): espera a sept-dic; `horario_por_foto.py` listo si se resuelve decisión 1.

## No tocar / reglas de equipo
- M1 PRESTADA (r.102): reversa antes 6:00.
- Correo solo-lectura (ambos vigilados 15min).
- Pruebas masivas SOLO Docker QA.
- Nombres/correos/contraseñas/salud NUNCA a API gratis (r.91).
- has_progress.py NO se usa (bug abierto).

## Próximos candidatos
F7-1 bloques 2/3 (reporte PDF), F6-2 bloques 2/3, F5 rest vistas, AV (loop confiabilidad).

## Al cierre
ESTADO ≤80 · BLOQUES 1 línea · commit+push · TEMP-DIAG=0 · temp HP normal.
