"""
Pydantic v2 schemas — request/response types for all API endpoints.
Strict validation, typed fields, no Any leakage to consumers.
"""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Shared ───────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: dict[str, Any] = {}


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    environment: str


# ── Discover ─────────────────────────────────────────────────────────────────

class DiscoverRequest(BaseModel):
    query: Annotated[str, Field(min_length=3, max_length=500)]
    preferences: list[str] = Field(default_factory=list, max_length=10)
    exclude_countries: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("preferences", "exclude_countries", mode="before")
    @classmethod
    def limit_list_items(cls, v: list[str]) -> list[str]:
        return [item[:100] for item in v[:20]]


class Destination(BaseModel):
    name: str
    country: str
    continent: str
    tagline: str
    why_visit: str
    best_time: str
    vibe: str
    lat: float
    lng: float
    hidden_gem_score: int = Field(ge=1, le=10)
    tags: list[str]


class DiscoverResponse(BaseModel):
    destinations: list[Destination]
    query_echo: str
    search_intent: str


# ── Story ────────────────────────────────────────────────────────────────────

class StoryRequest(BaseModel):
    destination: Annotated[str, Field(min_length=2, max_length=200)]
    pov: str = "first-person traveler"  # narrative POV


# ── Hidden Gems ──────────────────────────────────────────────────────────────

class GemsRequest(BaseModel):
    query: Annotated[str, Field(min_length=3, max_length=500)]
    n_results: int = Field(default=6, ge=1, le=12)
    continent: str | None = None


class GemItem(BaseModel):
    name: str
    country: str
    description: str
    authenticity_score: float
    tourist_density: str
    best_season: str
    tags: list[str]
    lat: float
    lng: float
    similarity: float
    ai_pitch: str


class GemsResponse(BaseModel):
    gems: list[GemItem]
    total: int


# ── Etiquette ────────────────────────────────────────────────────────────────

class EtiquetteRequest(BaseModel):
    destination: Annotated[str, Field(min_length=2, max_length=200)]


class EtiquetteResponse(BaseModel):
    destination: str
    greeting: str
    local_greeting_phrase: str
    dos: list[str]
    donts: list[str]
    dress_code: str
    tipping_norm: str
    sacred_sites_etiquette: str
    local_taboos: list[str]
    useful_phrases: list[dict[str, str]]  # [{"phrase": "...", "meaning": "..."}]


# ── Festival ─────────────────────────────────────────────────────────────────

class FestivalRequest(BaseModel):
    destination: Annotated[str, Field(min_length=2, max_length=200)]
    months_ahead: int = Field(default=3, ge=1, le=12)


class Festival(BaseModel):
    name: str
    date_description: str
    description: str
    cultural_significance: str
    traveler_tip: str
    crowd_level: str


class FestivalResponse(BaseModel):
    destination: str
    festivals: list[Festival]
    seasonal_summary: str


# ── Walking Tour ──────────────────────────────────────────────────────────────

class TourRequest(BaseModel):
    destination: Annotated[str, Field(min_length=2, max_length=200)]
    duration_hours: float = Field(default=2.0, ge=0.5, le=8.0)
    theme: str = "cultural highlights"


class TourStop(BaseModel):
    order: int
    name: str
    description: str
    narrative: str
    walking_time_from_prev: str
    lat: float
    lng: float
    insider_tip: str


class TourResponse(BaseModel):
    destination: str
    theme: str
    total_duration: str
    total_distance_km: float
    stops: list[TourStop]
    start_tip: str


# ── Timeline ─────────────────────────────────────────────────────────────────

class TimelineRequest(BaseModel):
    destination: Annotated[str, Field(min_length=2, max_length=200)]


class TimelineEra(BaseModel):
    era: str
    period: str
    title: str
    narrative: str
    key_figure: str
    landmark: str


class TimelineResponse(BaseModel):
    destination: str
    eras: list[TimelineEra]
    closing_reflection: str


# ── Food DNA ─────────────────────────────────────────────────────────────────

class FoodRequest(BaseModel):
    destination: Annotated[str, Field(min_length=2, max_length=200)]
    dietary_restrictions: list[str] = Field(default_factory=list, max_length=5)


class FoodStop(BaseModel):
    category: str  # street_food | traditional | modern_fusion
    dish_name: str
    description: str
    where_to_find: str
    price_range: str
    must_try_tip: str
    flavor_profile: list[str]


class FoodResponse(BaseModel):
    destination: str
    food_journey: list[FoodStop]
    food_culture_note: str
    beverage_pairing: str


# ── Chat ─────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str = Field(pattern=r"^(user|assistant)$")
    content: Annotated[str, Field(min_length=1, max_length=2000)]


class ChatRequest(BaseModel):
    destination: Annotated[str, Field(min_length=2, max_length=200)]
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_last_message_is_user(self) -> "ChatRequest":
        if self.messages and self.messages[-1].role != "user":
            raise ValueError("Last message must be from user.")
        return self
