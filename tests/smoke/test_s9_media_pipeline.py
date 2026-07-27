"""S9 (HAS Fase 2, Bloque 4): pipeline de media (imagen de prueba).

Ejercita la clasificacion real de adjuntos (imagen/audio/video/archivo)
y la construccion del placeholder de texto que evita que un
mensaje-solo-media se pierda al ser encolado y reprocesado. Usa un
archivo de imagen de prueba real (bytes minimos de un PNG valido), no
un mock del tipo MIME.
"""

from __future__ import annotations

import os
import tempfile

from gateway.config import Platform
from gateway.platforms.base import MessageEvent, MessageType
from gateway.run import (
    _build_media_placeholder,
    _event_media_is_audio,
    _event_media_is_image,
    _event_media_is_video,
)
from gateway.session import SessionSource

# 1x1 PNG real, minimo valido (no un mock de bytes).
_PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "89000000017352474200aece1ce90000000467414d410000b18f0bfc61050000"
    "00097048597300000ec300000ec301c76fa8640000000e49444154789c636460"
    "60000000050001a5f645400000000049454e44ae426082"
)


def _make_event_with_media(media_url: str, mime: str) -> MessageEvent:
    source = SessionSource(
        platform=Platform.TELEGRAM, chat_id="smoke-chat", user_id="smoke-user", chat_type="dm",
    )
    return MessageEvent(
        text="", source=source, message_id="smoke-media-1",
        media_urls=[media_url], media_types=[mime],
    )


def test_real_png_image_is_classified_as_image():
    with tempfile.TemporaryDirectory() as tmp:
        img_path = os.path.join(tmp, "prueba.png")
        with open(img_path, "wb") as f:
            f.write(_PNG_1X1)
        assert os.path.getsize(img_path) > 0

        event = _make_event_with_media(img_path, "image/png")
        assert _event_media_is_image(event, 0) is True
        assert _event_media_is_audio(event, 0) is False
        assert _event_media_is_video(event, 0) is False


def test_media_only_event_gets_a_placeholder_referencing_the_file():
    with tempfile.TemporaryDirectory() as tmp:
        img_path = os.path.join(tmp, "prueba.png")
        with open(img_path, "wb") as f:
            f.write(_PNG_1X1)

        event = _make_event_with_media(img_path, "image/png")
        placeholder = _build_media_placeholder(event)
        assert img_path in placeholder
        assert "image" in placeholder.lower()


def test_audio_attachment_is_classified_as_audio():
    event = _make_event_with_media("/tmp/nota.ogg", "audio/ogg")
    assert _event_media_is_audio(event, 0) is True
    assert _event_media_is_image(event, 0) is False
