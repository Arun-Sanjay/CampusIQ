/**
 * Chat types — mirror backend Pydantic schemas in backend/app/schemas/chat.py
 */

export type ChatType = 'note_assistant' | 'college_gpt' | 'placement_chatbot' | 'resume_builder'

export type MessageRole = 'user' | 'assistant' | 'system'

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
}
