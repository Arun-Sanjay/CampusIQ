/**
 * Adaptive Learning Engine types — mirror backend Pydantic schemas in
 * backend/app/schemas/skills.py
 */

export interface SkillNodeResponse {
  name: string
  domain: string
  description: string
  difficulty_tier: number
}

export interface SkillEdgeResponse {
  from_skill: string
  to_skill: string
  base_weight_hours: number
  adjusted_weight_hours: number | null
  domain: string | null
}

export interface CompanyProfile {
  id: string
  company: string
  role: string
  required_skills: string[]
  preferred_skills: string[]
  difficulty_tier: number
}

export interface MasteryItem {
  skill: string
  mastery: number
}

export interface MasterySnapshotResponse {
  declared_skills: string[]
  quiz_topics: Record<string, number>
  per_skill: MasteryItem[]
}

export interface GapBreakdownResponse {
  student_has: string[]
  missing: string[]
  present_count: number
  required_count: number
  coverage_percent: number
  gap_percent: number
  cosine_similarity: number
}

export interface PathEdge {
  from_skill: string
  to_skill: string
  weight: number
}

export interface SkillPathResult {
  target: string
  total_hours: number
  nodes: string[]
  edges: PathEdge[]
  reachable: boolean
}

export interface MSTEdge {
  from_skill: string
  to_skill: string
  weight: number
}

export interface MSTResponse {
  nodes: string[]
  edges: MSTEdge[]
  total_weight: number
}

export interface KnapsackItemResponse {
  topic: string
  hours: number
  value: number
  reason: string
  included: boolean
}

export interface KnapsackResponse {
  budget_hours: number
  total_hours: number
  total_value: number
  predicted_improvement_percent: number
  items: KnapsackItemResponse[]
}

export interface AdaptivePlanRequest {
  company: string
  role?: string | null
  available_hours: number
}

export interface AdaptivePlanResponse {
  plan_id: string | null
  company: CompanyProfile
  mastery: MasterySnapshotResponse
  gap: GapBreakdownResponse
  paths: SkillPathResult[]
  mst: MSTResponse
  knapsack: KnapsackResponse
}

export interface StudyOptimizerHistoryRow {
  id: string
  target_company: string | null
  target_role: string | null
  available_hours: number
  included_topics: Record<string, unknown>[]
  predicted_improvement: number
  actual_improvement: number | null
  created_at: string
}
