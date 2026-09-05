import { useEffect, useMemo, useState } from 'react'
import { Link, Route, Routes, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Catalogue, Episode, Show, publicApi, SearchItem } from './api'

function Image({ src, alt, className = '' }: { src: string | null; alt: string; className?: string }) {
  const [failed, setFailed] = useState(false)
  return <div className={`image-frame ${className}`}>{src && !failed ? <img src={src} alt={alt} loading="lazy" onError={() => setFailed(true)} /> : <div className="image-fallback"><span>PB</span></div>}</div>
}

function Loading({ tall = false }: { tall?: boolean }) { return <div className={`loading-screen ${tall ? 'tall' : ''}`}><span className="loader" /><span>Loading catalogue</span></div> }
function ErrorState({ retry }: { retry: () => void }) { return <div className="state-screen"><span className="state-kicker">Catalogue unavailable</span><h1>We lost the signal.</h1><p>There is a problem loading the published catalogue right now.</p><button className="button light" onClick={retry}>Try again</button></div> }
function EmptyState({ title = 'Nothing here yet', copy = 'Try a different search or filter.' }: { title?: string; copy?: string }) { return <div className="empty-state"><span>PB</span><h2>{title}</h2><p>{copy}</p></div> }
function AppShell({ catalogue }: { catalogue: Catalogue }) {
  const [search, setSearch] = useState('')
  const navigate = useNavigate()
  const location = useLocation()
  return <div className="site-shell"><header className="topbar"><Link className="wordmark" to="/"><span>PB</span><strong>PEBLO</strong></Link><nav><Link className={location.pathname === '/' ? 'active' : ''} to="/">Home</Link><Link className={location.pathname.startsWith('/search') ? 'active' : ''} to="/search">Browse</Link></nav><form className="search-mini" onSubmit={(event) => { event.preventDefault(); if (search.trim()) navigate(`/search?q=${encodeURIComponent(search.trim())}`) }}><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search shows, episodes…" aria-label="Search catalogue" /><button aria-label="Search" type="submit">⌕</button></form></header><main><Routes><Route path="/" element={<Home catalogue={catalogue} />} /><Route path="/search" element={<SearchPage catalogue={catalogue} />} /><Route path="/shows/:showId" element={<ShowDetail catalogue={catalogue} />} /><Route path="*" element={<Home catalogue={catalogue} />} /></Routes></main><footer><span>PEBLO TV</span><span>Published catalogue · {catalogue.catalogue_version}</span></footer></div>
}

function Home({ catalogue }: { catalogue: Catalogue }) {
  const showMap = useMemo(() => new Map(catalogue.shows.map((show) => [show.id, show])), [catalogue.shows])
  if (!catalogue.shows.length) return <EmptyState title="The catalogue is quiet" copy="Published shows will appear here when the next catalogue is live." />
  return <><Hero catalogue={catalogue} /><div className="home-content">{catalogue.sections.map((section) => { const shows = section.show_ids.map((id) => showMap.get(id)).filter((show): show is Show => Boolean(show)); return shows.length ? <ShowRow key={section.key} title={section.title} shows={shows} /> : null })}</div></>
}

function Hero({ catalogue }: { catalogue: Catalogue }) {
  const hero = catalogue.featured_hero
  if (!hero) return null
  return <section className="hero"><Image src={hero.banner} alt="" className="hero-image" /><div className="hero-shade" /><div className="hero-copy"><span className="hero-label">Featured</span><h1>{hero.title}</h1><p>{hero.synopsis}</p><Link className="button light" to={`/shows/${hero.show_id}`}>Explore show <span>↗</span></Link></div></section>
}

function ShowRow({ title, shows }: { title: string; shows: Show[] }) { return <section className="show-row"><div className="row-heading"><h2>{title}</h2><span>{shows.length} {shows.length === 1 ? 'show' : 'shows'}</span></div><div className="poster-rail">{shows.map((show) => <Link className="show-card" to={`/shows/${show.id}`} key={show.id}><Image src={show.poster} alt={`${show.title} poster`} className="poster" /><div><strong>{show.title}</strong><small>{show.categories.slice(0, 2).join(' · ') || 'Show'}</small></div></Link>)}</div></section> }

function FilterBar({ catalogue, values, onChange }: { catalogue: Catalogue; values: { category: string; language: string; section: string }; onChange: (key: string, value: string) => void }) {
  const languages = [...new Set(catalogue.shows.flatMap((show) => show.seasons.flatMap((season) => season.episodes.flatMap((episode) => episode.languages.map((language) => language.code)))))].sort()
  return <div className="filters"><select value={values.category} onChange={(event) => onChange('category', event.target.value)}><option value="">All categories</option>{catalogue.categories.map((category) => <option value={category.key} key={category.key}>{category.title}</option>)}</select><select value={values.language} onChange={(event) => onChange('language', event.target.value)}><option value="">All languages</option>{languages.map((language) => <option value={language} key={language}>{language}</option>)}</select><select value={values.section} onChange={(event) => onChange('section', event.target.value)}><option value="">All sections</option>{catalogue.sections.map((section) => <option value={section.key} key={section.key}>{section.title}</option>)}</select></div>
}

function SearchPage({ catalogue }: { catalogue: Catalogue }) {
  const [params, setParams] = useSearchParams()
  const q = params.get('q') || ''; const category = params.get('category') || ''; const language = params.get('language') || ''; const section = params.get('section') || ''
  const [query, setQuery] = useState(q)
  const [loading, setLoading] = useState(false); const [error, setError] = useState(''); const [results, setResults] = useState<SearchItem[]>([])
  useEffect(() => { setQuery(q); setLoading(true); setError(''); publicApi.search({ q, category, language, section }).then((data) => setResults(data.items)).catch((reason) => setError(reason instanceof Error ? reason.message : 'Search failed.')).finally(() => setLoading(false)) }, [q, category, language, section])
  const update = (key: string, value: string) => { const next = new URLSearchParams(params); value ? next.set(key, value) : next.delete(key); setParams(next) }
  return <div className="browse-page"><div className="browse-heading"><div><span className="eyebrow">Browse</span><h1>{q ? `Results for “${q}”` : 'Find your next watch'}</h1><p>Search the published catalogue and narrow it by language, category, or section.</p></div><form className="search-large" onSubmit={(event) => { event.preventDefault(); update('q', query.trim()) }}><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by title, episode, category" /><button className="button dark">Search</button></form></div><FilterBar catalogue={catalogue} values={{ category, language, section }} onChange={update} />{loading ? <Loading tall /> : error ? <div className="state-screen compact"><h2>Search unavailable</h2><p>{error}</p></div> : results.length ? <div className="result-grid">{results.map((item) => <SearchCard item={item} key={item.show_id} />)}</div> : <EmptyState title={q || category || language || section ? 'No matches found' : 'Start exploring'} copy={q || category || language || section ? 'Try removing a filter or using a broader search.' : 'Search for a show, episode, or category to begin.'} />}</div>
}

function SearchCard({ item }: { item: SearchItem }) { return <Link className="result-card" to={`/shows/${item.show_id}`}><Image src={item.poster} alt={`${item.title} poster`} className="poster" /><div className="result-copy"><span className="eyebrow">{item.categories.join(' · ') || 'Show'}</span><h2>{item.title}</h2><p>{item.synopsis}</p>{item.episodes.length > 0 && <small>{item.episodes.length} matching episode{item.episodes.length === 1 ? '' : 's'} · {item.episodes.flatMap((episode) => episode.languages.map((language) => language.code)).filter((value, index, list) => list.indexOf(value) === index).join(', ')}</small>}</div></Link> }

function ShowDetail({ catalogue }: { catalogue: Catalogue }) {
  const { showId } = useParams(); const show = catalogue.shows.find((item) => item.id === showId)
  if (!show) return <EmptyState title="Show not found" copy="This show is not part of the current published catalogue." />
  return <div className="detail-page"><section className="detail-hero"><Image src={show.banner || show.poster} alt="" className="detail-backdrop" /><div className="detail-shade" /><div className="detail-heading"><Link className="back-link" to="/">← Back to catalogue</Link><span className="eyebrow">{show.categories.join(' · ') || 'Show'}</span><h1>{show.title}</h1><p>{show.synopsis}</p></div></section><div className="detail-body"><div className="detail-art"><Image src={show.poster} alt={`${show.title} poster`} className="poster" /></div><div className="detail-content"><div className="detail-meta"><span>{show.seasons.length} {show.seasons.length === 1 ? 'season' : 'seasons'}</span><span>{show.seasons.reduce((count, season) => count + season.episodes.length, 0)} episodes</span><span>{show.categories.join(' · ')}</span></div>{show.seasons.length ? show.seasons.map((season) => <SeasonList season={season} key={season.number} />) : <EmptyState title="Episodes coming soon" copy="This show has no published seasons yet." />}</div></div></div>
}

function SeasonList({ season }: { season: { number: number; title: string | null; episodes: Episode[] } }) { return <section className="season-list"><div className="season-title"><h2>{season.title || `Season ${season.number}`}</h2><span>{season.episodes.length} episodes</span></div><div className="episode-list">{season.episodes.map((episode) => <EpisodeCard episode={episode} key={episode.id} />)}</div></section> }

function EpisodeCard({ episode }: { episode: Episode }) {
  const [language, setLanguage] = useState(episode.languages[0]?.code || '')
  return <article className="episode-card"><Image src={episode.thumbnail} alt={`${episode.title} thumbnail`} className="thumbnail" /><div><h3>{episode.title}</h3><p>{episode.synopsis}</p><div className="episode-meta"><span>{episode.duration_seconds ? `${Math.floor(episode.duration_seconds / 60)} min` : 'Episode'}</span>{episode.languages.length > 1 ? <label className="language-choice"><span>Audio</span><select aria-label={`Language for ${episode.title}`} value={language} onChange={(event) => setLanguage(event.target.value)}>{episode.languages.map((option) => <option value={option.code} key={option.code}>{option.code}</option>)}</select></label> : <span>{episode.languages[0]?.code || 'Original'}</span>}</div></div></article>
}

export default function App() {
  const [catalogue, setCatalogue] = useState<Catalogue | null>(null); const [loading, setLoading] = useState(true); const [error, setError] = useState(false)
  const load = () => { setLoading(true); setError(false); publicApi.catalogue().then(setCatalogue).catch(() => setError(true)).finally(() => setLoading(false)) }
  useEffect(load, [])
  if (loading) return <Loading tall />
  if (error || !catalogue) return <ErrorState retry={load} />
  return <AppShell catalogue={catalogue} />
}
