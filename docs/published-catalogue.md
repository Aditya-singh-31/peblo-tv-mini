# Published Catalogue

The published catalogue is a viewer-only JSON document. It contains no database records, admin status fields, timestamps, storage keys, upload metadata, or internal validation details.

## Contract

```json
{
  "schema_version": 1,
  "catalogue_version": "2026-09-05T12:00:00Z",
  "featured_hero": {
    "show_id": "show-opaque-id",
    "title": "Example Show",
    "synopsis": "A short synopsis.",
    "poster": "https://cdn.example.test/poster.jpg",
    "banner": "https://cdn.example.test/banner.jpg"
  },
  "sections": [
    {
      "key": "featured",
      "title": "Featured",
      "show_ids": ["show-opaque-id"]
    }
  ],
  "categories": [
    {
      "key": "documentary",
      "title": "Documentary",
      "show_ids": ["show-opaque-id"]
    }
  ],
  "shows": [
    {
      "id": "show-opaque-id",
      "title": "Example Show",
      "synopsis": "A short synopsis.",
      "categories": ["documentary"],
      "poster": "https://cdn.example.test/poster.jpg",
      "banner": "https://cdn.example.test/banner.jpg",
      "thumbnail": "https://cdn.example.test/thumb.jpg",
      "seasons": [
        {
          "number": 1,
          "title": "Season One",
          "episodes": [
            {
              "id": "episode-opaque-id",
              "title": "Episode 1",
              "synopsis": "An episode synopsis.",
              "duration_seconds": 1800,
              "thumbnail": "https://cdn.example.test/episode-thumb.jpg",
              "languages": [{"code": "en"}, {"code": "fr"}]
            }
          ]
        }
      ]
    }
  ]
}
```

## Rules

- Only shows with `status == "published"` are emitted.
- Only episodes with `status == "published"` are emitted.
- Season 0 is trailer content and is never emitted in `shows[].seasons`.
- Episodes with the same `content_group` are one logical episode. Their language variants are merged into one episode and sorted by language code.
- A language variant contributes its language code to `languages`; the catalogue does not expose the episode database rows or internal IDs.
- `poster`, `banner`, and `thumbnail` are public URLs. Storage keys, dimensions, MIME types, file sizes, and upload notes are omitted.
- `sections[].show_ids` and `categories[].show_ids` reference entries in `shows`.
- `featured_hero` is `null` when there are no published shows. Otherwise it is selected deterministically: the first published show in the first non-empty section, then the first published show overall.
- All collections are sorted deterministically: sections and categories by key, shows by title then ID, seasons by number, episodes by content group then title then ID, and languages by code.
- `show-opaque-id` and `episode-opaque-id` are public catalogue identifiers. They are not required to be database primary keys.

## Workspace catalogue state

The challenge seed data has been populated with published and draft content. The example above shows the expected contract; actual catalogue content varies based on what is marked `published` in the database.
