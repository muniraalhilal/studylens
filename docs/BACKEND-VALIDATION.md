# Backend verification — 28 September 2026

## Results

- **29 automated cases passed** on Python 3.12 / SQLite.
- **21 live HTTPS checks passed** against the actual public demo, in 5.54 seconds.
- Browser verification: Arabic no-signup entry → isolated workspace → automatic bilingual sample files → logout. No JavaScript console errors were observed.

## Automated coverage

Authentication and session expiry; hashed session tokens; per-visitor ownership on every document operation and quiz submission; guest resume without duplicate samples; guest cleanup without deleting personal accounts; rollback if sample creation fails; Secure/HttpOnly cookies; public mode disabling password registration/login; forged cookie rejection; exact quiz scoring; simultaneous submissions yielding one success and one conflict; strict answer validation; demo quotas; actual streamed request-body limits; parser timeouts; cited answer provenance; cascading deletion of only the owner's study records; real PDF and PPTX processing; malformed files; Arabic retrieval; origin validation and throttling.

## Live checks through the public URL

1. HTTPS and database health.
2. Public demo-only configuration.
3. Access denied without a session.
4. No-registration entry.
5. Secure HttpOnly cookie.
6. Automatic bilingual samples.
7. Existing guest session resumes.
8. A second visitor gets an independent identity.
9. Other visitor's document cannot be read.
10. Other visitor's document cannot be deleted.
11. File upload and separate-process parsing work.
12. Summary and flashcards are generated.
13. Document question returns cited passages.
14. Unrelated question returns no-match.
15. All correct answers produce exactly 100% on the server.
16. Repeated submission is rejected.
17. Card review is saved.
18. Progress reflects saved database records.
19. Another visitor's progress is unchanged.
20. Cross-origin mutations are rejected.
21. Logout revokes access.

## Scope and limits

These checks verify the small demo's behavior, not a formal security audit or production load certification. PostgreSQL/Docker and Windows execution have not been exercised. Rate limiting is per-process. File parsing runs in a disposable subprocess with a 15-second wall-clock timeout and Unix CPU limit (plus Linux address-space limit), not a full OS sandbox. One non-failing Starlette test-client deprecation warning remains.

Guest sessions expire after 24 hours. Expired records are cleaned on startup or the next new guest session. Public preview data is stored separately in data/public-demo.db; the personal database is not exposed.


## Structural review and regression update

The latest review moved shared document ingestion, ownership checks and presentation into `services/documents.py`. Authentication, document and quiz routers now share that service instead of importing one another. Sample imports now commit as a single transaction; a new test proves rollback if the second sample fails. The full updated suite passes **29 cases**.

The public service was restarted with the reviewed code and the same HTTPS link. The 21 live checks were repeated against it. This remains a small SQLite portfolio/demo application, not a production certification. PostgreSQL remains configured but untested; schema migrations, distributed rate limiting and broader load testing are future production work.
