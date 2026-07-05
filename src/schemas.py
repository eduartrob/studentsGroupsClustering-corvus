from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime

# --- Enlaces Sociales ---
class SocialLinkCreate(BaseModel):
    platform: str
    url: str

    class Config:
        orm_mode = True

class SocialLinkResponse(BaseModel):
    id: UUID
    platform: str
    url: str

    class Config:
        orm_mode = True


# --- Proyecto del Equipo ---
class ProjectResponse(BaseModel):
    title: str
    description: str

    class Config:
        orm_mode = True


# --- Miembro de Equipo ---
class MemberResponse(BaseModel):
    id: UUID
    name: Optional[str] = Field(None, alias="name")
    email: str
    avatarUrl: Optional[str] = Field(None, alias="avatarUrl")
    isMe: bool

    class Config:
        orm_mode = True
        allow_population_by_field_name = True


# --- Equipo Completo ---
class TeamResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    project: ProjectResponse
    memberCount: int
    maxMembers: int
    socialLinks: List[SocialLinkResponse]
    members: List[MemberResponse]

    class Config:
        orm_mode = True


# --- Edición del Equipo ---
class TeamUpdateRequest(BaseModel):
    name: str
    description: str
    socialLinks: List[SocialLinkCreate]


# --- Estudiante (Sugerencias e Invitados) ---
class StudentResponse(BaseModel):
    id: UUID
    name: Optional[str] = None
    username: str
    bio: Optional[str] = ""
    avatarUrl: Optional[str] = None
    isVerified: bool = False
    tags: List[str] = []

    class Config:
        orm_mode = True


# --- Solicitud de Integración ---
class RequestResponse(BaseModel):
    id: UUID
    state: str
    date: datetime = Field(..., alias="date")
    student: StudentResponse

    class Config:
        orm_mode = True
        allow_population_by_field_name = True


# --- Creación de Solicitud ---
class RequestCreate(BaseModel):
    studentId: UUID
