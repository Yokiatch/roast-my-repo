# modal_app.py — MiniCPM4-8B inference server on Modal
# Deploy:  modal deploy modal_app.py
# Test:    modal run modal_app.py
#
# After deploying, copy the printed URL into your .env as:
#   MODAL_ENDPOINT=https://your-workspace--roast-my-repo-serve.modal.run

import subprocess
import modal

# ── Volumes for caching model weights ────────────────────────────────────────
hf_cache_vol  = modal.Volume.from_name("huggingface-cache", create_if_missing=True)
vllm_cache_vol = modal.Volume.from_name("vllm-cache",       create_if_missing=True)

# ── Container image — CUDA base + vLLM ───────────────────────────────────────
vllm_image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.4.0-devel-ubuntu22.04",
        add_python="3.11",
    )
    .entrypoint([])
    .uv_pip_install(
        "vllm>=0.4.3",
        "huggingface_hub",
        "hf-transfer",
    )
    .env({
        "HF_HUB_ENABLE_HF_TRANSFER": "1",   # faster weight downloads
        "VLLM_LOG_STATS_INTERVAL": "30",
    })
)

# ── Model config ──────────────────────────────────────────────────────────────
MODEL_NAME    = "openbmb/MiniCPM4-8B"   # flagship OpenBMB model — 8B params, 8T token training
VLLM_PORT     = 8000
N_GPU         = 1
MINUTES       = 60

app = modal.App("roast-my-repo")


@app.function(
    image=vllm_image,
    gpu=f"A10G:{N_GPU}",           # A10G has 24GB VRAM — enough for 8B in fp16
    scaledown_window=10 * MINUTES, # keep warm for 10 min after last request
    timeout=10 * MINUTES,          # allow up to 10 min for cold start (model download)
    volumes={
        "/root/.cache/huggingface": hf_cache_vol,
        "/root/.cache/vllm":        vllm_cache_vol,
    },
)
@modal.concurrent(max_inputs=16)   # vLLM handles concurrent requests natively
@modal.web_server(port=VLLM_PORT, startup_timeout=10 * MINUTES)
def serve():
    """
    Starts a vLLM OpenAI-compatible server serving MiniCPM4-8B.
    The endpoint exposes the standard /v1/chat/completions API.
    """
    cmd = [
        "vllm", "serve", MODEL_NAME,
        "--host", "0.0.0.0",
        "--port", str(VLLM_PORT),
        "--served-model-name", "minicpm4",  # friendly alias for API calls
        "--trust-remote-code",              # required for MiniCPM custom code
        "--max-model-len", "16384",         # 16k context is plenty for code review
        "--gpu-memory-utilization", "0.90",
        "--enforce-eager",                  # skip CUDA graph compile on cold start
        "--uvicorn-log-level", "warning",
    ]
    print("Starting vLLM:", " ".join(cmd))
    subprocess.Popen(" ".join(cmd), shell=True)


@app.function(schedule=modal.Period(minutes=8))
def keep_warm():
    """
    Pings the /health endpoint every 8 minutes so the vLLM container
    never hits the 10-minute scaledown window during active use.
    Run: modal deploy modal_app.py  (scheduler activates automatically)
    """
    import urllib.request
    import os
    from dotenv import load_dotenv
    load_dotenv()
    url = os.getenv("MODAL_ENDPOINT", "").rstrip("/")
    if not url:
        print("[keep_warm] MODAL_ENDPOINT not set, skipping.")
        return
    try:
        req = urllib.request.Request(f"{url}/health")
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"[keep_warm] ✅ {resp.status}")
    except Exception as e:
        print(f"[keep_warm] ⚠ {e}")


# ── Local test entrypoint ─────────────────────────────────────────────────────
@app.local_entrypoint()
def main():
    """
    Quick smoke-test: call the deployed server from local machine.
    Run with: modal run modal_app.py
    """
    import urllib.request
    import json

    # Get the URL of the deployed function
    # You must have already run: modal deploy modal_app.py
    print("Sending test request to Modal endpoint...")

    import os
    from dotenv import load_dotenv
    load_dotenv()
    url = os.getenv("MODAL_ENDPOINT", "").rstrip("/")
    if not url:
        print("Set MODAL_ENDPOINT in your .env after running: modal deploy modal_app.py")
        return

    payload = {
        "model": "minicpm4",
        "messages": [
            {"role": "user", "content": "Say 'MiniCPM4 is live on Modal!' and nothing else."}
        ],
        "max_tokens": 32,
        "temperature": 0.1,
    }

    req = urllib.request.Request(
        f"{url}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:  # 5 min for cold start
        result = json.loads(resp.read())
        print("✅ Response:", result["choices"][0]["message"]["content"])