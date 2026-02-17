from app import app, mongo, bcrypt
from datetime import datetime

def seed_users():
    with app.app_context():
        # Clear existing users (optional, be careful in prod)
        # mongo.db.users.delete_many({}) 
        
        users = [
            {
                "name": "Dr. Admin HOD",
                "email": "hod@college.edu",
                "password": "admin", # Will be hashed
                "role": "hod",
                "dept": "MCA"
            },
            {
                "name": "Prof. Faculty",
                "email": "faculty@college.edu",
                "password": "faculty",
                "role": "faculty",
                "dept": "MCA"
            },
            {
                "name": "Student Ganesh",
                "email": "ganesh@college.edu",
                "password": "student",
                "role": "student",
                "dept": "MCA"
            }
        ]

        normalized_students = mongo.db.students.update_many(
            {"dept": {"$ne": "MCA"}},
            {"$set": {"dept": "MCA"}}
        )
        if normalized_students.modified_count > 0:
            print(f"Normalized {normalized_students.modified_count} existing student record(s) to MCA")

        for user in users:
            existing = mongo.db.users.find_one({"email": user['email']})
            if not existing:
                user['password'] = bcrypt.generate_password_hash(user['password']).decode('utf-8')
                user['created_at'] = datetime.now()
                mongo.db.users.insert_one(user)
                print(f"Created user: {user['name']} ({user['email']})")
            else:
                mongo.db.users.update_one(
                    {"email": user['email']},
                    {"$set": {"dept": "MCA"}}
                )
                print(f"User already exists, normalized dept to MCA: {user['email']}")

if __name__ == "__main__":
    seed_users()
