# tech_extractor.py
import re
import fitz
import os
import requests
import json

LLM_SERVICE_URL = os.getenv("LLM_URL", "http://localhost:3003") + "/api/v1/llm/analyze-homework"

def extraer_texto_pdf(contenido_bytes: bytes) -> str:
    try:
        doc   = fitz.open(stream=contenido_bytes, filetype="pdf")
        texto = " ".join(page.get_text() for page in doc)
        return re.sub(r'\s+', ' ', texto).strip()
    except Exception as e:
        print(f"⚠️ Error extrayendo texto del PDF: {e}")
        return ""

def analizar_documento_completo(contenido_bytes: bytes, titulo: str) -> dict:
    texto = extraer_texto_pdf(contenido_bytes)
    tiene_texto = len(texto.strip()) > 100
    
    tecnologias = []
    analisis_ia = {
        "es_ia": None,
        "probabilidad_ia": None,
        "etiqueta": "⚠️ Sin texto suficiente o error de IA"
    }

    if tiene_texto:
        try:
            print(f"🚀 Enviando documento '{titulo}' al LLM Service para extracción...")
            payload = {
                "title": titulo,
                "full_text": texto,
                "provider": "groq"
            }
            response = requests.post(LLM_SERVICE_URL, json=payload, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                tecnologias = data.get("tecnologias_detectadas", [])
                
                es_ia = data.get("es_ia")
                prob = data.get("probabilidad_ia")
                
                if prob is not None:
                    if prob >= 0.85:   etiqueta = "🤖 Muy probable IA"
                    elif prob >= 0.70: etiqueta = "🤖 Posiblemente IA"
                    elif prob >= 0.45: etiqueta = "🔍 Mixto"
                    else:              etiqueta = "✍️ Escrito por humano"
                else:
                    etiqueta = "⚠️ Sin análisis IA"

                analisis_ia = {
                    "es_ia": es_ia,
                    "probabilidad_ia": prob,
                    "etiqueta": etiqueta
                }
                print(f"✅ Respuesta del LLM: {len(tecnologias)} tecnologías, IA={prob}")
            else:
                print(f"❌ Error HTTP del LLM Service: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Excepción conectando al LLM Service: {e}")
    else:
        analisis_ia["etiqueta"] = "⚠️ PDF escaneado sin texto (imágenes)"

    return {
        "titulo":                 titulo,
        "tiene_texto":            tiene_texto,
        "palabras":               len(texto.split()) if texto else 0,
        "tecnologias_detectadas": tecnologias,
        "analisis_ia":            analisis_ia,
    }