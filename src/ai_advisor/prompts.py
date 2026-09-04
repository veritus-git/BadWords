"""System prompts, transcript compaction, LLM JSON parsing/validation.

Minimal module in Task 1 (parse_llm_json only — forward dependency of
client.chat_json); completed in Task 2.
"""

import json
import re


def parse_llm_json(raw):
    """Extract and parse the first JSON object from an LLM response.

    Tolerates ```json fences and surrounding prose. Raises ValueError.
    """
    if not raw or not str(raw).strip():
        raise ValueError("Empty LLM response")
    txt = str(raw).strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", txt, re.DOTALL)
    if fence:
        txt = fence.group(1)
    else:
        start, end = txt.find("{"), txt.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("No JSON object found in LLM response")
        txt = txt[start:end + 1]
    return json.loads(txt)
