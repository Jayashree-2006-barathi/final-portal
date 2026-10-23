"""
database.py - Database connection, schema setup, seed data, and atomic course operations
"""

import os
import sqlite3
import datetime
from werkzeug.security import generate_password_hash

DATABASE_PATH = os.getenv("DATABASE_PATH", "greenfield_erp.db")


def get_db_connection(db_path=None):
    """Returns a SQLite connection with row_factory and foreign keys enabled."""
    path = db_path or os.getenv("DATABASE_PATH", DATABASE_PATH)
    conn = sqlite3.connect(path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


def init_db(db_path=None):
    """Initializes tables and seeds initial data if not already populated."""
    conn = get_db_connection(db_path)
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            department TEXT NOT NULL DEFAULT 'Computer Science',
            program TEXT NOT NULL DEFAULT 'B.Tech Computer Science',
            semester INTEGER NOT NULL DEFAULT 5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            department TEXT NOT NULL,
            instructor TEXT NOT NULL,
            credits INTEGER NOT NULL DEFAULT 3,
            schedule TEXT NOT NULL,
            days TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            room TEXT NOT NULL,
            capacity INTEGER NOT NULL,
            waitlist_capacity INTEGER NOT NULL DEFAULT 10,
            is_closed INTEGER NOT NULL DEFAULT 0,
            description TEXT NOT NULL,
            prerequisites TEXT,
            term TEXT NOT NULL DEFAULT 'Fall 2026',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
            status TEXT NOT NULL CHECK(status IN ('Enrolled', 'Waitlisted', 'Withdrawn')),
            waitlist_position INTEGER DEFAULT NULL,
            enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Administrator',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_enrollments_student ON enrollments(student_id);
        CREATE INDEX IF NOT EXISTS idx_enrollments_course ON enrollments(course_id);
        CREATE INDEX IF NOT EXISTS idx_enrollments_status ON enrollments(course_id, status);
        CREATE INDEX IF NOT EXISTS idx_courses_dept ON courses(department);
        """)

    # Seed default admin if missing
    with conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS count FROM admins")
        if cursor.fetchone()["count"] == 0:
            admin_pwd = generate_password_hash("admin123")
            cursor.execute("""
                INSERT INTO admins (username, name, email, password_hash, role)
                VALUES (?, ?, ?, ?, ?)
            """, ("admin", "Registrar Admin", "admin@greenfield.edu", admin_pwd, "Administrator"))

    # Seed data if empty
    seed_if_empty(conn)
    conn.close()


def seed_if_empty(conn):
    """Seeds sample students and a comprehensive course catalogue if courses table is empty."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS count FROM courses")
    if cursor.fetchone()["count"] > 0:
        return

    # Seed default students
    # Default student: Alex Morgan (demo account matching ERP prototype)
    hashed_pwd = generate_password_hash("demo123")
    students_data = [
        ("STU-2026-001", "Alex Morgan", "alex.morgan@greenfield.edu", hashed_pwd, "Computer Science", "B.Tech Computer Science, Sem 5", 5),
        ("STU-2026-002", "Jordan Lee", "jordan.l@greenfield.edu", hashed_pwd, "Computer Science", "B.Tech Computer Science, Sem 5", 5),
        ("STU-2026-003", "Samira Patel", "samira.p@greenfield.edu", hashed_pwd, "Electrical Engineering", "B.Tech Electrical Eng, Sem 3", 3),
        ("STU-2026-004", "Marcus Johnson", "marcus.j@greenfield.edu", hashed_pwd, "Business Administration", "BBA Business Admin, Sem 5", 5),
        ("STU-2026-005", "Emily Chen", "emily.c@greenfield.edu", hashed_pwd, "Biology", "B.S. Molecular Biology, Sem 4", 4),
    ]

    cursor.executemany("""
        INSERT INTO students (student_id, name, email, password_hash, department, program, semester)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, students_data)

    # Seed diverse, realistic courses
    sample_courses = [
        (
            "CS301",
            "Data Structures & Algorithms",
            "Computer Science",
            "Dr. Wei Chen",
            4,
            "MWF 09:00 - 10:15",
            "MWF",
            "09:00 - 10:15",
            "Science Hall 301",
            30,
            10,
            0,
            "Fundamental algorithms and data structures: balanced trees, hash tables, graph algorithms, and asymptotic complexity analysis with hands-on implementation.",
            "CS201 Programming Fundamentals",
            "Fall 2026"
        ),
        (
            "CS405",
            "Database Systems & Design",
            "Computer Science",
            "Prof. Sarah Williams",
            3,
            "TTh 11:00 - 12:15",
            "TTh",
            "11:00 - 12:15",
            "Turing Hall 205",
            28,
            8,
            0,
            "Relational database design, SQL querying, indexing, transaction processing, concurrency control, and introduction to modern NoSQL and distributed stores.",
            "CS201 Programming Fundamentals",
            "Fall 2026"
        ),
        (
            "CS502",
            "Machine Learning & Pattern Recognition",
            "Computer Science",
            "Dr. Aris Thorne",
            4,
            "TTh 14:00 - 15:30",
            "TTh",
            "14:00 - 15:30",
            "AI Innovation Lab 401",
            24,
            10,
            0,
            "Supervised and unsupervised learning, linear models, neural networks, decision trees, reinforcement learning, and real-world evaluation methodologies.",
            "MA301 Linear Algebra & CS301",
            "Fall 2026"
        ),
        (
            "CS310",
            "Computer Networks & Protocols",
            "Computer Science",
            "Prof. David Miller",
            3,
            "MWF 11:30 - 12:30",
            "MWF",
            "11:30 - 12:30",
            "Engineering Center 302",
            32,
            5,
            0,
            "Architectural layers of computer communication, TCP/IP, routing algorithms, socket programming, network security, and modern cloud topologies.",
            "CS201 Programming Fundamentals",
            "Fall 2026"
        ),
        (
            "MA301",
            "Linear Algebra & Matrix Theory",
            "Mathematics",
            "Dr. Priya Kumar",
            3,
            "MWF 10:30 - 11:30",
            "MWF",
            "10:30 - 11:30",
            "Newton Hall 108",
            35,
            10,
            0,
            "Vector spaces, linear transformations, matrices, eigenvalues and eigenvectors, singular value decomposition, and computational applications.",
            "MA102 Calculus II",
            "Fall 2026"
        ),
        (
            "MA202",
            "Probability & Applied Statistics",
            "Mathematics",
            "Prof. Raymond Zhang",
            3,
            "TTh 09:30 - 10:45",
            "TTh",
            "09:30 - 10:45",
            "Newton Hall 112",
            30,
            8,
            0,
            "Discrete and continuous distributions, random variables, hypothesis testing, regression analysis, Bayesian inference, and Monte Carlo techniques.",
            "MA101 Calculus I",
            "Fall 2026"
        ),
        (
            "BIO210",
            "Genetics & Molecular Biology",
            "Biology",
            "Dr. Elena Rostova",
            4,
            "MWF 13:00 - 14:15",
            "MWF",
            "13:00 - 14:15",
            "Darwin Science Wing 204",
            25,
            5,
            0,
            "Mendelian inheritance, chromosome dynamics, molecular structure of genes, gene regulation, genetic engineering, and bioethics.",
            "BIO101 General Biology",
            "Fall 2026"
        ),
        (
            "BUS320",
            "Corporate Finance & Strategy",
            "Business Administration",
            "Prof. Jonathan Sterling",
            3,
            "TTh 13:00 - 14:15",
            "TTh",
            "13:00 - 14:15",
            "School of Management 104",
            35,
            10,
            0,
            "Valuation models, capital budgeting, risk and return trade-offs, financial statement analysis, capital structure, and corporate investment strategies.",
            "BUS101 Principles of Accounting",
            "Fall 2026"
        ),
        (
            "PSY205",
            "Cognitive Psychology & Neuroscience",
            "Psychology",
            "Dr. Miriam Vance",
            3,
            "MWF 14:30 - 15:30",
            "MWF",
            "14:30 - 15:30",
            "Behavioral Sciences 210",
            30,
            6,
            0,
            "Empirical investigation of perception, attention, memory retention, language acquisition, problem solving, and underlying neural mechanisms.",
            "PSY101 Introduction to Psychology",
            "Fall 2026"
        ),
        (
            "ME304",
            "Thermodynamics & Heat Transfer",
            "Mechanical Engineering",
            "Dr. Carlos Mendez",
            4,
            "TTh 08:00 - 09:30",
            "TTh",
            "08:00 - 09:30",
            "Engineering Hall 115",
            25,
            5,
            0,
            "First and second laws of thermodynamics, energy conversion systems, vapor and gas power cycles, heat conduction, convection, and thermal radiation.",
            "PH101 General Physics I",
            "Fall 2026"
        ),
        (
            "HU201",
            "Technical Writing & Professional Comm",
            "Humanities",
            "Prof. Angela Thompson",
            2,
            "Fri 15:00 - 17:00",
            "Fri",
            "15:00 - 17:00",
            "Liberal Arts Hall 110",
            22,
            5,
            0,
            "Crafting effective technical documentation, research papers, executive summaries, design specifications, and collaborative presentations.",
            "None",
            "Fall 2026"
        ),
        (
            "CS490",
            "Capstone Senior Design Project",
            "Computer Science",
            "Dr. Wei Chen",
            4,
            "MWF 15:45 - 17:00",
            "MWF",
            "15:45 - 17:00",
            "Innovation Hub Studio A",
            2, # Small capacity to easily demonstrate waitlist & full features
            3,
            0,
            "Collaborative multi-week software engineering project encompassing product requirements, system architecture, development, CI/CD, and showcase.",
            "CS301 & CS405",
            "Fall 2026"
        ),
        (
            "CS599",
            "Special Topics in Quantum Computing",
            "Computer Science",
            "Dr. Jennifer Hayes",
            3,
            "TTh 16:00 - 17:15",
            "TTh",
            "16:00 - 17:15",
            "Quantum Research Lab 102",
            15,
            0,
            1, # CLOSED to demonstrate closed course rejection
            "Advanced exploration of quantum algorithms (Shor, Grover), qubits, entanglement, quantum circuit design, and error correction models.",
            "MA301 Linear Algebra & Instructor Consent",
            "Fall 2026"
        )
    ]

    cursor.executemany("""
        INSERT INTO courses (
            code, title, department, instructor, credits, schedule, days, time_slot,
            room, capacity, waitlist_capacity, is_closed, description, prerequisites, term
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, sample_courses)

    # Let's seed initial enrollments for Alex Morgan (STU-2026-001) in CS301 and MA301
    # and enroll a student in CS490 to demonstrate limited seats
    alex_id = 1
    jordan_id = 2
    samira_id = 3

    # Course IDs:
    # 1: CS301, 2: CS405, 3: CS502, 4: CS310, 5: MA301, 12: CS490 (capacity 2)
    cursor.executemany("""
        INSERT INTO enrollments (student_id, course_id, status, enrolled_at)
        VALUES (?, ?, ?, ?)
    """, [
        (alex_id, 1, 'Enrolled', datetime.datetime.now().isoformat()),
        (alex_id, 5, 'Enrolled', datetime.datetime.now().isoformat()),
        (jordan_id, 12, 'Enrolled', datetime.datetime.now().isoformat()),
        (samira_id, 12, 'Enrolled', datetime.datetime.now().isoformat()) # CS490 now has 2 enrolled (at full capacity!)
    ])

    conn.commit()


def get_course_with_enrollment_counts(course_id, conn=None):
    """Fetches a course by ID along with real-time enrolled_count, waitlist_count, seats_remaining, and waitlist_spots_remaining."""
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                c.*,
                COALESCE(SUM(CASE WHEN e.status = 'Enrolled' THEN 1 ELSE 0 END), 0) AS enrolled_count,
                COALESCE(SUM(CASE WHEN e.status = 'Waitlisted' THEN 1 ELSE 0 END), 0) AS waitlist_count
            FROM courses c
            LEFT JOIN enrollments e ON c.id = e.course_id
            WHERE c.id = ?
            GROUP BY c.id
        """, (course_id,))
        row = cursor.fetchone()
        if not row:
            return None

        data = dict(row)
        data['seats_remaining'] = max(0, data['capacity'] - data['enrolled_count'])
        data['waitlist_spots_remaining'] = max(0, data['waitlist_capacity'] - data['waitlist_count'])
        
        if data['is_closed']:
            data['computed_status'] = 'Closed'
        elif data['seats_remaining'] > 0:
            data['computed_status'] = 'Open'
        elif data['waitlist_spots_remaining'] > 0:
            data['computed_status'] = 'Waitlist Open'
        else:
            data['computed_status'] = 'Full'

        return data
    finally:
        if should_close:
            conn.close()


def get_courses_list(search=None, department=None, availability=None, schedule_day=None, credits_val=None, conn=None):
    """Returns a list of courses with calculated seat remaining, waitlist counts, and availability."""
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        query = """
            SELECT 
                c.*,
                COALESCE(SUM(CASE WHEN e.status = 'Enrolled' THEN 1 ELSE 0 END), 0) AS enrolled_count,
                COALESCE(SUM(CASE WHEN e.status = 'Waitlisted' THEN 1 ELSE 0 END), 0) AS waitlist_count
            FROM courses c
            LEFT JOIN enrollments e ON c.id = e.course_id
            WHERE 1=1
        """
        params = []

        if department and department != 'All':
            query += " AND c.department = ?"
            params.append(department)

        if schedule_day and schedule_day != 'All':
            query += " AND c.days LIKE ?"
            params.append(f"%{schedule_day}%")

        if credits_val and credits_val != 'All':
            try:
                query += " AND c.credits = ?"
                params.append(int(credits_val))
            except ValueError:
                pass

        if search:
            search_term = f"%{search.strip()}%"
            query += " AND (c.code LIKE ? OR c.title LIKE ? OR c.instructor LIKE ? OR c.description LIKE ?)"
            params.extend([search_term, search_term, search_term, search_term])

        query += " GROUP BY c.id ORDER BY c.code ASC"

        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            data = dict(row)
            data['seats_remaining'] = max(0, data['capacity'] - data['enrolled_count'])
            data['waitlist_spots_remaining'] = max(0, data['waitlist_capacity'] - data['waitlist_count'])
            
            if data['is_closed']:
                data['computed_status'] = 'Closed'
            elif data['seats_remaining'] > 0:
                data['computed_status'] = 'Open'
            elif data['waitlist_spots_remaining'] > 0:
                data['computed_status'] = 'Waitlist Open'
            else:
                data['computed_status'] = 'Full'

            # Availability filter applied after seat calculations
            if availability == 'Open' and data['computed_status'] != 'Open':
                continue
            if availability == 'Waitlist' and data['computed_status'] != 'Waitlist Open':
                continue
            if availability == 'Full' and data['computed_status'] not in ('Full', 'Waitlist Open'):
                continue
            if availability == 'Available' and data['computed_status'] not in ('Open', 'Waitlist Open'):
                continue

            results.append(data)

        return results
    finally:
        if should_close:
            conn.close()


def enroll_student_in_course(student_id, course_id, conn=None):
    """
    Atomically enrolls or waitlists a student in a course.
    Returns: (success: bool, status: str, message: str, enrollment_data: dict)
    """
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        # Use IMMEDIATE transaction to prevent concurrent race conditions
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.cursor()

        # 1. Fetch course details with lock
        cursor.execute("""
            SELECT * FROM courses WHERE id = ?
        """, (course_id,))
        course = cursor.fetchone()
        if not course:
            conn.rollback()
            return False, "Not Found", "Course not found", None

        # Check if course is closed
        if course["is_closed"] == 1:
            conn.rollback()
            return False, "Closed", f"Registration for {course['code']} is closed.", None

        # 2. Check student's current active status in this course
        cursor.execute("""
            SELECT id, status, waitlist_position FROM enrollments 
            WHERE student_id = ? AND course_id = ?
            ORDER BY id DESC LIMIT 1
        """, (student_id, course_id))
        existing_enrollment = cursor.fetchone()

        if existing_enrollment and existing_enrollment["status"] == "Enrolled":
            conn.rollback()
            return False, "Already Enrolled", f"You are already enrolled in {course['code']}.", None

        if existing_enrollment and existing_enrollment["status"] == "Waitlisted":
            conn.rollback()
            return False, "Already Waitlisted", f"You are already on the waitlist for {course['code']} at position #{existing_enrollment['waitlist_position']}.", None

        # 3. Check current enrolled count
        cursor.execute("""
            SELECT COUNT(*) AS count FROM enrollments 
            WHERE course_id = ? AND status = 'Enrolled'
        """, (course_id,))
        enrolled_count = cursor.fetchone()["count"]

        now = datetime.datetime.now().isoformat()

        # 4. If seats are available, enrol directly!
        if enrolled_count < course["capacity"]:
            if existing_enrollment and existing_enrollment["status"] == "Withdrawn":
                cursor.execute("""
                    UPDATE enrollments 
                    SET status = 'Enrolled', waitlist_position = NULL, updated_at = ?
                    WHERE id = ?
                """, (now, existing_enrollment["id"]))
                enrollment_id = existing_enrollment["id"]
            else:
                cursor.execute("""
                    INSERT INTO enrollments (student_id, course_id, status, waitlist_position, enrolled_at, updated_at)
                    VALUES (?, ?, 'Enrolled', NULL, ?, ?)
                """, (student_id, course_id, now, now))
                enrollment_id = cursor.lastrowid

            conn.commit()
            return True, "Enrolled", f"Successfully enrolled in {course['code']} - {course['title']}.", {
                "enrollment_id": enrollment_id,
                "status": "Enrolled",
                "course_code": course["code"],
                "course_title": course["title"]
            }

        # 5. Course is full! Check if waitlist is supported and has space
        cursor.execute("""
            SELECT COUNT(*) AS count FROM enrollments 
            WHERE course_id = ? AND status = 'Waitlisted'
        """, (course_id,))
        waitlist_count = cursor.fetchone()["count"]

        if course["waitlist_capacity"] > 0 and waitlist_count < course["waitlist_capacity"]:
            next_pos = waitlist_count + 1
            if existing_enrollment and existing_enrollment["status"] == "Withdrawn":
                cursor.execute("""
                    UPDATE enrollments 
                    SET status = 'Waitlisted', waitlist_position = ?, updated_at = ?
                    WHERE id = ?
                """, (next_pos, now, existing_enrollment["id"]))
                enrollment_id = existing_enrollment["id"]
            else:
                cursor.execute("""
                    INSERT INTO enrollments (student_id, course_id, status, waitlist_position, enrolled_at, updated_at)
                    VALUES (?, ?, 'Waitlisted', ?, ?, ?)
                """, (student_id, course_id, next_pos, now, now))
                enrollment_id = cursor.lastrowid

            conn.commit()
            return True, "Waitlisted", f"{course['code']} is currently full. You have been placed on the waitlist at position #{next_pos}.", {
                "enrollment_id": enrollment_id,
                "status": "Waitlisted",
                "waitlist_position": next_pos,
                "course_code": course["code"],
                "course_title": course["title"]
            }
        else:
            conn.rollback()
            return False, "Full", f"{course['code']} is completely full and the waitlist is unavailable or at maximum capacity.", None

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        if should_close:
            conn.close()


def withdraw_student_from_course(student_id, course_id, conn=None):
    """
    Withdraws a student from a course.
    If student was Enrolled and there are waitlisted students,
    the top waitlisted student is automatically promoted to Enrolled (FIFO),
    and remaining waitlist positions are re-sequenced.
    Returns: (success: bool, message: str, details: dict)
    """
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.cursor()

        # Find active enrollment
        cursor.execute("""
            SELECT e.id, e.status, e.waitlist_position, c.code, c.title 
            FROM enrollments e
            JOIN courses c ON e.course_id = c.id
            WHERE e.student_id = ? AND e.course_id = ? AND e.status IN ('Enrolled', 'Waitlisted')
            ORDER BY e.id DESC LIMIT 1
        """, (student_id, course_id))
        record = cursor.fetchone()

        if not record:
            conn.rollback()
            return False, "No active enrollment found for this course.", None

        previous_status = record["status"]
        now = datetime.datetime.now().isoformat()

        # Mark current student as Withdrawn
        cursor.execute("""
            UPDATE enrollments 
            SET status = 'Withdrawn', waitlist_position = NULL, updated_at = ?
            WHERE id = ?
        """, (now, record["id"]))

        promoted_student_id = None
        # If the student was Enrolled, check waitlist for top student to promote
        if previous_status == "Enrolled":
            cursor.execute("""
                SELECT id, student_id FROM enrollments 
                WHERE course_id = ? AND status = 'Waitlisted'
                ORDER BY waitlist_position ASC, enrolled_at ASC
                LIMIT 1
            """, (course_id,))
            top_waitlisted = cursor.fetchone()

            if top_waitlisted:
                promoted_student_id = top_waitlisted["student_id"]
                cursor.execute("""
                    UPDATE enrollments 
                    SET status = 'Enrolled', waitlist_position = NULL, updated_at = ?
                    WHERE id = ?
                """, (now, top_waitlisted["id"]))

        # Re-sequence remaining waitlisted students for this course
        cursor.execute("""
            SELECT id FROM enrollments 
            WHERE course_id = ? AND status = 'Waitlisted'
            ORDER BY waitlist_position ASC, enrolled_at ASC
        """, (course_id,))
        remaining_waitlisted = cursor.fetchall()
        for idx, w_rec in enumerate(remaining_waitlisted, start=1):
            cursor.execute("""
                UPDATE enrollments SET waitlist_position = ? WHERE id = ?
            """, (idx, w_rec["id"]))

        conn.commit()
        return True, f"You have successfully withdrawn from {record['code']}.", {
            "course_code": record["code"],
            "course_title": record["title"],
            "previous_status": previous_status,
            "promoted_waitlist_student": promoted_student_id
        }

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        if should_close:
            conn.close()


def get_student_dashboard_data(student_id, conn=None):
    """Fetches complete student dashboard summary, active enrollments, and enrolled credit load."""
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        # Fetch student info
        cursor.execute("SELECT id, student_id, name, email, department, program, semester FROM students WHERE id = ?", (student_id,))
        student = cursor.fetchone()
        if not student:
            return None

        # Fetch enrollments with course details
        cursor.execute("""
            SELECT 
                e.id AS enrollment_id,
                e.status AS enrollment_status,
                e.waitlist_position,
                e.enrolled_at,
                e.updated_at,
                c.id AS course_id,
                c.code,
                c.title,
                c.department,
                c.instructor,
                c.credits,
                c.schedule,
                c.days,
                c.time_slot,
                c.room,
                c.capacity,
                c.waitlist_capacity,
                c.is_closed,
                c.description,
                c.term,
                (SELECT COUNT(*) FROM enrollments sub WHERE sub.course_id = c.id AND sub.status = 'Enrolled') AS enrolled_count
            FROM enrollments e
            JOIN courses c ON e.course_id = c.id
            WHERE e.student_id = ?
            ORDER BY 
                CASE e.status 
                    WHEN 'Enrolled' THEN 1 
                    WHEN 'Waitlisted' THEN 2 
                    ELSE 3 
                END,
                e.enrolled_at DESC
        """, (student_id,))
        rows = cursor.fetchall()

        enrollments = []
        enrolled_count = 0
        waitlisted_count = 0
        withdrawn_count = 0
        total_enrolled_credits = 0

        for r in rows:
            item = dict(r)
            item['seats_remaining'] = max(0, item['capacity'] - item['enrolled_count'])
            if item['enrollment_status'] == 'Enrolled':
                enrolled_count += 1
                total_enrolled_credits += item['credits']
            elif item['enrollment_status'] == 'Waitlisted':
                waitlisted_count += 1
            elif item['enrollment_status'] == 'Withdrawn':
                withdrawn_count += 1
            enrollments.append(item)

        return {
            "student": dict(student),
            "stats": {
                "enrolled_courses": enrolled_count,
                "waitlisted_courses": waitlisted_count,
                "withdrawn_courses": withdrawn_count,
                "total_credits": total_enrolled_credits,
                "max_credits": 18
            },
            "enrollments": enrollments
        }
    finally:
        if should_close:
            conn.close()


# ===================================================================
# ADMIN OPERATIONS & METRICS
# ===================================================================

def get_admin_stats(conn=None):
    """Fetches high-level metrics for admin dashboard."""
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS student_count FROM students")
        student_count = cursor.fetchone()["student_count"]

        cursor.execute("SELECT COUNT(*) AS course_count, COALESCE(SUM(capacity), 0) AS total_capacity, COALESCE(SUM(waitlist_capacity), 0) AS total_waitlist_capacity FROM courses")
        course_row = cursor.fetchone()
        course_count = course_row["course_count"]
        total_capacity = course_row["total_capacity"]
        total_waitlist_capacity = course_row["total_waitlist_capacity"]

        cursor.execute("SELECT COUNT(*) AS enrolled_count FROM enrollments WHERE status = 'Enrolled'")
        enrolled_count = cursor.fetchone()["enrolled_count"]

        cursor.execute("SELECT COUNT(*) AS waitlist_count FROM enrollments WHERE status = 'Waitlisted'")
        waitlist_count = cursor.fetchone()["waitlist_count"]

        cursor.execute("SELECT COUNT(*) AS withdrawn_count FROM enrollments WHERE status = 'Withdrawn'")
        withdrawn_count = cursor.fetchone()["withdrawn_count"]

        cursor.execute("SELECT COUNT(DISTINCT department) AS dept_count FROM courses")
        dept_count = cursor.fetchone()["dept_count"]

        utilization = round((enrolled_count / total_capacity * 100), 1) if total_capacity > 0 else 0

        return {
            "student_count": student_count,
            "course_count": course_count,
            "total_capacity": total_capacity,
            "total_waitlist_capacity": total_waitlist_capacity,
            "enrolled_count": enrolled_count,
            "waitlist_count": waitlist_count,
            "withdrawn_count": withdrawn_count,
            "dept_count": dept_count,
            "utilization": utilization
        }
    finally:
        if should_close:
            conn.close()


def get_admin_students(conn=None):
    """Lists all students with active enrollment statistics."""
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                s.id,
                s.student_id,
                s.name,
                s.email,
                s.department,
                s.program,
                s.semester,
                s.created_at,
                (SELECT COUNT(*) FROM enrollments e WHERE e.student_id = s.id AND e.status = 'Enrolled') AS enrolled_count,
                (SELECT COUNT(*) FROM enrollments e WHERE e.student_id = s.id AND e.status = 'Waitlisted') AS waitlist_count,
                (SELECT COALESCE(SUM(c.credits), 0) FROM enrollments e JOIN courses c ON e.course_id = c.id WHERE e.student_id = s.id AND e.status = 'Enrolled') AS total_credits
            FROM students s
            ORDER BY s.id ASC
        """)
        return [dict(r) for r in cursor.fetchall()]
    finally:
        if should_close:
            conn.close()


def get_admin_enrollments(status=None, course_id=None, conn=None):
    """Fetches enrollments with student and course metadata for admin audit."""
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        query = """
            SELECT 
                e.id AS enrollment_id,
                e.status,
                e.waitlist_position,
                e.enrolled_at,
                e.updated_at,
                s.id AS student_pk,
                s.student_id,
                s.name AS student_name,
                s.email AS student_email,
                s.department AS student_department,
                c.id AS course_id,
                c.code AS course_code,
                c.title AS course_title,
                c.credits,
                c.room,
                c.schedule
            FROM enrollments e
            JOIN students s ON e.student_id = s.id
            JOIN courses c ON e.course_id = c.id
            WHERE 1=1
        """
        params = []
        if status and status != 'All':
            query += " AND e.status = ?"
            params.append(status)
        if course_id:
            query += " AND e.course_id = ?"
            params.append(course_id)

        query += " ORDER BY e.id DESC"
        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]
    finally:
        if should_close:
            conn.close()


def create_course(data, conn=None):
    """Creates a new course record."""
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        code = data.get("code", "").strip().upper()
        title = data.get("title", "").strip()
        department = data.get("department", "Computer Science").strip()
        instructor = data.get("instructor", "").strip()
        credits = int(data.get("credits", 3))
        schedule = data.get("schedule", "MWF 10:00 - 11:15").strip()
        days = data.get("days", "MWF").strip()
        time_slot = data.get("time_slot", "10:00 - 11:15").strip()
        room = data.get("room", "TBD").strip()
        capacity = int(data.get("capacity", 30))
        waitlist_capacity = int(data.get("waitlist_capacity", 10))
        is_closed = 1 if data.get("is_closed") else 0
        description = data.get("description", title).strip()
        prerequisites = data.get("prerequisites", "None").strip()
        term = data.get("term", "Fall 2026").strip()

        cursor.execute("""
            INSERT INTO courses (
                code, title, department, instructor, credits, schedule, days, time_slot,
                room, capacity, waitlist_capacity, is_closed, description, prerequisites, term
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            code, title, department, instructor, credits, schedule, days, time_slot,
            room, capacity, waitlist_capacity, is_closed, description, prerequisites, term
        ))
        new_id = cursor.lastrowid
        conn.commit()
        return get_course_with_enrollment_counts(new_id, conn)
    finally:
        if should_close:
            conn.close()


def update_course(course_id, data, conn=None):
    """Updates existing course details."""
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM courses WHERE id = ?", (course_id,))
        if not cursor.fetchone():
            return None

        code = data.get("code", "").strip().upper()
        title = data.get("title", "").strip()
        department = data.get("department", "").strip()
        instructor = data.get("instructor", "").strip()
        credits = int(data.get("credits", 3))
        schedule = data.get("schedule", "").strip()
        days = data.get("days", "").strip()
        time_slot = data.get("time_slot", "").strip()
        room = data.get("room", "").strip()
        capacity = int(data.get("capacity", 30))
        waitlist_capacity = int(data.get("waitlist_capacity", 10))
        is_closed = 1 if data.get("is_closed") else 0
        description = data.get("description", "").strip()
        prerequisites = data.get("prerequisites", "None").strip()

        cursor.execute("""
            UPDATE courses SET
                code = COALESCE(NULLIF(?, ''), code),
                title = COALESCE(NULLIF(?, ''), title),
                department = COALESCE(NULLIF(?, ''), department),
                instructor = COALESCE(NULLIF(?, ''), instructor),
                credits = ?,
                schedule = COALESCE(NULLIF(?, ''), schedule),
                days = COALESCE(NULLIF(?, ''), days),
                time_slot = COALESCE(NULLIF(?, ''), time_slot),
                room = COALESCE(NULLIF(?, ''), room),
                capacity = ?,
                waitlist_capacity = ?,
                is_closed = ?,
                description = COALESCE(NULLIF(?, ''), description),
                prerequisites = COALESCE(NULLIF(?, ''), prerequisites)
            WHERE id = ?
        """, (
            code, title, department, instructor, credits, schedule, days, time_slot,
            room, capacity, waitlist_capacity, is_closed, description, prerequisites, course_id
        ))
        conn.commit()
        return get_course_with_enrollment_counts(course_id, conn)
    finally:
        if should_close:
            conn.close()


def toggle_course_status(course_id, conn=None):
    """Toggles open/closed registration status for a course."""
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, is_closed FROM courses WHERE id = ?", (course_id,))
        row = cursor.fetchone()
        if not row:
            return None

        new_status = 0 if row["is_closed"] == 1 else 1
        cursor.execute("UPDATE courses SET is_closed = ? WHERE id = ?", (new_status, course_id))
        conn.commit()
        return get_course_with_enrollment_counts(course_id, conn)
    finally:
        if should_close:
            conn.close()


def delete_course(course_id, conn=None):
    """Deletes a course and cascades to its enrollments."""
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, code, title FROM courses WHERE id = ?", (course_id,))
        row = cursor.fetchone()
        if not row:
            return False, "Course not found."

        cursor.execute("DELETE FROM courses WHERE id = ?", (course_id,))
        conn.commit()
        return True, f"Course {row['code']} - {row['title']} deleted successfully."
    finally:
        if should_close:
            conn.close()


def admin_drop_enrollment(enrollment_id, conn=None):
    """Administratively drops an enrollment and handles waitlist auto-promotion."""
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, course_id FROM enrollments WHERE id = ?", (enrollment_id,))
        row = cursor.fetchone()
        if not row:
            return False, "Enrollment record not found.", {}

        student_id = row["student_id"]
        course_id = row["course_id"]
        return withdraw_student_from_course(student_id, course_id, conn)
    finally:
        if should_close:
            conn.close()
