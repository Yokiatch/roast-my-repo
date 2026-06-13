# analyzer.py
# Calls the Modal-hosted MiniCPM4-8B endpoint (OpenAI-compatible /v1/chat/completions).

import json
import os
import re

import requests
import sseclient
from github_fetcher import RepoData
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

# ── Backend config ────────────────────────────────────────────────────────────
MODAL_ENDPOINT = os.getenv("MODAL_ENDPOINT", "").rstrip("/")
MODAL_MODEL    = "minicpm4"


# ── Low-level call ────────────────────────────────────────────────────────────

def _call_model(messages: list, max_tokens: int = 2000, temperature: float = 0.7) -> str:
    if not MODAL_ENDPOINT:
        raise ValueError(
            "MODAL_ENDPOINT is not set.\n"
            "Deploy modal_app.py then add MODAL_ENDPOINT to your .env or Space secrets."
        )
    return _call_modal(messages, max_tokens, temperature)


def _call_modal(messages: list, max_tokens: int, temperature: float) -> str:
    """Call the Modal vLLM endpoint with streaming to avoid timeout on large repos."""
    payload = {
        "model":       MODAL_MODEL,
        "messages":    messages,
        "max_tokens":  max_tokens,
        "temperature": temperature,
        "stream":      True,
    }
    resp = requests.post(
        f"{MODAL_ENDPOINT}/v1/chat/completions",
        json=payload,
        stream=True,
        timeout=300,
    )
    if resp.status_code != 200:
        raise ValueError(
            f"Modal endpoint returned {resp.status_code}: {resp.text[:300]}"
        )

    client = sseclient.SSEClient(resp)
    chunks = []
    for event in client.events():
        if event.data == "[DONE]":
            break
        try:
            delta = json.loads(event.data)["choices"][0]["delta"].get("content", "")
            if delta:
                chunks.append(delta)
        except (KeyError, json.JSONDecodeError):
            continue
    return "".join(chunks)


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
        "\n".join(data.file_tree[:40]),
        "",
        f"FILE CONTENTS ({len(data.file_contents)} files fetched):",
    ]
    for filename, content in data.file_contents.items():
        lines.append(f"\n--- {filename} ---\n{content}")
    return "\n".join(lines)


# ── Repo classifier ───────────────────────────────────────────────────────────

LARGE_REPO_THRESHOLDS = {
    "stars":        500,
    "contributors": 10,
    "open_issues":  50,
}

def classify_repo(data: RepoData) -> dict:
    """
    Returns is_large=True if repo looks like a library/framework/org project,
    along with the reasons that triggered it (for the UI warning banner).
    """
    reasons = []
    if data.stars >= LARGE_REPO_THRESHOLDS["stars"]:
        reasons.append(f"⭐ {data.stars:,} stars")
    if data.contributors >= LARGE_REPO_THRESHOLDS["contributors"]:
        reasons.append(f"👥 {data.contributors} contributors")
    if data.open_issues >= LARGE_REPO_THRESHOLDS["open_issues"]:
        reasons.append(f"🐛 {data.open_issues} open issues")
    return {"is_large": len(reasons) > 0, "reasons": reasons}


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
    Two-call analysis run in parallel:
      Call 1 → structured JSON  (roast, scorecard, red_flags, hire_score, hire_verdict)
      Call 2 → raw markdown     (generated README — no JSON wrapper, avoids escape hell)
    """
    print(f"[analyzer] using backend: Modal ({MODAL_MODEL})")

    context = build_context(data)

    analysis_prompt = f"""You are a brutally honest senior engineer who reviews student and junior developer GitHub repos. You are funny, direct, and specific — never generic.

GROUND TRUTH — these are verified facts from the repo, do NOT contradict them:
- .ENV FILE COMMITTED: {str(data.has_env_file).upper()} — only flag a committed .env as a security issue if this is TRUE. If FALSE, do not mention it.
- .ENV.EXAMPLE EXISTS: {str(data.has_env_example).upper()} — do not flag missing .env.example unless the repo clearly handles secrets
- README EXISTS: {str(data.has_readme).upper()}
- GITIGNORE EXISTS: {str(data.has_gitignore).upper()}

Here is the repo to analyze:

{context}

Analyze this repo and return ONLY a valid JSON object with exactly this structure.
No explanation, no markdown fences, no backticks — output raw JSON only:

{{
  "roast": "A 4-6 sentence brutal but funny roast. Reference actual filenames and code you saw. Be specific, not generic.",
  "scorecard": {{
    "code_quality":    {{ "score": <INT 1-10>, "reason": "one sentence" }},
    "documentation":  {{ "score": <INT 1-10>, "reason": "one sentence" }},
    "security":       {{ "score": <INT 1-10>, "reason": "one sentence" }},
    "structure":      {{ "score": <INT 1-10>, "reason": "one sentence" }},
    "portfolio_value":{{ "score": <INT 1-10>, "reason": "one sentence" }}
  }},
  "red_flags": [
    "specific red flag referencing actual file or code",
    "specific red flag 2",
    "specific red flag 3"
  ],
  "hire_score": <INT 1-10>,
  "hire_verdict": "One punchy sentence — would a recruiter close the tab or keep reading?"
}}

Scoring rules — be brutally accurate, never default to middle scores out of politeness:
- Score 1-2: missing basics, an embarrassment to put on a portfolio
- Score 3-4: barely functional, obvious critical gaps
- Score 5-6: mediocre, nothing impressive
- Score 7-8: genuinely solid work
- Score 9-10: exceptional, rare

Automatic score overrides — apply these regardless of anything else:
- Committed .env file → security score is 1, no exceptions
- Fewer than 5 meaningful files → structure score 1-2, portfolio_value score 1-2
- No README → documentation score 1
- hire_score 1-2 means recruiter closes the tab immediately
- hire_score 3-4 means recruiter skims and moves on
- hire_score 5+ means recruiter actually considers reaching out

Ground truth security facts — trust these, do NOT contradict them:
- HAS .ENV FILE COMMITTED is {str(data.has_env_file).upper()} — only flag a committed .env if this is TRUE
- HAS .ENV.EXAMPLE is {str(data.has_env_example).upper()} — do NOT flag missing .env.example unless this repo clearly needs one (i.e. it uses secrets or environment variables)
- NEVER mention .env or .env.example as a red flag if HAS .ENV FILE COMMITTED is FALSE and the repo has no obvious need for secrets
- NEVER invent security issues that aren't visible in the actual file contents or metadata above

Other rules:
- Red flags must be specific to THIS repo — reference actual filenames and code
- Roast must reference actual filenames or code you saw
- If the repo is genuinely good, reflect that honestly — don't manufacture problems
- Output only the JSON object, nothing else"""

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

    # ── Run both calls in parallel ────────────────────────────────────────────
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_analysis = ex.submit(
            _call_model, [{"role": "user", "content": analysis_prompt}], 1500, 0.7
        )
        f_readme = ex.submit(
            _call_model, [{"role": "user", "content": readme_prompt}], 1500, 0.4
        )
        raw_analysis     = f_analysis.result()
        generated_readme = f_readme.result()

    # ── Parse JSON response ───────────────────────────────────────────────────
    try:
        analysis = _parse_json_response(raw_analysis)
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(
            f"Could not parse analysis JSON from Modal ({MODAL_MODEL}): {e}\n"
            f"Raw response (first 500 chars):\n{raw_analysis[:500]}"
        )

    # ── Clean README output ───────────────────────────────────────────────────
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