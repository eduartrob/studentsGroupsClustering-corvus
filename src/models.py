import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime, TEXT, ARRAY, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)
    profile_picture = Column(TEXT, nullable=True)
    roleId = Column(Integer, ForeignKey("roles.id"), default=1)
    google_refresh_token = Column(TEXT, nullable=True)
    google_access_token = Column(TEXT, nullable=True)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    
    # Campos adicionales para soportar sugerencias y solicitudes
    bio = Column(TEXT, default="")
    tags = Column(ARRAY(String), default=[])
    is_verified = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    team = relationship("Team", back_populates="members", foreign_keys=[team_id])
    requests = relationship("TeamRequest", back_populates="student", cascade="all, delete-orphan")
    role = relationship("Role")

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)


class Team(Base):
    __tablename__ = "teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(TEXT, nullable=True)
    project_title = Column(String(255), default="Sistema de gestión de equipos")
    project_description = Column(TEXT, default="Herramienta colaborativa para conectar estudiantes y optimizar la asignación de proyectos académicos.")
    max_members = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    members = relationship("User", back_populates="team", foreign_keys=[User.team_id])
    social_links = relationship("TeamSocialLink", back_populates="team", cascade="all, delete-orphan")
    requests = relationship("TeamRequest", back_populates="team", cascade="all, delete-orphan")


class TeamSocialLink(Base):
    __tablename__ = "team_social_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String(100), nullable=False)
    url = Column(TEXT, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relación
    team = relationship("Team", back_populates="social_links")


class TeamRequest(Base):
    __tablename__ = "team_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    state = Column(String(50), default="PENDIENTE")  # 'PENDIENTE', 'ACEPTADA', 'RECHAZADA', 'CANCELADA'
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relaciones
    team = relationship("Team", back_populates="requests")
    student = relationship("User", back_populates="requests")


class StudentCourse(Base):
    __tablename__ = "student_courses"

    id = Column(String(255), primary_key=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    course_state = Column(String(50), nullable=True)
    average_grade = Column(Float, default=0.0)
    detected_technologies = Column(ARRAY(String), default=[])
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StudentSubmission(Base):
    __tablename__ = "student_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_name = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    grade = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class StudentDrivePDF(Base):
    __tablename__ = "student_drive_pdfs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    folder = Column(String(255), nullable=True)
    is_ai_generated = Column(Boolean, default=False)
    ai_probability = Column(Float, default=0.0)
    detected_technologies = Column(ARRAY(String), default=[])
    created_at = Column(DateTime, default=datetime.utcnow)


class StudentSkill(Base):
    __tablename__ = "student_skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    skill_name = Column(String(100), nullable=False)
    level = Column(String(50), nullable=False)
    percentage = Column(Float, default=0.0)
    evidence_courses = Column(ARRAY(String), default=[])
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
