export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export type Role = 'editor' | 'admin'

export interface User {
  id: number
  email: string
  role: Role
}

export interface Show {
  id: number
  title: string
  synopsis: string | null
  section: string | null
  category: string | null
  categories: string | null
  status: 'draft' | 'published'
  created_at: string
  updated_at: string
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface Season {
  id: number
  show_id: number
  season_number: number
  title: string | null
  status: 'draft' | 'published'
  is_trailer: boolean
  created_at: string
  updated_at: string
}

export interface Episode {
  id: number
  season_id: number
  title: string
  synopsis: string | null
  duration_seconds: number | null
  language: string | null
  content_group: string | null
  category: string | null
  status: 'draft' | 'published'
  season_number: number
  artwork_count: number
  is_trailer: boolean
  created_at: string
  updated_at: string
}

export interface Artwork {
  id: number
  episode_id: number | null
  show_id: number | null
  artwork_type: 'POSTER' | 'BANNER' | 'THUMBNAIL'
  storage_key: string
  mime_type: string | null
  width: number | null
  height: number | null
  file_size_bytes: number | null
  url: string
  created_at: string
  updated_at: string
}

export interface ValidationIssue {
  severity: 'error' | 'warning'
  entity_type: 'show' | 'season' | 'episode' | 'artwork' | 'other'
  entity_id: number | null
  show_title: string | null
  season_title: string | null
  episode_title: string | null
  field: string
  problem: string
  suggested_fix: string
}

export interface ValidationReport {
  can_publish: boolean
  total_issues: number
  issues: ValidationIssue[]
  groups: Record<string, ValidationIssue[]>
}

export interface PublishRun {
  id: number
  initiated_by_id: number | null
  started_at: string
  finished_at: string | null
  status: string
  outcome: string | null
  show_count: number
  episode_count: number
  catalogue_key: string | null
  catalogue_version: string | null
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface PublishResponse {
  publish_run_id: number
  outcome: 'published'
  catalogue_version: string
  catalogue_key: string
  show_count: number
  episode_count: number
}

export interface SearchParams {
  page?: number
  page_size?: number
  search?: string
  section?: string
  status?: string
  language?: string
}

export class ApiError extends Error {
  status: number
  detail: unknown

  constructor(status: number, detail: unknown) {
    super(typeof detail === 'string' ? detail : 'Request failed')
    this.status = status
    this.detail = detail
  }
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  const token = localStorage.getItem('peblo_token')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')

  const response = await fetch(`${API_URL}${path}`, { ...options, headers })
  const text = await response.text()
  const payload = text ? JSON.parse(text) : null
  if (!response.ok) throw new ApiError(response.status, payload?.detail ?? payload)
  return payload as T
}

export const jsonBody = (value: unknown): RequestInit => ({
  method: 'POST',
  body: JSON.stringify(value),
})

export const api = {
  login: (email: string, password: string) => apiFetch<{ access_token: string; role: Role }>('/auth/login', jsonBody({ email, password })),
  me: () => apiFetch<User>('/auth/me'),
  shows: (params: SearchParams) => apiFetch<Page<Show>>(`/admin/shows?${new URLSearchParams(Object.entries(params).filter(([, value]) => value !== undefined && value !== '') as string[][])}`),
  show: (id: number) => apiFetch<Show>(`/admin/shows/${id}`),
  createShow: (body: Record<string, unknown>) => apiFetch<Show>('/admin/shows', jsonBody(body)),
  updateShow: (id: number, body: Record<string, unknown>) => apiFetch<Show>(`/admin/shows/${id}`, { ...jsonBody(body), method: 'PATCH' }),
  seasons: (showId: number) => apiFetch<Season[]>(`/admin/shows/${showId}/seasons`),
  createSeason: (showId: number, body: { season_number: number; title?: string; status: string }) => apiFetch<Season>(`/admin/shows/${showId}/seasons`, jsonBody(body)),
  updateSeason: (id: number, body: Record<string, unknown>) => apiFetch<Season>(`/admin/seasons/${id}`, { ...jsonBody(body), method: 'PATCH' }),
  deleteSeason: (id: number) => apiFetch<void>(`/admin/seasons/${id}`, { method: 'DELETE' }),
  episodes: (params: { season_id?: number; page?: number; page_size?: number; search?: string; status?: string; language?: string; show_id?: number }) => apiFetch<Page<Episode>>(`/admin/episodes?${new URLSearchParams(Object.entries(params).filter(([, value]) => value !== undefined && value !== '').map(([key, value]) => [key, String(value)])).toString()}`),
  createEpisode: (body: Record<string, unknown>) => apiFetch<Episode>('/admin/episodes', jsonBody(body)),
  updateEpisode: (id: number, body: Record<string, unknown>) => apiFetch<Episode>(`/admin/episodes/${id}`, { ...jsonBody(body), method: 'PATCH' }),
  deleteEpisode: (id: number) => apiFetch<void>(`/admin/episodes/${id}`, { method: 'DELETE' }),
  artwork: (params: { show_id?: number; episode_id?: number }) => apiFetch<Artwork[]>(`/admin/artwork?${new URLSearchParams(Object.entries(params).map(([key, value]) => [key, String(value)]))}`),
  uploadArtwork: (type: string, file: File, target: { show_id?: number; episode_id?: number }) => {
    const body = new FormData()
    body.append('file', file)
    return apiFetch<Artwork>(`/admin/artwork?artwork_type=${type}&${new URLSearchParams(Object.entries(target).map(([key, value]) => [key, String(value)]))}`, { method: 'POST', body })
  },
  validationReport: () => apiFetch<ValidationReport>('/admin/validation-report'),
  publish: () => apiFetch<PublishResponse>('/admin/catalog/publish', { method: 'POST' }),
  history: (page = 1) => apiFetch<Page<PublishRun>>(`/admin/catalog/history?page=${page}&page_size=20`),
}
