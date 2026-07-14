import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import collections

def cluster_students_by_skills(users_data: list, skill_weights: dict = None):
    """
    Agrupa a los estudiantes utilizando sus habilidades (skills) y sus pesos.
    Paso 1: Agrupa perfiles similares (K-Means).
    Paso 2: Balancea para formar equipos heterogéneos.
    """
    if not users_data or len(users_data) < 3:
        return {u["id"]: 0 for u in users_data}

    if skill_weights is None:
        skill_weights = {}

    ids = [u["id"] for u in users_data]
    skills_list = [u["skills"] for u in users_data]

    # Recopilar todas las skills únicas
    all_skills = set()
    for s_list in skills_list:
        all_skills.update(s_list)
    
    all_skills = list(all_skills)
    
    if not all_skills:
         return {u["id"]: 0 for u in users_data}

    # 1. Construir Matriz Ponderada
    X = np.zeros((len(users_data), len(all_skills)))
    for i, s_list in enumerate(skills_list):
        for j, skill in enumerate(all_skills):
            if skill in s_list:
                # Usar peso proporcionado por LLM, default 5 si no existe
                X[i, j] = skill_weights.get(skill, 5)

    # 2. Búsqueda del K Óptimo (Silhouette) para perfiles
    max_k = min(6, len(users_data) - 1)
    best_k = 2
    best_score = -1
    
    if max_k >= 2:
        for k in range(2, max_k + 1):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X)
            if len(np.unique(labels)) > 1:
                score = silhouette_score(X, labels)
                if score > best_score:
                    best_score = score
                    best_k = k
    else:
        best_k = 1

    # 3. K-Means Final (Perfiles de Estudiantes)
    if best_k == 1:
        profile_labels = [0] * len(ids)
    else:
        kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
        profile_labels = kmeans.fit_predict(X)

    # 4. Fase 2: Formación de Equipos Heterogéneos (Balanceo)
    # Queremos equipos de aprox 3-4 personas
    num_students = len(ids)
    target_team_size = 3
    num_teams = max(1, num_students // target_team_size)
    
    teams = [[] for _ in range(num_teams)]
    
    # Agrupar estudiantes por perfil
    profiles = collections.defaultdict(list)
    for i, p_label in enumerate(profile_labels):
        profiles[p_label].append(i)
        
    # Distribuir estudiantes (Round-robin de diferentes perfiles para asegurar heterogeneidad)
    team_idx = 0
    # Ordenamos perfiles por cantidad de estudiantes para repartir equitativamente
    sorted_profiles = sorted(profiles.keys(), key=lambda k: len(profiles[k]), reverse=True)
    
    assigned = set()
    while len(assigned) < num_students:
        added_in_round = False
        for p in sorted_profiles:
            if profiles[p]:
                # Tomar un estudiante de este perfil
                student_idx = profiles[p].pop(0)
                teams[team_idx].append(student_idx)
                assigned.add(student_idx)
                added_in_round = True
                
                # Mover al siguiente equipo
                team_idx = (team_idx + 1) % num_teams
                
        if not added_in_round:
            break

    # Construir mapa de resultados
    final_cluster_map = {}
    for t_id, team_members in enumerate(teams):
        for student_idx in team_members:
            final_cluster_map[ids[student_idx]] = t_id

    return final_cluster_map
