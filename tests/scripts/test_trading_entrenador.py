"""Pruebas del entrenador de trading (Bloque AT, r.36-43 / r.40 / r.91).

Clavan lo que de verdad importa del laboratorio de entrenamiento, todo con
dobles LOCALES (nada de red, nada de Binance real — candado r.119):

  (1) el freno duro -3% diario dispara y BLOQUEA nuevas entradas;
  (2) la señal exige el CRUCE de las tres condiciones (dip + RSI + sentimiento):
      si falta una, no entra;
  (3) nunca se compromete más capital del disponible ni se supera el tope 5000;
  (4) fees y slippage se aplican en cada fill;
  (5) el RSI de Wilder da el valor esperado en un caso conocido;
  (6) take-profit y stop-loss por operación cierran como deben.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))

from trading_entrenador import (  # noqa: E402
    CAPITAL_MAX_MXN,
    EntrenadorTrading,
    FrenoDiarioActivado,
    Operacion,
    calcular_rsi,
)


# --------------------------------------------------------------------------- #
# Dobles locales inyectables                                                   #
# --------------------------------------------------------------------------- #

class MercadoFalso:
    def __init__(self, cierres, precio):
        self._cierres = list(cierres)
        self._precio = precio

    def historial_cierres(self, simbolo):
        return self._cierres

    def precio_actual(self, simbolo):
        return self._precio


class SentimientoFalso:
    def __init__(self, valor):
        self._valor = valor

    def score(self, simbolo):
        return self._valor


def _serie_caida(referencia=100.0, actual=90.0, n=20):
    """Serie que baja de forma sostenida: RSI bajo (sobreventa) y caída ≥10%."""
    paso = (referencia - actual) / (n - 1)
    return [referencia - paso * i for i in range(n)]


def _entrenador(cierres, precio, senti, **kw):
    return EntrenadorTrading(
        mercado=MercadoFalso(cierres, precio),
        sentimiento=SentimientoFalso(senti),
        **kw,
    )


HOY = date(2026, 8, 2)


# --------------------------------------------------------------------------- #
# (5) RSI                                                                      #
# --------------------------------------------------------------------------- #

def test_rsi_sin_datos_devuelve_none():
    assert calcular_rsi([1, 2, 3], periodo=14) is None


def test_rsi_serie_solo_sube_es_100():
    assert calcular_rsi(list(range(1, 20)), periodo=14) == 100.0


def test_rsi_caida_sostenida_es_muy_bajo():
    rsi = calcular_rsi(_serie_caida(), periodo=14)
    assert rsi is not None and rsi < 30.0  # sobreventa


# --------------------------------------------------------------------------- #
# (2) La señal exige el cruce de las tres condiciones                         #
# --------------------------------------------------------------------------- #

def test_senal_completa_entra():
    e = _entrenador(_serie_caida(), 90.0, 0.5)
    entra, det = e.hay_senal_entrada("BTCMXN")
    assert entra is True
    assert det["cond_caida"] and det["cond_rsi"] and det["cond_sentimiento"]


def test_sin_caida_no_entra():
    # precio en el máximo: no hay dip aunque el sentimiento sea alcista
    cierres = list(range(80, 100))
    e = _entrenador(cierres, 99.0, 0.9)
    entra, det = e.hay_senal_entrada("BTCMXN")
    assert entra is False and det["cond_caida"] is False


def test_sentimiento_bajista_no_entra():
    # caída y RSI bajo, pero las noticias apuntan a BAJA -> no se arriesga
    e = _entrenador(_serie_caida(), 90.0, -0.5)
    entra, det = e.hay_senal_entrada("BTCMXN")
    assert entra is False and det["cond_sentimiento"] is False
    assert det["cond_caida"] and det["cond_rsi"]  # las otras dos sí


def test_rsi_alto_no_entra():
    # cae de golpe al final pero venía subiendo -> RSI no está en sobreventa
    cierres = [80 + i for i in range(19)] + [90.0]
    e = _entrenador(cierres, 90.0, 0.9)
    entra, det = e.hay_senal_entrada("BTCMXN")
    assert det["cond_rsi"] is False and entra is False


# --------------------------------------------------------------------------- #
# (3) Capital: nunca más del disponible; el tope 5000 es duro                  #
# --------------------------------------------------------------------------- #

def test_capital_sobre_tope_es_rechazado():
    with pytest.raises(ValueError):
        _entrenador(_serie_caida(), 90.0, 0.5, capital_inicial=CAPITAL_MAX_MXN + 1)


def test_no_compromete_mas_del_disponible():
    e = _entrenador(_serie_caida(), 90.0, 0.5, capital_inicial=1000.0,
                    fraccion=0.20)
    e.abrir("BTCMXN", hoy=HOY)
    # 20% de 1000 comprometido -> quedan ~800 libres, nunca negativo
    assert e.capital == pytest.approx(800.0, abs=1e-6)
    assert e.capital >= 0


def test_capital_no_negativo_tras_varias_entradas():
    e = _entrenador(_serie_caida(), 90.0, 0.5, capital_inicial=1000.0,
                    fraccion=0.5)
    for _ in range(10):
        try:
            e.abrir("BTCMXN", hoy=HOY)
        except FrenoDiarioActivado:
            break
    assert e.capital >= 0


# --------------------------------------------------------------------------- #
# (4) Fees y slippage se aplican                                               #
# --------------------------------------------------------------------------- #

def test_fee_y_slippage_en_la_compra():
    e = _entrenador(_serie_caida(), 90.0, 0.5, capital_inicial=1000.0,
                    fraccion=1.0, comision=0.001, slippage=0.0005)
    op = e.abrir("BTCMXN", hoy=HOY)
    assert op is not None
    # precio de fill peor que el de mercado por el slippage
    assert op.precio_entrada == pytest.approx(90.0 * 1.0005)
    # unidades = (comprometido * (1-fee)) / precio_fill
    esperado = (1000.0 * 0.999) / (90.0 * 1.0005)
    assert op.unidades == pytest.approx(esperado)


# --------------------------------------------------------------------------- #
# (1) EL FRENO -3% DIARIO — el invariante crítico (r.40 CONFIRMADO)            #
# --------------------------------------------------------------------------- #

def test_freno_dispara_y_bloquea_nuevas_entradas():
    e = _entrenador(_serie_caida(), 90.0, 0.5, capital_inicial=1000.0,
                    fraccion=1.0)
    op = e.abrir("BTCMXN", hoy=HOY)          # compromete todo el capital
    assert e.freno_activado is False
    # el mercado se desploma un 10%: al cerrar, la pérdida supera el -3% del día
    e.cerrar(op, 81.0, "stop_manual", hoy=HOY)
    assert e.freno_activado is True
    # y ya no deja abrir nada más ese día
    with pytest.raises(FrenoDiarioActivado):
        e.abrir("BTCMXN", hoy=HOY)


def test_freno_no_dispara_con_perdida_menor_al_3pct():
    e = _entrenador(_serie_caida(), 90.0, 0.5, capital_inicial=1000.0,
                    fraccion=1.0)
    op = e.abrir("BTCMXN", hoy=HOY)
    e.cerrar(op, 89.0, "cierre", hoy=HOY)    # pérdida ~1.5%, bajo el umbral
    assert e.freno_activado is False


def test_freno_se_reinicia_al_cambiar_de_dia():
    e = _entrenador(_serie_caida(), 90.0, 0.5, capital_inicial=1000.0,
                    fraccion=1.0)
    op = e.abrir("BTCMXN", hoy=HOY)
    e.cerrar(op, 81.0, "stop", hoy=HOY)
    assert e.freno_activado is True
    manana = date(2026, 8, 3)
    # nuevo día: la referencia del freno se reinicia y vuelve a operar
    e.abrir("BTCMXN", hoy=manana)
    assert e.freno_activado is False


# --------------------------------------------------------------------------- #
# (6) Salidas: take-profit y stop-loss                                        #
# --------------------------------------------------------------------------- #

def test_take_profit_cierra_en_ganancia():
    e = _entrenador(_serie_caida(), 90.0, 0.5, capital_inicial=1000.0,
                    fraccion=1.0, take_profit=0.06)
    op = e.abrir("BTCMXN", hoy=HOY)
    entrada = op.precio_entrada
    e.evaluar_salidas({"BTCMXN": entrada * 1.07}, hoy=HOY)  # +7% > +6%
    assert op.cerrada and op.motivo_cierre == "take_profit"
    assert (op.resultado_mxn or 0) > 0


def test_stop_loss_cierra_en_perdida():
    e = _entrenador(_serie_caida(), 90.0, 0.5, capital_inicial=1000.0,
                    fraccion=1.0, stop_loss_op=0.04)
    op = e.abrir("BTCMXN", hoy=HOY)
    entrada = op.precio_entrada
    e.evaluar_salidas({"BTCMXN": entrada * 0.95}, hoy=HOY)  # -5% < -4%
    assert op.cerrada and op.motivo_cierre == "stop_loss"
    assert (op.resultado_mxn or 0) < 0


def test_resumen_reporta_numeros_no_promesas():
    e = _entrenador(_serie_caida(), 90.0, 0.5, capital_inicial=1000.0,
                    fraccion=0.5)
    op = e.abrir("BTCMXN", hoy=HOY)
    e.cerrar(op, op.precio_entrada * 1.06, "take_profit", hoy=HOY)
    r = e.resumen()
    assert r["operaciones"] == 1 and r["cerradas"] == 1
    assert set(r) >= {"capital_inicial", "pnl_realizado_mxn", "win_rate",
                      "freno_activado"}
