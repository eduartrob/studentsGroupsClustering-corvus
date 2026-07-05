# tech_extractor.py
import re
import fitz
from transformers import pipeline
from knowledge_base import CANDIDATOS, NOMBRE_ES

_zero_shot   = None
_ai_detector = None

def get_zero_shot():
    global _zero_shot
    if _zero_shot is None:
        print("⏳ Cargando modelo zero-shot...")
        _zero_shot = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
            device=-1,
        )
        print("✅ Zero-shot listo")
    return _zero_shot

def get_ai_detector():
    global _ai_detector
    if _ai_detector is None:
        print("⏳ Cargando detector de IA...")
        _ai_detector = pipeline(
            "text-classification",
            model="Hello-SimpleAI/chatgpt-detector-roberta",
            device=-1,
            truncation=True,
            max_length=512,
        )
        print("✅ Detector de IA listo")
    return _ai_detector

def extraer_texto_pdf(contenido_bytes: bytes) -> str:
    try:
        doc   = fitz.open(stream=contenido_bytes, filetype="pdf")
        texto = " ".join(page.get_text() for page in doc)
        return re.sub(r'\s+', ' ', texto).strip()
    except:
        return ""

def detectar_ia(texto: str) -> dict:
    if not texto or len(texto.strip()) < 80:
        return {"es_ia": None, "probabilidad_ia": None, "etiqueta": "⚠️ Sin texto suficiente"}
    try:
        detector = get_ai_detector()
        muestra  = " ".join(texto.split()[:500])
        res      = detector(muestra)[0]
        es_ia    = res["label"] == "ChatGPT"
        prob_ia  = res["score"] if es_ia else 1 - res["score"]

        if prob_ia >= 0.85:   etiqueta = "🤖 Muy probable IA"
        elif prob_ia >= 0.70: etiqueta = "🤖 Posiblemente IA"
        elif prob_ia >= 0.45: etiqueta = "🔍 Mixto"
        else:                 etiqueta = "✍️ Escrito por humano"

        return {
            "es_ia":           bool(es_ia),
            "probabilidad_ia": round(float(prob_ia), 3),
            "etiqueta":        etiqueta,
        }
    except Exception as e:
        return {"es_ia": None, "probabilidad_ia": None, "etiqueta": f"Error: {e}"}

def detectar_tecnologias(texto: str, titulo: str = "", umbral: float = 0.22) -> list:
    modelo = get_zero_shot()

    if texto and len(texto.strip()) > 150:
        palabras = texto.split()
        n        = len(palabras)
        muestra  = " ".join(palabras[:200] + palabras[n//2:n//2+100])
    else:
        muestra = titulo

    if not muestra.strip():
        return []

    try:
        resultado = modelo(muestra, candidate_labels=CANDIDATOS, multi_label=True)
        tecnologias = [
            {"tecnologia": NOMBRE_ES.get(label, label), "score": round(float(score), 3)}
            for label, score in zip(resultado["labels"], resultado["scores"])
            if score >= umbral
        ]
        tecnologias.sort(key=lambda x: x["score"], reverse=True)
        return tecnologias[:5]
    except Exception as e:
        print(f"    ⚠️ Error zero-shot: {e}")
        return []

def analizar_documento_completo(contenido_bytes: bytes, titulo: str) -> dict:
    texto       = extraer_texto_pdf(contenido_bytes)
    tiene_texto = len(texto.strip()) > 100
    tecnologias = detectar_tecnologias(texto, titulo=titulo)
    analisis_ia = detectar_ia(texto) if tiene_texto else {
        "es_ia": None, "probabilidad_ia": None, "etiqueta": "⚠️ PDF escaneado sin texto"
    }
    return {
        "titulo":                 titulo,
        "tiene_texto":            tiene_texto,
        "palabras":               len(texto.split()) if texto else 0,
        "tecnologias_detectadas": tecnologias,
        "analisis_ia":            analisis_ia,
    }