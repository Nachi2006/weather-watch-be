from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional
from datetime import datetime, date
from enum import Enum

class LabelData(BaseModel):
    labels: List[str]
    data: List[float]

class DashboardSummary(BaseModel):
    activeDisasters: int
    critical: int
    high: int
    medium: int
    populationAtRisk: int

class Analytics(BaseModel):
    disastersByType: LabelData
    severityDistribution: LabelData
    incidentsOverTime: LabelData
    populationAtRisk: LabelData
    responseStatus: LabelData

class Facility(BaseModel):
    id: str
    name: str
    type: str # Hospital, Shelter, Rescue Center
    latitude: float
    longitude: float

class HistoryEntry(BaseModel):
    date: date
    disaster: str
    location: str
    severity: str
    affectedArea: float
    status: str

class Report(BaseModel):
    id: str
    disasterType: str
    location: str
    submittedBy: str
    timeAgo: str
    status: str
    severity: str

class Alert(BaseModel):
    id: str
    title: str
    disasterId: str
    type: str
    severity: str
    location: str
    affectedArea: float
    populationAtRisk: int
    reportedMinutesAgo: int
    acknowledged: bool = False

class Disaster(BaseModel):
    id: str
    type: str
    location: str
    latitude: float
    longitude: float
    severity: str
    confidence: float
    affectedArea: float
    dryArea: float
    populationAtRisk: int
    status: str
    timestamp: datetime
    image: str
    reportedMinutesAgo: Optional[int] = None
    roadAccessibility: Optional[str] = None
    rainfall: Optional[str] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    waterLevel: Optional[str] = None
    originalImage: Optional[str] = None
    segmentationImage: Optional[str] = None
    overlayImage: Optional[str] = None
    aiSummary: Optional[str] = None
    recommendations: Optional[List[str]] = None

class Error(BaseModel):
    detail: str

# ── Request / Create models ──────────────────────────────────────────────────

class DisasterCreate(BaseModel):
    id: Optional[str] = None          # auto-generated if omitted
    type: str
    location: str
    latitude: float
    longitude: float
    severity: str
    confidence: float = 0.0
    affectedArea: float = 0.0
    dryArea: float = 0.0
    populationAtRisk: int = 0
    status: str = "Active"
    image: str = ""
    reportedMinutesAgo: Optional[int] = None
    roadAccessibility: Optional[str] = None
    rainfall: Optional[str] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    waterLevel: Optional[str] = None
    originalImage: Optional[str] = None
    segmentationImage: Optional[str] = None
    overlayImage: Optional[str] = None
    aiSummary: Optional[str] = None
    recommendations: Optional[List[str]] = None

class DisasterStatusUpdate(BaseModel):
    status: str

class AlertCreate(BaseModel):
    id: Optional[str] = None
    title: str
    disasterId: str
    type: str
    severity: str
    location: str
    affectedArea: float = 0.0
    populationAtRisk: int = 0
    reportedMinutesAgo: int = 0
    acknowledged: bool = False

class ReportCreate(BaseModel):
    id: Optional[str] = None
    disasterType: str
    location: str
    submittedBy: str = "Anonymous"
    timeAgo: str = "just now"
    status: str = "Pending"
    severity: str

class FacilityCreate(BaseModel):
    id: Optional[str] = None
    name: str
    type: str
    latitude: float
    longitude: float

# ── Auth models ──────────────────────────────────────────────────────────────

class UserRole(str, Enum):
    ADMIN = "Admin"
    RESCUE_TEAM = "Rescue Team"
    USER = "User"

class UserRegister(BaseModel):
    username: str
    email: str
    password: str
    role: Optional[str] = "User"
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes in seconds
    role: str
    username: str
    email: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    full_name: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

