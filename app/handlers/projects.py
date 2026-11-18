import logging
from html import escape

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.github_client import GitHubClient, validate_repository
from app.keyboards import (
    get_delete_confirm_keyboard,
    get_main_menu_keyboard,
    get_project_detail_keyboard,
    get_projects_keyboard,
)
from app.services import PAGE_SIZE, ProjectService

router = Router()
logger = logging.getLogger(__name__)


def is_admin(user_id: int | None) -> bool:
    return user_id is not None and user_id in settings.admin_ids_list


async def deny_message(message: Message) -> bool:
    if message.chat.type != ChatType.PRIVATE or not is_admin(
        message.from_user.id if message.from_user else None
    ):
        await message.answer("⛔ ليس لديك إذن لعرض أو إدارة المشاريع.")
        return True
    return False


async def deny_callback(callback: CallbackQuery) -> bool:
    if (
        not isinstance(callback.message, Message)
        or callback.message.chat.type != ChatType.PRIVATE
        or not is_admin(callback.from_user.id)
    ):
        await callback.answer("⛔ ليس لديك صلاحية.", show_alert=True)
        return True
    return False


def parse_slug(raw: str) -> tuple[str, str]:
    parts = raw.strip().split(maxsplit=1)
    if len(parts) != 2 or parts[1].count("/") != 1:
        raise ValueError("استخدم الأمر بالصيغة: owner/repository")
    return validate_repository(*parts[1].split("/", 1))


def parse_project_id(callback: CallbackQuery) -> int:
    project_id = int(callback.data.split(":", 1)[1])
    if not 0 < project_id <= 2**31 - 1:
        raise ValueError("Invalid project ID")
    return project_id


@router.message(Command("addproject"))
async def cmd_add_project(message: Message, session: AsyncSession):
    if await deny_message(message):
        return
    try:
        owner, repo = parse_slug(message.text or "")
    except ValueError as exc:
        await message.answer(f"⚠️ {escape(str(exc))}")
        return
    wait_msg = await message.answer("⏳ جارٍ التحقق من المستودع عبر GitHub…")
    try:
        await ProjectService.add_project(session, owner, repo, message.from_user.id)
        await wait_msg.edit_text(f"✅ تمت إضافة <code>{escape(owner)}/{escape(repo)}</code> بنجاح.")
    except ValueError as exc:
        await wait_msg.edit_text(f"⚠️ {escape(str(exc))}")
    except Exception as error:
        logger.warning("Project registration failed (%s)", type(error).__name__)
        await wait_msg.edit_text("❌ تعذرت إضافة المستودع بسبب مشكلة اتصال أو تخزين. راجع السجلات.")


async def send_project_list(target: Message | CallbackQuery, session: AsyncSession, page: int = 0):
    projects = await ProjectService.list_projects(session, page=page)
    text = (
        "📂 <b>المشاريع المسجلة</b>\nاختر مشروعًا لعرض حالته أو حذفه:"
        if projects
        else "📂 لا توجد مشاريع في هذه الصفحة."
    )
    keyboard = get_projects_keyboard(
        projects[:PAGE_SIZE], page=page, more=len(projects) > PAGE_SIZE
    )
    if isinstance(target, CallbackQuery):
        await target.answer()
        await target.message.edit_text(text, reply_markup=keyboard)
    else:
        await target.answer(text, reply_markup=keyboard)


@router.message(Command("projects"))
async def cmd_projects(message: Message, session: AsyncSession):
    if not await deny_message(message):
        await send_project_list(message, session)


@router.callback_query(F.data == "menu_projects")
@router.callback_query(F.data.regexp(r"^projects_page:[0-9]{1,8}$"))
async def cb_projects(callback: CallbackQuery, session: AsyncSession):
    if not await deny_callback(callback):
        page = int(callback.data.split(":")[1]) if ":" in callback.data else 0
        await send_project_list(callback, session, page)


@router.message(Command("settings"))
@router.callback_query(F.data == "menu_settings")
async def show_settings(event: Message | CallbackQuery):
    is_callback = isinstance(event, CallbackQuery)
    if await (deny_callback(event) if is_callback else deny_message(event)):
        return
    github = "مُهيّأ للطلبات الموثّقة" if settings.github_token else "قراءة عامة"
    text = f"⚙️ <b>إعدادات نَبْض</b>\nGitHub: {github}\nالوصول: المشرفون في المحادثة الخاصة."
    if is_callback:
        await event.answer()
        await event.message.edit_text(text, reply_markup=get_main_menu_keyboard())
    else:
        await event.answer(text, reply_markup=get_main_menu_keyboard())


@router.message(Command("status"))
async def cmd_status(message: Message):
    if await deny_message(message):
        return
    try:
        owner, repo = parse_slug(message.text or "")
    except ValueError as exc:
        await message.answer(f"⚠️ {escape(str(exc))}")
        return
    await fetch_and_send_status(message, owner, repo)


async def fetch_and_send_status(
    target: Message | CallbackQuery,
    owner: str,
    repo: str,
    *,
    edit: bool = False,
    project_id: int | None = None,
):
    msg = target.message if isinstance(target, CallbackQuery) else target
    if edit:
        wait_msg = msg
        await wait_msg.edit_text("⏳ جارٍ جلب بيانات GitHub…")
    else:
        wait_msg = await msg.answer("⏳ جارٍ جلب بيانات GitHub…")
    try:
        data = await GitHubClient().get_repository_status(owner, repo)
        emoji = {"success": "🟢", "failure": "🔴"}.get(data["workflow_conclusion"], "🟡")

        def c(value):
            return escape(str(value if value is not None else "غير متوفر")[:140])

        text = (
            f"📊 <b>تقرير المشروع:</b> <code>{c(data['full_name'])}</code>\n\n"
            f"🌿 الفرع الافتراضي: <code>{c(data['default_branch'])}</code>\n"
            f"🔗 المستودع: {c(data['repo_url'])}\n\n"
            f"💬 <b>آخر التزام:</b> <code>{c(data['commit_sha'])}</code>\n"
            f"{c(data['commit_message'])}\n"
            f"⚙️ GitHub Actions: {emoji} {c(data['workflow_status'])}"
            f" / {c(data['workflow_conclusion'])}\n"
        )
        if data["commit_error"]:
            text += f"⚠️ جلب الالتزامات: {c(data['commit_error'])}\n"
        if data["workflow_error"]:
            text += f"⚠️ جلب التشغيلات: {c(data['workflow_error'])}\n"
        if data["commit_url"]:
            text += f"🔗 التزام: {c(data['commit_url'])}\n"
        if data["workflow_url"]:
            text += f"🔗 التشغيل: {c(data['workflow_url'])}\n"
        await wait_msg.edit_text(
            text,
            reply_markup=get_project_detail_keyboard(project_id)
            if project_id is not None
            else get_main_menu_keyboard(),
            disable_web_page_preview=True,
        )
    except ValueError as exc:
        await wait_msg.edit_text(f"❌ {escape(str(exc))}", reply_markup=get_main_menu_keyboard())
    except Exception as error:
        logger.warning("Repository status failed (%s)", type(error).__name__)
        await wait_msg.edit_text(
            "❌ تعذر جلب حالة المستودع. أعد المحاولة لاحقًا.", reply_markup=get_main_menu_keyboard()
        )


async def get_registered_project(callback: CallbackQuery, session: AsyncSession):
    try:
        project_id = parse_project_id(callback)
    except (ValueError, TypeError):
        await callback.answer("معرّف المشروع غير صالح", show_alert=True)
        return None
    project = await ProjectService.get_project(session, project_id)
    if project is None:
        await callback.answer("المشروع غير مسجل", show_alert=True)
        return None
    return project


@router.callback_query(F.data.startswith("proj_status:"))
async def cb_project_status(callback: CallbackQuery, session: AsyncSession):
    if await deny_callback(callback):
        return
    project = await get_registered_project(callback, session)
    if project:
        await callback.answer()
        await fetch_and_send_status(
            callback,
            project.owner,
            project.repository,
            edit=True,
            project_id=project.id,
        )


@router.callback_query(F.data.startswith("proj_del_confirm:"))
async def cb_project_del_confirm(callback: CallbackQuery, session: AsyncSession):
    if await deny_callback(callback):
        return
    project = await get_registered_project(callback, session)
    if project:
        await callback.message.edit_text(
            f"⚠️ هل تريد حذف <code>{escape(project.full_name)}</code> من المراقبة؟",
            reply_markup=get_delete_confirm_keyboard(project.id),
        )
        await callback.answer()


@router.callback_query(F.data.startswith("proj_del_exec:"))
async def cb_project_del_exec(callback: CallbackQuery, session: AsyncSession):
    if await deny_callback(callback):
        return
    project = await get_registered_project(callback, session)
    if project:
        removed = await ProjectService.remove_project_by_id(
            session, project.id, callback.from_user.id
        )
        text = "🗑️ تم حذف المشروع من القائمة." if removed else "المشروع غير مسجل."
        await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard())
        await callback.answer()


@router.message(Command("removeproject"))
async def cmd_remove_project(message: Message, session: AsyncSession):
    if not await deny_message(message):
        await send_project_list(message, session)
