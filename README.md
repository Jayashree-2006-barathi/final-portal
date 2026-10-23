# Greenfield University — Student Course Registration Portal

A polished, full-stack course registration portal built for Greenfield University. Students can register for an account, sign in, browse and search the course catalogue with live seat counts, enrol in open classes, join waitlists when courses are full, withdraw from courses, and manage their academic schedule through an interactive dashboard and weekly timetable.

---

## 🌟 Features

### 1. Student Authentication & Profile Management
- **Registration**: Student registration with full name, validated email address, academic department selection, and password confirmation with instant validation feedback.
- **Unique Student ID**: Automatic generation of institutional student IDs (e.g. `STU-2026-101`).
- **Secure Password Hashing**: Passwords stored using Werkzeug's secure hash algorithms (PBKDF2/scrypt).
- **Authentication**: Flexible sign in using either email or Student ID.
- **Session Management**: Server-side signed HTTP-only cookies (`SameSite=Lax`).
- **Password Reset Flow**: Request reset token with expiration tracking, token verification, and new password confirmation.
- **Route & API Protection**: Enforced on the server; unauthorized requests are rejected with `401 Unauthorized`.

### 2. Live Course Catalogue & Discovery
- **Rich Course Information**: Course code, title, department, instructor, credits, schedule, room, term, course description, and prerequisites.
- **Real-Time Seat Tracking**: Live calculation of enrolled counts, seats remaining, and waitlist availability (`seats_remaining = capacity - enrolled_count`).
- **Multi-parameter Filtering**:
  - Live search input matching title, code, instructor, or keywords (debounced).
  - Department filter (Computer Science, Mathematics, Mechanical Engineering, Biology, Business Administration, Psychology, Humanities).
  - Availability filter (Open Seats, Waitlist Available, Full/Closed).
  - Schedule filter (MWF, TTh, Friday).
  - Credits filter (2, 3, or 4 credits).
- **Clear Status Badges**:
  - 🟢 **Open**: Shows remaining seat count (e.g., `12 seats remaining`).
  - 🟣 **Waitlist Open**: Indicates full course with available waitlist spots.
  - 🔴 **Full**: Indicates completely full course with no waitlist space.
  - ⚫ **Closed**: Explicitly labeled as registration closed.
  - 🟢 **✓ Enrolled**: Highlights courses in which the student is currently enrolled.
  - 🟣 **⏳ Waitlist**: Shows the student's active waitlist position (e.g., `Waitlist #1`).
- **Course Detail Modal**: Full modal view featuring prerequisite details, instructor info, and real-time visual capacity meter.

### 3. Atomic Enrolment & Waitlist System
- **Transactional Consistency**: SQLite `BEGIN IMMEDIATE` transactions prevent race conditions and over-enrolment during concurrent registration attempts.
- **Duplicate Prevention**: Immediate rejection if student is already enrolled or waitlisted in the course.
- **Full Course & Waitlist Placement**: When an open course fills up, students are smoothly placed on the waitlist with their FIFO position.
- **Withdrawal & Auto-Promotion**:
  - Students can safely withdraw with a confirmation modal explaining seat release.
  - If an enrolled student withdraws and there are waitlisted students, the top waitlisted student is **automatically promoted to Enrolled** (FIFO order), and subsequent waitlist positions are re-indexed.

### 4. Student Dashboard & Class Timetable
- **Overview Metrics**: Active enrolled course count, enrolled credit load vs max term limit (18 credits) with progress bar, waitlisted course count, and withdrawal count.
- **Course Management Table**: Direct access to view details or withdraw from enrolled/waitlisted subjects.
- **Weekly Schedule Grid**: Interactive 5-day timetable (Monday through Friday) mapping enrolled lecture blocks to their corresponding time slots and lecture rooms.

### 5. Administrator Dashboard & Academic Management
- **High-Level KPI Overview**: Total registered students, course offerings, live seat capacity & utilization percentage bar, waitlist demand, and departmental distribution.
- **Course Catalog Management**: Live search, department and status filters, add new course modal, edit course parameters, toggle open/closed registration status, and permanent deletion with cascade cleanup.
- **Student Directory & Enrolment Inspection**: Complete student directory with enrolled courses count and credit tallies; click "View Enrolments" to inspect any student's registered subjects and administratively drop them.
- **Live Registrations & Waitlist Audit**: Real-time log of all enrollments across all subjects with FIFO waitlist position rankings, timestamps, and administrative drop capability with automatic waitlist promotion.
- **Department Utilization Analytics**: Visual breakdown of seat occupancy across all university faculties.

### 6. Design & Accessibility
- Responsive across mobile, tablet, and desktop screens with mobile drawer navigation.
- Accessible focus states, semantic HTML, ARIA attributes (`role="dialog"`, `aria-modal="true"`, `aria-live="polite"`), and full keyboard navigation support (`Esc` to dismiss modals/drawers).
- Animated, auto-dismissing toast notifications for immediate user feedback.

---

## 🛠️ Tech Stack & Architecture

- **Backend**: Python 3, Flask 3, Werkzeug Security, python-dotenv
- **Database**: SQLite with foreign keys, transactional locking, and indexing
- **Frontend**: Responsive Single-Page Application (HTML5, CSS3 Custom Properties, Vanilla JavaScript ES6+)
- **Testing**: Pytest integration suite with isolated temporary test databases

---

## 📁 Project Structure

```
ERP/
├── app.py              # Flask server, route controllers, session auth, API endpoints
├── database.py         # SQLite connection, schema definition, seed data, transactional operations
├── index.html          # Responsive single-page application & university portal UI
├── pytest.ini          # Pytest configuration
├── requirements.txt    # Project dependencies
├── .env                # Local development configuration
├── .env.example        # Environment variable template
├── tests/
│   ├── test_api.py     # 13 student and catalog integration tests
│   └── test_admin.py   # Admin authentication, CRUD, and audit tests
└── README.md           # Documentation
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+ (tested with Python 3.12 / 3.14)

### 2. Setup Virtual Environment & Install Dependencies

```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Create or inspect the `.env` file (a default `.env` is pre-configured):
```env
SECRET_KEY=greenfield-secure-session-key-dev-replace-in-prod
DATABASE_PATH=greenfield_erp.db
PORT=5000
FLASK_ENV=development
```

### 4. Run the Application

```powershell
python app.py
```

Open your browser and navigate to:
```
http://localhost:5000
```

---

## 🔑 Demo Accounts

The database comes pre-seeded with sample courses across multiple departments, a demo student account, and a registrar administrator account:

### 🎓 Demo Student Account
- **Email**: `alex.morgan@greenfield.edu`
- **Password**: `demo123`
- **Student ID**: `STU-2026-001`
- **Pre-enrolled in**: `CS301` (Data Structures & Algorithms) and `MA301` (Linear Algebra)

### 🛡️ Demo Administrator Account
- **Email**: `admin@greenfield.edu` (or username `admin`)
- **Password**: `admin123`
- **Role**: `Administrator`
- **Privileges**: Access to `🛡️ Admin Portal` for course creation/editing, closing/reopening registration, reviewing student records, and managing waitlists.

Use the **"Fill Student"** or **"Fill Admin"** buttons on the Sign In page for instant one-click demo access.

---

## 🧪 Running Automated Tests

Run the full Pytest test suite:

```powershell
.\.venv\Scripts\pytest.exe -v
```

All 13 tests verify:
- Input validation on student registration (empty fields, invalid email, password length, password mismatch)
- Duplicate email rejection (409 Conflict)
- Sign-in with either Email or Student ID
- Session preservation and logout
- Password reset token generation and password updating
- Course catalogue querying, search, and multi-filter combinations
- Enrolment in open course and seat count decrements
- Duplicate enrolment rejection
- Closed course enrolment rejection
- Waitlist placement on full course (`CS490`)
- Maximum waitlist capacity rejection
- Automatic promotion of top waitlisted student upon withdrawal
- Server-side 401 protection on unauthorized endpoints
- Root and deep-linking HTML application serving
