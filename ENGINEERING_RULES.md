# CampusQueri — Permanent Engineering and Verification Rules

These rules apply to every phase of development. Never ignore them to save time.

---

## A. Inspect before modifying
1. Inspect the current project structure, configuration, dependencies and existing code.
2. Identify what is already implemented and preserve working functionality.
3. Read the relevant files before changing them.
4. Make a short plan listing files to create or modify and possible side effects.
5. Never overwrite existing work without understanding its purpose.

---

## B. Verify every code change
1. Review every changed file for syntax errors, missing imports, undefined variables, incorrect function calls, incorrect paths and inconsistent names.
2. Check that routes, templates, forms, database columns, JavaScript selectors and API responses agree with one another.
3. Check that environment variables are loaded correctly and secrets are not hardcoded.
4. Run Python compilation checks, such as `python -m compileall app scripts tests`, where applicable.
5. Run the relevant automated tests.
6. Start the application and exercise affected routes or workflows using the available local testing environment.
7. Check browser console errors and server logs when browser testing is available.
8. Verify database writes and reads against the configured MySQL database.

---

## C. Repeated execution and debugging
1. Perform at least three distinct verification passes for each meaningful implementation phase:
   - **Pass 1:** Static review, compilation and configuration checks.
   - **Pass 2:** Automated unit/integration tests and direct workflow tests.
   - **Pass 3:** Restart the relevant services, rerun the tests, and execute regression checks.
2. These must be real executions, not three repetitions of a claim or three identical commands without inspecting the results.
3. If a test fails, inspect the error, identify the root cause, fix the code and rerun the failed test.
4. After each fix, rerun the affected tests and the wider regression suite.
5. Repeat this process until the relevant checks pass or a genuine environmental blocker is documented.
6. Never suppress exceptions, weaken assertions, skip failing tests, or replace MySQL with SQLite just to obtain a passing result.
7. Do not report a command as successful unless its actual exit status and output support that conclusion.

---

## D. MySQL requirements
- Use MySQL, not SQLite.
- Test using the configured MySQL Server and database.
- Verify schema initialization, foreign keys, parameterized queries, commits, rollbacks and connection cleanup where applicable.
- Use a dedicated test database and safe test data.
- Do not destroy user data or reset a database without explicit authorization.
- If MySQL is unavailable, separate tests that genuinely passed from integration tests that could not run.

---

## E. Security requirements
- Never expose passwords, API keys, session secrets or database credentials.
- Keep `.env` out of version control.
- Enforce student/admin authorization on the server.
- Use password hashes, CSRF protection, secure sessions and server-side validation.
- Protect uploads and downloads, prevent path traversal and restrict file types and sizes.
- Keep drafts and archived content out of current student views and AI retrieval.
- Never trust client-side validation alone.

---

## F. Definition of done
A feature is complete only when its implementation exists, the relevant tests have actually run, failure cases have been checked, and connected workflows have been verified.

Maintain a project status report with these labels:
- **IMPLEMENTED AND TESTED**
- **IMPLEMENTED, NOT FULLY TESTED**
- **PARTIALLY IMPLEMENTED**
- **BLOCKED BY ENVIRONMENT**
- **NOT IMPLEMENTED**

Never claim the whole project is error-free or production-ready without evidence. Screenshots must come from the actual running application.

---

## G. Required report after every phase
Provide:
1. Files created or changed.
2. Features implemented.
3. Commands executed and their actual results.
4. Test counts and pass/fail results.
5. The three verification passes and what each verified.
6. Bugs found and the fixes applied.
7. Remaining defects, limitations and environmental blockers.
8. Exact commands to run the application.
9. A clear recommendation on whether the next phase can safely begin.

Do not start the next phase until the current phase's acceptance criteria are met or its unresolved blockers are explicitly identified.
