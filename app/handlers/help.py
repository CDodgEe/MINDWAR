"""
Хендлер помощи, правил и информации о проекте.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()


def help_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура разделов помощи."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⚔️ Форматы битв", callback_data="help_formats")
    builder.button(text="📈 Уровни и XP", callback_data="help_levels")
    builder.button(text="🔥 Серии и бонусы", callback_data="help_streaks")
    builder.button(text="🤖 Об AI Challenge", callback_data="help_about")
    builder.button(text="🚀 Начать игру", callback_data="start_challenge")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def help_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата в меню помощи."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад в справку", callback_data="show_help")
    builder.button(text="⚔️ В бой!", callback_data="start_challenge")
    builder.adjust(1, 1)
    return builder.as_markup()


HELP_MAIN_TEXT = (
    "❓ <b>КАК ИГРАТЬ В AI CHALLENGE</b>\n\n"
    "<b>AI Challenge</b> — это цифровая арена «AI VS Молодёжь», где ты "
    "проверяешь своё мышление, соревнуясь с искусственным интеллектом.\n\n"
    "🎯 <b>Цель:</b> доказать, что человеческий интеллект, критическое мышление "
    "и креативность превосходят шаблоны нейросетей.\n\n"
    "📌 <b>Основные возможности:</b>\n"
    "• ⚔️ <b>AI Battle</b> — дуэли с ИИ в 3 уникальных форматах\n"
    "• 🧠 <b>Ежедневный вызов</b> — свежая задача каждый день с бонусом к серии\n"
    "• 🎯 <b>Выбор категории</b> — от логики и промпт-инжиниринга до кибербезопасности\n"
    "• 🏆 <b>Рейтинг</b> — соревнуйся за топ среди всех участников\n"
    "• 🎖️ <b>Достижения</b> — собирай бейджи и прокачивай ранг\n\n"
    "Выбери раздел ниже, чтобы узнать больше 👇"
)


@router.message(F.text == "❓ Как играть")
@router.message(Command("help"))
@router.message(Command("rules"))
@router.callback_query(F.data == "show_help")
async def show_help(event: Message | CallbackQuery) -> None:
    """Показать главное меню помощи."""
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(HELP_MAIN_TEXT, reply_markup=help_menu_keyboard(), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(HELP_MAIN_TEXT, reply_markup=help_menu_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "help_formats")
async def help_formats_callback(callback: CallbackQuery) -> None:
    """Справка по форматам битв."""
    text = (
        "⚔️ <b>ФОРМАТЫ AI BATTLE</b>\n\n"
        "1️⃣ <b>Human First (Ответь первым)</b>\n"
        "Ты получаешь задачу и даёшь свой ответ ДО того, как увидишь ответ ИИ. "
        "Затем система сравнивает твоё решение и решение ИИ, определяя победителя.\n\n"
        "2️⃣ <b>AI Detective (Найди ошибку)</b>\n"
        "ИИ дал ответ с хитрой логической, фактической или программной ошибкой. "
        "Твоя задача — обнаружить «галлюцинацию» или ловушку и указать верный ответ.\n\n"
        "3️⃣ <b>Co-Creation (Улучши ответ)</b>\n"
        "ИИ сгенерировал сырой, шаблонный или неполный ответ. "
        "Ты выступаешь редактором и ментором, дополняя его глубокими инсайтами и креативом.\n\n"
        "4️⃣ <b>Multiple Choice</b>\n"
        "Тестовые сценарии на сообразительность, этику ИИ и промпт-инжиниринг с выбором варианта."
    )
    await callback.message.edit_text(text, reply_markup=help_back_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "help_levels")
async def help_levels_callback(callback: CallbackQuery) -> None:
    """Справка по уровням и XP."""
    text = (
        "📈 <b>УРОВНИ И ОЧКИ ОПЫТА (XP)</b>\n\n"
        "Каждое правильное действие приносит опыт (XP):\n"
        "• Легкое задание: <b>10–20 XP</b>\n"
        "• Среднее задание: <b>20–35 XP</b>\n"
        "• Сложное задание: <b>35–50+ XP</b>\n"
        "• Победа над ИИ в дуэли: <b>бонус +10 XP</b>\n\n"
        "🏆 <b>Ранги мастерства:</b>\n"
        "🌱 <b>Уровень 1: Новичок</b> (0–100 XP)\n"
        "🔍 <b>Уровень 2: Исследователь</b> (100–300 XP)\n"
        "⚡ <b>Уровень 3: Практик</b> (300–700 XP)\n"
        "🚀 <b>Уровень 4: Эксперт</b> (700–1500 XP)\n"
        "🧠 <b>Уровень 5: Сверхразум</b> (1500+ XP)\n\n"
        "<i>Все расчеты выполняются надежно на стороне сервера.</i>"
    )
    await callback.message.edit_text(text, reply_markup=help_back_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "help_streaks")
async def help_streaks_callback(callback: CallbackQuery) -> None:
    """Справка по сериям и бонусам."""
    text = (
        "🔥 <b>СЕРИИ И ЕЖЕДНЕВНЫЕ БОНУСЫ</b>\n\n"
        "Заходи в бот каждый день и проходи <b>Ежедневный вызов</b>!\n\n"
        "🔥 <b>Множители серии (Streak):</b>\n"
        "• 1-2 дня: базовый XP\n"
        "• 3-6 дней подряд: <b>+15% XP</b>\n"
        "• 7-13 дней подряд: <b>+30% XP</b> (Недельный чемпион!)\n"
        "• 14+ дней подряд: <b>+50% XP</b> (Легендарная серия!)\n\n"
        "⚠️ Если ты пропустишь день, серия обнулится. Не забывай заглядывать в бот!"
    )
    await callback.message.edit_text(text, reply_markup=help_back_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "help_about")
async def help_about_callback(callback: CallbackQuery) -> None:
    """О проекте AI Challenge."""
    text = (
        "🤖 <b>О ПРОЕКТЕ AI CHALLENGE</b>\n\n"
        "Тема: <b>AI VS Молодёжь</b>\n"
        "Слоган: <i>«ИИ может дать ответ. Но сможешь ли ты превзойти его?»</i>\n\n"
        "Проект создан, чтобы трансформировать пассивное потребление нейросетей "
        "в осознанное, критическое и профессиональное владение AI-инструментами.\n\n"
        "🛡️ <b>Безопасность:</b> Мы не храним персональные данные за пределами Telegram ID.\n"
        "Версия: <code>1.0.0</code>"
    )
    await callback.message.edit_text(text, reply_markup=help_back_keyboard(), parse_mode="HTML")
    await callback.answer()
