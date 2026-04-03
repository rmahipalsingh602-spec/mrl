from __future__ import annotations


def process_ai_command(text: str) -> str:
    prompt = text.strip()
    if not prompt:
        return "[AI] No prompt provided."
    return f"[AI] Generating: {prompt}..."
