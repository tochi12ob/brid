from database import Base, engine
from app.models import compliance, session, user  

print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Tables created successfully!")
