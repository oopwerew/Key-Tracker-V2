import os
import flet as ft
from typing import Optional, List, Dict, Any

from config import (
    DEFAULT_API_URL,
    COLOR_BG,
    COLOR_CARD,
    COLOR_PRIMARY,
    COLOR_PRIMARY_LIGHT,
    COLOR_PRIMARY_HOVER,
    COLOR_TEXT_DARK,
    COLOR_TEXT_MUTED,
    COLOR_BORDER,
    COLOR_SUCCESS,
    COLOR_SUCCESS_LIGHT,
    COLOR_WARNING,
    COLOR_WARNING_LIGHT,
    COLOR_DANGER,
    COLOR_SEGMENT_BG,
    FONT_FAMILY
)
from api_client import ApiClient

def main(page: ft.Page):
    # Настройки страницы под мобильный экран (iOS iPhone)
    page.title = "Key Tracker — Мобильная версия"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = COLOR_BG
    page.padding = 0
    page.fonts = {
        "SF Pro": FONT_FAMILY
    }
    page.theme = ft.Theme(
        font_family="SF Pro",
        color_scheme_seed=COLOR_PRIMARY
    )

    # Имитация размера мобильного устройства для десктопного превью
    page.window.width = 420
    page.window.height = 860
    page.window.min_width = 380
    page.window.min_height = 650
    page.window.resizable = True

    # Инициализация API клиента
    api = ApiClient(DEFAULT_API_URL)

    # Безопасное обновление элементов (предотвращает ошибки, если элемент еще не на странице)
    def safe_update(control):
        try:
            if control and getattr(control, "page", None):
                control.update()
            elif page:
                page.update()
        except Exception:
            pass

    # Локальное состояние приложения
    state = {
        "active_tab": 0,           # 0: Ключи, 1: История, 2: Сервер
        "filter_type": "all",      # "all", "available", "taken"
        "search_query": "",
        "keys": [],
        "stats": {"total": 0, "available": 0, "taken": 0},
        "history": [],
        "is_online": False,
        "is_loading": False
    }

    # UI контейнеры
    keys_list_view = ft.ListView(
        expand=True,
        spacing=12,
        padding=ft.padding.symmetric(horizontal=16, vertical=8)
    )

    history_list_view = ft.ListView(
        expand=True,
        spacing=10,
        padding=ft.padding.symmetric(horizontal=16, vertical=8)
    )

    # Индикатор статуса подключения
    connection_indicator = ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    width=8,
                    height=8,
                    border_radius=4,
                    bgcolor=COLOR_WARNING,
                    key="dot"
                ),
                ft.Text(
                    "Проверка...",
                    size=12,
                    color=COLOR_TEXT_MUTED,
                    weight=ft.FontWeight.W_500,
                    key="label"
                )
            ],
            spacing=6,
            alignment=ft.MainAxisAlignment.START
        ),
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        border_radius=12,
        bgcolor=COLOR_CARD,
        border=ft.border.all(1, COLOR_BORDER)
    )

    # Счетчики статистики (iOS Карточки-бейджы)
    stat_total_val = ft.Text("0", size=18, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_DARK)
    stat_available_val = ft.Text("0", size=18, weight=ft.FontWeight.BOLD, color=COLOR_SUCCESS)
    stat_taken_val = ft.Text("0", size=18, weight=ft.FontWeight.BOLD, color=COLOR_WARNING)

    def make_stat_card(label: str, val_control: ft.Text, bg_color: str, border_color: str):
        return ft.Container(
            content=ft.Column(
                controls=[
                    val_control,
                    ft.Text(label, size=11, color=COLOR_TEXT_MUTED, weight=ft.FontWeight.W_500)
                ],
                spacing=2,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            bgcolor=bg_color,
            border=ft.border.all(1, border_color),
            border_radius=14,
            padding=ft.padding.symmetric(vertical=8, horizontal=14),
            expand=True
        )

    stats_row = ft.Row(
        controls=[
            make_stat_card("Всего", stat_total_val, COLOR_CARD, COLOR_BORDER),
            make_stat_card("В наличии", stat_available_val, COLOR_SUCCESS_LIGHT, COLOR_SUCCESS),
            make_stat_card("Выданы", stat_taken_val, COLOR_WARNING_LIGHT, COLOR_WARNING)
        ],
        spacing=10
    )

    # Поле поиска
    search_field = ft.CupertinoTextField(
        placeholder_text="Поиск по номеру, кабинету, ФИО...",
        prefix=ft.Container(
            padding=ft.padding.only(left=8, right=4),
            content=ft.Icon(ft.CupertinoIcons.SEARCH, size=18, color=COLOR_TEXT_MUTED)
        ),
        bgcolor=COLOR_CARD,
        border=ft.border.all(1, COLOR_BORDER),
        border_radius=12,
        padding=ft.padding.symmetric(vertical=10, horizontal=8),
        on_change=lambda e: on_search_changed(e.control.value)
    )

    def on_segment_change(e):
        idx = e.control.selected_index
        filters = ["all", "available", "taken"]
        if 0 <= idx < len(filters):
            state["filter_type"] = filters[idx]
            load_keys(show_error_toast=True)

    segment_control = ft.CupertinoSlidingSegmentedButton(
        selected_index=0,
        controls=[
            ft.Container(content=ft.Text("Все", size=13, weight=ft.FontWeight.W_600), padding=ft.padding.symmetric(vertical=6)),
            ft.Container(content=ft.Text("В наличии", size=13, weight=ft.FontWeight.W_600), padding=ft.padding.symmetric(vertical=6)),
            ft.Container(content=ft.Text("Выданы", size=13, weight=ft.FontWeight.W_600), padding=ft.padding.symmetric(vertical=6))
        ],
        bgcolor=COLOR_SEGMENT_BG,
        thumb_color=COLOR_CARD,
        on_change=on_segment_change
    )

    # Уведомления (iOS Toast / SnackBar)
    def show_alert(message: str, is_error: bool = False):
        try:
            snack = ft.SnackBar(
                content=ft.Text(message, color=COLOR_CARD, weight=ft.FontWeight.W_500),
                bgcolor=COLOR_DANGER if is_error else COLOR_PRIMARY,
                duration=3000
            )
            page.open(snack)
        except Exception:
            pass

    # Обновление индикатора сети
    def update_network_indicator(online: bool, text: Optional[str] = None):
        state["is_online"] = online
        dot = connection_indicator.content.controls[0]
        label = connection_indicator.content.controls[1]
        if online:
            dot.bgcolor = COLOR_SUCCESS
            label.value = text or "Онлайн"
            label.color = COLOR_SUCCESS
        else:
            dot.bgcolor = COLOR_DANGER
            label.value = text or "Офлайн"
            label.color = COLOR_DANGER
        safe_update(connection_indicator)

    # Загрузка статистики
    def load_stats():
        ok, stats, _ = api.get_stats()
        if ok:
            state["stats"] = stats
            stat_total_val.value = str(stats.get("total", 0))
            stat_available_val.value = str(stats.get("available", 0))
            stat_taken_val.value = str(stats.get("taken", 0))
            safe_update(stats_row)

    # Отрисовка списка ключей
    def render_keys(keys_data: List[Dict[str, Any]], is_offline: bool = False):
        keys_list_view.controls.clear()

        if is_offline:
            keys_list_view.controls.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.CupertinoIcons.WIFI_SLASH, size=48, color=COLOR_TEXT_MUTED),
                            ft.Text("Сервер не подключен", size=16, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_DARK),
                            ft.Text(
                                "Запустите backend-сервер (server/run_server.sh) или проверьте адрес на вкладке «Сервер»",
                                size=13,
                                color=COLOR_TEXT_MUTED,
                                text_align=ft.TextAlign.CENTER
                            ),
                            ft.Container(height=8),
                            ft.CupertinoFilledButton(
                                text="Повторить попытку",
                                on_click=lambda e: load_keys(show_error_toast=True)
                            )
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8
                    ),
                    padding=ft.padding.all(32),
                    alignment=ft.alignment.center
                )
            )
            safe_update(keys_list_view)
            return

        if not keys_data:
            keys_list_view.controls.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.KEY_OFF_ROUNDED, size=48, color=COLOR_TEXT_MUTED),
                            ft.Text("Кабинеты не найдены", size=16, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_DARK),
                            ft.Text("Попробуйте изменить поисковый запрос или фильтр", size=13, color=COLOR_TEXT_MUTED, text_align=ft.TextAlign.CENTER)
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8
                    ),
                    padding=ft.padding.all(40),
                    alignment=ft.alignment.center
                )
            )
            safe_update(keys_list_view)
            return

        for k in keys_data:
            key_id = k.get("id", "")
            key_name = k.get("name", "")
            floor = k.get("floor", 1)
            status = k.get("status", "available")
            taken_by = k.get("taken_by")
            phone = k.get("phone")
            taken_at = k.get("taken_at")
            expected_return = k.get("expected_return")
            notes = k.get("notes")

            is_available = (status == "available")

            # Бейдж статуса
            if is_available:
                status_badge = ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.CupertinoIcons.CHECKMARK_CIRCLE_FILL, size=13, color=COLOR_SUCCESS),
                            ft.Text("В наличии", size=11, weight=ft.FontWeight.BOLD, color=COLOR_SUCCESS)
                        ],
                        spacing=4,
                        alignment=ft.MainAxisAlignment.CENTER
                    ),
                    bgcolor=COLOR_SUCCESS_LIGHT,
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=10
                )
            else:
                status_badge = ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.CupertinoIcons.PERSON_CROP_CIRCLE_FILL, size=13, color=COLOR_WARNING),
                            ft.Text("На руках", size=11, weight=ft.FontWeight.BOLD, color=COLOR_WARNING)
                        ],
                        spacing=4,
                        alignment=ft.MainAxisAlignment.CENTER
                    ),
                    bgcolor=COLOR_WARNING_LIGHT,
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=10
                )

            # Блок с информацией о выдаче
            info_block = None
            if not is_available and taken_by:
                info_rows = [
                    ft.Row(
                        controls=[
                            ft.Icon(ft.CupertinoIcons.PERSON_FILL, size=14, color=COLOR_PRIMARY),
                            ft.Text(f"Кому: {taken_by}", size=13, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_DARK)
                        ],
                        spacing=6
                    )
                ]
                if phone:
                    info_rows.append(
                        ft.Row(
                            controls=[
                                ft.Icon(ft.CupertinoIcons.PHONE_FILL, size=13, color=COLOR_TEXT_MUTED),
                                ft.Text(phone, size=12, color=COLOR_TEXT_MUTED)
                            ],
                            spacing=6
                        )
                    )
                if taken_at or expected_return:
                    time_text = []
                    if taken_at:
                        time_text.append(f"Взят: {taken_at[-5:] if ' ' in taken_at else taken_at}")
                    if expected_return:
                        time_text.append(f"Срок: {expected_return}")
                    info_rows.append(
                        ft.Row(
                            controls=[
                                ft.Icon(ft.CupertinoIcons.CLOCK, size=13, color=COLOR_WARNING),
                                ft.Text(" • ".join(time_text), size=12, weight=ft.FontWeight.W_500, color=COLOR_TEXT_DARK)
                            ],
                            spacing=6
                        )
                    )

                info_block = ft.Container(
                    content=ft.Column(controls=info_rows, spacing=4),
                    bgcolor="#F8F9FB",
                    border=ft.border.all(1, "#EAECEF"),
                    border_radius=10,
                    padding=ft.padding.all(10),
                    margin=ft.margin.only(top=6, bottom=6)
                )

            # Кнопка действия
            if is_available:
                action_btn = ft.CupertinoButton(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.VPN_KEY_ROUNDED, size=16, color=COLOR_CARD),
                            ft.Text("Выдать ключ", size=13, weight=ft.FontWeight.BOLD, color=COLOR_CARD)
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=6
                    ),
                    bgcolor=COLOR_PRIMARY,
                    border_radius=12,
                    padding=ft.padding.symmetric(vertical=8, horizontal=14),
                    on_click=lambda e, k_item=k: open_issue_modal(k_item)
                )
            else:
                action_btn = ft.CupertinoButton(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.CupertinoIcons.CHECKMARK_CIRCLE_FILL, size=16, color=COLOR_PRIMARY),
                            ft.Text("Принять возврат", size=13, weight=ft.FontWeight.BOLD, color=COLOR_PRIMARY)
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=6
                    ),
                    bgcolor=COLOR_PRIMARY_LIGHT,
                    border_radius=12,
                    padding=ft.padding.symmetric(vertical=8, horizontal=14),
                    on_click=lambda e, k_id=key_id: handle_return_key(k_id)
                )

            # Сборка карточки ключа
            card_content = [
                # Верхняя строка: Номер кабинета + Бейдж статуса
                ft.Row(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Container(
                                    content=ft.Text(f"№ {key_id}", size=14, weight=ft.FontWeight.BOLD, color=COLOR_PRIMARY),
                                    bgcolor=COLOR_PRIMARY_LIGHT,
                                    border_radius=8,
                                    padding=ft.padding.symmetric(horizontal=8, vertical=4)
                                ),
                                ft.Text(f"{floor} этаж", size=12, color=COLOR_TEXT_MUTED)
                            ],
                            spacing=8
                        ),
                        status_badge
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                # Название кабинета
                ft.Container(
                    content=ft.Text(key_name, size=16, weight=ft.FontWeight.W_600, color=COLOR_TEXT_DARK),
                    padding=ft.padding.only(top=6, bottom=2)
                )
            ]

            # Примечание кабинета
            if notes and is_available:
                card_content.append(
                    ft.Text(f"ℹ️ {notes}", size=12, color=COLOR_TEXT_MUTED)
                )

            # Если выдан — добавляем блок держателя
            if info_block:
                card_content.append(info_block)

            # Кнопка действия
            card_content.append(
                ft.Container(content=action_btn, margin=ft.margin.only(top=6))
            )

            # Финальная карточка
            card = ft.Container(
                content=ft.Column(controls=card_content, spacing=4),
                bgcolor=COLOR_CARD,
                border_radius=16,
                padding=ft.padding.all(14),
                border=ft.border.all(1, COLOR_BORDER)
            )

            keys_list_view.controls.append(card)

        safe_update(keys_list_view)

    # Загрузка списка ключей из API
    def load_keys(show_error_toast: bool = False):
        ok, keys_data, err = api.get_keys(
            search=state["search_query"],
            filter_type=state["filter_type"]
        )
        if ok:
            update_network_indicator(True)
            state["keys"] = keys_data
            render_keys(keys_data, is_offline=False)
            load_stats()
        else:
            update_network_indicator(False, "Офлайн")
            render_keys([], is_offline=True)
            if show_error_toast:
                show_alert(err or "Не удалось подключиться к серверу", is_error=True)

    def on_search_changed(query: str):
        state["search_query"] = query
        load_keys(show_error_toast=False)

    # Быстрый возврат ключа
    def handle_return_key(key_id: str):
        ok, msg = api.return_key(key_id)
        if ok:
            show_alert(f"Ключ №{key_id} успешно возвращен!")
            load_keys(show_error_toast=True)
            if state["active_tab"] == 1:
                load_history()
        else:
            show_alert(msg, is_error=True)

    # Модальное окно выдачи ключа (iOS Action Dialog)
    def open_issue_modal(key_data: Dict[str, Any]):
        key_id = key_data.get("id", "")
        key_name = key_data.get("name", "")

        fio_input = ft.CupertinoTextField(
            placeholder_text="Иванов Алексей Сергеевич",
            bgcolor="#F8F9FB",
            border=ft.border.all(1, COLOR_BORDER),
            border_radius=10,
            padding=ft.padding.symmetric(vertical=10, horizontal=10),
            autofocus=True
        )

        dept_input = ft.CupertinoTextField(
            placeholder_text="Отдел IT / +7 (999) 000-00-00",
            bgcolor="#F8F9FB",
            border=ft.border.all(1, COLOR_BORDER),
            border_radius=10,
            padding=ft.padding.symmetric(vertical=10, horizontal=10)
        )

        time_input = ft.CupertinoTextField(
            placeholder_text="до 18:00 / до конца дня",
            value="до 18:00",
            bgcolor="#F8F9FB",
            border=ft.border.all(1, COLOR_BORDER),
            border_radius=10,
            padding=ft.padding.symmetric(vertical=10, horizontal=10)
        )

        # Быстрые кнопки сроков возврата
        def set_preset_time(time_val: str):
            time_input.value = time_val
            safe_update(time_input)

        time_chips = ft.Row(
            controls=[
                ft.CupertinoButton(
                    content=ft.Text("До 18:00", size=11, color=COLOR_PRIMARY),
                    bgcolor=COLOR_PRIMARY_LIGHT,
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=8,
                    on_click=lambda e: set_preset_time("до 18:00")
                ),
                ft.CupertinoButton(
                    content=ft.Text("До конца дня", size=11, color=COLOR_PRIMARY),
                    bgcolor=COLOR_PRIMARY_LIGHT,
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=8,
                    on_click=lambda e: set_preset_time("до конца дня")
                ),
                ft.CupertinoButton(
                    content=ft.Text("До завтра", size=11, color=COLOR_PRIMARY),
                    bgcolor=COLOR_PRIMARY_LIGHT,
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=8,
                    on_click=lambda e: set_preset_time("до завтра")
                )
            ],
            spacing=6
        )

        dialog = None

        def submit_issue(e):
            fio = fio_input.value.strip()
            if not fio:
                show_alert("Пожалуйста, укажите ФИО сотрудника", is_error=True)
                return

            ok, msg = api.issue_key(
                key_id=key_id,
                user_name=fio,
                phone=dept_input.value.strip() if dept_input.value else None,
                expected_return=time_input.value.strip() if time_input.value else None
            )

            if ok:
                page.close(dialog)
                show_alert(f"Ключ №{key_id} успешно выдан {fio}!")
                load_keys(show_error_toast=True)
                if state["active_tab"] == 1:
                    load_history()
            else:
                show_alert(msg, is_error=True)

        dialog = ft.AlertDialog(
            title=ft.Row(
                controls=[
                    ft.Icon(ft.Icons.VPN_KEY_ROUNDED, color=COLOR_PRIMARY, size=24),
                    ft.Text(f"Выдать ключ № {key_id}", size=18, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_DARK)
                ],
                spacing=8
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(key_name, size=13, color=COLOR_TEXT_MUTED),
                        ft.Divider(color=COLOR_BORDER, height=16),
                        ft.Text("ФИО сотрудника / посетителя *", size=12, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_DARK),
                        fio_input,
                        ft.Container(height=4),
                        ft.Text("Отдел или номер телефона", size=12, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_DARK),
                        dept_input,
                        ft.Container(height=4),
                        ft.Text("Срок сдачи ключа", size=12, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_DARK),
                        time_chips,
                        time_input
                    ],
                    spacing=6,
                    tight=True
                ),
                width=340
            ),
            actions=[
                ft.TextButton(
                    "Отмена",
                    on_click=lambda e: page.close(dialog)
                ),
                ft.CupertinoFilledButton(
                    text="Выдать ключ",
                    on_click=submit_issue
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )

        page.open(dialog)

    # Окно добавления нового кабинета
    def open_add_key_modal(e):
        id_input = ft.CupertinoTextField(placeholder_text="Например: 402", bgcolor="#F8F9FB", border=ft.border.all(1, COLOR_BORDER), border_radius=10)
        name_input = ft.CupertinoTextField(placeholder_text="Например: Кабинет директора", bgcolor="#F8F9FB", border=ft.border.all(1, COLOR_BORDER), border_radius=10)
        floor_input = ft.CupertinoTextField(value="1", keyboard_type=ft.KeyboardType.NUMBER, bgcolor="#F8F9FB", border=ft.border.all(1, COLOR_BORDER), border_radius=10)
        notes_input = ft.CupertinoTextField(placeholder_text="Оборудование или особенности", bgcolor="#F8F9FB", border=ft.border.all(1, COLOR_BORDER), border_radius=10)

        add_dialog = None

        def submit_add(e):
            k_id = id_input.value.strip()
            k_name = name_input.value.strip()
            try:
                floor = int(floor_input.value.strip())
            except ValueError:
                floor = 1

            if not k_id or not k_name:
                show_alert("Укажите номер и название кабинета", is_error=True)
                return

            ok, msg = api.add_key(key_id=k_id, name=k_name, floor=floor, notes=notes_input.value.strip())
            if ok:
                page.close(add_dialog)
                show_alert("Кабинет успешно добавлен!")
                load_keys(show_error_toast=True)
            else:
                show_alert(msg, is_error=True)

        add_dialog = ft.AlertDialog(
            title=ft.Row(
                controls=[
                    ft.Icon(ft.CupertinoIcons.ADD, color=COLOR_PRIMARY, size=24),
                    ft.Text("Новый кабинет", size=18, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_DARK)
                ],
                spacing=8
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Номер кабинета / ключа *", size=12, weight=ft.FontWeight.BOLD),
                        id_input,
                        ft.Text("Название помещения *", size=12, weight=ft.FontWeight.BOLD),
                        name_input,
                        ft.Text("Этаж", size=12, weight=ft.FontWeight.BOLD),
                        floor_input,
                        ft.Text("Примечания (оборудование)", size=12, weight=ft.FontWeight.BOLD),
                        notes_input
                    ],
                    spacing=6,
                    tight=True
                ),
                width=340
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: page.close(add_dialog)),
                ft.CupertinoFilledButton(text="Добавить", on_click=submit_add)
            ]
        )
        page.open(add_dialog)

    # Экран Истории (Журнал выдачи/возврата)
    def load_history():
        ok, history_data, err = api.get_history(limit=100)
        history_list_view.controls.clear()

        if not ok or not history_data:
            history_list_view.controls.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.CupertinoIcons.CLOCK, size=48, color=COLOR_TEXT_MUTED),
                            ft.Text("Журнал пуст", size=16, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_DARK),
                            ft.Text("Здесь будут отображаться все выдачи и возвраты ключей", size=13, color=COLOR_TEXT_MUTED, text_align=ft.TextAlign.CENTER)
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8
                    ),
                    padding=ft.padding.all(40),
                    alignment=ft.alignment.center
                )
            )
            safe_update(history_list_view)
            return

        for item in history_data:
            action = item.get("action", "")
            timestamp = item.get("timestamp", "")
            key_id = item.get("key_id", "")
            key_name = item.get("key_name", "")
            user_name = item.get("user_name", "")
            details = item.get("details", "")

            # Цвет и иконка в зависимости от действия
            if "Выдача" in action:
                icon_color = COLOR_WARNING
                badge_bg = COLOR_WARNING_LIGHT
                icon = ft.Icons.KEY_ROUNDED
            elif "Возврат" in action:
                icon_color = COLOR_SUCCESS
                badge_bg = COLOR_SUCCESS_LIGHT
                icon = ft.CupertinoIcons.CHECKMARK_CIRCLE_FILL
            else:
                icon_color = COLOR_PRIMARY
                badge_bg = COLOR_PRIMARY_LIGHT
                icon = ft.CupertinoIcons.INFO

            item_card = ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Container(
                                            content=ft.Icon(icon, size=16, color=icon_color),
                                            bgcolor=badge_bg,
                                            padding=ft.padding.all(6),
                                            border_radius=8
                                        ),
                                        ft.Column(
                                            controls=[
                                                ft.Text(action, size=14, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_DARK),
                                                ft.Text(f"Кабинет №{key_id} • {key_name}", size=12, color=COLOR_TEXT_MUTED)
                                            ],
                                            spacing=2
                                        )
                                    ],
                                    spacing=8
                                ),
                                ft.Text(timestamp, size=11, color=COLOR_TEXT_MUTED)
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.Container(height=2),
                        ft.Row(
                            controls=[
                                ft.Text(f"Сотрудник: {user_name}", size=13, weight=ft.FontWeight.W_600, color=COLOR_TEXT_DARK),
                            ]
                        ),
                        ft.Text(details, size=11, color=COLOR_TEXT_MUTED) if details else ft.Container()
                    ],
                    spacing=4
                ),
                bgcolor=COLOR_CARD,
                border_radius=14,
                padding=ft.padding.all(12),
                border=ft.border.all(1, COLOR_BORDER)
            )
            history_list_view.controls.append(item_card)

        safe_update(history_list_view)

    # Экран настроек подключения к серверу
    server_input = ft.CupertinoTextField(
        value=api.base_url,
        placeholder_text="http://192.168.1.50:8000",
        bgcolor=COLOR_CARD,
        border=ft.border.all(1, COLOR_BORDER),
        border_radius=12,
        padding=ft.padding.symmetric(vertical=10, horizontal=10)
    )

    server_status_text = ft.Text("", size=13, color=COLOR_TEXT_MUTED)

    def test_server_connection(e):
        url = server_input.value.strip()
        if not url:
            show_alert("Введите адрес сервера", is_error=True)
            return

        api.set_base_url(url)
        ok, msg = api.check_health()
        if ok:
            update_network_indicator(True)
            server_status_text.value = " Подключение к API успешно установлено!"
            server_status_text.color = COLOR_SUCCESS
            show_alert("Связь с сервером подтверждена!")
            load_keys(show_error_toast=True)
        else:
            update_network_indicator(False, "Ошибка")
            server_status_text.value = f"❌ {msg}"
            server_status_text.color = COLOR_DANGER
            show_alert(msg, is_error=True)
        safe_update(server_status_text)

    settings_view = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Настройки синхронизации", size=18, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_DARK),
                ft.Text("Для совместной работы с ПК-версией укажите адрес бэкенд-сервера FastAPI:", size=13, color=COLOR_TEXT_MUTED),
                ft.Container(height=6),
                ft.Text("Адрес сервера (REST API)", size=12, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_DARK),
                server_input,
                ft.Container(height=4),
                ft.CupertinoFilledButton(
                    text="Проверить подключение",
                    on_click=test_server_connection
                ),
                server_status_text,
                ft.Container(height=16),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("💡 Как подключить телефон к ПК-серверу:", size=13, weight=ft.FontWeight.BOLD, color=COLOR_PRIMARY),
                            ft.Text("1. Запустите сервер на ПК через `server/run_server.sh`.", size=12, color=COLOR_TEXT_DARK),
                            ft.Text("2. Убедитесь, что ПК и телефон подключены к одной Wi-Fi сети.", size=12, color=COLOR_TEXT_DARK),
                            ft.Text("3. Введите локальный IP вашего компьютера (например: `http://192.168.1.45:8000`).", size=12, color=COLOR_TEXT_DARK),
                            ft.Text("4. Все выдачи и возвраты ключей будут синхронизироваться мгновенно!", size=12, color=COLOR_TEXT_DARK)
                        ],
                        spacing=6
                    ),
                    bgcolor=COLOR_PRIMARY_LIGHT,
                    padding=ft.padding.all(14),
                    border_radius=12
                )
            ],
            spacing=10
        ),
        padding=ft.padding.all(20),
        expand=True
    )

    # Основная область контента (вкладки)
    content_area = ft.Container(expand=True)

    def switch_tab(tab_index: int):
        state["active_tab"] = tab_index
        if tab_index == 0:
            content_area.content = ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                stats_row,
                                search_field,
                                segment_control
                            ],
                            spacing=10
                        ),
                        padding=ft.padding.symmetric(horizontal=16, vertical=8)
                    ),
                    keys_list_view
                ],
                expand=True,
                spacing=0
            )
            load_keys(show_error_toast=False)
        elif tab_index == 1:
            content_area.content = ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Text("Журнал операций", size=20, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_DARK),
                                ft.IconButton(
                                    icon=ft.CupertinoIcons.REFRESH,
                                    icon_color=COLOR_PRIMARY,
                                    tooltip="Обновить",
                                    on_click=lambda e: load_history()
                                )
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        padding=ft.padding.symmetric(horizontal=16, vertical=12)
                    ),
                    history_list_view
                ],
                expand=True,
                spacing=0
            )
            load_history()
        elif tab_index == 2:
            content_area.content = settings_view

        safe_update(content_area)

    # Нижняя навигационная панель (iOS Tab Bar)
    nav_bar = ft.NavigationBar(
        selected_index=0,
        bgcolor=COLOR_CARD,
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.VPN_KEY_OUTLINED,
                selected_icon=ft.Icons.VPN_KEY_ROUNDED,
                label="Ключи"
            ),
            ft.NavigationBarDestination(
                icon=ft.CupertinoIcons.CLOCK,
                selected_icon=ft.CupertinoIcons.CLOCK_FILL,
                label="История"
            ),
            ft.NavigationBarDestination(
                icon=ft.CupertinoIcons.SETTINGS,
                selected_icon=ft.CupertinoIcons.SETTINGS_SOLID,
                label="Сервер"
            )
        ],
        on_change=lambda e: switch_tab(e.control.selected_index)
    )

    # Верхний AppBar (в стиле iOS Large Title)
    header = ft.Container(
        content=ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text("Key Tracker", size=22, weight=ft.FontWeight.BOLD, color=COLOR_TEXT_DARK),
                        ft.Text("Ресепшн • Выдача ключей", size=12, color=COLOR_TEXT_MUTED)
                    ],
                    spacing=2
                ),
                ft.Row(
                    controls=[
                        connection_indicator,
                        ft.IconButton(
                            icon=ft.CupertinoIcons.ADD_CIRCLED_SOLID,
                            icon_color=COLOR_PRIMARY,
                            icon_size=28,
                            tooltip="Добавить кабинет",
                            on_click=open_add_key_modal
                        ),
                        ft.IconButton(
                            icon=ft.CupertinoIcons.REFRESH,
                            icon_color=COLOR_TEXT_MUTED,
                            icon_size=22,
                            tooltip="Обновить данные",
                            on_click=lambda e: load_keys(show_error_toast=True)
                        )
                    ],
                    spacing=2
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        ),
        bgcolor=COLOR_CARD,
        padding=ft.padding.only(left=16, right=8, top=14, bottom=10),
        border=ft.border.only(bottom=ft.BorderSide(1, COLOR_BORDER))
    )

    # Инициализируем содержимое первой вкладки
    content_area.content = ft.Column(
        controls=[
            ft.Container(
                content=ft.Column(
                    controls=[
                        stats_row,
                        search_field,
                        segment_control
                    ],
                    spacing=10
                ),
                padding=ft.padding.symmetric(horizontal=16, vertical=8)
            ),
            keys_list_view
        ],
        expand=True,
        spacing=0
    )

    # Корневой лэйаут приложения
    page.add(
        ft.Column(
            controls=[
                header,
                content_area,
                nav_bar
            ],
            expand=True,
            spacing=0
        )
    )
    page.update()

    # Загружаем данные
    load_keys(show_error_toast=False)

if __name__ == "__main__":
    ft.app(target=main)
