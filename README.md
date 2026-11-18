# نَبْض | مركز قيادة المشاريع

بوت تيليجرام عربي يقرأ حالة مستودعات GitHub ويحفظ المشاريع وسجل عمليات إضافتها وحذفها. يقدّم FastAPI نقطة الجاهزية `/healthz`.

## تشغيل محلي

يتطلب Python 3.12. أنشئ بوتًا في BotFather، ثم ضع `BOT_TOKEN` و`TELEGRAM_ADMIN_IDS` في ملف `.env` محلي. تحتاج الأوامر الإدارية إلى معرّف مشرف مُسجّل ومحادثة خاصة.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python -m alembic upgrade head
python -m pytest -q
python -m app.main
```

| الأمر | الوظيفة |
|---|---|
| `/start`، `/help`، `/id` | القائمة والمساعدة ومعرّف تيليجرام |
| `/addproject owner/repo` | التحقق من المستودع وتسجيله |
| `/projects`، `/removeproject` | قائمة المشروع واختيار الحذف المؤكد |
| `/status owner/repo` | الفرع وآخر commit وآخر تشغيل GitHub Actions |
| `/settings` | عرض إعدادات الوصول ونمط اتصال GitHub |

استخدم توكن GitHub اختياريًا بصلاحيات قراءة للمستودعات المقصودة. راجع [النشر](docs/DEPLOYMENT_STATUS.md) و[نتائج الاختبار](docs/TEST_REPORT.md).

```bash
python scripts/build_handoff.py
python scripts/verify_handoff.py
```
