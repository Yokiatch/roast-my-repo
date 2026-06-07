# modal_app.py — MiniCPM4-8B inference server on Modal
# Deploy:  modal deploy modal_app.py
# Test:    modal run modal_app.py

import subprocess
import modal

# ── Volumes for caching model weights ────────────────────────────────────────
hf_cache_vol   = modal.Volume.from_name("huggingface-cache", create_if_missing=True)
vllm_cache_vol = modal.Volume.from_name("vllm-cache",        create_if_missing=True)

# ── Container image ───────────────────────────────────────────────────────────
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
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
        "VLLM_LOG_STATS_INTERVAL": "30",
    })
)

# ── Model config ──────────────────────────────────────────────────────────────
MODEL_NAME = "openbmb/MiniCPM4-8B"
VLLM_PORT  = 8000
N_GPU      = 1
MINUTES    = 60

# Hardcoded endpoint URL — update if you redeploy under a different workspace
MODAL_ENDPOINT = "https://dineshkr20231--roast-my-repo-serve.modal.run"

app = modal.App("roast-my-repo")


@app.function(
    image=vllm_image,
    gpu=f"A10G:{N_GPU}",
    scaledown_window=10 * MINUTES,
    timeout=10 * MINUTES,
    volumes={
        "/root/.cache/huggingface": hf_cache_vol,
        "/root/.cache/vllm":        vllm_cache_vol,
    },
)
@modal.concurrent(max_inputs=16)
@modal.web_server(port=VLLM_PORT, startup_timeout=10 * MINUTES)
def serve():
    """
    Starts a vLLM OpenAI-compatible server serving MiniCPM4-8B.
    Exposes standard /v1/chat/completions API.
    """
    cmd = [
        "vllm", "serve", MODEL_NAME,
        "--host", "0.0.0.0",
        "--port", str(VLLM_PORT),
        "--served-model-name", "minicpm4",
        "--trust-remote-code",
        "--max-model-len", "16384",
        "--gpu-memory-utilization", "0.90",
        "--enforce-eager",
        "--uvicorn-log-level", "warning",
    ]
    print("Starting vLLM:", " ".join(cmd))
    subprocess.Popen(" ".join(cmd), shell=True)


@app.function(schedule=modal.Period(minutes=8))
def keep_warm():
    """
    Pings /health every 8 minutes to prevent the vLLM container
    hitting the 10-minute scaledown window during active use.
    Activates automatically after: modal deploy modal_app.py
    """
    import urllib.request
    try:
        req = urllib.request.Request(f"{MODAL_ENDPOINT}/health")
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"[keep_warm] ✅ {resp.status}")
    except Exception as e:
        print(f"[keep_warm] ⚠ {e}")


# ── Local smoke-test ──────────────────────────────────────────────────────────
@app.local_entrypoint()
def main():
    """
    Quick smoke-test: call the deployed server from local machine.
    Run with: modal run modal_app.py
    """
    import urllib.request
    import json

    print("Sending test request to Modal endpoint...")

    payload = {
        "model": "minicpm4",
        "messages": [
            {"role": "user", "content": "Say 'MiniCPM4 is live on Modal!' and nothing else."}
        ],
        "max_tokens": 32,
        "temperature": 0.1,
    }

    req = urllib.request.Request(
        f"{MODAL_ENDPOINT}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        result = json.loads(resp.read())
        print("✅ Response:", result["choices"][0]["message"]["content"])