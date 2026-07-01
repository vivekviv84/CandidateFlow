"""Source adapters that convert raw inputs into CandidateFragment objects."""

from app.adapters.ats_json_adapter import AtsJsonAdapter
from app.adapters.csv_adapter import CsvAdapter
from app.adapters.github_adapter import GitHubAdapter
from app.adapters.notes_adapter import NotesAdapter
from app.adapters.resume_adapter import ResumeAdapter

__all__ = [
    "AtsJsonAdapter",
    "CsvAdapter",
    "GitHubAdapter",
    "NotesAdapter",
    "ResumeAdapter",
]

