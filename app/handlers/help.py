"""
Хендлер помощи, правил и информации о проекте.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()


def help_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура разделов помощи."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⚡ Быстрый старт (В бой!)", callback_data="quick_battle")
    builder.button(text="⚔️ Форматы битв", callback_data="help_formats")
    builder.button(text="📈 Уровни и ранги", callback_data="help_levels")
    builder.button(text="🔥 Серии и бонусы", callback_data="help_streaks")
    builder.button(text="🤖 О проекте", callback_data="help_about")
    builder.adjust(1, 2, 2)
    return builder.as_markup()


def help_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата в меню помощи."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⚡ Начать игру прямо сейчас", callback_data="quick_battle")
    builder.button(text="⬅️ Назад в справку", callback_data="show_help")
    builder.adjust(1, 1)
    return builder.as_markup()


HELP_MAIN_TEXT = (
    "❓ <b>КАК ИГРАТЬ В AI CHALLENGE — ГАЙД ЗА 1 МИНУТУ</b>\n\n"
    "<b>AI Challenge</b> — это игра-битва между человеком и искусственным интеллектом!\n\n"
    "📌 <b>Главные правила просты:</b>\n"
    "1️⃣ <b>Выбирай битву</b> — нажми <b>«⚔️ AI Battle»</b> или <b>«⚡ Быстрая игра»</b>. "
    "Тебе попадётся интересная задача на логику, сообразительность или поиск багов в ответе ИИ.\n\n"
    "2️⃣ <b>Отвечай и получай XP</b> — правильные ответы дают очки опыта (XP) и приближают тебя к новому рангу.\n\n"
    "3️⃣ <b>Не пропускай «🧠 Ежедневный вызов»</b> — один короткий вопрос в день даёт +20 XP "
    "и растит твою серию дней активности 🔥. Чем длиннее серия — тем выше бонусы!\n\n"
    "4️⃣ <b>Смотри рейтинг</b> — соревнуйся с другими игроками за первые места в топе 🏆!\n\n"
    "Выбери подробный раздел ниже 👇"
)


@router.message(F.text.in_(["❓ Как играть", "❓ Помощь", "❓ Справка", "❓ Правила"]))
@router.message(Command("help"))
@router.message(Command("rules"))
@router.callback_query(F.data == "show_help")
async def show_help(event: Message | CallbackQuery) -> None:
    """Показать главное меню помощи."""
    if isinstance(event, CallbackQuery):
        await event.answer()
        if isinstance(event.message, Message):
            await event.message.edit_text(
                HELP_MAIN_TEXT, reply_markup=help_menu_keyboard(), parse_mode="HTML"
            )
    else:
        await event.answer(HELP_MAIN_TEXT, reply_markup=help_menu_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "help_formats")
async def help_formats_callback(callback: CallbackQuery) -> None:
    """Справка по форматам битв."""
    await callback.answer()
    text = (
        "⚔️ <b>ФОРМАТЫ БИТВ С ИИ</b>\n\n"
        "1️⃣ <b>Human First (Ответь быстрее ИИ)</b>\n"
        "Ты видишь задачу и выбираешь свой вариант. После этого смотришь правильный ответ и подробный разбор!\n\n"
        "2️⃣ <b>AI Detective (Найди ошибку)</b>\n"
        "Нейросеть дала ответ, но в нём закралась тонкая логическая ловушка или галлюцинация. "
        "Твоя задача — раскусить ИИ и найти ошибку!\n\n"
        "3️⃣ <b>Co-Creation (Улучши ответ)</b>\n"
        "ИИ сгенерировал сырой шаблон. Ты добавляешь точность, креатив и человеческий инсайт.\n\n"
        "4️⃣ <b>Multiple Choice</b>\n"
        "Быстрые тесты с 4 вариантами ответа — идеально для быстрой тренировки ума."
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=help_back_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "help_levels")
async def help_levels_callback(callback: CallbackQuery) -> None:
    """Справка по уровням и XP."""
    await callback.answer()
    text = (
        "📈 <b>РАНГИ И ОЧКИ ОПЫТА (XP)</b>\n\n"
        "За каждый правильный ответ ты получаешь XP:\n"
        "• Лёгкое задание: <b>10–20 XP</b>\n"
        "• Среднее задание: <b>20–35 XP</b>\n"
        "• Сложное задание: <b>35–50+ XP</b>\n\n"
        "🏆 <b>Иерархия рангов:</b>\n"
        "🌱 <b>Уровень 1: Новичок</b> (0–100 XP)\n"
        "🔍 <b>Уровень 2: Исследователь</b> (100–300 XP)\n"
        "⚡ <b>Уровень 3: Практик</b> (300–700 XP)\n"
        "🚀 <b>Уровень 4: Эксперт</b> (700–1500 XP)\n"
        "🧠 <b>Уровень 5: Сверхразум</b> (1500+ XP)\n\n"
        "Достигай уровня Сверхразума и держись в топе!"
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=help_back_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "help_streaks")
async def help_streaks_callback(callback: CallbackQuery) -> None:
    """Справка по сериям и бонусам."""
    await callback.answer()
    text = (
        "🔥 <b>СЕРИИ ПОБЕД И АКТИВНОСТЬ</b>\n\n"
        "Играй каждый день, побеждай нейросети и расти серию побед!\n\n"
        "🔥 <b>Что даёт серия непрерывных дней?</b>\n"
        "• Бонусный множитель опыта (XP)\n"
        "• Специальные достижения за серии 3, 7 и 14 дней подряд!\n\n"
        "⚠️ Если ты пропустишь хотя бы один день, серия сбросится до 1."
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=help_back_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "help_about")
async def help_about_callback(callback: CallbackQuery) -> None:
    """О проекте AI Challenge."""
    await callback.answer()
    text = (
        "🤖 <b>О ПРОЕКТЕ AI CHALLENGE</b>\n\n"
        "Тема проекта: <b>AI VS Человек</b>\n"
        "Слоган: <i>«Think smarter. Create better. Challenge AI.»</i>\n\n"
        "Цель — превратить пассивное использование нейросетей в осознанное критическое "
        "мышление и способность видеть сильные и слабые стороны искусственного интеллекта.\n\n"
        "🛡️ Данные аккаунта привязаны к твоему Telegram ID."
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=help_back_keyboard(), parse_mode="HTML")
