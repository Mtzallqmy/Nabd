from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📂 قائمة المشاريع", callback_data="menu_projects")
    builder.button(text="ℹ️ المساعدة والتعليمات", callback_data="menu_help")
    builder.button(text="🆔 معرّفي (ID)", callback_data="menu_id")
    builder.button(text="⚙️ الإعدادات", callback_data="menu_settings")
    builder.adjust(1, 2, 1)
    return builder.as_markup()


def get_projects_keyboard(projects: list, *, page: int, more: bool):
    builder = InlineKeyboardBuilder()
    for p in projects:
        builder.button(
            text=f"📊 {p.owner}/{p.repository}"[:64], callback_data=f"proj_status:{p.id}"
        )
    if page:
        builder.button(text="السابق", callback_data=f"projects_page:{page - 1}")
    if more:
        builder.button(text="التالي", callback_data=f"projects_page:{page + 1}")
    builder.button(text="🏠 الرئيسية", callback_data="menu_home")
    builder.adjust(1)
    return builder.as_markup()


def get_project_detail_keyboard(project_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 تحديث الحالة", callback_data=f"proj_status:{project_id}")
    builder.button(text="🗑️ حذف المشروع", callback_data=f"proj_del_confirm:{project_id}")
    builder.button(text="📂 العودة للمشاريع", callback_data="menu_projects")
    builder.adjust(2, 1)
    return builder.as_markup()


def get_delete_confirm_keyboard(project_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="⚠️ نعم، تأكيد الحذف", callback_data=f"proj_del_exec:{project_id}")
    builder.button(text="❌ إلغاء", callback_data=f"proj_status:{project_id}")
    builder.adjust(1)
    return builder.as_markup()
