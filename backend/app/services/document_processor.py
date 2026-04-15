"""Document processing pipeline — Phase 7.

Pipeline:
    1. Extract plaintext from the uploaded file (PyMuPDF / python-docx / text)
    2. Split into ~500-word chunks (divide and conquer, DAA Unit II)
    3. Huffman-encode each chunk (greedy algorithm, DAA Unit IV)
    4. Store DocumentChunk rows with plaintext + compressed bytes + codebook
    5. Generate an AI summary via Claude Haiku (optional, skipped if no API key)
    6. Update the document's processing_status to 'ready' or 'failed'

All of this runs in a FastAPI BackgroundTask so the POST /upload endpoint
returns immediately.
"""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.content import DocumentChunk
from app.models.user import Document, DocumentStatus
from app.services import chunking, claude_client, embeddings, huffman, text_extraction

logger = logging.getLogger(__name__)


def process_document(document_id: uuid.UUID) -> None:
    """Run the full processing pipeline for a document.

    This is called via FastAPI's BackgroundTasks, so it creates its own DB
    session (can't reuse the request session after the response returns).
    """
    with SessionLocal() as db:
        document = db.get(Document, document_id)
        if document is None:
            logger.error("process_document: document %s not found", document_id)
            return

        try:
            _run_pipeline(db, document)
        except Exception as e:
            logger.exception("Document processing failed for %s: %s", document_id, e)
            document.processing_status = DocumentStatus.FAILED
            db.commit()


def _run_pipeline(db: Session, document: Document) -> None:
    # ── Mark as processing ──
    document.processing_status = DocumentStatus.PROCESSING
    db.commit()
    logger.info("Processing document %s (%s)", document.id, document.file_name)

    # ── 1. Extract text ──
    try:
        text = text_extraction.extract_text(document.storage_path)
    except text_extraction.UnsupportedFormat as e:
        logger.warning("Unsupported format for %s: %s", document.id, e)
        document.processing_status = DocumentStatus.FAILED
        db.commit()
        return
    except Exception as e:
        logger.exception("Text extraction failed for %s", document.id)
        document.processing_status = DocumentStatus.FAILED
        db.commit()
        return

    if not text.strip():
        logger.warning("Document %s extracted empty text", document.id)
        document.processing_status = DocumentStatus.FAILED
        db.commit()
        return

    logger.info("Extracted %d chars from %s", len(text), document.file_name)

    # ── 2. Split into chunks ──
    chunks = chunking.split_into_chunks(text)
    logger.info("Split %s into %d chunks", document.file_name, len(chunks))

    if not chunks:
        document.processing_status = DocumentStatus.FAILED
        db.commit()
        return

    # ── 3. Huffman compress + 4. Embed (batched) + 5. Persist chunks ──
    # Clear any existing chunks first (in case of reprocessing)
    existing = db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).all()
    for row in existing:
        db.delete(row)
    db.flush()

    # Compute embeddings for ALL chunks in a single batch — much faster than
    # one-at-a-time encoding because Sentence Transformers vectorizes internally.
    chunk_texts = [c.text for c in chunks]
    if embeddings.is_available():
        try:
            chunk_embeddings = embeddings.embed_batch(chunk_texts)
            logger.info("Embedded %d chunks for %s", len(chunk_embeddings), document.file_name)
        except Exception as e:
            logger.warning("Embedding batch failed for %s: %s", document.id, e)
            chunk_embeddings = [[] for _ in chunks]
    else:
        logger.info("Embeddings unavailable — chunks will not be searchable")
        chunk_embeddings = [[] for _ in chunks]

    total_original = 0
    total_compressed = 0

    for chunk, embedding_vec in zip(chunks, chunk_embeddings):
        result = huffman.encode(chunk.text)
        total_original += result.original_size_bytes
        total_compressed += result.compressed_size_bytes

        db.add(
            DocumentChunk(
                document_id=document.id,
                chunk_index=chunk.index,
                chunk_text=chunk.text,
                compressed_text=result.compressed,
                codebook=result.codebook,
                compression_ratio=Decimal(str(result.savings_percent)),
                embedding=embedding_vec if embedding_vec else None,
            )
        )

    db.flush()

    total_savings = 0.0
    if total_original > 0:
        total_savings = round((1 - total_compressed / total_original) * 100, 2)

    logger.info(
        "Compressed %s: %d -> %d bytes (%.2f%% savings across %d chunks)",
        document.file_name,
        total_original,
        total_compressed,
        total_savings,
        len(chunks),
    )

    # ── 5. AI summary (best-effort) ──
    if claude_client.is_available():
        try:
            summary = claude_client.summarize_document(text)
            if summary:
                document.summary = summary
                logger.info("Generated summary for %s (%d chars)", document.id, len(summary))
        except Exception as e:
            # Never fail the whole pipeline because of the summary
            logger.warning("Summary generation failed for %s: %s", document.id, e)

    # ── 6. Mark ready ──
    document.processing_status = DocumentStatus.READY
    db.commit()
    logger.info("Document %s ready", document.id)


# ═══════════════════════════════════════════════════════════════
# Aggregate stats helpers (used by the API to populate responses)
# ═══════════════════════════════════════════════════════════════

def backfill_embeddings(document_id: uuid.UUID) -> int:
    """Generate embeddings for any chunks of `document_id` that are missing them.

    Useful for documents that were uploaded before Phase 8. Returns the number
    of chunks that received new embeddings.
    """
    if not embeddings.is_available():
        logger.warning("backfill_embeddings: embeddings not available")
        return 0

    with SessionLocal() as db:
        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .filter(DocumentChunk.embedding.is_(None))
            .order_by(DocumentChunk.chunk_index)
            .all()
        )
        if not chunks:
            return 0

        texts = [c.chunk_text for c in chunks]
        try:
            vectors = embeddings.embed_batch(texts)
        except Exception as e:
            logger.exception("backfill_embeddings failed: %s", e)
            return 0

        updated = 0
        for chunk, vec in zip(chunks, vectors):
            if vec:
                chunk.embedding = vec
                updated += 1
        db.commit()
        logger.info("Backfilled %d embeddings for document %s", updated, document_id)
        return updated


def aggregate_compression_stats(db: Session, document_id: uuid.UUID) -> dict:
    """Return {original_bytes, compressed_bytes, savings_percent, chunk_count}
    for all chunks of a document. Returns zeros if no chunks exist yet."""
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()
    if not chunks:
        return {
            "original_bytes": 0,
            "compressed_bytes": 0,
            "savings_percent": 0.0,
            "chunk_count": 0,
        }

    original = sum(len(c.chunk_text.encode("utf-8")) for c in chunks)
    compressed = sum(len(c.compressed_text or b"") for c in chunks)
    savings = 0.0
    if original > 0:
        savings = round((1 - compressed / original) * 100, 2)

    return {
        "original_bytes": original,
        "compressed_bytes": compressed,
        "savings_percent": savings,
        "chunk_count": len(chunks),
    }
