# API Test Cases for the BibleGarden Client Application

> **Date:** 2026-02-19
> **Goal:** ensure regression testing of all endpoints used by the BibleGarden iOS application before API refactoring.
> **Base URL:** `https://bibleapi.space`
> **Authorization:** header `X-API-Key: <api_key>` (for all client endpoints)

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [GET /api/languages](#2-get-apilanguages)
3. [GET /api/translations](#3-get-apitranslations)
4. [GET /api/translations/{translation_code}/books](#4-get-apitranslationstranslation_codebooks)
5. [GET /api/excerpt_with_alignment](#5-get-apiexcerpt_with_alignment)
6. [GET /api/audio/{translation}/{voice}/{book}/{chapter}.mp3](#6-get-apiaudiotranslationvoicebookchaptermp3)
7. [Model Contracts (Schemas)](#7-model-contracts-schemas)

---

## 1. Authentication

All client endpoints are protected by an API key in the `X-API-Key` header.

### TC-AUTH-1: Request without API key -> 403

```
GET /api/languages
(without X-API-Key header)
```

**Expected result:**
- HTTP 403
- Body: `{"detail": "Invalid or missing API Key"}`

**Actual result (2026-02-19):** HTTP 403, `{"detail":"Invalid or missing API Key"}` ✅

### TC-AUTH-2: Request with invalid API key -> 403

```
GET /api/languages
X-API-Key: wrong-key
```

**Expected result:**
- HTTP 403
- Body: `{"detail": "Invalid or missing API Key"}`

**Actual result:** HTTP 403, `{"detail":"Invalid or missing API Key"}` ✅

### TC-AUTH-3: Request with valid API key -> 200

```
GET /api/languages
X-API-Key: <valid_key>
```

**Expected result:** HTTP 200, array of languages

**Actual result:** HTTP 200 ✅

---

## 2. GET /api/languages

The client calls this endpoint when:
- Opening the settings screen (`PageSetupView`)
- Opening the multilingual step configuration (`MultilingualConfigSheet`)

### TC-LANG-1: Retrieving the list of languages

```
GET /api/languages
X-API-Key: <key>
```

**Expected result:**
- HTTP 200
- Array of `LanguageModel` objects
- Each object contains **required fields**: `alias` (string), `name_en` (string), `name_national` (string)

**Actual response:**
```json
[
  {"alias": "en", "name_en": "English", "name_national": "English"},
  {"alias": "ru", "name_en": "Russian", "name_national": "Русский"},
  {"alias": "uk", "name_en": "Ukrainian", "name_national": "Українська"}
]
```

### TC-LANG-2: Presence of supported languages

**Expected result:** the response contains languages with alias `"ru"`, `"en"`, `"uk"` (the app uses these three).

**Critical fields used by the client:**
| Field | Where used |
|-------|------------|
| `alias` | key for filtering translations, saved in `selectedLanguage`, `languageCode` |
| `name_national` | displayed in the language selection list |
| `name_en` | displayed as description in the list |

---

## 3. GET /api/translations

The client calls this endpoint in two modes:
- With `language=""` — get ALL translations (for caching in `SettingsManager.cachedAllTranslations`)
- With `language=<code>` — get translations for a specific language (in `MultilingualConfigSheet`)

### TC-TRANS-1: All translations (language empty)

```
GET /api/translations?language=
X-API-Key: <key>
```

**Expected result:**
- HTTP 200
- Array of `TranslationModel`
- Contains translations for all languages

**Actual result:** 8 active translations (ru: 2, en: 3, uk: 2) ✅

### TC-TRANS-2: Filter by language (language=ru)

```
GET /api/translations?language=ru
X-API-Key: <key>
```

**Expected result:**
- HTTP 200
- Array contains only translations with `language == "ru"`

**Actual result:** 2 translations (SYNO code=1, BTI code=11) ✅

### TC-TRANS-3: Filter by language (language=en)

```
GET /api/translations?language=en
X-API-Key: <key>
```

**Expected result:** translations with `language == "en"`

**Actual result:** 3 translations (BSB code=16, WEBUS code=17, WEBBE code=779) ✅

### TC-TRANS-4: Filter by language (language=uk)

```
GET /api/translations?language=uk
X-API-Key: <key>
```

**Expected result:** translations with `language == "uk"`

**Actual result:** 2 translations (UBH code=20, NPU code=21) ✅

### TC-TRANS-5: Default only_active=1

The client does not pass `only_active`; the expected default behavior is to return only active translations.

```
GET /api/translations?language=
```

**Expected result:** all returned translations have `active == true`

**Actual result:** 8 translations, all `active=true` ✅

### TC-TRANS-6: TranslationModel Structure

Each object in the array must contain:

| Field | Type | Required | Used by client |
|-------|------|----------|----------------|
| `code` | integer | Yes | translation key, passed to excerpt_with_alignment and translation_books |
| `alias` | string | Yes | — |
| `name` | string | Yes | displayed in selection list, saved as `translationName` |
| `description` | string \| null | Yes | displayed as subtitle, can be null |
| `language` | string | Yes | client-side filtering |
| `active` | boolean | Yes | — |
| `voices` | array of VoiceModel | Yes | list of voices for narrator selection |

### TC-TRANS-7: VoiceModel Structure inside TranslationModel

Each voice inside `voices` must contain:

| Field | Type | Required | Used by client |
|-------|------|----------|----------------|
| `code` | integer | Yes | voice key, passed to excerpt_with_alignment and translation_books |
| `alias` | string | Yes | — |
| `name` | string | Yes | displayed as narrator name |
| `description` | string \| null | No | displayed as narrator description |
| `is_music` | boolean | Yes | affects smooth pause (0.3 sec fade) when pausing audio |
| `active` | boolean | Yes | — |

**Example actual response (SYNO, Bondarenko voice):**
```json
{
  "code": 1,
  "alias": "bondarenko",
  "name": "Aleksandr Bondarenko",
  "description": "Text narrated by Aleksandr Viktorovich Bondarenko...",
  "is_music": true,
  "active": true,
  "anomalies_count": 481,
  "anomalies_open_count": 0
}
```

> **Note:** the fields `anomalies_count`, `anomalies_open_count` are not used by the client but must be present for schema compatibility.

---

## 4. GET /api/translations/{translation_code}/books

The client calls this endpoint to display the list of books and chapters (`PageSelectView`, `SettingsManager.getTranslationBooks()`).

### TC-BOOKS-1: Books with voice_code specified

```
GET /api/translations/1/books?voice_code=1
X-API-Key: <key>
```

**Expected result:**
- HTTP 200
- Array of 66 `TranslationBookModel` objects (full Bible)

**Actual result:** 66 books ✅

### TC-BOOKS-2: Books without voice_code

```
GET /api/translations/1/books
X-API-Key: <key>
```

**Expected result:**
- HTTP 200
- 66 books (voice_code is optional)

**Actual result:** 66 books ✅

> **Important:** without voice_code, the fields `anomalies_count` and `anomalies_open_count` may be `null`.

### TC-BOOKS-3: Books for English translation

```
GET /api/translations/16/books?voice_code=151
X-API-Key: <key>
```

**Expected result:** 66 books for BSB

**Actual result:** 66 books, 9 of them have non-empty `chapters_without_audio` ✅

### TC-BOOKS-4: Books for Ukrainian translation

```
GET /api/translations/20/books?voice_code=130
X-API-Key: <key>
```

**Expected result:** 66 books for UBH

**Actual result:** 66 books ✅

### TC-BOOKS-5: TranslationBookModel Structure

| Field | Type | Required | Used by client |
|-------|------|----------|----------------|
| `code` | integer | Yes | identifier |
| `book_number` | integer | Yes | book position (1-66), used for OT/NT separation (<39 = OT, >=39 = NT), navigation |
| `name` | string | Yes | book name, displayed in selection list and reading header |
| `alias` | string | Yes | short alias (e.g. "gen", "jhn"), used for forming excerpt requests and progress tracking |
| `chapters_count` | integer | Yes | number of chapters — forms chapter grid, used in reading progress |
| `chapters_without_audio` | array of int \| null | No | chapter numbers without audio — used for displaying mute icon |
| `chapters_without_text` | array of int \| null | No | chapter numbers without text — used for disabled state of chapter button |
| `anomalies_count` | integer \| null | No | not used by client |
| `anomalies_open_count` | integer \| null | No | not used by client |

**Example actual response (Genesis):**
```json
{
  "code": 7587,
  "book_number": 1,
  "name": "Genesis",
  "alias": "gen",
  "chapters_count": 50,
  "anomalies_count": 37,
  "anomalies_open_count": 0,
  "chapters_without_audio": [],
  "chapters_without_text": []
}
```

### TC-BOOKS-6: Book Order

**Expected result:** books are sorted by `book_number` from 1 (Genesis) to 66 (Revelation).

### TC-BOOKS-7: Alias Consistency Across Translations

**Expected result:** the same book has the same `alias` across different translations (e.g. the Gospel of John = "jhn" in SYNO, BSB, UBH). This is critical because the client forms excerpt requests using the alias.

---

## 5. GET /api/excerpt_with_alignment

**The main application endpoint.** The client calls it for:
- Loading text and audio alignment during reading (`PageReadView`)
- Loading multilingual steps (`PageMultilingualReadView`)
- Text preview in settings (`PageSetupView.loadExampleText()`)
- Voice preview (`MultilingualConfigSheet.toggleVoicePreview()`)

### TC-EXCERPT-1: Full chapter request (main use case)

```
GET /api/excerpt_with_alignment?translation=1&excerpt=jhn+1&voice=1
X-API-Key: <key>
```

**Expected result:**
- HTTP 200
- `is_single_chapter: true` (single chapter in excerpt)
- `parts`: array with 1 element
- `parts[0].verses`: 51 verses (John 1)
- `parts[0].audio_link`: non-empty URL string pointing to .mp3
- All verses have `begin > 0` and `end > begin`

**Actual result:**
- `is_single_chapter: true`
- 51 verses, first: begin=12.41, end=22.69
- audio_link: `https://api.bibleapi.space/api/audio/syn/bondarenko/43/01.mp3` ✅

### TC-EXCERPT-2: Verse range request

```
GET /api/excerpt_with_alignment?translation=1&excerpt=jhn+1:1-3&voice=1
X-API-Key: <key>
```

**Expected result:**
- HTTP 200
- `parts[0].verses`: exactly 3 verses
- `is_single_chapter: false` (verse range)

**Actual result:** 3 verses, `is_single_chapter: false` ✅

> **Important for client:** when `is_single_chapter == true`, `periodFrom=0, periodTo=0` — audio plays from the beginning of the file. When `false` — `periodFrom` and `periodTo` are taken from `begin`/`end` of the first/last verses.

### TC-EXCERPT-3: Request without voice (voice=0) — text preview

```
GET /api/excerpt_with_alignment?translation=1&excerpt=jhn+1:1-3&voice=0
X-API-Key: <key>
```

**Expected result:**
- HTTP 200
- `parts[0].audio_link`: empty string `""`
- `parts[0].verses[*].begin = 0.0`, `end = 0.0` (no alignment)

**Actual result:** audio_link=`""`, begin=0.0, end=0.0 ✅

### TC-EXCERPT-4: Navigation prev/next for the first chapter of the Bible

```
GET /api/excerpt_with_alignment?translation=1&excerpt=gen+1&voice=1
```

**Expected result:**
- `parts[0].prev_excerpt: ""` (no previous)
- `parts[0].next_excerpt: "gen 2"`

**Actual result:** prev_excerpt=`""`, next_excerpt=`"gen 2"` ✅

### TC-EXCERPT-5: Navigation prev/next for the last chapter of the Bible

```
GET /api/excerpt_with_alignment?translation=1&excerpt=rev+22&voice=1
```

**Expected result:**
- `parts[0].prev_excerpt: "rev 21"`
- `parts[0].next_excerpt: ""` (no next)

**Actual result:** prev_excerpt=`"rev 21"`, next_excerpt=`""` ✅

### TC-EXCERPT-6: Navigation prev/next for a middle chapter

```
GET /api/excerpt_with_alignment?translation=1&excerpt=jhn+1&voice=1
```

**Expected result:**
- `prev_excerpt`: `"luk 24"` (last chapter of previous book)
- `next_excerpt`: `"jhn 2"`

**Actual result:** prev_excerpt=`"luk 24"`, next_excerpt=`"jhn 2"` ✅

### TC-EXCERPT-7: English translation (BSB)

```
GET /api/excerpt_with_alignment?translation=16&excerpt=jhn+1:1-3&voice=151
```

**Expected result:**
- HTTP 200
- Text in English
- Audio link to BSB audio

**Actual result:**
- v1: "In the beginning was the Word...", begin=5.19, end=10.2
- audio_link: `https://api.bibleapi.space/api/audio/bsb/bsb_souer/43/01.mp3` ✅

### TC-EXCERPT-8: Ukrainian translation (UBH)

```
GET /api/excerpt_with_alignment?translation=20&excerpt=jhn+1:1-3&voice=130
```

**Expected result:**
- HTTP 200
- Text in Ukrainian
- book.name in Ukrainian

**Actual result:**
- v1: "Spokonviku bulo Slovo...", begin=19.06, end=28.99
- book.name: "Yevanheliya vid Yoana" ✅

### TC-EXCERPT-9: Invalid excerpt -> 422

```
GET /api/excerpt_with_alignment?translation=1&excerpt=invalid_book+999&voice=1
```

**Expected result:**
- HTTP 422
- Body: `{"detail": "<error description>"}`

**Actual result:** `{"detail":"Book with alias 'book' not found for translation 1."}` ✅

> **Important for client:** the 422 response has type `SimpleErrorResponse` with a `detail` field (string), not `HTTPValidationError`.

### TC-EXCERPT-10: ExcerptWithAlignmentModel Structure

| Field | Type | Required | Used by client |
|-------|------|----------|----------------|
| `title` | string | Yes | — (not used directly) |
| `is_single_chapter` | boolean | Yes | determines the periodFrom/periodTo mode for audio |
| `parts` | array of PartsWithAlignmentModel | Yes | main data |

### TC-EXCERPT-11: PartsWithAlignmentModel Structure

| Field | Type | Required | Used by client |
|-------|------|----------|----------------|
| `book` | BookInfoModel | Yes | `book.name` -> title, `book.number` -> navigation, `book.alias` — |
| `chapter_number` | integer | Yes | subtitle "Chapter N" |
| `audio_link` | string | Yes | audio file URL (empty string if no audio/voice=0) |
| `prev_excerpt` | string | Yes | "previous chapter" navigation (empty string if none) |
| `next_excerpt` | string | Yes | "next chapter" navigation (empty string if none) |
| `verses` | array of VerseWithAlignmentModel | Yes | text and timestamps |
| `notes` | array of NoteModel | Yes | footnotes |
| `titles` | array of TitleModel | Yes | section titles |

### TC-EXCERPT-12: BookInfoModel Structure

| Field | Type | Required | Used by client |
|-------|------|----------|----------------|
| `code` | integer | Yes | — |
| `number` | integer | Yes | `bookDigitCode`, `currentBookId` |
| `alias` | string | Yes | — |
| `name` | string | Yes | `currentExcerptTitle` |
| `chapters_count` | integer | Yes | — |

### TC-EXCERPT-13: VerseWithAlignmentModel Structure

| Field | Type | Required | Used by client |
|-------|------|----------|----------------|
| `code` | integer | Yes | link with notes and titles |
| `number` | integer | Yes | verse number, display, scroll |
| `join` | integer | Yes | verse sorting (number+join) |
| `text` | string | Yes | plain text for audio display |
| `html` | string | Yes | HTML markup for text display |
| `begin` | number | Yes | verse start time in audio file (seconds) |
| `end` | number | Yes | verse end time in audio file (seconds) |
| `start_paragraph` | boolean | Yes | paragraph start — used for auto-pause by paragraphs and for grouping in multilingual mode |

### TC-EXCERPT-14: NoteModel Structure

| Field | Type | Required | Used by client |
|-------|------|----------|----------------|
| `code` | integer | Yes | identifier |
| `number` | integer | Yes | — |
| `text` | string | Yes | footnote text |
| `verse_code` | integer \| null | No | link to verse.code — if set, the note is attached to a verse |
| `title_code` | integer \| null | No | link to title.code — if set, the note is attached to a title |
| `position_text` | integer | Yes | position in plain text |
| `position_html` | integer | Yes | position in HTML |

### TC-EXCERPT-15: TitleModel Structure

| Field | Type | Required | Used by client |
|-------|------|----------|----------------|
| `code` | integer | Yes | identifier, link to NoteModel.title_code |
| `text` | string | Yes | title text |
| `before_verse_code` | integer \| null | No | verse.code — title is shown before this verse |
| `metadata` | string \| null | No | title metadata |
| `reference` | string \| null | No | reference to related excerpts |
| `subtitle` | boolean | No (default false) | whether it is a subtitle |
| `position_text` | integer \| null | No | position in text |
| `position_html` | integer \| null | No | position in HTML |

### TC-EXCERPT-16: Titles and notes are linked to verses

```
GET /api/excerpt_with_alignment?translation=1&excerpt=gen+1&voice=1
```

**Expected result:**
- Titles have `before_verse_code` matching one of `verses[*].code`
- Notes have `verse_code` matching one of `verses[*].code`

**Actual result:** 2 titles (before verses 1 and 26), 15 notes — all linked to verses via verse_code ✅

### TC-EXCERPT-17: Monotonicity of begin/end

**Expected result:** for each verse `end > begin`, and verses are in chronological audio order (begin[i+1] >= end[i], considering join-based sorting).

**Actual result for jhn 1:** first begin=12.41, last end=563.92, all end > begin ✅

### TC-EXCERPT-18: start_paragraph is present and distributed

```
GET /api/excerpt_with_alignment?translation=1&excerpt=gen+1&voice=1
```

**Expected result:**
- The first verse has `start_paragraph: true`
- Not all verses have `start_paragraph: true` (there is separation)

**Actual result:** 8 out of 31 verses have `start_paragraph: true` ✅

### TC-EXCERPT-19: Titles with reference (for BSB)

```
GET /api/excerpt_with_alignment?translation=16&excerpt=mat+1&voice=151
```

**Expected result:**
- Titles may contain `reference` (link to parallel excerpts)

**Actual result:** title "The Genealogy of Jesus" with reference="(Ruth 4:18-22; Luke 3:23-38)" ✅

---

## 6. GET /api/audio/{translation}/{voice}/{book}/{chapter}.mp3

The client uses the URL from the `audio_link` field in the excerpt_with_alignment response, adding the `api_key` query parameter.

### TC-AUDIO-1: Fetching an audio file (GET)

```
GET /api/audio/syn/bondarenko/43/01.mp3?api_key=<key>
Host: api.bibleapi.space
```

**Expected result:**
- HTTP 200
- Content-Type: `audio/mpeg`
- Content-Length: > 0
- Accept-Ranges: bytes

**Actual result:**
- HTTP 200, Content-Type: audio/mpeg, Content-Length: 2257648
- Accept-Ranges: bytes ✅

### TC-AUDIO-2: Range request (streaming for iOS)

```
GET /api/audio/syn/bondarenko/43/01.mp3?api_key=<key>
Host: api.bibleapi.space
Range: bytes=0-1023
```

**Expected result:**
- HTTP 206 (Partial Content)
- Content-Range: `bytes 0-1023/<total>`
- Content-Length: 1024

**Actual result:**
- HTTP 206, Content-Range: bytes 0-1023/2257648, Content-Length: 1024 ✅

> **Critical:** iOS AVPlayer uses HTTP Range requests for streaming. Without 206 support, audio will not work.

### TC-AUDIO-3: HEAD request

```
HEAD /api/audio/syn/bondarenko/43/01.mp3?api_key=<key>
Host: api.bibleapi.space
```

**Expected result:**
- HTTP 200
- Same headers: Content-Type, Content-Length, Accept-Ranges

**Actual result:** HTTP 200, Content-Type: audio/mpeg ✅

### TC-AUDIO-4: CORS headers

**Expected result:**
- `Access-Control-Allow-Origin: *`

**Actual result:** `access-control-allow-origin: *` ✅

### TC-AUDIO-5: Audio for English translation

```
GET /api/audio/bsb/bsb_souer/43/01.mp3?api_key=<key>
Host: api.bibleapi.space
```

**Expected result:** HTTP 200, Content-Type: audio/mpeg

### TC-AUDIO-6: Audio for Ukrainian translation

```
GET /api/audio/ubh/kozlov_uk/43/01.mp3?api_key=<key>
Host: api.bibleapi.space
```

**Expected result:** HTTP 200, Content-Type: audio/mpeg

### TC-AUDIO-7: Authorization via api_key query parameter

**Expected result:** the audio endpoint accepts the API key via the `api_key` query parameter (not via header). The client passes the key this way.

### TC-AUDIO-8: audio_link from excerpt_with_alignment is correct

**Expected result:** the URL from the `audio_link` field of the excerpt_with_alignment response (with `?api_key=<key>` appended) is accessible and returns audio/mpeg.

---

## 7. Model Contracts (Schemas)

### TC-SCHEMA-1: Nullable fields do not break the client

The following fields can be `null` and the client must handle this (and does):

| Model | Field | Context |
|-------|-------|---------|
| `TranslationModel` | `description` | translation description |
| `VoiceModel` | `description` | narrator description |
| `TitleModel` | `before_verse_code` | — |
| `TitleModel` | `metadata` | — |
| `TitleModel` | `reference` | — |
| `TitleModel` | `subtitle` | default false |
| `TitleModel` | `position_text` | — |
| `TitleModel` | `position_html` | — |
| `NoteModel` | `verse_code` | can be null |
| `NoteModel` | `title_code` | can be null |
| `TranslationBookModel` | `anomalies_count` | null without voice_code |
| `TranslationBookModel` | `anomalies_open_count` | null without voice_code |
| `TranslationBookModel` | `chapters_without_audio` | can be null |
| `TranslationBookModel` | `chapters_without_text` | can be null |

### TC-SCHEMA-2: Empty arrays instead of null

**Expected result:**
- `parts[0].verses`: empty array `[]` if no verses (not null)
- `parts[0].notes`: empty array `[]` if no footnotes (not null)
- `parts[0].titles`: empty array `[]` if no titles (not null)
- `translation.voices`: empty array `[]` if no voices (not null)

### TC-SCHEMA-3: Empty strings for missing data

**Expected result:**
- `prev_excerpt`: `""` (empty string) when there is no previous chapter (not null)
- `next_excerpt`: `""` (empty string) when there is no next chapter (not null)
- `audio_link`: `""` (empty string) when there is no audio (not null)

---

## Endpoint Summary Table

| # | Method | Endpoint | Where used in client | Criticality |
|---|--------|----------|---------------------|-------------|
| 1 | GET | `/api/languages` | PageSetupView, MultilingualConfigSheet | High |
| 2 | GET | `/api/translations?language=` | SettingsManager (all translations cache) | High |
| 3 | GET | `/api/translations?language=<code>` | MultilingualConfigSheet | High |
| 4 | GET | `/api/translations/{code}/books?voice_code=` | PageSelectView, SettingsManager | High |
| 5 | GET | `/api/excerpt_with_alignment` | PageReadView, PageMultilingualReadView, PageSetupView, MultilingualConfigSheet, PageMultilingualConfigView | **Critical** |
| 6 | GET | `/api/audio/...mp3?api_key=` | AVPlayer (streaming) | **Critical** |

### Endpoints present in openapi.yaml but NOT used by the client:

| Endpoint | Note |
|----------|------|
| `GET /api/chapter_with_alignment` | Not used (present in spec, but client uses excerpt_with_alignment) |
| `GET /api/translation_info` | Commented out in PageSetupView code |
| `POST /api/auth/login` | Admin, not client |
| `GET /api/check_translation` | Not used by client |
| `GET /api/check_voice` | Not used by client |
| `POST /api/cache/clear` | Admin |
| `PUT /api/translations/{code}` | Admin |
| `PUT /api/voices/{code}` | Admin |
| `GET /api/voices/{code}/anomalies` | Admin |
| `POST /api/voices/anomalies` | Admin |
| `PATCH /api/voices/anomalies/{code}/status` | Admin |
| `POST /api/voices/manual-fixes` | Admin |

---

## Testing Parameters

### Main translation + voice combinations used by the app by default:

| Language | Translation (code) | Alias | Voice (code) | Voice alias |
|----------|-------------------|-------|--------------|-------------|
| ru | 1 | syn | 1 | bondarenko |
| ru | 1 | syn | 2 | prudovsky |
| ru | 11 | bti | 123 | prozorovsky |
| en | 16 | bsb | 150 | bsb_david |
| en | 16 | bsb | 151 | bsb_souer |
| en | 17 | webus | 152 | winfred_henson |
| uk | 20 | ubh | 130 | kozlov_uk |
| uk | 21 | npu | 131 | npu_uk |
| en | 779 | webbe | 129 | web_british |

### Key excerpt formats:

| Format | Example | Description |
|--------|---------|-------------|
| `<alias> <chapter>` | `jhn 1` | Full chapter |
| `<alias> <ch>:<v1>-<v2>` | `jhn 1:1-3` | Verse range |

### Boundary values for testing:

| Case | Excerpt |
|------|---------|
| First chapter of the Bible | `gen 1` |
| Last chapter | `rev 22` |
| Short chapter (Ps 117 = 2 verses) | `psa 117` |
| Long chapter (Ps 119 = 176 verses) | `psa 119` |
| Chapter with many footnotes | `gen 1` |
| Chapter with titles | `mat 1` |
