# tech_extractor.py
import re
import fitz
from transformers import pipeline

# ── Modelos (se cargan una sola vez) ─────────────────────────────
_zero_shot = None
_ai_detector = None

def get_zero_shot():
    global _zero_shot
    if _zero_shot is None:
        print("⏳ Cargando modelo zero-shot...")
        # MiniLM es mucho más ligero que bart-large-mnli
        _zero_shot = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
            device=-1,  # CPU
        )
        print("✅ Zero-shot listo")
    return _zero_shot

def get_ai_detector():
    global _ai_detector
    if _ai_detector is None:
        print("⏳ Cargando detector de IA...")
        # Modelo entrenado específicamente para detectar texto de ChatGPT
        _ai_detector = pipeline(
            "text-classification",
            model="Hello-SimpleAI/chatgpt-detector-roberta",
            device=-1,
            truncation=True,
            max_length=512,
        )
        print("✅ Detector de IA listo")
    return _ai_detector

# ── Extracción de texto ───────────────────────────────────────────

def extraer_texto_pdf(contenido_bytes: bytes) -> str:
    try:
        doc  = fitz.open(stream=contenido_bytes, filetype="pdf")
        texto = " ".join(page.get_text() for page in doc)
        texto = re.sub(r'\s+', ' ', texto).strip()
        return texto
    except:
        return ""

# ── Detector de IA ────────────────────────────────────────────────

def detectar_ia(texto: str) -> dict:
    if not texto or len(texto.strip()) < 80:
        return {
            "es_ia": None,
            "probabilidad_ia": None,
            "etiqueta": "⚠️ Sin texto suficiente",
        }
    try:
        detector = get_ai_detector()
        # Analizar los primeros 600 tokens
        muestra = " ".join(texto.split()[:500])
        res     = detector(muestra)[0]
        label   = res["label"]   # "ChatGPT" o "Human"
        score   = res["score"]

        es_ia    = label == "ChatGPT"
        prob_ia  = score if es_ia else 1 - score

        if prob_ia >= 0.85:
            etiqueta = "🤖 Muy probable IA"
        elif prob_ia >= 0.70:
            etiqueta = "🤖 Posiblemente IA"
        elif prob_ia >= 0.45:
            etiqueta = "🔍 Mixto"
        else:
            etiqueta = "✍️ Escrito por humano"

        return {
            "es_ia":           bool(es_ia),
            "probabilidad_ia": round(float(prob_ia), 3),
            "etiqueta":        etiqueta,
        }
    except Exception as e:
        return {"es_ia": None, "probabilidad_ia": None, "etiqueta": f"Error: {e}"}

# ── Detector de tecnologías (zero-shot) ───────────────────────────

# Candidatos amplios — NO son filtros, el modelo decide si aplican o no
# Están en inglés porque los modelos NLP funcionan mejor así
CANDIDATOS = [
    "Python programming", "JavaScript web development", "Java programming",
    "mobile app development Android iOS", "Flutter Dart development",
    "SQL databases", "NoSQL MongoDB databases", "cloud computing AWS Azure GCP",
    "cybersecurity network security", "computer networks Cisco routing",
    "machine learning artificial intelligence", "deep learning neural networks",
    "Linux operating systems", "Docker containers DevOps",
    "Git version control", "software engineering", "data structures algorithms",
    "web development frontend backend", "REST API development",
    "project management", "English language", "mathematics statistics",
    "digital electronics hardware", "compiler design automata theory",
    "software quality testing", "user interface design UX",
    "blockchain cryptocurrency", "data analysis visualization",
    "financial analysis accounting", "leadership management",
]

# Mapeo de candidatos en inglés → nombre en español para el response
NOMBRE_ES = {
    "Python programming":                      "Python",
    "JavaScript web development":              "JavaScript / Web",
    "Java programming":                        "Java",
    "mobile app development Android iOS":      "Desarrollo Móvil",
    "Flutter Dart development":                "Flutter / Dart",
    "SQL databases":                           "SQL / Bases de Datos",
    "NoSQL MongoDB databases":                 "MongoDB / NoSQL",
    "cloud computing AWS Azure GCP":           "Cloud Computing",
    "cybersecurity network security":          "Ciberseguridad",
    "computer networks Cisco routing":         "Redes / Cisco",
    "machine learning artificial intelligence":"Machine Learning / IA",
    "deep learning neural networks":           "Deep Learning",
    "Linux operating systems":                 "Linux / Sistemas Operativos",
    "Docker containers DevOps":               "Docker / DevOps",
    "Git version control":                     "Git / Control de Versiones",
    "software engineering":                    "Ingeniería de Software",
    "data structures algorithms":              "Estructuras de Datos",
    "web development frontend backend":        "Desarrollo Web",
    "REST API development":                    "APIs REST",
    "project management":                      "Administración de Proyectos",
    "English language":                        "Inglés",
    "mathematics statistics":                  "Matemáticas / Estadística",
    "digital electronics hardware":            "Electrónica Digital",
    "compiler design automata theory":         "Compiladores / Autómatas",
    "software quality testing":                "Calidad de Software",
    "user interface design UX":               "Diseño UI/UX",
    "blockchain cryptocurrency":               "Blockchain",
    "data analysis visualization":             "Análisis de Datos",
    "financial analysis accounting":           "Análisis Financiero",
    "leadership management":                   "Liderazgo / Gestión",
}

def detectar_tecnologias(texto: str, titulo: str = "", umbral: float = 0.20) -> list:
    """
    Usa zero-shot classification para detectar áreas de conocimiento.
    No depende de listas estáticas — funciona para cualquier carrera.
    El modelo decide qué candidatos aplican al contenido.
    """
    modelo = get_zero_shot()

    # Usar texto real si hay suficiente, si no usar título
    if texto and len(texto.strip()) > 150:
        # Tomar muestra representativa: inicio + medio del documento
        palabras = texto.split()
        n = len(palabras)
        muestra = " ".join(palabras[:200] + palabras[n//2:n//2+100])
    else:
        muestra = titulo

    if not muestra.strip():
        return []

    try:
        resultado = modelo(
            muestra,
            candidate_labels=CANDIDATOS,
            multi_label=True,   # puede pertenecer a varias categorías
        )

        tecnologias = []
        for label, score in zip(resultado["labels"], resultado["scores"]):
            if score >= umbral:
                tecnologias.append({
                    "tecnologia": NOMBRE_ES.get(label, label),
                    "score":      round(float(score), 3),
                })

        # Top 5 más relevantes
        tecnologias.sort(key=lambda x: x["score"], reverse=True)
        return tecnologias[:5]

    except Exception as e:
        print(f"    ⚠️ Error zero-shot: {e}")
        return []

# ── Análisis completo de un documento ────────────────────────────

def analizar_documento_completo(contenido_bytes: bytes, titulo: str) -> dict:
    texto       = extraer_texto_pdf(contenido_bytes)
    tiene_texto = len(texto.strip()) > 100

    tecnologias  = detectar_tecnologias(texto, titulo=titulo)
    analisis_ia  = detectar_ia(texto) if tiene_texto else {
        "es_ia": None,
        "probabilidad_ia": None,
        "etiqueta": "⚠️ PDF escaneado sin texto",
    }

    return {
        "titulo":                titulo,
        "tiene_texto":          tiene_texto,
        "palabras":             len(texto.split()) if texto else 0,
        "tecnologias_detectadas": tecnologias,
        "analisis_ia":           analisis_ia,
    }