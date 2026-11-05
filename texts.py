"""Shaharlar, darajalar va barcha matnlar (o'zbek va rus tillarida).

Bot gaplarini o'zgartirish uchun shu faylni tahrirlang.
"""

LANGS = ("uz", "ru", "en")

# kalit: (o'zbekcha nom, ruscha nom, kenglik, uzunlik)
CITIES = {
    "toshkent":  ("Toshkent",  "Ташкент",   41.311, 69.240),
    "nukus":     ("Nukus",     "Нукус",     42.460, 59.603),
    "moynoq":    ("Mo'ynoq",   "Муйнак",    43.768, 59.022),
    "urganch":   ("Urganch",   "Ургенч",    41.550, 60.631),
    "buxoro":    ("Buxoro",    "Бухара",    39.768, 64.421),
    "navoiy":    ("Navoiy",    "Навои",     40.084, 65.379),
    "samarqand": ("Samarqand", "Самарканд", 39.654, 66.959),
    "qarshi":    ("Qarshi",    "Карши",     38.861, 65.789),
    "termiz":    ("Termiz",    "Термез",    37.224, 67.278),
    "jizzax":    ("Jizzax",    "Джизак",    40.116, 67.842),
    "guliston":  ("Guliston",  "Гулистан",  40.490, 68.784),
    "namangan":  ("Namangan",  "Наманган",  40.998, 71.672),
    "andijon":   ("Andijon",   "Андижан",   40.783, 72.344),
    "fargona":   ("Farg'ona",  "Фергана",   40.384, 71.784),
}

ALERT_PM10 = 250   # shu qiymatdan oshsa ogohlantirish yuboriladi
ALERT_DUST = 200

# PM10 (µg/m³) chegaralari va ranglari (grafik uchun ham ishlatiladi)
LEVEL_LIMITS = [50, 100, 250, 430, 10**9]
LEVEL_EMOJI = ["🟢", "🟡", "🟠", "🔴", "🟣"]
LEVEL_COLORS = ["#4caf50", "#fbc02d", "#fb8c00", "#e53935", "#8e24aa"]

LEVELS = {
    "uz": [
        ("Yaxshi", "Havo toza. Bemalol sayr qilishingiz mumkin."),
        ("O'rtacha", "Sezgir odamlar (astma, allergiya) ehtiyot bo'lsin."),
        ("Yomon", "Uzoq vaqt tashqarida bo'lmang, sport bilan uyda shug'ullaning."),
        ("Juda yomon", "Niqob taqing (N95/FFP2), derazalarni yoping."),
        ("Xavfli", "Qum-chang bo'roni! Zarurat bo'lmasa tashqariga chiqmang."),
    ],
    "ru": [
        ("Хорошо", "Воздух чистый. Можно спокойно гулять."),
        ("Умеренно", "Чувствительным людям (астма, аллергия) стоит быть осторожнее."),
        ("Плохо", "Не находитесь долго на улице, занимайтесь спортом дома."),
        ("Очень плохо", "Наденьте маску (N95/FFP2), закройте окна."),
        ("Опасно", "Пыльная буря! Без необходимости не выходите на улицу."),
    ],
}

WEEKDAYS = {
    "uz": ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"],
    "ru": ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"],
}

T = {
    "uz": {
        # tugmalar
        "btn_now": "🌫 Hozirgi holat",
        "btn_fc": "📈 Prognoz",
        "btn_chart": "📊 Grafik",
        "btn_city": "🏙 Shahar",
        "btn_loc": "📍 Lokatsiya",
        "btn_report": "📸 Bo'ron xabari",
        "btn_feed": "👀 Xabarlar",
        "btn_sub": "🔔 Obuna",
        "btn_tips": "💊 Maslahatlar",
        "btn_info": "📚 Ma'lumot",
        "btn_lang": "🌐 Til / Язык / Language",
        "btn_refresh": "🔄 Yangilash",
        # umumiy
        "start": (
            "Assalomu alaykum, {name}! 👋\n\n"
            "Men <b>Chang Monitor</b> botiman 🌪\n"
            "O'zbekiston shaharlari bo'yicha <b>chang va qum bo'ronlari</b> haqida "
            "ma'lumot, prognoz, grafik va ogohlantirishlar beraman.\n\n"
            "📸 Bo'ronni o'z ko'zingiz bilan ko'rsangiz, rasmini yuboring: "
            "boshqalarni ogohlantiramiz!\n\n"
            "Boshlash uchun shahringizni tanlang yoki 📍 lokatsiya yuboring 👇"
        ),
        "help": (
            "<b>Buyruqlar:</b>\n"
            "/havo: hozirgi chang holati\n"
            "/prognoz: 3 kunlik prognoz\n"
            "/grafik: chang grafigi\n"
            "/shahar: shaharni tanlash\n"
            "/xabar: bo'ron rasmini yuborish\n"
            "/xabarlar: yaqin atrofdagi bo'ron xabarlari\n"
            "/obuna: ogohlantirish va kunlik hisobot\n"
            "/maslahat: sog'liq bo'yicha maslahatlar\n"
            "/malumot: chang bo'ronlari haqida\n"
            "/til: tilni o'zgartirish\n"
            "/stop: barcha ma'lumotlarimni o'chirish\n\n"
            "Ma'lumot manbasi: Open-Meteo / Copernicus CAMS."
        ),
        "choose_lang": "🌐 Tilni tanlang / Выберите язык / Choose language:",
        "lang_set": "✅ Til: O'zbekcha",
        "choose_city": "🏙 Shaharni tanlang:",
        "city_set": "✅ Shahar: <b>{name}</b>",
        "city_selected": "{name} tanlandi",
        "my_location": "Joylashuvim",
        "loc_saved": "✅ Joylashuvingiz saqlandi.",
        "need_city": "Avval shaharni tanlang 👇",
        "api_error": "😔 Ma'lumot olishda xatolik. Birozdan keyin qayta urinib ko'ring.",
        "unknown": "Tushunmadim 🤔 Quyidagi tugmalardan foydalaning yoki /help",
        "updating": "Yangilanmoqda...",
        "stop_done": "🗑 Ma'lumotlaringiz o'chirildi, xabarlar yuborilmaydi. Qaytish uchun /start",
        "not_set": "tanlanmagan",
        "enabled": "Yoqildi ✅",
        "disabled": "O'chirildi ❌",
        # hozirgi holat
        "dust": "Chang",
        "aod": "Aerozol (AOD)",
        "warn24": ("⚠️ <b>Diqqat!</b> Keyingi 24 soatda chang kuchayishi kutilmoqda: "
                   "soat {time} atrofida PM10 ≈ {pm10} µg/m³"),
        "morning": "☀️ <b>Xayrli tong!</b>\n\n",
        # prognoz
        "fc_title": "📈 <b>{place}: 3 kunlik chang va ob-havo prognozi</b>\n",
        "fc_line": "PM10 maks: <b>{pm10}</b> (soat {peak})  •  Chang: {dust}  •  PM2.5: {pm25}\n",
        "fc_note": "<i>Chang µg/m³ da, kunning eng yuqori ko'rsatkichi. Shamol: o'rtacha tezlik va shiddat.</i>",
        # grafik
        "chart_title": "{place}: chang prognozi (72 soat)",
        "chart_title_wind": "{place}: chang va shamol prognozi (72 soat)",
        "chart_dust": "Chang",
        "chart_y": "µg/m³",
        "chart_now": "hozir",
        "chart_caption": ("📊 <b>{place}</b>: 3 kunlik chang va shamol grafigi\n"
                          "Yuqorida chang. Rangli zonalar: 🟢 yaxshi → 🟣 xavfli\n"
                          "Pastda shamol: tezligi, shiddati va yo'nalishi (strelkalar shamol "
                          "qayoqqa esayotganini ko'rsatadi)"),
        "chart_caption_nowind": "📊 <b>{place}</b>: 3 kunlik chang grafigi\nRangli zonalar: 🟢 yaxshi → 🟣 xavfli",
        "chart_wind": "Shamol tezligi",
        "chart_gusts": "Shiddati",
        "chart_wind_y": "m/s",
        "chart_strong": "kuchli shamol",
        "chart_wait": "📊 Grafik tayyorlanmoqda...",
        # obuna
        "sub_text": (
            "🔔 <b>Obuna sozlamalari</b>\n📍 Joy: <b>{place}</b>\n\n"
            "• <b>Ogohlantirish</b>: keyingi 24 soatda PM10 {pm10} dan yoki chang "
            "{dust} µg/m³ dan oshsa xabar beraman. Yaqin atrofdan bo'ron rasmlari "
            "kelsa, ularni ham yuboraman.\n"
            "• <b>Kunlik hisobot</b>: har kuni soat {hour:02d}:00 da qisqa ma'lumot."
        ),
        "sub_alerts": "Bo'ron ogohlantirishlari",
        "sub_daily": "Kunlik hisobot ({hour:02d}:00)",
        # ogohlantirish
        "alert": (
            "🚨 <b>CHANG BO'RONI OGOHLANTIRISHI</b>\n\n"
            "📍 {place}\n"
            "🕐 {when}, soat {hour} atrofida\n"
            "{emoji} PM10 ≈ <b>{pm10}</b> µg/m³ ({level})\n"
            "🏜 Chang ≈ <b>{dust}</b> µg/m³\n\n"
            "💡 {advice}\n\nBatafsil: /maslahat"
        ),
        "today": "bugun",
        "tomorrow": "ertaga",
        # bo'ron xabarlari
        "report_prompt": (
            "📸 <b>Bo'ron xabarini yuborish</b>\n\n"
            "Chang yoki qum bo'ronini ko'rsangiz, <b>rasmini shu yerga yuboring</b>. "
            "Rasm ostiga izoh ham yozishingiz mumkin (masalan: \"Ko'rinish 100 m\").\n\n"
            "Xabaringiz <b>{place}</b> joyiga bog'lanadi. Boshqa joy bo'lsa, avval "
            "📍 lokatsiya yuboring."
        ),
        "report_pending": "🙏 Rahmat! Rasmingiz tekshiruvga yuborildi. Tasdiqlangach, yaqin atrofdagilar ko'radi.",
        "report_saved": "🙏 Rahmat! Xabaringiz saqlandi, yaqin atrofdagilar uni ko'ra oladi.",
        "report_limit": "⏳ Bir kunda ko'pi bilan {n} ta xabar yuborish mumkin. Ertaga yana urinib ko'ring.",
        "report_approved": "✅ Bo'ron xabaringiz tasdiqlandi va yaqin atrofdagilarga yuborildi. Rahmat!",
        "report_rejected": "❌ Bo'ron xabaringiz tasdiqlanmadi.",
        "report_nearby": "📸 <b>Yaqin atrofdan bo'ron xabari</b> ({km} km)\n📍 {place} • {time}",
        "feed_title": "👀 <b>So'nggi 24 soatdagi bo'ron xabarlari</b> ({km} km radiusda):",
        "feed_empty": "✅ So'nggi 24 soatda yaqin atrofingizdan bo'ron xabarlari kelmagan.",
        "feed_item": "📍 {place} • {time} • {km} km",
        # maslahat va ma'lumot
        "tips": (
            "💊 <b>Chang bo'ronida sog'likni saqlash</b>\n\n"
            "😷 <b>Niqob:</b> oddiy tibbiy niqob changdan yaxshi himoya qilmaydi, "
            "<b>N95 / FFP2</b> niqob taqing.\n"
            "🪟 <b>Uy:</b> deraza va eshiklarni yoping, tirqishlarni ho'l latta bilan bekiting. "
            "Havo tozalagich bo'lsa, yoqing.\n"
            "💧 <b>Suv:</b> ko'proq suv iching, burun va ko'zni toza suv bilan yuving.\n"
            "👓 <b>Ko'z:</b> ko'zoynak taqing, linza taqmaslikka harakat qiling.\n"
            "🏃 <b>Sport:</b> tashqarida yugurish va mashq qilishni to'xtating.\n"
            "🚗 <b>Mashina:</b> ko'rinish yomonlashadi. Tezlikni kamaytiring, "
            "konditsionerni ichki aylanish rejimiga qo'ying.\n\n"
            "👶👴 <b>Xavf guruhi:</b> bolalar, keksalar, homiladorlar, astma, yurak va o'pka "
            "kasalligi borlar uyda qolishi kerak.\n"
            "🚑 Nafas qisishi, ko'krak og'rig'i yoki kuchli yo'tal bo'lsa, <b>103</b> ga qo'ng'iroq qiling."
        ),
        "info": (
            "📚 <b>Chang va qum bo'ronlari haqida</b>\n\n"
            "🌪 <b>Chang bo'roni</b>: kuchli shamol quruq tuproq va qumni havoga ko'tarib, "
            "yuzlab kilometrga olib ketadi. Ko'rinish 1 km dan kam bo'lishi mumkin.\n\n"
            "🏜 <b>O'zbekistonda nega ko'p?</b>\n"
            "• Orol dengizi qurishi natijasida <b>Orolqum</b> cho'li paydo bo'ldi. U tuz va "
            "chang manbai.\n"
            "• Qizilqum va Qoraqum cho'llari yaqinligi.\n"
            "• Qurg'oqchilik va yashil maydonlarning kamayishi.\n\n"
            "🔬 <b>Ko'rsatkichlar:</b>\n"
            "• <b>PM10</b>: diametri 10 mikrondan kichik zarrachalar (chang, qum).\n"
            "• <b>PM2.5</b>: 2.5 mikrondan kichik zarrachalar. O'pkaga chuqur kiradi, eng xavflisi shu.\n"
            "• <b>Chang (dust)</b>: havodagi mineral chang miqdori.\n\n"
            "📏 JSST (WHO) tavsiyasi: PM10 sutkalik o'rtacha <b>45 µg/m³</b> dan, "
            "PM2.5 esa <b>15 µg/m³</b> dan oshmasligi kerak.\n\n"
            "🌳 <b>Yechim:</b> daraxt ekish va Orol tubida saksovul o'rmonlari barpo etish "
            "chang bo'ronlarini kamaytiradi."
        ),
    },
    "ru": {
        "btn_now": "🌫 Сейчас",
        "btn_fc": "📈 Прогноз",
        "btn_chart": "📊 График",
        "btn_city": "🏙 Город",
        "btn_loc": "📍 Геолокация",
        "btn_report": "📸 Сообщить о буре",
        "btn_feed": "👀 Сообщения",
        "btn_sub": "🔔 Подписка",
        "btn_tips": "💊 Советы",
        "btn_info": "📚 Информация",
        "btn_lang": "🌐 Til / Язык / Language",
        "btn_refresh": "🔄 Обновить",
        "start": (
            "Здравствуйте, {name}! 👋\n\n"
            "Я бот <b>Chang Monitor</b> 🌪\n"
            "Показываю уровень <b>пыли и пыльных бурь</b> в городах Узбекистана: "
            "текущие данные, прогноз, графики и предупреждения.\n\n"
            "📸 Видите бурю своими глазами? Пришлите фото, и мы предупредим других!\n\n"
            "Для начала выберите город или отправьте 📍 геолокацию 👇"
        ),
        "help": (
            "<b>Команды:</b>\n"
            "/havo: текущий уровень пыли\n"
            "/prognoz: прогноз на 3 дня\n"
            "/grafik: график пыли\n"
            "/shahar: выбрать город\n"
            "/xabar: отправить фото бури\n"
            "/xabarlar: сообщения о бурях поблизости\n"
            "/obuna: предупреждения и ежедневный отчёт\n"
            "/maslahat: советы для здоровья\n"
            "/malumot: о пыльных бурях\n"
            "/til: сменить язык\n"
            "/stop: удалить все мои данные\n\n"
            "Источник данных: Open-Meteo / Copernicus CAMS."
        ),
        "choose_lang": "🌐 Tilni tanlang / Выберите язык / Choose language:",
        "lang_set": "✅ Язык: Русский",
        "choose_city": "🏙 Выберите город:",
        "city_set": "✅ Город: <b>{name}</b>",
        "city_selected": "Выбран город {name}",
        "my_location": "Моё местоположение",
        "loc_saved": "✅ Ваше местоположение сохранено.",
        "need_city": "Сначала выберите город 👇",
        "api_error": "😔 Не удалось получить данные. Попробуйте чуть позже.",
        "unknown": "Не понял 🤔 Воспользуйтесь кнопками ниже или /help",
        "updating": "Обновляю...",
        "stop_done": "🗑 Ваши данные удалены, сообщения больше не придут. Чтобы вернуться: /start",
        "not_set": "не выбран",
        "enabled": "Включено ✅",
        "disabled": "Выключено ❌",
        "dust": "Пыль",
        "aod": "Аэрозоль (AOD)",
        "warn24": ("⚠️ <b>Внимание!</b> В ближайшие 24 часа ожидается усиление пыли: "
                   "около {time} PM10 ≈ {pm10} µg/m³"),
        "morning": "☀️ <b>Доброе утро!</b>\n\n",
        "fc_title": "📈 <b>{place}: прогноз пыли и погоды на 3 дня</b>\n",
        "fc_line": "PM10 макс: <b>{pm10}</b> (в {peak})  •  Пыль: {dust}  •  PM2.5: {pm25}\n",
        "fc_note": "<i>Пыль в µg/m³, максимум за день. Ветер: средняя скорость и порывы.</i>",
        "chart_title": "{place}: прогноз пыли (72 часа)",
        "chart_title_wind": "{place}: прогноз пыли и ветра (72 часа)",
        "chart_dust": "Пыль",
        "chart_y": "µg/m³",
        "chart_now": "сейчас",
        "chart_caption": ("📊 <b>{place}</b>: график пыли и ветра на 3 дня\n"
                          "Вверху пыль. Цветные зоны: 🟢 хорошо → 🟣 опасно\n"
                          "Внизу ветер: скорость, порывы и направление (стрелки показывают, "
                          "куда дует ветер)"),
        "chart_caption_nowind": "📊 <b>{place}</b>: график пыли на 3 дня\nЦветные зоны: 🟢 хорошо → 🟣 опасно",
        "chart_wind": "Скорость ветра",
        "chart_gusts": "Порывы",
        "chart_wind_y": "м/с",
        "chart_strong": "сильный ветер",
        "chart_wait": "📊 Готовлю график...",
        "sub_text": (
            "🔔 <b>Настройки подписки</b>\n📍 Место: <b>{place}</b>\n\n"
            "• <b>Предупреждения</b>: сообщу, если в ближайшие 24 часа PM10 превысит {pm10} "
            "или пыль превысит {dust} µg/m³. Также пришлю фото бурь, сделанные поблизости.\n"
            "• <b>Ежедневный отчёт</b>: каждый день в {hour:02d}:00 краткая сводка."
        ),
        "sub_alerts": "Предупреждения о бурях",
        "sub_daily": "Ежедневный отчёт ({hour:02d}:00)",
        "alert": (
            "🚨 <b>ПРЕДУПРЕЖДЕНИЕ О ПЫЛЬНОЙ БУРЕ</b>\n\n"
            "📍 {place}\n"
            "🕐 {when}, около {hour}\n"
            "{emoji} PM10 ≈ <b>{pm10}</b> µg/m³ ({level})\n"
            "🏜 Пыль ≈ <b>{dust}</b> µg/m³\n\n"
            "💡 {advice}\n\nПодробнее: /maslahat"
        ),
        "today": "сегодня",
        "tomorrow": "завтра",
        "report_prompt": (
            "📸 <b>Сообщить о буре</b>\n\n"
            "Если видите пыльную или песчаную бурю, <b>пришлите сюда фото</b>. "
            "Можно добавить подпись (например: \"Видимость 100 м\").\n\n"
            "Сообщение будет привязано к месту <b>{place}</b>. Если вы в другом месте, "
            "сначала отправьте 📍 геолокацию."
        ),
        "report_pending": "🙏 Спасибо! Фото отправлено на проверку. После одобрения его увидят люди поблизости.",
        "report_saved": "🙏 Спасибо! Сообщение сохранено, люди поблизости смогут его увидеть.",
        "report_limit": "⏳ Можно отправить не больше {n} сообщений в день. Попробуйте завтра.",
        "report_approved": "✅ Ваше сообщение о буре одобрено и отправлено людям поблизости. Спасибо!",
        "report_rejected": "❌ Ваше сообщение о буре не прошло проверку.",
        "report_nearby": "📸 <b>Сообщение о буре поблизости</b> ({km} км)\n📍 {place} • {time}",
        "feed_title": "👀 <b>Сообщения о бурях за последние 24 часа</b> (в радиусе {km} км):",
        "feed_empty": "✅ За последние 24 часа сообщений о бурях поблизости не было.",
        "feed_item": "📍 {place} • {time} • {km} км",
        "tips": (
            "💊 <b>Как беречь здоровье во время пыльной бури</b>\n\n"
            "😷 <b>Маска:</b> обычная медицинская маска плохо защищает от пыли. "
            "Используйте <b>N95 / FFP2</b>.\n"
            "🪟 <b>Дом:</b> закройте окна и двери, щели заложите влажной тканью. "
            "Если есть очиститель воздуха, включите его.\n"
            "💧 <b>Вода:</b> пейте больше воды, промывайте нос и глаза чистой водой.\n"
            "👓 <b>Глаза:</b> носите очки, по возможности не используйте линзы.\n"
            "🏃 <b>Спорт:</b> откажитесь от пробежек и тренировок на улице.\n"
            "🚗 <b>Авто:</b> видимость падает. Снизьте скорость, включите "
            "рециркуляцию воздуха.\n\n"
            "👶👴 <b>Группа риска:</b> дети, пожилые, беременные, люди с астмой, болезнями "
            "сердца и лёгких должны оставаться дома.\n"
            "🚑 При одышке, боли в груди или сильном кашле звоните <b>103</b>."
        ),
        "info": (
            "📚 <b>О пыльных и песчаных бурях</b>\n\n"
            "🌪 <b>Пыльная буря</b>: сильный ветер поднимает сухую почву и песок и "
            "переносит их на сотни километров. Видимость может падать ниже 1 км.\n\n"
            "🏜 <b>Почему их много в Узбекистане?</b>\n"
            "• Высыхание Аральского моря создало пустыню <b>Аралкум</b>, источник "
            "соли и пыли.\n"
            "• Близость пустынь Кызылкум и Каракум.\n"
            "• Засуха и сокращение зелёных зон.\n\n"
            "🔬 <b>Показатели:</b>\n"
            "• <b>PM10</b>: частицы меньше 10 микрон (пыль, песок).\n"
            "• <b>PM2.5</b>: частицы меньше 2.5 микрон. Глубоко проникают в лёгкие, самые опасные.\n"
            "• <b>Пыль (dust)</b>: количество минеральной пыли в воздухе.\n\n"
            "📏 Рекомендация ВОЗ: среднесуточный PM10 не выше <b>45 µg/m³</b>, "
            "PM2.5 не выше <b>15 µg/m³</b>.\n\n"
            "🌳 <b>Решение:</b> посадка деревьев и саксауловых лесов на дне Арала "
            "уменьшают пыльные бури."
        ),
    },
}

# ---------------- Ob-havo matnlari ----------------
WEATHER_T = {
    "uz": {
        "weather": "Ob-havo",
        "temp": "Harorat",
        "feels": "his qilinadi",
        "humidity": "Namlik",
        "precip": "Yog'in",
        "wind": "Shamol",
        "gusts": "shiddati",
        "ms": "m/s",
        "mm": "mm",
        "wind_warn": ("💨 <b>Kuchli shamol!</b> Shiddati {gust} m/s gacha ({when}, soat {hour} atrofida). "
                      "Shamol chang va qum ko'tarishi mumkin."),
        "fc_weather": ("🌡 {tmin}…{tmax}°C  {wemoji} {wdesc}\n"
                       "☔ {psum} mm ({pprob}%)  •  💨 {wmax} m/s, shiddati {gmax}  {arrow} {wdir}\n"),
        "no_weather": "<i>Ob-havo ma'lumotini olib bo'lmadi.</i>",
    },
    "ru": {
        "weather": "Погода",
        "temp": "Температура",
        "feels": "ощущается",
        "humidity": "Влажность",
        "precip": "Осадки",
        "wind": "Ветер",
        "gusts": "порывы",
        "ms": "м/с",
        "mm": "мм",
        "wind_warn": ("💨 <b>Сильный ветер!</b> Порывы до {gust} м/с ({when}, около {hour}). "
                      "Ветер может поднять пыль и песок."),
        "fc_weather": ("🌡 {tmin}…{tmax}°C  {wemoji} {wdesc}\n"
                       "☔ {psum} мм ({pprob}%)  •  💨 {wmax} м/с, порывы {gmax}  {arrow} {wdir}\n"),
        "no_weather": "<i>Не удалось получить данные о погоде.</i>",
    },
}
for _lang in ("uz", "ru"):
    T[_lang].update(WEATHER_T[_lang])

WIND_GUST_WARN = 15  # m/s: shundan kuchli shamol shiddati bo'lsa ogohlantiramiz

# WMO ob-havo kodlari: kod -> (emoji, o'zbekcha, ruscha)
WEATHER_CODES = {
    0: ("☀️", "Ochiq osmon", "Ясно"),
    1: ("🌤", "Asosan ochiq", "Преимущественно ясно"),
    2: ("⛅", "Qisman bulutli", "Переменная облачность"),
    3: ("☁️", "Bulutli", "Пасмурно"),
    45: ("🌫", "Tuman", "Туман"),
    48: ("🌫", "Qirovli tuman", "Изморозь, туман"),
    51: ("🌦", "Yengil shivalama", "Слабая морось"),
    53: ("🌦", "Shivalama", "Морось"),
    55: ("🌧", "Kuchli shivalama", "Сильная морось"),
    56: ("🌧", "Muzlovchi shivalama", "Ледяная морось"),
    57: ("🌧", "Muzlovchi shivalama", "Ледяная морось"),
    61: ("🌦", "Yengil yomg'ir", "Небольшой дождь"),
    63: ("🌧", "Yomg'ir", "Дождь"),
    65: ("🌧", "Kuchli yomg'ir", "Сильный дождь"),
    66: ("🌧", "Muzlovchi yomg'ir", "Ледяной дождь"),
    67: ("🌧", "Muzlovchi yomg'ir", "Ледяной дождь"),
    71: ("🌨", "Yengil qor", "Небольшой снег"),
    73: ("🌨", "Qor", "Снег"),
    75: ("❄️", "Kuchli qor", "Сильный снег"),
    77: ("🌨", "Qor donalari", "Снежная крупа"),
    80: ("🌦", "Jala", "Ливень"),
    81: ("🌧", "Kuchli jala", "Сильный ливень"),
    82: ("⛈", "Juda kuchli jala", "Очень сильный ливень"),
    85: ("🌨", "Qor yog'ishi", "Снегопад"),
    86: ("❄️", "Kuchli qor yog'ishi", "Сильный снегопад"),
    95: ("⛈", "Momaqaldiroq", "Гроза"),
    96: ("⛈", "Do'lli momaqaldiroq", "Гроза с градом"),
    99: ("⛈", "Kuchli do'lli momaqaldiroq", "Сильная гроза с градом"),
}

# Shamol qayerdan esayotgani (8 yo'nalish). Strelka shamol qayoqqa esayotganini ko'rsatadi.
WIND_DIRS = {
    "uz": ["Shimoliy", "Shimoli-sharqiy", "Sharqiy", "Janubi-sharqiy",
           "Janubiy", "Janubi-g'arbiy", "G'arbiy", "Shimoli-g'arbiy"],
    "ru": ["Северный", "Северо-восточный", "Восточный", "Юго-восточный",
           "Южный", "Юго-западный", "Западный", "Северо-западный"],
}
WIND_ARROWS = ["↓", "↙", "←", "↖", "↑", "↗", "→", "↘"]

WIND_LEVELS = {  # (chegara m/s, nomi)
    "uz": [(3, "sokin"), (6, "kuchsiz"), (10, "o'rtacha"), (15, "kuchli"), (10**9, "juda kuchli")],
    "ru": [(3, "штиль"), (6, "слабый"), (10, "умеренный"), (15, "сильный"), (10**9, "очень сильный")],
}


def weather_desc(code, lang: str = "uz"):
    emoji, uz, ru = WEATHER_CODES.get(code, ("🌡", "—", "—"))
    if lang == "en":
        return emoji, WEATHER_EN.get(code, "—")
    return emoji, (ru if lang == "ru" else uz)


def wind_dir(deg, lang: str = "uz"):
    """Gradusni yo'nalish nomi va strelkaga aylantiradi."""
    if deg is None:
        return "", "—"
    i = round(deg / 45) % 8
    return WIND_ARROWS[i], WIND_DIRS.get(lang, WIND_DIRS["uz"])[i]


def wind_level(speed, lang: str = "uz") -> str:
    for limit, name in WIND_LEVELS.get(lang, WIND_LEVELS["uz"]):
        if (speed or 0) < limit:
            return name
    return ""


# ---------------- English ----------------
CITY_EN = {
    "toshkent": "Tashkent", "nukus": "Nukus", "moynoq": "Muynak", "urganch": "Urgench",
    "buxoro": "Bukhara", "navoiy": "Navoi", "samarqand": "Samarkand", "qarshi": "Karshi",
    "termiz": "Termez", "jizzax": "Jizzakh", "guliston": "Gulistan", "namangan": "Namangan",
    "andijon": "Andijan", "fargona": "Fergana",
}

LEVELS["en"] = [
    ("Good", "The air is clean. Enjoy your time outdoors."),
    ("Moderate", "Sensitive people (asthma, allergies) should take care."),
    ("Poor", "Limit time outdoors, exercise indoors."),
    ("Very poor", "Wear a mask (N95/FFP2) and keep windows closed."),
    ("Hazardous", "Dust storm! Stay indoors unless absolutely necessary."),
]
WEEKDAYS["en"] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

WEATHER_EN = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime fog", 51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    56: "Freezing drizzle", 57: "Freezing drizzle", 61: "Light rain", 63: "Rain",
    65: "Heavy rain", 66: "Freezing rain", 67: "Freezing rain", 71: "Light snow", 73: "Snow",
    75: "Heavy snow", 77: "Snow grains", 80: "Rain showers", 81: "Heavy showers",
    82: "Violent showers", 85: "Snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Severe thunderstorm with hail",
}
WIND_DIRS["en"] = ["North", "Northeast", "East", "Southeast",
                   "South", "Southwest", "West", "Northwest"]
WIND_LEVELS["en"] = [(3, "calm"), (6, "light"), (10, "moderate"), (15, "strong"),
                     (10**9, "very strong")]

T["en"] = {
    "btn_now": "🌫 Now",
    "btn_fc": "📈 Forecast",
    "btn_chart": "📊 Chart",
    "btn_city": "🏙 City",
    "btn_loc": "📍 Location",
    "btn_report": "📸 Report a storm",
    "btn_feed": "👀 Reports",
    "btn_sub": "🔔 Alerts",
    "btn_tips": "💊 Health tips",
    "btn_info": "📚 About",
    "btn_lang": T["uz"]["btn_lang"],
    "btn_refresh": "🔄 Refresh",
    "start": (
        "Hello, {name}! 👋\n\n"
        "I'm the <b>Chang Monitor</b> bot 🌪\n"
        "I track <b>dust and sand storms</b> across Uzbekistan: current levels, "
        "forecasts, charts, weather and alerts.\n\n"
        "📸 See a storm with your own eyes? Send a photo and we'll warn others!\n\n"
        "To start, pick your city or send your 📍 location 👇"
    ),
    "help": (
        "<b>Commands:</b>\n"
        "/havo: current dust level and weather\n"
        "/prognoz: 3-day forecast\n"
        "/grafik: dust and wind chart\n"
        "/shahar: choose a city\n"
        "/xabar: send a storm photo\n"
        "/xabarlar: storm reports nearby\n"
        "/obuna: alerts and daily report\n"
        "/maslahat: health tips\n"
        "/malumot: about dust storms\n"
        "/til: change language\n"
        "/stop: delete all my data\n\n"
        "Data source: Open-Meteo / Copernicus CAMS."
    ),
    "choose_lang": T["uz"]["choose_lang"],
    "lang_set": "✅ Language: English",
    "choose_city": "🏙 Choose a city:",
    "city_set": "✅ City: <b>{name}</b>",
    "city_selected": "{name} selected",
    "my_location": "My location",
    "loc_saved": "✅ Your location has been saved.",
    "need_city": "Please choose a city first 👇",
    "api_error": "😔 Couldn't get the data. Please try again a bit later.",
    "unknown": "Sorry, I didn't get that 🤔 Use the buttons below or /help",
    "updating": "Refreshing...",
    "stop_done": "🗑 Your data has been deleted and you won't get messages. To come back: /start",
    "not_set": "not set",
    "enabled": "Enabled ✅",
    "disabled": "Disabled ❌",
    "dust": "Dust",
    "aod": "Aerosol (AOD)",
    "warn24": ("⚠️ <b>Heads up!</b> Dust is expected to rise in the next 24 hours: "
               "around {time} PM10 ≈ {pm10} µg/m³"),
    "morning": "☀️ <b>Good morning!</b>\n\n",
    "fc_title": "📈 <b>{place}: 3-day dust and weather forecast</b>\n",
    "fc_line": "PM10 max: <b>{pm10}</b> (at {peak})  •  Dust: {dust}  •  PM2.5: {pm25}\n",
    "fc_note": "<i>Dust in µg/m³, daily maximum. Wind: average speed and gusts.</i>",
    "chart_title": "{place}: dust forecast (72 hours)",
    "chart_title_wind": "{place}: dust and wind forecast (72 hours)",
    "chart_dust": "Dust",
    "chart_y": "µg/m³",
    "chart_now": "now",
    "chart_caption": ("📊 <b>{place}</b>: 3-day dust and wind chart\n"
                      "Top: dust. Colour zones: 🟢 good → 🟣 hazardous\n"
                      "Bottom: wind speed, gusts and direction (arrows show where the wind "
                      "is blowing to)"),
    "chart_caption_nowind": "📊 <b>{place}</b>: 3-day dust chart\nColour zones: 🟢 good → 🟣 hazardous",
    "chart_wind": "Wind speed",
    "chart_gusts": "Gusts",
    "chart_wind_y": "m/s",
    "chart_strong": "strong wind",
    "chart_wait": "📊 Preparing the chart...",
    "sub_text": (
        "🔔 <b>Alert settings</b>\n📍 Place: <b>{place}</b>\n\n"
        "• <b>Storm alerts</b>: I'll message you if PM10 is expected to exceed {pm10} "
        "or dust {dust} µg/m³ in the next 24 hours. I'll also forward storm photos "
        "taken nearby.\n"
        "• <b>Daily report</b>: a short summary every day at {hour:02d}:00."
    ),
    "sub_alerts": "Storm alerts",
    "sub_daily": "Daily report ({hour:02d}:00)",
    "alert": (
        "🚨 <b>DUST STORM ALERT</b>\n\n"
        "📍 {place}\n"
        "🕐 {when}, around {hour}\n"
        "{emoji} PM10 ≈ <b>{pm10}</b> µg/m³ ({level})\n"
        "🏜 Dust ≈ <b>{dust}</b> µg/m³\n\n"
        "💡 {advice}\n\nMore: /maslahat"
    ),
    "today": "today",
    "tomorrow": "tomorrow",
    "report_prompt": (
        "📸 <b>Report a storm</b>\n\n"
        "If you see a dust or sand storm, <b>send a photo here</b>. "
        "You can add a caption (e.g. \"Visibility 100 m\").\n\n"
        "Your report will be linked to <b>{place}</b>. If you're somewhere else, "
        "send your 📍 location first."
    ),
    "report_pending": "🙏 Thank you! Your photo is being reviewed. Once approved, people nearby will see it.",
    "report_saved": "🙏 Thank you! Your report is saved and people nearby can see it.",
    "report_limit": "⏳ You can send up to {n} reports per day. Please try again tomorrow.",
    "report_approved": "✅ Your storm report was approved and sent to people nearby. Thank you!",
    "report_rejected": "❌ Your storm report was not approved.",
    "report_nearby": "📸 <b>Storm report nearby</b> ({km} km)\n📍 {place} • {time}",
    "feed_title": "👀 <b>Storm reports from the last 24 hours</b> (within {km} km):",
    "feed_empty": "✅ No storm reports near you in the last 24 hours.",
    "feed_item": "📍 {place} • {time} • {km} km",
    "tips": (
        "💊 <b>Staying healthy during a dust storm</b>\n\n"
        "😷 <b>Mask:</b> a regular medical mask doesn't stop dust well. "
        "Wear an <b>N95 / FFP2</b> mask.\n"
        "🪟 <b>Home:</b> close windows and doors, seal gaps with a damp cloth. "
        "Turn on an air purifier if you have one.\n"
        "💧 <b>Water:</b> drink more water, rinse your nose and eyes with clean water.\n"
        "👓 <b>Eyes:</b> wear glasses and avoid contact lenses if you can.\n"
        "🏃 <b>Exercise:</b> skip outdoor runs and workouts.\n"
        "🚗 <b>Driving:</b> visibility drops. Slow down and switch the AC to "
        "recirculation.\n\n"
        "👶👴 <b>At-risk groups:</b> children, older people, pregnant women, and people "
        "with asthma, heart or lung disease should stay indoors.\n"
        "🚑 If you have shortness of breath, chest pain or a bad cough, call <b>103</b>."
    ),
    "info": (
        "📚 <b>About dust and sand storms</b>\n\n"
        "🌪 <b>A dust storm</b> happens when strong wind lifts dry soil and sand and "
        "carries it hundreds of kilometres. Visibility can drop below 1 km.\n\n"
        "🏜 <b>Why are they common in Uzbekistan?</b>\n"
        "• The drying of the Aral Sea created the <b>Aralkum</b> desert, a source of "
        "salt and dust.\n"
        "• The nearby Kyzylkum and Karakum deserts.\n"
        "• Drought and shrinking green areas.\n\n"
        "🔬 <b>Measurements:</b>\n"
        "• <b>PM10</b>: particles smaller than 10 microns (dust, sand).\n"
        "• <b>PM2.5</b>: particles smaller than 2.5 microns. They reach deep into the "
        "lungs and are the most harmful.\n"
        "• <b>Dust</b>: the amount of mineral dust in the air.\n\n"
        "📏 WHO guideline: daily average PM10 should stay below <b>45 µg/m³</b>, "
        "PM2.5 below <b>15 µg/m³</b>.\n\n"
        "🌳 <b>The fix:</b> planting trees and saxaul forests on the dry Aral seabed "
        "reduces dust storms."
    ),
    "weather": "Weather",
    "temp": "Temperature",
    "feels": "feels like",
    "humidity": "Humidity",
    "precip": "Precipitation",
    "wind": "Wind",
    "gusts": "gusts",
    "ms": "m/s",
    "mm": "mm",
    "wind_warn": ("💨 <b>Strong wind!</b> Gusts up to {gust} m/s ({when}, around {hour}). "
                  "Wind can lift dust and sand."),
    "fc_weather": ("🌡 {tmin}…{tmax}°C  {wemoji} {wdesc}\n"
                   "☔ {psum} mm ({pprob}%)  •  💨 {wmax} m/s, gusts {gmax}  {arrow} {wdir}\n"),
    "no_weather": "<i>Couldn't get weather data.</i>",
}
missing = set(T["uz"]) - set(T["en"])
assert not missing, f"English translation missing: {missing}"


# Har bir tugma barcha tillarda: handlerlar hammasini taniydi
BUTTONS = {key: {T[lang][key] for lang in LANGS} for key in T["uz"] if key.startswith("btn_")}


def t(lang: str, key: str, **kw) -> str:
    text = T.get(lang, T["uz"]).get(key) or T["uz"][key]
    return text.format(**kw) if kw else text


def level_index(pm10: float) -> int:
    for i, limit in enumerate(LEVEL_LIMITS):
        if (pm10 or 0) < limit:
            return i
    return len(LEVEL_LIMITS) - 1


def level(pm10: float, lang: str = "uz"):
    i = level_index(pm10)
    name, advice = LEVELS.get(lang, LEVELS["uz"])[i]
    return LEVEL_EMOJI[i], name, advice


def city_name(key: str, lang: str = "uz") -> str:
    uz, ru, _, _ = CITIES[key]
    if lang == "en":
        return CITY_EN.get(key, uz)
    return ru if lang == "ru" else uz


def bar(value: float, maxv: float = 500, width: int = 10) -> str:
    n = min(width, round((value or 0) / maxv * width))
    return "█" * n + "░" * (width - n)
