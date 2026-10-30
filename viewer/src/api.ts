
export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export interface Language {
  code: string
}

export interface Episode {
  id: string
  title: string
  synopsis: string | null
  duration_seconds: number | null
  thumbnail: string | null
  languages: Language[]
}

export interface Season {
  number: number
  title: string | null
  episodes: Episode[]
}

export interface Show {
  id: string
  title: string
  synopsis: string | null
  categories: string[]
  poster: string | null
  banner: string | null
  thumbnail: string | null
  seasons: Season[]
}

export interface Section {
  key: string
  title: string
  show_ids: string[]
}

export interface Category {
  key: string
  title: string
  show_ids: string[]
}

export interface Catalogue {
  schema_version: number
  catalogue_version: string
  featured_hero: {
    show_id: string
    title: string
    synopsis: string | null
    poster: string | null
    banner: string | null
  } | null
  sections: Section[]
  categories: Category[]
  shows: Show[]
}

export interface SearchEpisode extends Episode {
  season_number: number
  season_title: string | null
}

export interface SearchItem {
  show_id: string
  title: string
  synopsis: string | null
  categories: string[]
  poster: string | null
  banner: string | null
  thumbnail: string | null
  episodes: SearchEpisode[]
}

export interface SearchResponse {
  items: SearchItem[]
  total: number
}

// Sample catalogue for the public PEBLO TV portfolio demo.
const sampleCatalogue: Catalogue = {
  schema_version: 1,
  catalogue_version: 'portfolio-demo-v1',

  featured_hero: {
    show_id: 'wild-world',
    title: 'Wild World',
    synopsis: 'Discover breathtaking landscapes, extraordinary wildlife and the wonders of our natural world.',
    poster: 'https://images.unsplash.com/photo-1472396961693-142e6e269027?w=700',
    banner: 'https://images.unsplash.com/photo-1472396961693-142e6e269027?w=1800'
  },

  categories: [
    { key: 'documentary', title: 'Documentary', show_ids: ['wild-world', 'planet-earth'] },
    { key: 'adventure', title: 'Adventure', show_ids: ['wild-world', 'the-journey'] },
    { key: 'lifestyle', title: 'Lifestyle', show_ids: ['food-stories'] },
    { key: 'science', title: 'Science', show_ids: ['planet-earth'] }
  ],

  sections: [
    { key: 'featured', title: 'Featured Shows', show_ids: ['wild-world', 'the-journey'] },
    { key: 'nature', title: 'Nature & Discovery', show_ids: ['planet-earth', 'wild-world'] },
    { key: 'popular', title: 'Popular on PEBLO', show_ids: ['food-stories', 'the-journey'] }
  ],

  shows: [
    {
      id: 'wild-world',
      title: 'Wild World',
      synopsis: 'Explore the beauty of nature, from majestic wildlife to the most remote landscapes on Earth.',
      categories: ['Documentary', 'Adventure'],
      poster: 'https://images.unsplash.com/photo-1472396961693-142e6e269027?w=700',
      banner: 'https://images.unsplash.com/photo-1472396961693-142e6e269027?w=1800',
      thumbnail: 'https://images.unsplash.com/photo-1472396961693-142e6e269027?w=700',
      seasons: [
        {
          number: 1,
          title: 'Into the Wild',
          episodes: [
            {
              id: 'wild-ep-1',
              title: 'The Great Wilderness',
              synopsis: 'Journey through untouched forests and discover the animals that call them home.',
              duration_seconds: 1500,
              thumbnail: 'https://images.unsplash.com/photo-1448375240586-882707db888b?w=700',
              languages: [{ code: 'EN' }, { code: 'HI' }]
            },
            {
              id: 'wild-ep-2',
              title: 'Life in the Mountains',
              synopsis: 'Discover the incredible creatures surviving in the highest mountain ranges.',
              duration_seconds: 1320,
              thumbnail: 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=700',
              languages: [{ code: 'EN' }]
            }
          ]
        }
      ]
    },

    {
      id: 'planet-earth',
      title: 'Planet Earth',
      synopsis: 'A fascinating journey through our planet, its ecosystems and the science behind life.',
      categories: ['Documentary', 'Science'],
      poster: 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=700',
      banner: 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=1800',
      thumbnail: 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=700',
      seasons: [
        {
          number: 1,
          title: 'Our Living Planet',
          episodes: [
            {
              id: 'earth-ep-1',
              title: 'The Green Planet',
              synopsis: 'Explore the forests that sustain life across the world.',
              duration_seconds: 1800,
              thumbnail: 'https://images.unsplash.com/photo-1448375240586-882707db888b?w=700',
              languages: [{ code: 'EN' }, { code: 'HI' }]
            }
          ]
        }
      ]
    },

    {
      id: 'the-journey',
      title: 'The Journey',
      synopsis: 'Travel beyond familiar places and experience unforgettable destinations.',
      categories: ['Adventure', 'Travel'],
      poster: 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=700',
      banner: 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1800',
      thumbnail: 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=700',
      seasons: [
        {
          number: 1,
          title: 'Beyond the Horizon',
          episodes: [
            {
              id: 'journey-ep-1',
              title: 'Into the Mountains',
              synopsis: 'An unforgettable adventure across beautiful mountain landscapes.',
              duration_seconds: 1600,
              thumbnail: 'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?w=700',
              languages: [{ code: 'EN' }]
            }
          ]
        }
      ]
    },

    {
      id: 'food-stories',
      title: 'Food Stories',
      synopsis: 'Discover delicious food, culinary traditions and stories from around the world.',
      categories: ['Lifestyle', 'Food'],
      poster: 'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=700',
      banner: 'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=1800',
      thumbnail: 'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=700',
      seasons: [
        {
          number: 1,
          title: 'Taste the World',
          episodes: [
            {
              id: 'food-ep-1',
              title: 'A World of Flavours',
              synopsis: 'Explore delicious dishes and food cultures from different countries.',
              duration_seconds: 1200,
              thumbnail: 'https://images.unsplash.com/photo-1547592180-85f173990554?w=700',
              languages: [{ code: 'EN' }, { code: 'HI' }]
            }
          ]
        }
      ]
    }
  ]
}

// Convert sample shows into search results.
function getSearchItems(): SearchItem[] {
  return sampleCatalogue.shows.map((show) => ({
    show_id: show.id,
    title: show.title,
    synopsis: show.synopsis,
    categories: show.categories,
    poster: show.poster,
    banner: show.banner,
    thumbnail: show.thumbnail,
    episodes: show.seasons.flatMap((season) =>
      season.episodes.map((episode) => ({
        ...episode,
        season_number: season.number,
        season_title: season.title
      }))
    )
  }))
}

export async function publicFetch<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`)
  const text = await response.text()
  const payload = text ? JSON.parse(text) : null

  if (!response.ok) {
    throw new Error(
      typeof payload?.detail === 'string'
        ? payload.detail
        : 'The catalogue could not be loaded.'
    )
  }

  return payload as T
}

// Public Viewer uses local sample data, not the backend.
export const publicApi = {
  catalogue: async (): Promise<Catalogue> => sampleCatalogue,

  search: async (params: {
    q?: string
    category?: string
    language?: string
    section?: string
  }): Promise<SearchResponse> => {
    const q = (params.q || '').toLowerCase().trim()

    let items = getSearchItems()

    if (q) {
      items = items.filter((item) =>
        [
          item.title,
          item.synopsis || '',
          ...item.categories,
          ...item.episodes.map((episode) => episode.title),
          ...item.episodes.map((episode) => episode.synopsis || '')
        ]
          .join(' ')
          .toLowerCase()
          .includes(q)
      )
    }

    if (params.category) {
      const category = sampleCatalogue.categories.find(
        (item) => item.key === params.category || item.title.toLowerCase() === params.category!.toLowerCase()
      )

      if (category) {
        items = items.filter((item) =>
          category.show_ids.includes(item.show_id)
        )
      }
    }

    if (params.language) {
      items = items.filter((item) =>
        item.episodes.some((episode) =>
          episode.languages.some(
            (language) =>
              language.code.toLowerCase() === params.language!.toLowerCase()
          )
        )
      )
    }

    if (params.section) {
      const section = sampleCatalogue.sections.find(
        (item) => item.key === params.section
      )

      if (section) {
        items = items.filter((item) =>
          section.show_ids.includes(item.show_id)
        )
      }
    }

    return {
      items,
      total: items.length
    }
  }
}
