# analyzer.py
# Calls the Modal-hosted MiniCPM4-8B endpoint (OpenAI-compatible /v1/chat/completions).
# Falls back to Groq if MODAL_ENDPOINT is not set, so local dev still works.

import json
import os
import re

import requests
from github_fetcher import RepoData
from dotenv import load_dotenv

load_dotenv()

# ── Which backend to use ──────────────────────────────────────────────────────
# Set MODAL_ENDPOINT in .env after running: modal deploy modal_app.py
# e.g. MODAL_ENDPOINT=https://your-workspace--roast-my-repo-serve.modal.run
#
# If MODAL_ENDPOINT is absent, falls back to Groq (for local dev without Modal).

MODAL_ENDPOINT = os.getenv("MODAL_ENDPOINT", "").rstrip("/")
MODAL_MODEL    = "minicpm4"          # served-model-name set in modal_app.py

GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL     = "llama-3.1-8b-instant"


# ── Low-level call ─────────────────────────────────────────────────────────────

def _call_model(messages: list, max_tokens: int = 2000, temperature: float = 0.7) -> str:
    """
    Send a chat completion request.
    Uses Modal (MiniCPM4-8B) when MODAL_ENDPOINT is set, otherwise Groq.
    Returns raw text content of the first choice.
    """
    if MODAL_ENDPOINT:
        return _call_modal(messages, max_tokens, temperature)
    elif GROQ_API_KEY:
        return _call_groq(messages, max_tokens, temperature)
    else:
        raise ValueError(
            "No inference backend configured.\n"
            "  • For Modal (MiniCPM4): deploy modal_app.py then set MODAL_ENDPOINT in .env\n"
            "  • For local dev (Groq): set GROQ_API_KEY in .env"
        )


def _call_modal(messages: list, max_tokens: int, temperature: float) -> str:
    """Call the Modal vLLM OpenAI-compatible endpoint."""
    payload = {
        "model":       MODAL_MODEL,
        "messages":    messages,
        "max_tokens":  max_tokens,
        "temperature": temperature,
    }
    resp = requests.post(
        f"{MODAL_ENDPOINT}/v1/chat/completions",
        json=payload,
        timeout=120,   # cold starts can take ~60s on first request
    )
    if resp.status_code != 200:
        raise ValueError(
            f"Modal endpoint returned {resp.status_code}: {resp.text[:300]}"
        )
    return resp.json()["choices"][0]["message"]["content"].strip()


def _call_groq(messages: list, max_tokens: int, temperature: float) -> str:
    """Fallback: call Groq with llama-3.1-8b-instant."""
    from groq import Groq
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set.")
    client = Groq(api_key=GROQ_API_KEY)
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip()


# ── Context builder ───────────────────────────────────────────────────────────

def build_context(data: RepoData) -> str:
    lines = [
        f"REPO: {data.owner}/{data.repo_name}",
        f"DESCRIPTION: {data.description}",
        f"PRIMARY LANGUAGE: {data.primary_language}",
        f"STARS: {data.stars}",
        f"TOTAL FILES: {data.total_files}",
        f"HAS README: {data.has_readme}",
        f"HAS .GITIGNORE: {data.has_gitignore}",
        f"HAS .ENV FILE COMMITTED (BAD if True): {data.has_env_file}",
        f"HAS .ENV.EXAMPLE (GOOD practice): {data.has_env_example}",
        f"HAS DOCKERFILE: {data.has_dockerfile}",
        "",
        f"FILE TREE ({len(data.file_tree)} total files):",
        "\n".join(data.file_tree[:60]),
        "",
        f"FILE CONTENTS ({len(data.file_contents)} files fetched):",
    ]
    for filename, content in data.file_contents.items():
        lines.append(f"\n--- {filename} ---\n{content}")
    return "\n".join(lines)


# ── JSON parser ───────────────────────────────────────────────────────────────

def _parse_json_response(raw: str) -> dict:
    # Strip <think> tags (MiniCPM4 may emit chain-of-thought)
    if "<think>" in raw:
        raw = raw.split("</think>")[-1].strip()

    # Strip markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    # Extract JSON object
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    if start == -1 or end <= start:
        raise ValueError("No JSON object found in model response.")
    raw = raw[start:end]

    # Escape literal newlines inside string values
    raw = re.sub(r'(?<!\\)\n', '\\n', raw)
    # Strip remaining control characters
    raw = re.sub(r'[\x00-\x09\x0b\x0c\x0e-\x1f]', '', raw)

    return json.loads(raw)


# ── Main analysis function ────────────────────────────────────────────────────

def analyze_repo(data: RepoData) -> dict:
    """
    Two-call analysis:
      Call 1 → structured JSON  (roast, scorecard, red_flags, hire_score, hire_verdict)
      Call 2 → raw markdown     (generated README — no JSON wrapper, avoids escape hell)
    """
    backend = f"Modal ({MODAL_MODEL})" if MODAL_ENDPOINT else f"Groq ({GROQ_MODEL})"
    print(f"[analyzer] using backend: {backend}")

    context = build_context(data)

    # ── Call 1: Analysis JSON ─────────────────────────────────────────────────
    analysis_prompt = f"""You are a brutally honest senior engineer who reviews student and junior developer GitHub repos. You are funny, direct, and specific — never generic.

Here is the repo to analyze:

{context}

Analyze this repo and return ONLY a valid JSON object with exactly this structure.
No explanation, no markdown fences, no backticks — output raw JSON only:

{{
  "roast": "A 4-6 sentence brutal but funny roast. Reference actual filenames and code you saw. Be specific, not generic.",
  "scorecard": {{
    "code_quality":    {{ "score": 7, "reason": "one sentence" }},
    "documentation":  {{ "score": 3, "reason": "one sentence" }},
    "security":       {{ "score": 5, "reason": "one sentence" }},
    "structure":      {{ "score": 6, "reason": "one sentence" }},
    "portfolio_value":{{ "score": 4, "reason": "one sentence" }}
  }},
  "red_flags": [
    "specific red flag referencing actual file or code",
    "specific red flag 2",
    "specific red flag 3"
  ],
  "hire_score": 6,
  "hire_verdict": "One punchy sentence — would a recruiter close the tab or keep reading?"
}}

Rules:
- All scores are integers 1-10
- Red flags must be specific to THIS repo — no generic advice
- Roast must reference actual filenames or code you saw
- If the repo is genuinely good, say so — don't manufacture problems
- hire_score is overall recruiter impression out of 10
- Output only the JSON object, nothing else"""

    raw_analysis = _call_model(
        [{"role": "user", "content": analysis_prompt}],
        max_tokens=1500,
        temperature=0.7,
    )

    try:
        analysis = _parse_json_response(raw_analysis)
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(
            f"Could not parse analysis JSON from {backend}: {e}\n"
            f"Raw response (first 500 chars):\n{raw_analysis[:500]}"
        )

    # ── Call 2: README (plain markdown, no JSON) ──────────────────────────────
    readme_prompt = f"""You are a technical writer. Write a complete, professional README.md for the following GitHub repository.

Repository info:
{context[:3000]}

Output only the markdown content. No preamble or explanation before the README.
Include:
- Project title with emoji
- Short description (what it does and who it's for)
- Tech stack
- Prerequisites and local setup
- How to run / usage
- Folder structure (if non-trivial)
- License"""

    generated_readme = _call_model(
        [{"role": "user", "content": readme_prompt}],
        max_tokens=1500,
        temperature=0.4,
    )

    # Strip any accidental markdown wrapper the model adds
    if "<think>" in generated_readme:
        generated_readme = generated_readme.split("</think>")[-1].strip()
    if generated_readme.startswith("```"):
        generated_readme = generated_readme.split("```")[1]
        if generated_readme.startswith("markdown"):
            generated_readme = generated_readme[8:]
        generated_readme = generated_readme.rstrip("`").strip()

    return {
        "roast":            analysis.get("roast", ""),
        "scorecard":        analysis.get("scorecard", {}),
        "red_flags":        analysis.get("red_flags", []),
        "hire_score":       analysis.get("hire_score", 5),
        "hire_verdict":     analysis.get("hire_verdict", ""),
        "generated_readme": generated_readme,
    }