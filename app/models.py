# models.py
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Literal
from enum import Enum
from datetime import datetime

# Languages & Translations

class LanguageModel(BaseModel):
    alias: str
    name_en: str
    name_national: str

class VoiceModel(BaseModel):
    code: int
    alias: str
    name: str
    description: Optional[str] = None
    is_music: bool
    active: bool
    anomalies_count: int = 0
    anomalies_open_count: int = 0

class TranslationModel(BaseModel):
    code: int
    alias: str
    name: str
    description: Optional[str] = None
    language: str
    active: bool
    voices: list[VoiceModel]

# TranslationInfo

class BookInfoModel(BaseModel):
    code: int
    number: int
    alias: str
    name: str
    chapters_count: int

class TranslationInfoModel(BaseModel):
    code: int
    alias: str
    name: str
    description: Optional[str] = None
    language: str
    books_info: list[BookInfoModel]

# ExcerptWithAlignment
    
class VerseWithAlignmentModel(BaseModel):
    code: int
    number: int
    join: int
    text: str
    html: str
    begin: float
    end: float
    start_paragraph: bool

class NoteModel(BaseModel):
    code: int
    number: int
    text: str
    verse_code: Optional[int] = None
    title_code: Optional[int] = None
    position_text: int
    position_html: int

class TitleModel(BaseModel):
    code: int
    text: str
    before_verse_code: Optional[int] = None
    metadata: Optional[str] = None
    reference: Optional[str] = None
    subtitle: bool = False
    position_text: Optional[int] = None
    position_html: Optional[int] = None

class PartsWithAlignmentModel(BaseModel):
    book: BookInfoModel
    chapter_number: int
    audio_link: str
    prev_excerpt: str
    next_excerpt: str
    verses: list[VerseWithAlignmentModel]
    notes: list[NoteModel]
    titles: list[TitleModel]

class ExcerptWithAlignmentModel(BaseModel):
    title: str
    is_single_chapter: bool
    parts: list[PartsWithAlignmentModel]

# Update Models

class TranslationUpdateModel(BaseModel):
    alias: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None
    active: Optional[bool] = None

class VoiceUpdateModel(BaseModel):
    alias: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    is_music: Optional[bool] = None
    active: Optional[bool] = None

# Voice Anomalies

class AnomalyStatus(str, Enum):
    DETECTED = "detected"      # error detected (default)
    CONFIRMED = "confirmed"    # error confirmed
    DISPROVED = "disproved"    # error disproved, not confirmed by verification
    CORRECTED = "corrected"    # manual correction performed
    ALREADY_RESOLVED = "already_resolved" # already fixed previously
    DISPROVED_WHISPER = "disproved_whisper"  # auto-disproved by Whisper analysis

class VoiceAnomalyModel(BaseModel):
    code: int
    voice: int
    translation: int
    book_number: int
    chapter_number: int
    verse_number: int  # Changed from Optional[int] to int (NOT NULL)
    word: Optional[str] = None  # Changed from str to Optional[str] (nullable)
    position_in_verse: Optional[int] = None
    position_from_end: Optional[int] = None
    duration: Optional[float] = None  # Changed from float to Optional[float] (nullable)
    speed: Optional[float] = None  # Changed from float to Optional[float] (nullable)
    ratio: float
    anomaly_type: str = 'fast'  # Changed from Optional[str] to str (NOT NULL)
    status: AnomalyStatus = AnomalyStatus.DETECTED
    verse_text: Optional[str] = None
    updated_at: Optional[datetime] = None

class VoiceAnomaliesResponseModel(BaseModel):
    items: list[VoiceAnomalyModel]
    total_count: int

class AnomalyStatusUpdateModel(BaseModel):
    status: AnomalyStatus
    begin: Optional[float] = None  # New begin time for corrected status
    end: Optional[float] = None    # New end time for corrected status
    
    @model_validator(mode='after')
    def validate_correction_fields(self):
        """Validate begin/end fields based on status"""
        if self.status == AnomalyStatus.CORRECTED:
            if self.begin is None or self.end is None:
                raise ValueError('begin and end are required for corrected status')
            if self.begin >= self.end:
                raise ValueError('begin must be less than end')
        else:
            if self.begin is not None or self.end is not None:
                raise ValueError('begin and end are only allowed for corrected status')
        return self

# Translation Books

class TranslationBookModel(BaseModel):
    code: int
    book_number: int
    name: str
    alias: str
    chapters_count: int
    anomalies_count: Optional[int] = None
    anomalies_open_count: Optional[int] = None
    chapters_without_audio: list[int] = Field(default_factory=list)
    chapters_without_text: list[int] = Field(default_factory=list)


# Voice Anomaly Creation

class VoiceAnomalyCreateModel(BaseModel):
    voice: int
    translation: int
    book_number: int
    chapter_number: int
    verse_number: int
    word: Optional[str] = None
    position_in_verse: Optional[int] = None
    position_from_end: Optional[int] = None
    duration: Optional[float] = None
    speed: Optional[float] = None
    ratio: float
    anomaly_type: str = 'manual'
    status: AnomalyStatus = AnomalyStatus.DETECTED
    
    @field_validator('anomaly_type')
    @classmethod
    def validate_anomaly_type(cls, v):
        valid_types = ['fast', 'slow', 'long', 'short', 'manual']
        if v not in valid_types:
            raise ValueError(f'Anomaly type must be one of: {", ".join(valid_types)}')
        return v
    
    @field_validator('ratio')
    @classmethod
    def validate_ratio(cls, v):
        if v <= 0:
            raise ValueError('Ratio must be positive')
        return v

# Audio Error Models

class AudioFileNotFoundError(BaseModel):
    detail: str
    alternative_url: Optional[str] = None

# Voice Manual Fixes Models

class VoiceManualFixCreateModel(BaseModel):
    voice: int
    book_number: int
    chapter_number: int
    verse_number: int
    begin: float
    end: float
    info: Optional[str] = None
    
    @field_validator('book_number')
    @classmethod
    def validate_book_number(cls, v):
        if v < 1 or v > 66:
            raise ValueError('Book number must be between 1 and 66')
        return v
    
    @field_validator('chapter_number')
    @classmethod
    def validate_chapter_number(cls, v):
        if v < 1:
            raise ValueError('Chapter number must be greater than 0')
        return v
    
    @field_validator('verse_number')
    @classmethod
    def validate_verse_number(cls, v):
        if v < 1:
            raise ValueError('Verse number must be greater than 0')
        return v
    
    @model_validator(mode='after')
    def validate_timing(self):
        if self.begin >= self.end:
            raise ValueError('Begin time must be less than end time')
        if self.begin < 0:
            raise ValueError('Begin time must be non-negative')
        return self

class VoiceManualFixModel(BaseModel):
    code: int
    voice: int
    book_number: int
    chapter_number: int
    verse_number: int
    begin: float
    end: float
    info: Optional[str] = None

# About

class LocalizedText(BaseModel):
    en: str
    ru: str
    uk: str

class AboutContactModel(BaseModel):
    id: str
    icon: str
    url: str
    sort_order: int
    label: LocalizedText
    subtitle: LocalizedText

class AboutModel(BaseModel):
    contacts: list[AboutContactModel]
    about_text: LocalizedText

