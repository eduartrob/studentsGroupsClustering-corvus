from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from core.database import get_db
from models.models import User, Team, TeamMember, TeamSocialLink, TeamRequest, UserSkill, Skill
from models.schemas import (
    TeamResponse, TeamUpdateRequest, ProjectResponse, MemberResponse,
    SocialLinkResponse, RequestResponse, RequestCreate, StudentResponse
)
from core.auth import get_current_user


def get_user_team_id(db, user_id):
    tm = db.query(TeamMember).filter(TeamMember.userId == user_id).first()
    return tm.teamId if tm else None

def set_user_team_id(db, user_id, team_id, is_leader=False):
    db.query(TeamMember).filter(TeamMember.userId == user_id).delete()
    if team_id:
        db.add(TeamMember(teamId=team_id, userId=user_id, is_leader=is_leader))
    db.commit()

def is_team_admin(db, team_id, user_id):
    tm = db.query(TeamMember).filter(TeamMember.teamId == team_id, TeamMember.userId == user_id).first()
    return tm.is_leader if tm else False

def get_team_admin_id(db, team_id):
    tm = db.query(TeamMember).filter(TeamMember.teamId == team_id, TeamMember.is_leader == True).first()
    return tm.userId if tm else None

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
    if not get_user_team_id(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario no pertenece a ningún equipo en este momento."
        )

    team = db.query(Team).filter(Team.id == get_user_team_id(db, current_user.id)).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El equipo asociado no existe en el sistema."
        )

    # Cargar integrantes y formatear
    members = db.query(User).filter(User.id.in_(db.query(TeamMember.userId).filter(TeamMember.teamId == team.id))).all()
    
    # Ordenar para que el admin (admin_id) quede primero
    members.sort(key=lambda m: 0 if is_team_admin(db, team.id, m.id) else 1)
    
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
        description=team.project.description if team.project and team.project.description else "",
        project=ProjectResponse(
            title=team.project.name if team.project else "Sin Proyecto",
            description=team.project.description if (team.project and team.project.description) else ""
        ),
        memberCount=len(members),
        maxMembers=team.project.team_size if team.project else 4,
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
    Si el usuario no tiene equipo, lo crea automáticamente.
    """
    if not get_user_team_id(db, current_user.id):
        raise HTTPException(status_code=400, detail="No puedes crear un equipo sin estar asignado a un proyecto. Usa unirse a proyecto primero.")
    else:
        team = db.query(Team).filter(Team.id == get_user_team_id(db, current_user.id)).first()
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El equipo no existe."
            )

        if not is_team_admin(db, team.id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el administrador del equipo puede modificar esta configuración."
            )

        # Actualizar datos básicos
        team.name = update_data.name
        # team.description = update_data.description  # Removing because Team no longer has description
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
    if not get_user_team_id(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No perteneces a ningún equipo."
        )

    old_team_id = get_user_team_id(db, current_user.id)
    set_user_team_id(db, current_user.id, None)
    
    # Check if the user was the admin
    team = db.query(Team).filter(Team.id == old_team_id).first()
    if team and is_team_admin(db, team.id, current_user.id):
        # User is the admin, need to assign new admin or delete team
        remaining_member = db.query(User).filter(User.id.in_(db.query(TeamMember.userId).filter(TeamMember.teamId == old_team_id))).first()
        if remaining_member:
            set_user_team_id(db, remaining_member.id, team.id, is_leader=True)
        else:
            db.delete(team)

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
    if not get_user_team_id(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No perteneces a ningún equipo."
        )

    team = db.query(Team).filter(Team.id == get_user_team_id(db, current_user.id)).first()
    if team and not is_team_admin(db, team.id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el administrador puede expulsar integrantes."
        )

    # Verificar que el usuario a expulsar sea de tu equipo y no seas tú mismo
    if memberId == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes expulsarte a ti mismo del equipo. Usa /leave en su lugar."
        )

    member = db.query(User).filter(User.id == memberId, User.id.in_(db.query(TeamMember.userId).filter(TeamMember.teamId == get_user_team_id(db, current_user.id)))).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El integrante especificado no pertenece a tu equipo."
        )

    # Expulsar al integrante
    set_user_team_id(db, member.id, None)
    db.commit()

    return {"message": "El integrante ha sido removido del equipo"}


# =========================================================================
# 2.2. SOLICITUDES DE INTEGRACIÓN (INVITACIONES)
# =========================================================================

@router.get("/requests", response_model=List[RequestResponse])
def get_requests(
    filter: str = Query(..., description="Filtros válidos: 'recibidas' o 'enviadas'"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene las solicitudes del usuario filtradas por estado.
    """
    query = db.query(TeamRequest)

    if filter == "enviadas":
        if not get_user_team_id(db, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No perteneces a ningún equipo para consultar invitaciones enviadas."
            )
        # Mostrar solicitudes enviadas por este equipo
        requests = query.filter(
            TeamRequest.team_id == get_user_team_id(db, current_user.id),
            TeamRequest.state == "PENDIENTE"
        ).all()

    elif filter == "recibidas":
        # Mostrar solicitudes PENDIENTES donde el usuario sea el destino
        requests = query.filter(
            TeamRequest.student_id == current_user.id,
            TeamRequest.state == "PENDIENTE"
        ).all()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filtro no válido. Usa 'enviadas' o 'recibidas'."
        )

    # Mapeo a respuesta
    response = []
    for r in requests:
        # Si la envié yo, quiero ver a quién se la envié (r.student).
        # Si la recibí yo, quiero ver quién me la envió (el admin del equipo emisor).
        if filter == "recibidas":
            # Consulta directa al equipo por team_id para evitar problemas de
            # lazy loading donde r.team puede ser None en ciertos contextos de sesión
            sender_team = db.query(Team).filter(Team.id == r.team_id).first()
            if sender_team:
                team_admin = db.query(User).filter(User.id == get_team_admin_id(db, sender_team.id)).first()
                target_user = team_admin if team_admin else r.student
            else:
                target_user = r.student
        else:
            target_user = r.student

        response.append(
            RequestResponse(
                id=r.id,
                state=r.state,
                date=r.created_at,
                student=StudentResponse(
                    id=target_user.id,
                    name=target_user.full_name or target_user.username,
                    username=target_user.username,
                    bio=target_user.bio,
                    avatarUrl=target_user.profile_picture,
                    isVerified=target_user.is_verified,
                    tags=target_user.tags
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
    if body.studentId == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes enviarte una invitación a ti mismo."
        )

    # 1. Validar que el emisor pertenezca a un equipo
    if not get_user_team_id(db, current_user.id):
        # Opcional: Podríamos autocrear el equipo aquí si no tiene uno.
        # Por ahora creamos un equipo por defecto para el flujo
        new_team = Team(
            name=f"Equipo de {current_user.full_name or current_user.username}",
            description="Equipo creado automáticamente al enviar invitación.",
        )
        db.add(new_team)
        db.commit()
        db.refresh(new_team)
        set_user_team_id(db, current_user.id, new_team.id, is_leader=True)
        db.commit()

    team = db.query(Team).filter(Team.id == get_user_team_id(db, current_user.id)).first()

    # 2. Validar que el equipo no esté lleno
    members_count = db.query(User).filter(User.id.in_(db.query(TeamMember.userId).filter(TeamMember.teamId == team.id))).count()
    if members_count >= (team.project.team_size if team.project else 4):
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

    # 4. Evitar invitaciones duplicadas pendientes
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

    # 5. Crear la solicitud
    new_request = TeamRequest(
        team_id=team.id,
        student_id=body.studentId,
        state="PENDIENTE"
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    # 6. Notificar por FCM
    import asyncio
    from services.rabbitmq_service import publish_push_notification
    try:
        asyncio.run(publish_push_notification(
            user_id=str(student.id),
            title="Nueva invitación de equipo",
            body=f"{current_user.full_name or current_user.username} te ha invitado a su equipo.",
            data={
                "type": "TEAM_INVITE", 
                "requestId": str(new_request.id),
                "authorName": current_user.full_name or current_user.username,
                "authorPhotoUrl": current_user.profile_picture
            }
        ))
    except Exception as e:
        print(f"Error sending push notification: {e}")

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
    if request.team_id != get_user_team_id(db, current_user.id) and request.student_id != current_user.id:
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
    # Primero buscar la solicitud sin filtrar por estado para dar mejor error
    raw_request = db.query(TeamRequest).filter(
        TeamRequest.id == requestId
    ).first()
    
    if not raw_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La invitación no existe. Puede que haya sido cancelada o que el ID sea incorrecto."
        )
    
    if raw_request.state != "PENDIENTE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Esta invitación ya fue procesada (estado actual: {raw_request.state})."
        )
    
    request = raw_request

    # Asegurar que sea el estudiante correcto quien acepta
    if request.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No eres el destinatario de esta invitación."
        )

    # Validar que el equipo emisor no se haya llenado mientras tanto
    sender_team = db.query(Team).filter(Team.id == request.team_id).first()
    sender_members_count = db.query(User).filter(User.id.in_(db.query(TeamMember.userId).filter(TeamMember.teamId == sender_team.id))).count()

    # Averiguar estado del equipo receptor (el current_user)
    receiver_team_id = get_user_team_id(db, current_user.id)
    receiver_members_count = 0
    receiver_team = None
    if receiver_team_id:
        receiver_team = db.query(Team).filter(Team.id == receiver_team_id).first()
        receiver_members_count = db.query(User).filter(User.id.in_(db.query(TeamMember.userId).filter(TeamMember.teamId == receiver_team_id))).count()

    # ========================================================
    # LÓGICA BIDIRECCIONAL BASADA EN TAMAÑO DE EQUIPO
    # ========================================================
    # Si el Receptor ya tiene un equipo (2+ personas) y el Emisor está solo (1 persona):
    if receiver_members_count > 1 and sender_members_count == 1:
        # El Emisor (Sender) se unirá al equipo del Receptor.
        # Validar si el equipo del Receptor tiene cupo para el Emisor
        if receiver_members_count >= (receiver_team.project.team_size if receiver_team.project else 4):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tu equipo ya se encuentra lleno, por lo que esta persona no puede unirse a tu equipo."
            )

        # El Emisor es el único miembro de su equipo (que es él mismo, el admin_id).
        sender_user = db.query(User).filter(User.id == get_team_admin_id(db, sender_team.id)).first()
        
        # El Emisor se une al equipo del Receptor
        set_user_team_id(db, sender_user.id, receiver_team.id)
        
        # El equipo del Emisor queda vacío, lo borramos.
        db.delete(sender_team)
        
        # Actualizamos la solicitud a ACEPTADA
        request.state = "ACEPTADA"
        
        # El Receptor NO cambia de equipo. Se queda en su propio equipo.
        target_team_name = receiver_team.name
        user_to_notify_id = sender_user.id
        notification_title = "¡Te has unido a un equipo!"
        notification_body = f"{current_user.full_name or current_user.username} aceptó tu invitación y te ha integrado a su equipo."
        
    else:
        # LÓGICA ORIGINAL: El Receptor se une al equipo del Emisor.
        if sender_members_count >= (sender_team.project.team_size if sender_team.project else 4):
            # Cancelar esta solicitud automáticamente
            request.state = "CANCELADA"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La invitación ya no es válida porque el equipo del emisor se encuentra lleno."
            )
            
        # Si el Receptor tenía un equipo anterior, debe abandonarlo.
        if receiver_team_id and receiver_team_id != request.team_id:
            old_team = receiver_team
            if old_team and old_is_team_admin(db, team.id, current_user.id):
                remaining_member = db.query(User).filter(User.id.in_(db.query(TeamMember.userId).filter(TeamMember.teamId == old_team.id)), User.id != current_user.id).first()
                if remaining_member:
                    old_set_user_team_id(db, remaining_member.id, team.id, is_leader=True)
                else:
                    db.delete(old_team)
                    
        # El Receptor se une al equipo del Emisor
        set_user_team_id(db, current_user.id, request.team_id)
        request.state = "ACEPTADA"
        
        target_team_name = sender_team.name
        user_to_notify_id = get_team_admin_id(db, sender_team.id)
        notification_title = "¡Nuevo miembro en tu equipo!"
        notification_body = f"{current_user.full_name or current_user.username} ha aceptado tu invitación."

    # Cancelar cualquier otra solicitud pendiente que tuviese este estudiante
    db.query(TeamRequest).filter(
        TeamRequest.student_id == current_user.id,
        TeamRequest.state == "PENDIENTE",
        TeamRequest.id != request.id
    ).delete()
    
    db.commit()

    # Notificar al usuario afectado en tiempo real
    import asyncio
    from services.rabbitmq_service import publish_push_notification
    try:
        asyncio.run(publish_push_notification(
            user_id=str(user_to_notify_id),
            title=notification_title,
            body=notification_body,
            data={
                "type": "team_accept",
                "authorName": current_user.full_name or current_user.username,
                "authorPhotoUrl": current_user.profile_picture
            }
        ))
    except Exception as e:
        print(f"Error publishing accept notification: {e}")

    return {"message": f"Operación exitosa con el equipo '{target_team_name}'."}


# =========================================================================
# 2.3. SUGERENCIAS DE CANDIDATOS
# =========================================================================



@router.get("/suggestions", response_model=List[StudentResponse])
def get_suggestions(
    skill: Optional[str] = Query(None, description="Filtro opcional por tag o habilidad"),
    search: Optional[str] = Query(None, description="Filtro opcional por nombre o usuario"),
    show_all: bool = Query(False, description="Si es True, ignora el modelo de clustering y muestra a todos"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Obtener los IDs excluidos
    excluded_ids = [current_user.id]
    
    # Excluir a cualquiera a quien YO (mi equipo) le haya mandado solicitud
    if get_user_team_id(db, current_user.id):
        all_team_invites = db.query(TeamRequest).filter(
            TeamRequest.team_id == get_user_team_id(db, current_user.id)
        ).all()
        for invite in all_team_invites:
            if invite.student_id not in excluded_ids:
                excluded_ids.append(invite.student_id)
            
        # Excluir también a los que YA ESTÁN en mi equipo
        team_members = db.query(User.id).filter(User.id.in_(db.query(TeamMember.userId).filter(TeamMember.teamId == get_user_team_id(db, current_user.id)))).all()
        for member in team_members:
            if member[0] not in excluded_ids:
                excluded_ids.append(member[0])

    # Excluir también a los admins de equipos que ME hayan invitado a MÍ
    # (si alguien ya te mandó invitación, no debe seguir saliendo en tus sugerencias)
    incoming_requests = db.query(TeamRequest).filter(
        TeamRequest.student_id == current_user.id,
        TeamRequest.state == "PENDIENTE"
    ).all()
    for incoming in incoming_requests:
        # Excluir al admin del equipo que me invitó
        team_that_invited = db.query(Team).filter(Team.id == incoming.team_id).first()
        if team_that_invited and get_team_admin_id(db, team_that_invited.id) not in excluded_ids:
            excluded_ids.append(get_team_admin_id(db, team_that_invited.id))
        # Excluir también a todos los miembros de ese equipo
        members_of_inviting_team = db.query(User.id).filter(User.id.in_(db.query(TeamMember.userId).filter(TeamMember.teamId == incoming.team_id))).all()
        for m in members_of_inviting_team:
            if m[0] not in excluded_ids:
                excluded_ids.append(m[0])

    # 2. Filtrar alumnos sin equipo (ALUMNO)
    from models.models import Role, Career
    
    # Lógica para agrupar carreras similares (ej. "ingeniería en software" y "ingeniería en desarrollo de software")
    current_career = db.query(Career).filter(Career.id == current_user.careerId).first()
    if current_career and "SOFTWARE" in current_career.name.upper():
        similar_careers = db.query(Career.id).filter(Career.name.ilike("%SOFTWARE%")).all()
        career_ids = [c[0] for c in similar_careers]
        career_filter = User.careerId.in_(career_ids)
    else:
        career_filter = User.careerId == current_user.careerId
        
    filters = [
        Role.name == "ALUMNO",
        User.universityId == current_user.universityId,
        career_filter,
        User.semester == current_user.semester,
        ~User.id.in_(excluded_ids)
    ]
    
    if search:
        filters.append(
            or_(
                User.full_name.ilike(f"%{search}%"),
                User.username.ilike(f"%{search}%")
            )
        )
    
    # ML Feature: Penalizamos a los del mismo cluster en la etapa de puntuación en lugar de excluirlos
    # Así, los amigos (del mismo cluster) seguirán apareciendo en la lista general.
    # Eliminamos el hard filter de cluster_id aquí.
        
    query = db.query(User).join(Role, User.roleId == Role.id).filter(*filters)

    all_students = query.all()

    # Filtrar eficientemente estudiantes cuyo equipo ya está lleno
    # Contamos cuántos miembros hay por cada equipo
    from sqlalchemy import func
    team_sizes = db.query(TeamMember.teamId, func.count(TeamMember.userId)).group_by(TeamMember.teamId).all()
    team_size_map = {t_id: count for t_id, count in team_sizes}
    
    # Obtenemos el max_members de los equipos
    teams = db.query(Team).all()
    team_max_map = {t.id: (t.project.team_size if t.project else 4) for t in teams}

    # Convertimos los excluded_ids a string para una comprobación robusta en Python
    excluded_ids_str = {str(eid) for eid in excluded_ids}

    students = []
    for s in all_students:
        # Validación extra de seguridad: no incluir a nadie que esté en excluded_ids
        if str(s.id) in excluded_ids_str:
            continue
            
        if get_user_team_id(db, s.id):
            # Validacion extra: si está en MI equipo, omitir (aunque ya debió filtrarse arriba)
            if get_user_team_id(db, current_user.id) and str(get_user_team_id(db, s.id)) == str(get_user_team_id(db, current_user.id)):
                continue
                
            current_size = team_size_map.get(get_user_team_id(db, s.id), 0)
            max_size = team_max_map.get(get_user_team_id(db, s.id), 3)
            if current_size >= max_size:
                continue # Saltar estudiante si su equipo ya está lleno
        students.append(s)
    
    # 3. Minería de datos: Recomendar equipos Full Stack
    # Obtenemos las habilidades del usuario actual
    my_skills_db = db.query(UserSkill).filter(UserSkill.userId == current_user.id).all()
    my_skill_ids = {us.skillId for us in my_skills_db}
    my_tags = [db.query(Skill).filter(Skill.id == sid).first().name for sid in my_skill_ids if db.query(Skill).filter(Skill.id == sid).first()]

    # Definimos habilidades core de un equipo de desarrollo (Full Stack / Tech)
    tech_keywords = {
        'react', 'angular', 'vue', 'html', 'css', 'javascript', 'typescript', 'frontend', 'front',
        'node', 'python', 'java', 'go', 'php', 'c#', 'sql', 'mysql', 'postgres', 'mongodb', 'backend', 'back', 'api',
        'docker', 'aws', 'cloud', 'devops', 'git', 'linux',
        'flutter', 'mobile', 'android', 'ios', 'kotlin', 'swift',
        'ui', 'ux', 'diseño', 'figma', 'machine learning', 'ai', 'datos', 'data', 'full stack', 'fullstack'
    }

    # Calculamos el score de complementariedad para cada estudiante
    student_scores = []
    for s in students:
        s_skills = db.query(UserSkill).filter(UserSkill.userId == s.id).all()
        s_skill_ids = {us.skillId for us in s_skills}
        s_tags = [db.query(Skill).filter(Skill.id == sid).first().name for sid in s_skill_ids if db.query(Skill).filter(Skill.id == sid).first()]
        
        # Filtro opcional por skill
        if skill and skill.lower() != 'all skills' and not any(skill.lower() in t.lower() for t in s_tags):
            continue
            
        score = 0
        if not show_all:
            # Puntuación Inteligente (Full Stack Oriented)
            for tag in s_tags:
                # ¿El estudiante tiene esta habilidad y YO NO? (Complementario)
                if not any(tag.lower() == my_tag.lower() for my_tag in my_tags):
                    is_tech = any(kw in tag.lower() for kw in tech_keywords)
                    if is_tech:
                        score += 5.0 # Alto valor a habilidades Tech complementarias
                    else:
                        score += 0.5 # Poco valor a habilidades raras/random
                else:
                    # Si tenemos la misma habilidad, sumamos un poco por afinidad
                    score += 1.0

            # ML Feature: Si están en el mismo cluster, los penalizamos en puntaje para que 
            # las sugerencias opuestas queden arriba, pero los amigos sigan apareciendo abajo.
            if current_user.cluster_id is not None and s.cluster_id == current_user.cluster_id:
                score -= 20.0
        
        student_scores.append((score, s, s_tags))

    # Ordenar por mayor complementariedad, luego por total de habilidades (para desempatar)
    student_scores.sort(key=lambda x: (x[0], len(x[2])), reverse=True)
    
    # Tomar todos los estudiantes ordenados
    top_students = student_scores

    response = []
    for score, s, s_tags in top_students:
        response.append(
            StudentResponse(
                id=s.id,
                name=s.full_name or s.username,
                username=s.username,
                bio=s.bio,
                avatarUrl=s.profile_picture,
                isVerified=s.is_verified,
                tags=s_tags
            )
        )
    return response

@router.get("/students", response_model=List[StudentResponse])
def get_student_directory(
    skill: Optional[str] = Query(None, description="Filtro opcional por tag o habilidad"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Directorio de alumnos con filtro estricto por universidad, carrera y cuatrimestre.
    Se excluyen alumnos que ya tienen equipo y al propio usuario.
    """
    from models.models import Role, UserSkill
    
    query = db.query(User).join(Role, User.roleId == Role.id).filter(
        ~User.id.in_(db.query(TeamMember.userId)),
        Role.name == "ALUMNO",
        User.id != current_user.id,
        User.universityId == current_user.universityId,
        User.careerId == current_user.careerId,
        User.semester == current_user.semester
    )
    
    students = query.all()
    
    response = []
    for s in students:
        s_skills_db = db.query(UserSkill).filter(UserSkill.userId == s.id).all()
        s_tags = [sk.skill.name for sk in s_skills_db if sk.skill]
        
        if skill:
            skill_lower = skill.lower()
            has_skill = any(skill_lower in t.lower() for t in s_tags)
            if not has_skill:
                continue

        response.append(
            StudentResponse(
                id=s.id,
                name=s.full_name or s.username,
                username=s.username,
                bio=s.bio,
                avatarUrl=s.profile_picture,
                isVerified=s.is_verified,
                tags=s_tags
            )
        )
        
    return response

# =========================================================================
# 5. PROFESOR: DIRECTORIO
# =========================================================================

@router.get("/prof/directory")
def get_prof_directory(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Directorio de equipos y alumnos sin equipo para el dashboard del profesor.
    Filtra por la carrera y universidad del profesor.
    """
    from models.schemas import ProfDirectoryResponse
    from models.models import Role, UserSkill

    if current_user.role.name not in ["PROFESOR", "DOCENTE"]:
        raise HTTPException(status_code=403, detail="No autorizado")

    # Alumnos de la misma carrera
    students_query = db.query(User).join(Role, User.roleId == Role.id).filter(
        Role.name == "ALUMNO",
        User.careerId == current_user.careerId,
        User.universityId == current_user.universityId
    ).all()

    teams_dict = {}
    students_without_team = []

    for s in students_query:
        s_skills_db = db.query(UserSkill).filter(UserSkill.userId == s.id).all()
        s_tags = [sk.skill.name for sk in s_skills_db if sk.skill]

        user_team_member = db.query(TeamMember).filter(TeamMember.userId == s.id).first()
        team_id = user_team_member.teamId if user_team_member else None

        if team_id:
            if team_id not in teams_dict:
                team = db.query(Team).filter(Team.id == team_id).first()
                if team:
                    social_links = db.query(TeamSocialLink).filter(TeamSocialLink.team_id == team.id).all()
                    
                    team_memberships = db.query(TeamMember).filter(TeamMember.teamId == team.id).all()
                    members = [tm.user for tm in team_memberships if tm.user]
                    members_response = [
                        MemberResponse(
                            id=m.id,
                            name=m.full_name or m.username,
                            email=m.email,
                            avatarUrl=m.profile_picture,
                            isMe=False
                        ) for m in members
                    ]
                    
                    teams_dict[team_id] = TeamResponse(
                        id=team.id,
                        name=team.name or "Equipo Sin Nombre",
                        description=team.project.description if (team.project and team.project.description) else "",
                        project=ProjectResponse(
                            title=team.project.name if team.project else "Sin Proyecto", 
                            description=team.project.description if (team.project and team.project.description) else ""
                        ),
                        memberCount=len(members),
                        maxMembers=team.project.team_size if team.project else 4,
                        socialLinks=social_links,
                        members=members_response
                    )
        else:
            students_without_team.append(StudentResponse(
                id=s.id,
                name=s.full_name or s.username,
                username=s.username,
                bio=s.bio,
                avatarUrl=s.profile_picture,
                isVerified=s.is_verified,
                tags=s_tags
            ))

    return {
        "teams": list(teams_dict.values()),
        "studentsWithoutTeam": students_without_team
    }
