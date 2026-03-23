"""
Модели данных для приложения.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


class AnalysisType:
    FULL = "Full"
    SECURITY_ONLY = "SecurityOnly"
    STYLE_ONLY = "StyleOnly"
    PERFORMANCE = "Performance"
    BEST_PRACTICES = "BestPractices"
    CODE_EXAMPLES = "CodeExamples"


@dataclass
class CodeSubmission:
    code: str
    language: str = "Python"
    analysis_type: str = AnalysisType.FULL
    complexity_limit: int = 1000
    include_code_examples: bool = True


@dataclass
class AnalysisResult:
    errors: List[str] = field(default_factory=list)
    style_issues: List[str] = field(default_factory=list)
    security_risks: List[str] = field(default_factory=list)
    best_practices: List[str] = field(default_factory=list)
    performance_issues: List[str] = field(default_factory=list)
    architecture_issues: List[str] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)
    code_suggestions: List[str] = field(default_factory=list)
    language: str = "unknown"
    summary: str = ""
    complexity_score: int = 0
    maintainability_score: int = 0
    security_score: int = 0
    performance_score: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> "AnalysisResult":
        return cls(
            errors=data.get("errors", []),
            style_issues=data.get("style_issues", []),
            security_risks=data.get("security_risks", []),
            best_practices=data.get("best_practices", []),
            performance_issues=data.get("performance_issues", []),
            architecture_issues=data.get("architecture_issues", []),
            improvement_suggestions=data.get("improvement_suggestions", []),
            code_suggestions=data.get("code_suggestions", []),
            language=data.get("language", "unknown"),
            summary=data.get("summary", ""),
            complexity_score=data.get("complexity_score", 0),
            maintainability_score=data.get("maintainability_score", 0),
            security_score=data.get("security_score", 0),
            performance_score=data.get("performance_score", 0),
        )


@dataclass
class AnalysisHistoryItem:
    id: int
    timestamp: datetime
    code: str
    language: str
    result: str
    analysis_type: str


@dataclass
class GitFileInfo:
    name: str = ""
    path: str = ""
    type: str = "file"
    size: int = 0
    download_url: Optional[str] = None


@dataclass
class GitCommitResult:
    success: bool = False
    error_message: Optional[str] = None
    branch_name: Optional[str] = None
    pull_request_url: Optional[str] = None
    pull_request_number: int = 0


@dataclass
class GitRepoAnalysisRequest:
    repository_url: str
    path: Optional[str] = None
    branch: Optional[str] = None
    language: Optional[str] = None
    analysis_type: str = AnalysisType.FULL
    token: Optional[str] = None
    apply_fixes: bool = False
    add_comment: bool = False
    pull_request_number: Optional[int] = None
    description: Optional[str] = None


@dataclass
class TokenValidationResult:
    is_valid: bool = False
    user_name: Optional[str] = None
    error_message: Optional[str] = None
