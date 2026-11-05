# 📱 Chang Monitor App: Telegram Mini App

Bu **ikkinchi bot**. U Telegram ichida ochiladigan **ilova (Mini App)** bilan ishlaydi. Botda **"📱 Ilovani ochish"** tugmasi bor, uni bosganda chiroyli dashboard ochiladi.

Birinchi bot (`chang-bot`) o'zgarmaydi va alohida ishlayveradi.

## Ilovada nimalar bor
**🏠 Asosiy**
- Ob-havoga mos shahar rasmi, havo sifati o'lchagichi (PM10), PM2.5, chang, aerozol, namlik
- 🎯 **Bo'ron xavfi indeksi (0–100)**: shamol, tuproq quruqligi, namlik, yog'in va chang prognozidan hisoblanadi, 3 kunlik ko'rinishi bilan
- ⏰ **Eng toza soatlar**: tashqariga chiqish uchun eng yaxshi vaqt; yugurish, sayr, bola bilan sayr va deraza ochish uchun "mumkin / ehtiyot / tavsiya etilmaydi"
- 🚬 **"Bugun qancha chang yutdingiz?"**: PM2.5 sigaret ekvivalentida (Berkeley Earth hisobi)
- 🧪 **To'liq havo sifati**: AQI (AQSH), ozon, NO₂, SO₂, CO, UV indeksi
- 📸 **Bo'ron rasmlari**: yaqin atrofdagi rasmlar va ilovadan rasm yuborish
- Ob-havo, shamol kompasi, 24 soatlik grafik, ogohlantirishlar

**📈 Prognoz**: 3 kunlik kartochkalar (bo'ron xavfi bilan), 72 soatlik chang va shamol grafiklari

**🗺 Xarita**
- 🏙 Shaharlar: 14 shahar chang darajasi rangida va 📸 bo'ron rasmlari
- 🌪 **Chang buluti**: 3 kunlik chang harakati animatsiyasi va shamol strelkalari (▶ tugmasi)

**📊 Statistika**
- 🏆 Shaharlar reytingi (eng toza → eng changli)
- 📅 30/90 kunlik chang tarixi: o'rtacha, changli kunlar, JSST me'yoridan oshgan kunlar, eng changli kun, taqvim va grafik
- 🌊 Orol dengizi fojiasi: yillar bo'yicha interaktiv sxema

**⚙️ Sozlamalar**
- Til: o'zbekcha (asosiy), ruscha, inglizcha
- 👤 **Shaxsiy profil**: astma/allergiya, homilador, keksa, bolali ota-ona, sportchi. Maslahatlar, faollik chegaralari va ogohlantirishlar moslashadi (sezgir profilda bot PM10 150 dan ogohlantiradi)
- Bo'ron ogohlantirishlari va kunlik hisobot, sog'liq maslahatlari

🌓 Telegram mavzusiga moslashadi. 🔐 Sozlamalar va rasm yuborish Telegram imzosi (initData) bilan himoyalangan.

## Bo'ron rasmlari va admin
Railway'da `ADMIN_ID` o'zgaruvchisiga o'z Telegram ID raqamingizni yozing (@userinfobot orqali bilib olasiz). Shunda:
- foydalanuvchi ilovadan yuborgan rasm sizga ✅ / ❌ tugmalari bilan keladi;
- tasdiqlasangiz, rasm ilovada ko'rinadi va 100 km radiusdagi obunachilarga yuboriladi;
- `/stat` buyrug'i statistikani ko'rsatadi.

`ADMIN_ID` bo'lmasa, rasmlar darhol ilovada ko'rinadi, lekin hech kimga avtomatik yuborilmaydi.

## Fayllar
| Fayl | Vazifasi |
|---|---|
| `app.py` | Veb-server (ilova va API) hamda bot |
| `webapp/index.html`, `app.css`, `app.js` | Ilovaning ko'rinishi va mantiqi |
| `webapp/i18n.js` | Ilova matnlari (uz / ru / en) |
| `texts.py` | Bot matnlari, shaharlar, darajalar, maslahatlar |
| `api.py` | Open-Meteo'dan ma'lumot olish |
| `scene.py` | Ob-havoga mos shahar rasmlari |
| `db.py` | Foydalanuvchi sozlamalari va bo'ron rasmlari (SQLite) |
| `risk.py` | Bo'ron xavfi indeksi |
| `mock_data.py` | Faqat sinov uchun soxta ma'lumot (`MOCK_DATA=1`) |

---

# Railway'ga joylash (10 daqiqa)

## 1. Yangi xizmat qo'shish
1. Railway'da **birinchi bot turgan loyihani** oching.
2. Yuqori o'ngdagi **+ Add** (yoki **+ New**) → **GitHub Repo** → `chang-app` ni tanlang.
3. Yangi kartochka paydo bo'ladi. Bu ikkinchi bot.

## 2. Tokenni kiritish
1. Yangi kartochkani bosing → **Variables** → **+ New Variable**:
   - `BOT_TOKEN` = **ikkinchi** botning tokeni (birinchisiniki emas!)
2. Railway `.env.example` dan taklif qilgan boshqa qatorlarni olib tashlang yoki bo'sh qoldiring.

## 3. Internet manzili (domen) yaratish
1. Shu kartochkada **Settings** → **Networking** → **Generate Domain** ni bosing.
2. Port so'ralsa, **8080** deb yozing.
3. `chang-app-production-xxxx.up.railway.app` ko'rinishidagi manzil paydo bo'ladi.
   Bot bu manzilni o'zi aniqlaydi, uni hech qayerga yozish shart emas.

## 4. Tekshirish
1. **Deployments** → **View logs**. Quyidagi yozuvlar chiqishi kerak:
   - `Veb-server 8080-portda ishga tushdi`
   - `Ilova manzili: https://...`
   - `Bot ishga tushdi`
2. Telegramda ikkinchi botingizni oching → **/start** → **📱 Ilovani ochish**. 🎉
3. Chap pastda **Ilova** menyu tugmasi ham paydo bo'ladi.

## 5. (Ixtiyoriy) Sozlamalarni saqlash uchun Volume
Volume'siz har yangilanishda foydalanuvchilar sozlamalari o'chib ketadi.
1. Kartochka ustida o'ng tugma → **Attach Volume** → mount path: `/data`
2. **Variables**: `DB_PATH` = `/data/chang_app.db`

## (Ixtiyoriy) Ilovaga to'g'ridan-to'g'ri havola
@BotFather → `/newapp` → ikkinchi botni tanlang → nom, tavsif, rasm (640×360) → URL'ga Railway manzilini yozing → qisqa nom (masalan `dashboard`).
Shunda `t.me/BOTINGIZ/dashboard` havolasi ilovani darhol ochadi.

---

## O'z kompyuteringizda sinash
```
pip install -r requirements.txt
MOCK_DATA=1 python app.py
```
Brauzerda http://localhost:8080 ni oching. `MOCK_DATA=1` internetsiz soxta ma'lumot bilan ishlaydi. Haqiqiy ma'lumot uchun uni olib tashlang.

## Muammolar bo'lsa
| Muammo | Yechim |
|---|---|
| Botda "Ilova manzili hali sozlanmagan" | 3-qadam: **Generate Domain** qiling, keyin **Redeploy** |
| Ilova ochiladi, lekin "Ma'lumot yuklanmadi" | Railway loglarini tekshiring |
| `Conflict: terminated by other getUpdates` | Bitta token ikki joyda ishlayapti. Ikkinchi xizmatga **ikkinchi** bot tokeni yozilganini tekshiring |
| Bildirishnomalar kelmayapti | Ilovada **Sozlamalar** → ogohlantirishlarni yoqing. Ilova Telegram ichida ochilgan bo'lishi kerak |
