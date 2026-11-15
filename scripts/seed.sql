-- ========================================================
-- CampusQueri Demo Seed Data
-- Compatible with MySQL Workbench & Flask Seed Script
-- Default Admin: admin@campusqueri.edu / Admin@123
-- Default Student: student@campusqueri.edu / Student@123
-- ========================================================

USE `campusqueri_db`;

-- --------------------------------------------------------
-- 1. Insert Users
-- --------------------------------------------------------
INSERT INTO `users` (`id`, `email`, `password_hash`, `full_name`, `roll_number`, `role`, `is_active`) VALUES
(1, 'admin@campusqueri.edu', 'scrypt:32768:8:1$ptLKQur56u3ObVHu$216cd30a308c5a186c9828f0ec0f4616be46c18ff6430b1a2a29c8cb1b9ffd56552f71a9d38298009df47e280de4cf0ff2c2e4d870000872ce842ba89daa1d8b', 'Admin Office Coordinator', NULL, 'admin', 1),
(2, 'student@campusqueri.edu', 'scrypt:32768:8:1$f49CADL4jMQXKG7N$e91b39c4d40ed0e85bface8526970d16b840a130745bbd437796e22f25f0b7444fe76ca2e879bae0e9c7619e91b580a8e335928417884e27ee31bf1e610a44bf', 'Aarav Patel', 'TYBCA-2026-001', 'student', 1),
(3, 'priya.sharma@campusqueri.edu', 'scrypt:32768:8:1$f49CADL4jMQXKG7N$e91b39c4d40ed0e85bface8526970d16b840a130745bbd437796e22f25f0b7444fe76ca2e879bae0e9c7619e91b580a8e335928417884e27ee31bf1e610a44bf', 'Priya Sharma', 'TYBCA-2026-042', 'student', 1)
ON DUPLICATE KEY UPDATE `full_name` = VALUES(`full_name`);

-- --------------------------------------------------------
-- 2. Insert Categories
-- --------------------------------------------------------
INSERT INTO `categories` (`id`, `name`, `slug`, `description`, `icon`, `is_active`) VALUES
(1, 'Examination', 'examination', 'Semester examinations, practicals, hall tickets, and re-evaluation circulars', 'bi-mortarboard', 1),
(2, 'Academics', 'academics', 'Syllabus updates, lecture schedules, projects, and assignment submissions', 'bi-book', 1),
(3, 'Scholarship & Financial Aid', 'scholarship', 'Government merit scholarships, fee concession forms, and renewal notices', 'bi-award', 1),
(4, 'Placements & Internships', 'placement', 'Campus recruitment drives, pre-placement talks, and industrial internships', 'bi-briefcase', 1),
(5, 'Campus Events', 'events', 'Annual fests, hackathons, seminars, and technical workshops', 'bi-calendar-event', 1),
(6, 'Administrative Office', 'administrative', 'Fee payment schedules, document clearances, railway concessions, and IDs', 'bi-building', 1)
ON DUPLICATE KEY UPDATE `description` = VALUES(`description`);

-- --------------------------------------------------------
-- 3. Insert Notices
-- --------------------------------------------------------
INSERT INTO `notices` (`id`, `title`, `slug`, `summary`, `content`, `category_id`, `priority`, `status`, `published_at`, `expires_at`, `created_by`) VALUES
(1,
 'TYBCA Semester 6 Final Examination Schedule & Hall Ticket Distribution',
 'tybca-sem-6-final-exam-schedule-2026',
 'Detailed timetable for TYBCA Semester 6 Theory and Practical examinations with hall ticket pickup counters.',
 'All Final Year BCA (Semester 6) students are hereby informed that the University Semester Examinations will commence from November 15, 2026. Students must clear all laboratory dues and obtain No-Dues signatures before collecting their Hall Tickets. Hall tickets will be issued at the Exam Cell (Room 204) between 10:00 AM and 04:00 PM upon presentation of valid College ID card and Fee Receipt.',
 1, 'urgent', 'published', NOW(), DATE_ADD(NOW(), INTERVAL 30 DAY), 1),

(2,
 'Post-Matric State & Central Scholarship 2026-27 Portal Opened',
 'scholarship-portal-opened-2026',
 'Eligible students must submit certified income certificates, caste certificates, and previous marksheets for online verification.',
 'The Department of Higher Education has opened the scholarship portal for academic year 2026-27. All eligible candidates must complete their online registration and submit physical documentation copies at Administrative Window 3 for institutional verification. Incomplete applications or delayed submissions will not be endorsed by the college.',
 3, 'high', 'published', NOW(), DATE_ADD(NOW(), INTERVAL 20 DAY), 1),

(3,
 'Annual IT Symposium: TechnoVision 2026 Project Submissions',
 'annual-it-symposium-technovision-2026',
 'Call for software, cloud, and AI project submissions for BCA and CS departments. Cash prizes and certificates.',
 'Department of Computer Applications cordially invites entries for TechnoVision 2026. Teams comprising up to 3 students can submit software solutions in categories including Web/Cloud Applications, AI/ML Prototypes, and Mobile Solutions. Shortlisted teams will present live to industry judges on November 28, 2026.',
 5, 'medium', 'published', NOW(), DATE_ADD(NOW(), INTERVAL 25 DAY), 1),

(4,
 'TCS & Infosys Campus Placement Drive 2026 Registration',
 'tcs-infosys-campus-placement-drive-2026',
 'Pre-placement talk and registration guidelines for eligible TYBCA final year graduates.',
 'The Training and Placement Cell announces the commencement of campus recruitment by TCS and Infosys. Minimum eligibility criteria: 60% aggregate across semesters 1 to 5 with no active backlogs. Interested eligible students must upload their updated resumes on the portal and register before the deadline.',
 4, 'high', 'published', NOW(), DATE_ADD(NOW(), INTERVAL 15 DAY), 1),

(5,
 'Central Library Book Returns and Final Clearance Notice',
 'central-library-book-returns-clearance',
 'All borrowed reference books must be returned prior to semester exams to avoid per-day overdue penalties.',
 'Students of all streams are advised to return overdue library books by the prescribed deadline. No-Dues certificates required for exam hall ticket clearance will only be stamped after all books and penalties are accounted for.',
 6, 'low', 'published', NOW(), DATE_ADD(NOW(), INTERVAL 45 DAY), 1)
ON DUPLICATE KEY UPDATE `content` = VALUES(`content`);

-- --------------------------------------------------------
-- 4. Insert Deadlines
-- --------------------------------------------------------
INSERT INTO `deadlines` (`id`, `notice_id`, `title`, `due_date`, `office_location`, `contact_person`, `contact_email`, `status`) VALUES
(1, 1, 'Hall Ticket Collection & No-Dues Clearance', DATE_ADD(NOW(), INTERVAL 5 DAY), 'Exam Cell (Room 204)', 'Prof. S. R. Joshi (Controller of Exams)', 'examcell@campusqueri.edu', 'upcoming'),
(2, 2, 'Scholarship Document Hard-Copy Verification', DATE_ADD(NOW(), INTERVAL 12 DAY), 'Admin Window 3 (Accounts Dept)', 'Mr. K. Verma (Scholarship In-charge)', 'scholarships@campusqueri.edu', 'upcoming'),
(3, 3, 'TechnoVision Project Abstract Submission', DATE_ADD(NOW(), INTERVAL 10 DAY), 'Lab 4 (BCA Dept)', 'Dr. Neha Mehta (Event Coordinator)', 'technovision@campusqueri.edu', 'upcoming'),
(4, 4, 'Placement Portal Resume Submission', DATE_ADD(NOW(), INTERVAL 7 DAY), 'Training & Placement Office (Building B)', 'Prof. Rajesh Kulkarni (TPO)', 'placements@campusqueri.edu', 'upcoming'),
(5, 5, 'Final Library Clearance Deadline', DATE_ADD(NOW(), INTERVAL 18 DAY), 'Ground Floor Library Desk', 'Mrs. Sunita Deshmukh (Librarian)', 'library@campusqueri.edu', 'upcoming')
ON DUPLICATE KEY UPDATE `title` = VALUES(`title`);

-- --------------------------------------------------------
-- 5. Insert Sample Flowchart
-- --------------------------------------------------------
INSERT INTO `flowcharts` (`id`, `notice_id`, `title`, `description`, `graph_data`, `preview_image`, `created_by`) VALUES
(1, 1, 'Exam Hall Ticket Clearance Workflow',
 'Step-by-step procedural flowchart for students to obtain Semester Exam Hall Tickets.',
 '{
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
 }',
 NULL, 1)
ON DUPLICATE KEY UPDATE `title` = VALUES(`title`);

-- --------------------------------------------------------
-- 6. Insert Notifications
-- --------------------------------------------------------
INSERT INTO `notifications` (`id`, `user_id`, `notice_id`, `title`, `message`, `is_read`) VALUES
(1, 2, 1, 'Important: Exam Hall Tickets Available', 'Collection for TYBCA Sem 6 hall tickets begins this Thursday at Room 204.', 0),
(2, 2, 2, 'Scholarship Document Verification Deadline', 'Please submit your attested income certificate at Window 3 before the deadline.', 0),
(3, 3, 4, 'Placement Registration Open', 'TCS & Infosys registration link is now live on the student dashboard.', 0)
ON DUPLICATE KEY UPDATE `title` = VALUES(`title`);
