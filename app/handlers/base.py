from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.keyboards import get_main_menu_keyboard

router = Router()

WELCOME_TEXT = (
    "🚀 <b>أهلًا بك في نَبْض | مركز قيادة المشاريع</b>\n\n"
    "مراقبة المستودعات البرمجية وعمليات GitHub عبر تيليجرام.\n"
    "للوصول إلى معلومات المشاريع يجب أن تكون من المشرفين المصرح لهم."
)
HELP_TEXT = (
    "📖 <b>دليل نَبْض</b>\n\n"
    "/start — القائمة الرئيسية\n"
    "/help — المساعدة\n"
    "/id — إظهار معرفك\n"
    "/addproject owner/repo — إضافة مستودع (للمشرفين)\n"
    "/projects — قائمة المستودعات (للمشرفين)\n"
    "/status owner/repo — تقرير GitHub (للمشرفين)\n"
    "/removeproject — حذف مشروع بعد التأكيد (للمشرفين)\n"
    "/settings — عرض إعدادات التشغيل (للمشرفين)"
)


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(WELCOME_TEXT, reply_markup=get_main_menu_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT)


@router.message(Command("id"))
async def cmd_id(message: Message):
    if message.from_user is None:
        return
    await message.answer(f"🆔 معرّفك في تيليجرام هو: <code>{message.from_user.id}</code>")


@router.callback_query(F.data == "menu_home")
async def cb_home(callback: CallbackQuery):
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    await callback.message.edit_text(WELCOME_TEXT, reply_markup=get_main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu_help")
async def cb_help(callback: CallbackQuery):
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    await callback.message.edit_text(HELP_TEXT, reply_markup=get_main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu_id")
async def cb_id(callback: CallbackQuery):
    await callback.answer(f"معرّفك: {callback.from_user.id}", show_alert=True)
