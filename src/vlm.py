"""Optional local VLM integration via llama-cpp-python."""

import os
import threading
from pathlib import Path

from llama_cpp import Llama

# Path where models are stored
MODELS_DIR = Path.home() / ".pixstruct" / "models"
MOONDREAM_FILE = "moondream2-Q4_K_M.gguf"
VLM_TIMEOUT_SECONDS = 60

# Singleton — load model once, reuse across requests
_vlm_model: Llama | None = None


def _get_model() -> Llama:
    """Load model on first call, return cached instance after."""
    global _vlm_model
    if _vlm_model is None:
        model_path = MODELS_DIR / MOONDREAM_FILE
        if not model_path.exists():
            raise FileNotFoundError(
                f"Moondream2 model not found at {model_path}. "
                "Run `pixstruct setup` to download models."
            )
        _vlm_model = Llama(
            model_path=str(model_path),
            n_threads=max(1, (os.cpu_count() or 1) - 1),
            n_ctx=2048,
            verbose=False,
        )
    return _vlm_model


def describe_bill_image(image_bytes: bytes) -> str:
    """Return a local visual description when a GGUF VLM is installed."""
    model = _get_model()

    prompt = (
        "Describe the layout and content of this bill or receipt image. "
        "Identify: vendor or hospital name, date, all line items with prices, "
        "subtotal, tax, tip if any, and total amount. "
        "Be specific about numbers and names you can see."
    )

    result_holder: dict = {"output": "", "done": False}

    def _run_inference() -> None:
        try:
            response = model(
                prompt,
                max_tokens=512,
                stop=["</s>"],
            )
            result_holder["output"] = response["choices"][0]["text"].strip()
        except Exception as e:
            result_holder["output"] = f"VLM inference error: {e}"
        finally:
            result_holder["done"] = True

    # Run inference in a thread so we can enforce a timeout
    thread = threading.Thread(target=_run_inference, daemon=True)
    thread.start()
    thread.join(timeout=VLM_TIMEOUT_SECONDS)

    if not result_holder["done"]:
        # Timeout hit — return whatever partial output we have
        return result_holder["output"] or "VLM timed out — using OCR only."

    return result_holder["output"]
