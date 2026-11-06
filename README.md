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

**📈 Prognoz**: 7 kunlik prognoz (harorat, chang, bo'ron xavfi, yog'in, shamol), 7 kunlik chang va shamol grafiklari. Chang prognozi taxminan 5 kunga beriladi

**🗺 Xarita**
- 🏙 Shaharlar: 14 shahar chang darajasi rangida va 📸 bo'ron rasmlari
- 🌪 **Chang buluti**: 3 kunlik chang harakati animatsiyasi va shamol strelkalari (▶ tugmasi)

**📊 Statistika**
- 🏆 Shaharlar reytingi (eng toza → eng changli)
- 📅 30/90 kunlik chang tarixi: o'rtacha, changli kunlar, JSST me'yoridan oshgan kunlar, eng changli kun, taqvim va grafik
- 🌊 Orol dengizi fojiasi: yillar bo'yicha interaktiv sxema

**⚙️ Sozlamalar**
- 🎨 Mavzu: Avto (Telegram), ☀️ Yorug' yoki 🌙 Qorong'i
- Til: o'zbekcha (asosiy), ruscha, inglizcha
- 👤 **Shaxsiy profil**: astma/allergiya, homilador, keksa, bolali ota-ona, sportchi. Maslahatlar, faollik chegaralari va ogohlantirishlar moslashadi (sezgir profilda bot PM10 150 dan ogohlantiradi)
- Bo'ron ogohlantirishlari va kunlik hisobot, sog'liq maslahatlari

🎨 Dizayn O'zbekiston tabiatidan ilhomlangan: firuza (Samarqand koshinlari), qum (Qizilqum), saksovul ranglari, milliy girih naqshi va hudud bo'yicha fon (Orolbo'yi, Qizilqum, Zarafshon vodiysi, Farg'ona vodiysi, Mirzacho'l, Poytaxt). 🔐 Sozlamalar va rasm yuborish Telegram imzosi (initData) bilan himoyalangan.

## 🩺 Sog'liq bo'limi
Havo va ob-havo ma'lumotlari sog'liq bilan bog'lanadi. **Ilova tashxis qo'ymaydi va dori tavsiya qilmaydi**, u faqat taxminiy xavf darajasini va umumiy ehtiyot choralarini ko'rsatadi. Har sahifada tibbiy eslatma bor.

1. **Sog'liq xavfi (bugun / ertaga)**, 6 toifa bo'yicha: 🫁 nafas yo'llari (PM2.5, PM10, ozon), ❤️ yurak (PM2.5, haddan tashqari issiq yoki sovuq), 👁 ko'z va allergiya (chang, shamol), 🌡 issiqlik, 🤧 shamollash va gripp (sovuq, keskin sovish, namlik, mavsum), ☀️ UV. Shaxsiy profilga moslashadi: masalan, astma, homiladorlik yoki keksalikda chegaralar 30% pastroq bo'ladi.
2. **Mavsumiy xavf taqvimi**: 2015 yildan buyongi arxiv asosida har bir shahar uchun 12 oy. 🌪 chang bo'ronlari, 🔥 issiqlik, 🤧 shamollash va ☀️ UV mavsumlari ko'rsatiladi.
3. **Sog'liq kundaligi** (faqat rozilik bilan): har kungi simptomlar va og'irligi. Shu kungi havo ma'lumoti avtomatik yoziladi. Ilova simptomlarni chang va harorat bilan solishtiradi (*"Yo'tal ko'pincha chang yuqori kunlarda bo'lgan"*). Barcha yozuvlar bir tugma bilan o'chiriladi.
4. **Bot eslatmalari**: soat 20:00 da ertangi muhim xavf haqida (profilga qarab), oy boshida yangi mavsum haqida, soat 21:00 da kundalikka yozish eslatmasi.
5. **Shifokor uchun PDF hisobot**: so'nggi 30 kunlik simptomlar, havo grafigi va kuzatuvlar. Bot uni Telegram chatga yuboradi.
6. **Ochiq tadqiqot ma'lumoti**: `/docs` sahifasi. Arxiv va **anonim** simptomlar statistikasi (`/api/research/symptoms.csv`) ochiq. Faqat kamida 5 kishi yozgan shahar-kunlar chiqariladi, ism, ID va izohlar hech qachon berilmaydi.

## 🗄 Ochiq ma'lumotlar arxivi
Ilova **14 ta shahar** bo'yicha har kungi ma'lumotlarni avtomatik saqlaydi:
PM10, PM2.5, chang (o'rtacha va maksimum), aerozol (AOD), AQI, ozon, NO₂, SO₂, CO, UV, harorat (min/maks), namlik, shamol, shiddat, yog'in, bo'ron xavfi indeksi va haqiqiy datchik o'lchovlari (`WAQI_TOKEN` bo'lsa, har soat yoziladi).

- Birinchi ishga tushishda **o'tgan 92 kun** avtomatik to'ldiriladi. Keyin arxiv har kuni o'sib boradi (soat 00:07 va 06:07 da yangilanadi).
- Ilovada: **Statistika** bo'limida 30 kun / 90 kun / 1 yil / hammasi, turli ko'rsatkichlar grafigi, istalgan kunning to'liq tafsiloti.

**Arxiv ochiq, istalgan odam yuklab olishi mumkin:**
| Usul | Qanday |
|---|---|
| Ilovada | **Statistika** → **⬇️ Yuklab olish**. Bot faylni Telegram chatga yuboradi |
| Botda | `/arxiv` buyrug'i, keyin shahar yoki "Barcha shaharlar" tanlanadi |
| Havola (CSV) | `https://SIZNING-DOMEN/api/archive.csv?key=nukus&days=365&lang=uz` |
| Havola (JSON) | `https://SIZNING-DOMEN/api/archive?key=all&days=0` |

`key`: shahar (`toshkent`, `nukus`, `samarqand`, …) yoki `all`. `days`: 30, 90, 365 yoki `0` (butun arxiv). `lang`: `uz`/`ru` (Excel uchun `;` va o'nlik vergul) yoki `en`.

### 📜 2015 yildan boshlab tarixiy ma'lumot
Server ishga tushganda arxiv fonda **2015 yildan** to'ldiriladi (to'xtasa, qolgan joyidan davom etadi):

| Davr | Ma'lumot | Manba | Kalit |
|---|---|---|---|
| 2015 → hozir | Harorat, namlik, shamol, yog'in, tuproq namligi | Open-Meteo ERA5 arxivi | kerak emas |
| 2022 → hozir | PM10, PM2.5, chang, gazlar, AQI, UV | Open-Meteo / CAMS | kerak emas |
| 2015 → 2021 | PM10, PM2.5, aerozol (AOD), chang aerozoli | Copernicus CAMS reanalizi (EAC4) | **`ADS_KEY`** (bepul) |

**2015–2021 yillar chang ma'lumoti uchun Copernicus kalitini olish (5 daqiqa):**
1. https://ads.atmosphere.copernicus.eu saytida **Register** orqali bepul ro'yxatdan o'ting va emailni tasdiqlang.
2. Saytga kirib, **CAMS global reanalysis (EAC4)** sahifasini oching → **Download** bo'limi pastidagi **Terms of use** (litsenziya) ni qabul qiling.
3. O'z profilingizga kiring (yuqori o'ng burchakdagi ism) va **API Token** (Personal Access Token) ni nusxalang.
4. Railway → **chang-app** → **Variables** → `ADS_KEY` = token.
5. Har bir yil Copernicus navbatida bir necha daqiqadan bir necha soatgacha tayyorlanadi. Jarayon ilovada (**Statistika → Arxiv qamrovi**) ko'rinadi.

Ilovada **Statistika → Yillar**: har yilgi o'rtacha chang va changli kunlar jadvali, 2015 yildan buyongi oylik grafik, istalgan yilning taqvimi. Yuklab olishda **boshlanish va tugash yilini** tanlash mumkin. Havola orqali: `/api/archive.csv?key=nukus&from=2015&to=2020`.

⚠️ **Arxiv yo'qolmasligi uchun Volume shart!** Volume'siz Railway har yangilanishda bazani o'chiradi. Model ma'lumotining so'nggi 92 kuni qayta tiklanadi, lekin undan eski kunlar va datchik o'lchovlari yo'qoladi:
1. **chang-app** kartochkasi ustida o'ng tugma → **Attach Volume** → mount path: `/data`
2. **Variables**: `DB_PATH` = `/data/chang_app.db`

## 📡 Haqiqiy datchiklar (ixtiyoriy, bepul)
Ilova asosan sun'iy yo'ldosh modeli (Copernicus CAMS) ma'lumotini ko'rsatadi. Haqiqiy o'lchash stansiyalari ma'lumotini ham qo'shish mumkin (Toshkent va boshqa shaharlardagi datchiklar):
1. https://aqicn.org/data-platform/token/ sahifasini oching, email kiriting va emailga kelgan **token**ni oling.
2. Railway → **chang-app** → **Variables** → `WAQI_TOKEN` = token.
3. Ilovada **📡 Haqiqiy datchik** kartasi va xaritada **📡 Datchiklar** rejimi paydo bo'ladi.

Agar yaqin atrofda (60 km ichida) datchik bo'lmasa, ilova buni yozib, model ma'lumotini ko'rsataveradi.

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
| `sensors.py` | Haqiqiy datchiklar (aqicn.org) |
| `archive.py` | Har kungi ma'lumotlar arxivi va CSV eksport |
| `history.py` | 2015 yildan tarixiy import (ERA5, Open-Meteo, CAMS EAC4) |
| `health.py` | Sog'liq xavfi, mavsumlar, kundalik tahlili, PDF hisobot |
| `webapp/docs.html` | Tadqiqotchilar uchun ochiq ma'lumotlar hujjati (`/docs`) |
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
