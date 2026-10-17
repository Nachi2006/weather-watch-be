from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from db.db import Base

class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="User") 
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Test(Base):
    __tablename__ = "test"
    id = Column(Integer, primary_key=True)
    name = Column(String)

class DisasterModel(Base):
    __tablename__ = "disasters"
    id = Column(String, primary_key=True, index=True)
    type = Column(String)
    location = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    severity = Column(String)
    confidence = Column(Float)
    affectedArea = Column(Float)
    dryArea = Column(Float)
    populationAtRisk = Column(Integer)
    status = Column(String)
    timestamp = Column(DateTime)
    image = Column(String)
    reportedMinutesAgo = Column(Integer, nullable=True)
    roadAccessibility = Column(String, nullable=True)
    rainfall = Column(String, nullable=True)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    waterLevel = Column(String, nullable=True)
    originalImage = Column(String, nullable=True)
    segmentationImage = Column(String, nullable=True)
    overlayImage = Column(String, nullable=True)
    aiSummary = Column(String, nullable=True)

class AlertModel(Base):
    __tablename__ = "alerts"
    id = Column(String, primary_key=True, index=True)
    title = Column(String)
    disasterId = Column(String)
    type = Column(String)
    severity = Column(String)
    location = Column(String)
    affectedArea = Column(Float)
    populationAtRisk = Column(Integer)
    reportedMinutesAgo = Column(Integer)
    acknowledged = Column(Boolean, default=False)

class ReportModel(Base):
    __tablename__ = "reports"
    id = Column(String, primary_key=True, index=True)
    disasterType = Column(String)
    location = Column(String)
    submittedBy = Column(String)
    timeAgo = Column(String)
    status = Column(String)
    severity = Column(String)

class HistoryEntryModel(Base):
    __tablename__ = "history_entries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date)
    disaster = Column(String)
    location = Column(String)
    severity = Column(String)
    affectedArea = Column(Float)
    status = Column(String)

class FacilityModel(Base):
    __tablename__ = "facilities"
    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    type = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)