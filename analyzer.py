import json
import os
from groq import Groq
from github_fetcher import RepoData
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.1-8b-instant"


def build_context(data: RepoData) -> str:
    """Build a compact context string from repo data."""
    lines = [
        f"REPO: {data.owner}/{data.repo_name}",
        f"DESCRIPTION: {data.description}",
        f"PRIMARY LANGUAGE: {data.primary_language}",
        f"STARS: {data.stars}",
        f"TOTAL FILES: {data.total_files}",
        f"HAS README: {data.has_readme}",
        f"HAS .GITIGNORE: {data.has_gitignore}",
        f"HAS .ENV FILE COMMITTED (this is BAD if True): {data.has_env_file}",
        f"HAS .ENV.EXAMPLE (this is GOOD practice): {data.has_env_example}",
        f"HAS DOCKERFILE: {data.has_dockerfile}",
        "",
        "FILE TREE (first 60 files):",
        "\n".join(data.file_tree[:30]),
        "",
        "FILE CONTENTS:",
    ]

    for filename, content in data.file_contents.items():
        lines.append(f"\n--- {filename} ---\n{content}")

    return "\n".join(lines)


def analyze_repo(data: RepoData) -> dict:
    """
    Run the full analysis. Returns a dict with:
    - roast, scorecard, red_flags, generated_readme, hire_score, hire_verdict
    """
    context = build_context(data)

    prompt = f"""You are a brutally honest senior engineer who reviews student and junior developer GitHub repos. You are funny, direct, and specific — never generic.

Here is the repo to analyze:

{context}

Analyze this repo and return ONLY a valid JSON object with exactly this structure. No explanation, no markdown, no backticks:

{{
  "roast": "A 4-6 sentence brutal but funny roast of this specific repo. Reference actual files and problems you found. Be specific, not generic. Make it sting a little but stay professional.",
  "scorecard": {{
    "code_quality": {{ "score": 7, "reason": "one sentence explanation" }},
    "documentation": {{ "score": 3, "reason": "one sentence explanation" }},
    "security": {{ "score": 5, "reason": "one sentence explanation" }},
    "structure": {{ "score": 6, "reason": "one sentence explanation" }},
    "portfolio_value": {{ "score": 4, "reason": "one sentence explanation" }}
  }},
  "red_flags": [
    "specific red flag 1",
    "specific red flag 2",
    "specific red flag 3"
  ],
  "generated_readme": "A complete, professional README.md for this repo in markdown format. Include: project title, description, tech stack, setup instructions, usage, and folder structure.",
  "hire_score": 6,
  "hire_verdict": "One punchy sentence — would a recruiter close the tab or keep reading?"
}}

Rules:
- Scores are integers 1-10
- Red flags must be specific to THIS repo, not generic advice
- The roast must reference actual filenames or content you saw
- If the repo is actually good, say so — don't manufacture problems
- hire_score is the overall recruiter impression score out of 10"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=4000,
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    # Strip <think> tags
    if "<think>" in raw:
        raw = raw.split("</think>")[-1].strip()

    # Fix invalid control characters (newlines inside JSON strings)
    import re
    # Extract just the JSON object
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start != -1 and end > start:
        raw = raw[start:end]

    # Replace literal newlines inside JSON string values with \n
    raw = re.sub(r'(?<!\\)\n', '\\n', raw)
    # Remove other control characters
    raw = re.sub(r'[\x00-\x09\x0b\x0c\x0e-\x1f]', '', raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Last resort — ask model to simplify the readme
        raw = re.sub(r'("generated_readme"\s*:\s*)".*?"', r'\1"See repository for details."', raw, flags=re.DOTALL)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse response: {e}")