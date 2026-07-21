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

import re
import unicodedata
from typing import Dict, List, Pattern

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
        # Fail safe: never raise, never imply "escalate". No signal at all
        # is the correct behavior when the detector itself is broken.
        return []


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
        return None


def register_offer(
    session_key: str, category: str, original_message: str = "",
    now: Optional[float] = None,
) -> None:
    """Record that an offer was made -- starts the throttle and the pending window.

    *original_message* is the user's message that triggered the offer --
    stored so that, if Arturo confirms "si", the caller knows WHAT to
    re-ask chat-reasoning (the reply itself is just "si", not the question).
    """
    try:
        now = now if now is not None else time.time()
        state = _get_state(session_key)
        state["last_offer_ts"] = now
        state["pending_category"] = category
        state["pending_message"] = original_message
        state["pending_ts"] = now
    except Exception:
        pass  # fail-safe: worst case, the next message can offer again


def build_offer_text(
    category: str, monthly_spend_usd: float, budget_mxn: float = 100.0,
    *, standalone: bool = False,
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
    """
    label = CATEGORY_LABELS.get(category, "algo complejo")
    body = (
        f"🤔 Esto se ve como {label}. Gasto acumulado este mes: "
        f"${monthly_spend_usd:.2f} USD (de tu tope de ${budget_mxn:.0f} MXN). "
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
            return None
        pending_message = state.get("pending_message") or ""
        state["pending_category"] = None
        state["pending_message"] = None
        if answer is False:
            blocked: Set[str] = state["blocked_categories"]  # type: ignore[assignment]
            blocked.add(pending_category)
        return {"answer": answer, "category": pending_category, "message": pending_message}
    except Exception:
        return None
