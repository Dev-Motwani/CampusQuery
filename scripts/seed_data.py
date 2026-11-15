"""
Database Seeding Script for CampusQueri (TYBCA Project).
Populates the database with realistic college categories, users, notices, deadlines, and flowchart workflows.
Can seed into MySQL (default) or SQLite (testing).
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.database import db
from app.models import User, Category, Notice, Deadline, Flowchart, Notification


def seed_database(app=None):
    """Executes demo data seeding within the given or default Flask application context."""
    if app is None:
        app = create_app()

    with app.app_context():
        print(">> Creating database tables if they do not exist...")
        db.create_all()

        print(">> Seeding users...")
        # 1. Users
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

        print(">> Seeding categories...")
        # 2. Categories
        categories_data = [
            ("Examination", "examination", "Semester examinations, practicals, hall tickets, and re-evaluation circulars", "bi-mortarboard"),
            ("Academics", "academics", "Syllabus updates, lecture schedules, projects, and assignment submissions", "bi-book"),
            ("Scholarship & Financial Aid", "scholarship", "Government merit scholarships, fee concession forms, and renewal notices", "bi-award"),
            ("Placements & Internships", "placement", "Campus recruitment drives, pre-placement talks, and industrial internships", "bi-briefcase"),
            ("Campus Events", "events", "Annual fests, hackathons, seminars, and technical workshops", "bi-calendar-event"),
            ("Administrative Office", "administrative", "Fee payment schedules, document clearances, railway concessions, and IDs", "bi-building"),
        ]
        category_map = {}
        for name, slug, desc, icon in categories_data:
            cat = Category.query.filter_by(slug=slug).first()
            if not cat:
                cat = Category(name=name, slug=slug, description=desc, icon=icon, is_active=True)
                db.session.add(cat)
                db.session.flush()
            category_map[slug] = cat

        print(">> Seeding notices & deadlines...")
        # 3. Notices & Deadlines
        notices_data = [
            {
                "title": "TYBCA Semester 6 Final Examination Schedule & Hall Ticket Distribution",
                "slug": "tybca-sem-6-final-exam-schedule-2026",
                "summary": "Detailed timetable for TYBCA Semester 6 Theory and Practical examinations with hall ticket pickup counters.",
                "content": "All Final Year BCA (Semester 6) students are hereby informed that the University Semester Examinations will commence from November 15, 2026. Students must clear all laboratory dues and obtain No-Dues signatures before collecting their Hall Tickets. Hall tickets will be issued at the Exam Cell (Room 204) between 10:00 AM and 04:00 PM upon presentation of valid College ID card and Fee Receipt.",
                "category_slug": "examination",
                "priority": "urgent",
                "status": "published",
                "deadline": {
                    "title": "Hall Ticket Collection & No-Dues Clearance",
                    "days": 5,
                    "office_location": "Exam Cell (Room 204)",
                    "contact_person": "Prof. S. R. Joshi (Controller of Exams)",
                    "contact_email": "examcell@campusqueri.edu",
                }
            },
            {
                "title": "Post-Matric State & Central Scholarship 2026-27 Portal Opened",
                "slug": "scholarship-portal-opened-2026",
                "summary": "Eligible students must submit certified income certificates, caste certificates, and previous marksheets for online verification.",
                "content": "The Department of Higher Education has opened the scholarship portal for academic year 2026-27. All eligible candidates must complete their online registration and submit physical documentation copies at Administrative Window 3 for institutional verification. Incomplete applications or delayed submissions will not be endorsed by the college.",
                "category_slug": "scholarship",
                "priority": "high",
                "status": "published",
                "deadline": {
                    "title": "Scholarship Document Hard-Copy Verification",
                    "days": 12,
                    "office_location": "Admin Window 3 (Accounts Dept)",
                    "contact_person": "Mr. K. Verma (Scholarship In-charge)",
                    "contact_email": "scholarships@campusqueri.edu",
                }
            },
            {
                "title": "Annual IT Symposium: TechnoVision 2026 Project Submissions",
                "slug": "annual-it-symposium-technovision-2026",
                "summary": "Call for software, cloud, and AI project submissions for BCA and CS departments. Cash prizes and certificates.",
                "content": "Department of Computer Applications cordially invites entries for TechnoVision 2026. Teams comprising up to 3 students can submit software solutions in categories including Web/Cloud Applications, AI/ML Prototypes, and Mobile Solutions. Shortlisted teams will present live to industry judges on November 28, 2026.",
                "category_slug": "events",
                "priority": "medium",
                "status": "published",
                "deadline": {
                    "title": "TechnoVision Project Abstract Submission",
                    "days": 10,
                    "office_location": "Lab 4 (BCA Dept)",
                    "contact_person": "Dr. Neha Mehta (Event Coordinator)",
                    "contact_email": "technovision@campusqueri.edu",
                }
            },
            {
                "title": "TCS & Infosys Campus Placement Drive 2026 Registration",
                "slug": "tcs-infosys-campus-placement-drive-2026",
                "summary": "Pre-placement talk and registration guidelines for eligible TYBCA final year graduates.",
                "content": "The Training and Placement Cell announces the commencement of campus recruitment by TCS and Infosys. Minimum eligibility criteria: 60% aggregate across semesters 1 to 5 with no active backlogs. Interested eligible students must upload their updated resumes on the portal and register before the deadline.",
                "category_slug": "placement",
                "priority": "high",
                "status": "published",
                "deadline": {
                    "title": "Placement Portal Resume Submission",
                    "days": 7,
                    "office_location": "Training & Placement Office (Building B)",
                    "contact_person": "Prof. Rajesh Kulkarni (TPO)",
                    "contact_email": "placements@campusqueri.edu",
                }
            },
            {
                "title": "Central Library Book Returns and Final Clearance Notice",
                "slug": "central-library-book-returns-clearance",
                "summary": "All borrowed reference books must be returned prior to semester exams to avoid per-day overdue penalties.",
                "content": "Students of all streams are advised to return overdue library books by the prescribed deadline. No-Dues certificates required for exam hall ticket clearance will only be stamped after all books and penalties are accounted for.",
                "category_slug": "administrative",
                "priority": "low",
                "status": "published",
                "deadline": {
                    "title": "Final Library Clearance Deadline",
                    "days": 18,
                    "office_location": "Ground Floor Library Desk",
                    "contact_person": "Mrs. Sunita Deshmukh (Librarian)",
                    "contact_email": "library@campusqueri.edu",
                }
            }
        ]

        created_notices = []
        for n_data in notices_data:
            notice = Notice.query.filter_by(slug=n_data["slug"]).first()
            if not notice:
                notice = Notice(
                    title=n_data["title"],
                    slug=n_data["slug"],
                    summary=n_data["summary"],
                    content=n_data["content"],
                    category_id=category_map[n_data["category_slug"]].id,
                    priority=n_data["priority"],
                    status=n_data["status"],
                    published_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(days=30),
                    created_by=admin_user.id
                )
                db.session.add(notice)
                db.session.flush()

                # Add deadline
                dl_info = n_data["deadline"]
                deadline = Deadline(
                    notice_id=notice.id,
                    title=dl_info["title"],
                    due_date=datetime.utcnow() + timedelta(days=dl_info["days"]),
                    office_location=dl_info["office_location"],
                    contact_person=dl_info["contact_person"],
                    contact_email=dl_info["contact_email"],
                    status="upcoming"
                )
                db.session.add(deadline)

            created_notices.append(notice)

        print(">> Seeding flowchart...")
        # 4. Flowchart
        flowchart = Flowchart.query.filter_by(title="Exam Hall Ticket Clearance Workflow").first()
        if not flowchart:
            graph_data = {
                "nodes": [
                    {"id": "1", "type": "start", "label": "Start: Final Year Exam Preparation", "x": 100, "y": 50},
                    {"id": "2", "type": "process", "label": "Clear Department & Lab Dues", "x": 100, "y": 140},
                    {"id": "3", "type": "process", "label": "Return Borrowed Books to Library", "x": 100, "y": 230},
                    {"id": "4", "type": "decision", "label": "Fee Dues Pending?", "x": 100, "y": 320},
                    {"id": "5", "type": "process", "label": "Pay Balance at Accounts Window 2", "x": 280, "y": 320},
                    {"id": "6", "type": "process", "label": "Collect Signed No-Dues Slip", "x": 100, "y": 420},
                    {"id": "7", "type": "end", "label": "Receive Hall Ticket at Exam Cell (Room 204)", "x": 100, "y": 510}
                ],
                "edges": [
                    {"id": "e1-2", "source": "1", "target": "2", "label": ""},
                    {"id": "e2-3", "source": "2", "target": "3", "label": ""},
                    {"id": "e3-4", "source": "3", "target": "4", "label": ""},
                    {"id": "e4-5", "source": "4", "target": "5", "label": "Yes"},
                    {"id": "e5-6", "source": "5", "target": "6", "label": "Paid"},
                    {"id": "e4-6", "source": "4", "target": "6", "label": "No"},
                    {"id": "e6-7", "source": "6", "target": "7", "label": "Verified"}
                ]
            }
            flowchart = Flowchart(
                notice_id=created_notices[0].id,
                title="Exam Hall Ticket Clearance Workflow",
                description="Step-by-step procedural flowchart for students to obtain Semester Exam Hall Tickets.",
                graph_data=graph_data,
                preview_image=None,
                created_by=admin_user.id
            )
            db.session.add(flowchart)

        print(">> Seeding notifications...")
        # 5. Notifications
        existing_notif = Notification.query.filter_by(user_id=student1.id).first()
        if not existing_notif:
            notif1 = Notification(
                user_id=student1.id,
                notice_id=created_notices[0].id,
                title="Important: Exam Hall Tickets Available",
                message="Collection for TYBCA Sem 6 hall tickets begins this Thursday at Room 204.",
                is_read=False
            )
            notif2 = Notification(
                user_id=student1.id,
                notice_id=created_notices[1].id,
                title="Scholarship Document Verification Deadline",
                message="Please submit your attested income certificate at Window 3 before the deadline.",
                is_read=False
            )
            db.session.add_all([notif1, notif2])

        db.session.commit()
        print(">> Database seeding completed successfully!")

        # Print summary
        user_count = User.query.count()
        cat_count = Category.query.count()
        notice_count = Notice.query.count()
        dl_count = Deadline.query.count()
        fc_count = Flowchart.query.count()
        notif_count = Notification.query.count()

        print("-" * 50)
        print(f" Users seeded:         {user_count}")
        print(f" Categories seeded:    {cat_count}")
        print(f" Notices seeded:       {notice_count}")
        print(f" Deadlines seeded:     {dl_count}")
        print(f" Flowcharts seeded:    {fc_count}")
        print(f" Notifications seeded: {notif_count}")
        print("-" * 50)


if __name__ == "__main__":
    app = create_app()
    seed_database(app)
