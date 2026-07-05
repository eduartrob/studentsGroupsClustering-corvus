# Documentación de Endpoints - Gestión de Equipos (Corvus)

Esta sección de la API administra el flujo de equipos, solicitudes de integración y sugerencias de candidatos, integrando autenticación por token JWT (Bearer Token) y persistencia en base de datos PostgreSQL.

---

## 1. Configuración de Base de Datos y Entorno

### 1.1. Ejecutar Schema en PostgreSQL
Copia el contenido del archivo [database.sql](file:///c:/Users/reygu/Desktop/UNIVERSIDAD%20POLITECNICA%20DE%20CHIAPAS/9NO%20CUATRIMESTRE/Mineria%20de%20Datos/Corte%202/studentsGroupsClustering-corvus/src/database.sql) y ejecútalo en tu cliente Postgres (PgAdmin, DBeaver o CLI) para crear o alterar las tablas de la base de datos local.

### 1.2. Configurar Archivo `.env`
Crea un archivo `.env` en la raíz del proyecto basándote en [.env.example](file:///c:/Users/reygu/Desktop/UNIVERSIDAD%20POLITECNICA%20DE%20CHIAPAS/9NO%20CUATRIMESTRE/Mineria%20de%20Datos/Corte%202/studentsGroupsClustering-corvus/src/.env.example):
```env
DATABASE_URL=postgresql://tu_usuario:tu_contraseña@localhost:5432/corvus_db
JWT_SECRET=tu_firma_secreta_jwt
JWT_ALGORITHM=HS256
DEV_BYPASS=true
```

> [!TIP]
> **Modo Bypass de Desarrollo (`DEV_BYPASS=true`)**: 
> Si está activado, en lugar de generar un token JWT complejo en tus pruebas locales, puedes simplemente enviar el **UUID** del usuario directamente como token en el header `Authorization: Bearer <user-uuid>` y la API lo autenticará directamente contra la base de datos.

---

## 2. Especificación de Endpoints

### 2.1. Gestión de Equipo (`/teams/my-team`)

#### ── GET `/teams/my-team`
Obtiene los detalles del equipo del usuario autenticado (integrantes, proyecto y redes).
* **Headers**:
  * `Authorization`: `Bearer <token_jwt_o_uuid>`
* **Respuesta (200 OK)**:
  ```json
  {
    "id": "e5c2b3a8-4e12-42bb-9bb1-396328321cb5",
    "name": "Corvus Devs",
    "description": "Equipo encargado del desarrollo de la plataforma móvil Corvus.",
    "project": {
      "title": "Sistema de gestión de equipos",
      "description": "Herramienta colaborativa para conectar estudiantes y optimizar la asignación de proyectos académicos."
    },
    "memberCount": 3,
    "maxMembers": 3,
    "socialLinks": [
      { "id": "1", "platform": "Discord", "url": "https://discord.gg/corvus-devs" },
      { "id": "2", "platform": "WhatsApp", "url": "https://chat.whatsapp.com/corvus-chat" }
    ],
    "members": [
      {
        "id": "user-uuid-1",
        "name": "Alex Rivera",
        "email": "arivera@university.edu",
        "avatarUrl": "https://...",
        "isMe": true
      },
      {
        "id": "user-uuid-2",
        "name": "Elena Morales",
        "email": "emorales@university.edu",
        "avatarUrl": "https://...",
        "isMe": false
      }
    ]
  }
  ```

#### ── PUT `/teams/my-team`
Actualiza el nombre, descripción y enlaces de redes sociales del equipo.
* **Headers**:
  * `Authorization`: `Bearer <token_jwt_o_uuid>`
* **Cuerpo de la Petición (Request Body)**:
  ```json
  {
    "name": "Corvus Devs Actualizado",
    "description": "Nueva descripción del equipo...",
    "socialLinks": [
      { "platform": "Discord", "url": "https://discord.gg/nuevo-enlace" },
      { "platform": "WhatsApp", "url": "https://chat.whatsapp.com/nuevo-chat" }
    ]
  }
  ```
* **Respuesta (200 OK)**: Retorna el objeto del equipo actualizado con la misma estructura del `GET /teams/my-team`.

#### ── POST `/teams/my-team/leave`
El usuario autenticado abandona su equipo actual.
* **Headers**:
  * `Authorization`: `Bearer <token_jwt_o_uuid>`
* **Respuesta (200 OK)**:
  ```json
  {
    "message": "Has salido del equipo con éxito"
  }
  ```

#### ── DELETE `/teams/my-team/members/{memberId}`
Expulsa a un integrante del equipo del usuario autenticado (modelo democrático).
* **Headers**:
  * `Authorization`: `Bearer <token_jwt_o_uuid>`
* **Parámetro de Ruta (Path Param)**:
  * `memberId`: UUID del usuario a remover.
* **Respuesta (200 OK)**:
  ```json
  {
    "message": "El integrante ha sido removido del equipo"
  }
  ```

---

### 2.2. Solicitudes (`/teams/requests`)

#### ── GET `/teams/requests`
Obtiene las solicitudes enviadas por el equipo o las invitaciones aceptadas.
* **Headers**:
  * `Authorization`: `Bearer <token_jwt_o_uuid>`
* **Parámetros de Consulta (Query Params)**:
  * `filter`: Puede ser `enviadas` (obtiene invitaciones pendientes enviadas por tu equipo) o `aceptadas` (obtiene invitaciones que ya fueron aceptadas).
* **Respuesta (200 OK)**:
  ```json
  [
    {
      "id": "req-uuid-123",
      "state": "PENDIENTE",
      "date": "2026-07-04T12:00:00Z",
      "student": {
        "id": "student-uuid",
        "name": "Sophia Patel",
        "username": "@sophia_data",
        "bio": "Data Scientist focused on NLP and machine learning.",
        "avatarUrl": "https://...",
        "isVerified": true,
        "tags": ["Python", "PyTorch", "AI/ML"]
      }
    }
  ]
  ```

#### ── POST `/teams/requests`
Envía una invitación a un alumno que no pertenece a ningún equipo.
* **Headers**:
  * `Authorization`: `Bearer <token_jwt_o_uuid>`
* **Cuerpo de la Petición (Request Body)**:
  ```json
  {
    "studentId": "uuid-del-estudiante-a-invitar"
  }
  ```
* **Respuesta (201 Created)**: Retorna la solicitud creada con estado `PENDIENTE`.

#### ── DELETE `/teams/requests/{requestId}`
Cancela una invitación que fue enviada por el equipo, o la rechaza si eres el estudiante.
* **Headers**:
  * `Authorization`: `Bearer <token_jwt_o_uuid>`
* **Parámetro de Ruta (Path Param)**:
  * `requestId`: UUID del registro en la tabla `team_requests`.
* **Respuesta (200 OK)**:
  ```json
  {
    "message": "Solicitud cancelada con éxito"
  }
  ```

#### ── POST `/teams/requests/{requestId}/accept`
*(Endpoint Adicional)* Permite al estudiante aceptar la invitación recibida de un equipo.
* **Headers**:
  * `Authorization`: `Bearer <token_jwt_o_uuid>`
* **Respuesta (200 OK)**:
  ```json
  {
    "message": "Te has unido al equipo 'Corvus Devs' exitosamente."
  }
  ```

---

### 2.3. Sugerencias (`/teams/suggestions`)

#### ── GET `/teams/suggestions`
Obtiene alumnos que no pertenezcan a ningún equipo y que no tengan invitaciones pendientes de tu parte.
* **Headers**:
  * `Authorization`: `Bearer <token_jwt_o_uuid>`
* **Parámetros de Consulta (Query Params)**:
  * `skill`: *(Opcional)* Filtro para buscar por habilidad o etiqueta de tecnología (Ej: `?skill=TypeScript`).
* **Respuesta (200 OK)**:
  ```json
  [
    {
      "id": "student-uuid-99",
      "name": "Elena Rodríguez",
      "username": "@elena_dev",
      "bio": "Full-stack developer passionate about building scalable RAG applications and UI/UX",
      "avatarUrl": "https://...",
      "isVerified": false,
      "tags": ["React", "TypeScript", "UI/UX"]
    }
  ]
  ```
