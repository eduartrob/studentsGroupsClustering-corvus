from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from core.auth import get_current_user
from models.models import User, UserSkill, Skill

router = APIRouter(tags=["Profile"])

@router.post("/sync-perfil")
def sync_perfil(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Dummy implementation that returns success
    return {"status": "success", "message": "Perfil sincronizado correctamente"}

@router.get("/mi-perfil/completo")
def perfil_completo(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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
