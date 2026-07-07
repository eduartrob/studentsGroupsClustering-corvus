# main.py
from classroom_client import get_all_pdfs_from_drive
import os
import io
import re
import pickle
import time
import json
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks
from fastapi.responses import RedirectResponse, HTMLResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.http import MediaIoBaseDownload
from knowledge_base import UNIFICAR
from auth import SCOPES, get_credentials
from sqlalchemy.orm import Session
from src.database import get_db
from src.auth import get_current_user
from src.models import StudentCourse, StudentSubmission, StudentDrivePDF, StudentSkill, User
from src.database import SessionLocal
from classroom_client import (
    get_courses, get_my_submissions,
    get_my_drive_files, get_drive_service
)
from clustering import cluster_students
from tech_extractor import analizar_documento_completo
from nlp_processor import analizar_perfil_alumno, detectar_tecnologias_por_taxonomia
from templates import get_auth_success_html
from src.routers.teams import router as teams_router

app = FastAPI(title="Student Clustering API")
app.include_router(teams_router)
_cache: dict = {}

# Whitelist de habilidades válidas de Ingeniería de Software, Sistemas y Negocios
VALIDS_SKILLS = {
    "Python", "JavaScript / Web", "Java", "Desarrollo Móvil", "Flutter / Dart",
    "SQL / Bases de Datos", "MongoDB / NoSQL", "Cloud Computing", "Ciberseguridad",
    "Redes / Cisco", "Machine Learning / IA", "Deep Learning", "Linux / Sistemas Operativos",
    "Docker / DevOps", "Git / Control de Versiones", "Ingeniería de Software",
    "Estructuras de Datos", "Desarrollo Web", "APIs REST", "Compiladores / Autómatas",
    "Calidad de Software", "Diseño UI/UX", "Blockchain", "Análisis de Datos",
    "Sistemas Embebidos", "Sistemas Operativos", "Arquitectura de Computadoras",
    "Métodos Numéricos", "Administración de Proyectos", "Liderazgo / Gestión",
    "Análisis Financiero", "Marketing / Estrategia", "Recursos Humanos",
    "Cadena de Suministro", "Emprendimiento", "Inteligencia de Negocios",
    "Comportamiento Organizacional", "Economía", "Negocios Internacionales",
    "Ventas / Atención al Cliente", "Gestión de Calidad", "Inglés",
    "Matemáticas / Estadística", "Álgebra / Matemáticas Discretas"
}

REDIRECT_URI = "http://localhost:8000/callback"
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

# ── Auth ──────────────────────────────────────────────────────────

@app.get("/login")
def login():
    flow = Flow.from_client_secrets_file(
        "credentials.json", scopes=SCOPES, redirect_uri=REDIRECT_URI
    )
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="select_account",
    )
    open("oauth_state.txt", "w").write(state)
    open("oauth_code_verifier.txt", "w").write(flow.code_verifier or "")
    return RedirectResponse(auth_url)

@app.get("/callback")
def callback(request: Request, code: str = None, state: str = None, error: str = None):
    if error:
        return HTMLResponse(f"<h2>Error: {error}</h2>")
    if not code:
        return HTMLResponse("<h2>No se recibió código</h2>")
    if not os.path.exists("oauth_state.txt"):
        return HTMLResponse("<h2>Sesión expirada, ve a <a href='/login'>/login</a></h2>")

    saved_state    = open("oauth_state.txt").read().strip()
    saved_verifier = open("oauth_code_verifier.txt").read().strip() \
                     if os.path.exists("oauth_code_verifier.txt") else None

    flow = Flow.from_client_secrets_file(
        "credentials.json", scopes=SCOPES,
        redirect_uri=REDIRECT_URI, state=saved_state,
        **({"code_verifier": saved_verifier} if saved_verifier else {})
    )
    flow.fetch_token(code=code, client_secret=flow.client_config["client_secret"])
    pickle.dump(flow.credentials, open("token.pickle", "wb"))

    for f in ["oauth_state.txt", "oauth_code_verifier.txt"]:
        if os.path.exists(f):
            os.remove(f)

    return HTMLResponse(get_auth_success_html())

# ── Helper ────────────────────────────────────────────────────────

def require_auth():
    creds = get_credentials()
    if not creds:
        raise HTTPException(
            status_code=401,
            detail="No autenticado. Ve primero a http://localhost:8000/login"
        )
    return creds

def normalizar(texto: str) -> str:
    if not texto:
        return ""
    texto = texto.lower().strip()
    for a, b in [("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"),("ñ","n")]:
        texto = texto.replace(a, b)
    texto = re.sub(r'[^a-z0-9\s]', ' ', texto)
    return " ".join(texto.split())

def formatear_tiempo(segundos: float) -> str:
    minutos = int(segundos // 60)
    segs = segundos % 60
    if minutos > 0:
        return f"{minutos}m {segs:.2f}s"
    return f"{segs:.2f}s"

# ── Endpoints ─────────────────────────────────────────────────────

@app.get("/")
def root():
    creds = get_credentials()
    if creds:
        return {"status": "✅ Autenticado", "docs": "http://localhost:8000/docs"}
    return {"status": "⚠️ No autenticado", "login": "http://localhost:8000/login"}

@app.get("/courses")
def list_courses():
    require_auth()
    try:
        courses = get_courses()
        return {"courses": [{"id": c["id"], "name": c["name"]} for c in courses]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cluster/{course_id}")
def cluster_course(course_id: str, n_clusters: int = 4):
    require_auth()
    try:
        scores = get_my_submissions(course_id)
        if not scores:
            return {
                "course_id": course_id,
                "mensaje": "No tienes entregas calificadas aún en este curso",
                "scores": {}
            }
        return {
            "course_id": course_id,
            "total_tareas": len(scores),
            "calificaciones": scores,
            "promedio": round(sum(scores.values()) / len(scores), 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cluster/{course_id}/summary")
def cluster_summary(course_id: str):
    require_auth()
    if course_id not in _cache:
        raise HTTPException(
            status_code=404,
            detail="Corre primero POST /cluster/{course_id}"
        )
    results = cluster_students(_cache[course_id])
    summary = {}
    for r in results:
        summary.setdefault(r["level"], []).append(r["name"])
    return {"summary": summary}

PDF_CACHE_FILE = "pdf_analysis_cache.json"

def load_pdf_cache() -> dict:
    if os.path.exists(PDF_CACHE_FILE):
        try:
            with open(PDF_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_pdf_cache(cache: dict):
    try:
        with open(PDF_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except:
        pass

PROFILE_CACHE_FILE = "profile_cache.json"

def load_profile_cache() -> dict:
    if os.path.exists(PROFILE_CACHE_FILE):
        try:
            with open(PROFILE_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_profile_cache(cache: dict):
    try:
        with open(PROFILE_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except:
        pass

procesando_actualmente = set()

def procesar_perfil_en_background(user_id: str):
    db = SessionLocal()
    try:
        current_user = db.query(User).filter(User.id == user_id).first()
        if not current_user:
            return

        max_pdfs = 15
        start_time = time.time()
        
        # Construir credenciales de Google a partir de la base de datos
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from auth import request_credentials, SCOPES
        
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
        token_uri = "https://oauth2.googleapis.com/token"
        if os.path.exists("credentials.json") and (not client_id or not client_secret):
            try:
                with open("credentials.json", "r") as f:
                    data = json.load(f)
                    web_data = data.get("web", {})
                    client_id = client_id or web_data.get("client_id")
                    client_secret = client_secret or web_data.get("client_secret")
                    token_uri = web_data.get("token_uri", token_uri)
            except Exception as e:
                print(f"⚠️ Error al leer credentials.json: {e}")
                
        user_creds = None
        if current_user.google_access_token or current_user.google_refresh_token:
            user_creds = Credentials(
                token=current_user.google_access_token,
                refresh_token=current_user.google_refresh_token,
                token_uri=token_uri,
                client_id=client_id,
                client_secret=client_secret,
                scopes=SCOPES
            )
            
            if user_creds and user_creds.expired and user_creds.refresh_token:
                try:
                    user_creds.refresh(Request())
                    current_user.google_access_token = user_creds.token
                    db.commit()
                    print(f"🔄 Token de Google refrescado y guardado para {current_user.email}")
                except Exception as ref_err:
                    print(f"⚠️ Error al refrescar token de Google: {ref_err}")
                    
        if not user_creds:
            print("⚠️ No credentials for background task")
            return
            
        token_token = request_credentials.set(user_creds)
        try:
            print("📚 Obteniendo cursos...")
            cursos = get_courses()
            todas_las_tareas = []
            materias_detalle = []
            tecnologias_por_curso = defaultdict(set)

            def buscar_curso_de_carpeta(nombre_carpeta: str) -> str:
                if not nombre_carpeta:
                    return None
                folder_norm = normalizar(nombre_carpeta)
                for c in cursos:
                    curso_norm = normalizar(c["name"])
                    if curso_norm == folder_norm or curso_norm in folder_norm or folder_norm in curso_norm:
                        return c["name"]
                folder_words = set(folder_norm.split())
                for c in cursos:
                    curso_words = set(normalizar(c["name"]).split())
                    if len(folder_words & curso_words) >= max(1, len(curso_words) // 2):
                        return c["name"]
                return None

            for curso in cursos:
                tareas_curso = {}
                try:
                    subs = get_my_submissions(curso["id"], curso.get("courseState"))
                    for titulo, calificacion in subs.items():
                        todas_las_tareas.append({
                            "curso":        curso["name"],
                            "tarea":        titulo,
                            "calificacion": calificacion or 0
                        })
                        tareas_curso[titulo] = calificacion or 0
                        for tech in detectar_tecnologias_por_taxonomia(titulo):
                            tecnologias_por_curso[curso["name"]].add(tech)
                except:
                    pass

                calificaciones_validas = [v for v in tareas_curso.values() if v > 0]
                prom = round(sum(calificaciones_validas) / len(calificaciones_validas), 1) if calificaciones_validas else 0

                materias_detalle.append({
                    "nombre":      curso["name"],
                    "tareas":      len(tareas_curso),
                    "promedio":    prom,
                    "tecnologias": [],
                })

            print("🧠 Detectando tecnologías por títulos...")
            perfil_tareas = analizar_perfil_alumno(todas_las_tareas)
            tech_pool = defaultdict(lambda: {"scores": [], "cals": [], "materias": set()})

            for t in perfil_tareas.get("tecnologias", []):
                tech_pool[t["tecnologia"]]["cals"].append(t["promedio_calificacion"])

            print("📄 Buscando PDFs...")
            drive      = get_drive_service()
            todos_pdfs = get_all_pdfs_from_drive()
            documentos = []
            docs_con_ia = []

            # Filtrar inteligentemente con Ollama
            print("🧠 Filtrando PDFs inteligentemente con Ollama local...")
            try:
                import requests, os
                llm_url = os.getenv("LLM_URL", "http://localhost:3003") + "/api/v1/llm/filter-software-documents"
                payload = {
                    "documents": [{"id": p.get("id"), "name": p.get("name"), "folder": p.get("carpeta", "")} for p in todos_pdfs],
                    "provider": "ollama"
                }
                resp = requests.post(llm_url, json=payload, timeout=60)
                if resp.status_code == 200:
                    valid_ids = resp.json().get("valid_ids", [])
                    if valid_ids:
                        pdfs_a_analizar = [p for p in todos_pdfs if p.get("id") in valid_ids]
                        print(f"✅ Ollama filtró {len(pdfs_a_analizar)} PDFs de software de un total de {len(todos_pdfs)}.")
                    else:
                        print("⚠️ Ollama no devolvió IDs válidos. Analizando todos por precaución.")
                        pdfs_a_analizar = todos_pdfs
                else:
                    print(f"⚠️ Error del filtro Ollama (status {resp.status_code}). Analizando todos.")
                    pdfs_a_analizar = todos_pdfs
            except Exception as e:
                print(f"⚠️ Error conectando al filtro Ollama: {e}. Analizando todos.")
                pdfs_a_analizar = todos_pdfs

            total = len(pdfs_a_analizar)
            pdf_cache = load_pdf_cache()
            cache_updated = False

            for i, pdf in enumerate(pdfs_a_analizar):
                nombre  = pdf.get("name", "")
                carpeta = pdf.get("carpeta", "")
                file_id = pdf.get("id", "")

                if file_id in pdf_cache:
                    analisis = pdf_cache[file_id]
                    es_ia     = analisis.get("analisis_ia", {}).get("es_ia", False)
                    prob_ia   = analisis.get("analisis_ia", {}).get("probabilidad_ia")
                    techs_doc = analisis.get("tecnologias_detectadas", [])
                else:
                    try:
                        # Pequeña pausa para no saturar la API del LLM si procesamos muchos de golpe
                        time.sleep(2)
                        
                        req  = drive.files().get_media(fileId=file_id)
                        buf  = io.BytesIO()
                        dl   = MediaIoBaseDownload(buf, req)
                        done = False
                        while not done:
                            _, done = dl.next_chunk()

                        analisis  = analizar_documento_completo(buf.getvalue(), nombre)
                        pdf_cache[file_id] = analisis
                        cache_updated = True

                        es_ia     = analisis.get("analisis_ia", {}).get("es_ia", False)
                        prob_ia   = analisis.get("analisis_ia", {}).get("probabilidad_ia")
                        techs_doc = analisis.get("tecnologias_detectadas", [])
                    except Exception as e:
                        print(f"⚠️ Error al procesar PDF {nombre}: {e}")
                        continue

                documentos.append({
                    "nombre":          nombre,
                    "carpeta":         carpeta,
                    "hecho_con_ia":    bool(es_ia) if es_ia is not None else None,
                    "probabilidad_ia": prob_ia,
                    "tecnologias":     [t["tecnologia"] for t in techs_doc],
                })

                if es_ia:
                    docs_con_ia.append(nombre)
                else:
                    for t in techs_doc:
                        score_val = t.get("score", t.get("similitud", 0))
                        tech_pool[t["tecnologia"]]["scores"].append(score_val)
                        tech_pool[t["tecnologia"]]["materias"].add(carpeta)

                    curso_asociado = buscar_curso_de_carpeta(carpeta)
                    if curso_asociado:
                        for t in techs_doc:
                            tech_final = UNIFICAR.get(t["tecnologia"], t["tecnologia"])
                            if tech_final in VALIDS_SKILLS:
                                tecnologias_por_curso[curso_asociado].add(tech_final)

            if cache_updated:
                save_pdf_cache(pdf_cache)

            tech_pool_unificado = defaultdict(lambda: {"scores": [], "cals": [], "materias": set()})
            for tech, data in tech_pool.items():
                tech_final = UNIFICAR.get(tech, tech)
                tech_pool_unificado[tech_final]["scores"].extend(data["scores"])
                tech_pool_unificado[tech_final]["cals"].extend(data["cals"])
                tech_pool_unificado[tech_final]["materias"].update(data["materias"])

            habilidades = []
            for tech, data in tech_pool_unificado.items():
                if tech not in VALIDS_SKILLS:
                    continue
                scores   = data["scores"]
                cals     = data["cals"]
                materias = list(data["materias"])

                sim_prom   = sum(scores) / len(scores) if scores else 0
                cal_prom   = sum(cals)   / len(cals)   if cals   else 0
                porcentaje = round(min(100, (sim_prom * 60) + (cal_prom * 0.4)), 1)

                if porcentaje < 20 and cal_prom < 50:
                    continue

                if porcentaje >= 70 or cal_prom >= 85:   nivel = "Experto"
                elif porcentaje >= 45 or cal_prom >= 70: nivel = "Avanzado"
                elif porcentaje >= 20 or cal_prom >= 50: nivel = "Intermedio"
                else:                                     nivel = "Básico"

                habilidades.append({
                    "habilidad": tech,
                    "nivel":      nivel,
                    "porcentaje": porcentaje,
                    "materias":   [m for m in materias[:3] if m],
                })

            habilidades.sort(key=lambda x: -x["porcentaje"])

            for m in materias_detalle:
                m["tecnologias"] = sorted(list(tecnologias_por_curso[m["nombre"]]))

            materias_relevantes = [
                m for m in materias_detalle
                if len(m["tecnologias"]) > 0
            ]

            result = {
                "alumno": current_user.email,
                "tiempo_ejecucion": formatear_tiempo(time.time() - start_time),
                "resumen": {
                    "total_materias":         len(cursos),
                    "materias_relevantes":    len(materias_relevantes),
                    "total_tareas":           len(todas_las_tareas),
                    "total_pdfs_en_drive":    len(todos_pdfs),
                    "pdfs_analizados":        len(documentos),
                    "documentos_con_ia":      len(docs_con_ia),
                    "habilidades_detectadas": len(habilidades),
                },
                "habilidades":       habilidades,
                "materias":          materias_relevantes,
                "documentos_con_ia": docs_con_ia,
            }

            try:
                db.query(StudentSkill).filter(StudentSkill.student_id == current_user.id).delete()
                db.query(StudentCourse).filter(StudentCourse.student_id == current_user.id).delete()
                db.query(StudentSubmission).filter(StudentSubmission.student_id == current_user.id).delete()
                db.query(StudentDrivePDF).filter(StudentDrivePDF.student_id == current_user.id).delete()
                db.commit()

                for m in materias_detalle:
                    course_id = next((c["id"] for c in cursos if c["name"] == m["nombre"]), f"temp_{m['nombre']}")
                    db_course = StudentCourse(
                        id=course_id,
                        student_id=current_user.id,
                        name=m["nombre"],
                        course_state=next((c.get("courseState") for c in cursos if c["name"] == m["nombre"]), "ACTIVE"),
                        average_grade=m["promedio"],
                        detected_technologies=m["tecnologias"]
                    )
                    db.add(db_course)

                for t in todas_las_tareas:
                    db_sub = StudentSubmission(
                        student_id=current_user.id,
                        course_name=t["curso"],
                        title=t["tarea"],
                        grade=t["calificacion"]
                    )
                    db.add(db_sub)

                for doc in documentos:
                    doc_file_id = next((pdf["id"] for pdf in pdfs_a_analizar if pdf["name"] == doc["nombre"]), f"temp_{doc['nombre']}")
                    db.query(StudentDrivePDF).filter(StudentDrivePDF.file_id == doc_file_id).delete()
                    
                    db_pdf = StudentDrivePDF(
                        student_id=current_user.id,
                        file_id=doc_file_id,
                        name=doc["nombre"],
                        folder=doc["carpeta"],
                        is_ai_generated=doc["hecho_con_ia"] or False,
                        ai_probability=doc["probabilidad_ia"] or 0.0,
                        detected_technologies=doc["tecnologias"]
                    )
                    db.add(db_pdf)

                for h in habilidades:
                    db_skill = StudentSkill(
                        student_id=current_user.id,
                        skill_name=h["habilidad"],
                        level=h["nivel"],
                        percentage=h["porcentaje"],
                        evidence_courses=h["materias"]
                    )
                    db.add(db_skill)

                current_user.tags = [h["habilidad"] for h in habilidades]
                db.commit()
                print(f"✅ Procesamiento asíncrono guardado para {current_user.email}.")
            except Exception as db_save_err:
                print(f"⚠️ Error al guardar asíncronamente: {db_save_err}")
                db.rollback()

            try:
                cache = load_profile_cache()
                cache[str(current_user.id)] = result
                save_profile_cache(cache)
            except:
                pass

        finally:
            request_credentials.reset(token_token)

    except Exception as e:
        print(f"⚠️ Error fatal en background task: {e}")
    finally:
        db.close()
        procesando_actualmente.discard(user_id)


@app.post("/teams/sync-perfil")
def sync_perfil(
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_id = str(current_user.id)
    # Verificar si ya está procesando
    if user_id in procesando_actualmente:
        return {"status": "processing"}
        
    # Verificar si ya tiene cache (si ya tiene, no hace falta lanzar sync otra vez)
    db_courses = db.query(StudentCourse).filter(StudentCourse.student_id == current_user.id).first()
    if db_courses:
        return {"status": "already_cached"}

    # Lanzar análisis asíncrono
    procesando_actualmente.add(user_id)
    background_tasks.add_task(procesar_perfil_en_background, user_id)
    
    return {"status": "started"}

@app.get("/teams/mi-perfil/completo")
def perfil_completo(
    force_refresh: bool = False,
    background_tasks: BackgroundTasks = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_key = str(current_user.id)
    
    if user_key in procesando_actualmente:
        return {"status": "processing"}

    if not force_refresh:
        try:
            db_courses = db.query(StudentCourse).filter(StudentCourse.student_id == current_user.id).all()
            if db_courses:
                db_skills = db.query(StudentSkill).filter(StudentSkill.student_id == current_user.id).all()
                db_submissions = db.query(StudentSubmission).filter(StudentSubmission.student_id == current_user.id).all()
                db_pdfs = db.query(StudentDrivePDF).filter(StudentDrivePDF.student_id == current_user.id).all()

                habilidades = [{
                    "habilidad": sk.skill_name,
                    "nivel": sk.level,
                    "porcentaje": sk.percentage,
                    "materias": sk.evidence_courses
                } for sk in db_skills]
                habilidades.sort(key=lambda x: -x["porcentaje"])

                materias_relevantes = [{
                    "nombre": c.name,
                    "tareas": sum(1 for s in db_submissions if s.course_name == c.name),
                    "promedio": c.average_grade,
                    "tecnologias": c.detected_technologies
                } for c in db_courses if len(c.detected_technologies) > 0]

                docs_con_ia = [pdf.name for pdf in db_pdfs if pdf.is_ai_generated]

                return {
                    "status": "completed",
                    "alumno": current_user.email,
                    "tiempo_ejecucion": "0.0s (Cargado de Base de Datos)",
                    "resumen": {
                        "total_materias": len(db_courses),
                        "materias_relevantes": len(materias_relevantes),
                        "total_tareas": len(db_submissions),
                        "total_pdfs_en_drive": len(db_pdfs),
                        "pdfs_analizados": len(db_pdfs),
                        "documentos_con_ia": len(docs_con_ia),
                        "habilidades_detectadas": len(habilidades),
                    },
                    "habilidades": habilidades,
                    "materias": materias_relevantes,
                    "documentos_con_ia": docs_con_ia,
                }
        except Exception as e:
            pass

    # Si no tiene cache y pide /completo en vez de /sync-perfil
    procesando_actualmente.add(user_key)
    if background_tasks:
        background_tasks.add_task(procesar_perfil_en_background, user_key)
    return {"status": "processing"}