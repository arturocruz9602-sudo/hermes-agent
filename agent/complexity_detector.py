"""Complexity signal detector for Tarea E (candidate categories for
suggesting escalation to chat-reasoning/deepseek-v4-pro).

SAFETY INVARIANT (non-negotiable, per Arturo 19 Jul 2026):
This module NEVER decides to escalate to a more expensive/deeper model on
its own. detect_categories() only classifies text into candidate
categories -- it is a SIGNAL, not an instruction. Any caller integrating
this MUST always ask Arturo for explicit confirmation before switching to
chat-reasoning/deepseek-v4-pro. Never escalate silently, ever, even if a
match looks certain.

Fail-safe on error: if anything inside detect_categories() raises, it is
caught and an empty list is returned (behaves as "no signal detected").
The safe default on internal failure is doing nothing extra -- not asking
more, not escalating, not raising. Never fail open into an escalate signal.

v1 scope: 3_trading is intentionally NOT included here. Zero evidence of
real usage as of 19 Jul 2026 (see reporte_validacion_historial.md /
reporte_sesion_19jul_4bloques.md). Add it back only once Arturo actually
resumes trading -- do not add it preemptively.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Dict, List, Pattern

_log = logging.getLogger(__name__)

CATEGORIES: Dict[str, List[str]] = {
    "1_razonamiento": [
        "analiza a fondo", "razona paso a paso", "piensa bien", "piénsalo bien",
        "compara a profundidad", "evalúa todas las opciones", "pros y contras",
        "qué me conviene", "ayúdame a decidir", "modo profundo", "usa reasoning",
        "qué opción es mejor", "a manera de ensayo", "no me des tablas solo texto",
        "proyección de", "análisis desde el día", "honestidad y precisión",
        "si no tienes forma de verificar", "basándote en tus registros reales",
    ],
    "2_programacion": [
        "refactoriza", "arquitectura", "diseña el sistema", "depura", "debuggea",
        "por qué falla", "por qué no funciona", "no jala", "no sirve", "se traba",
        "optimiza el rendimiento", "race condition", "concurrencia",
        "migra la base de datos", "revisa la seguridad", "vulnerabilidad",
        "eficientizar", "cambiar el código", "reiniciar el gateway",
        "variable de entorno", "optimización de consulta", "optimizar la consulta",
        "consulta de base de datos",
    ],
    "4_diagnostico": [
        "diagnóstico", "síntomas", "causa raíz", "root cause", "no arranca",
        "se cayó", "quedó pegado", "análisis de logs", "por qué se rompió",
        "diagnostica", "se saturó", "te estás saturando",
        "resolvimos varios problemas", "bug de sintaxis", "crasheando",
        "volviste a fallar",
    ],
}


def _strip_accents(text: str) -> str:
    """Fold away accents/diacritics (á->a, é->e, ñ->n, ...).

    Same idiom already used elsewhere in this codebase for the same reason
    (agent/turn_finalizer.py::_strip_accents_for_match, added so
    _FABRICATED_SUCCESS_RE doesn't need to enumerate every accented
    conjugation) -- reused here instead of inventing a second one. Applied
    to BOTH the compiled keyword patterns and the input text at match time,
    so folding stays internally consistent regardless of which accented
    form (or none) either side happens to use.
    """
    return "".join(
        c for c in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(c)
    )


def _compile_patterns() -> Dict[str, List[Pattern]]:
    compiled: Dict[str, List[Pattern]] = {}
    for cat, keywords in CATEGORIES.items():
        compiled[cat] = [
            re.compile(r"\b" + re.escape(_strip_accents(kw)) + r"\b", re.IGNORECASE)
            for kw in keywords
        ]
    return compiled


_COMPILED_PATTERNS = _compile_patterns()


def detect_categories(text: str) -> List[str]:
    """Return the list of candidate complexity categories matched in *text*.

    Word-boundary matching (\\bkeyword\\b), case- and accent-insensitive
    (both sides folded through _strip_accents -- "por que se rompio" now
    matches "por qué se rompió" and vice versa). Conjugation/stemming is
    deliberately NOT normalized (e.g. "depura" still won't match
    "depurar"/"depuración") -- out of scope for this pass, see module notes.

    Returns an empty list on empty/None input or on any internal error --
    see the fail-safe invariant in the module docstring. This is a SIGNAL
    for a caller to ask Arturo, never an instruction to escalate on its own.
    """
    if not text:
        return []
    try:
        folded = _strip_accents(text)
        hits: List[str] = []
        for category, patterns in _COMPILED_PATTERNS.items():
            for pattern in patterns:
                if pattern.search(folded):
                    hits.append(category)
                    break
        return hits
    except Exception:
        _log.warning(
            "detect_categories fallo -- Tarea E no vera NINGUNA categoria en este mensaje",
            exc_info=True,
        )
        # Fail safe: never raise, never imply "escalate". No signal at all
        # is the correct behavior when the detector itself is broken.
        return []


# =============================================================================
# Bloque O (22 Jul 2026): deroga los criterios (a)/(b)/(c) de Bloque L y el
# gate de Bloque M como código Python heurístico -- ver assess_data_need()
# y self_assess_response() más abajo (autoevaluación real via Gemini).
# fetch_context_summary() sigue viva, reutilizada por O.1.
# =============================================================================

def fetch_context_summary(query: str, *, max_results: int = 3) -> Optional[str]:
    """Bloque L.2: consulta gratuita (Brave Search, via tools.web_tools --
    ya configurado como backend "brave-free" cuando BRAVE_SEARCH_API_KEY
    existe) para traer datos actuales ANTES de ofrecer DeepSeek a Arturo.
    Devuelve un resumen corto (titulos + descripciones, recortado) o None
    si la busqueda no esta disponible o no trajo nada -- nunca lanza, un
    fallo aqui degrada a "sin resumen", no bloquea la oferta.
    """
    if not query:
        return None
    try:
        import json as _json

        from tools.web_tools import web_search_tool

        raw = web_search_tool(query, limit=max_results)
        parsed = _json.loads(raw)
        if not parsed.get("success"):
            return None
        results = ((parsed.get("data") or {}).get("web")) or []
        if not results:
            return None
        parts = []
        for r in results[:max_results]:
            title = (r.get("title") or "").strip()
            desc = (r.get("description") or "").strip()
            # Bloque O.3: los snippets de Brave a veces traen markup HTML
            # crudo (ej. "<strong>...</strong>") -- se limpia porque el
            # formato de oferta exige "resumen sin snippets crudos".
            desc = re.sub(r"<[^>]+>", "", desc)
            title = re.sub(r"<[^>]+>", "", title)
            if title:
                parts.append(f"{title}: {desc}" if desc else title)
        if not parts:
            return None
        summary = " | ".join(parts)
        return summary[:400]
    except Exception:
        _log.warning(
            "fetch_context_summary fallo -- la oferta ira sin resumen de contexto",
            exc_info=True,
        )
        return None


# =============================================================================
# Integration layer: throttle, per-category block, offer text, reply parsing
# =============================================================================
#
# Corrección de premisa (19 Jul 2026, antes de escribir esto): se pidió
# reutilizar "el parser de sí/no de Tarea D" -- verificado en el código real
# (gateway/run.py, _DEEPSEEK_AUTH_RE) que Tarea D NO tiene un parser de sí/no
# genérico. Su mecanismo exige un verbo + el nombre "deepseek" cerca
# (ej. "usa deepseek", "ocupa deepseek") -- funciona para autorizar un
# proveedor por nombre, no para responder sí/no a una oferta. Tampoco existe
# en ningún otro lugar del framework un parser de sí/no en lenguaje natural
# genérico (sí existe tools/slash_confirm.py, pero es para botones de
# Telegram con 3 opciones fijas "Approve Once/Always Approve/Cancel" que no
# encajan semánticamente con esta pregunta, y adaptar sus etiquetas requiere
# tocar el adaptador de la plataforma, fuera de alcance de hoy). Por eso
# parse_yes_no() de abajo SÍ es código nuevo -- se avisó antes de escribirlo,
# como se pidió para puntos genuinamente ambiguos.
#
# Para reducir el riesgo de un parser nuevo: NO hace substring matching
# (evita interpretar un "no" perdido dentro de un mensaje largo no
# relacionado como rechazo de la oferta) -- exige que el mensaje COMPLETO,
# ya normalizado, sea una de un set corto y conocido de respuestas sí/no.
# Cualquier mensaje ambiguo devuelve None (fail-safe: no se asume nada).

import time
from typing import Optional, Set

CATEGORY_LABELS: Dict[str, str] = {
    "1_razonamiento": "una decisión o análisis complejo",
    "2_programacion": "un problema técnico no trivial",
    "4_diagnostico": "un diagnóstico técnico",
    # Bloque L (22 Jul 2026) -- categorías del clasificador nuevo, ver
    # classify_complexity() abajo.
    "3_multivariable": "una decisión con varias variables dependientes entre sí",
    "1_incertidumbre": "algo donde mi primera respuesta no fue suficiente",
}

OFFER_THROTTLE_SECONDS = 30 * 60  # decisión 1: máximo una oferta cada 30 min
PENDING_OFFER_TIMEOUT_SECONDS = 20 * 60  # ventana de validez de una oferta

_AFFIRMATIVE = {
    "si", "sí", "simon", "simón", "va", "dale", "adelante", "hazlo",
    "porfa hazlo", "obvio", "claro", "sale", "de una",
}
_NEGATIVE = {
    "no", "nel", "nop", "no gracias", "mejor no", "paso", "no por ahora",
    "asi esta bien", "así está bien", "no hace falta", "no es necesario",
}

# Estado en memoria, por sesión -- mismo patrón que tools/approval.py
# (_session_approved: dict[str, set]). Se pierde al reiniciar el proceso,
# igual que el estado de aprobaciones de approval.py -- aceptable, es un
# throttle de conveniencia, no un control de seguridad que deba sobrevivir
# un reinicio.
_session_state: Dict[str, Dict[str, object]] = {}


def _get_state(session_key: str) -> Dict[str, object]:
    return _session_state.setdefault(session_key, {
        "last_offer_ts": 0.0,
        "blocked_categories": set(),
        "pending_category": None,
        "pending_message": None,
        "pending_ts": 0.0,
        "pending_context_data": "",
    })


def should_offer(
    session_key: str, categories: List[str], now: Optional[float] = None,
) -> Optional[str]:
    """Return the first category worth offering, or None.

    Applies decision 1 (throttle: max one offer per 30 min, global per
    session -- not per category) and decision 2 (a "no" blocks that SAME
    category for the rest of the session; a different, non-blocked
    category can still offer, still subject to the same 30-min throttle).
    Fail-safe: any internal error returns None (no offer), never raises.
    """
    if not categories:
        return None
    try:
        now = now if now is not None else time.time()
        state = _get_state(session_key)
        if now - float(state["last_offer_ts"]) < OFFER_THROTTLE_SECONDS:
            return None
        blocked: Set[str] = state["blocked_categories"]  # type: ignore[assignment]
        for category in categories:
            if category not in blocked:
                return category
        return None
    except Exception:
        _log.warning("should_offer fallo -- no se ofrecera nada en este turno", exc_info=True)
        return None


def register_offer(
    session_key: str, category: str, original_message: str = "",
    now: Optional[float] = None, context_data: str = "",
) -> None:
    """Record that an offer was made -- starts the throttle and the pending window.

    *original_message* is the user's message that triggered the offer --
    stored so that, if Arturo confirms "si", the caller knows WHAT to
    re-ask chat-reasoning (the reply itself is just "si", not the question).

    *context_data* (Bloque L, 22 Jul 2026): the free-lookup summary (Brave
    Search / etc) already fetched BEFORE the offer was sent, so the real
    despacho after "si" can reuse it instead of searching again, and so it
    builds a MINIMAL request (current message + this data) instead of
    replaying the full session history.
    """
    try:
        now = now if now is not None else time.time()
        state = _get_state(session_key)
        state["last_offer_ts"] = now
        state["pending_category"] = category
        state["pending_message"] = original_message
        state["pending_ts"] = now
        state["pending_context_data"] = context_data
    except Exception:
        pass  # fail-safe: worst case, the next message can offer again


def build_offer_text(
    category: str, monthly_spend_usd: float, budget_mxn: float = 100.0,
    *, standalone: bool = False, context_summary: Optional[str] = None,
) -> str:
    """Build the plain-text offer.

    Decision 3: category shown in simple language (CATEGORY_LABELS), not
    the raw internal category key.

    *standalone*: True when this is sent as its OWN message (via
    agent.background_review_callback, delivered after the main response
    finishes streaming -- see 19 Jul 2026 fix, root cause: appending to
    final_response inside finalize_turn arrives too late for a platform
    that streams the main response live, since the stream consumer has
    already delivered everything before finalize_turn's post-processing
    runs). False (default) keeps the old leading separator, for the
    fallback path where no callback exists (e.g. CLI) and the text is
    still appended directly to final_response.

    *context_summary* (Bloque L, 22 Jul 2026): short summary of what a free
    lookup (Brave Search / etc) already found about the topic, shown to
    Arturo BEFORE he decides -- so the offer says "ya tengo X, ¿le entro
    con DeepSeek?" instead of asking blind.
    """
    label = CATEGORY_LABELS.get(category, "algo complejo")
    context_line = f"\nYa tengo esto: {context_summary}\n" if context_summary else ""
    body = (
        f"🤔 Esto se ve como {label}. Gasto acumulado este mes: "
        f"${monthly_spend_usd:.2f} USD (de tu tope de ${budget_mxn:.0f} MXN). "
        f"{context_line}"
        f"¿Uso razonamiento profundo (deepseek-v4-pro) para esto? Responde "
        f"sí/no -- si no contesto en un rato sigo normal, sin costo extra."
    )
    return body if standalone else f"\n\n---\n{body}"


def parse_yes_no(text: str) -> Optional[bool]:
    """Interpret *text* as an affirmative/negative reply, or None if unclear.

    Whole-message match only (after accent-fold + lowercase + strip trailing
    punctuation) against a short known set -- deliberately NOT substring
    matching, so a long unrelated message that happens to contain "no"
    somewhere is never misread as declining an offer. See the module note
    above on why this is new code instead of a reused parser.
    """
    if not text:
        return None
    try:
        normalized = _strip_accents(text).strip().lower().rstrip(".!¡¿? ")
        if normalized in _AFFIRMATIVE:
            return True
        if normalized in _NEGATIVE:
            return False
        return None
    except Exception:
        _log.warning(
            "parse_yes_no fallo -- la respuesta de Arturo queda como ambigua",
            exc_info=True,
        )
        return None


def check_pending_reply(
    session_key: str, text: str, now: Optional[float] = None,
) -> Optional[Dict[str, object]]:
    """Resolve *text* against a pending offer for this session, if any.

    Returns a dict ``{"answer": bool, "category": str, "message": str}``
    when the reply resolves the pending offer -- "message" is the ORIGINAL
    user text that triggered the offer (needed by the caller to actually
    re-ask chat-reasoning; the reply itself is just "si"/"no", not the
    question). Returns None when there is no pending offer, it expired, or
    the reply doesn't parse as yes/no -- in all three cases the caller
    should treat this as a normal message, not an answer to the offer.
    ``answer is False`` records the category as blocked per decision 2.
    Fail-safe: any internal error returns None.
    """
    try:
        now = now if now is not None else time.time()
        state = _get_state(session_key)
        pending_category = state.get("pending_category")
        if not pending_category:
            return None
        expired = now - float(state["pending_ts"]) > PENDING_OFFER_TIMEOUT_SECONDS
        answer = None if expired else parse_yes_no(text)
        if answer is None:
            # Hardening (19 Jul 2026, post-incident): the offer is only valid
            # for the message immediately following it -- ANY other message
            # in between (a new question, a duplicate delivery, a stray
            # "si"/"no" about something unrelated sent later) clears the
            # pending state instead of leaving it dangling for up to 20 min.
            # Previously a stale offer stayed "armable" by any later message
            # that happened to parse as yes/no, with no requirement that it
            # actually be a reply to THIS offer -- real financial exposure
            # (a genuine, unauthorized ~$0.06 USD DeepSeek charge) came from
            # this class of ambiguity, even though the exact trigger for
            # that specific incident was never fully reproduced. Narrowing
            # the window to "next message only" removes the whole category
            # of stale-pending-offer collision regardless of the precise
            # mechanism. Real reply-to-message-id correlation (mirroring
            # Tarea D) would be even tighter, but requires plumbing the sent
            # offer's platform message id back through
            # agent.background_review_callback, which is fire-and-forget by
            # design today -- out of scope for this pass.
            state["pending_category"] = None
            state["pending_message"] = None
            state["pending_context_data"] = ""
            return None
        pending_message = state.get("pending_message") or ""
        pending_context_data = state.get("pending_context_data") or ""
        state["pending_category"] = None
        state["pending_message"] = None
        state["pending_context_data"] = ""
        if answer is False:
            blocked: Set[str] = state["blocked_categories"]  # type: ignore[assignment]
            blocked.add(pending_category)
        return {
            "answer": answer, "category": pending_category, "message": pending_message,
            "context_data": pending_context_data,
        }
    except Exception:
        _log.warning(
            "check_pending_reply fallo -- se pierde la respuesta a la oferta pendiente",
            exc_info=True,
        )
        return None


# =============================================================================
# Bloque O (22 Jul 2026) -- Tarea E v2. Deroga los criterios a/b/c de Bloque L
# y el gate de Bloque M como codigo Python heuristico -- reemplazados por
# autoevaluacion real via una llamada barata a Gemini. Ver
# assess_data_need() (compuerta 1, PRE-respuesta) y
# self_assess_response() (compuerta 2, POST-respuesta) mas abajo.
# =============================================================================

def _resolve_litellm_credentials() -> "tuple[str, str]":
    """Mismo mecanismo real usado en el resto del proyecto (fase2_extract_
    candidates.py, gateway/run.py) -- expansion manual de ${VAR}, porque
    hermes_cli.model_switch no expande esos placeholders.

    Lee las credenciales de LiteLLM de las DOS formas validas en que
    config.yaml las puede guardar, en este orden:
      1. entrada 'LiteLLM' de custom_providers (forma historica), y
      2. la seccion `model:` con base_url/api_key en linea.
    El fallback (2) nace de un incidente real del 30 jul 2026: se
    restauro `config.yaml.known-good` (4 jul), que guarda las mismas
    credenciales en `model:` y NO tiene entrada en custom_providers.
    Con solo la forma (1), esta funcion lanzaba, _call_cheap_model_json
    se lo tragaba en silencio y TODA la autoevaluacion de Tarea E caia
    al default fail-safe sin una sola linea de log -- verificado en vivo
    con 8/8 casos devolviendo el default identico."""
    import os as _os
    from hermes_cli.config import load_config
    from hermes_cli.env_loader import load_hermes_dotenv

    load_hermes_dotenv()
    cfg = load_config()

    def expand(value: str) -> str:
        return re.sub(
            r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}",
            lambda m: _os.environ.get(m.group(1), ""),
            str(value),
        )

    custom_provs = (cfg.get("custom_providers") if isinstance(cfg, dict) else None) or []
    entry = next(
        (p for p in custom_provs if isinstance(p, dict) and p.get("name") == "LiteLLM"),
        None,
    )
    candidatos = []
    if entry is not None:
        candidatos.append(("custom_providers['LiteLLM']", entry))
    model_cfg = (cfg.get("model") if isinstance(cfg, dict) else None) or {}
    if isinstance(model_cfg, dict):
        candidatos.append(("model:", model_cfg))

    for origen, fuente in candidatos:
        base_url = expand(fuente.get("base_url", ""))
        api_key = expand(fuente.get("api_key", ""))
        if base_url and api_key:
            return base_url, api_key
        _log.warning(
            "credenciales de LiteLLM incompletas en %s (base_url=%s, api_key=%s)",
            origen, bool(base_url), bool(api_key),
        )

    raise RuntimeError(
        "credenciales de LiteLLM no encontradas en config.yaml: ni en "
        "custom_providers['LiteLLM'] ni en la seccion model: "
        "(revisar config.yaml y ${LITELLM_MASTER_KEY} en .env)"
    )


def _call_cheap_model_json(prompt: str, *, max_tokens: int = 300) -> Optional[dict]:
    """Llama chat-primary (Gemini, barato) pidiendo JSON, parsea la
    respuesta. None en cualquier fallo -- nunca lanza."""
    try:
        import json as _json
        import urllib.request as _ur

        base_url, api_key = _resolve_litellm_credentials()
        payload = {
            "model": "chat-primary",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0,
        }
        req = _ur.Request(
            base_url.rstrip("/") + "/chat/completions",
            data=_json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with _ur.urlopen(req, timeout=25) as resp:
            body = _json.loads(resp.read().decode("utf-8"))
        raw = (body.get("choices") or [{}])[0].get("message", {}).get("content", "")
        raw = raw.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        parsed = _json.loads(raw)
        if not isinstance(parsed, dict):
            _log.warning(
                "modelo barato devolvio JSON que no es objeto (%s) -- se usa el default",
                type(parsed).__name__,
            )
            return None
        return parsed
    except Exception:
        # HAS §F9-L6/L14: el silencio nunca es un estado valido de fallo.
        # Antes esto devolvia None sin log alguno, y quien llama cae a su
        # default fail-safe -- indistinguible de "el modelo dijo que todo
        # bien". Asi murio Tarea E entera el 30 jul 2026 sin dejar rastro.
        _log.warning("fallo la llamada al modelo barato -- se usa el default", exc_info=True)
        return None


_DATA_NEED_RUBRIC = """Responde SOLO con JSON valido, sin texto extra, con esta forma exacta:
{{"necesita_datos": true|false, "fuentes": ["brave"|"coingecko", ...]}}

necesita_datos=true SOLO si el mensaje pide informacion que cambia con el tiempo
y que tu (Gemini) no puedes saber con certeza sin buscar: precios de mercado o
criptomonedas actuales, noticias recientes, datos externos que cambian.
necesita_datos=false para todo lo demas: aritmetica, explicaciones de codigo,
conceptos generales, conversacion normal, preguntas sobre el propio sistema.

fuentes (solo si necesita_datos=true): "coingecko" para precios de
criptomonedas/mercado, "brave" para cualquier otra busqueda web (noticias,
hechos actuales).

Mensaje del usuario: {user_message}"""


def assess_data_need(user_message: str) -> dict:
    """Bloque O.1 -- compuerta 1 (PRE-respuesta). Llamada barata a Gemini
    con rubrica fija. Devuelve {"necesita_datos": bool, "fuentes": [...]}.
    Fail-safe: cualquier error -> necesita_datos=False (nunca bloquea la
    respuesta normal por un fallo aqui)."""
    default = {"necesita_datos": False, "fuentes": []}
    if not user_message:
        return default
    parsed = _call_cheap_model_json(
        _DATA_NEED_RUBRIC.format(user_message=user_message), max_tokens=150,
    )
    if not parsed:
        return default
    necesita = bool(parsed.get("necesita_datos"))
    fuentes = parsed.get("fuentes") or []
    if not isinstance(fuentes, list):
        fuentes = []
    fuentes = [f for f in fuentes if f in ("brave", "coingecko")]
    return {"necesita_datos": necesita, "fuentes": fuentes}


_COINGECKO_IDS = {
    "btc": "bitcoin", "bitcoin": "bitcoin",
    "eth": "ethereum", "ethereum": "ethereum",
    "sol": "solana", "solana": "solana",
    "bnb": "binancecoin",
    "xrp": "ripple", "ripple": "ripple",
    "doge": "dogecoin", "dogecoin": "dogecoin",
    "ada": "cardano", "cardano": "cardano",
}
_COIN_MENTION_RE = re.compile(
    r"\b(btc|bitcoin|eth|ethereum|sol|solana|bnb|xrp|ripple|doge|dogecoin|ada|cardano)\b",
    re.IGNORECASE,
)


def fetch_coingecko_prices(user_message: str) -> Optional[dict]:
    """Bloque O.1 -- precio real y actual desde CoinGecko (API publica, sin
    key) para cualquier moneda mencionada en el mensaje. Devuelve
    {"bitcoin": 65000.0, ...} en USD, o None si no se detecto ninguna
    moneda conocida o la consulta fallo. Nunca lanza."""
    try:
        import json as _json
        import urllib.request as _ur

        mentions = {m.lower() for m in _COIN_MENTION_RE.findall(user_message)}
        ids = sorted({_COINGECKO_IDS[m] for m in mentions if m in _COINGECKO_IDS})
        if not ids:
            return None
        url = (
            "https://api.coingecko.com/api/v3/simple/price?ids="
            + ",".join(ids) + "&vs_currencies=usd"
        )
        req = _ur.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; HermesAgent/1.0)"})
        with _ur.urlopen(req, timeout=15) as resp:
            body = _json.loads(resp.read().decode("utf-8"))
        prices = {coin_id: data.get("usd") for coin_id, data in body.items() if isinstance(data, dict)}
        return prices or None
    except Exception:
        _log.warning(
            "fetch_coingecko_prices fallo -- se respondera sin precios reales",
            exc_info=True,
        )
        return None


_PRICE_MENTION_RE = re.compile(r"\$\s?([\d,]+(?:\.\d+)?)")


def gather_pre_response_context(user_message: str) -> Optional[str]:
    """Bloque O.1 completo: clasifica, busca si hace falta, reconcilia
    conflictos entre fuentes, y arma el bloque de contexto a inyectar
    ANTES de que el modelo principal responda (via el hook pre_llm_call).
    Devuelve None si no hace falta nada o todo fallo -- fail-safe, nunca
    bloquea la respuesta normal.
    """
    try:
        # Bloque O.6: chequeo determinista PRIMERO (no depende del
        # clasificador de O.1) -- si el usuario está pidiendo verificar un
        # incidente/fallo pasado, corre el script real y fuerza esa
        # evidencia al contexto antes de que el modelo pueda especular.
        if looks_like_incident_check(user_message):
            return run_incident_verification()

        assessment = assess_data_need(user_message)
        if not assessment.get("necesita_datos"):
            return None
        fuentes = assessment.get("fuentes") or ["brave"]

        coingecko_prices = None
        if "coingecko" in fuentes:
            coingecko_prices = fetch_coingecko_prices(user_message)

        brave_summary = None
        if "brave" in fuentes or not coingecko_prices:
            # Bloque O -- bug real encontrado en producción: mandar el
            # mensaje completo del usuario (multi-línea, largo) como query
            # de Brave devolvía 422 Unprocessable Entity. Brave espera
            # queries cortas tipo buscador, no un párrafo -- se colapsa a
            # una sola línea y se trunca.
            _brave_query = re.sub(r"\s+", " ", user_message).strip()[:150]
            brave_summary = fetch_context_summary(_brave_query)

        parts = []
        if coingecko_prices:
            price_lines = ", ".join(f"{coin}: ${price:,.2f} USD" for coin, price in coingecko_prices.items())
            parts.append(f"Precio real y actual (CoinGecko, ahora mismo): {price_lines}")

        if brave_summary:
            # Regla de conflicto de datos (O.1): si el resumen de busqueda
            # trae una cifra en dolares que difiere >5% del precio real de
            # CoinGecko, señalarlo explicitamente en vez de dejar que el
            # modelo elija una cifra vieja sin avisar -- caso real que
            # motivo esto: ETH $1,917 vs $1,736 presentados sin avisar del
            # conflicto en el mismo mensaje.
            if coingecko_prices:
                mentioned = [float(m.replace(",", "")) for m in _PRICE_MENTION_RE.findall(brave_summary)]
                for coin, real_price in coingecko_prices.items():
                    for mentioned_price in mentioned:
                        if real_price and abs(mentioned_price - real_price) / real_price > 0.05:
                            parts.append(
                                f"AVISO: los resultados de búsqueda mencionan una cifra "
                                f"(${mentioned_price:,.2f}) que difiere más de 5% del precio "
                                f"real actual de {coin} (${real_price:,.2f}, CoinGecko en vivo) "
                                f"-- probablemente una noticia vieja con un precio desactualizado. "
                                f"Usa el precio real de CoinGecko, y si mencionas la cifra de la "
                                f"búsqueda dile a Arturo explícitamente que es una cifra vieja/"
                                f"distinta, nunca las presentes como si coincidieran."
                            )
                            break
            parts.append(f"Resultados de búsqueda web (Brave, ahora mismo): {brave_summary}")

        if not parts:
            return None
        return (
            "[Datos actuales obtenidos ANTES de responder -- intégralos en tu "
            "respuesta en español, no los ignores ni respondas sin ellos]\n"
            + "\n".join(parts)
        )
    except Exception:
        _log.warning(
            "gather_pre_response_context fallo -- se respondera SIN los datos frescos ya obtenidos",
            exc_info=True,
        )
        return None


_SELF_ASSESS_RUBRIC = """Acabas de responder un mensaje de un usuario. Evalúa tu PROPIA
respuesta con honestidad. Responde SOLO con JSON valido, sin texto extra, con esta
forma exacta:
{{"resolvi_con_confianza": true|false, "multivariable": true|false, "que_me_falto": "..."|null}}

resolvi_con_confianza=true SOLO si diste una respuesta completa, decisiva, sin
lenguaje de duda ("podría ser", "prueba con", "no estoy seguro") y sin presentar
múltiples causas/opciones sin decidirte por una.

EXCEPCIÓN 2 (saludos / sin pregunta real): resolvi_con_confianza=true
automático y que_me_falto=null cuando el mensaje del usuario es un
saludo, una palabra suelta, o no contiene ninguna pregunta o solicitud
real (ej. "Hermes", "hola", "buenas noches", "gracias") -- no hay nada
que resolver en un saludo, contestarlo de vuelta ES la respuesta
completa y correcta.

EXCEPCIÓN IMPORTANTE (no es lo mismo "no decidí" que "correctamente le
devolví la decisión al usuario"): resolvi_con_confianza=true TAMBIÉN
cuando ya investigaste/explicaste todo lo que había que explicar y la
respuesta termina pidiéndole al usuario que elija entre opciones ya
presentadas, PORQUE la decisión depende de su preferencia personal o
afecta algo que solo él debe decidir (ej. reiniciar su propia sesión o
no, elegir entre A o B cuando ambas son válidas y correctas, autorizar
un gasto o una acción). Ahí no te faltó nada real -- preguntarle a él es
la respuesta correcta, no una respuesta incompleta.

Esto incluye el caso en que el mensaje es tan vago que NO se puede
resolver sin más información del usuario (ej. "ayuda", "tengo un
problema", "no sirve"): si le pediste que concrete, resolvi_con_confianza=true
-- lo que falta ahí es información que SOLO él tiene, no capacidad tuya,
y un modelo más caro tampoco lo adivinaría. Distinto es cuando lo que
falta lo podías averiguar TÚ (ej. "logs?" -> dónde están los logs se
revisa en el sistema): eso sí es resolvi_con_confianza=false.

Reserva
resolvi_con_confianza=false para cuando TÚ deberías haber podido decidir
o afirmar algo con la información que ya tenías, y no lo hiciste
(lenguaje de duda, causas sin diagnosticar, technical open questions que
te correspondía resolver a ti).

multivariable=true si la pregunta involucraba múltiples factores/variables
dependientes entre sí que interactúan de forma no trivial (ej. varias posiciones
financieras, interacción entre varios componentes de un sistema).

que_me_falto: si tu respuesta se quedó corta en algo real (no aplica si
resolvi_con_confianza=true Y multivariable=false, NI cuando terminaste
correctamente con una pregunta de la EXCEPCIÓN de arriba), describe en
una frase corta QUÉ te faltó resolver. null si no te faltó nada.

Pregunta del usuario: {user_message}

Tu respuesta: {gemini_response}"""


def self_assess_response(user_message: str, gemini_response: str) -> dict:
    """Bloque O.2 -- compuerta 2 (POST-respuesta). Reemplaza los criterios
    a/b/c de Bloque L y el gate de Bloque M (código Python heurístico) con
    autoevaluación real: la misma llamada barata a Gemini que se usa en
    O.1, ahora pidiéndole que evalúe su PROPIA respuesta.
    Devuelve {"resolvi_con_confianza": bool, "multivariable": bool,
    "que_me_falto": str|None}. Fail-safe: cualquier error ->
    resolvi_con_confianza=True (no ofrecer, nunca por defecto)."""
    default = {"resolvi_con_confianza": True, "multivariable": False, "que_me_falto": None}
    if not user_message or not gemini_response:
        return default
    parsed = _call_cheap_model_json(
        _SELF_ASSESS_RUBRIC.format(
            user_message=user_message[:2000], gemini_response=gemini_response[:3000],
        ),
        max_tokens=300,
    )
    if not parsed:
        return default
    resolvi = parsed.get("resolvi_con_confianza")
    multivar = parsed.get("multivariable")
    falto = parsed.get("que_me_falto")
    return {
        "resolvi_con_confianza": True if resolvi is None else bool(resolvi),
        "multivariable": bool(multivar),
        "que_me_falto": falto if isinstance(falto, str) and falto.strip() else None,
    }


def should_offer_v2(assessment: dict) -> bool:
    """Bloque O.2: regla de decisión sobre el resultado de
    self_assess_response(). Ofrece SOLO si resolvi_con_confianza=false, O
    (multivariable=true Y que_me_falto no es null)."""
    if not assessment.get("resolvi_con_confianza", True):
        return True
    if assessment.get("multivariable") and assessment.get("que_me_falto"):
        return True
    return False


_OFFER_DAILY_CAP = 3


def offers_today_count(session_key: str) -> int:
    """Bloque O.2, anti-spam: cuenta ofertas ya hechas HOY (fecha local)
    para esta sesión, vía state.db (tabla mensajes_pendientes reutilizada
    como bitácora simple -- ver register_offer_v2). Fail-safe: error -> 0
    (no bloquea la primera oferta del día por un fallo de conteo)."""
    try:
        import sqlite3
        import time as _time

        today = _time.strftime("%Y-%m-%d")
        con = sqlite3.connect("/home/arturo/.hermes/state.db")
        try:
            cur = con.execute(
                "SELECT COUNT(*) FROM tarea_e_ofertas WHERE session_key = ? AND fecha = ?",
                (session_key, today),
            )
            row = cur.fetchone()
            return int(row[0]) if row else 0
        finally:
            con.close()
    except Exception:
        _log.warning(
            "offers_today_count fallo -- el tope diario anti-spam queda SIN efecto",
            exc_info=True,
        )
        return 0


def register_offer_v2(session_key: str) -> None:
    """Bloque O.2: registra una oferta hecha HOY para el conteo anti-spam.
    Crea la tabla si no existe. Fail-safe: nunca lanza."""
    try:
        import sqlite3
        import time as _time

        today = _time.strftime("%Y-%m-%d")
        con = sqlite3.connect("/home/arturo/.hermes/state.db")
        try:
            con.execute(
                "CREATE TABLE IF NOT EXISTS tarea_e_ofertas ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, session_key TEXT NOT NULL, "
                "fecha TEXT NOT NULL, ts REAL NOT NULL)"
            )
            con.execute(
                "INSERT INTO tarea_e_ofertas (session_key, fecha, ts) VALUES (?, ?, ?)",
                (session_key, today, _time.time()),
            )
            con.commit()
        finally:
            con.close()
    except Exception:
        pass


# Tasa de referencia USD->MXN (Bloque O.3, 22 Jul 2026). No hay API de tipo
# de cambio ya integrada en el proyecto -- valor fijo conservador, revisar
# si Arturo confirma un valor real distinto. Solo afecta el texto informativo
# de la oferta, nunca un cálculo de facturación real (el costo real siempre
# sale del ledger real de litellm en USD).
_MXN_PER_USD = 18.5


def build_offer_text_v2(
    *, motivo: str, resumen: Optional[str], que_me_falto: Optional[str],
    monthly_spend_usd: float, est_cost_usd: float = 0.01,
) -> str:
    """Bloque O.3: formato de oferta FIJO, máximo 4 líneas, en español,
    gasto mostrado en MXN (convertido). Reemplaza el build_offer_text
    variable de Bloque L."""
    spend_mxn = monthly_spend_usd * _MXN_PER_USD
    cost_mxn = est_cost_usd * _MXN_PER_USD
    lines = [f"🤔 Esto se ve {motivo}."]
    if resumen:
        lines.append(f"Ya tengo: {resumen[:200]}")
    lines.append(f"Mi respuesta se quedó corta en: {que_me_falto or 'no fue lo bastante completa'}.")
    lines.append(
        f"¿Le entro con DeepSeek? (~${cost_mxn:.2f} MXN, gasto acumulado del mes: "
        f"${spend_mxn:.2f} MXN) sí/no — si no contestas, sigo normal sin costo."
    )
    return "\n".join(lines)


# =============================================================================
# Bloque O.4 (22 Jul 2026): enforcement de español en toda respuesta.
# =============================================================================

_SPANISH_STOPWORDS = {
    "de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las", "por",
    "un", "para", "con", "no", "una", "su", "al", "es", "lo", "como", "mas",
    "pero", "sus", "le", "ya", "o", "este", "si", "porque", "esta", "entre",
    "cuando", "muy", "sin", "sobre", "tambien", "me", "hasta", "donde", "quien",
}
_ENGLISH_STOPWORDS = {
    "the", "of", "and", "to", "in", "is", "you", "that", "it", "was", "for",
    "on", "are", "as", "with", "his", "they", "at", "be", "this", "have",
    "from", "or", "had", "by", "but", "not", "what", "all", "were", "we",
    "when", "your", "can", "there", "use", "each", "which", "she", "how",
    "their", "will", "up", "other", "about", "out", "many", "then", "them",
    "these", "would", "like", "into", "has", "more", "these",
}


def response_looks_like_english(text: str) -> bool:
    """Bloque O.4: heurístico barato (sin llamada a modelo) para detectar
    si una respuesta salió en inglés en vez de español -- conteo de
    stopwords conocidas. Requiere un mínimo de palabras para no disparar
    con textos cortos (ej. "OK", nombres de variables) y un margen claro
    (más hits en inglés que en español, y al menos 5 hits en inglés) para
    evitar falsos positivos con código/nombres técnicos mezclados."""
    if not text:
        return False
    words = re.findall(r"[a-zA-ZáéíóúñÁÉÍÓÚÑ]+", text.lower())
    es_hits = sum(1 for w in words if w in _SPANISH_STOPWORDS)
    en_hits = sum(1 for w in words if w in _ENGLISH_STOPWORDS)

    # Textos CORTOS (30 jul 2026): el piso de 20 palabras + 5 stopwords
    # dejaba pasar sin filtro TODA respuesta breve en ingles -- que son
    # justo las que Arturo ve a diario ("Hello! How can I help you
    # today?" = 7 palabras). Reportado por el en vivo: saludo en español,
    # respuesta en ingles, y el enforcement de Bloque O.4 ni se entero
    # (no habia una sola linea en el journal porque nunca se llamo).
    # Verificado: 6 de 6 respuestas cortas en ingles pasaban, incluida
    # una de 19 palabras.
    # La regla corta pide MARGEN AMPLIO (el doble) en vez de cero
    # stopwords españolas, porque varias son identicas en ambos idiomas
    # ("me", "no", "a", "son"): exigir es_hits==0 dejaba pasar
    # "...let me know what you need" por un solo "me". Con el margen, un
    # texto en español con terminos tecnicos en ingles ("ya quedo el
    # deploy") nunca dispara, y >=2 inglesas evita morder un error citado
    # de una sola palabra.
    if len(words) < 20:
        return len(words) >= 4 and en_hits >= 2 and en_hits > 2 * es_hits

    return en_hits >= 5 and en_hits > es_hits


def regenerate_in_spanish(text: str) -> Optional[str]:
    """Bloque O.4: si la respuesta salió en inglés, se manda UNA vez más
    a Gemini pidiendo la misma respuesta en español, preservando
    contenido/formato. None si falla -- el caller decide el fallback."""
    if not text:
        return None
    prompt = (
        "Traduce/reescribe el siguiente texto completo al español, "
        "conservando exactamente el mismo contenido, formato, bloques de "
        "código (sin traducir el código en sí, solo comentarios/prosa), y "
        "estructura. Responde SOLO con el texto reescrito, sin comentarios "
        "adicionales:\n\n" + text
    )
    try:
        import json as _json
        import urllib.request as _ur

        base_url, api_key = _resolve_litellm_credentials()
        payload = {
            "model": "chat-primary",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4000,
            "temperature": 0,
        }
        req = _ur.Request(
            base_url.rstrip("/") + "/chat/completions",
            data=_json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with _ur.urlopen(req, timeout=30) as resp:
            body = _json.loads(resp.read().decode("utf-8"))
        text_out = (body.get("choices") or [{}])[0].get("message", {}).get("content", "")
        return text_out.strip() or None
    except Exception:
        _log.warning(
            "regenerate_in_spanish fallo -- la respuesta puede quedar en ingles",
            exc_info=True,
        )
        return None


# =============================================================================
# Bloque O.5 (22 Jul 2026): único atajo válido para saltarse la oferta.
# =============================================================================

_URGENT_SHORTCUT_RE = re.compile(
    r"^\s*(?:urgente\s+con\s+deepseek\s*:\s*|/deepseek\s+)(.+)$",
    re.IGNORECASE | re.DOTALL,
)


def parse_urgent_shortcut(text: str) -> Optional[str]:
    """Bloque O.5: único atajo válido para despachar DeepSeek sin pasar
    por la oferta -- comando EXPLÍCITO del usuario, con la autorización
    incluida en el mismo mensaje ("urgente con deepseek: ..." o
    "/deepseek ..."). Devuelve el texto de la tarea si matchea, None si
    no. El sistema NUNCA inicia DeepSeek sin que el usuario lo haya
    pedido explícitamente de una forma u otra (oferta+sí, o este atajo) --
    esto NO es un camino silencioso, es la autorización puntual explícita
    que pide Bloque O.5."""
    if not text:
        return None
    m = _URGENT_SHORTCUT_RE.match(text.strip())
    if not m:
        return None
    task = m.group(1).strip()
    return task or None


# =============================================================================
# Bloque O.6 (22 Jul 2026): disparo AUTOMATICO de verificar_incidente.py.
# Encontrado en pruebas reales: solo tener la skill en disco NO basta --
# el modelo no siempre la invoca por su cuenta (caso real reproducido en
# esta misma sesion: Hermes inventó un timestamp "18:33:24" que no
# correspondía a nada real en vez de correr el script). Igual que O.1,
# esto se fuerza inyectando el resultado REAL antes de que el modelo
# responda, para que nunca tenga la oportunidad de especular sin la
# evidencia real ya puesta enfrente.
# =============================================================================

_INCIDENT_CHECK_RE = re.compile(
    r"\b(verifica|revisa|checa)\b[^.!?\n]{0,40}\b(fallo|error|incidente)\b"
    r"|\bque\s+(fallo|paso|pas[oó])\b"
    r"|\bpor\s+qu[ée]\s+fall[oó]\b"
    r"|\bverifica(?:r)?\s+(?:el\s+)?incidente\b",
    re.IGNORECASE,
)


def looks_like_incident_check(user_message: str) -> bool:
    """Bloque O.6: heurístico determinista (sin llamada a modelo, para
    ser rápido y confiable) que detecta si el usuario está pidiendo
    investigar un fallo/incidente pasado."""
    if not user_message:
        return False
    folded = _strip_accents(user_message).lower()
    return bool(_INCIDENT_CHECK_RE.search(folded))


def run_incident_verification(window_minutes: int = 45) -> str:
    """Bloque O.6: corre verificar_incidente.py con "ahora" como
    timestamp aproximado y arma el bloque de contexto con instrucciones
    estrictas: solo citar lo real, decir "sin evidencia" si no hay nada,
    nunca inventar.

    Hallazgo real (27 Jul 2026, diagnóstico en vivo): con el default
    original (±10 min), un incidente real de hace 16 minutos quedó
    FUERA de la ventana -- el script correctamente no encontró nada
    relevante, pero el resto de la ventana (ruido rutinario de litellm)
    sí calificó como "hay_evidencia_real: true", exactamente el patrón
    de "fragmentos reales pero irrelevantes presentados como si fueran
    la evidencia pedida" descrito en reporte_bloque_o_22jul.md. Subido
    a 45 min: la ventana ES simétrica (verificar_incidente.py no acepta
    un rango asimétrico), pero un piso más alto de reach hacia atrás
    cubre demoras realistas ("hace un momento", "hace rato") sin tocar
    el contrato del script (usado también a mano por Arturo)."""
    try:
        import subprocess
        import time as _time

        now_str = _time.strftime("%Y-%m-%d %H:%M:%S")
        result = subprocess.run(
            [
                "/home/arturo/.hermes/hermes-agent/venv/bin/python3",
                "/home/arturo/.hermes/scripts/verificar_incidente.py",
                now_str, "--ventana-min", str(window_minutes),
            ],
            capture_output=True, text=True, timeout=30,
        )
        output = result.stdout.strip() or result.stderr.strip() or "(sin salida del script)"
        return (
            "[Verificación de incidente -- evidencia REAL obtenida con "
            "verificar_incidente.py, ventana ±{}min desde ahora. REGLA "
            "ESTRICTA: cita SOLO lo que aparece aquí abajo, con las líneas "
            "reales. Si 'hay_evidencia_real' es false, dilo explícitamente "
            "-- PROHIBIDO inventar timestamps, causas, o líneas de log que "
            "no estén en este bloque. PROHIBIDO ADEMÁS: llamar read_file/"
            "terminal/search_files sobre OTROS logs para responder esto -- "
            "la evidencia de arriba ya es la verificación completa y "
            "actualizada (hallazgo real 27 Jul: sin esta regla, el modelo "
            "leyó un log rotado de hace un mes y lo presentó como el "
            "estado actual). Si el bloque de abajo no alcanza, dilo así, "
            "no busques por tu cuenta en otros archivos.]\n{}"
        ).format(window_minutes, output)
    except Exception as e:
        return (
            "[Verificación de incidente: el script determinista falló al "
            f"correr ({e}). Dile a Arturo que no se pudo verificar "
            "automáticamente -- NUNCA inventes una causa sin esta evidencia.]"
        )
