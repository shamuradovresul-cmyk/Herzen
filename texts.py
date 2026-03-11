TEXTS: dict[str, dict] = {
    "ru": {
        "choose_lang":     "🌍 Выберите язык / Choose language / 选择语言",
        "ask_group":       "👋 Привет! Я бот расписания РГПУ им. Герцена.\n\nВыбери факультет и группу 👇",
        "group_ok":        "✅ Группа <b>{}</b> установлена! 🎓",
        "group_empty":     "⚠️ Группа <b>{}</b> установлена, но расписание пустое.",
        "group_err":       "❌ Группа не найдена. Попробуй ID вручную: /setgroup 22885",
        "group_invalid":   "❌ ID должен состоять только из цифр.",
        "start":           "👋 <b>Бот расписания РГПУ им. Герцена</b>\n\nГруппа: <b>{name}</b>{subgroup}\n\nИспользуй кнопки ниже:",
        "no_lessons":      "Занятий нет 🎉",
        "no_week":         "На этой неделе занятий нет 🎉",
        "no_nextweek":     "На следующей неделе занятий нет 🎉",
        "loading":         "⏳ Загружаю расписание...",
        "loading_week":    "⏳ Загружаю расписание на неделю...",
        "loading_fac":     "⏳ Загружаю список факультетов...",
        "notify_on":       "🔔 Уведомления <b>включены</b>! Напомню за 30 мин до занятия.",
        "notify_off":      "🔕 Уведомления <b>выключены</b>.",
        "notify_soon":     "⏰ <b>Через 30 минут занятие!</b>\n\n",
        "setgroup_hint":   "Укажи ID группы:\n<code>/setgroup 22885</code>\n\nИли выбери кнопкой 👇",
        "setgroup_ok":     "✅ Группа <b>{}</b> установлена. Занятий: {}",
        "choose_fac":      "🏛 Выбери факультет / институт:",
        "choose_form":     "📋 Выбери форму обучения:",
        "choose_level":    "🎓 Выбери ступень обучения:",
        "choose_course":   "📚 Выбери курс:",
        "choose_group":    "👥 Выбери группу:",
        "choose_subgroup": "👤 Есть подгруппы. Выбери свою:",
        "btn_today":       "📅 Сегодня",
        "btn_tomorrow":    "📅 Завтра",
        "btn_week":        "📆 Эта неделя",
        "btn_nextweek":    "📆 След. неделя",
        "btn_notify":      "🔔 Уведомления",
        "btn_evening":     "🌙 Расписание вечером",
        "btn_lang":        "🌍 Язык",
        "btn_group":       "👥 Сменить группу",
        "evening_on":      "🌙 Вечернее расписание <b>включено</b>! Буду присылать завтрашнее расписание в 20:00.",
        "evening_off":     "🌙 Вечернее расписание <b>выключено</b>.",
        "no_tomorrow":     "Завтра занятий нет 🎉",
        "subgroup_label":  " · Подгруппа <b>{}</b>",
        "help_text": (
            "🆘 <b>Справка</b>\n\n"
            "/today — Сегодня\n"
            "/tomorrow — Завтра\n"
            "/week — Эта неделя\n"
            "/nextweek — Следующая неделя\n"
            "/notify — Уведомления за 30 мин\n"
            "/evening — Вечерняя рассылка в 20:00\n"
            "/setgroup — Сменить группу\n"
            "/lang — Язык\n"
            "/help — Справка"
        ),
        "days": ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"],
    },
    "en": {
        "btn_today":    "📅 Today",       "btn_tomorrow":  "📅 Tomorrow",
        "btn_week":     "📆 This week",   "btn_nextweek":  "📆 Next week",
        "btn_notify":   "🔔 Notifications","btn_evening":  "🌙 Evening schedule",
        "btn_lang":     "🌍 Language",    "btn_group":     "👥 Change group",
        "notify_on":    "🔔 Notifications <b>enabled</b>! Reminder 30 min before class.",
        "notify_off":   "🔕 Notifications <b>disabled</b>.",
        "evening_on":   "🌙 Evening schedule <b>enabled</b>! Tomorrow's schedule at 8 PM.",
        "evening_off":  "🌙 Evening schedule <b>disabled</b>.",
        "no_lessons":   "No classes 🎉",
        "no_week":      "No classes this week 🎉",
        "no_nextweek":  "No classes next week 🎉",
        "no_tomorrow":  "No classes tomorrow 🎉",
        "days": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],
    },
    "zh": {
        "btn_today":    "📅 今天",  "btn_tomorrow": "📅 明天",
        "btn_week":     "📆 本周",  "btn_nextweek": "📆 下周",
        "btn_notify":   "🔔 通知",  "btn_evening":  "🌙 晚间课表",
        "btn_lang":     "🌍 语言",  "btn_group":    "👥 更换小组",
        "notify_on":    "🔔 通知<b>已开启</b>！将在课前30分钟提醒。",
        "notify_off":   "🔕 通知<b>已关闭</b>。",
        "evening_on":   "🌙 晚间课表<b>已开启</b>！晚8点发送明天课表。",
        "evening_off":  "🌙 晚间课表<b>已关闭</b>。",
        "no_lessons":   "没有课 🎉",
        "no_week":      "本周没有课 🎉",
        "no_nextweek":  "下周没有课 🎉",
        "no_tomorrow":  "明天没有课 🎉",
        "days": ["周一","周二","周三","周四","周五","周六","周日"],
    },
}

# Заполняем пропуски из RU
for _lang in ["en", "zh"]:
    for _k, _v in TEXTS["ru"].items():
        TEXTS[_lang].setdefault(_k, _v)
