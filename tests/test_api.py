"""
tests/test_api.py - Comprehensive Unit & Integration Tests for Course Registration Portal
"""

import os
import tempfile
import pytest
import database
from app import app


@pytest.fixture
def client():
    # Create a temporary database for test isolation
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key-12345"
    os.environ["DATABASE_PATH"] = db_path

    # Initialize schema & seeds
    database.init_db(db_path)

    with app.test_client() as client:
        yield client

    # Cleanup
    os.close(db_fd)
    if os.path.exists(db_path):
        os.remove(db_path)


def test_student_registration_validation(client):
    """Test validation errors during student registration."""
    # Missing name
    res = client.post("/api/auth/register", json={
        "name": "",
        "email": "student@greenfield.edu",
        "password": "password123",
        "confirm_password": "password123"
    })
    assert res.status_code == 400
    assert "Full name is required" in res.get_json()["error"]

    # Invalid email
    res = client.post("/api/auth/register", json={
        "name": "Jane Doe",
        "email": "not-an-email",
        "password": "password123",
        "confirm_password": "password123"
    })
    assert res.status_code == 400
    assert "valid email address" in res.get_json()["error"]

    # Passwords mismatch
    res = client.post("/api/auth/register", json={
        "name": "Jane Doe",
        "email": "jane.doe@greenfield.edu",
        "password": "password123",
        "confirm_password": "differentpassword"
    })
    assert res.status_code == 400
    assert "do not match" in res.get_json()["error"]

    # Password too short
    res = client.post("/api/auth/register", json={
        "name": "Jane Doe",
        "email": "jane.doe@greenfield.edu",
        "password": "123",
        "confirm_password": "123"
    })
    assert res.status_code == 400
    assert "at least 6 characters" in res.get_json()["error"]


def test_student_registration_and_login_flow(client):
    """Test full registration, login, session check, and logout."""
    # Register new student
    res = client.post("/api/auth/register", json={
        "name": "Maria Sanders",
        "email": "maria.s@greenfield.edu",
        "password": "securepassword123",
        "confirm_password": "securepassword123",
        "department": "Computer Science",
        "program": "B.Tech Computer Science"
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert data["student"]["email"] == "maria.s@greenfield.edu"
    assert data["student"]["student_id"].startswith("STU-2026-")

    # Session is active
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    assert me_res.get_json()["student"]["name"] == "Maria Sanders"

    # Logout
    logout_res = client.post("/api/auth/logout")
    assert logout_res.status_code == 200

    # Now /api/auth/me should be 401
    me_res2 = client.get("/api/auth/me")
    assert me_res2.status_code == 401

    # Login with newly created credentials
    login_res = client.post("/api/auth/login", json={
        "email": "maria.s@greenfield.edu",
        "password": "securepassword123"
    })
    assert login_res.status_code == 200
    assert login_res.get_json()["student"]["email"] == "maria.s@greenfield.edu"

    # Login with student ID
    client.post("/api/auth/logout")
    stu_id = data["student"]["student_id"]
    login_id_res = client.post("/api/auth/login", json={
        "email": stu_id,
        "password": "securepassword123"
    })
    assert login_id_res.status_code == 200


def test_duplicate_email_registration_rejected(client):
    """Ensure duplicate email registration is rejected with 409 conflict."""
    res = client.post("/api/auth/register", json={
        "name": "Duplicate Alex",
        "email": "alex.morgan@greenfield.edu", # already seeded
        "password": "mypassword123",
        "confirm_password": "mypassword123"
    })
    assert res.status_code == 409
    assert "already exists" in res.get_json()["error"]


def test_password_reset_flow(client):
    """Test generating a reset token and resetting student password."""
    # Request reset token
    res = client.post("/api/auth/forgot-password", json={
        "email": "alex.morgan@greenfield.edu"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    token = data["reset_token"]
    assert token is not None

    # Reset password with token
    reset_res = client.post("/api/auth/reset-password", json={
        "token": token,
        "new_password": "brandnewpassword456",
        "confirm_password": "brandnewpassword456"
    })
    assert reset_res.status_code == 200
    assert "successfully reset" in reset_res.get_json()["message"]

    # Try signing in with old password (should fail)
    bad_login = client.post("/api/auth/login", json={
        "email": "alex.morgan@greenfield.edu",
        "password": "demo123"
    })
    assert bad_login.status_code == 401

    # Sign in with new password (should succeed)
    good_login = client.post("/api/auth/login", json={
        "email": "alex.morgan@greenfield.edu",
        "password": "brandnewpassword456"
    })
    assert good_login.status_code == 200


def test_course_catalogue_search_and_filters(client):
    """Test querying courses with search terms and filters."""
    # List all courses
    res = client.get("/api/courses")
    assert res.status_code == 200
    data = res.get_json()
    assert data["count"] >= 10

    # Search by code
    res_search = client.get("/api/courses?search=CS405")
    courses = res_search.get_json()["courses"]
    assert len(courses) == 1
    assert courses[0]["code"] == "CS405"

    # Filter by department
    res_dept = client.get("/api/courses?department=Mathematics")
    math_courses = res_dept.get_json()["courses"]
    assert all(c["department"] == "Mathematics" for c in math_courses)
    assert len(math_courses) >= 2

    # Filter by schedule day
    res_sched = client.get("/api/courses?schedule=TTh")
    tth_courses = res_sched.get_json()["courses"]
    assert all("TTh" in c["days"] for c in tth_courses)


def test_enrolment_in_available_course(client):
    """Test enrolling in an available course and checking seat consistency."""
    # Sign in as Alex Morgan
    client.post("/api/auth/login", json={
        "email": "alex.morgan@greenfield.edu",
        "password": "demo123"
    })

    # CS405 has capacity 28 and 0 enrolled initially
    detail_before = client.get("/api/courses/2").get_json()["course"]
    seats_before = detail_before["seats_remaining"]

    # Enrol in CS405
    enrol_res = client.post("/api/enrollments", json={"course_id": 2})
    assert enrol_res.status_code == 200
    assert enrol_res.get_json()["status"] == "Enrolled"

    # Verify seats remaining decreased by 1
    detail_after = client.get("/api/courses/2").get_json()["course"]
    assert detail_after["seats_remaining"] == seats_before - 1
    assert detail_after["my_status"] == "Enrolled"

    # Verify on student dashboard
    dash_res = client.get("/api/student/dashboard")
    dash = dash_res.get_json()
    enrolled_codes = [e["code"] for e in dash["enrollments"] if e["enrollment_status"] == "Enrolled"]
    assert "CS405" in enrolled_codes


def test_reject_duplicate_enrolment(client):
    """Prevent enrolling twice in the same course."""
    client.post("/api/auth/login", json={
        "email": "alex.morgan@greenfield.edu",
        "password": "demo123"
    })

    # Alex is already enrolled in CS301 (seeded)
    res = client.post("/api/enrollments", json={"course_id": 1})
    assert res.status_code == 400
    assert "already enrolled" in res.get_json()["error"].lower()


def test_reject_enrolment_in_closed_course(client):
    """Closed courses must reject enrolment."""
    client.post("/api/auth/login", json={
        "email": "alex.morgan@greenfield.edu",
        "password": "demo123"
    })

    # CS599 is marked is_closed = 1 (id 13)
    res = client.post("/api/enrollments", json={"course_id": 13})
    assert res.status_code == 400
    assert "closed" in res.get_json()["error"].lower()


def test_waitlist_and_auto_promotion_on_withdrawal(client):
    """
    Test full course placement onto waitlist,
    and automatic promotion of top waitlisted student when an enrolled student withdraws.
    """
    # Course 12 (CS490) has capacity 2, seeded with Jordan (id 2) and Samira (id 3)
    # Login as Alex Morgan (id 1)
    client.post("/api/auth/login", json={
        "email": "alex.morgan@greenfield.edu",
        "password": "demo123"
    })

    # Attempt to enroll in full course CS490 (id 12)
    res = client.post("/api/enrollments", json={"course_id": 12})
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "Waitlisted"
    assert data["details"]["waitlist_position"] == 1

    # Verify Alex's status on dashboard is Waitlisted
    dash = client.get("/api/student/dashboard").get_json()
    alex_cs490 = next(e for e in dash["enrollments"] if e["code"] == "CS490")
    assert alex_cs490["enrollment_status"] == "Waitlisted"
    assert alex_cs490["waitlist_position"] == 1

    # Now log in as Jordan (id 2) who is currently Enrolled in CS490
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={
        "email": "jordan.l@greenfield.edu",
        "password": "demo123"
    })

    # Jordan withdraws from CS490
    withdraw_res = client.post("/api/enrollments/12/withdraw")
    assert withdraw_res.status_code == 200
    assert withdraw_res.get_json()["success"] is True

    # Now verify that Alex (id 1) has been automatically promoted to 'Enrolled'!
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={
        "email": "alex.morgan@greenfield.edu",
        "password": "demo123"
    })
    alex_dash = client.get("/api/student/dashboard").get_json()
    promoted_cs490 = next(e for e in alex_dash["enrollments"] if e["code"] == "CS490")
    assert promoted_cs490["enrollment_status"] == "Enrolled"
    assert promoted_cs490["waitlist_position"] is None


def test_unauthorized_access(client):
    """Unauthenticated users cannot access protected endpoints."""
    res = client.post("/api/enrollments", json={"course_id": 1})
    assert res.status_code == 401

    res = client.get("/api/student/dashboard")
    assert res.status_code == 401


def test_index_route_and_deep_links(client):
    """Ensure root and deep link routes serve the frontend HTML application."""
    res = client.get("/")
    assert res.status_code == 200
    assert b"Greenfield University" in res.data
    assert b"Course Registration Portal" in res.data

    res_deep = client.get("/catalogue")
    assert res_deep.status_code == 200
    assert b"Greenfield University" in res_deep.data


def test_course_detail_endpoint(client):
    """Test fetching course detail by ID with real-time capacity and auth decorator."""
    # When unauthenticated
    res = client.get("/api/courses/1")
    assert res.status_code == 200
    data = res.get_json()["course"]
    assert data["code"] == "CS301"
    assert data["my_status"] is None

    # When authenticated as Alex Morgan (who is enrolled in CS301)
    client.post("/api/auth/login", json={
        "email": "alex.morgan@greenfield.edu",
        "password": "demo123"
    })
    res_auth = client.get("/api/courses/1")
    assert res_auth.status_code == 200
    data_auth = res_auth.get_json()["course"]
    assert data_auth["my_status"] == "Enrolled"


def test_waitlist_max_capacity_rejection(client):
    """When both course capacity and waitlist capacity are exhausted, registration is completely rejected."""
    # Course 12 (CS490) has capacity 2, waitlist_capacity 3
    # Seeded with Jordan (id 2) and Samira (id 3) in Enrolled
    # Alex (id 1) registers and joins waitlist (pos 1)
    client.post("/api/auth/login", json={
        "email": "alex.morgan@greenfield.edu",
        "password": "demo123"
    })
    r1 = client.post("/api/enrollments", json={"course_id": 12})
    assert r1.status_code == 200
    assert r1.get_json()["status"] == "Waitlisted"
    client.post("/api/auth/logout")

    # Marcus (id 4) joins waitlist (pos 2)
    client.post("/api/auth/login", json={
        "email": "marcus.j@greenfield.edu",
        "password": "demo123"
    })
    r2 = client.post("/api/enrollments", json={"course_id": 12})
    assert r2.status_code == 200
    assert r2.get_json()["status"] == "Waitlisted"
    client.post("/api/auth/logout")

    # Emily (id 5) joins waitlist (pos 3 - full waitlist!)
    client.post("/api/auth/login", json={
        "email": "emily.c@greenfield.edu",
        "password": "demo123"
    })
    r3 = client.post("/api/enrollments", json={"course_id": 12})
    assert r3.status_code == 200
    assert r3.get_json()["status"] == "Waitlisted"
    client.post("/api/auth/logout")

    # Now register a brand new 6th student
    client.post("/api/auth/register", json={
        "name": "Sixth Student",
        "email": "sixth@greenfield.edu",
        "password": "password123",
        "confirm_password": "password123"
    })
    # 6th student tries to enroll in CS490 (course full + waitlist full!)
    r4 = client.post("/api/enrollments", json={"course_id": 12})
    assert r4.status_code == 400
    assert "full" in r4.get_json()["error"].lower()

