import gradio as gr
from github_fetcher import fetch_repo
from analyzer import analyze_repo


def roast_repo(github_url: str):
    if not github_url.strip():
        return (
            "Please enter a GitHub URL.",
            "", "", "", "", ""
        )

    try:
        # Step 1: Fetch
        yield (
            "⏳ Fetching repo...", "", "", "", "", ""
        )
        data = fetch_repo(github_url.strip())

        # Step 2: Analyze
        yield (
            "🔥 Roasting...", "", "", "", "", ""
        )
        result = analyze_repo(data)

        # Step 3: Build scorecard markdown
        sc = result["scorecard"]
        def bar(score):
            filled = "█" * score
            empty  = "░" * (10 - score)
            return f"{filled}{empty} {score}/10"

        scorecard_md = f"""## 📊 Scorecard

| Dimension | Score | |
|---|---|---|
| 🧠 Code Quality | {sc['code_quality']['score']}/10 | {sc['code_quality']['reason']} |
| 📄 Documentation | {sc['documentation']['score']}/10 | {sc['documentation']['reason']} |
| 🔒 Security | {sc['security']['score']}/10 | {sc['security']['reason']} |
| 🏗️ Structure | {sc['structure']['score']}/10 | {sc['structure']['reason']} |
| 💼 Portfolio Value | {sc['portfolio_value']['score']}/10 | {sc['portfolio_value']['reason']} |

---

## 💼 Hire Me Score

# {result['hire_score']}/10

> {result['hire_verdict']}
"""

        # Step 4: Build red flags markdown
        flags = result["red_flags"]
        flags_md = "\n".join([f"- 🚨 {f}" for f in flags]) if flags else "✅ No major red flags found."

        # Step 5: Repo summary
        summary_md = f"""**{data.owner}/{data.repo_name}**
⭐ {data.stars} stars · 🗣️ {data.primary_language} · 📁 {data.total_files} files

_{data.description}_"""

        yield (
            result["roast"],
            scorecard_md,
            flags_md,
            result["generated_readme"],
            summary_md,
            "✅ Done!",
        )

    except ValueError as e:
        yield (str(e), "", "", "", "", "❌ Error")
    except Exception as e:
        yield (f"Something went wrong: {str(e)}", "", "", "", "", "❌ Error")


# ── UI ────────────────────────────────────────────────────────────────────────
with gr.Blocks(
    theme=gr.themes.Base(
        primary_hue="orange",
        secondary_hue="red",
        neutral_hue="slate",
        font=gr.themes.GoogleFont("Inter"),
    ),
    title="🔥 Roast My Repo",
    css="""
    .contain { max-width: 900px; margin: 0 auto; }
    .roast-box textarea { font-size: 16px !important; line-height: 1.7 !important; }
    .score-box { font-size: 15px !important; }
    footer { display: none !important; }
    .gr-button-primary { background: linear-gradient(135deg, #f97316, #ef4444) !important; border: none !important; }
    """
) as demo:

    gr.Markdown("""
# 🔥 Roast My Repo
### Paste a GitHub URL. Brace yourself.

*AI-powered code review that tells you what your friends won't.*
""")

    with gr.Row():
        url_input = gr.Textbox(
            placeholder="https://github.com/username/repo",
            label="GitHub Repository URL",
            scale=4,
        )
        roast_btn = gr.Button("🔥 Roast It!", variant="primary", scale=1)

    status = gr.Textbox(label="Status", interactive=False, max_lines=1)
    summary = gr.Markdown()

    gr.Markdown("---")

    with gr.Row():
        with gr.Column(scale=1):
            scorecard_out = gr.Markdown(label="Scorecard", elem_classes=["score-box"])
        with gr.Column(scale=1):
            roast_out = gr.Textbox(
                label="🔥 The Roast",
                lines=10,
                interactive=False,
                elem_classes=["roast-box"],
            )

    gr.Markdown("---")

    red_flags_out = gr.Markdown(label="🚨 Red Flags")

    gr.Markdown("---")

    with gr.Accordion("📄 Generated README (copy & use)", open=False):
        readme_out = gr.Code(language="markdown", label="Generated README.md")

    gr.Markdown("""
---
*Built for the HuggingFace Build Small Hackathon · Chapter One: Backyard AI*
*Uses Llama 3.1 8B via Groq · No auth required · Public repos only*
""")

    roast_btn.click(
        fn=roast_repo,
        inputs=[url_input],
        outputs=[roast_out, scorecard_out, red_flags_out, readme_out, summary, status],
    )

    url_input.submit(
        fn=roast_repo,
        inputs=[url_input],
        outputs=[roast_out, scorecard_out, red_flags_out, readme_out, summary, status],
    )

if __name__ == "__main__":
    demo.launch()