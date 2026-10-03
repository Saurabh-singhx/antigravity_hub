from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class QnASource(BaseModel):
    source_type: str = "github_repo"          # "github_repo" | "tech_handle" | "engineering_blog"
    source_name: str                          # e.g., "yangshun/tech-interview-handbook"
    source_url: str                           # e.g., "https://github.com/yangshun/tech-interview-handbook"
    source_quote: Optional[str] = None        # Verifiable excerpt proving source authenticity
    stars: Optional[int] = None
    reliability_score: float = 1.0
    verified: bool = True


class QnAItem(BaseModel):
    id: str
    job_title: str                            # Target applied job role (e.g. "Full Stack Engineer (+Flutter)")
    company: Optional[str] = None             # Target applied company
    slot_id: int                              # 1 (Morning), 2 (Afternoon), 3 (Evening)
    slot_name: str = "morning"                # "morning" | "afternoon" | "evening"
    date: str                                 # Format: YYYY-MM-DD
    question: str                             # Plain interview question title
    answer: str                               # Authentic, structured, verified answer content
    category: str = "Fundamentals"            # "Fundamentals" | "Architecture" | "System Design" | "Behavioral"
    tech_stack: List[str] = Field(default_factory=list)  # e.g. ["Flutter", "Dart", "Async"]
    source: QnASource
    difficulty: str = "Medium"                # "Easy" | "Medium" | "Hard"
    is_mastered: bool = False
    created_at: Optional[str] = None


class SlotExecution(BaseModel):
    id: Optional[int] = None
    date: str                                 # YYYY-MM-DD
    slot_id: int                              # 1, 2, 3
    slot_name: str
    executed_at: str
    question_count: int = 0
    status: str = "completed"                 # "completed", "skipped", "failed"
    notes: Optional[str] = None


class PaginatedQnAResponse(BaseModel):
    items: List[QnAItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class DailyQnAResponse(BaseModel):
    date: str
    active_slot_id: Optional[int]
    active_slot_name: Optional[str]
    slot_progress: Dict[str, Any]             # slot 1, 2, 3 completion status
    items: List[QnAItem]
    total_questions: int


class QnAManualTriggerRequest(BaseModel):
    slot_id: Optional[int] = None             # If None, automatically computes current active slot
    force: bool = False                       # If True, re-runs slot even if already executed today
