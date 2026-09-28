# Stable portfolio deployment: FastAPI + PostgreSQL

Status: deployment files are ready and local tests pass. A hosted service has **not** been provisioned yet. Render, Neon and GitHub account connections are needed before publishing.

## Target architecture

Browser → Render HTTPS service (FastAPI + static frontend) → Neon PostgreSQL.

The cloud app runs independently of the developer laptop. Render supplies the stable service URL. The free service can sleep when idle; visitors may wait for a cold start. A stable URL is not a promise of uninterrupted availability or a forever-free plan.

## Prepared configuration

- `render.yaml`: free Python web service, one worker, health endpoint, Secure cookies, public no-signup mode.
- `DATABASE_URL`: entered privately in Render; never committed. Use a Neon connection string with `sslmode=require` and any provider-supplied TLS parameters intact.
- SQLAlchemy accepts `postgres://`, `postgresql://` or explicit `postgresql+psycopg://` URLs and selects psycopg 3.
- Origin checking uses Render's `RENDER_EXTERNAL_URL` automatically. Set APP_ORIGIN only for a custom domain.
- Hosted startup refuses SQLite to prevent accidental data loss on an ephemeral filesystem. It also refuses HTTP origins or insecure session cookies.
- Small database connection pool with health checks and connection recycling.
- GitHub Actions includes SQLite and PostgreSQL 16 jobs. The PostgreSQL job uses a disposable, dedicated test database; it has not been executed locally yet.

## Publish after account connection

1. Create the source repository from the StudyLens folder. Exclude `.env`, `data/`, virtual environments and caches. Do not upload personal lecture files.
2. Select the Neon **Free** plan and create a PostgreSQL project for StudyLens. Do not enable a paid upgrade or billing resource.
3. Create a separate disposable Neon test branch/database and run the suite there using `TEST_DATABASE_URL`, with a database name beginning `studylens_test`. Never run the destructive tests against the live app database.
4. Deploy the repository as a Render Blueprint using `render.yaml`, and supply the production DATABASE_URL through its private environment settings.
5. Keep the **Free** service plan. If a provider requires payment or a card, stop and review the requirement with the account owner.
6. Wait for a successful build and deployment. Verify `/api/health` returns database `ok`, then perform no-signup entry, two-visitor isolation, upload, question-answering and quiz/progress checks against the actual hosted HTTPS URL.
7. Confirm the URL survives a service restart, then use that verified URL on the CV. Update screenshots and the README with the real deployment URL; do not use an invented or pending URL.

Tables are initialized from the existing first-release SQLAlchemy models on startup. Future schema changes require versioned migrations; create_all is not a schema-upgrade mechanism.

## Local validation

```bash
python -m pytest -q
```

Latest local result: **36 cases passed**, including seven cloud-configuration cases. PostgreSQL CI and real hosted runtime validation remain pending account connection and deployment.

## Sources

- [FastAPI on Render](https://render.com/docs/deploy-fastapi)
- [Render free service behavior and limitations](https://render.com/docs/free)
- [Render environment variables](https://render.com/docs/environment-variables)
- [Neon Free plan](https://neon.com/docs/introduction/free-tier)

## بالعربية

الإعداد جاهز لنشر الباك إند نفسه على استضافة مستقلة عن جهازك، مع PostgreSQL لحفظ البيانات. لم يتم إنشاء الرابط الثابت بعد؛ يلزم تفعيل حسابات Render وNeon وGitHub أولًا.

بعد النشر والتحقق سأستخدم الرابط الحقيقي للسيرة الذاتية. قد تتأخر أول زيارة للخطة المجانية بعد الخمول. لا توجد ترقية مدفوعة مفعلة في ملفات المشروع.
