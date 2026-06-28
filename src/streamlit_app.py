"""Streamlit UI for StructIt offline document extraction."""

from __future__ import annotations

import csv
import json
import os
from io import StringIO

import pandas as pd
import streamlit as st

from src.database import get_document, init_db, list_documents
from src.document_pipeline import process_document

st.set_page_config(
    page_title="StructIt",
    page_icon="src/static/icon-192.png",
    layout="wide",
)


def main() -> None:
    """Render the Streamlit application."""
    init_db()
    st.sidebar.title("StructIt")
    page = st.sidebar.radio(
        "Navigation",
        ["Home", "Upload", "Results", "History", "Settings"],
    )

    if page == "Home":
        render_home()
    elif page == "Upload":
        render_upload()
    elif page == "Results":
        render_results()
    elif page == "History":
        render_history()
    else:
        render_settings()


def render_home() -> None:
    """Render the landing page."""
    st.title("StructIt")
    st.caption("Offline-first, CPU-only document structuring.")
    st.write(
        "Upload PDF, DOCX, TXT, or image files. StructIt extracts text locally, "
        "normalizes it, converts it to structured JSON, and stores results in SQLite."
    )
    st.info("No OpenAI, Anthropic, or cloud inference is used.")


def render_upload() -> None:
    """Render upload and processing workflow."""
    st.title("Upload")
    runtime = st.sidebar.selectbox(
        "Local model runtime",
        ["none", "llama.cpp", "ollama"],
        index=["none", "llama.cpp", "ollama"].index(
            os.getenv("STRUCTIT_LLM_RUNTIME", "none")
        ),
    )
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["pdf", "docx", "txt", "jpg", "jpeg", "png", "webp"],
        accept_multiple_files=False,
    )

    if not uploaded_file:
        return

    if st.button("Extract JSON", type="primary"):
        progress = st.progress(0)
        log_area = st.empty()
        logs = ["Reading uploaded file..."]
        log_area.code("\n".join(logs), language="text")

        try:
            progress.progress(20)
            with st.spinner("Processing locally on CPU..."):
                result = process_document(
                    uploaded_file.getvalue(),
                    filename=uploaded_file.name,
                    content_type=uploaded_file.type or "",
                    model_runtime=runtime,
                )
            progress.progress(100)
        except Exception as exc:
            st.error(f"Processing failed: {exc}")
            return

        logs.extend(result.get("logs", []))
        log_area.code("\n".join(logs), language="text")
        st.session_state["latest_document_id"] = result["id"]
        st.success(f"Saved document #{result['id']} with status: {result['status']}")
        render_document_result(result)


def render_results() -> None:
    """Render the most recent or selected result."""
    st.title("Results")
    document_id = st.session_state.get("latest_document_id")
    if not document_id:
        documents = list_documents(limit=1)
        document_id = documents[0]["id"] if documents else None

    if not document_id:
        st.info("No processed documents yet.")
        return

    document = get_document(int(document_id))
    if not document:
        st.warning("Selected document was not found.")
        return
    render_document_result(document)


def render_history() -> None:
    """Render document history table."""
    st.title("History")
    documents = list_documents(limit=200)
    if not documents:
        st.info("No history yet.")
        return

    frame = pd.DataFrame(documents)
    st.dataframe(frame, use_container_width=True, hide_index=True)

    selected_id = st.number_input(
        "Open document id",
        min_value=1,
        step=1,
        value=int(documents[0]["id"]),
    )
    document = get_document(int(selected_id))
    if document:
        render_document_result(document)


def render_settings() -> None:
    """Render local runtime settings."""
    st.title("Settings")
    st.write("All settings are local environment variables.")
    st.code(
        "\n".join(
            [
                "STRUCTIT_LLM_RUNTIME=none | llama.cpp | ollama",
                "STRUCTIT_OLLAMA_MODEL=llama3.2:3b",
                "TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
            ]
        ),
        language="text",
    )
    st.warning("Use only local models. Do not configure cloud API keys.")


def render_document_result(document: dict) -> None:
    """Render JSON result, raw text preview, logs, and downloads."""
    structured = document.get("structured_json") or document.get("structured") or {}
    st.subheader(document.get("filename", "Document"))
    st.caption(
        f"Status: {document.get('status')} | Source: {document.get('source_type')}"
    )

    left, right = st.columns([2, 1])
    with left:
        st.json(structured)
    with right:
        st.download_button(
            "Download JSON",
            data=json.dumps(structured, indent=2),
            file_name=f"structit_{document.get('id', 'result')}.json",
            mime="application/json",
        )
        st.download_button(
            "Download CSV",
            data=_structured_to_csv(structured),
            file_name=f"structit_{document.get('id', 'result')}.csv",
            mime="text/csv",
        )

    with st.expander("Extraction logs"):
        st.code("\n".join(document.get("logs", [])), language="text")
    with st.expander("Raw text preview"):
        st.text((document.get("raw_text") or "")[:4000])


def _structured_to_csv(structured: dict) -> str:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["field", "value"])
    for key, value in structured.items():
        if isinstance(value, list):
            writer.writerow([key, "; ".join(str(item) for item in value)])
        else:
            writer.writerow([key, value])
    return output.getvalue()


if __name__ == "__main__":
    main()
