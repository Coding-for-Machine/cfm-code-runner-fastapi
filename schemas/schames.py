
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class LanguageEnum(str, Enum):
    """Qo'llab-quvvatlanadigan dasturlash tillari"""
    python = "python"
    cpp = "cpp"
    c = "c"
    go = "go"


class SubmissionRequest(BaseModel):
    """Kod yuborish so'rovi"""
    source_code: str = Field(..., description="Manba kod", min_length=1)
    language: LanguageEnum = Field(..., description="Dasturlash tili")
    input_data: str = Field(default="", description="Kirish ma'lumotlari")
    time_limit: float = Field(
        default=1.0, 
        gt=0, 
        le=10, 
        description="Vaqt limiti (soniyada)"
    )
    memory_limit: int = Field(
        default=262144, 
        gt=0, 
        le=1048576, 
        description="Xotira limiti (KB)"
    )

    @field_validator('source_code')
    @classmethod
    def validate_source_code(cls, v):
        if len(v.strip()) == 0:
            raise ValueError("Manba kod bo'sh bo'lishi mumkin emas")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "source_code": "n = int(input())\nprint(n ** 2)",
                "language": "python",
                "input_data": "5",
                "time_limit": 1.0,
                "memory_limit": 262144
            }
        }

class SubmissionResponse(BaseModel):
    status: str
    time: float
    memory: int
    exit_code: int
    stdout: str
    stderr: str
    message: str
    timestamp: str


class TestCase(BaseModel):
    input: str = Field(default="", description="Kirish ma'lumotlari")
    expected_output: Optional[str] = Field(None, description="Kutilayotgan chiqish")


class BatchSubmissionRequest(BaseModel):
    source_code: str = Field(..., min_length=1)
    language: LanguageEnum
    test_cases: List[TestCase] = Field(..., min_items=1, max_items=50)
    time_limit: float = Field(default=1.0, gt=0, le=10)
    memory_limit: int = Field(default=262144, gt=0, le=1048576)

    # class Config:
    #     json_schema_extra = {
    #         "example": {
    #             "source_code": "n = int(input())\nprint(n * 2)",
    #             "language": "python",
    #             "test_cases": [
    #                 {"input": "5", "expected_output": "10"},
    #                 {"input": "10", "expected_output": "20"}
    #             ],
    #             "time_limit": 1.0,
    #             "memory_limit": 262144
    #         }
    #     }


class TestResult(BaseModel):
    test_number: int
    status: str
    time: float
    memory: int
    stdout: str
    stderr: str
    input_data: str
    expected_output: Optional[str] = None
    passed: Optional[bool] = None
    message: str = ""


class BatchSubmissionResponse(BaseModel):
    total_tests: int
    passed_tests: int
    failed_tests: int
    total_time: float
    average_time: float
    results: List[TestResult]
