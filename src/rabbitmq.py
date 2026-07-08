import os
import json
import asyncio
import aio_pika
from sqlalchemy.orm import Session
from src.database import SessionLocal
from src.models import User, UserSkill, Skill

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
