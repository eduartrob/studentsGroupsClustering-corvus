# nlp_processor.py
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from collections import defaultdict
import numpy as np

# Taxonomía de tecnologías — esto es referencia, NO filtro estático
# Si una tarea no cae aquí, igual se detecta por TF-IDF
TAXONOMY = {
    "Ciberseguridad":  ["seguridad", "ciberseguridad", "amenaza", "vulnerabilidad",
                        "rasp", "wipe", "cifrado", "firewall", "malware", "phishing",
                        "ofuscacion", "autoproteccion", "depuracion", "fuga"],
    "Cloud / AWS":     ["aws", "cloud", "nube", "amazon", "azure", "gcp",
                        "foundation", "s3", "ec2", "lambda", "serverless"],
    "Redes":           ["cisco", "red", "network", "tcp", "ip", "router",
                        "switch", "dhcp", "dns", "protocolo", "firewall"],
    "Móvil / Android": ["movil", "android", "ios", "flutter", "kotlin",
                        "swift", "gps", "apk", "pantalla", "captura"],
    "Python":          ["python", "django", "flask", "fastapi", "pandas",
                        "numpy", "scikit", "matplotlib"],
    "Bases de datos":  ["sql", "mysql", "postgresql", "mongodb", "redis",
                        "base de datos", "query", "nosql", "orm"],
    "IA / ML":         ["machine learning", "inteligencia artificial", "clustering",
                        "clasificacion", "regresion", "red neuronal", "deep learning",
                        "nlp", "procesamiento"],
    "Web":             ["html", "css", "javascript", "react", "angular",
                        "nodejs", "api", "rest", "frontend", "backend"],
    "Sistemas":        ["linux", "windows", "kernel", "proceso", "memoria",
                        "sistema operativo", "bash", "shell", "docker"],
}

def limpiar_texto(texto: str) -> str:
    texto = texto.lower()
    texto = re.sub(r'[^a-záéíóúüñ\s]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto

def detectar_tecnologias_por_taxonomia(titulo: str) -> list:
    """Detecta tecnologías usando la taxonomía como referencia."""
    titulo_limpio = limpiar_texto(titulo)
    encontradas = []
    for tech, keywords in TAXONOMY.items():
        if any(kw in titulo_limpio for kw in keywords):
            encontradas.append(tech)
    return encontradas

def extraer_terminos_tfidf(titulos: list, top_n: int = 15) -> list:
    """
    Usa TF-IDF para extraer los términos más relevantes
    de todos los títulos — detecta conocimientos no previstos.
    """
    if not titulos:
        return []

    titulos_limpios = [limpiar_texto(t) for t in titulos]

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),      # unigramas y bigramas
        min_df=1,
        max_features=200,
        stop_words=_stopwords_es()
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(titulos_limpios)
        feature_names = vectorizer.get_feature_names_out()
        scores = np.asarray(tfidf_matrix.sum(axis=0)).flatten()
        top_indices = scores.argsort()[::-1][:top_n]
        return [feature_names[i] for i in top_indices]
    except:
        return []

def analizar_perfil_alumno(tareas: list) -> dict:
    """
    tareas: [{"curso": str, "tarea": str, "calificacion": float}]
    Retorna perfil completo con tecnologías detectadas.
    """
    if not tareas:
        return {"tecnologias": [], "resumen": "Sin tareas"}

    titulos = [t["tarea"] for t in tareas]

    # 1. Detección por taxonomía con peso de calificación
    tech_scores = defaultdict(lambda: {"score": 0, "tareas": [], "calificaciones": []})

    for tarea in tareas:
        techs = detectar_tecnologias_por_taxonomia(tarea["tarea"])
        cal = tarea["calificacion"] or 0
        for tech in techs:
            tech_scores[tech]["score"] += 1 + (cal / 100)
            tech_scores[tech]["tareas"].append(tarea["tarea"])
            tech_scores[tech]["calificaciones"].append(cal)

    # 2. TF-IDF para detectar términos relevantes no cubiertos por taxonomía
    terminos_tfidf = extraer_terminos_tfidf(titulos)

    # 3. Detectar tecnologías emergentes no en taxonomía
    tech_conocidas = set()
    for techs in [detectar_tecnologias_por_taxonomia(t) for t in titulos]:
        tech_conocidas.update(techs)

    terminos_nuevos = [
        t for t in terminos_tfidf
        if not any(
            t in kw or kw in t
            for techs in TAXONOMY.values()
            for kw in techs
        ) and len(t) > 3
    ][:5]

    # 4. Construir resultado
    resultado = []

    for tech, data in sorted(tech_scores.items(),
                              key=lambda x: x[1]["score"], reverse=True):
        cals = data["calificaciones"]
        promedio_cal = sum(cals) / len(cals) if cals else 0
        score = round(data["score"], 2)

        if promedio_cal >= 85 and score >= 2:
            nivel = "🏆 Experto"
        elif promedio_cal >= 70 or score >= 1.5:
            nivel = "🥈 Avanzado"
        elif promedio_cal >= 50 or score >= 0.5:
            nivel = "📘 Básico"
        else:
            nivel = "⚠️ En progreso"

        resultado.append({
            "tecnologia": tech,
            "nivel": nivel,
            "score": score,
            "promedio_calificacion": round(promedio_cal, 1),
            "evidencias": data["tareas"][:3],  # max 3 ejemplos
        })

    # 5. Resumen automático
    if resultado:
        top = resultado[0]
        resumen = (
            f"El alumno tiene mayor fortaleza en {top['tecnologia']} "
            f"con nivel {top['nivel']} y promedio de {top['promedio_calificacion']}. "
            f"Términos relevantes detectados: {', '.join(terminos_tfidf[:5])}."
        )
    else:
        resumen = f"Términos detectados por TF-IDF: {', '.join(terminos_tfidf[:8])}"

    return {
        "tecnologias": resultado,
        "terminos_clave_tfidf": terminos_tfidf[:10],
        "terminos_emergentes": terminos_nuevos,
        "resumen": resumen
    }

def _stopwords_es() -> list:
    return [
        "de", "la", "el", "en", "y", "a", "los", "del", "las", "un",
        "una", "por", "con", "para", "es", "se", "al", "lo", "le",
        "da", "su", "que", "no", "si", "mi", "me", "c1", "c2", "c3",
        "practica", "actividad", "tarea", "investigacion", "evaluacion",
        "ordinaria", "diagnostica", "curso", "introduccion", "fundamentos"
    ]