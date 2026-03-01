# Тест-кейсы API Bible для клиентского приложения BibleGarden

> **Дата:** 2026-02-19
> **Цель:** обеспечить регрессионную проверку всех эндпоинтов, используемых iOS-приложением BibleGarden, перед рефакторингом API.
> **Base URL:** `https://bibleapi.space`
> **Авторизация:** заголовок `X-API-Key: <api_key>` (для всех клиентских эндпоинтов)

---

## Оглавление

1. [Аутентификация](#1-аутентификация)
2. [GET /api/languages](#2-get-apilanguages)
3. [GET /api/translations](#3-get-apitranslations)
4. [GET /api/translations/{translation_code}/books](#4-get-apitranslationstranslation_codebooks)
5. [GET /api/excerpt_with_alignment](#5-get-apiexcerpt_with_alignment)
6. [GET /api/audio/{translation}/{voice}/{book}/{chapter}.mp3](#6-get-apiaudiotranslationvoicebookchaptermp3)
7. [Контракты моделей (схемы)](#7-контракты-моделей-схемы)

---

## 1. Аутентификация

Все клиентские эндпоинты защищены API-ключом в заголовке `X-API-Key`.

### TC-AUTH-1: Запрос без API-ключа → 403

```
GET /api/languages
(без заголовка X-API-Key)
```

**Ожидаемый результат:**
- HTTP 403
- Тело: `{"detail": "Invalid or missing API Key"}`

**Фактический результат (2026-02-19):** HTTP 403, `{"detail":"Invalid or missing API Key"}` ✅

### TC-AUTH-2: Запрос с неверным API-ключом → 403

```
GET /api/languages
X-API-Key: wrong-key
```

**Ожидаемый результат:**
- HTTP 403
- Тело: `{"detail": "Invalid or missing API Key"}`

**Фактический результат:** HTTP 403, `{"detail":"Invalid or missing API Key"}` ✅

### TC-AUTH-3: Запрос с корректным API-ключом → 200

```
GET /api/languages
X-API-Key: <valid_key>
```

**Ожидаемый результат:** HTTP 200, массив языков

**Фактический результат:** HTTP 200 ✅

---

## 2. GET /api/languages

Клиент вызывает этот эндпоинт при:
- Открытии экрана настроек (`PageSetupView`)
- Открытии конфигурации мультиязычного шага (`MultilingualConfigSheet`)

### TC-LANG-1: Получение списка языков

```
GET /api/languages
X-API-Key: <key>
```

**Ожидаемый результат:**
- HTTP 200
- Массив объектов `LanguageModel`
- Каждый объект содержит **обязательные поля**: `alias` (string), `name_en` (string), `name_national` (string)

**Фактический ответ:**
```json
[
  {"alias": "en", "name_en": "English", "name_national": "English"},
  {"alias": "ru", "name_en": "Russian", "name_national": "Русский"},
  {"alias": "uk", "name_en": "Ukrainian", "name_national": "Українська"}
]
```

### TC-LANG-2: Наличие поддерживаемых языков

**Ожидаемый результат:** ответ содержит языки с alias `"ru"`, `"en"`, `"uk"` (приложение использует эти три).

**Критичные поля, используемые клиентом:**
| Поле | Где используется |
|------|------------------|
| `alias` | ключ для фильтрации переводов, сохраняется в `selectedLanguage`, `languageCode` |
| `name_national` | отображается в списке выбора языка |
| `name_en` | отображается как описание в списке |

---

## 3. GET /api/translations

Клиент вызывает этот эндпоинт в двух режимах:
- С `language=""` — получить ВСЕ переводы (для кэширования в `SettingsManager.cachedAllTranslations`)
- С `language=<код>` — получить переводы для конкретного языка (в `MultilingualConfigSheet`)

### TC-TRANS-1: Все переводы (language пустой)

```
GET /api/translations?language=
X-API-Key: <key>
```

**Ожидаемый результат:**
- HTTP 200
- Массив `TranslationModel`
- Содержит переводы всех языков

**Фактический результат:** 8 активных переводов (ru: 2, en: 3, uk: 2) ✅

### TC-TRANS-2: Фильтр по языку (language=ru)

```
GET /api/translations?language=ru
X-API-Key: <key>
```

**Ожидаемый результат:**
- HTTP 200
- Массив содержит только переводы с `language == "ru"`

**Фактический результат:** 2 перевода (SYNO code=1, BTI code=11) ✅

### TC-TRANS-3: Фильтр по языку (language=en)

```
GET /api/translations?language=en
X-API-Key: <key>
```

**Ожидаемый результат:** переводы с `language == "en"`

**Фактический результат:** 3 перевода (BSB code=16, WEBUS code=17, WEBBE code=779) ✅

### TC-TRANS-4: Фильтр по языку (language=uk)

```
GET /api/translations?language=uk
X-API-Key: <key>
```

**Ожидаемый результат:** переводы с `language == "uk"`

**Фактический результат:** 2 перевода (UBH code=20, NPU code=21) ✅

### TC-TRANS-5: По умолчанию only_active=1

Клиент не передаёт `only_active`, ожидается поведение по умолчанию — только активные переводы.

```
GET /api/translations?language=
```

**Ожидаемый результат:** все возвращённые переводы имеют `active == true`

**Фактический результат:** 8 переводов, все `active=true` ✅

### TC-TRANS-6: Структура TranslationModel

Каждый объект в массиве должен содержать:

| Поле | Тип | Обязательное | Используется клиентом |
|------|-----|---|---|
| `code` | integer | ✅ | ключ перевода, передаётся в excerpt_with_alignment и translation_books |
| `alias` | string | ✅ | — |
| `name` | string | ✅ | отображается в списке выбора, сохраняется как `translationName` |
| `description` | string \| null | ✅ | отображается как подпись, может быть null |
| `language` | string | ✅ | фильтрация на клиенте |
| `active` | boolean | ✅ | — |
| `voices` | array of VoiceModel | ✅ | список голосов для выбора диктора |

### TC-TRANS-7: Структура VoiceModel внутри TranslationModel

Каждый голос внутри `voices` должен содержать:

| Поле | Тип | Обязательное | Используется клиентом |
|------|-----|---|---|
| `code` | integer | ✅ | ключ голоса, передаётся в excerpt_with_alignment и translation_books |
| `alias` | string | ✅ | — |
| `name` | string | ✅ | отображается как имя диктора |
| `description` | string \| null | нет | отображается как описание диктора |
| `is_music` | boolean | ✅ | влияет на smooth pause (0.3 сек fade) при паузе аудио |
| `active` | boolean | ✅ | — |

**Пример фактического ответа (SYNO, голос Бондаренко):**
```json
{
  "code": 1,
  "alias": "bondarenko",
  "name": "Александр Бондаренко",
  "description": "Текст читает Александр Викторович Бондаренко...",
  "is_music": true,
  "active": true,
  "anomalies_count": 481,
  "anomalies_open_count": 0
}
```

> **Примечание:** поля `anomalies_count`, `anomalies_open_count` клиентом не используются, но должны присутствовать для совместимости схемы.

---

## 4. GET /api/translations/{translation_code}/books

Клиент вызывает этот эндпоинт для отображения списка книг и глав (`PageSelectView`, `SettingsManager.getTranslationBooks()`).

### TC-BOOKS-1: Книги с указанием voice_code

```
GET /api/translations/1/books?voice_code=1
X-API-Key: <key>
```

**Ожидаемый результат:**
- HTTP 200
- Массив из 66 объектов `TranslationBookModel` (полная Библия)

**Фактический результат:** 66 книг ✅

### TC-BOOKS-2: Книги без voice_code

```
GET /api/translations/1/books
X-API-Key: <key>
```

**Ожидаемый результат:**
- HTTP 200
- 66 книг (voice_code опционален)

**Фактический результат:** 66 книг ✅

> **Важно:** без voice_code поля `anomalies_count` и `anomalies_open_count` могут быть `null`.

### TC-BOOKS-3: Книги для английского перевода

```
GET /api/translations/16/books?voice_code=151
X-API-Key: <key>
```

**Ожидаемый результат:** 66 книг для BSB

**Фактический результат:** 66 книг, 9 из них имеют непустой `chapters_without_audio` ✅

### TC-BOOKS-4: Книги для украинского перевода

```
GET /api/translations/20/books?voice_code=130
X-API-Key: <key>
```

**Ожидаемый результат:** 66 книг для UBH

**Фактический результат:** 66 книг ✅

### TC-BOOKS-5: Структура TranslationBookModel

| Поле | Тип | Обязательное | Используется клиентом |
|------|-----|---|---|
| `code` | integer | ✅ | идентификатор |
| `book_number` | integer | ✅ | позиция книги (1–66), используется для OT/NT разделения (<39 = OT, >=39 = NT), навигации |
| `name` | string | ✅ | название книги, отображается в списке выбора и в заголовке чтения |
| `alias` | string | ✅ | короткий алиас (e.g. "gen", "jhn"), используется для формирования excerpt-запросов и трекинга прогресса |
| `chapters_count` | integer | ✅ | количество глав — формирует сетку глав, используется в прогрессе чтения |
| `chapters_without_audio` | array of int \| null | нет | номера глав без аудио — используется для отображения иконки 🔇 |
| `chapters_without_text` | array of int \| null | нет | номера глав без текста — используется для disabled-состояния кнопки главы |
| `anomalies_count` | integer \| null | нет | клиентом не используется |
| `anomalies_open_count` | integer \| null | нет | клиентом не используется |

**Пример фактического ответа (Бытие):**
```json
{
  "code": 7587,
  "book_number": 1,
  "name": "Бытие",
  "alias": "gen",
  "chapters_count": 50,
  "anomalies_count": 37,
  "anomalies_open_count": 0,
  "chapters_without_audio": [],
  "chapters_without_text": []
}
```

### TC-BOOKS-6: Порядок книг

**Ожидаемый результат:** книги отсортированы по `book_number` от 1 (Бытие/Genesis) до 66 (Откровение/Revelation).

### TC-BOOKS-7: Консистентность alias между переводами

**Ожидаемый результат:** одна и та же книга имеет одинаковый `alias` в разных переводах (e.g. книга Иоанна = "jhn" в SYNO, BSB, UBH). Это критично, т.к. клиент формирует excerpt-запросы по alias.

---

## 5. GET /api/excerpt_with_alignment

**Главный эндпоинт приложения.** Клиент вызывает его для:
- Загрузки текста и аудио-выравнивания при чтении (`PageReadView`)
- Загрузки мультиязычных шагов (`PageMultilingualReadView`)
- Превью текста в настройках (`PageSetupView.loadExampleText()`)
- Превью голоса (`MultilingualConfigSheet.toggleVoicePreview()`)

### TC-EXCERPT-1: Запрос полной главы (основной кейс)

```
GET /api/excerpt_with_alignment?translation=1&excerpt=jhn+1&voice=1
X-API-Key: <key>
```

**Ожидаемый результат:**
- HTTP 200
- `is_single_chapter: true` (один chapter в excerpt)
- `parts`: массив с 1 элементом
- `parts[0].verses`: 51 стих (Ин 1)
- `parts[0].audio_link`: непустая строка URL на .mp3
- Все стихи имеют `begin > 0` и `end > begin`

**Фактический результат:**
- `is_single_chapter: true`
- 51 стих, первый: begin=12.41, end=22.69
- audio_link: `https://api.bibleapi.space/api/audio/syn/bondarenko/43/01.mp3` ✅

### TC-EXCERPT-2: Запрос диапазона стихов

```
GET /api/excerpt_with_alignment?translation=1&excerpt=jhn+1:1-3&voice=1
X-API-Key: <key>
```

**Ожидаемый результат:**
- HTTP 200
- `parts[0].verses`: ровно 3 стиха
- `is_single_chapter: false` (диапазон стихов)

**Фактический результат:** 3 стиха, `is_single_chapter: false` ✅

> **Важно для клиента:** когда `is_single_chapter == true`, `periodFrom=0, periodTo=0` — аудио играет от начала файла. Когда `false` — `periodFrom` и `periodTo` берутся из `begin`/`end` первого/последнего стихов.

### TC-EXCERPT-3: Запрос без голоса (voice=0) — текстовый превью

```
GET /api/excerpt_with_alignment?translation=1&excerpt=jhn+1:1-3&voice=0
X-API-Key: <key>
```

**Ожидаемый результат:**
- HTTP 200
- `parts[0].audio_link`: пустая строка `""`
- `parts[0].verses[*].begin = 0.0`, `end = 0.0` (нет выравнивания)

**Фактический результат:** audio_link=`""`, begin=0.0, end=0.0 ✅

### TC-EXCERPT-4: Навигация prev/next для первой главы Библии

```
GET /api/excerpt_with_alignment?translation=1&excerpt=gen+1&voice=1
```

**Ожидаемый результат:**
- `parts[0].prev_excerpt: ""` (нет предыдущей)
- `parts[0].next_excerpt: "gen 2"`

**Фактический результат:** prev_excerpt=`""`, next_excerpt=`"gen 2"` ✅

### TC-EXCERPT-5: Навигация prev/next для последней главы Библии

```
GET /api/excerpt_with_alignment?translation=1&excerpt=rev+22&voice=1
```

**Ожидаемый результат:**
- `parts[0].prev_excerpt: "rev 21"`
- `parts[0].next_excerpt: ""` (нет следующей)

**Фактический результат:** prev_excerpt=`"rev 21"`, next_excerpt=`""` ✅

### TC-EXCERPT-6: Навигация prev/next для средней главы

```
GET /api/excerpt_with_alignment?translation=1&excerpt=jhn+1&voice=1
```

**Ожидаемый результат:**
- `prev_excerpt`: `"luk 24"` (последняя глава предыдущей книги)
- `next_excerpt`: `"jhn 2"`

**Фактический результат:** prev_excerpt=`"luk 24"`, next_excerpt=`"jhn 2"` ✅

### TC-EXCERPT-7: Английский перевод (BSB)

```
GET /api/excerpt_with_alignment?translation=16&excerpt=jhn+1:1-3&voice=151
```

**Ожидаемый результат:**
- HTTP 200
- Текст на английском
- Audio link на BSB аудио

**Фактический результат:**
- v1: "In the beginning was the Word...", begin=5.19, end=10.2
- audio_link: `https://api.bibleapi.space/api/audio/bsb/bsb_souer/43/01.mp3` ✅

### TC-EXCERPT-8: Украинский перевод (UBH)

```
GET /api/excerpt_with_alignment?translation=20&excerpt=jhn+1:1-3&voice=130
```

**Ожидаемый результат:**
- HTTP 200
- Текст на украинском
- book.name на украинском

**Фактический результат:**
- v1: "Споконвіку було Слово...", begin=19.06, end=28.99
- book.name: "Євангелія від Йоана" ✅

### TC-EXCERPT-9: Невалидный excerpt → 422

```
GET /api/excerpt_with_alignment?translation=1&excerpt=invalid_book+999&voice=1
```

**Ожидаемый результат:**
- HTTP 422
- Тело: `{"detail": "<описание ошибки>"}`

**Фактический результат:** `{"detail":"Book with alias 'book' not found for translation 1."}` ✅

> **Важно для клиента:** ответ 422 имеет тип `SimpleErrorResponse` с полем `detail` (string), а не `HTTPValidationError`.

### TC-EXCERPT-10: Структура ExcerptWithAlignmentModel

| Поле | Тип | Обязательное | Используется клиентом |
|------|-----|---|---|
| `title` | string | ✅ | — (не используется напрямую) |
| `is_single_chapter` | boolean | ✅ | определяет режим periodFrom/periodTo для аудио |
| `parts` | array of PartsWithAlignmentModel | ✅ | основные данные |

### TC-EXCERPT-11: Структура PartsWithAlignmentModel

| Поле | Тип | Обязательное | Используется клиентом |
|------|-----|---|---|
| `book` | BookInfoModel | ✅ | `book.name` → заголовок, `book.number` → навигация, `book.alias` — |
| `chapter_number` | integer | ✅ | подзаголовок "Глава N" |
| `audio_link` | string | ✅ | URL аудиофайла (пустая строка если нет аудио/voice=0) |
| `prev_excerpt` | string | ✅ | навигация «предыдущая глава» (пустая строка если нет) |
| `next_excerpt` | string | ✅ | навигация «следующая глава» (пустая строка если нет) |
| `verses` | array of VerseWithAlignmentModel | ✅ | текст и временные метки |
| `notes` | array of NoteModel | ✅ | сноски |
| `titles` | array of TitleModel | ✅ | заголовки разделов |

### TC-EXCERPT-12: Структура BookInfoModel

| Поле | Тип | Обязательное | Используется клиентом |
|------|-----|---|---|
| `code` | integer | ✅ | — |
| `number` | integer | ✅ | `bookDigitCode`, `currentBookId` |
| `alias` | string | ✅ | — |
| `name` | string | ✅ | `currentExcerptTitle` |
| `chapters_count` | integer | ✅ | — |

### TC-EXCERPT-13: Структура VerseWithAlignmentModel

| Поле | Тип | Обязательное | Используется клиентом |
|------|-----|---|---|
| `code` | integer | ✅ | связь с notes и titles |
| `number` | integer | ✅ | номер стиха, отображение, скролл |
| `join` | integer | ✅ | сортировка стихов (number+join) |
| `text` | string | ✅ | plain-text для аудио-отображения |
| `html` | string | ✅ | HTML-разметка для текстового отображения |
| `begin` | number | ✅ | время начала стиха в аудиофайле (секунды) |
| `end` | number | ✅ | время конца стиха в аудиофайле (секунды) |
| `start_paragraph` | boolean | ✅ | начало абзаца — используется для автопаузы по абзацам и для группировки в мультиязычном режиме |

### TC-EXCERPT-14: Структура NoteModel

| Поле | Тип | Обязательное | Используется клиентом |
|------|-----|---|---|
| `code` | integer | ✅ | идентификатор |
| `number` | integer | ✅ | — |
| `text` | string | ✅ | текст сноски |
| `verse_code` | integer \| null | нет | связь с verse.code — если set, сноска привязана к стиху |
| `title_code` | integer \| null | нет | связь с title.code — если set, сноска привязана к заголовку |
| `position_text` | integer | ✅ | позиция в plain-text |
| `position_html` | integer | ✅ | позиция в HTML |

### TC-EXCERPT-15: Структура TitleModel

| Поле | Тип | Обязательное | Используется клиентом |
|------|-----|---|---|
| `code` | integer | ✅ | идентификатор, связь с NoteModel.title_code |
| `text` | string | ✅ | текст заголовка |
| `before_verse_code` | integer \| null | нет | verse.code — заголовок показывается перед этим стихом |
| `metadata` | string \| null | нет | метаданные заголовка |
| `reference` | string \| null | нет | ссылка на связанные отрывки |
| `subtitle` | boolean | нет (default false) | является ли подзаголовком |
| `position_text` | integer \| null | нет | позиция в тексте |
| `position_html` | integer \| null | нет | позиция в HTML |

### TC-EXCERPT-16: Заголовки и сноски привязаны к стихам

```
GET /api/excerpt_with_alignment?translation=1&excerpt=gen+1&voice=1
```

**Ожидаемый результат:**
- Titles имеют `before_verse_code` совпадающий с одним из `verses[*].code`
- Notes имеют `verse_code` совпадающий с одним из `verses[*].code`

**Фактический результат:** 2 title (перед стихами 1 и 26), 15 notes — все привязаны к стихам через verse_code ✅

### TC-EXCERPT-17: Монотонность begin/end

**Ожидаемый результат:** для каждого стиха `end > begin`, и стихи идут в хронологическом порядке аудио (begin[i+1] >= end[i], с учётом join-сортировки).

**Фактический результат для jhn 1:** first begin=12.41, last end=563.92, все end > begin ✅

### TC-EXCERPT-18: start_paragraph присутствует и распределён

```
GET /api/excerpt_with_alignment?translation=1&excerpt=gen+1&voice=1
```

**Ожидаемый результат:**
- Первый стих имеет `start_paragraph: true`
- Не все стихи имеют `start_paragraph: true` (есть разделение)

**Фактический результат:** 8 из 31 стихов имеют `start_paragraph: true` ✅

### TC-EXCERPT-19: Titles с reference (для BSB)

```
GET /api/excerpt_with_alignment?translation=16&excerpt=mat+1&voice=151
```

**Ожидаемый результат:**
- Titles могут содержать `reference` (ссылку на параллельные отрывки)

**Фактический результат:** title "The Genealogy of Jesus" с reference="(Ruth 4:18–22; Luke 3:23–38)" ✅

---

## 6. GET /api/audio/{translation}/{voice}/{book}/{chapter}.mp3

Клиент использует URL из поля `audio_link` ответа excerpt_with_alignment, добавляя query-параметр `api_key`.

### TC-AUDIO-1: Получение аудиофайла (GET)

```
GET /api/audio/syn/bondarenko/43/01.mp3?api_key=<key>
Host: api.bibleapi.space
```

**Ожидаемый результат:**
- HTTP 200
- Content-Type: `audio/mpeg`
- Content-Length: > 0
- Accept-Ranges: bytes

**Фактический результат:**
- HTTP 200, Content-Type: audio/mpeg, Content-Length: 2257648
- Accept-Ranges: bytes ✅

### TC-AUDIO-2: Range-запрос (стриминг для iOS)

```
GET /api/audio/syn/bondarenko/43/01.mp3?api_key=<key>
Host: api.bibleapi.space
Range: bytes=0-1023
```

**Ожидаемый результат:**
- HTTP 206 (Partial Content)
- Content-Range: `bytes 0-1023/<total>`
- Content-Length: 1024

**Фактический результат:**
- HTTP 206, Content-Range: bytes 0-1023/2257648, Content-Length: 1024 ✅

> **Критично:** iOS AVPlayer использует HTTP Range requests для стриминга. Без поддержки 206 — аудио не заработает.

### TC-AUDIO-3: HEAD-запрос

```
HEAD /api/audio/syn/bondarenko/43/01.mp3?api_key=<key>
Host: api.bibleapi.space
```

**Ожидаемый результат:**
- HTTP 200
- Те же заголовки Content-Type, Content-Length, Accept-Ranges

**Фактический результат:** HTTP 200, Content-Type: audio/mpeg ✅

### TC-AUDIO-4: CORS-заголовки

**Ожидаемый результат:**
- `Access-Control-Allow-Origin: *`

**Фактический результат:** `access-control-allow-origin: *` ✅

### TC-AUDIO-5: Аудио для английского перевода

```
GET /api/audio/bsb/bsb_souer/43/01.mp3?api_key=<key>
Host: api.bibleapi.space
```

**Ожидаемый результат:** HTTP 200, Content-Type: audio/mpeg

### TC-AUDIO-6: Аудио для украинского перевода

```
GET /api/audio/ubh/kozlov_uk/43/01.mp3?api_key=<key>
Host: api.bibleapi.space
```

**Ожидаемый результат:** HTTP 200, Content-Type: audio/mpeg

### TC-AUDIO-7: Авторизация через query параметр api_key

**Ожидаемый результат:** аудио-эндпоинт принимает API-ключ через query-параметр `api_key` (не через заголовок). Клиент передаёт ключ именно так.

### TC-AUDIO-8: audio_link из excerpt_with_alignment корректен

**Ожидаемый результат:** URL из поля `audio_link` ответа excerpt_with_alignment (с добавлением `?api_key=<key>`) доступен и отдаёт audio/mpeg.

---

## 7. Контракты моделей (схемы)

### TC-SCHEMA-1: Nullable поля не ломают клиент

Следующие поля могут быть `null` и клиент должен это обрабатывать (и делает это):

| Модель | Поле | Контекст |
|--------|------|----------|
| `TranslationModel` | `description` | описание перевода |
| `VoiceModel` | `description` | описание диктора |
| `TitleModel` | `before_verse_code` | — |
| `TitleModel` | `metadata` | — |
| `TitleModel` | `reference` | — |
| `TitleModel` | `subtitle` | default false |
| `TitleModel` | `position_text` | — |
| `TitleModel` | `position_html` | — |
| `NoteModel` | `verse_code` | может быть null |
| `NoteModel` | `title_code` | может быть null |
| `TranslationBookModel` | `anomalies_count` | null без voice_code |
| `TranslationBookModel` | `anomalies_open_count` | null без voice_code |
| `TranslationBookModel` | `chapters_without_audio` | может быть null |
| `TranslationBookModel` | `chapters_without_text` | может быть null |

### TC-SCHEMA-2: Пустые массивы вместо null

**Ожидаемый результат:**
- `parts[0].verses`: пустой массив `[]` если нет стихов (не null)
- `parts[0].notes`: пустой массив `[]` если нет сносок (не null)
- `parts[0].titles`: пустой массив `[]` если нет заголовков (не null)
- `translation.voices`: пустой массив `[]` если нет голосов (не null)

### TC-SCHEMA-3: Пустые строки для отсутствующих данных

**Ожидаемый результат:**
- `prev_excerpt`: `""` (пустая строка) когда нет предыдущей главы (не null)
- `next_excerpt`: `""` (пустая строка) когда нет следующей главы (не null)
- `audio_link`: `""` (пустая строка) когда нет аудио (не null)

---

## Сводная таблица эндпоинтов

| # | Метод | Эндпоинт | Где используется в клиенте | Критичность |
|---|-------|----------|---------------------------|-------------|
| 1 | GET | `/api/languages` | PageSetupView, MultilingualConfigSheet | Высокая |
| 2 | GET | `/api/translations?language=` | SettingsManager (кэш всех переводов) | Высокая |
| 3 | GET | `/api/translations?language=<code>` | MultilingualConfigSheet | Высокая |
| 4 | GET | `/api/translations/{code}/books?voice_code=` | PageSelectView, SettingsManager | Высокая |
| 5 | GET | `/api/excerpt_with_alignment` | PageReadView, PageMultilingualReadView, PageSetupView, MultilingualConfigSheet, PageMultilingualConfigView | **Критическая** |
| 6 | GET | `/api/audio/...mp3?api_key=` | AVPlayer (стриминг) | **Критическая** |

### Эндпоинты, которые есть в openapi.yaml, но НЕ используются клиентом:

| Эндпоинт | Примечание |
|----------|------------|
| `GET /api/chapter_with_alignment` | Не используется (есть в спеке, но клиент использует excerpt_with_alignment) |
| `GET /api/translation_info` | Закомментирован в коде PageSetupView |
| `POST /api/auth/login` | Админский, не клиентский |
| `GET /api/check_translation` | Не используется клиентом |
| `GET /api/check_voice` | Не используется клиентом |
| `POST /api/cache/clear` | Админский |
| `PUT /api/translations/{code}` | Админский |
| `PUT /api/voices/{code}` | Админский |
| `GET /api/voices/{code}/anomalies` | Админский |
| `POST /api/voices/anomalies` | Админский |
| `PATCH /api/voices/anomalies/{code}/status` | Админский |
| `POST /api/voices/manual-fixes` | Админский |

---

## Параметры для тестирования

### Основные комбинации translation + voice, используемые в приложении по умолчанию:

| Язык | Перевод (code) | Alias | Голос (code) | Alias голоса |
|------|----------------|-------|--------------|--------------|
| ru | 1 | syn | 1 | bondarenko |
| ru | 1 | syn | 2 | prudovsky |
| ru | 11 | bti | 123 | prozorovsky |
| en | 16 | bsb | 150 | bsb_david |
| en | 16 | bsb | 151 | bsb_souer |
| en | 17 | webus | 152 | winfred_henson |
| uk | 20 | ubh | 130 | kozlov_uk |
| uk | 21 | npu | 131 | npu_uk |
| en | 779 | webbe | 129 | web_british |

### Ключевые excerpt-форматы:

| Формат | Пример | Описание |
|--------|--------|----------|
| `<alias> <chapter>` | `jhn 1` | Полная глава |
| `<alias> <ch>:<v1>-<v2>` | `jhn 1:1-3` | Диапазон стихов |

### Граничные значения для тестирования:

| Кейс | Excerpt |
|------|---------|
| Первая глава Библии | `gen 1` |
| Последняя глава | `rev 22` |
| Короткая глава (Пс 117 = 2 стиха) | `psa 117` |
| Длинная глава (Пс 119 = 176 стихов) | `psa 119` |
| Глава с множеством сносок | `gen 1` |
| Глава с заголовками | `mat 1` |
