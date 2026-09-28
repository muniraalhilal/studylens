# No-signup demo and temporary sharing

Select **Try the demo — no sign-up / جرّبي الديمو بدون تسجيل** on the entry screen. The backend creates an independent 24-hour session and loads both sample lectures. Each visitor has separate files, quiz results and progress. There is no shared demo password. Local personal registration remains optional.

## Create a temporary HTTPS link

Install the official [Cloudflare quick tunnel executable](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/) and run from the project folder with the virtual environment active:

```bash
python scripts/share_demo.py
# Or specify the installed executable:
python scripts/share_demo.py --cloudflared /absolute/path/to/cloudflared
```

The helper starts a separate service on 127.0.0.1:8001 using **data/public-demo.db**. It configures the exact generated HTTPS origin, Secure cookies and public demo-only mode. It verifies the public database health endpoint before printing SHARE_URL. It never exposes the personal service on port 8000 or its database.

Public mode hides account forms and disables registration/password login at the API level. All study features still use the real FastAPI backend. Uploaded demo files are processed on the host computer; use samples or non-sensitive coursework.

**This is a temporary preview, not permanent hosting.** Keep the computer awake, internet connected and both processes running. Ctrl+C stops the helper and its processes. The URL changes on restart and availability is not guaranteed. Quick tunnels require no account, API key or subscription.

Guest limits per session: 10 materials, 30 quiz attempts, 100 card reviews. Authentication limit: 15 requests per minute per IP. Other mutations: 120 per minute. These are small-demo safeguards, not distributed production protections.

TRUST_CLOUDFLARE must be enabled only behind a local trusted cloudflared process. The helper disables Uvicorn proxy-header interpretation and binds the backend to loopback.

## بالعربية

زر الديمو يدخل الزائر مباشرة بدون بريد أو كلمة مرور، ويجهّز الملفات التجريبية تلقائيًا. لكل زائر جلسة مستقلة تنتهي بعد ٢٤ ساعة؛ تنظّف البيانات المنتهية عند بدء السيرفر أو إنشاء جلسة تجريبية جديدة.

رابط المشاركة مؤقت ويحتاج بقاء الجهاز مستيقظًا والبرنامج والإنترنت شغّالين. يتغير الرابط عند إعادة تشغيل المشاركة. قاعدة بيانات المشاركة منفصلة عن الحسابات والملفات المحلية.

[Backend verification report](BACKEND-VALIDATION.md)
