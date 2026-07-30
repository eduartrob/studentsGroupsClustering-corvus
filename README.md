# Students Groups Clustering Service — Corvus Platform

Este microservicio pertenece a la plataforma **CORVUS**. Es el módulo encargado del **agrupamiento inteligente de estudiantes y gestión de equipos de trabajo** para proyectos integradores.

---

## 🎯 Función en el Ecosistema CORVUS
* **Formación de Equipos:** Creación, solicitud de ingreso, aprobación de miembros y enlaces de proyecto (`teams`, `team_members`, `team_requests`, `team_social_links`).
* **Algoritmos de Agrupamiento:** Algoritmos de clustering sintético y emparejamiento de habilidades para sugerencias de equipos equilibrados.
* **Gestión de Liderazgo:** Control de roles de líderes y miembros dentro de cada proyecto integrador.
* **Base de Datos Dedicada:** Opera sobre su base de datos PostgreSQL aislada **`corvus_students_groups_db`**.

---

## ⚙️ Tecnologías
* **Lenguaje & Framework:** Python 3.10+, FastAPI, Uvicorn.
* **ORM:** SQLAlchemy.
* **Base de Datos:** PostgreSQL (`corvus_students_groups_db`).

---

## 🛠️ Ejecución Local Independiente

### 1. Entorno Virtual & Dependencias
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Variables de Entorno
Crea un archivo `.env` basado en `.env.example`:
```env
PORT=8004
DATABASE_URL="postgresql://corvus_user:password@localhost:5432/corvus_students_groups_db"
```

### 3. Iniciar Servidor en Desarrollo
```bash
uvicorn main:app --reload --port 8004
```
La documentación interactiva Swagger estará disponible en `http://localhost:8004/docs`.

---

## 🐳 Ejecución con Docker

```bash
docker build -t corvus-students-groups .
docker run -p 8004:8004 --env-file .env corvus-students-groups
```

---

## 🔗 Integración con la Orquestación de CORVUS
Forma parte de la pila expuesta por **`orchestration-back-corvus`** y sus servicios son redirigidos por el API Gateway (`/api/v1/teams`).
