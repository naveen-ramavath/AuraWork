from database.postgres import SessionLocal
from database.models import User, UserAuth, SessionState

db = SessionLocal()

try:
    db.query(UserAuth).delete()
    db.query(SessionState).delete()
    db.query(User).delete()
    db.commit()
    print("Database cleared successfully!")
finally:
    db.close()
