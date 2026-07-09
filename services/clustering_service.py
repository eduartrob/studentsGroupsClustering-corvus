import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import MultiLabelBinarizer



def cluster_students_by_skills(users_data: list):
    """
    Agrupa a los estudiantes utilizando sus habilidades (skills).
    Encuentra el K óptimo automáticamente usando el método de la Silueta.
    users_data: [{"id": uuid, "skills": ["skill1", "skill2"]}, ...]
    Retorna un diccionario: {user_id: cluster_id}
    """
    if not users_data or len(users_data) < 3:
        return {u["id"]: 0 for u in users_data}

    # 1. One-Hot Encoding
    ids = [u["id"] for u in users_data]
    skills_list = [u["skills"] for u in users_data]

    mlb = MultiLabelBinarizer()
    X = mlb.fit_transform(skills_list)
    
    # Si nadie tiene skills, asignar todo a cluster 0
    if X.shape[1] == 0:
         return {u["id"]: 0 for u in users_data}

    # 2. Búsqueda del K Óptimo (Silhouette)
    max_k = min(6, len(users_data) - 1)
    best_k = 2
    best_score = -1
    
    if max_k >= 2:
        for k in range(2, max_k + 1):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X)
            # Evitar error si todos caen en un solo cluster
            if len(np.unique(labels)) > 1:
                score = silhouette_score(X, labels)
                if score > best_score:
                    best_score = score
                    best_k = k
    else:
        best_k = 1

    # 3. K-Means Final
    if best_k == 1:
        return {uid: 0 for uid in ids}
        
    kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)
    
    # Retornamos dict id -> cluster_id
    return {ids[i]: int(labels[i]) for i in range(len(ids))}

