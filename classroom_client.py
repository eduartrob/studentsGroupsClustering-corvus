# classroom_client.py
from googleapiclient.discovery import build
from auth import get_credentials

def get_service():
    creds = get_credentials()
    return build("classroom", "v1", credentials=creds)

def get_drive_service():
    creds = get_credentials()
    return build("drive", "v3", credentials=creds)

def get_courses():
    service = get_service()
    result = service.courses().list(pageSize=100).execute()
    return result.get("courses", [])

def get_my_submissions(course_id: str):
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

    return scores

def get_all_pdfs_from_drive() -> list:
    drive = get_drive_service()

    res = drive.files().list(
        q="name='Classroom' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name)",
        pageSize=10,
    ).execute()

    if not res["files"]:
        print("❌ No se encontró carpeta Classroom en Drive")
        return []

    classroom_id = res["files"][0]["id"]
    print(f"📁 Carpeta Classroom encontrada")

    todos_folder_ids = [classroom_id]
    todos_folder_ids += _recolectar_todos_folders(drive, classroom_id)
    print(f"📂 Total subcarpetas: {len(todos_folder_ids)}")

    todos_pdfs = []
    folder_names = {}

    for i in range(0, len(todos_folder_ids), 5):
        batch = todos_folder_ids[i:i+5]

        for fid in batch:
            try:
                f = drive.files().get(fileId=fid, fields="id, name").execute()
                folder_names[fid] = f.get("name", "")
            except:
                folder_names[fid] = ""

        for fid in batch:
            page_token = None
            while True:
                try:
                    # Buscar PDFs Y shortcuts en esta carpeta
                    result = drive.files().list(
                        q=f"'{fid}' in parents and trashed=false and (mimeType='application/pdf' or mimeType='application/vnd.google-apps.shortcut')",
                        fields="nextPageToken, files(id, name, mimeType, shortcutDetails)",
                        pageSize=100,
                        **({"pageToken": page_token} if page_token else {})
                    ).execute()

                    for archivo in result.get("files", []):
                        carpeta = folder_names.get(fid, "")

                        if archivo["mimeType"] == "application/pdf":
                            # PDF directo
                            archivo["carpeta"] = carpeta
                            todos_pdfs.append(archivo)

                        elif archivo["mimeType"] == "application/vnd.google-apps.shortcut":
                            # Resolver el shortcut
                            target_id   = archivo.get("shortcutDetails", {}).get("targetId")
                            target_mime = archivo.get("shortcutDetails", {}).get("targetMimeType", "")

                            if target_id and "pdf" in target_mime:
                                try:
                                    # Obtener el archivo real
                                    real = drive.files().get(
                                        fileId=target_id,
                                        fields="id, name, mimeType"
                                    ).execute()
                                    real["carpeta"] = carpeta
                                    real["nombre_original"] = archivo["name"]
                                    todos_pdfs.append(real)
                                except:
                                    pass

                    page_token = result.get("nextPageToken")
                    if not page_token:
                        break

                except Exception as e:
                    print(f"  ⚠️ Error en folder {fid}: {e}")
                    break

    print(f"📄 Total PDFs encontrados: {len(todos_pdfs)}")
    return todos_pdfs

def _recolectar_todos_folders(drive, parent_id: str, depth: int = 0) -> list:
    """Recolecta recursivamente todos los folder IDs dentro de parent_id."""
    if depth > 5:
        return []

    result = drive.files().list(
        q=f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name)",
        pageSize=100,
    ).execute()

    folders = result.get("files", [])
    ids = [f["id"] for f in folders]

    for folder in folders:
        ids += _recolectar_todos_folders(drive, folder["id"], depth + 1)

    return ids

def _get_folder_names(drive, folder_ids: list) -> dict:
    """Obtiene nombres de folders por ID."""
    names = {}
    for i in range(0, len(folder_ids), 100):
        batch = folder_ids[i:i+100]
        id_query = " or ".join([f"id='{fid}'" for fid in batch])
        result = drive.files().list(
            q=id_query,
            fields="files(id, name)",
            pageSize=100,
        ).execute()
        for f in result.get("files", []):
            names[f["id"]] = f["name"]
    return names

def get_my_drive_files():
    return get_all_pdfs_from_drive()