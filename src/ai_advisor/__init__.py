"""AI Advisor addon for BadWords.

LLM-powered edit suggestions and social-clip finder, OpenAI-compatible
providers (LM Studio, Ollama, cloud). See docs/superpowers/specs/
2026-09-04-ai-advisor-addon-design.md.
"""

__version__ = "0.1.0"


def open_panel(main_window):
    """Open the AI Advisor panel. Called from gui.py, exception-guarded there."""
    from .panel import AIPanel
    return AIPanel(main_window)
