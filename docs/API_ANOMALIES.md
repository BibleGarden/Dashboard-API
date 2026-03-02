# Voice Anomalies API

## Anomaly Statuses

- `detected` - error detected automatically (default)
- `confirmed` - error confirmed upon review
- `disproved` - error disproved, not confirmed by review
- `corrected` - manual correction performed
- `already_resolved` - already fixed previously (system use only)
- `disproved_whisper` - automatically disproved by Whisper analysis (system use only)

## API Methods

### GET /voices/{voice_code}/anomalies

Retrieve list of anomalies for a voice with optional status filtering.

**Parameters:**
- `voice_code` (path) - voice code
- `status` (query, optional) - anomaly status filter

**Request example:**
```
GET /voices/1/anomalies?status=detected
```

### PATCH /voices/anomalies/{anomaly_code}/status

Update anomaly status with optional timestamp correction.

**Parameters:**
- `anomaly_code` (path) - anomaly code

**Request body:**
```json
{
  "status": "detected|confirmed|disproved|corrected|disproved_whisper",
  "begin": 10.5,  // only for "corrected" status
  "end": 12.0     // only for "corrected" status
}
```

**Validation rules:**
- For `corrected` status, `begin` and `end` fields are **required**
- For other statuses, `begin` and `end` fields are **not allowed**
- `begin` must be less than `end`
- Statuses `already_resolved` and `disproved_whisper` cannot be set manually
- **Cannot change status from `corrected` to `confirmed`**

**Request examples:**

1. Confirming an anomaly:
```json
{
  "status": "confirmed"
}
```

2. Disproving an anomaly:
```json
{
  "status": "disproved"
}
```

3. Correction with new timestamps:
```json
{
  "status": "corrected",
  "begin": 10.5,
  "end": 12.0
}
```

### POST /voices/anomalies

Create a new voice anomaly.

**Request body:**
```json
{
  "voice": 1,
  "translation": 1,
  "book_number": 1,
  "chapter_number": 1,
  "verse_number": 1,
  "word": "word",              // optional
  "position_in_verse": 5,     // optional
  "position_from_end": 3,     // optional
  "duration": 1.5,            // optional
  "speed": 2.0,               // optional
  "ratio": 1.8,               // required, must be > 0
  "anomaly_type": "manual",   // default "manual"
  "status": "detected"        // default "detected"
}
```

**Anomaly types:**
- `fast` - fast pronunciation
- `slow` - slow pronunciation
- `long` - long pause
- `short` - short pause
- `manual` - added manually (default)

**Validation rules:**
- The `ratio` field is required and must be a positive number
- Fields `voice`, `translation`, `book_number`, `chapter_number`, `verse_number` are required
- The system verifies the existence of the specified voice, translation, and verse
- The anomaly type must be one of the allowed values

## voice_manual_fixes Logic

When updating an anomaly status, the system automatically manages the `voice_manual_fixes` table:

### DISPROVED and CORRECTED Statuses
- A record is created or updated in `voice_manual_fixes`
- For `DISPROVED`: original timestamps from `voice_alignments` are used
- For `CORRECTED`: the `begin` and `end` values from the request are used

### CONFIRMED Status
- If a record exists in `voice_manual_fixes` with matching timestamps - it is deleted
- If timestamps do not match - a 422 error is returned
- If no record exists - no action is taken

This allows tracking verses that have been manually reviewed, so that new anomalies are not created for them during re-parsing.

## Excerpts with Corrections

### GET /excerpt_with_alignment

The method for retrieving Bible excerpts with voice alignment timestamps automatically applies corrections from the `voice_manual_fixes` table.

**How it works:**
- If a record exists in `voice_manual_fixes` for a verse - the corrected timestamps are used
- If no record exists - the original timestamps from `voice_alignments` are used
- Implemented via SQL COALESCE: `COALESCE(vmf.begin, a.begin)` and `COALESCE(vmf.end, a.end)`

**Request example:**
```
GET /excerpt_with_alignment?translation=16&excerpt=jhn 3:16-17&voice=1
```

In the response, the `begin` and `end` fields for each verse will contain the current timestamps with all corrections applied.
