import re

with open("src/routers/teams.py", "r") as f:
    content = f.read()

# Add get_my_profile_complete and modify get_suggestions

replacement = """
from src.models import UserSkill, Skill

@router.get("/mi-perfil/completo")
def perfil_completo(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Fetch user skills
    user_skills = db.query(UserSkill).filter(UserSkill.userId == current_user.id).all()
    habilidades = []
    for us in user_skills:
        skill = db.query(Skill).filter(Skill.id == us.skillId).first()
        if skill:
            habilidades.append({
                "habilidad": skill.name,
                "nivel": "Intermedio",
                "porcentaje": 100,
                "materias": []
            })
    
    return {
        "status": "completed",
        "alumno": current_user.email,
        "tiempo_ejecucion": "0.0s",
        "resumen": {
            "total_materias": 0,
            "materias_relevantes": 0,
            "total_tareas": 0,
            "total_pdfs_en_drive": 0,
            "pdfs_analizados": 0,
            "documentos_con_ia": 0,
            "habilidades_detectadas": len(habilidades),
        },
        "habilidades": habilidades,
        "materias": [],
        "documentos_con_ia": [],
    }

@router.get("/suggestions", response_model=List[StudentResponse])
def get_suggestions(
    skill: Optional[str] = Query(None, description="Filtro opcional por tag o habilidad"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Obtener los IDs excluidos
    excluded_ids = [current_user.id]
    if current_user.team_id:
        pending_invites = db.query(TeamRequest).filter(
            TeamRequest.team_id == current_user.team_id,
            TeamRequest.state == "PENDIENTE"
        ).all()
        for invite in pending_invites:
            excluded_ids.append(invite.student_id)

    # 2. Filtrar alumnos sin equipo (ALUMNO)
    from src.models import Role
    query = db.query(User).join(Role, User.roleId == Role.id).filter(
        User.team_id == None,
        Role.name == "ALUMNO",
        ~User.id.in_(excluded_ids)
    )

    students = query.all()
    
    # 3. Minería de datos: Recomendar equipos Full Stack
    # Obtenemos las habilidades del usuario actual
    my_skills_db = db.query(UserSkill).filter(UserSkill.userId == current_user.id).all()
    my_skill_ids = {us.skillId for us in my_skills_db}

    # Calculamos el score de complementariedad para cada estudiante
    student_scores = []
    for s in students:
        s_skills = db.query(UserSkill).filter(UserSkill.userId == s.id).all()
        s_skill_ids = {us.skillId for us in s_skills}
        s_tags = [db.query(Skill).filter(Skill.id == sid).first().name for sid in s_skill_ids if db.query(Skill).filter(Skill.id == sid).first()]
        
        # Filtro opcional
        if skill and not any(skill.lower() in t.lower() for t in s_tags):
            continue
            
        # Distancia/Complementariedad: Cuantas habilidades tiene el estudiante que yo NO tengo
        complementary_skills = s_skill_ids - my_skill_ids
        score = len(complementary_skills)
        
        student_scores.append((score, s, s_tags))

    # Ordenar por mayor complementariedad, luego por total de habilidades (para desempatar)
    student_scores.sort(key=lambda x: (x[0], len(x[2])), reverse=True)
    
    # Tomar los top 20
    top_students = student_scores[:20]

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
"""

# Replace the old get_suggestions
pattern = r'@router\.get\("/suggestions".*?return response'
new_content = re.sub(pattern, replacement.strip(), content, flags=re.DOTALL)

with open("src/routers/teams.py", "w") as f:
    f.write(new_content)
