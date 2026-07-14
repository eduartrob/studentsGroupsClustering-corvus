import os
import json
import asyncio
import aio_pika
from sqlalchemy.orm import Session
from core.database import SessionLocal
from models.models import User, UserSkill, Skill

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
EXCHANGE_NAME = "corvus_events"
QUEUE_NAME = "clustering_profile_updates"

async def process_profile_update(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            body = message.body.decode()
            payload = json.loads(body)
            user_id_str = payload.get("userId")
            data = payload.get("data", {})
            skills = data.get("skills")

            if not user_id_str or skills is None:
                return

            # Ejecutar de forma síncrona la actualización de base de datos
            def db_update():
                db: Session = SessionLocal()
                try:
                    import uuid
                    user_id = uuid.UUID(user_id_str)
                    
                    # Verificar que el usuario exista en esta BD
                    user = db.query(User).filter(User.id == user_id).first()
                    if not user:
                        return
                    
                    # Borrar habilidades actuales
                    db.query(UserSkill).filter(UserSkill.userId == user_id).delete()
                    db.commit()

                    # Insertar nuevas habilidades
                    for skill_name in skills:
                        skill = db.query(Skill).filter(Skill.name == skill_name).first()
                        if not skill:
                            skill = Skill(name=skill_name)
                            db.add(skill)
                            db.commit()
                            db.refresh(skill)

                        existing = db.query(UserSkill).filter(
                            UserSkill.userId == user_id,
                            UserSkill.skillId == skill.id
                        ).first()
                        if not existing:
                            user_skill = UserSkill(userId=user_id, skillId=skill.id)
                            db.add(user_skill)
                    
                    db.commit()
                    print(f"✅ Habilidades actualizadas en Clustering para User {user_id}")
                    
                    # --- Trigger Background Clustering ---
                    if user.universityId and user.careerId and user.semester:
                        # 1. Obtener todos los alumnos del mismo grupo
                        from src.models import Role
                        alumnos = db.query(User).join(Role, User.roleId == Role.id).filter(
                            Role.name == "ALUMNO",
                            User.universityId == user.universityId,
                            User.careerId == user.careerId,
                            User.semester == user.semester
                        ).all()
                        
                        # 2. Formatear data y Obtener Pesos de Habilidades
                        from models.models import CareerSkill
                        career_skills_db = db.query(CareerSkill).filter(CareerSkill.careerId == user.careerId).all()
                        skill_weights = {}
                        for cs in career_skills_db:
                            sk = db.query(Skill).filter(Skill.id == cs.skillId).first()
                            if sk:
                                skill_weights[sk.name] = cs.weight

                        users_data = []
                        for a in alumnos:
                            # Obtener skills
                            a_skills_db = db.query(UserSkill).filter(UserSkill.userId == a.id).all()
                            a_skill_ids = [us.skillId for us in a_skills_db]
                            a_skill_names = [db.query(Skill).filter(Skill.id == sid).first().name for sid in a_skill_ids if db.query(Skill).filter(Skill.id == sid).first()]
                            users_data.append({"id": a.id, "skills": a_skill_names})
                            
                        # 3. Correr ML Clustering con Pesos
                        from services.clustering_service import cluster_students_by_skills
                        cluster_map = cluster_students_by_skills(users_data, skill_weights)
                        
                        # 4. Actualizar base de datos
                        for a in alumnos:
                            if a.id in cluster_map:
                                a.cluster_id = cluster_map[a.id]
                        db.commit()
                        print(f"🧠 ML Clustering re-calculado para el grupo de {user_id}")
                        
                except Exception as e:
                    print(f"❌ Error actualizando habilidades en DB: {e}")
                    db.rollback()
                finally:
                    db.close()

            # Correr en un threadpool para no bloquear el loop asíncrono
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, db_update)

        except Exception as e:
            print(f"❌ Error procesando mensaje de RabbitMQ: {e}")

async def start_rabbitmq_consumer():
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        channel = await connection.channel()
        
        exchange = await channel.declare_exchange(
            EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
        )
        
        queue = await channel.declare_queue(QUEUE_NAME, durable=True)
        await queue.bind(exchange, routing_key="auth.profile.updated")
        
        await queue.consume(process_profile_update)
        print("✅ Consumidor RabbitMQ iniciado en Clustering Service")
        return connection
    except Exception as e:
        print(f"❌ Error conectando a RabbitMQ: {e}")
        return None

async def publish_push_notification(user_id: str, title: str, body: str, data: dict = None):
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        channel = await connection.channel()
        exchange = await channel.declare_exchange(
            EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
        )
        
        message_body = {
            "user_id": user_id,
            "title": title,
            "body": body,
            "data": data or {}
        }
        
        await exchange.publish(
            aio_pika.Message(body=json.dumps(message_body).encode()),
            routing_key="notifications.push.send"
        )
        await connection.close()
    except Exception as e:
        print(f"❌ Error publicando notificación Push: {e}")
