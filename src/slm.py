"""Phi-3 Mini SLM integration via llama-cpp-python."""

import os
from pathlib import Path

from llama_cpp import Llama

MODELS_DIR = Path.home() / ".pixstruct" / "models"
PHI3_FILE = "Phi-3-mini-4k-instruct-Q4_K_M.gguf"

_slm_model: Llama | None = None


def _get_model() -> Llama:
    global _slm_model
    if _slm_model is None:
        model_path = MODELS_DIR / PHI3_FILE
        if not model_path.exists():
            raise FileNotFoundError(
                f"Phi-3 Mini model not found at {model_path}. "
                "Run `pixstruct setup` to download models."
            )
        _slm_model = Llama(
            model_path=str(model_path),
            n_threads=max(1, os.cpu_count() - 1),
            n_ctx=2048,
            verbose=False,
        )
    return _slm_model


def run_slm(prompt: str, system_prompt: str) -> str:
    """Run Phi-3 Mini with a system prompt and user prompt. Returns raw string."""
    model = _get_model()

    full_prompt = (
        f"<|system|>\n{system_prompt}<|end|>\n"
        f"<|user|>\n{prompt}<|end|>\n"
        "<|assistant|>\n"
    )

    response = model(
        full_prompt,
        max_tokens=1024,
        stop=["<|end|>", "<|user|>"],
        temperature=0.1,  # low temp = more deterministic JSON output
    )
    return response["choices"][0]["text"].strip()
