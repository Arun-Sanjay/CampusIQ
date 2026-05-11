"""Tests for the admin Knowledge Editor — chunk CRUD + AI-mediated suggestions."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest

from app.models.content import (
    CollegeDocument,
    CollegeDocumentCategory,
    CollegeDocumentChunk,
)
from app.services.vector_search import CollegeSearchHit


def _signup(client, signup_payload, role: str) -> tuple[dict, str]:
    r = client.post("/api/v1/auth/signup", json=signup_payload(role))
    assert r.status_code in (200, 201), r.text
    data = r.json()
    return ({"Authorization": f"Bearer {data['access_token']}"}, data["user"]["id"])


def _seed_doc_with_chunk(
    db_session,
    *,
    uploader_id: uuid.UUID,
    chunk_text: str = "Lab attendance is 80% as per the current handbook.",
    category: CollegeDocumentCategory = CollegeDocumentCategory.HANDBOOK,
) -> tuple[CollegeDocument, CollegeDocumentChunk]:
    doc = CollegeDocument(
        uploaded_by_id=uploader_id,
        title="Test Handbook",
        file_name="handbook.pdf",
        storage_path="/tmp/handbook.pdf",
        file_type="application/pdf",
        document_category=category,
        processing_status="ready",
    )
    db_session.add(doc)
    db_session.flush()
    chunk = CollegeDocumentChunk(
        college_document_id=doc.id,
        chunk_index=0,
        chunk_text=chunk_text,
        compressed_text=b"\x00",
        codebook={},
        compression_ratio=Decimal("0.0"),
        embedding=None,
    )
    db_session.add(chunk)
    db_session.commit()
    db_session.refresh(doc)
    db_session.refresh(chunk)
    return doc, chunk


def test_patch_chunk_rewrites_text_embedding_and_compression(
    client, signup_payload, db_session
):
    admin_headers, admin_id = _signup(client, signup_payload, "admin")
    doc, chunk = _seed_doc_with_chunk(db_session, uploader_id=uuid.UUID(admin_id))

    original_compressed = bytes(chunk.compressed_text or b"")

    # Mock embeddings so we don't hit Sentence Transformers in CI.
    fake_embedding = [0.1] * 384
    with patch("app.services.chunk_edit.embeddings.is_available", return_value=True), \
        patch("app.services.chunk_edit.embeddings.embed_text", return_value=fake_embedding):
        r = client.patch(
            f"/api/v1/college-documents/{doc.id}/chunks/{chunk.id}",
            json={"chunk_text": "Lab attendance is now 75% per the updated handbook."},
            headers=admin_headers,
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["chunk_text"].startswith("Lab attendance is now 75%")
    # compression_ratio is recomputed (could be 0 for short text but field is present)
    assert body["compression_ratio"] is not None
    # original_bytes reflects the new text length
    assert body["original_bytes"] == len(
        "Lab attendance is now 75% per the updated handbook.".encode("utf-8")
    )

    db_session.refresh(chunk)
    assert chunk.chunk_text.startswith("Lab attendance is now 75%")
    assert bytes(chunk.compressed_text or b"") != original_compressed
    assert chunk.embedding is not None and len(list(chunk.embedding)) == 384


def test_patch_chunk_404_for_unknown_chunk(client, signup_payload, db_session):
    admin_headers, admin_id = _signup(client, signup_payload, "admin")
    doc, _ = _seed_doc_with_chunk(db_session, uploader_id=uuid.UUID(admin_id))

    with patch("app.services.chunk_edit.embeddings.is_available", return_value=False):
        r = client.patch(
            f"/api/v1/college-documents/{doc.id}/chunks/{uuid.uuid4()}",
            json={"chunk_text": "Some long-enough replacement text."},
            headers=admin_headers,
        )
    assert r.status_code == 404


def test_patch_chunk_forbidden_for_non_admin(client, signup_payload, db_session):
    admin_headers, admin_id = _signup(client, signup_payload, "admin")
    doc, chunk = _seed_doc_with_chunk(db_session, uploader_id=uuid.UUID(admin_id))

    student_headers, _ = _signup(client, signup_payload, "student")
    r = client.patch(
        f"/api/v1/college-documents/{doc.id}/chunks/{chunk.id}",
        json={"chunk_text": "Some long-enough replacement text."},
        headers=student_headers,
    )
    assert r.status_code == 403


def test_post_chunk_appends_with_correct_index(client, signup_payload, db_session):
    admin_headers, admin_id = _signup(client, signup_payload, "admin")
    doc, chunk = _seed_doc_with_chunk(db_session, uploader_id=uuid.UUID(admin_id))
    assert chunk.chunk_index == 0

    with patch("app.services.chunk_edit.embeddings.is_available", return_value=False):
        r = client.post(
            f"/api/v1/college-documents/{doc.id}/chunks",
            json={"chunk_text": "A brand new policy paragraph to append."},
            headers=admin_headers,
        )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["chunk_index"] == 1
    assert body["chunk_text"].startswith("A brand new policy")


def test_delete_chunk_removes_row(client, signup_payload, db_session):
    from sqlalchemy import select

    admin_headers, admin_id = _signup(client, signup_payload, "admin")
    doc, chunk = _seed_doc_with_chunk(db_session, uploader_id=uuid.UUID(admin_id))
    chunk_id = chunk.id

    r = client.delete(
        f"/api/v1/college-documents/{doc.id}/chunks/{chunk_id}",
        headers=admin_headers,
    )
    assert r.status_code == 204

    # Skip ORM identity map; query directly via Core to avoid refreshing the
    # stale chunk instance that the test session still holds.
    db_session.expunge_all()
    remaining = db_session.scalar(
        select(CollegeDocumentChunk).where(CollegeDocumentChunk.id == chunk_id)
    )
    assert remaining is None


def _fake_college_hit(chunk_id, doc_id, text, similarity, category="handbook"):
    return CollegeSearchHit(
        chunk_id=chunk_id,
        document_id=doc_id,
        document_title="Test Handbook",
        document_category=category,
        chunk_index=0,
        chunk_text=text,
        similarity=similarity,
    )


def test_suggest_update_existing(client, signup_payload, db_session):
    admin_headers, admin_id = _signup(client, signup_payload, "admin")
    doc, chunk = _seed_doc_with_chunk(db_session, uploader_id=uuid.UUID(admin_id))
    hit = _fake_college_hit(chunk.id, doc.id, chunk.chunk_text, similarity=0.82)

    with patch(
        "app.services.knowledge_suggest.embeddings.is_available", return_value=True
    ), patch(
        "app.services.knowledge_suggest.vector_search.search_college_chunks",
        return_value=[hit],
    ), patch(
        "app.services.knowledge_suggest.claude_client.generate_completion",
        return_value="Lab attendance is now 75% per the updated handbook.",
    ):
        r = client.post(
            "/api/v1/college-documents/suggest",
            json={"statement": "lab attendance is 75%"},
            headers=admin_headers,
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kind"] == "update_existing"
    assert body["similarity"] >= 0.55
    assert body["current_chunk_text"].startswith("Lab attendance is 80%")
    assert body["proposed_chunk_text"].startswith("Lab attendance is now 75%")
    assert body["document_id"] == str(doc.id)
    assert body["chunk_id"] == str(chunk.id)


def test_suggest_create_new_when_no_match(client, signup_payload, db_session):
    admin_headers, admin_id = _signup(client, signup_payload, "admin")
    doc, chunk = _seed_doc_with_chunk(db_session, uploader_id=uuid.UUID(admin_id))
    # Top hit's similarity below threshold → fall through to create_new
    weak_hit = _fake_college_hit(chunk.id, doc.id, chunk.chunk_text, similarity=0.31)

    with patch(
        "app.services.knowledge_suggest.embeddings.is_available", return_value=True
    ), patch(
        "app.services.knowledge_suggest.vector_search.search_college_chunks",
        return_value=[weak_hit],
    ), patch(
        "app.services.knowledge_suggest.claude_client.generate_completion",
        return_value="Phones are no longer permitted in the mess hall after 9pm.",
    ):
        r = client.post(
            "/api/v1/college-documents/suggest",
            json={"statement": "no phones in mess hall after 9pm"},
            headers=admin_headers,
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kind"] == "create_new"
    assert body["proposed_chunk_text"].startswith("Phones are no longer permitted")
    assert len(body["candidate_documents"]) == 1
    assert body["candidate_documents"][0]["document_id"] == str(doc.id)


def test_admin_knowledge_chat_type_blocked_for_students(client, signup_payload):
    student_headers, _ = _signup(client, signup_payload, "student")
    r = client.post(
        "/api/v1/chat/sessions",
        json={"chat_type": "admin_knowledge"},
        headers=student_headers,
    )
    assert r.status_code == 403, r.text
