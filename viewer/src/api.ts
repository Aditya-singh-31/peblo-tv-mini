export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export interface Language { code: string }
export interface Episode { id: string; title: string; synopsis: string | null; duration_seconds: number | null; thumbnail: string | null; languages: Language[] }
export interface Season { number: number; title: string | null; episodes: Episode[] }
export interface Show { id: string; title: string; synopsis: string | null; categories: string[]; poster: string | null; banner: string | null; thumbnail: string | null; seasons: Season[] }
export interface Section { key: string; title: string; show_ids: string[] }
export interface Category { key: string; title: string; show_ids: string[] }
export interface Catalogue { schema_version: number; catalogue_version: string; featured_hero: { show_id: string; title: string; synopsis: string | null; poster: string | null; banner: string | null } | null; sections: Section[]; categories: Category[]; shows: Show[] }
export interface SearchEpisode extends Episode { season_number: number; season_title: string | null }
export interface SearchItem { show_id: string; title: string; synopsis: string | null; categories: string[]; poster: string | null; banner: string | null; thumbnail: string | null; episodes: SearchEpisode[] }
export interface SearchResponse { items: SearchItem[]; total: number }

export async function publicFetch<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`)
  const text = await response.text()
  const payload = text ? JSON.parse(text) : null
  if (!response.ok) throw new Error(typeof payload?.detail === 'string' ? payload.detail : 'The catalogue could not be loaded.')
  return payload as T
}

export const publicApi = {
  catalogue: () => publicFetch<Catalogue>('/catalog'),
  search: (params: { q?: string; category?: string; language?: string; section?: string }) => {
    const query = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => { if (value) query.set(key, value) })
    return publicFetch<SearchResponse>(`/catalog/search?${query.toString()}`)
  },
}
