# nlp_processor.py
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import defaultdict

def limpiar_texto(texto: str) -> str:
    texto = texto.lower()
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto

def detectar_tecnologias_por_taxonomia(titulo: str) -> list:
    """
    Sin taxonomía estática — devuelve vacío.
    La detección la hace tech_extractor con zero-shot.
    Se mantiene para no romper imports.
    """
    return []

def extraer_terminos_tfidf(titulos: list, top_n: int = 15) -> list:
    if not titulos or len(titulos) < 2:
        return []
    titulos_limpios = [limpiar_texto(t) for t in titulos]
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        max_features=200,
        stop_words=_stopwords_es()
    )
    try:
        matrix = vectorizer.fit_transform(titulos_limpios)
        names  = vectorizer.get_feature_names_out()
        scores = np.asarray(matrix.sum(axis=0)).flatten()
        top    = scores.argsort()[::-1][:top_n]
        return [names[i] for i in top]
    except:
        return []

def analizar_perfil_alumno(tareas: list) -> dict:
    if not tareas:
        return {"tecnologias": [], "terminos_clave": []}
    titulos  = [t["tarea"] for t in tareas]
    terminos = extraer_terminos_tfidf(titulos)
    return {
        "tecnologias":    [],
        "terminos_clave": terminos[:10],
    }

def _stopwords_es() -> list:
    return [
        "de", "la", "el", "en", "y", "a", "los", "del", "las", "un",
        "una", "por", "con", "para", "es", "se", "al", "lo", "le",
        "da", "su", "que", "no", "si", "mi", "me", "c1", "c2", "c3",
        "practica", "actividad", "tarea", "investigacion", "evaluacion",
        "ordinaria", "diagnostica", "curso", "introduccion", "fundamentos",
        "examen", "corte", "proyecto", "parcial", "unidad", "act", "entrega",
    ]