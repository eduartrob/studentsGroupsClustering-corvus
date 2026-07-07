from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from ..database import get_db
from ..models import User, Team, TeamSocialLink, TeamRequest
from ..schemas import (
    TeamResponse, TeamUpdateRequest, ProjectResponse, MemberResponse,
    SocialLinkResponse, RequestResponse, RequestCreate, StudentResponse
)
from ..auth import get_current_user

router = APIRouter(prefix="/teams", tags=["Teams"])


# =========================================================================
# 2.1. GESTIÓN DE EQUIPO
# =========================================================================

@router.get("/my-team", response_model=TeamResponse)
def get_my_team(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene los detalles del equipo del usuario autenticado (integrantes, proyecto y redes).
    """
    if not current_user.team_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario no pertenece a ningún equipo en este momento."
        )

    team = db.query(Team).filter(Team.id == current_user.team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El equipo asociado no existe en el sistema."
        )

    # Cargar integrantes y formatear
    members = db.query(User).filter(User.team_id == team.id).all()
    members_response = []
    for m in members:
        members_response.append(
            MemberResponse(
                id=m.id,
                name=m.full_name or m.username,
                email=m.email,
                avatarUrl=m.profile_picture,
                isMe=(m.id == current_user.id)
            )
        )

    # Cargar enlaces de redes sociales
    social_links = db.query(TeamSocialLink).filter(TeamSocialLink.team_id == team.id).all()

    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        project=ProjectResponse(
            title=team.project_title,
            description=team.project_description
        ),
        memberCount=len(members),
        maxMembers=team.max_members,
        socialLinks=social_links,
        members=members_response
    )


@router.put("/my-team", response_model=TeamResponse)
def update_my_team(
    update_data: TeamUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Actualiza el nombre, descripción y enlaces sociales del equipo actual del usuario.
    """
    if not current_user.team_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No perteneces a ningún equipo, por lo que no puedes editar sus datos."
        )

    team = db.query(Team).filter(Team.id == current_user.team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El equipo no existe."
        )

    # Actualizar datos básicos
    team.name = update_data.name
    team.description = update_data.description
    team.updated_at = datetime.utcnow()

    # Reemplazar enlaces de redes sociales (eliminar antiguos y agregar nuevos)
    db.query(TeamSocialLink).filter(TeamSocialLink.team_id == team.id).delete()
    for link_in in update_data.socialLinks:
        new_link = TeamSocialLink(
            team_id=team.id,
            platform=link_in.platform,
            url=link_in.url
        )
        db.add(new_link)

    db.commit()
    db.refresh(team)

    # Retornar equipo actualizado
    return get_my_team(current_user=current_user, db=db)


@router.post("/my-team/leave")
def leave_team(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    El usuario decide abandonar su equipo actual.
    """
    if not current_user.team_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No perteneces a ningún equipo."
        )

    old_team_id = current_user.team_id
    current_user.team_id = None
    db.commit()

    # Si el equipo se queda sin integrantes, se elimina automáticamente
    active_members_count = db.query(User).filter(User.team_id == old_team_id).count()
    if active_members_count == 0:
        db.query(Team).filter(Team.id == old_team_id).delete()
        db.commit()

    return {"message": "Has salido del equipo con éxito"}


@router.delete("/my-team/members/{memberId}")
def remove_member(
    memberId: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remueve a un integrante específico de tu equipo (modelo democrático).
    """
    if not current_user.team_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No perteneces a ningún equipo."
        )

    # Verificar que el usuario a expulsar sea de tu equipo y no seas tú mismo
    if memberId == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes expulsarte a ti mismo del equipo. Usa /leave en su lugar."
        )

    member = db.query(User).filter(User.id == memberId, User.team_id == current_user.team_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El integrante especificado no pertenece a tu equipo."
        )

    # Expulsar al integrante
    member.team_id = None
    db.commit()

    return {"message": "El integrante ha sido removido del equipo"}


# =========================================================================
# 2.2. SOLICITUDES DE INTEGRACIÓN (INVITACIONES)
# =========================================================================

@router.get("/requests", response_model=List[RequestResponse])
def get_requests(
    filter: str = Query(..., description="Filtros válidos: 'aceptadas' o 'enviadas'"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene las solicitudes del usuario filtradas por estado.
    """
    query = db.query(TeamRequest)

    if filter == "enviadas":
        if not current_user.team_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No perteneces a ningún equipo para consultar invitaciones enviadas."
            )
        # Mostrar solicitudes enviadas por este equipo
        requests = query.filter(
            TeamRequest.team_id == current_user.team_id,
            TeamRequest.state == "PENDIENTE"
        ).all()

    elif filter == "aceptadas":
        # Mostrar solicitudes que ya se aceptaron asociadas a este usuario o su equipo
        if current_user.team_id:
            requests = query.filter(
                TeamRequest.team_id == current_user.team_id,
                TeamRequest.state == "ACEPTADA"
            ).all()
        else:
            requests = query.filter(
                TeamRequest.student_id == current_user.id,
                TeamRequest.state == "ACEPTADA"
            ).all()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filtro no válido. Usa 'enviadas' o 'aceptadas'."
        )

    # Mapeo a respuesta
    response = []
    for r in requests:
        response.append(
            RequestResponse(
                id=r.id,
                state=r.state,
                date=r.created_at,
                student=StudentResponse(
                    id=r.student.id,
                    name=r.student.full_name or r.student.username,
                    username=r.student.username,
                    bio=r.student.bio,
                    avatarUrl=r.student.profile_picture,
                    isVerified=r.student.is_verified,
                    tags=r.student.tags
                )
            )
        )
    return response


@router.post("/requests", response_model=RequestResponse, status_code=status.HTTP_201_CREATED)
def invite_student(
    body: RequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Envía una invitación a un alumno candidato.
    """
    # 1. Validar que el emisor pertenezca a un equipo
    if not current_user.team_id:
        # Opcional: Podríamos autocrear el equipo aquí si no tiene uno.
        # Por ahora creamos un equipo por defecto para el flujo
        new_team = Team(
            name=f"Equipo de {current_user.full_name or current_user.username}",
            description="Equipo creado automáticamente al enviar invitación."
        )
        db.add(new_team)
        db.commit()
        db.refresh(new_team)
        current_user.team_id = new_team.id
        db.commit()

    team = db.query(Team).filter(Team.id == current_user.team_id).first()

    # 2. Validar que el equipo no esté lleno
    members_count = db.query(User).filter(User.team_id == team.id).count()
    if members_count >= team.max_members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tu equipo ya tiene el cupo máximo de integrantes."
        )

    # 3. Validar la existencia del alumno a invitar
    student = db.query(User).filter(User.id == body.studentId).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El alumno que deseas invitar no existe."
        )

    # 4. Validar que el alumno no tenga ya un equipo
    if student.team_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El estudiante seleccionado ya forma parte de otro equipo."
        )

    # 5. Evitar invitaciones duplicadas pendientes
    existing_request = db.query(TeamRequest).filter(
        TeamRequest.team_id == team.id,
        TeamRequest.student_id == body.studentId,
        TeamRequest.state == "PENDIENTE"
    ).first()
    if existing_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una invitación pendiente enviada a este estudiante."
        )

    # 6. Crear la solicitud
    new_request = TeamRequest(
        team_id=team.id,
        student_id=body.studentId,
        state="PENDIENTE"
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    return RequestResponse(
        id=new_request.id,
        state=new_request.state,
        date=new_request.created_at,
        student=StudentResponse(
            id=student.id,
            name=student.full_name or student.username,
            username=student.username,
            bio=student.bio,
            avatarUrl=student.profile_picture,
            isVerified=student.is_verified,
            tags=student.tags
        )
    )


@router.delete("/requests/{requestId}")
def cancel_request(
    requestId: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancela o elimina una invitación pendiente enviada.
    """
    request = db.query(TeamRequest).filter(TeamRequest.id == requestId).first()
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La solicitud no existe."
        )

    # Solo el equipo emisor o el alumno receptor de la solicitud pueden eliminarla/rechazarla
    if request.team_id != current_user.team_id and request.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para cancelar o rechazar esta solicitud."
        )

    # Eliminar físicamente para liberar al candidato de la lista local
    db.delete(request)
    db.commit()

    return {"message": "Solicitud cancelada con éxito"}


# =========================================================================
# ENDPOINTS ADICIONALES DE ACEPTACIÓN / RECHAZO (FLUJO ESTUDIANTE)
# =========================================================================

@router.post("/requests/{requestId}/accept")
def accept_request(
    requestId: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Permite al estudiante receptor aceptar la invitación de integración a un equipo.
    """
    request = db.query(TeamRequest).filter(
        TeamRequest.id == requestId,
        TeamRequest.state == "PENDIENTE"
    ).first()
    
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La invitación no existe o ya no está pendiente."
        )

    # Asegurar que sea el estudiante correcto quien acepta
    if request.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No eres el destinatario de esta invitación."
        )

    # Validar que el equipo emisor no se haya llenado mientras tanto
    team = db.query(Team).filter(Team.id == request.team_id).first()
    members_count = db.query(User).filter(User.team_id == team.id).count()
    if members_count >= team.max_members:
        # Cancelar esta solicitud automáticamente
        request.state = "CANCELADA"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La invitación ya no es válida porque el equipo se encuentra lleno."
        )

    # Actualizar estado de la solicitud y unir al estudiante al equipo
    request.state = "ACEPTADA"
    current_user.team_id = request.team_id
    db.commit()

    # Cancelar cualquier otra solicitud pendiente que tuviese este estudiante
    db.query(TeamRequest).filter(
        TeamRequest.student_id == current_user.id,
        TeamRequest.state == "PENDIENTE"
    ).delete()
    db.commit()

    return {"message": f"Te has unido al equipo '{team.name}' exitosamente."}


# =========================================================================
# 2.3. SUGERENCIAS DE CANDIDATOS
# =========================================================================

@router.get("/suggestions", response_model=List[StudentResponse])
def get_suggestions(
    skill: Optional[str] = Query(None, description="Filtro opcional por tag o habilidad"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene una lista de estudiantes candidatos (sin equipo, excluyendo el usuario actual
    y alumnos que ya tengan invitaciones pendientes enviadas por el equipo del usuario).
    """
    # 1. Obtener los IDs de alumnos que ya tienen invitación pendiente enviada por este equipo
    excluded_ids = [current_user.id]
    
    if current_user.team_id:
        pending_invites = db.query(TeamRequest).filter(
            TeamRequest.team_id == current_user.team_id,
            TeamRequest.state == "PENDIENTE"
        ).all()
        for invite in pending_invites:
            excluded_ids.append(invite.student_id)

    # 2. Filtrar alumnos sin equipo y que no estén excluidos (SOLO ROL STUDENT = 3)
    query = db.query(User).filter(
        User.team_id == None,
        User.roleId == 3,
        ~User.id.in_(excluded_ids)
    )

    # 3. Filtrar por habilidad/skill si se solicita (búsqueda case-insensitive en el array de tags)
    if skill:
        query = query.filter(func.array_to_string(User.tags, ',').ilike(f"%{skill}%"))

    students = query.limit(20).all()

    # Mapeo a respuesta
    response = []
    for s in students:
        response.append(
            StudentResponse(
                id=s.id,
                name=s.full_name or s.username,
                username=s.username,
                bio=s.bio,
                avatarUrl=s.profile_picture,
                isVerified=s.is_verified,
                tags=s.tags
            )
        )
    return response
