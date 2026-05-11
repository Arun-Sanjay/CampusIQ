/**
 * Tracks in-flight AI quiz generations across the teacher portal so the
 * chip overlay stays visible even when the teacher navigates away from
 * /teacher/quizzes while the request is still cooking.
 */
import { create } from 'zustand'
import type { Difficulty } from '../types'

export interface PendingQuizGen {
  id: string
  startedAt: number
  subjectCode: string
  subjectName: string
  difficulty: Difficulty
  numQuestions: number
  topic: string | null
}

interface QuizGenerationStore {
  pending: PendingQuizGen[]
  add: (job: PendingQuizGen) => void
  remove: (id: string) => void
  clear: () => void
}

export const useQuizGenerationStore = create<QuizGenerationStore>((set) => ({
  pending: [],
  add: (job) => set((state) => ({ pending: [...state.pending, job] })),
  remove: (id) => set((state) => ({ pending: state.pending.filter((p) => p.id !== id) })),
  clear: () => set({ pending: [] }),
}))
