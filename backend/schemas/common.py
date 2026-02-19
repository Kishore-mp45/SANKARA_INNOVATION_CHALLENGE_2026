"""Common Schemas"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any, List


class StatusResponse(BaseModel):
    status: str
    message: str
    version: str
    timestamp: datetime
    database_connected: bool
    uptime_seconds: float


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[Any] = None


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int


class SuccessResponse(BaseModel):
    success: bool
    message: str
