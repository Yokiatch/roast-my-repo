import requests
import base64
from dataclasses import dataclass
import os
from dotenv import load_dotenv
load_dotenv()

# Files we care about — in priority order
PRIORITY_FILES = [
    "README.md", "readme.md",
    "requirements.txt", "package.json", "Pipfile", "pyproject.toml",
    "main.py", "app.py", "index.py", "server.py",
    "index.js", "index.ts", "app.js", "app.ts",
    ".gitignore", ".env.example",
    "Dockerfile", "docker-compose.yml",
    "config.py", "settings.py", "utils.py", "helpers.py",
]
# NOTE: .env intentionally excluded — we detect its presence via has_env_file
# but never fetch the contents (could contain real secrets)

# File extensions we can read as text
TEXT_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".txt",
                   ".md", ".yml", ".yaml", ".toml", ".cfg", ".ini", ".env"}

MAX_FILES = 12  # fetch up to 12 files for richer analysis

@dataclass
class RepoData:
    owner: str
    repo_name: str
    description: str
    primary_language: str
    stars: int
    file_tree: list[str]
    file_contents: dict[str, str]   # filename → content
    has_readme: bool
    has_gitignore: bool
    has_env_file: bool
    has_env_example: bool
    has_dockerfile: bool
    total_files: int

def get_headers() -> dict:
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

def parse_github_url(url: str) -> tuple[str, str]:
    url = url.strip().rstrip("/")
    # Strip .git suffix
    if url.endswith(".git"):
        url = url[:-4]
    if "github.com" not in url:
        raise ValueError("Not a valid GitHub URL.")
    parts = url.split("github.com/")[-1].split("/")
    if len(parts) < 2:
        raise ValueError("URL must be in format: github.com/owner/repo")
    return parts[0], parts[1]


def fetch_repo(url: str) -> RepoData:
    owner, repo_name = parse_github_url(url)

    meta_resp = requests.get(
        f"https://api.github.com/repos/{owner}/{repo_name}",
        headers=get_headers(), timeout=10
    )
    if meta_resp.status_code == 404:
        raise ValueError(f"Repo '{owner}/{repo_name}' not found. Is it public?")
    if meta_resp.status_code == 429 or meta_resp.status_code == 403:
        reset = meta_resp.headers.get("X-RateLimit-Reset", "")
        msg = "GitHub rate limit hit — add a GITHUB_TOKEN to .env for higher limits"
        if reset:
            import time
            wait = max(0, int(reset) - int(time.time()))
            msg += f" (resets in ~{wait}s)"
        raise ValueError(msg)
    if meta_resp.status_code != 200:
        raise ValueError(f"GitHub API error {meta_resp.status_code}: {meta_resp.text[:200]}")

    meta = meta_resp.json()

    tree_resp = requests.get(
        f"https://api.github.com/repos/{owner}/{repo_name}/git/trees/HEAD?recursive=1",
        headers=get_headers(), timeout=10
    )
    if tree_resp.status_code != 200:
        file_tree = []
    else:
        tree_data = tree_resp.json()
        all_items = tree_data.get("tree", [])
        # GitHub truncates at 100k nodes — warn in file_tree if so
        file_tree = [item["path"] for item in all_items if item["type"] == "blob"]
        if tree_data.get("truncated"):
            file_tree.insert(0, "⚠ tree truncated by GitHub (>100k nodes)")

    file_tree_lower = [f.lower() for f in file_tree]
    has_readme      = any("readme" in f for f in file_tree_lower)
    has_gitignore   = ".gitignore" in file_tree_lower
    has_env_file    = ".env" in file_tree_lower
    has_env_example = any(".env.example" in f or ".env.sample" in f for f in file_tree_lower)
    has_dockerfile  = any("dockerfile" in f for f in file_tree_lower)

    file_contents = {}
    files_to_fetch = []

    for priority in PRIORITY_FILES:
        matches = [f for f in file_tree if f.lower() == priority.lower() or f.lower().endswith("/" + priority.lower())]
        if matches:
            files_to_fetch.append(matches[0])
        if len(files_to_fetch) >= MAX_FILES:
            break

    if len(files_to_fetch) < MAX_FILES:
        for f in file_tree:
            ext = "." + f.split(".")[-1] if "." in f else ""
            if ext in TEXT_EXTENSIONS and f not in files_to_fetch:
                files_to_fetch.append(f)
            if len(files_to_fetch) >= MAX_FILES:
                break

    for filepath in files_to_fetch:
        content = fetch_file_content(owner, repo_name, filepath)
        if content:
            file_contents[filepath] = content

    return RepoData(
        owner=owner,
        repo_name=repo_name,
        description=meta.get("description") or "No description provided.",
        primary_language=meta.get("language") or "Unknown",
        stars=meta.get("stargazers_count", 0),
        file_tree=file_tree,
        file_contents=file_contents,
        has_readme=has_readme,
        has_gitignore=has_gitignore,
        has_env_file=has_env_file,
        has_env_example=has_env_example,
        has_dockerfile=has_dockerfile,
        total_files=len(file_tree),
    )


def fetch_file_content(owner: str, repo: str, filepath: str) -> str | None:
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/contents/{filepath}",
            headers=get_headers(), timeout=10
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("encoding") == "base64":
            content = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
            return content[:3000] if len(content) > 3000 else content
        return None
    except Exception:
        return None