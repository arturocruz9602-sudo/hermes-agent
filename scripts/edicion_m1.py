#!/usr/bin/env python3
"""edicion_m1 — Bloque AU-3, Piezas 2 y 3 (HAS Fase 8 / OT-8; r.102).

Lleva la lista de cortes aprobada (Pieza 1, `corte_silencios`) a la línea de
tiempo de DaVinci Resolve en la MacBook M1, por SSH desde Hermes. Dos cosas que
importan por igual:

  PIEZA 2 — La M1 es PRESTADA (r.102). Es el equipo de trabajo de Arturo, no de
  Hermes. Toda configuración nocturna (p. ej. `caffeinate`, para que no se
  duerma mientras renderiza) se APLICA → se USA → se REVIERTE antes de las 06:00
  → se VERIFICA revertida. La Mac queda EXACTAMENTE como estaba. `SesionM1` es el
  sobre de seguridad que garantiza esto con triple candado:
    (a) reversión en `finally` — ocurre aunque el trabajo reviente a media noche;
    (b) verificación explícita de que revirtió — si no, ALARMA, nunca en silencio;
    (c) auto-expiración del lado de la Mac (`caffeinate -t`) atada al deadline —
        si Hermes muere de golpe (sin `__exit__`), la config igual se cae sola
        antes de las 06:00 ("por si salgo y olvido apagarla", r.102).

  PIEZA 3 — Edición de línea de tiempo vía la API Python de DaVinci Resolve
  Studio (OT-8): crear proyecto desde template → importar la carpeta indicada →
  clips al timeline en orden → aplicar los cortes aprobados → guardar. **SIN
  render, SIN efectos**: el proyecto queda ABIERTO para que Arturo lo revise
  (DECISIONES 31 jul: edición creativa autónoma no se promete). Los cortes se
  aplican armando el timeline SOLO con los segmentos conservados (el complemento
  de los silencios) — no se destruye nada, se reordena.

  El RENDER es aparte y SÍ es automático (r.102), pero es el paso pesado que
  calienta la Mac: por eso solo corre DENTRO de una `SesionM1` (con caffeinate
  puesto) y antes del deadline. `render_nocturno` lo hace; el timeline de la
  Pieza 3 nunca renderiza.

El ejecutor SSH es INYECTABLE (B10, r.119): el módulo no abre red ni toca la M1
por su cuenta. En pruebas se inyecta un doble; en producción, el SSH real.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime, time as dtime
from typing import Callable, Optional, Protocol


# ── frontera de la ventana nocturna (r.102) ──────────────────────────────────
DEADLINE_DEFECTO = dtime(6, 0)   # a las 06:00 la config nocturna YA no debe estar
FPS_DEFECTO = 30                 # cuadros/seg del material (iPhone/QuickTime); configurable


class VentanaNocturnaError(RuntimeError):
    """Se intentó trabajar en la M1 fuera de la ventana permitida (ya es ≥06:00)."""


class ReversionError(RuntimeError):
    """Una config nocturna NO quedó revertida al verificar. Es una alarma dura
    (r.102): la Mac prestada no puede quedar tocada. Nunca se traga en silencio."""


# ── ejecutor SSH inyectable ──────────────────────────────────────────────────
@dataclass
class ResultadoComando:
    ok: bool
    salida: str
    codigo: int = 0


class EjecutorSSH(Protocol):
    """Puerto: corre un comando en la M1 y devuelve su resultado. La implementación
    real hace SSH; en pruebas se inyecta un doble. El módulo NUNCA abre SSH solo."""
    def correr(self, comando: str) -> ResultadoComando: ...


# ── config nocturna: aplicar / usar / revertir / verificar (r.102) ───────────
@dataclass
class ConfigNocturna:
    """Una configuración temporal en la M1 prestada. Cada una sabe cómo aplicarse,
    revertirse y VERIFICAR que revirtió. `verificar` corre tras revertir y su salida
    debe CONTENER `senal_revertido` para dar la reversión por buena — si no, alarma.

    El detalle fino de la reversión no vive en un flag ciego: es el CRITERIO
    (la señal que confirma que la Mac quedó limpia) escrito donde Hermes lo lea
    ("inteligencia, no jaulas")."""
    nombre: str
    aplicar_cmd: str
    revertir_cmd: str
    verificar_cmd: str
    senal_revertido: str   # subcadena que la salida de `verificar_cmd` debe contener


def caffeinate(segundos_hasta_deadline: int) -> ConfigNocturna:
    """La config nocturna canónica: evita que la Mac se duerma para poder renderizar.

    Usa `caffeinate -dimsu -t N` con N = segundos hasta el deadline: se AUTO-EXPIRA
    del lado de la Mac antes de las 06:00 aunque Hermes muera y nunca mande el kill
    (r.102, tercer candado). Revertir = matar el proceso caffeinate. Verificar =
    `pmset -g assertions` NO debe reportar que algo previene el sueño por nosotros."""
    seg = max(1, int(segundos_hasta_deadline))
    return ConfigNocturna(
        nombre="caffeinate",
        # -t se auto-expira; el nohup+& lo deja corriendo tras cerrar la sesión SSH
        aplicar_cmd=f"nohup caffeinate -dimsu -t {seg} >/dev/null 2>&1 & echo $!",
        revertir_cmd="pkill -x caffeinate || true",
        verificar_cmd="pmset -g assertions | grep -c PreventUserIdleSystemSleep || true",
        # tras revertir, el conteo de assertions nuestras debe ser 0
        senal_revertido="0",
    )


# ── PIEZA 2: el sobre de seguridad de la M1 prestada (r.102) ─────────────────
@dataclass
class SesionM1:
    """Context manager que garantiza que la M1 queda como estaba (r.102).

    Uso:
        with SesionM1(ejecutor, configs=[caffeinate(seg)], ahora=...) as s:
            editor.ejecutar(script, s)      # trabajo
        # al salir: revierte TODO y verifica revertido, pase lo que pase.

    - `__enter__` se niega si ya es ≥ deadline (no hay ventana) y aplica cada config.
    - `__exit__` revierte SIEMPRE (aunque el bloque lance) y verifica cada reversión;
      si algo no revirtió, levanta `ReversionError` — la Mac prestada no se deja tocada.
    - Todo se loggea: éxito Y fallo (regla 3)."""
    ejecutor: EjecutorSSH
    configs: list[ConfigNocturna] = field(default_factory=list)
    ahora: Optional[datetime] = None
    deadline: dtime = DEADLINE_DEFECTO
    logger: Optional[Callable[[str], None]] = None
    _aplicadas: list[ConfigNocturna] = field(default_factory=list, init=False)
    activa: bool = field(default=False, init=False)

    def _log(self, m: str) -> None:
        (self.logger or (lambda _: None))(m)

    def _momento(self) -> datetime:
        return self.ahora or datetime.now()

    def segundos_hasta_deadline(self, ahora: Optional[datetime] = None) -> int:
        """Segundos desde `ahora` hasta el próximo deadline (hoy si aún no pasó,
        mañana si ya pasó). Sirve para atar la auto-expiración de la config."""
        ahora = ahora or self._momento()
        objetivo = datetime.combine(ahora.date(), self.deadline)
        if objetivo <= ahora:
            from datetime import timedelta
            objetivo = objetivo + timedelta(days=1)
        return int((objetivo - ahora).total_seconds())

    def dentro_de_ventana(self, ahora: Optional[datetime] = None) -> bool:
        """True si aún hay ventana para trabajar: la config debe caerse antes de las
        06:00, así que no se abre sesión entre las 06:00 y (fin de la madrugada).
        Trabajar de noche (p. ej. 22:00–05:59) sí es ventana."""
        ahora = ahora or self._momento()
        # la ventana nocturna es cualquier hora ANTES del deadline en la madrugada,
        # o de noche antes de medianoche; el único momento sin ventana es la mañana
        # (deadline ≤ hora < ~mediodía), cuando Arturo puede necesitar la Mac.
        return not (self.deadline <= ahora.time() < dtime(12, 0))

    def __enter__(self) -> "SesionM1":
        ahora = self._momento()
        if not self.dentro_de_ventana(ahora):
            raise VentanaNocturnaError(
                f"Son las {ahora.time():%H:%M}: fuera de la ventana nocturna "
                f"(deadline {self.deadline:%H:%M}). No se toca la Mac prestada.")
        for cfg in self.configs:
            r = self.ejecutor.correr(cfg.aplicar_cmd)
            if not r.ok:
                self._log(f"[m1] FALLO al aplicar {cfg.nombre}: {r.salida}")
                # si algo falló al aplicar, revierte lo ya aplicado y aborta
                self._revertir_todo()
                raise RuntimeError(f"no se pudo aplicar {cfg.nombre}: {r.salida}")
            self._aplicadas.append(cfg)
            self._log(f"[m1] aplicada config nocturna '{cfg.nombre}' "
                      f"(auto-expira en {self.segundos_hasta_deadline(ahora)}s)")
        self.activa = True
        return self

    def _revertir_todo(self) -> list[str]:
        """Revierte cada config aplicada y VERIFICA. Devuelve la lista de configs
        que NO quedaron limpias (vacía = todo bien)."""
        sucias: list[str] = []
        for cfg in reversed(self._aplicadas):
            self.ejecutor.correr(cfg.revertir_cmd)
            ver = self.ejecutor.correr(cfg.verificar_cmd)
            limpio = cfg.senal_revertido in (ver.salida or "")
            if limpio:
                self._log(f"[m1] '{cfg.nombre}' REVERTIDA y verificada limpia")
            else:
                sucias.append(cfg.nombre)
                self._log(f"[m1] ALARMA: '{cfg.nombre}' NO verificó revertida "
                          f"(salida={ver.salida!r})")
        self._aplicadas.clear()
        return sucias

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.activa = False
        sucias = self._revertir_todo()
        if sucias:
            # la Mac quedó tocada: es una alarma dura, no se traga (r.102, regla 3)
            raise ReversionError(
                f"La M1 prestada NO quedó limpia: {', '.join(sucias)} sigue(n) "
                f"sin revertir. Revisar manualmente antes de que Arturo la use.")
        return False  # no suprime excepciones del bloque de trabajo


# ── PIEZA 3: edición de línea de tiempo en DaVinci (SIN render) ──────────────
def segmentos_conservados(duracion: float, cortes: list) -> list[tuple[float, float]]:
    """El complemento de los cortes: los tramos de audio/video que SE QUEDAN, en
    orden. Aplicar los cortes = armar el timeline solo con estos segmentos. `cortes`
    son objetos con `.inicio`/`.fin` (los `Corte` de la Pieza 1). Nunca destruye:
    reconstruye la cinta sin los silencios."""
    puntos = sorted(cortes, key=lambda c: c.inicio)
    segs: list[tuple[float, float]] = []
    cursor = 0.0
    for c in puntos:
        ini = max(0.0, min(c.inicio, duracion))
        fin = max(0.0, min(c.fin, duracion))
        if ini > cursor + 1e-9:
            segs.append((round(cursor, 6), round(ini, 6)))
        cursor = max(cursor, fin)
    if duracion > cursor + 1e-9:
        segs.append((round(cursor, 6), round(duracion, 6)))
    return segs


@dataclass
class ResultadoEdicion:
    ok: bool
    motivo: str
    script: str = ""
    segmentos: int = 0


class EditorDaVinci:
    """Genera y (dentro de una SesionM1) ejecuta el script Python de DaVinci Resolve
    que arma la línea de tiempo con los cortes aprobados. SIN render, SIN efectos:
    deja el proyecto abierto para revisión de Arturo (OT-8; DECISIONES 31 jul)."""

    def __init__(self, ejecutor: EjecutorSSH, fps: int = FPS_DEFECTO,
                 logger: Optional[Callable[[str], None]] = None):
        self.ejecutor = ejecutor
        self.fps = fps
        self._log = logger or (lambda m: None)

    def _seg_a_frame(self, seg: float) -> int:
        return round(seg * self.fps)

    def generar_script(self, proyecto: str, carpeta_material: str,
                       duracion: float, cortes: list, template: str = "") -> str:
        """Arma el script Python de la API de Resolve. Determinista y auditable:
        importa la carpeta, crea un timeline y le agrega SOLO los segmentos
        conservados (en frames), y guarda. NO contiene ninguna llamada de render."""
        segs = segmentos_conservados(duracion, cortes)
        entradas = ",\n        ".join(
            f'{{"startFrame": {self._seg_a_frame(a)}, "endFrame": {self._seg_a_frame(b)}}}'
            for a, b in segs
        )
        tpl_line = (f'pm.LoadProject("{template}") or ' if template else "")
        return f'''#!/usr/bin/env python3
# Generado por Hermes (AU-3) — arma el timeline con los cortes aprobados.
# SIN render, SIN efectos: deja el proyecto abierto para revisión de Arturo.
import DaVinciResolveScript as dvr

resolve = dvr.scriptapp("Resolve")
pm = resolve.GetProjectManager()
project = {tpl_line}pm.CreateProject("{proyecto}")
mp = project.GetMediaPool()

# 1) importar la carpeta indicada
clips = mp.ImportMedia(["{carpeta_material}"])

# 2) timeline nuevo + segmentos CONSERVADOS en orden (frames @ {self.fps}fps)
mp.CreateEmptyTimeline("{proyecto}_timeline")
segmentos = [
        {entradas}
]
for item in clips:
    entradas = [dict(mediaPoolItem=item, **s) for s in segmentos]
    mp.AppendToTimeline(entradas)

# 3) guardar — NUNCA renderizar aquí
pm.SaveProject()
print("timeline armado:", len(segmentos), "segmentos; proyecto abierto para revisión")
'''

    def ejecutar(self, script: str, sesion: SesionM1) -> ResultadoEdicion:
        """Corre el script en la M1 DENTRO de una SesionM1 activa. Rechaza si la
        sesión no está activa (sin caffeinate no se trabaja de noche) o si el script
        contiene una llamada de render (esta pieza es SIN render). Loggea éxito Y fallo."""
        if not sesion.activa:
            self._log("[davinci] BLOQUEADO: la SesionM1 no está activa")
            return ResultadoEdicion(ok=False, motivo="la SesionM1 no está activa "
                                    "(la config nocturna debe estar puesta)")
        if any(t in script for t in ("Render", "StartRendering", "AddRenderJob",
                                     "DeleteAllRenderJobs")):
            self._log("[davinci] BLOQUEADO: el script de timeline NO debe renderizar")
            return ResultadoEdicion(ok=False,
                                    motivo="el paso de edición es SIN render (OT-8)")
        r = sesion.ejecutor.correr(
            "cd /tmp && cat > hermes_davinci.py <<'PYEOF'\n" + script +
            "\nPYEOF\npython3 hermes_davinci.py")
        if not r.ok:
            self._log(f"[davinci] FALLO al armar timeline: {r.salida}")
            return ResultadoEdicion(ok=False, motivo=f"fallo en DaVinci: {r.salida}")
        n = script.count('"startFrame"')  # una vez por segmento conservado
        self._log(f"[davinci] timeline armado ({r.salida.strip()})")
        return ResultadoEdicion(ok=True, motivo="timeline armado; proyecto abierto "
                                "para revisión (sin render)", script=script,
                                segmentos=max(0, n))


# ── render nocturno: automático (r.102) pero solo dentro del sobre M1 ────────
def render_nocturno(sesion: SesionM1, proyecto: str, preset: str = "YouTube 1080p",
                    logger: Optional[Callable[[str], None]] = None) -> ResultadoComando:
    """El render SÍ es automático (r.102), pero es el paso que calienta la Mac: solo
    corre DENTRO de una SesionM1 activa (con caffeinate puesto) y antes del deadline.
    Fuera de eso se niega. Loggea éxito Y fallo (regla 3)."""
    log = logger or (lambda m: None)
    if not sesion.activa:
        log("[render] BLOQUEADO: sin SesionM1 activa (caffeinate) no se renderiza")
        return ResultadoComando(ok=False, salida="sin SesionM1 activa", codigo=1)
    if not sesion.dentro_de_ventana():
        log("[render] BLOQUEADO: fuera de la ventana nocturna")
        return ResultadoComando(ok=False, salida="fuera de ventana", codigo=1)
    r = sesion.ejecutor.correr(
        f'python3 - <<PYEOF\nimport DaVinciResolveScript as dvr\n'
        f'r = dvr.scriptapp("Resolve"); pm = r.GetProjectManager()\n'
        f'p = pm.LoadProject("{proyecto}")\n'
        f'p.LoadRenderPreset("{preset}"); p.AddRenderJob(); p.StartRendering()\n'
        f'print("render lanzado")\nPYEOF')
    if r.ok:
        log(f"[render] OK: {r.salida.strip()}")
    else:
        log(f"[render] FALLO: {r.salida}")
    return r


# ── CLI (demo con ejecutor de eco; NO toca la M1 real) ───────────────────────
def main(argv: Optional[list[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Edición M1/DaVinci (AU-3) — demo local")
    ap.add_argument("--proyecto", default="podcast_demo")
    ap.add_argument("--carpeta", default="/Users/arturo/Movies/podcast")
    ap.add_argument("--duracion", type=float, default=60.0)
    args = ap.parse_args(argv)

    class _Eco:
        def correr(self, cmd):  # noqa: D401
            return ResultadoComando(ok=True, salida="[eco] " + cmd.splitlines()[0])

    from corte_silencios import Corte  # cortes de ejemplo
    cortes = [Corte(1.25, 2.8), Corte(10.2, 13.5)]
    editor = EditorDaVinci(_Eco(), logger=print)
    script = editor.generar_script(args.proyecto, args.carpeta, args.duracion, cortes)
    print("── script DaVinci generado (SIN render) ──")
    print(script)
    print("── segmentos conservados ──", segmentos_conservados(args.duracion, cortes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
