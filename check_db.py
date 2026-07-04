from database.postgres import SessionLocal
from database.models import User, UserAuth

db = SessionLocal()

print("========== USERS ==========")
users = db.query(User).all()

for u in users:
    print(f"ID: {u.id}")
    print(f"Phone: {u.phone_number}")
    print("-" * 40)

print("\n========== USER AUTHS ==========")

auths = db.query(UserAuth).all()

for a in auths:
    print(f"User ID: {a.user_id}")
    print(f"Access Token Present: {bool(a.google_access_token)}")
    print(f"Refresh Token Present: {bool(a.google_refresh_token)}")
    print(f"Expiry: {a.google_token_expiry}")
    print("-" * 40)

db.close()