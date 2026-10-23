"""
tests/test_admin.py - Unit & Integration Tests for Administrator Dashboard & Capabilities
"""

import os
import tempfile
import pytest
import database
from app import app


@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key-admin-test"
    os.environ["DATABASE_PATH"] = db_path

    database.init_db(db_path)

    with app.test_client() as client:
        yield client

    os.close(db_fd)
    if os.path.exists(db_path):
        os.remove(db_path)


def test_admin_login_and_unauthorized_protection(client):
    """Test admin authentication and route protection."""
    # Student login cannot access admin endpoint
    client.post("/api/auth/login", json={
        "email": "alex.morgan@greenfield.edu",
        "password": "demo123"
    })
    res_forbidden = client.get("/api/admin/stats")
    assert res_forbidden.status_code == 403

    # Sign out student
    client.post("/api/auth/logout")

    # Login as Admin using default admin account
    res_admin = client.post("/api/admin/login", json={
        "email": "admin@greenfield.edu",
        "password": "admin123"
    })
    assert res_admin.status_code == 200
    data = res_admin.get_json()
    assert data["role"] == "admin"
    assert data["admin"]["username"] == "admin"

    # Now admin stats is accessible
    stats_res = client.get("/api/admin/stats")
    assert stats_res.status_code == 200
    stats = stats_res.get_json()
    assert "student_count" in stats
    assert "course_count" in stats
    assert "enrolled_count" in stats
    assert "utilization" in stats


def test_admin_course_crud_and_status_toggle(client):
    """Test creating, updating, toggling status, and deleting courses as admin."""
    # Login as admin
    client.post("/api/admin/login", json={
        "email": "admin@greenfield.edu",
        "password": "admin123"
    })

    # Create new course
    create_res = client.post("/api/admin/courses", json={
        "code": "CS399",
        "title": "Cloud Native Architecture",
        "department": "Computer Science",
        "instructor": "Dr. Sarah Connor",
        "credits": 4,
        "schedule": "TTh 14:00 - 15:30",
        "days": "TTh",
        "time_slot": "14:00 - 15:30",
        "room": "Tech Lab 304",
        "capacity": 25,
        "waitlist_capacity": 5,
        "description": "Design and build microservices with Kubernetes, Docker, and distributed storage.",
        "prerequisites": "CS301",
        "term": "Fall 2026"
    })
    assert create_res.status_code == 201
    course_data = create_res.get_json()["course"]
    course_id = course_data["id"]
    assert course_data["code"] == "CS399"
    assert course_data["is_closed"] == 0

    # Toggle status to closed
    toggle_res = client.post(f"/api/admin/courses/{course_id}/toggle-status")
    assert toggle_res.status_code == 200
    assert toggle_res.get_json()["course"]["is_closed"] == 1

    # Toggle status back to open
    toggle_res2 = client.post(f"/api/admin/courses/{course_id}/toggle-status")
    assert toggle_res2.status_code == 200
    assert toggle_res2.get_json()["course"]["is_closed"] == 0

    # Update course
    update_res = client.put(f"/api/admin/courses/{course_id}", json={
        "code": "CS399",
        "title": "Advanced Cloud Native Architecture",
        "capacity": 30
    })
    assert update_res.status_code == 200
    assert update_res.get_json()["course"]["title"] == "Advanced Cloud Native Architecture"
    assert update_res.get_json()["course"]["capacity"] == 30

    # Delete course
    del_res = client.delete(f"/api/admin/courses/{course_id}")
    assert del_res.status_code == 200
    assert del_res.get_json()["success"] is True


def test_admin_students_and_enrollments_management(client):
    """Test admin student directory listing, audit list, and administrative drop."""
    client.post("/api/admin/login", json={
        "email": "admin@greenfield.edu",
        "password": "admin123"
    })

    # List all students
    students_res = client.get("/api/admin/students")
    assert students_res.status_code == 200
    students = students_res.get_json()["students"]
    assert len(students) >= 5

    # Check student enrollments
    alex_student_id = students[0]["id"]
    alex_enrols_res = client.get(f"/api/admin/students/{alex_student_id}/enrollments")
    assert alex_enrols_res.status_code == 200
    assert "enrollments" in alex_enrols_res.get_json()

    # List audit enrollments
    audit_res = client.get("/api/admin/enrollments?status=Enrolled")
    assert audit_res.status_code == 200
    enrols = audit_res.get_json()["enrollments"]
    assert len(enrols) > 0

    # Test administrative drop
    first_enrollment_id = enrols[0]["enrollment_id"]
    drop_res = client.post(f"/api/admin/enrollments/{first_enrollment_id}/drop")
    assert drop_res.status_code == 200
    assert drop_res.get_json()["success"] is True
