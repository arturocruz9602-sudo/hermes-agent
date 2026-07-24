"""Single source of truth for the QA automation account's identity
(HAS OT-QA). Deliberately dependency-free (no telethon, no sqlite) so
anything can import it -- including agent/agent_init.py, on every agent
construction -- without pulling in unrelated weight.
"""

# Hermes QA De La Cruz -- Telegram user_id, authorized in the pairing
# store 24-jul-2026 (see `hermes pairing list` / telegram-approved.json).
QA_USER_ID = 8727618189
