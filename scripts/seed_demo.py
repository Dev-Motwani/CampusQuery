"""
Demo Seed Script for CampusQuery (Phase 2).
Populates realistic, visibly marked SAMPLE data for:
- Users (Admin, Students)
- Categories (Scholarships, Admissions, CET, Examinations, Sports, Events, General)
- Fictional Offices (visibly marked SAMPLE)
- Notices with multiple deadline milestones
- Flowchart diagrams & Document attachments

Repeatable & idempotent: Safe to execute multiple times without duplicates.
"""
import os
import sys
import hashlib
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Force UTF-8 encoding for Windows console compatibility
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app import create_app
from app.database import db
from app.models import (
    User,
    Category,
    OfficeInformation,
    Notice,
    Deadline,
    Document,
    NoticeDocument,
    Flowchart,
    NoticeFlowchart,
    Notification
)


def seed_demo_data(app=None, verbose=True):
    """Executes repeatable seed operations inside an explicit transaction."""
    if app is None:
        app = create_app("development")

    def log(msg):
        if verbose:
            print(msg)

    with app.app_context():
        log("=" * 65)
        log(" [CAMPUSQUERY] DEMO SEED DATA GENERATOR")
        log("=" * 65)

        try:
            # 1. Users
            log("\n>> [1/6] Seeding Users...")
            admin_user = User.query.filter_by(email="admin@campusqueri.edu").first()
            if not admin_user:
                admin_user = User(
                    email="admin@campusqueri.edu",
                    full_name="Admin Office Coordinator",
                    roll_number=None,
                    role="admin",
                    is_active=True
                )
                admin_user.set_password("Admin@123")
                db.session.add(admin_user)

            student1 = User.query.filter_by(email="student@campusqueri.edu").first()
            if not student1:
                student1 = User(
                    email="student@campusqueri.edu",
                    full_name="Aarav Patel",
                    roll_number="TYBCA-2026-001",
                    role="student",
                    is_active=True
                )
                student1.set_password("Student@123")
                db.session.add(student1)

            student2 = User.query.filter_by(email="priya.sharma@campusqueri.edu").first()
            if not student2:
                student2 = User(
                    email="priya.sharma@campusqueri.edu",
                    full_name="Priya Sharma",
                    roll_number="TYBCA-2026-042",
                    role="student",
                    is_active=True
                )
                student2.set_password("Student@123")
                db.session.add(student2)

            db.session.flush()
            log("   [PASS] 3 Users verified/seeded")

            # 2. Categories (Scholarships, Admissions, CET, Examinations, Sports, Events, General)
            log("\n>> [2/6] Seeding Categories...")
            categories_data = [
                ("Scholarships", "scholarships", "State & Central government financial aid, fee concessions, and minority grants.", "bi-award"),
                ("Admissions", "admissions", "Undergraduate and postgraduate admission rounds, eligibility lists, and counseling.", "bi-door-open"),
                ("CET", "cet", "State Common Entrance Test schedules, syllabus, center lists, and scorecards.", "bi-card-checklist"),
                ("Examinations", "examinations", "Semester exams, practical evaluations, hall tickets, and re-checking circulars.", "bi-mortarboard"),
                ("Sports", "sports", "Inter-collegiate championships, annual athletic meets, and team trials.", "bi-trophy"),
                ("Events", "events", "Annual technical fests, hackathons, guest lectures, and cultural galas.", "bi-calendar-event"),
                ("General Notices", "general", "Library dues, campus identity cards, bus/railway concessions, and holiday alerts.", "bi-megaphone"),
            ]
            category_map = {}
            for name, slug, desc, icon in categories_data:
                cat = Category.query.filter_by(slug=slug).first()
                if not cat:
                    cat = Category(name=name, slug=slug, description=desc, icon=icon, is_active=True)
                    db.session.add(cat)
                    db.session.flush()
                category_map[slug] = cat
            log(f"   [PASS] {len(category_map)} Categories verified/seeded")

            # 3. Fictional Office Information (Visibly marked SAMPLE)
            log("\n>> [3/6] Seeding Sample Office Information...")
            offices_data = [
                {
                    "name": "[SAMPLE] Office of the Controller of Examinations",
                    "department": "Examination Section",
                    "building": "[SAMPLE] Main Academic Block, Room 204",
                    "person": "[SAMPLE] Prof. S. R. Joshi",
                    "email": "sample.examcell@campusqueri.edu",
                    "phone": "[SAMPLE] +91 20 2550 0101",
                    "hours": "[SAMPLE] Mon-Fri 10:00 AM - 04:30 PM",
                    "visit_instructions": "Bring original College ID card and Fee Clearance Slip. Submit hall ticket grievance forms at Counter 1 before 02:00 PM.",
                },
                {
                    "name": "[SAMPLE] Central Admissions & Eligibility Desk",
                    "department": "Academic Admissions Directorate",
                    "building": "[SAMPLE] Admin Hall Counter 2",
                    "person": "[SAMPLE] Dr. Anita Kulkarni",
                    "email": "sample.admissions@campusqueri.edu",
                    "phone": "[SAMPLE] +91 20 2550 0102",
                    "hours": "[SAMPLE] Mon-Sat 09:30 AM - 05:00 PM",
                    "visit_instructions": "Carry original 10th/12th marksheets with two sets of self-attested photocopies and CAP allotment letter.",
                },
                {
                    "name": "[SAMPLE] State CET Facilitation Center (FC-6142)",
                    "department": "State CET Cell Liaison",
                    "building": "[SAMPLE] Computer Center Building, Lab 2",
                    "person": "[SAMPLE] Prof. R. V. Patil",
                    "email": "sample.cet@campusqueri.edu",
                    "phone": "[SAMPLE] +91 20 2550 0103",
                    "hours": "[SAMPLE] Mon-Fri 10:00 AM - 04:00 PM",
                    "visit_instructions": "Token numbers issued from 09:30 AM. Verify digital application status online prior to physical document scrutiny.",
                },
                {
                    "name": "[SAMPLE] Student Welfare & Scholarship Desk",
                    "department": "Student Welfare Department",
                    "building": "[SAMPLE] Student Amenities Building, Window 4",
                    "person": "[SAMPLE] Mr. K. Verma",
                    "email": "sample.scholarships@campusqueri.edu",
                    "phone": "[SAMPLE] +91 20 2550 0104",
                    "hours": "[SAMPLE] Mon-Fri 10:30 AM - 03:30 PM",
                    "visit_instructions": "Submit MahaDBT application printouts along with valid Income Certificate and Domicile Certificate during desk hours.",
                },
                {
                    "name": "[SAMPLE] Department of Physical Education & Sports",
                    "department": "Physical Education & Athletics",
                    "building": "[SAMPLE] Sports Complex Office",
                    "person": "[SAMPLE] Coach Vikram Deshmukh",
                    "email": "sample.sports@campusqueri.edu",
                    "phone": "[SAMPLE] +91 20 2550 0105",
                    "hours": "[SAMPLE] Mon-Sat 07:00 AM - 11:00 AM, 04:00 PM - 07:00 PM",
                    "visit_instructions": "Report in athletic kit with medical fitness certificate from registered medical practitioner for team trials.",
                },
            ]
            office_records = []
            for o in offices_data:
                office = OfficeInformation.query.filter_by(office_name=o["name"]).first()
                if not office:
                    office = OfficeInformation(
                        office_name=o["name"],
                        department=o.get("department"),
                        building_room=o["building"],
                        contact_person=o["person"],
                        contact_email=o["email"],
                        contact_phone=o["phone"],
                        office_hours=o["hours"],
                        visit_instructions=o.get("visit_instructions"),
                        is_sample=True
                    )
                    db.session.add(office)
                    db.session.flush()
                else:
                    office.department = o.get("department")
                    office.visit_instructions = o.get("visit_instructions")
                office_records.append(office)
            log(f"   [PASS] {len(office_records)} Sample Offices verified/seeded")

            # 4. Notices with Multiple Deadlines (Task 5 & 6)
            log("\n>> [4/6] Seeding Notices with Multiple Milestones...")
            notices_data = [
                {
                    "title": "[SAMPLE] TYBCA Semester 6 Final Exam Schedule & Hall Ticket Clearance",
                    "slug": "sample-tybca-sem-6-exam-schedule-2026",
                    "summary": "Mandatory clearance schedule, lab term-work submissions, and hall ticket issuance counters.",
                    "content": "All Final Year BCA Semester 6 students must complete lab journal verifications and obtain No-Dues signatures prior to collecting hall tickets.",
                    "cat": "examinations",
                    "priority": "urgent",
                    "status": "published",
                    "office_idx": 0,
                    "milestones": [
                        ("Lab Journal & Project Viva Clearance", 4, "ongoing", "Department Lab 3"),
                        ("Hall Ticket Pickup Counter", 8, "upcoming", "Exam Cell Room 204"),
                        ("Commencement of Theory Examinations", 20, "upcoming", "Exam Centers A & B"),
                    ]
                },
                {
                    "title": "[SAMPLE] Post-Graduate MCA / M.Sc. Admission Rounds 2026-27",
                    "slug": "sample-pg-mca-admission-rounds-2026",
                    "summary": "Institutional rounds counseling and document verification for BCA graduates.",
                    "content": "Eligible candidates seeking admission to MCA Semester 1 must report with original CET scorecards and marksheets.",
                    "cat": "admissions",
                    "priority": "high",
                    "status": "published",
                    "office_idx": 1,
                    "milestones": [
                        ("Online Application & Option Form Submission", 7, "ongoing", "Online Portal"),
                        ("Physical Document Verification Round 1", 14, "upcoming", "Admin Hall Counter 2"),
                        ("Final Fee Payment & Seat Confirmation", 21, "upcoming", "Accounts Window 1"),
                    ]
                },
                {
                    "title": "[SAMPLE] State CET 2026 Hall Ticket Download & Mock Test Schedule",
                    "slug": "sample-state-cet-2026-mock-tests",
                    "summary": "Admit cards for Common Entrance Test available for download. Computer-based mock practice links active.",
                    "content": "Registered CET candidates can access the online examination simulation link and verify allotted test centers.",
                    "cat": "cet",
                    "priority": "medium",
                    "status": "published",
                    "office_idx": 2,
                    "milestones": [
                        ("Hall Ticket Error Correction Window", 5, "ongoing", "CET Desk Room 108"),
                        ("Statewide Online Mock Simulation", 11, "upcoming", "Center Lab 1"),
                    ]
                },
                {
                    "title": "[SAMPLE] State & Central Merit Scholarship Renewal Portal 2026",
                    "slug": "sample-merit-scholarship-renewal-2026",
                    "summary": "Eligible students must upload income certificates, caste affidavits, and bank passbooks.",
                    "content": "Government scholarship portal is accepting renewal applications for current academic session.",
                    "cat": "scholarships",
                    "priority": "high",
                    "status": "published",
                    "office_idx": 3,
                    "milestones": [
                        ("Online Document Upload Deadline", 15, "upcoming", "National Scholarship Portal"),
                        ("College Endorsement & Hard Copy Scrutiny", 25, "upcoming", "Window 4 Accounts"),
                    ]
                },
                {
                    "title": "[SAMPLE] Inter-Collegiate Cricket & Badminton Selection Trials",
                    "slug": "sample-intercollegiate-sports-trials-2026",
                    "summary": "Selection trials for university sports contingent. BCA students eligible to participate.",
                    "content": "Department of Physical Education invites interested players for trials at the campus ground.",
                    "cat": "sports",
                    "priority": "medium",
                    "status": "published",
                    "office_idx": 4,
                    "milestones": [
                        ("Athlete Medical Fitness Submission", 6, "upcoming", "Gymnasium Desk"),
                        ("Physical Ground Trials & Match Selections", 9, "upcoming", "Main Cricket Ground"),
                    ]
                },
                {
                    "title": "[SAMPLE] TechnoVision 2026 Annual IT Hackathon & Symposium",
                    "slug": "sample-technovision-hackathon-2026",
                    "summary": "48-hour software development challenge for Computer Applications students with cash prizes.",
                    "content": "Teams of 2 to 4 students can register prototypes in Web Dev, AI/ML, and Cloud Systems.",
                    "cat": "events",
                    "priority": "medium",
                    "status": "published",
                    "office_idx": 2,
                    "milestones": [
                        ("Abstract & Problem Statement Submission", 10, "upcoming", "Online Form"),
                        ("Live Code Submission & Jury Presentation", 24, "upcoming", "Auditorium Hall"),
                    ]
                },
                {
                    "title": "[SAMPLE] Central Library Clearance & Smart Campus ID Card Issuance",
                    "slug": "sample-library-clearance-smart-card-2026",
                    "summary": "Return overdue library books and pick up RFID-enabled smart campus access badges.",
                    "content": "All students must clear pending library book dues before the semester exam clearance window.",
                    "cat": "general",
                    "priority": "low",
                    "status": "published",
                    "office_idx": 0,
                    "milestones": [
                        ("Overdue Book Return Amnesty Period", 12, "upcoming", "Ground Floor Library Desk"),
                        ("RFID Smart Identity Card Distribution", 22, "upcoming", "Admin Hall Window 1"),
                    ]
                },
            ]

            notice_records = []
            for n in notices_data:
                notice = Notice.query.filter_by(slug=n["slug"]).first()
                if not notice:
                    notice = Notice(
                        title=n["title"],
                        slug=n["slug"],
                        summary=n["summary"],
                        content=n["content"],
                        category_id=category_map[n["cat"]].id,
                        priority=n["priority"],
                        status=n["status"],
                        published_at=datetime.utcnow(),
                        expires_at=datetime.utcnow() + timedelta(days=45),
                        created_by=admin_user.id,
                        office_id=office_records[n["office_idx"]].id,
                        eligibility="Enrolled students with verified admission status and valid college credentials.",
                        required_documents="College Identity Card, Relevant Marksheet, Fee Challan / Payment Receipt.",
                        submission_instructions="Present physical forms and original verification documents at the specified office desk."
                    )
                    db.session.add(notice)
                    db.session.flush()

                    # Add Multiple Milestones per notice
                    for m_name, days_ahead, m_status, instructions in n["milestones"]:
                        dl = Deadline(
                            notice_id=notice.id,
                            milestone_name=m_name,
                            due_date=datetime.utcnow() + timedelta(days=days_ahead),
                            status=m_status,
                            office_id=office_records[n["office_idx"]].id,
                            instructions=instructions
                        )
                        db.session.add(dl)

                notice_records.append(notice)
            log(f"   [PASS] {len(notice_records)} Notices seeded with multi-milestone deadlines")

            # 5. Documents & Flowcharts Junction Links
            log("\n>> [5/6] Seeding Flowcharts, Documents & Junction Links...")
            # Sample Flowchart
            fc = Flowchart.query.filter_by(slug="sample-hall-ticket-clearance-workflow").first()
            if not fc:
                fc = Flowchart(
                    title="[SAMPLE] Exam Hall Ticket Clearance Workflow",
                    slug="sample-hall-ticket-clearance-workflow",
                    description="Step-by-step procedural diagram for semester hall ticket clearance.",
                    graph_data={
                        "nodes": [
                            {"id": "1", "type": "start", "label": "Start: Lab Journal Verification", "x": 100, "y": 50},
                            {"id": "2", "type": "process", "label": "Sign No-Dues at Library Desk", "x": 100, "y": 140},
                            {"id": "3", "type": "decision", "label": "Fee Pending?", "x": 100, "y": 230},
                            {"id": "4", "type": "process", "label": "Clear Balance at Window 2", "x": 280, "y": 230},
                            {"id": "5", "type": "end", "label": "Receive Hall Ticket (Room 204)", "x": 100, "y": 320}
                        ],
                        "edges": [
                            {"id": "e1-2", "source": "1", "target": "2"},
                            {"id": "e2-3", "source": "2", "target": "3"},
                            {"id": "e3-4", "source": "3", "target": "4", "label": "Yes"},
                            {"id": "e4-5", "source": "4", "target": "5"},
                            {"id": "e3-5", "source": "3", "target": "5", "label": "No"}
                        ]
                    },
                    created_by=admin_user.id
                )
                db.session.add(fc)
                db.session.flush()

                # Link to exam notice
                nf = NoticeFlowchart(
                    notice_id=notice_records[0].id,
                    flowchart_id=fc.id,
                    caption="Visual Procedure for Hall Ticket Clearance"
                )
                db.session.add(nf)

            # Sample Documents (Physical files & DB metadata)
            upload_docs_dir = os.path.join(app.root_path, "..", "uploads", "documents")
            os.makedirs(upload_docs_dir, exist_ok=True)

            pdf_path = os.path.join(upload_docs_dir, "sample_exam_guidelines_2026.pdf")
            if not os.path.exists(pdf_path):
                import io, pypdf
                raw_pdf = b"""%PDF-1.4
1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj
2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj
3 0 obj <</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources <</Font <</F1 5 0 R>>>>>> endobj
4 0 obj <</Length 62>> stream
BT
/F1 12 Tf
100 700 Td
(Official TYBCA Examination Guidelines & Clearance Schedule 2026) Tj
ET
endstream
endobj
5 0 obj <</Type /Font /Subtype /Type1 /BaseFont /Helvetica>> endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000244 00000 n 
0000000357 00000 n 
trailer <</Size 6 /Root 1 0 R>>
startxref
431
%%EOF
"""
                try:
                    r = pypdf.PdfReader(io.BytesIO(raw_pdf))
                    w = pypdf.PdfWriter()
                    w.append(r)
                    with open(pdf_path, "wb") as f:
                        w.write(f)
                except Exception:
                    with open(pdf_path, "wb") as f:
                        f.write(raw_pdf)

            docx_path = os.path.join(upload_docs_dir, "sample_scholarship_checklist.docx")
            if not os.path.exists(docx_path):
                try:
                    import docx
                    d = docx.Document()
                    d.add_heading("Scholarship Application Required Documents Checklist", level=1)
                    d.add_paragraph("1. Domicile Certificate issued by Competent Authority")
                    d.add_paragraph("2. Annual Income Certificate for current financial year")
                    d.add_paragraph("3. Previous Year Academic Marksheets (All Semesters)")
                    d.add_paragraph("4. Aadhaar Card linked with Bank Account")
                    d.save(docx_path)
                except Exception as e:
                    print(f"   [WARN] Could not generate sample docx: {e}")

            # Document 1: PDF Exam Guidelines
            pdf_bytes = open(pdf_path, "rb").read() if os.path.exists(pdf_path) else b"%PDF-1.4 mock"
            doc1 = Document.query.filter_by(filename="sample_exam_guidelines_2026.pdf").first()
            if not doc1:
                doc1 = Document(
                    filename="sample_exam_guidelines_2026.pdf",
                    original_name="Official_TYBCA_Exam_Guidelines_2026.pdf",
                    file_path="uploads/documents/sample_exam_guidelines_2026.pdf",
                    file_size=len(pdf_bytes),
                    file_type="application/pdf",
                    label="Detailed Instructions",
                    description="Official instructions for hall ticket clearance and lab journal submissions.",
                    extracted_text="Official TYBCA Examination Guidelines & Clearance Schedule 2026",
                    extraction_status="success",
                    sha256_hash=hashlib.sha256(pdf_bytes).hexdigest(),
                    uploaded_by=admin_user.id
                )
                db.session.add(doc1)
                db.session.flush()

                nd1 = NoticeDocument(
                    notice_id=notice_records[0].id,
                    document_id=doc1.id,
                    display_label="Download Official Exam Rules PDF"
                )
                db.session.add(nd1)
            else:
                doc1.label = "Detailed Instructions"
                doc1.file_size = len(pdf_bytes)
                doc1.extracted_text = "Official TYBCA Examination Guidelines & Clearance Schedule 2026"
                doc1.extraction_status = "success"
                doc1.sha256_hash = hashlib.sha256(pdf_bytes).hexdigest()

            # Document 2: DOCX Scholarship Checklist
            docx_bytes = open(docx_path, "rb").read() if os.path.exists(docx_path) else b"PK\x03\x04 mock"
            doc2 = Document.query.filter_by(filename="sample_scholarship_checklist.docx").first()
            if not doc2:
                doc2 = Document(
                    filename="sample_scholarship_checklist.docx",
                    original_name="MahaDBT_Scholarship_Checklist_2026.docx",
                    file_path="uploads/documents/sample_scholarship_checklist.docx",
                    file_size=len(docx_bytes),
                    file_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    label="Required-Document Checklist",
                    description="Mandatory certificates and verification checklist for state scholarships.",
                    extracted_text="Scholarship Application Required Documents Checklist: 1. Domicile Certificate 2. Income Certificate 3. Academic Marksheets 4. Aadhaar Card",
                    extraction_status="success",
                    sha256_hash=hashlib.sha256(docx_bytes).hexdigest(),
                    uploaded_by=admin_user.id
                )
                db.session.add(doc2)
                db.session.flush()

                nd2 = NoticeDocument(
                    notice_id=notice_records[3].id,
                    document_id=doc2.id,
                    display_label="Download MahaDBT Checklist (.docx)"
                )
                db.session.add(nd2)
            else:
                doc2.label = "Required-Document Checklist"
                doc2.file_size = len(docx_bytes)
                doc2.extracted_text = "Scholarship Application Required Documents Checklist: 1. Domicile Certificate 2. Income Certificate 3. Academic Marksheets 4. Aadhaar Card"
                doc2.extraction_status = "success"
                doc2.sha256_hash = hashlib.sha256(docx_bytes).hexdigest()

            # 6. Notifications
            log("\n>> [6/6] Seeding Student Alerts...")
            if not Notification.query.filter_by(user_id=student1.id).first():
                notif1 = Notification(
                    user_id=student1.id,
                    notice_id=notice_records[0].id,
                    title="Important: Exam Clearance Schedule Released",
                    message="TYBCA Sem 6 hall ticket clearance begins this week at Room 204.",
                    notification_type="new_notice",
                    is_read=False
                )
                notif2 = Notification(
                    user_id=student1.id,
                    notice_id=notice_records[3].id,
                    title="Scholarship Renewal Deadline Approaching",
                    message="Please submit your income certificate at Window 4 before the due date.",
                    notification_type="deadline_reminder",
                    is_read=False
                )
                db.session.add_all([notif1, notif2])

            # Commit all changes atomically
            db.session.commit()
            log("\n>> [PASS] Transaction committed cleanly!")

            # Report stats
            log("\n" + "-" * 55)
            log(f" Users:             {User.query.count()}")
            log(f" Categories:        {Category.query.count()}")
            log(f" Offices (Sample):  {OfficeInformation.query.count()}")
            log(f" Notices:           {Notice.query.count()}")
            log(f" Deadlines:         {Deadline.query.count()}")
            log(f" Flowcharts:        {Flowchart.query.count()}")
            log(f" Documents:         {Document.query.count()}")
            log(f" Notifications:     {Notification.query.count()}")
            log("-" * 55)
            log("\n*** SUCCESS: Seed operations completed idempotently! ***")
            return True

        except Exception as e:
            db.session.rollback()
            log(f"\n>> [ERROR] Seeding failed, transaction rolled back: {e}")
            raise


if __name__ == "__main__":
    app = create_app("development")
    seed_demo_data(app)
