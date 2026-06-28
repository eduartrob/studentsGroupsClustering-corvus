#clustering.py
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

def cluster_students(course_grades: dict, n_clusters: int = 4):
    """
    course_grades: {student_id: {"name": str, "scores": {materia: nota}}}
    Retorna lista de alumnos con su cluster asignado.
    """
    # Construir DataFrame
    records = []
    for uid, data in course_grades.items():
        row = {"id": uid, "name": data["name"]}
        row.update(data["scores"])
        records.append(row)

    df = pd.DataFrame(records).set_index("id")
    names = df["name"]
    df = df.drop(columns=["name"]).fillna(0)

    if df.empty or len(df) < n_clusters:
        raise ValueError("No hay suficientes datos para clustering")

    # Normalizar
    scaler = StandardScaler()
    X = scaler.fit_transform(df)

    # K-Means
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)

    # PCA para visualización 2D (opcional)
    pca = PCA(n_components=2)
    coords = pca.fit_transform(X)

    # Interpretar clusters: el de mayor promedio = "experto"
    cluster_means = pd.Series(labels).groupby(labels).apply(
        lambda idx: X[idx.index].mean()
    )
    sorted_clusters = cluster_means.sort_values(ascending=False).index.tolist()
    level_names = ["Experto", "Avanzado", "Intermedio", "Básico"]
    cluster_to_level = {c: level_names[i] for i, c in enumerate(sorted_clusters[:n_clusters])}

    results = []
    for i, (uid, row) in enumerate(df.iterrows()):
        results.append({
            "student_id": uid,
            "name": names[uid],
            "cluster": int(labels[i]),
            "level": cluster_to_level[labels[i]],
            "pca_x": float(coords[i][0]),
            "pca_y": float(coords[i][1]),
            "avg_score": float(row.mean()),
        })

    return results