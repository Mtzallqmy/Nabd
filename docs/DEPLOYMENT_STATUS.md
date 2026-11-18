# النشر

## Docker Compose

بعد إعداد `.env`، اترك `DATABASE_URL` فارغًا لاستخدام SQLite داخل وحدة تخزين Compose، أو اضبط رابط PostgreSQL.

```bash
docker compose build
docker compose run --rm nabd python -m alembic upgrade head
docker compose up -d
curl -fsS http://localhost:8080/healthz
```

## Railway وNeon

1. اربط خدمة Railway بالمستودع بعد اعتماد طلب الدمج. يستخدم المشروع Dockerfile و`railway.toml`.
2. اضبط `BOT_TOKEN` و`TELEGRAM_ADMIN_IDS` و`DATABASE_URL` في Railway Variables. اضبط `GITHUB_TOKEN` اختياريًا للقراءة فقط و`LOG_LEVEL` عند الحاجة. يمكن للمنصة توفير `PORT`.
3. استخدم رابط PostgreSQL المجمّع للتطبيق. طبّق `python -m alembic upgrade head` مرة واحدة من مهمة صيانة آمنة على الرابط المباشر عبر `MIGRATION_DATABASE_URL`. اجعل الدور المستخدم لتشغيل البوت محدودًا بصلاحيات التطبيق.
4. تحقق من `/healthz`، ثم نفّذ `/start` و`/status` وجرّب التسجيل والاسترجاع من محادثة مشرف خاصة. `200` يعني أن اتصال قاعدة البيانات ناجح وأن طلب Telegram `getUpdates` اكتمل مؤخرًا. تحقق من الأوامر بإرسال رسائل فعلية.
5. خصّص نسخة واحدة لكل توكن. عند استبدال نشر قائم بنفس التوكن، أوقف العملية القديمة قبل تشغيل الجديدة لأن فحص الجاهزية ينتظر أول استجابة polling. توقّع انقطاعًا قصيرًا أثناء الاستبدال.

## ترحيل قاعدة سابقة

افحص نسخة من القاعدة وحدد مراجعة Alembic قبل الترحيل. خذ نسخة احتياطية وافحص تكرار `lower(owner), lower(repository)` قبل الترحيل. إذا كانت نسخة Carbon أنشأت الجداول بواسطة `create_all`، طابقها مع مراجعة `0001_create_projects` أولًا. بعد تطابق المخطط فقط، يمكن تسجيل المراجعة باستخدام `alembic stamp 0001_create_projects` قبل الترقية. استخدم استعادة النسخة الاحتياطية عند التراجع في الإنتاج. حذف سجل النشاط أو تقليص نوع معرّف المستخدم قد يفقد بيانات.

حالة التسليم تشمل تجهيز إعدادات النشر. تشغيل Railway والتحقق الحي من Telegram وNeon يتطلبان خدمة وبيانات اعتماد للمشروع.
