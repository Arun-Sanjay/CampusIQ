"""College document processing pipeline (Phase 10, F5).

Same shape as `services/document_processor.py` but writes to
`college_document_chunks` instead of `document_chunks`. Kept as a separate
module so the schemas, error paths, and ownership rules don't drift.
"""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.content import CollegeDocument, CollegeDocumentChunk
from app.services import chunking, claude_client, embeddings, huffman, text_extraction

logger = logging.getLogger(__name__)


def process_college_document(college_document_id: uuid.UUID) -> None:
    """Run the full processing pipeline for a college document.

    Called via FastAPI BackgroundTasks, so it owns its own session.
    """
    with SessionLocal() as db:
        document = db.get(CollegeDocument, college_document_id)
        if document is None:
            logger.error(
                "process_college_document: document %s not found", college_document_id
            )
            return

        try:
            _run_pipeline(db, document)
        except Exception as e:
            logger.exception(
                "College document processing failed for %s: %s", college_document_id, e
            )
            document.processing_status = "failed"
            db.commit()


def _run_pipeline(db: Session, document: CollegeDocument) -> None:
    document.processing_status = "processing"
    db.commit()
    logger.info("Processing college document %s (%s)", document.id, document.file_name)

    # ── 1. Extract text ──
    try:
        text = text_extraction.extract_text(document.storage_path)
    except text_extraction.UnsupportedFormat as e:
        logger.warning("Unsupported format for %s: %s", document.id, e)
        document.processing_status = "failed"
        db.commit()
        return
    except Exception:
        logger.exception("Text extraction failed for %s", document.id)
        document.processing_status = "failed"
        db.commit()
        return

    if not text.strip():
        logger.warning("College document %s extracted empty text", document.id)
        document.processing_status = "failed"
        db.commit()
        return

    logger.info("Extracted %d chars from %s", len(text), document.file_name)

    # ── 2. Chunk ──
    chunks = chunking.split_into_chunks(text)
    logger.info("Split %s into %d chunks", document.file_name, len(chunks))

    if not chunks:
        document.processing_status = "failed"
        db.commit()
        return

    # ── 3. Clear old chunks (reprocessing case) ──
    existing = (
        db.query(CollegeDocumentChunk)
        .filter(CollegeDocumentChunk.college_document_id == document.id)
        .all()
    )
    for row in existing:
        db.delete(row)
    db.flush()

    # ── 4. Batch-embed ──
    chunk_texts = [c.text for c in chunks]
    if embeddings.is_available():
        try:
            chunk_embeddings = embeddings.embed_batch(chunk_texts)
            logger.info(
                "Embedded %d college chunks for %s",
                len(chunk_embeddings),
                document.file_name,
            )
        except Exception as e:
            logger.warning("College embedding batch failed for %s: %s", document.id, e)
            chunk_embeddings = [[] for _ in chunks]
    else:
        logger.info("Embeddings unavailable — college chunks won't be searchable")
        chunk_embeddings = [[] for _ in chunks]

    # ── 5. Huffman compress + persist ──
    total_original = 0
    total_compressed = 0
    for chunk, embedding_vec in zip(chunks, chunk_embeddings):
        result = huffman.encode(chunk.text)
        total_original += result.original_size_bytes
        total_compressed += result.compressed_size_bytes

        db.add(
            CollegeDocumentChunk(
                college_document_id=document.id,
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

    # ── 6. AI summary (best-effort) ──
    if claude_client.is_available():
        try:
            summary = claude_client.summarize_document(text)
            if summary:
                document.summary = summary
                logger.info(
                    "Generated college summary for %s (%d chars)",
                    document.id,
                    len(summary),
                )
        except Exception as e:
            logger.warning("College summary generation failed for %s: %s", document.id, e)

    document.processing_status = "ready"
    db.commit()
    logger.info("College document %s ready", document.id)
