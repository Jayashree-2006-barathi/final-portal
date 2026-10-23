"""
app.py - Greenfield University Student Course Registration Portal Backend
Flask API & Application Server
"""

import os
import re
import secrets
import datetime
import sqlite3
import traceback
from functools import wraps
from flask import Flask, request, jsonify, session, send_from_directory, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

import database

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder="static")
app.secret_key = os.getenv("SECRET_KEY", "greenfield-fallback-secret-2026")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False  # Set to True if running behind HTTPS

# Initialize DB on start
database.init_db()


@app.before_request
def handle_cors_preflight():
    if request.method == "OPTIONS":
        res = app.make_default_options_response()
        res.headers["Access-Control-Allow-Origin"] = "*"
        res.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        res.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
        return res


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    return response



def login_required(f):
    """Decorator to protect student API endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "student_id" not in session:
            return jsonify({"error": "Unauthorized. Please sign in to continue."}), 401
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to protect administrator API endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("is_admin"):
            return jsonify({"error": "Admin access required. Please sign in as an administrator."}), 403
        return f(*args, **kwargs)
    return decorated_function


def get_current_student():
    """Helper to fetch logged-in student row."""
    if "student_id" not in session:
        return None
    conn = database.get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, student_id, name, email, department, program, semester FROM students WHERE id = ?", (session["student_id"],))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ===================================================================
# AUTHENTICATION ENDPOINTS
# ===================================================================

@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")
    confirm_password = str(data.get("confirm_password") or "")
    department = str(data.get("department") or "Computer Science").strip()
    program = str(data.get("program") or f"B.Tech {department}").strip()

    # Validations
    if not name:
        return jsonify({"error": "Full name is required."}), 400
    if len(name) < 2:
        return jsonify({"error": "Name must be at least 2 characters long."}), 400

    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not email or not re.match(email_regex, email):
        return jsonify({"error": "Please enter a valid email address."}), 400

    if not password:
        return jsonify({"error": "Password is required."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long."}), 400
    if password != confirm_password:
        return jsonify({"error": "Passwords do not match."}), 400

    conn = database.get_db_connection()
    try:
        cursor = conn.cursor()
        # Check duplicate email (case-insensitive)
        cursor.execute("SELECT id FROM students WHERE LOWER(TRIM(email)) = LOWER(TRIM(?))", (email,))
        if cursor.fetchone():
            return jsonify({"error": "An account with this email address already exists. Please sign in instead."}), 409

        # Generate unique Student ID: STU-2026-XXX guaranteed never to collide
        cursor.execute("SELECT student_id FROM students WHERE student_id LIKE 'STU-2026-%'")
        existing_ids = {row["student_id"] for row in cursor.fetchall()}
        next_num = 101
        while f"STU-2026-{next_num:03d}" in existing_ids:
            next_num += 1
        student_id_str = f"STU-2026-{next_num:03d}"

        # Hash password securely
        pwd_hash = generate_password_hash(password)

        cursor.execute("""
            INSERT INTO students (student_id, name, email, password_hash, department, program, semester)
            VALUES (?, ?, ?, ?, ?, ?, 5)
        """, (student_id_str, name, email, pwd_hash, department, program))
        new_id = cursor.lastrowid
        conn.commit()

        # Establish session
        session["student_id"] = new_id

        return jsonify({
            "success": True,
            "message": "Registration successful! Welcome to Greenfield University.",
            "student": {
                "id": new_id,
                "student_id": student_id_str,
                "name": name,
                "email": email,
                "department": department,
                "program": program,
                "semester": 5
            }
        }), 201
    except sqlite3.IntegrityError as err:
        conn.rollback()
        err_str = str(err).lower()
        if "email" in err_str:
            return jsonify({"error": "An account with this email address already exists. Please sign in instead."}), 409
        elif "student_id" in err_str:
            return jsonify({"error": "Student ID generation conflict occurred. Please submit again."}), 409
        return jsonify({"error": f"Database integrity error: {str(err)}"}), 409
    except Exception as err:
        conn.rollback()
        traceback.print_exc()
        return jsonify({"error": f"Registration failed: {str(err)}"}), 500
    finally:
        conn.close()


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    identifier = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not identifier:
        return jsonify({"error": "Email or Student ID is required."}), 400
    if not password:
        return jsonify({"error": "Password is required."}), 400

    conn = database.get_db_connection()
    try:
        cursor = conn.cursor()
        # Allow sign in with either email or student_id
        cursor.execute("""
            SELECT id, student_id, name, email, password_hash, department, program, semester 
            FROM students 
            WHERE LOWER(email) = ? OR LOWER(student_id) = ?
        """, (identifier, identifier))
        student = cursor.fetchone()

        if student and check_password_hash(student["password_hash"], password):
            session["student_id"] = student["id"]
            session.pop("is_admin", None)
            session.pop("admin_id", None)
            session.pop("admin_name", None)

            return jsonify({
                "success": True,
                "role": "student",
                "message": f"Welcome back, {student['name']}!",
                "student": {
                    "id": student["id"],
                    "student_id": student["student_id"],
                    "name": student["name"],
                    "email": student["email"],
                    "department": student["department"],
                    "program": student["program"],
                    "semester": student["semester"]
                }
            })

        # Check if credentials match administrator account
        cursor.execute("""
            SELECT id, username, name, email, password_hash, role
            FROM admins
            WHERE LOWER(email) = ? OR LOWER(username) = ?
        """, (identifier, identifier))
        admin = cursor.fetchone()

        if admin and check_password_hash(admin["password_hash"], password):
            session["admin_id"] = admin["id"]
            session["is_admin"] = True
            session["admin_name"] = admin["name"]
            session.pop("student_id", None)

            return jsonify({
                "success": True,
                "role": "admin",
                "message": f"Welcome back, Administrator {admin['name']}!",
                "admin": {
                    "id": admin["id"],
                    "username": admin["username"],
                    "name": admin["name"],
                    "email": admin["email"],
                    "role": admin["role"]
                }
            })

        return jsonify({"error": "Invalid email/ID or password. Please try again."}), 401
    finally:
        conn.close()


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Signed out successfully."})


@app.route("/api/auth/me", methods=["GET"])
def me():
    if session.get("is_admin"):
        return jsonify({
            "authenticated": True,
            "role": "admin",
            "is_admin": True,
            "admin": {
                "id": session.get("admin_id"),
                "name": session.get("admin_name", "Registrar Admin"),
                "role": "Administrator"
            }
        })

    student = get_current_student()
    if not student:
        return jsonify({"authenticated": False, "student": None}), 401
    return jsonify({"authenticated": True, "role": "student", "student": student})


@app.route("/api/auth/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()

    if not email:
        return jsonify({"error": "Please enter your registered email address."}), 400

    conn = database.get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM students WHERE LOWER(email) = ?", (email,))
        student = cursor.fetchone()

        if not student:
            # For security, avoid account enumeration or give helpful note
            return jsonify({
                "success": False,
                "error": "No account found with this email address. Please check your email or register."
            }), 404

        token = secrets.token_urlsafe(32)
        expires_at = (datetime.datetime.now() + datetime.timedelta(hours=2)).isoformat()

        cursor.execute("""
            INSERT INTO password_resets (student_id, token, expires_at)
            VALUES (?, ?, ?)
        """, (student["id"], token, expires_at))
        conn.commit()

        return jsonify({
            "success": True,
            "message": "Password reset link generated successfully.",
            "reset_token": token,
            "reset_url": f"/#reset-password?token={token}"
        })
    finally:
        conn.close()


@app.route("/api/auth/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json(silent=True) or {}
    token = data.get("token", "").strip()
    new_password = data.get("new_password", "")
    confirm_password = data.get("confirm_password", "")

    if not token:
        return jsonify({"error": "Reset token is required."}), 400
    if not new_password or len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters long."}), 400
    if new_password != confirm_password:
        return jsonify({"error": "Passwords do not match."}), 400

    conn = database.get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, student_id, expires_at, used 
            FROM password_resets 
            WHERE token = ?
        """, (token,))
        reset_record = cursor.fetchone()

        if not reset_record:
            return jsonify({"error": "Invalid or expired reset token."}), 400
        if reset_record["used"] == 1:
            return jsonify({"error": "This reset token has already been used. Please request a new one."}), 400

        expires_at = datetime.datetime.fromisoformat(reset_record["expires_at"])
        if datetime.datetime.now() > expires_at:
            return jsonify({"error": "This reset token has expired. Please request a new one."}), 400

        # Update password
        new_hash = generate_password_hash(new_password)
        cursor.execute("UPDATE students SET password_hash = ? WHERE id = ?", (new_hash, reset_record["student_id"]))
        cursor.execute("UPDATE password_resets SET used = 1 WHERE id = ?", (reset_record["id"],))
        conn.commit()

        return jsonify({
            "success": True,
            "message": "Your password has been successfully reset. You can now sign in with your new password."
        })
    finally:
        conn.close()


# ===================================================================
# COURSE CATALOGUE ENDPOINTS
# ===================================================================

@app.route("/api/courses", methods=["GET"], strict_slashes=False)
@app.route("/api/courses/", methods=["GET"], strict_slashes=False)
def get_courses():
    search = request.args.get("search", "")
    department = request.args.get("department", "All")
    availability = request.args.get("availability", "All")
    schedule_day = request.args.get("schedule", "All")
    credits_val = request.args.get("credits", "All")

    courses = database.get_courses_list(
        search=search,
        department=department,
        availability=availability,
        schedule_day=schedule_day,
        credits_val=credits_val
    )

    # If student is logged in, attach their current enrollment status for each course
    student_id = session.get("student_id")
    if student_id:
        conn = database.get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT course_id, status, waitlist_position 
                FROM enrollments 
                WHERE student_id = ? AND status IN ('Enrolled', 'Waitlisted')
            """, (student_id,))
            my_records = {row["course_id"]: dict(row) for row in cursor.fetchall()}
            for c in courses:
                rec = my_records.get(c["id"])
                if rec:
                    c["my_status"] = rec["status"]
                    c["my_waitlist_position"] = rec["waitlist_position"]
                else:
                    c["my_status"] = None
                    c["my_waitlist_position"] = None
        finally:
            conn.close()
    else:
        for c in courses:
            c["my_status"] = None
            c["my_waitlist_position"] = None

    return jsonify({"courses": courses, "count": len(courses)})


@app.route("/api/courses/<int:course_id>", methods=["GET"])
def get_course_detail(course_id):
    course = database.get_course_with_enrollment_counts(course_id)
    if not course:
        return jsonify({"error": "Course not found."}), 404

    # Check student enrollment status
    student_id = session.get("student_id")
    course["my_status"] = None
    course["my_waitlist_position"] = None

    if student_id:
        conn = database.get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT status, waitlist_position, enrolled_at 
                FROM enrollments 
                WHERE student_id = ? AND course_id = ? AND status IN ('Enrolled', 'Waitlisted')
                ORDER BY id DESC LIMIT 1
            """, (student_id, course_id))
            rec = cursor.fetchone()
            if rec:
                course["my_status"] = rec["status"]
                course["my_waitlist_position"] = rec["waitlist_position"]
                course["my_enrolled_at"] = rec["enrolled_at"]
        finally:
            conn.close()

    return jsonify({"course": course})


# ===================================================================
# ENROLMENT & WITHDRAWAL ENDPOINTS
# ===================================================================

@app.route("/api/enrollments", methods=["POST"])
@login_required
def enroll():
    data = request.get_json(silent=True) or {}
    course_id = data.get("course_id")

    if not course_id:
        return jsonify({"error": "course_id is required."}), 400

    try:
        course_id = int(course_id)
    except ValueError:
        return jsonify({"error": "Invalid course_id format."}), 400

    student_id = session["student_id"]

    try:
        success, status, message, details = database.enroll_student_in_course(student_id, course_id)
        if not success:
            return jsonify({"error": message, "status": status}), 400

        # Return updated course and enrollment details
        updated_course = database.get_course_with_enrollment_counts(course_id)
        return jsonify({
            "success": True,
            "message": message,
            "status": status,
            "details": details,
            "course": updated_course
        }), 200
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred during enrolment: {str(e)}"}), 500


@app.route("/api/enrollments/<int:course_id>/withdraw", methods=["POST"])
@login_required
def withdraw(course_id):
    student_id = session["student_id"]

    try:
        success, message, details = database.withdraw_student_from_course(student_id, course_id)
        if not success:
            return jsonify({"error": message}), 400

        updated_course = database.get_course_with_enrollment_counts(course_id)
        return jsonify({
            "success": True,
            "message": message,
            "details": details,
            "course": updated_course
        }), 200
    except Exception as e:
        return jsonify({"error": f"An error occurred while withdrawing: {str(e)}"}), 500


@app.route("/api/enrollments/my", methods=["GET"])
@login_required
def my_enrollments():
    student_id = session["student_id"]
    dashboard_data = database.get_student_dashboard_data(student_id)
    return jsonify(dashboard_data)


@app.route("/api/student/dashboard", methods=["GET"])
@login_required
def student_dashboard():
    student_id = session["student_id"]
    dashboard_data = database.get_student_dashboard_data(student_id)
    if not dashboard_data:
        return jsonify({"error": "Student record not found."}), 404
    return jsonify(dashboard_data)


# ===================================================================
# ADMINISTRATOR DASHBOARD & MANAGEMENT API
# ===================================================================

@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    """Explicit admin login route."""
    data = request.get_json(silent=True) or {}
    identifier = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not identifier or not password:
        return jsonify({"error": "Email/username and password are required."}), 400

    conn = database.get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, name, email, password_hash, role
            FROM admins
            WHERE LOWER(email) = ? OR LOWER(username) = ?
        """, (identifier, identifier))
        admin = cursor.fetchone()

        if not admin or not check_password_hash(admin["password_hash"], password):
            return jsonify({"error": "Invalid administrator credentials."}), 401

        session["admin_id"] = admin["id"]
        session["is_admin"] = True
        session["admin_name"] = admin["name"]
        session.pop("student_id", None)

        return jsonify({
            "success": True,
            "role": "admin",
            "message": f"Welcome back, {admin['name']}!",
            "admin": {
                "id": admin["id"],
                "username": admin["username"],
                "name": admin["name"],
                "email": admin["email"],
                "role": admin["role"]
            }
        })
    finally:
        conn.close()


@app.route("/api/admin/me", methods=["GET"])
@admin_required
def admin_me():
    return jsonify({
        "authenticated": True,
        "is_admin": True,
        "admin": {
            "id": session.get("admin_id"),
            "name": session.get("admin_name", "Registrar Admin"),
            "role": "Administrator"
        }
    })


@app.route("/api/admin/stats", methods=["GET"])
@admin_required
def admin_stats():
    stats = database.get_admin_stats()
    return jsonify(stats)


@app.route("/api/admin/students", methods=["GET"])
@admin_required
def admin_students():
    students = database.get_admin_students()
    return jsonify({"students": students, "count": len(students)})


@app.route("/api/admin/students/<int:student_id>/enrollments", methods=["GET"])
@admin_required
def admin_student_enrollments(student_id):
    data = database.get_student_dashboard_data(student_id)
    if not data:
        return jsonify({"error": "Student not found."}), 404
    return jsonify(data)


@app.route("/api/admin/enrollments", methods=["GET"])
@admin_required
def admin_enrollments():
    status = request.args.get("status", "All")
    course_id = request.args.get("course_id")
    if course_id:
        try:
            course_id = int(course_id)
        except ValueError:
            course_id = None

    enrollments = database.get_admin_enrollments(status=status, course_id=course_id)
    return jsonify({"enrollments": enrollments, "count": len(enrollments)})


@app.route("/api/admin/courses", methods=["GET"])
@admin_required
def admin_courses():
    courses = database.get_courses_list()
    return jsonify({"courses": courses, "count": len(courses)})


@app.route("/api/admin/courses", methods=["POST"])
@admin_required
def admin_create_course():
    data = request.get_json(silent=True) or {}
    code = data.get("code", "").strip().upper()
    title = data.get("title", "").strip()
    if not code:
        return jsonify({"error": "Course code is required (e.g., CS305)."}), 400
    if not title:
        return jsonify({"error": "Course title is required."}), 400

    try:
        new_course = database.create_course(data)
        return jsonify({
            "success": True,
            "message": f"Course {code} created successfully.",
            "course": new_course
        }), 201
    except Exception as e:
        return jsonify({"error": f"Failed to create course: {str(e)}"}), 400


@app.route("/api/admin/courses/<int:course_id>", methods=["PUT"])
@admin_required
def admin_update_course(course_id):
    data = request.get_json(silent=True) or {}
    try:
        updated = database.update_course(course_id, data)
        if not updated:
            return jsonify({"error": "Course not found."}), 404
        return jsonify({
            "success": True,
            "message": "Course details updated successfully.",
            "course": updated
        })
    except Exception as e:
        return jsonify({"error": f"Failed to update course: {str(e)}"}), 400


@app.route("/api/admin/courses/<int:course_id>/toggle-status", methods=["POST"])
@admin_required
def admin_toggle_course_status(course_id):
    updated = database.toggle_course_status(course_id)
    if not updated:
        return jsonify({"error": "Course not found."}), 404
    status_label = "Closed" if updated.get("is_closed") else "Open"
    return jsonify({
        "success": True,
        "message": f"Registration status for {updated['code']} changed to {status_label}.",
        "course": updated
    })


@app.route("/api/admin/courses/<int:course_id>", methods=["DELETE"])
@admin_required
def admin_delete_course(course_id):
    success, message = database.delete_course(course_id)
    if not success:
        return jsonify({"error": message}), 404
    return jsonify({"success": True, "message": message})


@app.route("/api/admin/enrollments/<int:enrollment_id>/drop", methods=["POST"])
@admin_required
def admin_drop_enrollment(enrollment_id):
    try:
        success, message, details = database.admin_drop_enrollment(enrollment_id)
        if not success:
            return jsonify({"error": message}), 400
        return jsonify({
            "success": True,
            "message": message,
            "details": details
        })
    except Exception as e:
        return jsonify({"error": f"Failed to drop enrollment: {str(e)}"}), 500


# ===================================================================
# ERROR HANDLERS
# ===================================================================

@app.errorhandler(404)
def handle_404(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": f"API endpoint not found: {request.path}"}), 404
    return send_from_directory(".", "index.html")


@app.errorhandler(500)
def handle_500(e):
    traceback.print_exc()
    if request.path.startswith("/api/"):
        err_detail = getattr(e, "description", str(e))
        return jsonify({"error": f"Internal server error: {err_detail}"}), 500
    return "Internal Server Error", 500


# ===================================================================
# FRONTEND ENTRY POINT & STATIC ASSETS
# ===================================================================

@app.route("/")
def index():
    """Serves the single-page application."""
    return send_from_directory(".", "index.html")


@app.route("/<path:path>")
def static_proxy(path):
    """Fallback to allow deep linking or static assets."""
    if path.startswith("api/"):
        return jsonify({"error": f"API endpoint not found: /{path}"}), 404
    if os.path.exists(path):
        return send_from_directory(".", path)
    return send_from_directory(".", "index.html")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Starting Greenfield University ERP Course Registration Portal on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=True)
