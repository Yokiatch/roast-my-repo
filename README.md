---
title: Roast My Repo
emoji: 🔥
colorFrom: red
colorTo: yellow
sdk: gradio
sdk_version: 5.29.0
app_file: app.py
pinned: false
license: mit
short_description: AI-powered brutal code review for your GitHub repos
---

# 🔥 Roast My Repo

> Paste a GitHub URL. Brace yourself.

AI-powered code review that tells you what your friends won't. Built for the [HuggingFace Build Small Hackathon](https://huggingface.co/build-small-hackathon) — Chapter One: Backyard AI.

Powered by **[MiniCPM4-8B](https://huggingface.co/openbmb/MiniCPM4-8B)** (OpenBMB) served via **[Modal](https://modal.com)**.

---

## What it does

Paste any public GitHub repo URL and get:

- 🔥 **The Roast** — brutal, funny, specific critique referencing actual filenames and code
- 📊 **Scorecard** — rated across Code Quality, Documentation, Security, Structure, and Portfolio Value
- 🚨 **Red Flags** — specific issues found in this repo, not generic advice
- 📄 **Generated README** — a production-quality README you can copy and use immediately
- 💼 **Hire Me Score** — would a recruiter close the tab or keep reading?

---

## Who it's for

Final-year CS students and junior developers who want honest feedback on their GitHub portfolio before applying for jobs. Built because most people's repos look worse than their actual skills — and nobody tells them.

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI | Gradio 5 (custom terminal CSS) |
| Inference | [MiniCPM4-8B](https://huggingface.co/openbmb/MiniCPM4-8B) via vLLM on Modal |
| Serving | Modal A10G GPU · OpenAI-compatible `/v1/chat/completions` |
| Repo fetching | GitHub REST API (tree + contents) |
| Local dev fallback | Groq (llama-3.1-8b-instant) |

---

## Why MiniCPM4-8B?

MiniCPM4-8B from OpenBMB packs serious reasoning quality into 8B parameters — trained on 8 trillion tokens. It fits comfortably on a single A10G (24GB VRAM) in fp16, keeps Modal costs low, and handles code review prompts with chain-of-thought quality that rivals much larger models. For a hackathon constraint of "small model, real output", it's the right call.

---

## How it works

```
GitHub URL
    │
    ▼
Fetch repo metadata + file tree + up to 12 key files (GitHub API)
    │
    ▼
Build context string → two sequential MiniCPM4-8B calls
    │
    ├── Call 1: Structured JSON  (roast · scorecard · red_flags · hire_score)
    └── Call 2: Plain markdown   (generated README — avoids JSON escape hell)
    │
    ▼
Render terminal UI (Gradio + custom CSS)
```

---

## Local Setup

### Prerequisites

- Python 3.11+
- A [Modal](https://modal.com) account (free tier works)
- A [GitHub token](https://github.com/settings/tokens) (for higher rate limits)
- Optional: [Groq API key](https://console.groq.com) for local dev without Modal

### Install

```bash
git clone https://huggingface.co/spaces/Yokiatch/roast-my-repo
cd roast-my-repo
pip install -r requirements.txt
```

### Configure

Create a `.env` file:

```env
MODAL_ENDPOINT=https://your-workspace--roast-my-repo-serve.modal.run
GITHUB_TOKEN=your-github-token

# Local dev only (no Modal needed):
# GROQ_API_KEY=your-groq-key
```

### Deploy the Modal inference server

```bash
modal deploy modal_app.py
```

Copy the printed URL into `MODAL_ENDPOINT` in your `.env`.

### Run locally

```bash
python app.py
```

---

## HuggingFace Space Setup

Add these under **Settings → Variables and secrets**:

| Secret | Value |
|---|---|
| `MODAL_ENDPOINT` | Your deployed Modal URL |
| `GITHUB_TOKEN` | GitHub personal access token |

The Space runs `app.py` directly — no other config needed.

---

## Project Structure

```
roast-my-repo/
├── app.py              # Gradio UI + roast_repo handler
├── analyzer.py         # Two-call MiniCPM4 analysis logic
├── github_fetcher.py   # GitHub API: tree fetch + file contents
├── modal_app.py        # vLLM server on Modal (MiniCPM4-8B)
├── requirements.txt
└── .env.example        # Template — never commit real secrets
```

---

## Security Notes

- `.env` files are **detected** (flagged as a red flag) but **never fetched** — contents are not read
- Private repos return a clean "not found" error
- `GITHUB_TOKEN` is read from Space secrets, never hardcoded

---

## Credits

- **[OpenBMB](https://github.com/OpenBMB)** — [MiniCPM4-8B](https://huggingface.co/openbmb/MiniCPM4-8B) model
- **[Modal](https://modal.com)** — GPU inference infrastructure

---

## License

MIT — built by [Yokiatch](https://github.com/Yokiatch) for the HuggingFace Build Small Hackathon 2026.