import gradio as gr
from github_fetcher import fetch_repo
from analyzer import analyze_repo

# ── Custom CSS — terminal hacker aesthetic ────────────────────────────────────
CSS = """
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
    --bg:        #080b0f;
    --bg2:       #0c1018;
    --bg3:       #111620;
    --border:    #1a2332;
    --border-hi: #243040;
    --green:     #00ff88;
    --green-dim: #00cc6a;
    --red:       #ff4455;
    --amber:     #ffaa00;
    --blue:      #4488ff;
    --text:      #c8d8e8;
    --muted:     #4a6080;
    --mono:      'JetBrains Mono', monospace;
    --sans:      'Space Grotesk', sans-serif;
}

/* ── Reset ── */
* { box-sizing: border-box; }

body, .gradio-container {
    background: var(--bg) !important;
    font-family: var(--mono) !important;
    color: var(--text) !important;
}

.gradio-container {
    max-width: 1000px !important;
    margin: 0 auto !important;
    padding: 0 !important;
}

/* Hide gradio footer and extra chrome */
footer, .built-with { display: none !important; }
.svelte-1ipelgc { display: none !important; }

/* ── Scanline overlay effect ── */
.gradio-container::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0, 255, 136, 0.01) 2px,
        rgba(0, 255, 136, 0.01) 4px
    );
    pointer-events: none;
    z-index: 9999;
}

/* ── Header ── */
.header-block {
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
    padding: 32px 40px 28px;
    position: relative;
    overflow: hidden;
}

.header-block::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--green), var(--amber), var(--red), transparent);
    animation: scanline 3s linear infinite;
}

@keyframes scanline {
    0%   { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}

/* ── Panels ── */
.panel {
    background: var(--bg2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    overflow: hidden;
}

.panel-header {
    background: var(--bg3);
    border-bottom: 1px solid var(--border);
    padding: 8px 16px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--muted);
    display: flex;
    align-items: center;
    gap: 8px;
}

.panel-header::before {
    content: '';
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 6px var(--green);
    animation: blink 2s ease-in-out infinite;
}

@keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}

/* ── Input ── */
.gr-textbox textarea, .gr-textbox input {
    background: var(--bg3) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    color: var(--green) !important;
    font-family: var(--mono) !important;
    font-size: 13px !important;
    padding: 12px 16px !important;
    caret-color: var(--green);
    transition: border-color 0.2s !important;
}

.gr-textbox textarea:focus, .gr-textbox input:focus {
    border-color: var(--green) !important;
    box-shadow: 0 0 0 2px rgba(0, 255, 136, 0.08) !important;
    outline: none !important;
}

.gr-textbox label span {
    font-family: var(--mono) !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: var(--muted) !important;
}

/* ── Button ── */
.roast-btn {
    background: transparent !important;
    border: 1px solid var(--green) !important;
    color: var(--green) !important;
    font-family: var(--mono) !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    padding: 12px 28px !important;
    border-radius: 4px !important;
    cursor: pointer !important;
    position: relative !important;
    overflow: hidden !important;
    transition: all 0.2s !important;
}

.roast-btn::before {
    content: '';
    position: absolute;
    inset: 0;
    background: var(--green);
    transform: translateX(-101%);
    transition: transform 0.2s ease;
}

.roast-btn:hover::before { transform: translateX(0); }
.roast-btn:hover { color: var(--bg) !important; }
.roast-btn:hover span { color: var(--bg) !important; position: relative; z-index: 1; }
.roast-btn span { position: relative; z-index: 1; }

/* ── Output areas ── */
.gr-textbox.output textarea {
    color: var(--text) !important;
    font-size: 14px !important;
    line-height: 1.8 !important;
    background: var(--bg2) !important;
    border: none !important;
    padding: 20px !important;
}

/* ── Markdown ── */
.gr-markdown {
    font-family: var(--mono) !important;
    color: var(--text) !important;
    font-size: 13px !important;
    line-height: 1.8 !important;
}

.gr-markdown h2 {
    font-family: var(--sans) !important;
    font-size: 14px !important;
    font-weight: 700 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: var(--green) !important;
    border-bottom: 1px solid var(--border) !important;
    padding-bottom: 8px !important;
    margin: 20px 0 14px !important;
}

.gr-markdown table {
    width: 100% !important;
    border-collapse: collapse !important;
    font-size: 13px !important;
}

.gr-markdown table th {
    background: var(--bg3) !important;
    color: var(--muted) !important;
    font-size: 10px !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    padding: 8px 12px !important;
    border: 1px solid var(--border) !important;
    text-align: left !important;
}

.gr-markdown table td {
    padding: 10px 12px !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    vertical-align: top !important;
}

.gr-markdown table tr:hover td {
    background: rgba(0, 255, 136, 0.03) !important;
}

.gr-markdown blockquote {
    border-left: 2px solid var(--amber) !important;
    padding: 8px 16px !important;
    margin: 12px 0 !important;
    background: rgba(255, 170, 0, 0.05) !important;
    border-radius: 0 4px 4px 0 !important;
    color: var(--amber) !important;
    font-style: italic !important;
}

.gr-markdown li {
    margin-bottom: 6px !important;
    padding-left: 4px !important;
}

.gr-markdown li::marker {
    color: var(--red) !important;
}

/* ── Accordion ── */
.gr-accordion {
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    background: var(--bg2) !important;
}

.gr-accordion summary {
    font-family: var(--mono) !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    color: var(--muted) !important;
    padding: 12px 16px !important;
    cursor: pointer !important;
    transition: color 0.2s !important;
}

.gr-accordion summary:hover { color: var(--text) !important; }

/* ── Code block ── */
.gr-code {
    background: var(--bg3) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    font-family: var(--mono) !important;
    font-size: 12px !important;
}

/* ── Status bar ── */
.status-bar textarea {
    font-family: var(--mono) !important;
    font-size: 12px !important;
    color: var(--green) !important;
    background: var(--bg3) !important;
    border: 1px solid var(--border) !important;
    padding: 8px 14px !important;
}

/* ── Divider ── */
hr {
    border: none !important;
    border-top: 1px solid var(--border) !important;
    margin: 8px 0 !important;
}

/* ── Summary block ── */
.repo-summary p {
    font-family: var(--mono) !important;
    font-size: 13px !important;
    color: var(--text) !important;
    padding: 12px 0 !important;
}

.repo-summary strong {
    color: var(--green) !important;
    font-weight: 700 !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-hi); border-radius: 2px; }

/* ── Animations ── */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}

.gr-markdown, .gr-textbox { animation: fadeIn 0.3s ease both; }
"""

HEADER = """
<div style="padding: 32px 40px 24px; background: #0c1018; border-bottom: 1px solid #1a2332; position: relative; overflow: hidden;">
    <div style="position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, transparent, #00ff88 30%, #ffaa00 60%, #ff4455, transparent);"></div>
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 10px;">
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #4a6080; letter-spacing: 0.15em;">
            <span style="color: #00ff88;">▸</span> build-small-hackathon
            <span style="margin: 0 8px; color: #1a2332;">│</span>
            <span style="color: #ffaa00;">chapter-one: backyard-ai</span>
            <span style="margin: 0 8px; color: #1a2332;">│</span>
            llama-3.1-8b · groq
        </div>
    </div>
    <h1 style="font-family: 'JetBrains Mono', monospace; font-size: 32px; font-weight: 700; color: #fff; margin: 0 0 6px; letter-spacing: -0.02em;">
        🔥 <span style="color: #00ff88;">roast</span>_my_repo<span style="color: #00ff88; animation: blink 1s step-end infinite;">_</span>
    </h1>
    <p style="font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #4a6080; margin: 0; letter-spacing: 0.02em;">
        paste a github url. brace yourself. &nbsp;
        <span style="color: #1a2332;">──</span>&nbsp;
        <span style="color: #ff4455;">brutal</span> · <span style="color: #ffaa00;">specific</span> · <span style="color: #00ff88;">actionable</span>
    </p>
</div>
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
</style>
"""

FOOTER = """
<div style="padding: 16px 40px; background: #0c1018; border-top: 1px solid #1a2332; font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #2a3848; display: flex; justify-content: space-between; align-items: center;">
    <span>built by <a href="https://github.com/Yokiatch" style="color: #4a6080; text-decoration: none;" target="_blank" rel="noopener noreferrer">Yokiatch</a> · hf build small hackathon 2026</span>
    <span>public repos only · 60 req/hr · <span style="color: #00ff88;">free</span></span>
</div>
"""


def roast_repo(github_url: str):
    empty = ("", "", "", "", "", "")
    if not github_url.strip():
        yield ("⚠ please enter a github url", "", "", "", "", "")
        return

    try:
        yield ("[ fetching repo... ]", "", "", "", "", "")
        data = fetch_repo(github_url.strip())

        yield ("[ analyzing codebase... ]", "", "", "", "", "")
        result = analyze_repo(data)

        sc = result["scorecard"]

        def score_bar(score):
            color = "#00ff88" if score >= 7 else "#ffaa00" if score >= 5 else "#ff4455"
            filled = "█" * score
            empty_b = "░" * (10 - score)
            return f'<span style="color:{color}; font-family: monospace;">{filled}{empty_b}</span> <span style="color:#c8d8e8;">{score}/10</span>'

        scorecard_md = f"""## 📊 Scorecard

| Dimension | Score | Reason |
|---|---|---|
| 🧠 Code Quality | {sc['code_quality']['score']}/10 | {sc['code_quality']['reason']} |
| 📄 Documentation | {sc['documentation']['score']}/10 | {sc['documentation']['reason']} |
| 🔒 Security | {sc['security']['score']}/10 | {sc['security']['reason']} |
| 🏗 Structure | {sc['structure']['score']}/10 | {sc['structure']['reason']} |
| 💼 Portfolio Value | {sc['portfolio_value']['score']}/10 | {sc['portfolio_value']['reason']} |

---

## 💼 Hire Me Score: {result['hire_score']}/10

> {result['hire_verdict']}
"""

        flags = result["red_flags"]
        flags_md = "\n".join([f"- 🚨 `{f}`" for f in flags]) if flags else "✅ no critical red flags found. rare."

        summary_md = f"""**`{data.owner}/{data.repo_name}`** &nbsp;·&nbsp; ⭐ {data.stars} &nbsp;·&nbsp; `{data.primary_language}` &nbsp;·&nbsp; 📁 {data.total_files} files

_{data.description}_"""

        yield (
            result["roast"],
            scorecard_md,
            flags_md,
            result["generated_readme"],
            summary_md,
            "✅ done — scroll down for results",
        )

    except ValueError as e:
        yield (f"❌ {e}", "", "", "", "", "error")
    except Exception as e:
        yield (f"❌ unexpected error: {e}", "", "", "", "", "error")


# ── UI ────────────────────────────────────────────────────────────────────────
with gr.Blocks(
    css=CSS,
    title="🔥 Roast My Repo",
    theme=gr.themes.Base(
        primary_hue="green",
        neutral_hue="slate",
    ),
) as demo:

    gr.HTML(HEADER)

    with gr.Column(elem_classes=["main-content"], scale=1):
        with gr.Row(equal_height=True):
            url_input = gr.Textbox(
                placeholder="https://github.com/username/repo",
                label="// target repository",
                show_label=True,
                scale=5,
            )
            roast_btn = gr.Button(
                "[ execute roast ]",
                variant="primary",
                scale=1,
                elem_classes=["roast-btn"],
            )

        status = gr.Textbox(
            label="// status",
            interactive=False,
            max_lines=1,
            elem_classes=["status-bar"],
        )

        summary = gr.Markdown(elem_classes=["repo-summary"])

        gr.HTML('<div style="height: 1px; background: #1a2332; margin: 8px 0;"></div>')

        with gr.Row():
            with gr.Column(scale=1):
                scorecard_out = gr.Markdown(label="scorecard")
            with gr.Column(scale=1):
                roast_out = gr.Textbox(
                    label="// the roast",
                    lines=14,
                    interactive=False,
                    elem_classes=["output"],
                )

        gr.HTML('<div style="height: 1px; background: #1a2332; margin: 8px 0;"></div>')

        red_flags_out = gr.Markdown(label="red flags")

        with gr.Accordion("// generated readme.md — copy & use", open=False):
            readme_out = gr.Code(language="markdown", label="")

    gr.HTML(FOOTER)

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