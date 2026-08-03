#!/usr/bin/env python3
"""
trading_entrenador.py — El laboratorio de trading de Hermes (ENTRENAMIENTO).

Bloque AT (Fase 10 / OT-10 / B4). Gobernado por r.36-43 y r.91 del
CUESTIONARIO_MAESTRO y por las decisiones del 01 ago en DECISIONES.md.

QUÉ ES Y QUÉ NO ES
------------------
- ES un simulador de estrategia sobre la **testnet de Binance** (cuenta
  verificada, SIN fondos reales) con capital SIMULADO de hasta 5,000 MXN,
  ciclos SEMANALES. Su meta es ENTRENAR una estrategia y REPORTAR números
  reales. La meta "2,000/semana" (r.36) es objetivo de entrenamiento, NO una
  promesa: aquí no se promete rendimiento, se mide.
- NO mueve dinero real. El dinero real sigue atado a B4 (2 meses de papel
  medido) y a propone-y-apruebas SIEMPRE (DECISIONES 01 ago).

LA ESTRATEGIA — buy-the-dip informado por sentimiento (r.36-43)
---------------------------------------------------------------
Arturo, textual: "si una cripto cae pero las noticias apuntan a que sube en la
semana, se arriesga". La investigación web (02 ago, ver ESTADO) es clara en que
comprar la caída A SECAS rinde mal —se queda uno invertido dentro de los bear
markets—. Por eso la entrada exige el CRUCE de tres condiciones, no una:

    1. CAÍDA   — el precio cayó ≥ `umbral_caida` respecto a su referencia.
    2. AGOTAMIENTO — RSI < `rsi_sobreventa` (la caída está exhausta, no en
       caída libre); confirma que el dip es un pullback y no el inicio de un
       desplome.
    3. SENTIMIENTO ALCISTA — la señal de noticias/mercado apunta a alza
       (divergencia clásica: miedo extremo + acumulación => rebote probable).

Si las tres se cumplen, se arriesga una fracción del capital. Salida por
take-profit, stop-loss por operación, o cierre al terminar el ciclo semanal.

EL FRENO DURO -3% DIARIO (r.40, CONFIRMADO — "que quede así -3%")
----------------------------------------------------------------
Circuit-breaker independiente de la estrategia: si en un día la pérdida
acumulada llega a -3% del capital con el que abrió el día, Hermes DETIENE toda
entrada nueva por ese día y avisa. No contradice la estrategia (esta busca
ganar); solo evita el día catastrófico. Con $2,000 reales = apagado al perder
$60. Aquí opera sobre el capital simulado.

ARQUITECTURA — todo inyectable (r.119: nada de red en pruebas)
--------------------------------------------------------------
Esta sesión corre en el HOST con credenciales de PRODUCCIÓN y SIN canal QA. Por
eso el módulo NO golpea ningún servicio real por sí mismo: el cliente de mercado
y la fuente de sentimiento son INYECTABLES. En pruebas se inyectan dobles
locales; la conexión EN VIVO a la testnet (`MercadoBinanceTestnet`) queda como
paso documentado que exige keys en `.env` y correr dentro del laboratorio
Docker/QA (ver ESTADO.md, pendiente de despliegue).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Optional, Protocol, Sequence

# --------------------------------------------------------------------------- #
# Parámetros por defecto (calibrables; se ajustan con los resultados del lab)  #
# --------------------------------------------------------------------------- #

CAPITAL_MAX_MXN = 5_000.0          # tope duro de capital simulado (r.36-43)
FRENO_DIARIO = 0.03                # -3% diario (r.40, CONFIRMADO)
COMISION_SPOT = 0.001              # 0.1% por lado (fee spot típico de Binance)
SLIPPAGE = 0.0005                  # 0.05% de deslizamiento por fill

UMBRAL_CAIDA = 0.05               # cae ≥5% vs. referencia para considerar dip
RSI_SOBREVENTA = 30.0             # RSI < 30 = agotamiento de vendedores
SENTIMIENTO_ALCISTA = 0.15        # score de sentimiento ≥ esto = apunta a alza
FRACCION_POR_OPERACION = 0.20     # se arriesga 20% del capital disponible
TAKE_PROFIT = 0.06               # cierra en +6%
STOP_LOSS_OP = 0.04              # stop por operación en -4%


class FrenoDiarioActivado(RuntimeError):
    """Se intentó operar con el freno -3% del día ya disparado."""


# --------------------------------------------------------------------------- #
# Indicadores                                                                  #
# --------------------------------------------------------------------------- #

def calcular_rsi(precios: Sequence[float], periodo: int = 14) -> Optional[float]:
    """RSI de Wilder sobre una serie de cierres.

    Devuelve None si no hay suficientes datos (< periodo+1 precios): sin
    historia no se inventa una señal —el silencio se reporta como None, no
    como un número falso (regla 3: el silencio nunca es un fallo mudo)—.
    """
    if len(precios) < periodo + 1:
        return None
    ganancias = 0.0
    perdidas = 0.0
    # Primer promedio: media simple de las primeras `periodo` variaciones.
    for i in range(1, periodo + 1):
        delta = precios[i] - precios[i - 1]
        if delta >= 0:
            ganancias += delta
        else:
            perdidas -= delta
    avg_g = ganancias / periodo
    avg_p = perdidas / periodo
    # Suavizado de Wilder para el resto de la serie.
    for i in range(periodo + 1, len(precios)):
        delta = precios[i] - precios[i - 1]
        subida = max(delta, 0.0)
        bajada = max(-delta, 0.0)
        avg_g = (avg_g * (periodo - 1) + subida) / periodo
        avg_p = (avg_p * (periodo - 1) + bajada) / periodo
    if avg_p == 0:
        return 100.0
    rs = avg_g / avg_p
    return 100.0 - (100.0 / (1.0 + rs))


# --------------------------------------------------------------------------- #
# Puertos inyectables                                                          #
# --------------------------------------------------------------------------- #

class FuenteMercado(Protocol):
    """De dónde salen los precios. La implementación real habla con Binance
    testnet; en pruebas se inyecta un doble local."""

    def historial_cierres(self, simbolo: str) -> Sequence[float]:
        ...

    def precio_actual(self, simbolo: str) -> float:
        ...


class FuenteSentimiento(Protocol):
    """Señal de noticias/mercado en [-1, 1]: <0 bajista, >0 alcista.
    r.91: a APIs gratis solo van números (montos/tickets), nunca texto de
    correos/nombres/salud; un score numérico de sentimiento es apto."""

    def score(self, simbolo: str) -> float:
        ...


@dataclass
class Operacion:
    simbolo: str
    precio_entrada: float
    unidades: float
    costo_mxn: float          # capital comprometido, ya con fee+slippage
    abierta_en: str
    precio_salida: Optional[float] = None
    resultado_mxn: Optional[float] = None
    motivo_cierre: Optional[str] = None

    @property
    def cerrada(self) -> bool:
        return self.precio_salida is not None


# --------------------------------------------------------------------------- #
# El entrenador                                                                #
# --------------------------------------------------------------------------- #

@dataclass
class EntrenadorTrading:
    """Motor de la estrategia sobre capital SIMULADO.

    `mercado` y `sentimiento` son inyectables: sin ellos el motor no toca red.
    """

    mercado: FuenteMercado
    sentimiento: FuenteSentimiento
    capital_inicial: float = CAPITAL_MAX_MXN
    umbral_caida: float = UMBRAL_CAIDA
    rsi_sobreventa: float = RSI_SOBREVENTA
    sentimiento_alcista: float = SENTIMIENTO_ALCISTA
    fraccion: float = FRACCION_POR_OPERACION
    take_profit: float = TAKE_PROFIT
    stop_loss_op: float = STOP_LOSS_OP
    comision: float = COMISION_SPOT
    slippage: float = SLIPPAGE

    capital: float = field(init=False)
    operaciones: list[Operacion] = field(default_factory=list, init=False)
    log: list[str] = field(default_factory=list, init=False)

    # Estado del freno diario.
    _dia: Optional[date] = field(default=None, init=False)
    _capital_apertura_dia: float = field(default=0.0, init=False)
    _frenado_hoy: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if self.capital_inicial > CAPITAL_MAX_MXN:
            raise ValueError(
                f"capital {self.capital_inicial} excede el tope simulado "
                f"de {CAPITAL_MAX_MXN} MXN (r.36-43)."
            )
        self.capital = self.capital_inicial

    # -- freno diario ------------------------------------------------------- #
    def _asegurar_dia(self, hoy: date) -> None:
        """Al cambiar el día, se reinicia la marca de referencia del freno."""
        if self._dia != hoy:
            self._dia = hoy
            self._capital_apertura_dia = self.capital
            self._frenado_hoy = False

    @property
    def freno_activado(self) -> bool:
        return self._frenado_hoy

    def _revisar_freno(self, hoy: date) -> bool:
        """Devuelve True si el freno -3% del día está (o quedó) disparado."""
        self._asegurar_dia(hoy)
        if self._frenado_hoy:
            return True
        piso = self._capital_apertura_dia * (1.0 - FRENO_DIARIO)
        if self.capital <= piso:
            self._frenado_hoy = True
            self._log(
                f"FRENO -3% DISPARADO: capital {self.capital:.2f} ≤ piso "
                f"{piso:.2f} (apertura {self._capital_apertura_dia:.2f}). "
                f"Sin más entradas hoy. AVISO A ARTURO PENDIENTE (r.119)."
            )
        return self._frenado_hoy

    # -- señal de entrada --------------------------------------------------- #
    def hay_senal_entrada(self, simbolo: str) -> tuple[bool, dict]:
        """Evalúa el CRUCE de las tres condiciones. Devuelve (entra, detalle)
        siempre con el detalle de cada condición, aunque no entre (regla 3:
        loguear éxito Y no-señal, nunca silencio)."""
        cierres = list(self.mercado.historial_cierres(simbolo))
        precio = self.mercado.precio_actual(simbolo)
        referencia = max(cierres) if cierres else precio
        caida = (referencia - precio) / referencia if referencia else 0.0
        rsi = calcular_rsi(cierres)
        senti = self.sentimiento.score(simbolo)

        cond_caida = caida >= self.umbral_caida
        cond_rsi = rsi is not None and rsi < self.rsi_sobreventa
        cond_senti = senti >= self.sentimiento_alcista
        entra = cond_caida and cond_rsi and cond_senti

        detalle = {
            "simbolo": simbolo, "precio": precio, "referencia": referencia,
            "caida": round(caida, 4), "rsi": None if rsi is None else round(rsi, 2),
            "sentimiento": round(senti, 4),
            "cond_caida": cond_caida, "cond_rsi": cond_rsi,
            "cond_sentimiento": cond_senti, "entra": entra,
        }
        return entra, detalle

    # -- operar ------------------------------------------------------------- #
    def abrir(self, simbolo: str, hoy: Optional[date] = None) -> Optional[Operacion]:
        """Abre una operación si hay señal y el freno no está disparado."""
        hoy = hoy or datetime.now().date()
        if self._revisar_freno(hoy):
            raise FrenoDiarioActivado(
                "freno -3% del día activo: no se abren operaciones"
            )
        entra, detalle = self.hay_senal_entrada(simbolo)
        if not entra:
            self._log(f"sin señal en {simbolo}: {detalle}")
            return None

        # Dimensionamiento: fracción del capital disponible, nunca más del que hay.
        comprometido = min(self.capital * self.fraccion, self.capital)
        if comprometido <= 0:
            self._log(f"sin capital disponible para {simbolo}")
            return None
        precio = detalle["precio"]
        precio_fill = precio * (1.0 + self.slippage)          # compras "peor"
        unidades = (comprometido * (1.0 - self.comision)) / precio_fill

        self.capital -= comprometido
        op = Operacion(
            simbolo=simbolo, precio_entrada=precio_fill, unidades=unidades,
            costo_mxn=comprometido, abierta_en=hoy.isoformat(),
        )
        self.operaciones.append(op)
        self._log(
            f"ABRE {simbolo} @ {precio_fill:.4f} | {unidades:.6f} u | "
            f"comprometido {comprometido:.2f} MXN | capital libre {self.capital:.2f}"
        )
        return op

    def cerrar(self, op: Operacion, precio: float, motivo: str,
               hoy: Optional[date] = None) -> float:
        """Cierra una operación al precio dado; abona el resultado al capital y
        revisa el freno con el capital ya actualizado."""
        hoy = hoy or datetime.now().date()
        if op.cerrada:
            return op.resultado_mxn or 0.0
        precio_fill = precio * (1.0 - self.slippage)          # vendes "peor"
        bruto = op.unidades * precio_fill
        neto = bruto * (1.0 - self.comision)
        self.capital += neto
        op.precio_salida = precio_fill
        op.resultado_mxn = neto - op.costo_mxn
        op.motivo_cierre = motivo
        self._log(
            f"CIERRA {op.simbolo} @ {precio_fill:.4f} ({motivo}) | "
            f"resultado {op.resultado_mxn:+.2f} MXN | capital {self.capital:.2f}"
        )
        self._revisar_freno(hoy)
        return op.resultado_mxn

    def evaluar_salidas(self, precios: dict[str, float],
                        hoy: Optional[date] = None) -> None:
        """Aplica take-profit / stop-loss por operación a las abiertas."""
        for op in self.operaciones:
            if op.cerrada or op.simbolo not in precios:
                continue
            precio = precios[op.simbolo]
            rend = (precio - op.precio_entrada) / op.precio_entrada
            if rend >= self.take_profit:
                self.cerrar(op, precio, "take_profit", hoy)
            elif rend <= -self.stop_loss_op:
                self.cerrar(op, precio, "stop_loss", hoy)

    # -- reporte ------------------------------------------------------------ #
    def valor_en_riesgo(self, precios: dict[str, float]) -> float:
        """Valor de mercado de las posiciones abiertas."""
        total = 0.0
        for op in self.operaciones:
            if not op.cerrada and op.simbolo in precios:
                total += op.unidades * precios[op.simbolo]
        return total

    def resumen(self) -> dict:
        cerradas = [o for o in self.operaciones if o.cerrada]
        ganadas = [o for o in cerradas if (o.resultado_mxn or 0) > 0]
        pnl = self.capital - self.capital_inicial
        return {
            "capital_inicial": round(self.capital_inicial, 2),
            "capital_libre": round(self.capital, 2),
            "pnl_realizado_mxn": round(pnl, 2),
            "operaciones": len(self.operaciones),
            "cerradas": len(cerradas),
            "ganadas": len(ganadas),
            "win_rate": round(len(ganadas) / len(cerradas), 3) if cerradas else None,
            "freno_activado": self._frenado_hoy,
        }

    def _log(self, msg: str) -> None:
        self.log.append(f"{datetime.now().isoformat(timespec='seconds')} {msg}")


# --------------------------------------------------------------------------- #
# Implementación EN VIVO (testnet) — PENDIENTE de keys + laboratorio (r.119)   #
# --------------------------------------------------------------------------- #

class MercadoBinanceTestnet:
    """Cliente real contra la **testnet** de Binance (sin fondos).

    NO se usa en esta sesión: corre en el HOST con credenciales de producción y
    sin canal QA (candado r.119). Requiere BINANCE_TESTNET_API_KEY /
    _API_SECRET en `.env` y correr dentro del laboratorio Docker/QA. Se deja
    cableado para que el despliegue sea solo inyectarlo en EntrenadorTrading.
    """

    def __init__(self, api_key: Optional[str] = None,
                 api_secret: Optional[str] = None, intervalo: str = "1h"):
        from binance.client import Client  # import perezoso: pruebas no lo cargan

        api_key = api_key or os.environ.get("BINANCE_TESTNET_API_KEY", "")
        api_secret = api_secret or os.environ.get("BINANCE_TESTNET_API_SECRET", "")
        if not api_key or not api_secret:
            raise RuntimeError(
                "faltan BINANCE_TESTNET_API_KEY/_SECRET en .env — la conexión "
                "en vivo a la testnet queda PENDIENTE (ver ESTADO.md)."
            )
        # testnet=True apunta al Spot Testnet (https://testnet.binance.vision).
        self.client = Client(api_key, api_secret, testnet=True)
        self.intervalo = intervalo

    def historial_cierres(self, simbolo: str) -> Sequence[float]:
        klines = self.client.get_klines(symbol=simbolo, interval=self.intervalo,
                                         limit=100)
        return [float(k[4]) for k in klines]  # índice 4 = precio de cierre

    def precio_actual(self, simbolo: str) -> float:
        return float(self.client.get_symbol_ticker(symbol=simbolo)["price"])


if __name__ == "__main__":  # pragma: no cover
    print(__doc__)
