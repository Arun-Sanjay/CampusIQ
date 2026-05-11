"""AI chat services — RAG over course or college documents.

Phase 9 (F2): Note Assistant — RAG over a student's course documents
Phase 10 (F5): CollegeGPT — RAG over admin-uploaded college documents

Pipeline for each user message:
    1. Retrieve top-K most semantically similar chunks from pgvector
    2. Build a system prompt that grounds Claude in those chunks
    3. Stream Claude's response to the caller
    4. Persist user message + assistant message + source citations after the
       stream completes
"""
from __future__ import annotations

import logging
import uuid
from collections.abc import Iterator
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, ChatSession, ChatType, MessageRole
from app.models.user import User
from app.services import chat as chat_service
from app.services import claude_client, vector_search
from app.services.vector_search import CollegeSearchHit, SearchHit

logger = logging.getLogger(__name__)


# ── RAG configuration ──
TOP_K = 5
MAX_CHUNK_CHARS = 1500          # truncate any single chunk to keep prompt sane
MAX_HISTORY_MESSAGES = 8         # last N turns of conversation to keep
MAX_TOKENS = 1024                # default cap on Claude's response length
QUESTIONS_MODE_MAX_TOKENS = 1500  # solved problems with steps need more headroom


# Shared header for all three Note Assistant modes — keeps the grounding +
# behavior rules consistent and lets each mode-specific tail focus only on
# response shape.
NOTE_ASSISTANT_HEADER = """You are CampusIQ Note Assistant — an AI tutor that helps engineering students understand their course material.

You are given the most relevant excerpts from the student's own course documents below as CONTEXT. Use them to answer the student's question.

CRITICAL OUTPUT FORMAT RULES:
- Ground every claim in the provided context. If the answer isn't in the context, say so honestly.
- Use clear, conversational language — like a friendly senior explaining a topic.
- DO NOT mention "context" or "excerpts" — answer naturally.
- DO NOT invent facts that aren't in the context."""


EXPLAIN_MODE_TAIL = """RESPONSE STYLE — EXPLANATION:
- Lead with a one-sentence direct answer.
- Then expand in 2-4 short paragraphs, building intuition before formalism.
- Use H3 (###) for subsections only when the topic genuinely has 2+ subtopics.
- Use a bulleted list when (and only when) you have 3+ parallel items.
- Use inline code (`like_this`) for identifiers; fenced code blocks only for runnable snippets.
- DO NOT use any of these special fenced blocks: ```solved, ```unsolved, ```answer, ```mermaid. Those are for other modes.
- Aim for 150-400 words. Resist longer; cut hedging."""


DIAGRAM_MODE_TAIL = """RESPONSE STYLE — DIAGRAM + EXPLANATION:

You MUST produce exactly one Mermaid diagram followed by a short explanation.

OUTPUT TEMPLATE (follow exactly):

  <one-sentence intro: what the diagram shows>

  ```mermaid
  <valid Mermaid syntax — see DIAGRAM TYPES below>
  ```

  ### How to read this
  <2-3 short paragraphs walking through the diagram>

DIAGRAM TYPES — pick the one that fits the question:
- Flowchart (default for processes/algorithms): `flowchart TD` with `A[Step]`, `B{Decision}`, `A --> B`.
- Sequence diagram (for protocols/interactions): `sequenceDiagram` with `Alice->>Bob: msg`.
- State machine (for state-driven systems): `stateDiagram-v2` with `[*] --> S1` and `S1 --> S2 : event`.
- Class/ER (for data models): `classDiagram` or `erDiagram`.
- Graph (for graph algorithms / trees): `graph LR` with edges.

MERMAID RULES (strict — diagrams that violate these will fail to render):
- Always start with the diagram-type keyword on its own line.
- Node IDs must be alphanumeric; labels go in `[]` or `{}` or `()`.
- No HTML inside labels; escape special chars (`#35;` for `#`).
- Keep diagrams under 25 nodes — split into multiple if larger.
- DO NOT include the word "mermaid" inside the diagram itself.

If the question doesn't naturally lend itself to a visual, produce a tiny conceptual flowchart of "Topic -> Key Idea 1 / Key Idea 2 / Key Idea 3"."""


QUESTIONS_MODE_TAIL = """RESPONSE STYLE — PRACTICE PROBLEMS:

Parse the student's request to determine:
- How many problems they want (default: 3 if unspecified).
- Whether they want SOLVED, UNSOLVED, or BOTH (default: 2 solved + 1 unsolved).
- The topic/concept to test on.

OUTPUT FORMAT — produce one fenced block per problem, in order:

For a SOLVED problem:
  ```solved meta={"index": 1, "problem": "<one-line problem statement>"}
  STEP 1 — <TITLE IN CAPS, e.g. "CHARACTERISTIC EQUATION">
  <body — math, derivation, plain prose>

  STEP 2 — <title>
  <body>

  STEP N — <title>
  <body>

  ANSWER
  <final boxed result, e.g. "x = 5">
  ```

For an UNSOLVED practice problem:
  ```unsolved meta={"index": 1, "problem": "<one-line problem statement>", "hint": "<one-line hint, hidden by default>"}
  <2-3 sentence intro: why this matters, what concept it tests>

  Steps to try:
  1. <hint at first step>
  2. <hint at second step>
  3. <hint at third step>
  ```

STRICT RULES:
- One fenced block per problem. Do not combine.
- The `meta=` JSON must be on the same line as the opening fence and be valid JSON.
- Use STEP N — TITLE (uppercase, em-dash) headers inside solved problems — the renderer styles these specially.
- The ANSWER block must come last inside a solved problem.
- For unsolved problems, the `hint` field is hidden until the student clicks "Show hint" — keep it to one line.
- Between fenced blocks, put one blank line. No prose between blocks.
- Open with one short sentence (e.g. "Here are 3 problems on Dijkstra — 2 solved, 1 for you to try.") then the fenced blocks.

If the student's request can't be parsed, ask one clarifying question instead of producing problems."""


# Pre-composed full prompts so we don't re-concat on every request.
EXPLAIN_MODE_SYSTEM = f"{NOTE_ASSISTANT_HEADER}\n\n{EXPLAIN_MODE_TAIL}"
DIAGRAM_MODE_SYSTEM = f"{NOTE_ASSISTANT_HEADER}\n\n{DIAGRAM_MODE_TAIL}"
QUESTIONS_MODE_SYSTEM = f"{NOTE_ASSISTANT_HEADER}\n\n{QUESTIONS_MODE_TAIL}"

# Backwards-compat alias — older code paths may still import the original constant.
NOTE_ASSISTANT_SYSTEM = EXPLAIN_MODE_SYSTEM


def _select_note_assistant_system_prompt(mode: str | None) -> tuple[str, int]:
    """Pick the system prompt + max-tokens budget for the requested Note Assistant mode.

    Unknown / missing modes fall back to Explain (the default behavior).
    """
    if mode == "diagram":
        return DIAGRAM_MODE_SYSTEM, MAX_TOKENS
    if mode == "questions":
        return QUESTIONS_MODE_SYSTEM, QUESTIONS_MODE_MAX_TOKENS
    return EXPLAIN_MODE_SYSTEM, MAX_TOKENS


COLLEGE_GPT_SYSTEM = """You are CollegeGPT — an AI assistant that answers questions about a student's college using its OFFICIAL DOCUMENTS (handbooks, timetables, placement records, faculty lists, hostel rules).

You are given the most relevant excerpts from the college's documents below as CONTEXT. Use them to answer the student's question.

Guidelines:
- Always ground your answers in the provided context. If the official documents don't cover the question, say so honestly and recommend the student check with the relevant office (academic, hostel, placement, etc.).
- Be precise about rules, dates, and policies — students rely on this for compliance.
- When citing a rule, mention which type of document it came from (handbook, hostel rules, etc.) so the student knows where to look it up.
- Use clear, conversational language and short paragraphs.
- DO NOT make up policies that aren't in the documents.
- DO NOT mention the word "context" or "excerpts" — just answer naturally."""


PLACEMENT_CHATBOT_SYSTEM = """You are CampusIQ Placement Coach — an AI mentor that helps engineering students prepare for campus placements.

You are given RELEVANT EXCERPTS from the college's placement records (previous interview experiences, CGPA cutoffs, hiring trends, offer data). Use them to give concrete, data-backed advice.

Guidelines:
- Ground every claim in the provided context when it's there. If the records don't cover the question, answer from general placement wisdom but make that clear.
- Be direct and actionable. Students want specific guidance on what to study, what to expect in interviews, and how to negotiate.
- When citing numbers (CGPA cutoffs, package ranges, selection rates), quote them exactly from the records and mention they're based on college data.
- Never guarantee an offer — give probabilistic, grounded advice instead.
- Use short paragraphs and bulleted lists when helpful.
- DO NOT mention the word "context" or "excerpts" — just answer naturally, like a knowledgeable senior passing down hard-won advice."""


@dataclass
class StreamedAnswer:
    """Final result captured after a streaming response completes."""

    text: str
    citations: list[dict]


def _format_chunks_as_context(hits: list[SearchHit]) -> str:
    """Render retrieved subject doc chunks as a numbered context block."""
    if not hits:
        return "(No relevant material was found in the student's documents.)"

    parts: list[str] = []
    for i, hit in enumerate(hits, start=1):
        truncated = hit.chunk_text
        if len(truncated) > MAX_CHUNK_CHARS:
            truncated = truncated[:MAX_CHUNK_CHARS] + "…"
        parts.append(
            f"[{i}] {hit.subject_code} — {hit.document_title} (chunk {hit.chunk_index})\n"
            f"{truncated}"
        )
    return "\n\n---\n\n".join(parts)


def _format_college_chunks_as_context(hits: list[CollegeSearchHit]) -> str:
    """Render retrieved college doc chunks as a numbered context block."""
    if not hits:
        return "(No relevant material was found in the college's documents.)"

    parts: list[str] = []
    for i, hit in enumerate(hits, start=1):
        truncated = hit.chunk_text
        if len(truncated) > MAX_CHUNK_CHARS:
            truncated = truncated[:MAX_CHUNK_CHARS] + "…"
        parts.append(
            f"[{i}] {hit.document_category.upper()} — {hit.document_title} (chunk {hit.chunk_index})\n"
            f"{truncated}"
        )
    return "\n\n---\n\n".join(parts)


def _citations_from_hits(hits: list[SearchHit]) -> list[dict]:
    """Compact citation records for note-assistant chunks."""
    return [
        {
            "document_id": str(hit.document_id),
            "document_title": hit.document_title,
            "subject_code": hit.subject_code,
            "subject_name": hit.subject_name,
            "chunk_index": hit.chunk_index,
            "similarity": round(hit.similarity, 4),
        }
        for hit in hits
    ]


def _citations_from_college_hits(hits: list[CollegeSearchHit]) -> list[dict]:
    """Compact citation records for CollegeGPT chunks. Uses the same citation
    schema as note-assistant so the frontend can render either uniformly —
    `subject_code` is repurposed to show the document category."""
    return [
        {
            "document_id": str(hit.document_id),
            "document_title": hit.document_title,
            "subject_code": hit.document_category.upper(),
            "subject_name": hit.document_title,
            "chunk_index": hit.chunk_index,
            "similarity": round(hit.similarity, 4),
        }
        for hit in hits
    ]


def stream_rag_response(
    db: Session,
    *,
    user: User,
    session: ChatSession,
    user_message_text: str,
    subject_id: uuid.UUID | None = None,
    mode: str | None = None,
) -> Iterator[str]:
    """Generator that:
    1. Retrieves chunks (note-assistant or college-gpt depending on session.chat_type)
    2. Persists the user message
    3. Yields the assistant's response as text deltas
    4. Persists the assistant message + citations after the stream is exhausted

    `mode` is only meaningful for Note Assistant sessions and selects which
    system-prompt variant the LLM gets. Non-Note-Assistant sessions ignore it.

    The caller (route handler) wraps this in a StreamingResponse.
    """
    is_college_gpt = session.chat_type == ChatType.COLLEGE_GPT
    is_placement_chatbot = session.chat_type == ChatType.PLACEMENT_CHATBOT
    is_note_assistant = session.chat_type == ChatType.NOTE_ASSISTANT

    # ── 1. Retrieve relevant chunks (different table / filter per chat_type) ──
    if is_placement_chatbot:
        # Placement Chatbot reuses the college docs table but filters to
        # the `placement_record` category so it only sees placement-specific
        # excerpts (CGPA cutoffs, interview experiences, offer data).
        college_hits = vector_search.search_college_chunks(
            db,
            query=user_message_text,
            user=user,
            category="placement_record",
            top_k=TOP_K,
        )
        citations = _citations_from_college_hits(college_hits)
        context_block = _format_college_chunks_as_context(college_hits)
    elif is_college_gpt:
        college_hits = vector_search.search_college_chunks(
            db,
            query=user_message_text,
            user=user,
            top_k=TOP_K,
        )
        citations = _citations_from_college_hits(college_hits)
        context_block = _format_college_chunks_as_context(college_hits)
    else:
        hits = vector_search.search_chunks(
            db,
            query=user_message_text,
            user=user,
            subject_id=subject_id,
            top_k=TOP_K,
        )
        citations = _citations_from_hits(hits)
        context_block = _format_chunks_as_context(hits)

    # ── 2. Save the user message right away (before streaming) ──
    chat_service.add_message(db, session, MessageRole.USER, user_message_text)

    # ── 3. Build the prompt: system + recent history + new user turn ──
    if is_placement_chatbot:
        system_prompt = (
            f"{PLACEMENT_CHATBOT_SYSTEM}\n\n"
            f"=== RELEVANT EXCERPTS FROM PLACEMENT RECORDS ===\n\n"
            f"{context_block}\n\n"
            f"=== END OF EXCERPTS ==="
        )
        max_tokens = MAX_TOKENS
    elif is_college_gpt:
        system_prompt = (
            f"{COLLEGE_GPT_SYSTEM}\n\n"
            f"=== RELEVANT MATERIAL FROM THE COLLEGE'S OFFICIAL DOCUMENTS ===\n\n"
            f"{context_block}\n\n"
            f"=== END OF MATERIAL ==="
        )
        max_tokens = MAX_TOKENS
    else:
        # Note Assistant — pick the prompt variant for the requested mode.
        base_prompt, max_tokens = _select_note_assistant_system_prompt(mode)
        system_prompt = (
            f"{base_prompt}\n\n"
            f"=== RELEVANT MATERIAL FROM THE STUDENT'S COURSE DOCUMENTS ===\n\n"
            f"{context_block}\n\n"
            f"=== END OF MATERIAL ==="
        )

    # Recent history (excluding the user message we just persisted, since we'll
    # send it as the final turn)
    history_msgs = chat_service.list_messages(db, session)
    # Drop the just-added user message from history (we re-add it below)
    history_msgs = [m for m in history_msgs if m.id != _last_user_message_id(history_msgs)]
    # Limit to recent N
    history_msgs = history_msgs[-MAX_HISTORY_MESSAGES:]

    messages_for_claude: list[dict] = [
        {"role": m.role.value, "content": m.content}
        for m in history_msgs
        if m.role != MessageRole.SYSTEM
    ]
    messages_for_claude.append({"role": "user", "content": user_message_text})

    # ── 4. Stream the response, capturing the full text as we go ──
    full_text_parts: list[str] = []
    try:
        for delta in claude_client.stream_completion(
            system=system_prompt,
            messages=messages_for_claude,
            max_tokens=max_tokens,
            temperature=0.4,
        ):
            full_text_parts.append(delta)
            yield delta
    finally:
        # ── 5. Persist the assistant message even if the client disconnects ──
        full_text = "".join(full_text_parts).strip()
        if full_text:
            # Stash the rendering mode so history re-renders use the right parser.
            assistant_meta = {"mode": mode or "explain"} if is_note_assistant else None
            chat_service.add_message(
                db,
                session,
                MessageRole.ASSISTANT,
                full_text,
                source_citations=citations,
                assistant_meta=assistant_meta,
            )


def _last_user_message_id(messages: list[ChatMessage]) -> uuid.UUID | None:
    """Return the id of the most recent user message in `messages`."""
    for m in reversed(messages):
        if m.role == MessageRole.USER:
            return m.id
    return None


def answer_question_blocking(
    db: Session,
    *,
    user: User,
    session: ChatSession,
    user_message_text: str,
    subject_id: uuid.UUID | None = None,
    mode: str | None = None,
) -> StreamedAnswer:
    """Non-streaming convenience wrapper. Used by tests + frontends that don't
    want to bother with chunked transfer encoding."""
    text_parts: list[str] = []
    for delta in stream_rag_response(
        db,
        user=user,
        session=session,
        user_message_text=user_message_text,
        subject_id=subject_id,
        mode=mode,
    ):
        text_parts.append(delta)

    # The streaming generator already persisted the assistant message; pull its
    # citations off the freshly-saved row.
    last = chat_service.list_messages(db, session)[-1]
    return StreamedAnswer(
        text="".join(text_parts).strip(),
        citations=last.source_citations or [],
    )
