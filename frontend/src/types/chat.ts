/**
 * Chat types — mirror backend Pydantic schemas in backend/app/schemas/chat.py
 */

export type ChatType =
  | 'note_assistant'
  | 'college_gpt'
  | 'placement_chatbot'
  | 'resume_builder'
  | 'admin_knowledge'

export type MessageRole = 'user' | 'assistant' | 'system'

/**
 * Note Assistant response modes — the student picks one per message.
 * - explain   — concept explanation in plain markdown (default)
 * - diagram   — Mermaid diagram followed by an explanation
 * - questions — solved / unsolved practice problems in fenced cards
 */
export type AssistantMode = 'explain' | 'diagram' | 'questions'

export interface SourceCitation {
  document_id: string
  document_title: string
  subject_code: string
  subject_name: string
  chunk_index: number
  similarity: number
}

export interface ChatMessage {
  id: string
  session_id: string
  role: MessageRole
  content: string
  source_citations: SourceCitation[] | null
  /** Note Assistant mode the response was generated in (null for legacy + non-NA chats). */
  mode?: AssistantMode | null
  created_at: string
}

export interface ChatSession {
  id: string
  user_id: string
  chat_type: ChatType
  subject_id: string | null
  title: string | null
  created_at: string
  last_message_at: string
}

export interface ChatSessionWithMessages extends ChatSession {
  messages: ChatMessage[]
}

export interface ChatSessionCreate {
  chat_type?: ChatType
  subject_id?: string
  title?: string
}

export interface ChatMessageRequest {
  content: string
  subject_id?: string
  stream?: boolean
  /** Note Assistant mode (server ignores it for non-NA sessions). */
  mode?: AssistantMode
}
