# CampusQuery 🎓
> **Smart College Notice Board, Academic Deadline Tracker, Procedural Flowchart Builder & Grounded Gemini AI Assistant**  
> Tailored for **TYBCA** with Python Flask 3, Bootstrap 5, Vanilla JavaScript, and MySQL 8 (with transparent SQLite development fallback).

[![Status](https://img.shields.io/badge/Status-Release%20Ready%20(Phase%2012)-success.svg)](file:///c:/Users/mrksp/CampusQueri)
[![Tests](https://img.shields.io/badge/Tests-168%20Passed%20%7C%200%20Failed-brightgreen.svg)](file:///c:/Users/mrksp/CampusQueri/tests)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![Database](https://img.shields.io/badge/Database-MySQL%208%20%2F%20SQLite%20Fallback-orange.svg)](https://mysql.com)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](file:///c:/Users/mrksp/CampusQueri/LICENSE)

---

## 📌 Executive Summary

**CampusQuery** is an integrated academic communications, procedural guidance, and administrative workflow system built for college campuses. It bridges the gap between chaotic multi-channel college announcements (WhatsApp groups, fragmented bulletin boards, unindexed PDFs) and modern, accessible, grounded web applications.

### Core Capabilities
1. **Academic Notice & Circular Management**: Complete administrative publication lifecycle (**Draft** → **Published** → **Archived**), categorized taxonomy, milestone-based deadlines, and parameterized full-text search.
2. **Dynamic Deadline Engine & Notifications**: Automated calculation of milestone statuses (*Upcoming*, *Due Today*, *Overdue*, *Closed*), in-portal student notifications on publication and milestone revisions, and office contact attribution.
3. **Secure Document Management**: High-integrity PDF/DOCX upload pipeline outside static web roots, magic byte header verification, multi-strategy text extraction (`pypdf` and `python-docx`), transparent OCR-needed diagnostics, and strict publication-gated downloads.
4. **Interactive Flowchart Builder**: Visual process builder powered by vendored **Drawflow**, automated step-to-graph synthesis with branching Yes/No decision logic, and server-side vector PDF (`ReportLab`) and raster PNG (`Pillow`) exporters.
5. **Grounded Gemini AI Academic Assistant**: Server-side Google GenAI (Gemini) assistant answering student inquiries strictly using verified published circulars and extracted document content. Features indirect prompt-injection defenses, server-side citation allowlists, and an automatic offline directory fallback mode.
6. **Accessible & Responsive Frontend**: WCAG AA compliant color contrast, explicit form labels, skip-to-content accessibility navigation, high-visibility focus indicators, and fully responsive layouts across mobile, tablet, and desktop viewports.

---

## 🛠️ Technology Stack

| Layer | Technologies | Rationale & Specifications |
| :--- | :--- | :--- |
| **Backend Framework** | **Python 3.12**, **Flask 3.0.3** | Modular Blueprint architecture, application factory pattern (`create_app`), production-grade WSGI compatibility. |
| **Database & ORM** | **MySQL 8.x**, **SQLAlchemy 2.x**, **PyMySQL** | Relational schema with foreign keys, indexes, cascades, transactions, and automatic fallback to thread-safe SQLite for local standalone development. |
| **Frontend UI** | **Bootstrap 5.3.3**, **Bootstrap Icons 1.11** | Clean academic theme, responsive grid, zero heavy client framework dependencies. |
| **Interactive Graphs**| **Drawflow 0.0.59** (Vendored) | Lightweight (MIT), vanilla JavaScript DOM canvas, no external CDNs required for runtime. |
| **Document Processing**| **pypdf 4.2.0**, **python-docx 1.1.0** | Server-side text extraction and PDF/DOCX stream validation. |
| **Diagram Exporters** | **ReportLab 4.1.0**, **Pillow 10.3.0** | Server-side generation of institutional vector PDFs and high-res raster PNGs. |
| **AI Retrieval & Chat**| **Google GenAI SDK** (Gemini 1.5/2.0 API) | Server-side inference with strict prompt boundaries, retrieval-augmented grounding, and offline fallback. |
| **Security & Forms** | **Flask-WTF 1.2.1**, **WTForms 3.1.2** | CSRF protection, secure cookie sessions (`HttpOnly`, `SameSite='Lax'`), `scrypt` password hashing. |
| **Testing & QA** | **pytest 8.1.1**, **Requests 2.31.0** | 12 automated test modules covering unit, integration, RBAC, accessibility, and live HTTP socket verifications. |

---

## 📂 Project Directory Architecture

```text
CampusQuery/
├── .venv/                              # Python 3.12 Virtual Environment
├── .env                                # Local environment configuration (DB credentials, secret keys)
├── .env.example                        # Documented environment variable template
├── .gitignore                          # Git tracking exclusions (.env, .db, upload binaries, pycache)
├── requirements.txt                    # Pinned Python package dependencies
├── schema.sql                          # MySQL 8 DDL schema script (MySQL Workbench compatible)
├── run.py                              # Flask development server entry point
├── config.py                           # Legacy config wrapper pointing to app/config.py
├── README.md                           # Comprehensive documentation and release handbook
├── ENGINEERING_RULES.md                # Permanent architecture, security, and verification rules
├── app/
│   ├── __init__.py                     # Flask application factory (create_app)
│   ├── config.py                       # Config classes (Development, Testing, Production)
│   ├── database.py                     # SQLAlchemy instance & MySQL/SQLite connection helpers
│   ├── models/                         # Relational data models (10 tables)
│   │   ├── __init__.py                 # Clean package exports
│   │   ├── user.py                     # User authentication & role-based access control
│   │   ├── category.py                 # Academic categories & deletion protection
│   │   ├── notice.py                   # Notices, publication lifecycle, and search indexes
│   │   ├── deadline.py                 # Multi-milestone deadline calculations & status derivation
│   │   ├── document.py                 # File metadata, extraction logs, and security checks
│   │   ├── flowchart.py                # Graph JSON storage, node schemas, and step generators
│   │   ├── office.py                   # Administrative office directories & location details
│   │   └── notification.py             # In-portal student notification triggers
│   ├── auth/                           # Authentication blueprint package (/auth)
│   ├── student/                        # Student & public portal blueprint package (/)
│   ├── admin/                          # Administrative control panel blueprint package (/admin)
│   ├── documents/                      # Document upload/download management blueprint (/documents)
│   ├── flowcharts/                     # Flowchart builder & export blueprint (/flowcharts)
│   ├── assistant/                      # Grounded Gemini AI assistant blueprint (/assistant)
│   ├── services/                       # Business logic services
│   │   ├── retrieval_service.py        # Notice & document search, ranking, and context filtering
│   │   ├── gemini_service.py           # Gemini API client, injection defenses, and offline fallback
│   │   └── flowchart_exporter.py       # Pillow & ReportLab server-side diagram renderers
│   ├── static/                         # Static assets (served by web server)
│   │   ├── css/
│   │   │   ├── style.css               # Core custom CSS, focus rings, and WCAG overrides
│   │   │   └── drawflow.min.css        # Vendored Drawflow styling
│   │   ├── js/
│   │   │   ├── main.js                 # Vanilla JS: alerts, form submission states, health ping
│   │   │   └── drawflow.min.js         # Vendored Drawflow editor library
│   │   └── img/                        # Verified application screenshots and branding
│   └── templates/                      # Jinja2 HTML templates
│       ├── base.html                   # Master layout with accessible navigation and footer
│       ├── auth/                       # Login and registration templates
│       ├── student/                    # Portal dashboard, notice search, details, offices, inbox
│       ├── admin/                      # Dashboard metrics, notice CRUD, category manager
│       ├── documents/                  # Document management & upload modal templates
│       ├── flowcharts/                 # Graph editor, step generator, and public diagram viewer
│       ├── assistant/                  # AI conversational interface with citation cards
│       └── errors/                     # Standardized 400, 403, 404, 413, 500 error pages
├── uploads/                            # Isolated directory outside web server roots
│   ├── documents/                      # Uploaded PDF and DOCX binaries (doc_<uuid>.<ext>)
│   └── flowcharts/                     # Exported image and PDF diagrams
├── scripts/                            # Operational, database, and verification utilities
│   ├── init_db.py                      # Database creation and table initialization utility
│   ├── create_admin.py                 # Secure administrator account creation script
│   ├── seed_demo.py                    # Idempotent demo data seeder (users, notices, offices)
│   ├── verify_phase12_live.py          # Phase 12 live HTTP socket verification suite
│   ├── capture_screenshots.ps1         # Automated headless Chrome screenshot capture tool
│   └── ...                             # Phase-specific verification test scripts
└── tests/                              # Pytest automated test suite (168 tests, 12 modules)
    ├── test_authentication.py          # Auth, login, registration, scrypt hashing, RBAC (14)
    ├── test_database_crud.py           # Relational schema integrity, foreign keys, cascades (10)
    ├── test_admin_notices.py           # Admin notices CRUD, validation, lifecycle states (23)
    ├── test_student_portal.py          # Student dashboard, search, filters, pagination (17)
    ├── test_deadlines_and_notifications.py # Deadline calculation, IST times, inbox (17)
    ├── test_document_management.py     # Magic bytes, text extraction, download gating (21)
    ├── test_flowchart_builder.py       # Graph JSON validation, step generator, exports (15)
    ├── test_gemini_assistant.py        # Prompt injection defense, allowlists, offline fallback (15)
    ├── test_phase10_security_and_regression.py # Security hardening, CSRF, XSS defense (18)
    ├── test_phase11_accessibility.py   # WCAG contrast, aria attributes, skip navigation (10)
    ├── test_phase11_mobile_responsive.py # Responsive viewports, mobile touch targets (8)
    └── test_phase12_final_acceptance.py# End-to-end user journeys & release acceptance (9)
```

---

## 🚀 Setup & Execution Guide (Windows Environment)

### Step 1: Prerequisites
Ensure the following tools are installed on your Windows machine:
- **Python 3.12+** (Ensure `python` and `pip` are accessible in PowerShell / Command Prompt).
- **Git** for version control.
- **MySQL Server 8.0+** and **MySQL Workbench** *(optional if running in standalone SQLite dev mode)*.

---

### Step 2: Virtual Environment & Dependencies
Clone the repository and initialize the Python virtual environment:

```powershell
# Navigate into the project directory
cd C:\Users\mrksp\CampusQueri

# Create virtual environment if not already present
python -m venv .venv

# Activate the virtual environment
# In PowerShell:
.\.venv\Scripts\Activate.ps1

# In Command Prompt (cmd.exe):
.\.venv\Scripts\activate.bat

# Install all frozen dependencies
pip install -r requirements.txt
```

---

### Step 3: Database Provisioning (MySQL & Workbench)

#### Option A: Running with Local MySQL Server
1. **Verify MySQL Service**: Open PowerShell and check if MySQL is running:
   ```powershell
   Get-Service -Name "*mysql*"
   ```
   If stopped, start the service as Administrator:
   ```powershell
   Start-Service MySQL80
   ```
2. **Execute Least-Privilege Provisioning Script in MySQL Workbench**:
   Launch MySQL Workbench, open a Query Tab against `localhost:3306` (as `root`), and execute:
   ```sql
   -- Create Database
   CREATE DATABASE IF NOT EXISTS campusqueri_db
     CHARACTER SET utf8mb4
     COLLATE utf8mb4_unicode_ci;

   -- Create Dedicated Application User with Least Privilege
   CREATE USER IF NOT EXISTS 'campus_app'@'localhost' IDENTIFIED BY 'StrongCampusPass@2026!';

   -- Grant Only Required CRUD Permissions (No administrative grant options)
   GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, INDEX, ALTER ON campusqueri_db.* TO 'campus_app'@'localhost';
   FLUSH PRIVILEGES;
   ```
3. **Import Schema**:
   In MySQL Workbench, open `C:\Users\mrksp\CampusQueri\schema.sql` and click **Execute (⚡ Lightning Bolt)**.

#### Option B: Automatic SQLite Development Fallback
If MySQL Server is not installed or the local service is stopped, CampusQuery's resilient database connection engine (`app/database.py`) **automatically falls back to a local SQLite database** (`instance/campusqueri_dev.db`). The application provides identical schema structure, constraints, and features without any manual reconfiguration required.

---

### Step 4: Environment Configuration (`.env`)
Create your `.env` file based on `.env.example`:

```powershell
cp .env.example .env
```

Review and adjust variables in `.env`:
```ini
# Flask Secret Key for sessions and CSRF
SECRET_KEY=change-this-to-a-secure-random-secret-key-32-chars

# Database Configuration (MySQL)
DB_HOST=localhost
DB_PORT=3306
DB_NAME=campusqueri_db
DB_USER=campus_app
DB_PASSWORD=StrongCampusPass@2026!

# Document Upload Limits
MAX_CONTENT_LENGTH=10485760
UPLOAD_FOLDER=uploads/documents

# Google Gemini API Key (Optional: system operates in offline directory mode if omitted)
GEMINI_API_KEY=your_gemini_api_key_here

# Runtime Environment (development, testing, production)
FLASK_ENV=development
```

---

### Step 5: Initialize Tables & Seed Demo Content
Run the non-destructive initialization and demo seeder scripts:

```powershell
# 1. Initialize tables and verify constraints
& .venv\Scripts\python.exe scripts\init_db.py

# 2. Seed realistic demo data (users, categories, offices, notices, deadlines)
& .venv\Scripts\python.exe scripts\seed_demo.py
```

#### Pre-Configured Demo Accounts (Ready to Test):
| Role | Email | Password | Full Name | Permissions |
| :--- | :--- | :--- | :--- | :--- |
| **Administrator** | `admin@campusqueri.edu` | `Admin@123` | Admin Office Coordinator | Full CRUD over notices, categories, documents, and flowcharts. |
| **Student** | `student@campusqueri.edu` | `Student@123` | Aarav Patel | Read-only notices, deadlines, inbox, document downloads, AI chat. |
| **Student (Peer)**| `priya.sharma@campusqueri.edu` | `Student@123` | Priya Sharma | Second student account for multi-user notification testing. |

---

### Step 6: Provision Custom Admin Account (CLI Tool)
To create or update a dedicated administrator account securely with interactive password masking or command-line parameters:

```powershell
# Interactive mode (prompts securely for password):
& .venv\Scripts\python.exe scripts\create_admin.py

# Command-line parameter mode:
& .venv\Scripts\python.exe scripts\create_admin.py --email custom.admin@campusqueri.edu --name "Dean of Academics" --password "SecurePass@2026"
```

---

### Step 7: Launch the Application
Start the Flask development server:

```powershell
& .venv\Scripts\python.exe run.py
```

Access the application in your browser:
- **Student Portal**: `http://127.0.0.1:5000`
- **Admin Control Panel**: `http://127.0.0.1:5000/admin`
- **Health Check Endpoints**:
  - Web: `http://127.0.0.1:5000/health`
  - JSON API: `http://127.0.0.1:5000/api/health`

---

## 🔍 Core Feature Specifications

### 1. Notice Management & Search Engine
- **Lifecycle Pipeline**:
  - `draft`: Editable by admins only; completely hidden from public queries and search.
  - `published`: Immediately indexable, visible to students, searchable, and AI-retrievable.
  - `archived`: Read-only historic record; removed from active student listings and AI context.
- **Search Capabilities**: Parameterized query filtering (`?q=keyword&category=cet&priority=urgent&sort=date_desc`) defeating SQL injection.
- **Pagination**: Scalable server-side pagination with preserved query parameters across page transitions.

### 2. Milestone Deadline Engine & Real-Time Notifications
- **Timezone Strategy**: All server storage operates in UTC (`datetime.utcnow()`); user interfaces display Indian Standard Time (IST, UTC+05:30) with clear AM/PM indicators.
- **Dynamic Derived Statuses**:
  - `UPCOMING`: Closing date is in the future.
  - `DUE_TODAY`: Closing date falls within the current calendar day in IST.
  - `OVERDUE` / `EXPIRED`: Closing date has passed.
- **Notifications**: Automated trigger generates unread student notifications on:
  1. Initial notice publication.
  2. Material revisions to milestone dates or application requirements.

### 3. Secure Document Management
- **Storage Location**: Files reside in `uploads/documents/`, strictly outside web server roots (`app/static/`).
- **Filename Randomization**: Files are saved with cryptographically random UUIDv4 filenames (`doc_<hex32>.<ext>`). Original filenames are sanitized and used solely for the `Content-Disposition` download header.
- **Magic Byte Verification**: Rejects MIME-spoofing via binary header analysis (`%PDF-` for PDFs, `PK\x03\x04` for DOCX).
- **Text Extraction**: Uses `pypdf` for PDF page streams and `python-docx` for XML paragraph tables.
- **Publication-State Gating**: Direct download URLs (`/documents/<id>/download`) strictly block access if the document is not linked to at least one currently `published` notice.

### 4. Interactive Flowchart Builder
- **Visual Editor**: Integrated **Drawflow** canvas supporting drag-and-drop node placement, custom wiring, and zoom/pan controls.
- **Step-to-Graph Generator**: Administrative form accepts sequential process steps and branching decision conditions, synthesizing a wired flowchart JSON structure automatically.
- **Server-Side Exporters**:
  - **Vector PDF (`/flowcharts/<id>/export/pdf`)**: Generated via `ReportLab` with institutional typography and headers.
  - **Raster PNG (`/flowcharts/<id>/export/png`)**: High-resolution image rendered using Python `Pillow`.

### 5. Grounded Gemini AI Academic Assistant
- **Context Filtering**: Retrieval searches only `published` notices and successfully extracted document text.
- **Indirect Prompt Injection Defense**: Uploaded text is treated as untrusted data; delimiter override attempts (`<<<UNTRUSTED_ACADEMIC_DATA_END>>>`) and persona redirection strings are sanitized.
- **Server-Side Citation Allowlist**: Resolves citations (`[NOTICE-X]`, `[DOC-Y]`) strictly against server-vetted entity IDs to eliminate hallucinated hyperlinks.
- **Resilient Offline Directory Fallback**: If `GEMINI_API_KEY` is not provided or the Google API times out, the assistant cleanly reverts to an offline keyword search engine without failing.

---

## 🧪 Verification & Automated Regression Testing

CampusQuery features an exhaustive automated test suite comprising **168 test cases across 12 distinct test suites**, achieving a 100% pass rate.

### Executing the Pytest Suite
Run the full test suite with verbose output:

```powershell
& .venv\Scripts\python.exe -m pytest tests -v
```

### Test Suite Breakdown:
| Test Module | Focus Area | Checks | Status |
| :--- | :--- | :---: | :---: |
| `tests/test_authentication.py` | Registration, login, scrypt hashing, session hijacking prevention, RBAC barriers | 14 | ✅ PASSED |
| `tests/test_database_crud.py` | Schema constraints, foreign key cascades, transaction atomicity, connection cleanup | 10 | ✅ PASSED |
| `tests/test_admin_notices.py` | Notice CRUD, milestone validations, category protections, draft-publish transitions | 23 | ✅ PASSED |
| `tests/test_student_portal.py` | Student dashboard, parameterized search, category filters, pagination, empty states | 17 | ✅ PASSED |
| `tests/test_deadlines_and_notifications.py` | Deadline engine, status calculations, notification triggers, mark-all-read | 17 | ✅ PASSED |
| `tests/test_document_management.py` | PDF/DOCX magic bytes, extraction edge cases, download authorization gating | 21 | ✅ PASSED |
| `tests/test_flowchart_builder.py` | Graph JSON validation, node schemas, step generator, binary PNG & PDF exports | 15 | ✅ PASSED |
| `tests/test_gemini_assistant.py` | Indirect prompt injection defense, server citation allowlist, offline fallback | 15 | ✅ PASSED |
| `tests/test_phase10_security_and_regression.py` | Independent security audit, CSRF enforcement, XSS escaping, parameterization | 18 | ✅ PASSED |
| `tests/test_phase11_accessibility.py` | WCAG AA color contrast, explicit form labels, skip-navigation, aria landmarks | 10 | ✅ PASSED |
| `tests/test_phase11_mobile_responsive.py` | Responsive viewports (375px mobile, 768px tablet, 1280px desktop), touch targets | 8 | ✅ PASSED |
| `tests/test_phase12_final_acceptance.py` | Complete end-to-end user workflows, admin notice lifecycle, secret protection | 9 | ✅ PASSED |
| **TOTAL** | **Full System Regression Suite** | **168** | **✅ 100% PASS** |

### Live HTTP Socket Verification
Verify all live HTTP endpoints, static assets, and session authentication against the running server:

```powershell
& .venv\Scripts\python.exe scripts\verify_phase12_live.py
```

---

## 🛠️ Comprehensive Troubleshooting Guide

### 1. `2003: Can't connect to MySQL server on 'localhost:3306'`
- **Cause**: MySQL Windows service is stopped or port 3306 is not listening.
- **Resolution**:
  1. Open PowerShell as Administrator and run: `Start-Service MySQL80`
  2. Verify listening status: `Test-NetConnection -ComputerName localhost -Port 3306`
  3. **Note**: If MySQL cannot be run locally, CampusQuery's transparent fallback automatically creates and utilizes `instance/campusqueri_dev.db` with identical schema and functionality.

### 2. `Address already in use` (Port 5000 Conflict)
- **Cause**: Another background process or previous Flask instance is holding port 5000.
- **Resolution**:
  ```powershell
  # Locate the PID occupying port 5000:
  Get-NetTCPConnection -LocalPort 5000 | Select-Object OwningProcess

  # Terminate the process (replace <PID>):
  Stop-Process -Id <PID> -Force
  ```

### 3. `413 Request Entity Too Large`
- **Cause**: Uploaded file exceeds the configured 10 MB limit (`MAX_CONTENT_LENGTH = 10 * 1024 * 1024`).
- **Resolution**: Compress the PDF/DOCX or adjust `MAX_CONTENT_LENGTH` in `app/config.py` if larger files are required by institution policy.

### 4. `400 Bad Request: CSRF session token missing`
- **Cause**: Submitting a state-changing form (POST) without a valid `csrf_token` input, or submitting after an expired session.
- **Resolution**: Ensure `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` is present inside the form and clear stale browser cookies if necessary.

### 5. Document Extraction Returns `scanned_ocr_required`
- **Cause**: Uploaded PDF contains raster images of scanned text rather than selectable text streams.
- **Resolution**: This is expected and honest behavior. CampusQuery transparently flags documents requiring OCR without claiming non-existent OCR support or producing corrupted text output.

### 6. Gemini Assistant Shows "Operating in Offline Grounded Directory Mode"
- **Cause**: `GEMINI_API_KEY` is omitted from `.env`, or the external Google GenAI API timed out.
- **Resolution**: Supply a valid API key in `.env` (`GEMINI_API_KEY=AIzaSy...`). The portal remains fully functional in offline mode, answering student inquiries directly from matching database records.

---

## 📋 Release Acceptance Checklist & Feature Matrix

| Phase | Milestone Name | Objective & Deliverables | Verification Evidence | Status |
| :---: | :--- | :--- | :--- | :---: |
| **01** | Workspace Audit & Foundation | Directory structure, `.venv`, blueprints, application factory | `scripts/verify_foundation.py` | ✅ Complete |
| **02** | MySQL Database & Demo Data | Schema, tables, relationships, indexes, `schema.sql`, seeder | `scripts/verify_database.py` | ✅ Complete |
| **03** | Authentication & RBAC | Student/admin auth, scrypt passwords, session hardening, CSRF | `tests/test_authentication.py` | ✅ Complete |
| **04** | Admin Panel & Content | Summaries, notice CRUD, lifecycle states, milestone dates | `tests/test_admin_notices.py` | ✅ Complete |
| **05** | Student Portal & Search | Category tiles, parameterized search, filters, pagination | `tests/test_student_portal.py` | ✅ Complete |
| **06** | Deadlines & Notifications | Milestone calculation, in-portal notifications, office cards | `tests/test_deadlines_and_notifications.py` | ✅ Complete |
| **07** | Document Management | PDF/DOCX uploads, magic bytes, extraction, download gating | `tests/test_document_management.py` | ✅ Complete |
| **08** | Flowchart Builder | Drawflow editor, step generator, binary PNG & PDF exporters | `tests/test_flowchart_builder.py` | ✅ Complete |
| **09** | Grounded Gemini AI | Context retrieval, prompt injection defense, offline fallback | `tests/test_gemini_assistant.py` | ✅ Complete |
| **10** | Security Audit & Regression | Independent QA, parameterized queries, XSS & CSRF defense | `tests/test_phase10_security_and_regression.py` | ✅ Complete |
| **11** | UI Polish & Accessibility | WCAG AA contrast, focus rings, responsive mobile/desktop | `tests/test_phase11_accessibility.py` | ✅ Complete |
| **12** | Final Acceptance & Release | End-to-end workflow audit, setup guide, release documentation | `tests/test_phase12_final_acceptance.py` | ✅ Complete |

---

## 📄 License & Attribution

- **License**: MIT Open Source License.
- **Project**: Developed for the **TYBCA (Third Year Bachelor of Computer Applications)** academic curriculum.
- **Components**:
  - [Bootstrap 5](https://getbootstrap.com) (MIT License)
  - [Bootstrap Icons](https://icons.getbootstrap.com) (MIT License)
  - [Drawflow](https://github.com/jerosoler/Drawflow) (MIT License)
  - [ReportLab](https://www.reportlab.com) (BSD License)
  - [Pillow](https://python-pillow.org) (HPND License)
  - [Google GenAI SDK](https://github.com/google-gemini) (Apache 2.0)
