from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import User

engine = create_engine('postgresql://postgres:corvusdb_secret123@localhost:5432/corvus_auth_db')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

user = db.query(User).filter(User.email == 'eduartrob@gmail.com').first()
if user:
    print(f"Name: {user.full_name}")
    print(f"University ID: {user.universityId}")
    print(f"University Relation: {user.university}")
    if user.university:
        print(f"University Name: {user.university.name}")
    else:
        print("University Relation is None")
else:
    print("User not found")
