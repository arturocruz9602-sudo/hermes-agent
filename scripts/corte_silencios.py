#!/usr/bin/env python3
"""corte_silencios — Bloque AU-3, Pieza 1 (HAS Fase 8 / OT-8 / §E6).

Corta los silencios de una grabación SIN destruir habla, con verificación
automática obligatoria antes de entregar nada (§E6). Es el paso que a Arturo
le come horas y donde la IA de DaVinci le fallaba: detecta como "silencio" la
cola de una palabra que se apaga y se la recorta (r.49 — "las palabras que
pierden fuerza al final... la IA las detecta como silencio y quedan palabras
recortadas"). Este módulo existe para que ESO no pase, y para PROBAR que no
pasó antes de tocar el timeline.

Parámetros §E6 (calibración Blue Yeti Nano; se reajustan con una grabación de
calibración de 60s — no se clavan a ojo):
  - Duración mínima de silencio para considerar corte: 500 ms.
  - Padding: conservar 200 ms ANTES y 250 ms DESPUÉS de cada segmento de habla.
    Ahí viven las colas de las consonantes finales — este fue el fallo original.
  - Nunca cortar silencios dentro de una misma oración (<300 ms entre palabras).

Verificación automática §E6 (obligatoria antes de entregar): se transcribe el
original y el resultado, se comparan conteo de palabras y WER.
  - Criterio: palabras perdidas = 0 y WER(resultado vs original) ≤ 2 %.
  - Si falla: relaja el umbral 3 dB y aumenta el padding 50 ms, reintenta (máx
    3 iteraciones). Si aun así falla, entrega el ORIGINAL con el reporte
    "no pude cortar sin riesgo" — nunca entrega un corte que destruye habla.

El transcriptor (Whisper) es INYECTABLE: el módulo no abre red ni modelos de
pago solo (B10, r.119). Para el laboratorio trae un ORÁCULO determinista
(`transcribir_resultado_simulado`) que modela exactamente el fallo de r.49 a
partir de la cola de fade de cada palabra, así toda la lógica se prueba sin
audio ni Whisper real (r.20). En producción se inyecta el Whisper de verdad.

QUÉ NO HACE: no toca el audio ni el timeline (eso es la Pieza 2/3, en la M1 vía
DaVinci); entrega la LISTA de cortes aprobada. No abre la DB ni la red solo.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable, Optional

# ── parámetros §E6 (en milisegundos salvo indicación) ────────────────────────
MIN_SILENCIO_MS = 500        # silencio más corto que esto no se considera corte
PAD_ANTES_MS = 200           # se conserva antes del arranque de cada habla
PAD_DESPUES_MS = 250         # se conserva después — aquí vive la cola de la consonante
MIN_ENTRE_PALABRAS_MS = 300  # <300 ms entre palabras = misma oración, jamás se corta

# criterio de la verificación §E6
MAX_PALABRAS_PERDIDAS = 0
MAX_WER = 0.02

# relajación al reintentar (§E6): umbral +3 dB, padding +50 ms
RELAX_PAD_MS = 50
# cada +3 dB de umbral recupera aprox. este tramo de cola de fade que antes se
# clasificaba como silencio (modelo de laboratorio; en producción lo fija el
# detector real de dBFS sobre el audio). No es un gate ciego: es el CRITERIO
# numérico que hace que relajar el umbral de verdad rescate cola de palabra.
RELAX_CAPTURA_FADE_MS = 120
MAX_ITER = 3


# ── modelo de datos ──────────────────────────────────────────────────────────
@dataclass
class Palabra:
    """Una palabra con sus tiempos (segundos), como los da Whisper con
    marcas por palabra. `cola_ms` es la cola de fade final: los últimos ms en
    que la energía cae y el detector de silencios PUEDE confundirla con silencio
    (r.49). Por defecto 0 (palabra que termina con energía). El texto se usa
    para el conteo de palabras y el WER de la verificación."""
    inicio: float
    fin: float
    texto: str
    cola_ms: float = 0.0

    @property
    def dur_ms(self) -> float:
        return (self.fin - self.inicio) * 1000.0


@dataclass
class Corte:
    """Un tramo de silencio a ELIMINAR (segundos). Nunca toca habla: el planificador
    garantiza que `[inicio, fin]` cae entre dos palabras, ya restado el padding."""
    inicio: float
    fin: float

    @property
    def dur_ms(self) -> float:
        return (self.fin - self.inicio) * 1000.0


@dataclass
class ParametrosCorte:
    """Los parámetros §E6 vigentes de una corrida. Se relajan al reintentar."""
    min_silencio_ms: float = MIN_SILENCIO_MS
    pad_antes_ms: float = PAD_ANTES_MS
    pad_despues_ms: float = PAD_DESPUES_MS
    min_entre_palabras_ms: float = MIN_ENTRE_PALABRAS_MS
    captura_fade_ms: float = 0.0   # cuánta cola recupera el umbral actual (0 = sin relajar)

    def relajado(self) -> "ParametrosCorte":
        """Umbral +3 dB (→ más captura de cola) y padding +50 ms antes y después."""
        return ParametrosCorte(
            min_silencio_ms=self.min_silencio_ms,
            pad_antes_ms=self.pad_antes_ms + RELAX_PAD_MS,
            pad_despues_ms=self.pad_despues_ms + RELAX_PAD_MS,
            min_entre_palabras_ms=self.min_entre_palabras_ms,
            captura_fade_ms=self.captura_fade_ms + RELAX_CAPTURA_FADE_MS,
        )


@dataclass
class Verificacion:
    """Resultado de la verificación §E6. `ok` solo si NO se perdió ninguna palabra
    y el WER está dentro del criterio. Nunca falla en silencio (regla 3)."""
    ok: bool
    palabras_original: int
    palabras_resultado: int
    palabras_perdidas: int
    wer: float
    detalle: str = ""


@dataclass
class ResultadoCorte:
    """Lo que entrega el pipeline. Si `entrego_original` es True, no se pudo cortar
    sin riesgo tras `iteraciones` intentos y se devuelve el material intacto con el
    motivo — jamás un corte que destruye habla (§E6)."""
    cortes: list[Corte]
    verificacion: Optional[Verificacion]
    iteraciones: int
    entrego_original: bool
    motivo: str
    params_finales: ParametrosCorte

    @property
    def segundos_recortados(self) -> float:
        return round(sum(c.dur_ms for c in self.cortes) / 1000.0, 3)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


# ── 1. planificación de cortes (§E6) ─────────────────────────────────────────
def plan_cortes(palabras: list[Palabra], params: Optional[ParametrosCorte] = None) -> list[Corte]:
    """Calcula qué silencios ELIMINAR sin tocar habla (§E6).

    Regla por hueco entre dos palabras consecutivas:
      - Si el hueco < `min_entre_palabras_ms` (300 ms): misma oración, NO se corta.
      - Si el hueco < `min_silencio_ms` (500 ms): silencio demasiado corto, NO se corta.
      - Si es cortable: se conserva `pad_despues` tras la palabra previa y `pad_antes`
        antes de la siguiente. El tramo removible es lo que quede EN MEDIO. Si el
        padding se come el hueco entero, no queda nada que cortar (y así debe ser:
        más vale un silencio natural que una consonante recortada).

    El padding es, además, el "pequeño silencio natural" que Arturo quiere conservar
    entre párrafos (r.49): no deja los cortes pegados y secos.
    """
    p = params or ParametrosCorte()
    cortes: list[Corte] = []
    if len(palabras) < 2:
        return cortes
    pad_antes = p.pad_antes_ms / 1000.0
    pad_despues = p.pad_despues_ms / 1000.0
    for prev, nxt in zip(palabras, palabras[1:]):
        hueco_ms = (nxt.inicio - prev.fin) * 1000.0
        if hueco_ms < p.min_entre_palabras_ms:      # <300 ms: misma oración
            continue
        if hueco_ms < p.min_silencio_ms:            # <500 ms: no alcanza a ser corte
            continue
        ini = prev.fin + pad_despues
        fin = nxt.inicio - pad_antes
        if fin - ini > 1e-9:                        # queda algo que cortar tras el padding
            cortes.append(Corte(inicio=round(ini, 6), fin=round(fin, 6)))
    return cortes


def _corte_invade_habla(palabras: list[Palabra], cortes: list[Corte],
                        params: ParametrosCorte) -> Optional[str]:
    """Invariante estructural, independiente de la transcripción: ningún corte
    puede solaparse con el span REAL de una palabra ni con su padding obligatorio.
    Devuelve un mensaje si algo invade habla, o None si está limpio. Este chequeo
    es barato y atrapa un bug de planificación antes de gastar en Whisper."""
    pad_antes = params.pad_antes_ms / 1000.0
    pad_despues = params.pad_despues_ms / 1000.0
    for c in cortes:
        for w in palabras:
            # zona protegida: la palabra + su padding a cada lado
            prot_ini = w.inicio - pad_antes
            prot_fin = w.fin + pad_despues
            if c.inicio < prot_fin and c.fin > prot_ini:
                return (f"corte [{c.inicio:.3f},{c.fin:.3f}] invade la zona protegida "
                        f"de '{w.texto}' [{prot_ini:.3f},{prot_fin:.3f}]")
    return None


# ── 2. verificación §E6 (WER + palabras perdidas) ────────────────────────────
def _wer(ref: list[str], hyp: list[str]) -> float:
    """Word Error Rate = (sustituciones+inserciones+borrados)/palabras_ref, por
    distancia de edición a nivel palabra (Levenshtein). Referencia = original."""
    n, m = len(ref), len(hyp)
    if n == 0:
        return 0.0 if m == 0 else 1.0
    dp = list(range(m + 1))
    for i in range(1, n + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, m + 1):
            cur = dp[j]
            costo = 0 if ref[i - 1] == hyp[j - 1] else 1
            dp[j] = min(dp[j] + 1,        # borrado
                        dp[j - 1] + 1,    # inserción
                        prev + costo)     # sustitución/acierto
            prev = cur
    return dp[m] / n


def _palabras_texto(palabras: list[Palabra]) -> list[str]:
    return [w.texto.lower() for w in palabras if w.texto.strip()]


def verificar_corte(palabras_original: list[str], palabras_resultado: list[str]) -> Verificacion:
    """Compara las dos transcripciones (original vs resultado del corte). `ok` solo
    si no se perdió ninguna palabra Y el WER ≤ 2 % (§E6). Loggea el detalle siempre."""
    n_orig, n_res = len(palabras_original), len(palabras_resultado)
    perdidas = max(0, n_orig - n_res)
    wer = _wer(palabras_original, palabras_resultado)
    ok = perdidas <= MAX_PALABRAS_PERDIDAS and wer <= MAX_WER
    detalle = (f"palabras {n_orig}→{n_res} (perdidas {perdidas}); "
               f"WER {wer:.4f} (máx {MAX_WER}); {'OK' if ok else 'FALLA'}")
    return Verificacion(ok=ok, palabras_original=n_orig, palabras_resultado=n_res,
                        palabras_perdidas=perdidas, wer=round(wer, 4), detalle=detalle)


# ── 3. oráculo de laboratorio: modela el fallo real de r.49 ──────────────────
def transcribir_resultado_simulado(palabras: list[Palabra], cortes: list[Corte],
                                   params: ParametrosCorte) -> list[str]:
    """Devuelve la transcripción que resultaría del corte, modelando EXACTAMENTE
    el fallo de r.49: una palabra se pierde si el detector (a este umbral) no
    capturó toda su cola de fade Y el padding que se conservó no alcanza a cubrir
    lo que faltó — entonces el corte siguiente muerde la consonante final y Whisper
    ya no la lee. Una palabra está a salvo si `captura_fade + pad_despues ≥ cola_ms`.

    Es el oráculo del laboratorio (r.20): permite probar la verificación §E6 y su
    loop de relajación sin audio ni Whisper real. En producción se inyecta el
    Whisper de verdad sobre el clip ya cortado."""
    cobertura = params.captura_fade_ms + params.pad_despues_ms
    salida: list[str] = []
    # ¿hay algún corte que empiece justo después de esta palabra? El corte que
    # sigue a una palabra arranca exactamente en `fin + pad_despues`, así que la
    # ventana es esa (no un fudge). Si no hay corte tras ella, su cola no peligra.
    ventana = params.pad_despues_ms / 1000.0 + 1e-3
    inicios_corte = sorted(c.inicio for c in cortes)
    for w in palabras:
        if not w.texto.strip():
            continue
        hay_corte_despues = any(w.fin - 1e-6 <= ci <= w.fin + ventana
                                for ci in inicios_corte)
        if w.cola_ms > 0 and hay_corte_despues and cobertura < w.cola_ms - 1e-9:
            continue  # la consonante final se recortó: Whisper ya no lee esta palabra
        salida.append(w.texto.lower())
    return salida


# ── 4. pipeline con verificación y relajación (§E6) ──────────────────────────
def cortar_con_verificacion(
    palabras: list[Palabra],
    transcribir_resultado: Optional[Callable[[list[Palabra], list[Corte], ParametrosCorte], list[str]]] = None,
    params: Optional[ParametrosCorte] = None,
    logger: Optional[Callable[[str], None]] = None,
) -> ResultadoCorte:
    """Planifica los cortes, VERIFICA que no destruyan habla y, si fallan, relaja
    umbral+padding y reintenta (máx 3, §E6). Si tras los reintentos sigue fallando,
    entrega el ORIGINAL con el reporte "no pude cortar sin riesgo".

    `transcribir_resultado(palabras, cortes, params) -> list[str]` es el puerto
    inyectable: en producción transcribe el clip cortado con Whisper; en pruebas y
    en el laboratorio se usa `transcribir_resultado_simulado`. Nunca abre red solo.
    """
    log = logger or (lambda m: None)
    transcribir = transcribir_resultado or transcribir_resultado_simulado
    orig_texto = _palabras_texto(palabras)
    p = params or ParametrosCorte()

    ultimo_cortes: list[Corte] = []
    ultima_verif: Optional[Verificacion] = None
    for it in range(1, MAX_ITER + 1):
        cortes = plan_cortes(palabras, p)
        ultimo_cortes = cortes
        # invariante estructural barato antes de "transcribir"
        invasion = _corte_invade_habla(palabras, cortes, p)
        if invasion:
            log(f"[corte-silencios] iter {it}: INVARIANTE ROTO — {invasion}")
            verif = Verificacion(ok=False, palabras_original=len(orig_texto),
                                 palabras_resultado=len(orig_texto), palabras_perdidas=0,
                                 wer=0.0, detalle=f"corte invade habla: {invasion}")
        else:
            res_texto = transcribir(palabras, cortes, p)
            verif = verificar_corte(orig_texto, res_texto)
        ultima_verif = verif
        log(f"[corte-silencios] iter {it}: {len(cortes)} cortes, "
            f"{round(sum(c.dur_ms for c in cortes)/1000.0,2)}s recortados; {verif.detalle}")
        if verif.ok and not invasion:
            return ResultadoCorte(cortes=cortes, verificacion=verif, iteraciones=it,
                                  entrego_original=False,
                                  motivo=f"corte verificado sin pérdida de habla ({verif.detalle})",
                                  params_finales=p)
        if it < MAX_ITER:
            p = p.relajado()
            log(f"[corte-silencios] relajo umbral +3dB y padding +{RELAX_PAD_MS}ms "
                f"(pad_despues={p.pad_despues_ms}ms, captura_fade={p.captura_fade_ms}ms)")

    # agotados los reintentos: entrega el original, NUNCA un corte que destruye habla
    log("[corte-silencios] AGOTADO: no pude cortar sin riesgo → entrego el original")
    return ResultadoCorte(cortes=[], verificacion=ultima_verif, iteraciones=MAX_ITER,
                          entrego_original=True,
                          motivo="no pude cortar sin riesgo; entrego el material original (§E6)",
                          params_finales=p)


# ── CLI ──────────────────────────────────────────────────────────────────────
def main(argv: Optional[list[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Corte de silencios §E6 con verificación (AU-3)")
    ap.add_argument("palabras", help="ruta a JSON [{inicio,fin,texto,cola_ms?}, ...]")
    args = ap.parse_args(argv)

    datos = json.loads(Path(args.palabras).read_text(encoding="utf-8"))
    palabras = [Palabra(**d) for d in datos]
    res = cortar_con_verificacion(palabras, logger=lambda m: print(m))

    print("\n── resultado ──")
    if res.entrego_original:
        print(f"⚠ {res.motivo}")
    else:
        print(f"✓ {len(res.cortes)} cortes · {res.segundos_recortados}s recortados · "
              f"{res.iteraciones} iteración(es)")
        for c in res.cortes:
            print(f"   cortar [{c.inicio:.3f}s → {c.fin:.3f}s]  ({c.dur_ms:.0f} ms)")
    if res.verificacion:
        print(f"verificación §E6: {res.verificacion.detalle}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
