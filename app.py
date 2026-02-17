import cv2
import numpy as np
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_pymongo import PyMongo
from datetime import datetime, timedelta
import jwt
from functools import wraps
from flask_bcrypt import Bcrypt
import os

DEPARTMENT_CODE = "MCA"
DEPARTMENT_FULL_NAME = "Master of Computer Applications"

app = Flask(__name__)
# Allow Mobile Access
CORS(app, resources={r"/*": {"origins": "*"}}) 

app.config["MONGO_URI"] = os.getenv("MONGO_URI", "mongodb+srv://ganeshbramhane0700:Ganesh9093@cluster0.c3liorh.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "super-secret-key-change-this-in-prod")
mongo = PyMongo(app)
bcrypt = Bcrypt(app)
_ai_engine = None


def get_ai_engine():
    """
    Lazy-load DeepFace/TensorFlow stack so the web server can bind PORT quickly
    on platforms like Render.
    """
    global _ai_engine
    if _ai_engine is None:
        from ai_engine import get_face_embedding, verify_match
        _ai_engine = (get_face_embedding, verify_match)
    return _ai_engine

def decode_image(base64_string):
    try:
        if "base64," in base64_string: base64_string = base64_string.split(",")[1]
        img_data = base64.b64decode(base64_string)
        nparr = np.frombuffer(img_data, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except: return None

# --- AUTH MIDDLEWARE ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1] # Bearer <token>
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = mongo.db.users.find_one({'email': data['email']})
            if not current_user:
                return jsonify({'message': 'User not found!'}), 401
        except Exception as e:
            return jsonify({'message': 'Token is invalid!', 'error': str(e)}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated

# --- ROUTES ---

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200

@app.route('/api/auth/register', methods=['POST'])
def register_user():
    data = request.json
    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    
    # Check if user exists
    if mongo.db.users.find_one({"email": data['email']}):
        return jsonify({"message": "User already exists"}), 400

    new_user = {
        "name": data['name'],
        "email": data['email'],
        "password": hashed_password,
        "role": data.get('role', 'student'), # student, faculty, hod
        "dept": DEPARTMENT_CODE,
        "created_at": datetime.now()
    }
    mongo.db.users.insert_one(new_user)
    return jsonify({"message": "User registered successfully"}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    user = mongo.db.users.find_one({"email": data['email']})
    
    if user and bcrypt.check_password_hash(user['password'], data['password']):
        token = jwt.encode({
            'email': user['email'],
            'role': user['role'],
            'name': user.get('name', ''),
            'dept': user.get('dept', ''),
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm="HS256")
        
        return jsonify({
            'token': token, 
            'role': user['role'],
            'name': user['name']
        })
    
    return jsonify({"message": "Invalid credentials"}), 401

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json or {}
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    dept = DEPARTMENT_CODE
    password = (data.get('password') or '').strip()

    if not name or not email:
        return jsonify({"error": "Name and email are required."}), 400
    if '@' not in email:
        return jsonify({"error": "Please enter a valid email address."}), 400
    if password and len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    if mongo.db.students.find_one({"email": email}):
        return jsonify({"error": "Student with this email is already registered."}), 400

    existing_user = mongo.db.users.find_one({"email": email})
    if existing_user and existing_user.get('role') != 'student':
        return jsonify({"error": "This email is already linked to a non-student account."}), 400

    img = decode_image(data.get('image'))
    if img is None:
        return jsonify({"error": "Image Error"}), 400

    get_face_embedding, _ = get_ai_engine()
    embedding = get_face_embedding(img)
    if not embedding:
        return jsonify({"error": "Face not detected. Keep straight."}), 400

    mongo.db.students.insert_one({
        "name": name,
        "email": email,
        "dept": dept,
        "embedding": embedding,
        "created_at": datetime.now()
    })

    # AUTO-CREATE STUDENT LOGIN ACCOUNT
    if not existing_user:
        final_password = password if password else "student123"
        hashed_password = bcrypt.generate_password_hash(final_password).decode('utf-8')
        mongo.db.users.insert_one({
            "name": name,
            "email": email,
            "password": hashed_password,
            "role": "student",
            "dept": dept,
            "created_at": datetime.now()
        })

    login_hint = "Use your selected password to login." if password else "Use default password 'student123' to login."
    return jsonify({
        "message": f"Registration successful for {DEPARTMENT_FULL_NAME} ({DEPARTMENT_CODE}). {login_hint}"
    }), 201

@app.route('/api/mark_attendance', methods=['POST'])
def mark_attendance():
    data = request.json
    img = decode_image(data.get('image'))
    if img is None: return jsonify({"error": "Camera Error"}), 400

    get_face_embedding, verify_match = get_ai_engine()
    live_emb = get_face_embedding(img)
    if not live_emb: return jsonify({"error": "No face"}), 400

    students = list(mongo.db.students.find({}))
    if not students: return jsonify({"error": "No students registered"}), 404
    
    known_embs = [s['embedding'] for s in students]

    is_match, index = verify_match(known_embs, live_emb)
    if is_match:
        student = students[index]
        today = datetime.now().strftime("%Y-%m-%d")
        time_now = datetime.now().strftime("%H:%M:%S")
        
        # Check Duplicate
        if not mongo.db.attendance.find_one({"student_id": str(student['_id']), "date": today}):
            mongo.db.attendance.insert_one({
                "student_id": str(student['_id']), 
                "name": student['name'],
                "date": today, 
                "time": time_now,
                "status": "Present"
            })
        return jsonify({"match": True, "name": student['name']})
    
    return jsonify({"match": False, "message": "Unknown"}), 401

@app.route('/api/stats', methods=['GET'])
# @token_required # Optional: protect this if needed
def get_stats():
    total = mongo.db.students.count_documents({})
    today = datetime.now().strftime("%Y-%m-%d")
    present = mongo.db.attendance.count_documents({"date": today})
    return jsonify({"total_students": total, "present_today": present})

@app.route('/api/attendance_log', methods=['GET'])
def get_logs():
    # Get last 10 logs
    logs = list(mongo.db.attendance.find({}, {'_id': 0}).sort('_id', -1).limit(10))
    return jsonify(logs)

@app.route('/api/students', methods=['GET'])
@token_required
def get_students(current_user):
    if current_user.get('role') not in ['hod', 'faculty']:
        return jsonify({"message": "Unauthorized"}), 403

    total_sessions = len(mongo.db.attendance.distinct("date"))

    attendance_stats_pipeline = [
        {"$sort": {"date": -1, "time": -1}},
        {"$group": {
            "_id": "$student_id",
            "present_days": {"$sum": 1},
            "last_date": {"$first": "$date"},
            "last_time": {"$first": "$time"}
        }}
    ]
    attendance_stats = {
        item["_id"]: item
        for item in mongo.db.attendance.aggregate(attendance_stats_pipeline)
    }

    students = list(mongo.db.students.find({}, {"name": 1, "email": 1, "dept": 1, "created_at": 1}))
    response = []

    for student in students:
        sid = str(student["_id"])
        stats = attendance_stats.get(sid, {})
        present_days = stats.get("present_days", 0)
        attendance_percentage = round((present_days / total_sessions) * 100, 2) if total_sessions else 0

        response.append({
            "student_id": sid,
            "name": student.get("name", ""),
            "email": student.get("email", ""),
            "dept": student.get("dept", ""),
            "present_days": present_days,
            "total_sessions": total_sessions,
            "attendance_percentage": attendance_percentage,
            "last_seen_date": stats.get("last_date"),
            "last_seen_time": stats.get("last_time")
        })

    response.sort(key=lambda s: (s.get("name") or "").lower())
    return jsonify({"students": response, "total_students": len(response), "total_sessions": total_sessions})

# --- DASHBOARD ROUTES ---

@app.route('/api/dashboard/hod', methods=['GET'])
@token_required
def get_hod_dashboard(current_user):
    if current_user['role'] != 'hod':
        return jsonify({"message": "Unauthorized"}), 403

    total_students = mongo.db.students.count_documents({})
    total_faculty = mongo.db.users.count_documents({"role": "faculty"})
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")

    # Last 7 days trend
    dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
    attendance_trend = []
    for date in dates:
        day_count = mongo.db.attendance.count_documents({"date": date})
        day_rate = round((day_count / total_students) * 100, 2) if total_students else 0
        attendance_trend.append({"date": date, "count": day_count, "rate": day_rate})

    today_attendance = mongo.db.attendance.count_documents({"date": today_str})
    today_attendance_rate = round((today_attendance / total_students) * 100, 2) if total_students else 0

    # Sessions are treated as unique attendance dates in system
    session_dates = mongo.db.attendance.distinct("date")
    total_sessions = len(session_dates)

    # Present days per student
    pipeline = [
        {"$group": {"_id": "$student_id", "present_days": {"$sum": 1}}}
    ]
    present_by_student = {
        item["_id"]: item["present_days"]
        for item in mongo.db.attendance.aggregate(pipeline)
    }

    students = list(mongo.db.students.find({}, {"name": 1, "email": 1, "dept": 1}))
    defaulters = []
    all_percentages = []

    for student in students:
        sid = str(student["_id"])
        present_days = present_by_student.get(sid, 0)
        attendance_percentage = round((present_days / total_sessions) * 100, 2) if total_sessions else 0
        all_percentages.append(attendance_percentage)

        if total_sessions > 0 and attendance_percentage < 75:
            defaulters.append({
                "name": student.get("name", "Unknown"),
                "email": student.get("email", ""),
                "dept": student.get("dept", ""),
                "attendance_percentage": attendance_percentage,
                "present_days": present_days,
                "total_sessions": total_sessions
            })

    defaulters.sort(key=lambda x: x["attendance_percentage"])

    # Department-wise attendance view for today
    dept_map = {}
    today_present_ids = set(mongo.db.attendance.distinct("student_id", {"date": today_str}))
    for student in students:
        dept = (student.get("dept") or "Unassigned").strip() or "Unassigned"
        sid = str(student["_id"])
        if dept not in dept_map:
            dept_map[dept] = {"dept": dept, "total_students": 0, "present_today": 0}
        dept_map[dept]["total_students"] += 1
        if sid in today_present_ids:
            dept_map[dept]["present_today"] += 1

    dept_overview = []
    for item in dept_map.values():
        rate = round((item["present_today"] / item["total_students"]) * 100, 2) if item["total_students"] else 0
        dept_overview.append({**item, "attendance_rate": rate})
    dept_overview.sort(key=lambda x: x["dept"])

    average_attendance_rate = round(sum(all_percentages) / len(all_percentages), 2) if all_percentages else 0

    return jsonify({
        "stats": {
            "total_students": total_students,
            "active_faculty": total_faculty,
            "today_attendance": today_attendance,
            "today_attendance_rate": today_attendance_rate,
            "average_attendance_rate": average_attendance_rate,
            "total_sessions": total_sessions
        },
        "attendance_trend": attendance_trend,
        "defaulters": defaulters[:5],
        "defaulter_count": len(defaulters),
        "dept_overview": dept_overview
    })

@app.route('/api/dashboard/student', methods=['GET'])
@token_required
def get_student_dashboard(current_user):
    # Find student record linked to this user email
    student = mongo.db.students.find_one({"email": current_user['email']})

    attendance_history = []
    attendance_percentage = 0
    summary = {
        "present_days": 0,
        "absent_days": 0,
        "total_sessions": 0,
        "current_streak": 0
    }
    recent_sessions = []

    if student:
        student_id = str(student["_id"])
        attendance_history = list(
            mongo.db.attendance.find({"student_id": student_id}, {"_id": 0}).sort("date", -1)
        )

        all_session_dates = sorted(mongo.db.attendance.distinct("date"), reverse=True)
        total_sessions = len(all_session_dates)
        present_days = len(attendance_history)
        attendance_percentage = round((present_days / total_sessions) * 100, 2) if total_sessions else 0
        absent_days = max(total_sessions - present_days, 0)

        by_date = {item["date"]: item for item in attendance_history}

        # Build last 7 sessions with Present/Absent status
        for date in all_session_dates[:7]:
            day_log = by_date.get(date)
            if day_log:
                recent_sessions.append({
                    "date": date,
                    "status": "Present",
                    "time": day_log.get("time", "--:--:--")
                })
            else:
                recent_sessions.append({
                    "date": date,
                    "status": "Absent",
                    "time": "--:--:--"
                })

        # Current streak over latest sessions
        current_streak = 0
        for date in all_session_dates:
            if date in by_date:
                current_streak += 1
            else:
                break

        summary = {
            "present_days": present_days,
            "absent_days": absent_days,
            "total_sessions": total_sessions,
            "current_streak": current_streak
        }

    return jsonify({
        "student_details": {
            "name": current_user.get('name', current_user.get('email', 'Student')),
            "dept": current_user.get('dept', student.get('dept', 'N/A') if student else 'N/A'),
            "email": current_user.get('email', '')
        },
        "attendance_percentage": attendance_percentage,
        "summary": summary,
        "recent_sessions": recent_sessions,
        "history": attendance_history[:20]
    })

# --- LEAVE ROUTES ---

@app.route('/api/leave/apply', methods=['POST'])
@token_required
def apply_leave(current_user):
    if current_user['role'] != 'student':
        return jsonify({"message": "Only students can apply"}), 403
    
    data = request.json
    leave_app = {
        "student_id": data.get('student_id', str(current_user.get('_id', 'unknown'))), # better to use ID
        "email": current_user['email'],
        "name": current_user['name'],
        "type": data.get('type', 'Sick Leave'),
        "from_date": data.get('from_date'),
        "to_date": data.get('to_date'),
        "reason": data.get('reason'),
        "status": "Pending",
        "applied_on": datetime.now()
    }
    mongo.db.leaves.insert_one(leave_app)
    return jsonify({"message": "Leave Applied Successfully"}), 201

@app.route('/api/leave/all', methods=['GET'])
@token_required
def get_all_leaves(current_user):
    if current_user['role'] not in ['hod', 'faculty']:
        return jsonify({"message": "Unauthorized"}), 403
    
    leaves = list(mongo.db.leaves.find({}, {'_id': 0}).sort('applied_on', -1))
    return jsonify(leaves)

@app.route('/api/leave/my', methods=['GET'])
@token_required
def get_my_leaves(current_user):
    leaves = list(mongo.db.leaves.find({"email": current_user['email']}, {'_id': 0}).sort('applied_on', -1))
    return jsonify(leaves)

@app.route('/api/leave/action', methods=['POST'])
@token_required
def leave_action(current_user):
    if current_user['role'] not in ['hod', 'faculty']:
        return jsonify({"message": "Unauthorized"}), 403
        
    data = request.json
    # In real app use _id, here using email + date for simplicity logic
    # Assuming data has identifier
    mongo.db.leaves.update_one(
        {"email": data['email'], "from_date": data['from_date']}, # risky matcher but ok for mvp
        {"$set": {"status": data['status'], "action_by": current_user['name']}}
    )
    return jsonify({"message": f"Leave {data['status']}"})




if __name__ == '__main__':
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host='0.0.0.0', port=port, debug=debug)
