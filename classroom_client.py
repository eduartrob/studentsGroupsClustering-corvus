# classroom_client.py
import os
import json
from googleapiclient.discovery import build
from auth import get_credentials

CLASSROOM_CACHE_FILE = "classroom_cache.json"

def _load_classroom_cache() -> dict:
    if os.path.exists(CLASSROOM_CACHE_FILE):
        try:
            with open(CLASSROOM_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def _save_classroom_cache(cache: dict):
    try:
        with open(CLASSROOM_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except:
        pass

def get_service():
    creds = get_credentials()
    return build("classroom", "v1", credentials=creds)

def get_drive_service():
    creds = get_credentials()
    return build("drive", "v3", credentials=creds)

def get_courses():
    service = get_service()
    # Solo buscar cursos activos para acelerar el cálculo
    result = service.courses().list(pageSize=100, courseStates=["ACTIVE"]).execute()
    return result.get("courses", [])

def get_my_submissions(course_id: str, course_state: str = None):
    # Cargar caché de Classroom
    cache = _load_classroom_cache()
    
    # Si la materia es ARCHIVED y ya está en caché, la devolvemos inmediatamente
    if course_state == "ARCHIVED" and course_id in cache:
        return cache[course_id]
        
    service = get_service()
    work_map = {}

    try:
        works_result = service.courses().courseWork().list(
            courseId=course_id,
            fields="courseWork(id,title)"
        ).execute()
        work_map = {w["id"]: w["title"] for w in works_result.get("courseWork", [])}
    except Exception as e:
        # Si falla courseWork, continuamos con map vacío
        pass

    try:
        submissions = service.courses().courseWork().studentSubmissions().list(
            courseId=course_id,
            courseWorkId="-",
            userId="me",
        ).execute()
    except Exception as e:
        return {}

    scores = {}
    for sub in submissions.get("studentSubmissions", []):
        wid    = sub.get("courseWorkId", "")
        grade  = sub.get("assignedGrade")
        titulo = work_map.get(wid, wid)  # si no hay título usa el ID
        if grade is not None:
            scores[titulo] = grade
        elif sub.get("state") in ["TURNED_IN", "RETURNED"]:
            # incluir tareas entregadas aunque no tengan calificación
            scores[titulo] = sub.get("draftGrade", 0) or 0

    # Guardar en caché antes de retornar
    cache[course_id] = scores
    _save_classroom_cache(cache)
    return scores

def get_all_pdfs_from_drive() -> list:
    drive = get_drive_service()

    # 1. Traer todas las carpetas del Drive del usuario de forma masiva
    folders = []
    page_token = None
    print("📁 Obteniendo lista de carpetas en Google Drive...")
    while True:
        try:
            res = drive.files().list(
                q="mimeType='application/vnd.google-apps.folder' and trashed=false",
                fields="nextPageToken, files(id, name, parents)",
                pageSize=1000,
                **({"pageToken": page_token} if page_token else {})
            ).execute()
            folders.extend(res.get("files", []))
            page_token = res.get("nextPageToken")
            if not page_token:
                break
        except Exception as e:
            print(f"❌ Error al obtener carpetas de Drive: {e}")
            break

    if not folders:
        print("❌ No se encontraron carpetas en Drive")
        return []

    # Crear mapa de ID a objeto de carpeta para búsquedas rápidas
    folder_map = {f["id"]: f for f in folders}
    
    # Encontrar la carpeta "Classroom"
    classroom_folder = next((f for f in folders if f["name"] == "Classroom"), None)
    if not classroom_folder:
        print("❌ No se encontró la carpeta 'Classroom' en Google Drive")
        return []
    
    classroom_id = classroom_folder["id"]
    print(f"📁 Carpeta 'Classroom' encontrada (ID: {classroom_id})")

    # Mapear parent_id -> list of child_ids en memoria para recorrer el árbol
    children_map = {}
    for f in folders:
        for parent in f.get("parents", []):
            children_map.setdefault(parent, []).append(f["id"])

    # Encontrar de forma iterativa todas las subcarpetas dentro de "Classroom"
    todos_folder_ids = set([classroom_id])
    to_process = [classroom_id]
    while to_process:
        curr = to_process.pop()
        children = children_map.get(curr, [])
        for child in children:
            if child not in todos_folder_ids:
                todos_folder_ids.add(child)
                to_process.append(child)

    print(f"📂 Total subcarpetas de Classroom mapeadas en memoria: {len(todos_folder_ids)}")

    # 2. Traer todos los PDFs y accesos directos únicamente de las carpetas de Classroom mapeadas
    todos_pdfs = []
    folder_ids_list = list(todos_folder_ids)
    limite_lote = 20
    
    print("🔍 Buscando todos los PDFs y accesos directos en las carpetas de Classroom...")
    for k in range(0, len(folder_ids_list), limite_lote):
        lote = folder_ids_list[k:k+limite_lote]
        parents_query = " or ".join([f"'{fid}' in parents" for fid in lote])
        q_string = f"trashed=false and (mimeType='application/pdf' or mimeType='application/vnd.google-apps.shortcut') and ({parents_query})"
        
        page_token = None
        while True:
            try:
                res = drive.files().list(
                    q=q_string,
                    fields="nextPageToken, files(id, name, mimeType, parents, shortcutDetails)",
                    pageSize=1000,
                    **({"pageToken": page_token} if page_token else {})
                ).execute()
                
                for archivo in res.get("files", []):
                    parents = archivo.get("parents", [])
                    matching_parent = next((p for p in parents if p in todos_folder_ids), None)
                    if not matching_parent:
                        continue
                    
                    carpeta_nombre = folder_map.get(matching_parent, {}).get("name", "")
                    
                    if archivo["mimeType"] == "application/pdf":
                        archivo["carpeta"] = carpeta_nombre
                        todos_pdfs.append(archivo)
                    elif archivo["mimeType"] == "application/vnd.google-apps.shortcut":
                        # Resolver acceso directo
                        target_id = archivo.get("shortcutDetails", {}).get("targetId")
                        target_mime = archivo.get("shortcutDetails", {}).get("targetMimeType", "")
                        if target_id and "pdf" in target_mime:
                            try:
                                real = drive.files().get(
                                    fileId=target_id,
                                    fields="id, name, mimeType"
                                ).execute()
                                real["carpeta"] = carpeta_nombre
                                real["nombre_original"] = archivo["name"]
                                todos_pdfs.append(real)
                            except Exception as e:
                                pass
                
                page_token = res.get("nextPageToken")
                if not page_token:
                    break
            except Exception as e:
                print(f"❌ Error al obtener archivos de Drive en lote: {e}")
                break

    print(f"📄 Total PDFs de Classroom listos para análisis: {len(todos_pdfs)}")
    return todos_pdfs

def get_my_drive_files():
    return get_all_pdfs_from_drive()