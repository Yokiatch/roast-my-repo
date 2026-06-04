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

## What it does

Paste any public GitHub repo URL and get:

- 🔥 **The Roast** — brutal, funny, specific critique referencing actual files
- 📊 **Scorecard** — rated across Code Quality, Documentation, Security, Structure, and Portfolio Value
- 🚨 **Red Flags** — specific issues found in the repo
- 📄 **Generated README** — a production-quality README you can copy and use
- 💼 **Hire Me Score** — would a recruiter close the tab or keep reading?

## Who it's for

Final year CS students and junior developers who want honest feedback on their GitHub portfolio before applying for jobs. Built because most people's repos look worse than their actual skills.

## Tech Stack

- **Gradio** — UI
- **Llama 3.1 8B via Groq** — analysis and roasting
- **GitHub REST API** — repo fetching
- **Python** — everything else

## How it works

GitHub URL
│
▼
Fetch repo metadata + file tree + key file contents (GitHub API)
│
▼
Build context → Llama 3.1 8B prompt → structured JSON response
│
▼
Scorecard + Roast + Red Flags + Generated README + Hire Score

## Local setup

```bash
git clone https://huggingface.co/spaces/build-small-hackathon/roast-my-repo
cd roast-my-repo
pip install -r requirements.txt
```

Create a `.env` file:

GROQ_API_KEY=your-groq-api-key
GITHUB_TOKEN=your-github-token

Run:
```bash
python app.py
```

## Built by

**Yokiatch** — [github.com/Yokiatch](https://github.com/Yokiatch)