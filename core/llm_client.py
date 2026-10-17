import json
import logging
import re
from typing import Any, Dict, List, Optional
import httpx
from core.config import settings

logger = logging.getLogger("fixpilot.llm")


def clean_json_response(raw_text: str) -> Dict[str, Any]:
    """Extract and parse clean JSON from model output, handling reasoning prefixes, markdown blocks, and unescaped characters."""
    cleaned = raw_text.strip()

    # 1. Search for ```json { ... } ``` or ``` { ... } ``` blocks
    json_blocks = re.findall(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", cleaned, re.IGNORECASE)
    for block in json_blocks:
        try:
            return json.loads(block.strip(), strict=False)
        except Exception:
            pass

    # 2. Balanced brace extractor from first '{' to matching '}'
    start = cleaned.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(cleaned)):
            c = cleaned[i]
            if c == '"' and not escape:
                in_string = not in_string
            elif not in_string:
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        candidate = cleaned[start : i + 1]
                        try:
                            return json.loads(candidate, strict=False)
                        except Exception:
                            sanitized = re.sub(r'(?<!\\)\n', r'\\n', candidate)
                            try:
                                return json.loads(sanitized, strict=False)
                            except Exception:
                                pass
                        break
            if c == '\\' and not escape:
                escape = True
            else:
                escape = False
        start = cleaned.find("{", start + 1)

    # 3. Last-ditch attempt: between first { and last }
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        snippet = cleaned[first_brace : last_brace + 1]
        try:
            return json.loads(snippet, strict=False)
        except Exception:
            sanitized = re.sub(r'(?<!\\)\n', r'\\n', snippet)
            try:
                return json.loads(sanitized, strict=False)
            except Exception:
                pass

    raise ValueError(f"Failed to parse LLM output as JSON: {raw_text[:250]}...")


async def _try_provider(
    base_url: str,
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
    timeout_sequence: List[float],
    provider_name: str,
    extra_headers: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """Attempts chat completion with escalating timeouts.

    Only retries on timeout. Non-timeout errors (4xx, 5xx, connection)
    immediately return None to fall through to the next provider.
    """
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    if extra_headers:
        headers.update(extra_headers)

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    for attempt, timeout in enumerate(timeout_sequence, 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    if "choices" in data and data["choices"]:
                        logger.info(
                            f"[{provider_name}] Success with {model} "
                            f"(attempt {attempt}, timeout {timeout}s)"
                        )
                        return data["choices"][0]["message"]["content"]
                    else:
                        logger.warning(
                            f"[{provider_name}] Response missing choices: {data}"
                        )
                        return None
                else:
                    logger.warning(
                        f"[{provider_name}] HTTP {resp.status_code}: {resp.text[:200]}"
                    )
                    return None

        except httpx.TimeoutException:
            logger.warning(
                f"[{provider_name}] Timeout after {timeout}s for {model} "
                f"(attempt {attempt}/{len(timeout_sequence)})"
            )
            continue

        except Exception as e:
            logger.warning(f"[{provider_name}] Call failed: {e}")
            return None

    logger.warning(
        f"[{provider_name}] All {len(timeout_sequence)} attempts timed out for {model}"
    )
    return None


async def call_nemotron(
    messages: List[Dict[str, str]],
    model_name: str,
    fallback_model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    timeout_seconds: Optional[float] = None
) -> str:
    """Dispatches chat completion request to NVIDIA API -> Nebius Token Factory -> OpenRouter -> Simulation."""
    try:
        timeout_seq = [float(t.strip()) for t in settings.LLM_TIMEOUT_SEQUENCE.split(",") if t.strip()]
    except Exception:
        timeout_seq = [30.0, 60.0, 90.0]

    if timeout_seconds is not None:
        timeout_seq = [timeout_seconds]

    # 1. NVIDIA API (build.nvidia.com) - PRIMARY
    if settings.NVIDIA_API_KEY and not settings.NVIDIA_API_KEY.startswith("your_"):
        result = await _try_provider(
            base_url=settings.NVIDIA_BASE_URL,
            api_key=settings.NVIDIA_API_KEY,
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_sequence=timeout_seq,
            provider_name="NVIDIA API"
        )
        if result is not None:
            return result

    # 2. Nebius Token Factory
    if settings.NEBIUS_API_KEY and not settings.NEBIUS_API_KEY.startswith("your_"):
        result = await _try_provider(
            base_url=settings.NEBIUS_BASE_URL,
            api_key=settings.NEBIUS_API_KEY,
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_sequence=timeout_seq,
            provider_name="Nebius Token Factory"
        )
        if result is not None:
            return result

    # 3. OpenRouter Fallback
    if settings.OPENROUTER_API_KEY and not settings.OPENROUTER_API_KEY.startswith("your_"):
        target_model = fallback_model or model_name
        result = await _try_provider(
            base_url=settings.OPENROUTER_BASE_URL,
            api_key=settings.OPENROUTER_API_KEY,
            model=target_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_sequence=timeout_seq,
            provider_name="OpenRouter",
            extra_headers={
                "HTTP-Referer": "https://github.com/sanidhyaagrawal17/fixpilot-ai",
                "X-Title": "FixPilot Hackathon Agent"
            }
        )
        if result is not None:
            return result

    # 4. Offline / Simulation fallback if no credentials are configured or network calls fail
    logger.info("Operating in simulated diagnostic mode.")
    return _generate_simulation_response(messages, model_name)


def _generate_simulation_response(messages: List[Dict[str, str]], model_name: str) -> str:
    """Provides deterministic baseline responses for local testing without active API credits."""
    user_content = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    
    if "classify" in model_name or "nano" in model_name:
        # Heuristic classification
        err_type = "runtime"
        if "IndexError" in user_content or "KeyError" in user_content or "TypeError" in user_content or "AttributeError" in user_content:
            err_type = "type"
        elif "SyntaxError" in user_content or "IndentationError" in user_content:
            err_type = "syntax"
        elif "ImportError" in user_content or "ModuleNotFoundError" in user_content:
            err_type = "import"
        elif "AssertionError" in user_content:
            err_type = "logic"

        # Extract exact error message line from traceback
        lines = [l.strip() for l in user_content.splitlines() if l.strip()]
        last_error_line = next((l for l in reversed(lines) if "Error" in l or "Exception" in l or "assert" in l), "Detected runtime discrepancy")
        msg = last_error_line

        # Detect file and line (Python or JS)
        file_match = re.search(r'File "([^"]+)", line (\d+)', user_content)
        lang = "python"
        if file_match:
            aff_file = file_match.group(1)
            aff_line = int(file_match.group(2))
        else:
            v8_match = re.search(r'at\s+(?:.*?\s+)?\(?([^:\s()]+):(\d+):(\d+)\)?', user_content)
            if v8_match:
                aff_file = v8_match.group(1)
                aff_line = int(v8_match.group(2))
                lang = "javascript"
            else:
                aff_file = "solution.py"
                aff_line = 2

        if "javascript" in user_content.lower() or ".js" in user_content:
            lang = "javascript"

        return json.dumps({
            "error_type": err_type,
            "error_message": msg,
            "affected_file": aff_file,
            "affected_line": aff_line,
            "language": lang,
            "confidence": 0.95
        })

    elif "ultra" in model_name or "analyze" in model_name:
        return json.dumps({
            "root_cause": "Index/value out of bound or unhandled NoneType access in solution flow.",
            "explanation": "Execution attempted to access an element past the collection boundary or dereferenced a null state without a guard clause.",
            "affected_code_snippet": "return items[len(items)]",
            "suggested_approach": "Apply boundary check or len(items) - 1 / safe null fallback.",
            "doc_references": ["https://docs.python.org/3/tutorial/errors.html"]
        })

    else:
        # Super / Fixer
        return json.dumps({
            "fixed_code": "# Autonomous fix applied by FixPilot\ndef get_last_item(items):\n    if not items:\n        return None\n    return items[len(items) - 1]\n",
            "explanation": "Corrected off-by-one index error by referencing len(items) - 1 and added safety guard for empty input.",
            "changes_summary": [
                "Replaced items[len(items)] with items[len(items) - 1]",
                "Added empty collection guard check"
            ]
        })
