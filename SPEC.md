# Spec: StructIt

## 1. Summary

StructIt is an offline desktop application that converts invoice and receipt
images into structured JSON for local search, storage, and downstream
processing.

## 2. Problem Statement

Documents often exist as images rather than searchable structured data.
Invoices and receipts are commonly stored as JPG, PNG, or PDF image files,
which makes them difficult to search, filter, and analyze.

## 3. Goals

- Convert any invoice or receipt image into queryable JSON offline.
- Support common image-based document formats such as JPG, PNG, and PDF
  image files.
- Produce structured output that matches the invoice schema.
- Store processed results locally in SQLite without requiring network access.

## 4. Non-Goals

- Audio processing
- Video processing
- Cloud-based inference or storage
- GPU acceleration

## 5. User Stories

- As an accountant, I want to convert scanned invoices into structured JSON so
  I can search, filter, and report on them offline.
- As a privacy-conscious user, I want all document processing to remain local
  so my data never leaves my device.
- As an operator, I want clear failure handling for poor-quality scans so
  invalid or unparseable documents are surfaced safely.

## 6. Functional Requirements

- FR1: The system shall accept invoice and receipt images in JPG, PNG, and
  PDF image formats.
- FR2: The system shall run OCR over the input image to extract text content.
- FR3: The system shall use a locally stored LLM to transform OCR output into
  structured JSON that matches the invoice schema.
- FR4: The system shall persist the resulting JSON in a local SQLite database.
- FR5: The system shall return a structured failure or warning state when the
  input image is blurry, unreadable, or produces empty OCR output.
- FR6: The system shall retry or return a structured error when the LLM
  produces invalid JSON.
- FR7: The system shall operate without any network calls at runtime.

## 7. Non-Functional Requirements

- NFR1: Memory usage shall remain under 3GB during processing.
- NFR2: Average processing time shall remain under 30 seconds per image.
- NFR3: CPU usage shall remain below 75% during normal processing.
- NFR4: All OCR and LLM assets shall be stored locally and loaded without
  external services.

## 8. Architecture Overview

```text
Image -> OCR -> LLM -> JSON -> SQLite
```

## 9. Failure Handling

- Blurry image: flag the result as low confidence and return a clear warning
  or failure state.
- Empty OCR output: treat the document as unparseable and return a structured
  failure result.
- Invalid JSON from the LLM: retry with a recovery prompt or return a
  structured error response.

## 10. Acceptance Criteria

- A clear invoice image produces structured JSON matching the invoice schema.
- A low-quality or blurry image is marked with a warning or failure state.
- An empty OCR result is handled as a structured parse failure.
- Invalid LLM JSON output is recovered or surfaced as an explicit error.

## 11. Open Questions

- Which invoice schema version should be the initial target for output
  validation?
- Should the first release support batch processing of multiple images, or
  single-image processing only?
