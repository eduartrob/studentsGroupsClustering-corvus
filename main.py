# main.py
from classroom_client import get_all_pdfs_from_drive
import os
import io
import re
import pickle
import time
import json
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.http import MediaIoBaseDownload
from knowledge_base import UNIFICAR
from auth import SCOPES, get_credentials
from classroom_client import (
    get_courses, get_my_submissions,
    get_my_drive_files, get_drive_service
)
from clustering import cluster_students
from tech_extractor import analizar_documento_completo, detectar_tecnologias
from nlp_processor import analizar_perfil_alumno, detectar_tecnologias_por_taxonomia
from templates import get_auth_success_html
from src.routers.teams import router as teams_router

app = FastAPI(title="Student Clustering API")
app.include_router(teams_router)
_cache: dict = {}

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

@app.get("/mi-perfil/completo")
def perfil_completo():
    max_pdfs = 15  # Límite interno de PDFs a analizar
    start_time = time.time()
    require_auth()
    try:
        # ── 1. Cursos y tareas
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
            prom = round(sum(calificaciones_validas) / len(calificaciones_validas), 1) \
                   if calificaciones_validas else 0

            materias_detalle.append({
                "nombre":      curso["name"],
                "tareas":      len(tareas_curso),
                "promedio":    prom,
                "tecnologias": [],
            })

        print(f"✅ {len(todas_las_tareas)} tareas de {len(cursos)} cursos")

        # ── 2. NLP sobre títulos
        print("🧠 Detectando tecnologías por títulos...")
        perfil_tareas = analizar_perfil_alumno(todas_las_tareas)
        tech_pool = defaultdict(lambda: {"scores": [], "cals": [], "materias": set()})

        for t in perfil_tareas.get("tecnologias", []):
            tech_pool[t["tecnologia"]]["cals"].append(t["promedio_calificacion"])
            print(f"  📌 {t['tecnologia']} — cal: {t['promedio_calificacion']}")

        # ── 3. PDFs del Drive
        print("📄 Buscando PDFs...")
        drive      = get_drive_service()
        todos_pdfs = get_all_pdfs_from_drive()
        documentos = []
        docs_con_ia = []

        pdfs_a_analizar = todos_pdfs[:max_pdfs]
        total = len(pdfs_a_analizar)
        print(f"🔍 Analizando {total} de {len(todos_pdfs)} PDFs...")

        pdf_cache = load_pdf_cache()
        cache_updated = False

        for i, pdf in enumerate(pdfs_a_analizar):
            nombre  = pdf.get("name", "")
            carpeta = pdf.get("carpeta", "")
            file_id = pdf.get("id", "")

            if file_id in pdf_cache:
                print(f"  [{i+1}/{total}] (Caché) {nombre[:50]}")
                analisis = pdf_cache[file_id]
                es_ia     = analisis.get("analisis_ia", {}).get("es_ia", False)
                prob_ia   = analisis.get("analisis_ia", {}).get("probabilidad_ia")
                techs_doc = analisis.get("tecnologias_detectadas", [])
            else:
                print(f"  [{i+1}/{total}] (IA local) {nombre[:50]}")
                try:
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
                    print(f"    ⚠️ Error: {e}")
                    continue

            print(f"    IA: {es_ia} ({prob_ia}) | Techs: {[t['tecnologia'] for t in techs_doc]}")

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
                        tecnologias_por_curso[curso_asociado].add(t["tecnologia"])

        if cache_updated:
            save_pdf_cache(pdf_cache)

        # ── 4. Calcular habilidades ──────────────────────────────────────
        print("📊 Calculando habilidades...")

        # Fusionar duplicados entre ambas fuentes
        tech_pool_unificado = defaultdict(lambda: {"scores": [], "cals": [], "materias": set()})
        for tech, data in tech_pool.items():
            tech_final = UNIFICAR.get(tech, tech)
            tech_pool_unificado[tech_final]["scores"].extend(data["scores"])
            tech_pool_unificado[tech_final]["cals"].extend(data["cals"])
            tech_pool_unificado[tech_final]["materias"].update(data["materias"])

        habilidades = []
        for tech, data in tech_pool_unificado.items():
            scores   = data["scores"]
            cals     = data["cals"]
            materias = list(data["materias"])

            sim_prom   = sum(scores) / len(scores) if scores else 0
            cal_prom   = sum(cals)   / len(cals)   if cals   else 0
            porcentaje = round(min(100, (sim_prom * 60) + (cal_prom * 0.4)), 1)

            # Descartar sin evidencia real
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

        # ── 5. Rellenar tecnologías por materia y filtrar las vacías
        for m in materias_detalle:
            m["tecnologias"] = sorted(list(tecnologias_por_curso[m["nombre"]]))

        # Solo mostrar materias con tecnologías detectadas
        materias_relevantes = [
            m for m in materias_detalle
            if len(m["tecnologias"]) > 0
        ]

        print(f"✅ {len(habilidades)} habilidades | {len(materias_relevantes)} materias relevantes")

        return {
            "alumno": "233352@ids.upchiapas.edu.mx",
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))