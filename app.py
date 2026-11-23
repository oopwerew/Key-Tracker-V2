import platform
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from storage import KeyStorage

# Настройка глобальной темы CustomTkinter
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

# Шрифты в стиле iOS
SYSTEM_OS = platform.system()
FONT_FAMILY = "SF Pro Display" if SYSTEM_OS == "Darwin" else "Segoe UI"
FONT_BOLD = (FONT_FAMILY, 15, "bold")
FONT_TITLE = (FONT_FAMILY, 22, "bold")
FONT_SUBTITLE = (FONT_FAMILY, 13)
FONT_BODY = (FONT_FAMILY, 13)
FONT_CARD_TITLE = (FONT_FAMILY, 18, "bold")
FONT_BADGE = (FONT_FAMILY, 11, "bold")

# Палитра iOS White & Blue
COLOR_BG = "#F2F2F7"           # Мягкий фон экрана (iOS System Grouped Background)
COLOR_CARD = "#FFFFFF"         # Чистый белый фон карточек
COLOR_PRIMARY = "#007AFF"      # iOS Синий (Accent)
COLOR_PRIMARY_HOVER = "#0062CC"
COLOR_SECONDARY = "#E5E5EA"    # Разделители и обводка
COLOR_TEXT_DARK = "#1C1C1E"    # Основной текст
COLOR_TEXT_MUTED = "#8E8E93"   # Второстепенный текст
COLOR_SUCCESS = "#34C759"      # iOS Зеленый (В наличии)
COLOR_WARNING = "#FF9500"      # iOS Оранжевый (Выдан)
COLOR_DANGER = "#FF3B30"       # iOS Красный (Удаление)

class KeyTrackerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.storage = KeyStorage()
        self.current_user_name = "Максим"
        self.current_role = "Пользователь"
        self.active_filter = "all"

        self.title("Key Tracker V2 — Учёт ключей")
        self.geometry("980x720")
        self.minsize(860, 600)
        self.configure(fg_color=COLOR_BG)

        self._build_ui()
        self.refresh_view()

    def _build_ui(self):
        # 1. Верхняя панель (iOS Navigation Bar)
        self.header_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=0, height=80)
        self.header_frame.pack(fill="x", side="top")
        self.header_frame.pack_propagate(False)

        # Логотип и заголовок
        title_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=25, pady=15)

        self.lbl_logo = ctk.CTkLabel(
            title_box,
            text="🔑 Key Tracker",
            font=FONT_TITLE,
            text_color=COLOR_PRIMARY
        )
        self.lbl_logo.pack(anchor="w")

        self.lbl_sub = ctk.CTkLabel(
            title_box,
            text="Система контроля и выдачи ключей по кабинетам",
            font=FONT_SUBTITLE,
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_sub.pack(anchor="w")

        # Сегментированный переключатель ролей (iOS Segmented Control)
        role_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        role_box.pack(side="right", padx=25, pady=18)

        self.role_switch = ctk.CTkSegmentedButton(
            role_box,
            values=["👤 Пользователь", "🛡 Администратор"],
            font=(FONT_FAMILY, 13, "bold"),
            selected_color=COLOR_PRIMARY,
            selected_hover_color=COLOR_PRIMARY_HOVER,
            unselected_color="#E5E5EA",
            unselected_hover_color="#D1D1D6",
            text_color=COLOR_TEXT_DARK,
            corner_radius=20,
            command=self._on_role_change
        )
        self.role_switch.set("👤 Пользователь")
        self.role_switch.pack()

        # 2. Основная рабочая область
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=25, pady=20)

    def _on_role_change(self, value):
        if "Администратор" in value:
            self.current_role = "Администратор"
        else:
            self.current_role = "Пользователь"
        self.refresh_view()

    def refresh_view(self):
        # Очищаем текущий контент
        for widget in self.main_container.winfo_children():
            widget.destroy()

        if self.current_role == "Пользователь":
            self._render_user_view()
        else:
            self._render_admin_view()

    # ==========================================
    #             ПОЛЬЗОВАТЕЛЬСКИЙ ЭКРАН
    # ==========================================
    def _render_user_view(self):
        # Верхняя панель поиска и пользователя
        top_bar = ctk.CTkFrame(self.main_container, fg_color=COLOR_CARD, corner_radius=16, height=70)
        top_bar.pack(fill="x", pady=(0, 15))
        top_bar.pack_propagate(False)

        # Текущий пользователь
        user_info_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        user_info_box.pack(side="left", padx=20, pady=12)

        ctk.CTkLabel(user_info_box, text="Вы вошли как:", font=FONT_SUBTITLE, text_color=COLOR_TEXT_MUTED).pack(anchor="w")
        
        self.ent_user = ctk.CTkEntry(
            user_info_box,
            width=180,
            height=30,
            font=(FONT_FAMILY, 13, "bold"),
            corner_radius=10,
            border_color=COLOR_SECONDARY,
            fg_color="#F2F2F7",
            text_color=COLOR_TEXT_DARK
        )
        self.ent_user.insert(0, self.current_user_name)
        self.ent_user.pack(anchor="w", pady=(2, 0))
        self.ent_user.bind("<FocusOut>", lambda e: self._save_user_name())

        # Поле поиска
        search_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        search_box.pack(side="left", padx=20, pady=15, fill="x", expand=True)

        self.search_entry = ctk.CTkEntry(
            search_box,
            placeholder_text="🔍 Поиск кабинета по номеру или названию...",
            height=38,
            font=FONT_BODY,
            corner_radius=12,
            border_color=COLOR_SECONDARY,
            fg_color="#F2F2F7",
            text_color=COLOR_TEXT_DARK
        )
        self.search_entry.pack(fill="x")
        self.search_entry.bind("<KeyRelease>", lambda e: self._render_keys_list())

        # Фильтр кнопок
        filter_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        filter_box.pack(side="right", padx=20, pady=15)

        self.btn_filter_all = ctk.CTkButton(
            filter_box, text="Все", width=70, height=34, corner_radius=17,
            font=FONT_BODY, fg_color=COLOR_PRIMARY if self.active_filter == "all" else "#E5E5EA",
            text_color="#FFFFFF" if self.active_filter == "all" else COLOR_TEXT_DARK,
            command=lambda: self._set_filter("all")
        )
        self.btn_filter_all.pack(side="left", padx=4)

        self.btn_filter_avail = ctk.CTkButton(
            filter_box, text="Свободные", width=100, height=34, corner_radius=17,
            font=FONT_BODY, fg_color=COLOR_PRIMARY if self.active_filter == "available" else "#E5E5EA",
            text_color="#FFFFFF" if self.active_filter == "available" else COLOR_TEXT_DARK,
            command=lambda: self._set_filter("available")
        )
        self.btn_filter_avail.pack(side="left", padx=4)

        # Контейнер со скроллом для карточек ключей
        self.scroll_frame = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent", corner_radius=0)
        self.scroll_frame.pack(fill="both", expand=True)

        self._render_keys_list()

    def _save_user_name(self):
        val = self.ent_user.get().strip()
        if val:
            self.current_user_name = val

    def _set_filter(self, filter_name):
        self.active_filter = filter_name
        self.refresh_view()

    def _render_keys_list(self):
        # Очистить список
        for w in self.scroll_frame.winfo_children():
            w.destroy()

        search_query = self.search_entry.get().strip() if hasattr(self, 'search_entry') else ""
        keys = self.storage.get_keys(search=search_query, filter_type=self.active_filter)

        if not keys:
            empty_box = ctk.CTkFrame(self.scroll_frame, fg_color=COLOR_CARD, corner_radius=16)
            empty_box.pack(fill="x", pady=40, padx=50)
            ctk.CTkLabel(empty_box, text="Кабинеты не найдены", font=FONT_BOLD, text_color=COLOR_TEXT_MUTED).pack(pady=30)
            return

        # Рисуем карточки
        for k in keys:
            self._create_user_key_card(k)

    def _create_user_key_card(self, key_data):
        card = ctk.CTkFrame(self.scroll_frame, fg_color=COLOR_CARD, corner_radius=16, height=100)
        card.pack(fill="x", pady=6, padx=5)
        card.pack_propagate(False)

        # Левая часть: Номер кабинета
        left_box = ctk.CTkFrame(card, fg_color="#F0F4FF", corner_radius=12, width=90, height=75)
        left_box.pack(side="left", padx=15, pady=12)
        left_box.pack_propagate(False)

        ctk.CTkLabel(
            left_box,
            text=f"№{key_data['id']}",
            font=FONT_CARD_TITLE,
            text_color=COLOR_PRIMARY
        ).pack(expand=True)

        # Центральная часть: Название, этаж, заметка
        center_box = ctk.CTkFrame(card, fg_color="transparent")
        center_box.pack(side="left", fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(
            center_box,
            text=key_data["name"],
            font=(FONT_FAMILY, 16, "bold"),
            text_color=COLOR_TEXT_DARK
        ).pack(anchor="w")

        info_text = f"Этаж: {key_data['floor']}  •  {key_data.get('notes', '')}"
        ctk.CTkLabel(
            center_box,
            text=info_text,
            font=FONT_SUBTITLE,
            text_color=COLOR_TEXT_MUTED
        ).pack(anchor="w", pady=(3, 0))

        # Правая часть: Статус и кнопка действия
        right_box = ctk.CTkFrame(card, fg_color="transparent")
        right_box.pack(side="right", padx=20, pady=15)

        is_available = key_data["status"] == "available"
        is_my_key = (key_data.get("taken_by") == self.current_user_name)

        if is_available:
            # Бейдж "В наличии"
            badge = ctk.CTkLabel(
                right_box,
                text="● В наличии",
                font=FONT_BADGE,
                text_color=COLOR_SUCCESS
            )
            badge.pack(side="left", padx=(0, 20))

            # Кнопка "Взять ключ"
            btn_take = ctk.CTkButton(
                right_box,
                text="Взять ключ",
                font=FONT_BOLD,
                width=130,
                height=38,
                corner_radius=19,
                fg_color=COLOR_PRIMARY,
                hover_color=COLOR_PRIMARY_HOVER,
                command=lambda k=key_data: self._user_take_key_click(k)
            )
            btn_take.pack(side="left")
        else:
            # Бейдж "Выдан"
            taken_text = f"Выдан: {key_data['taken_by']} ({key_data.get('taken_at', '')})"
            badge = ctk.CTkLabel(
                right_box,
                text=f"● {taken_text}",
                font=FONT_BADGE,
                text_color=COLOR_WARNING
            )
            badge.pack(side="left", padx=(0, 20))

            # Кнопка возврата активна, если этот ключ взял текущий пользователь
            btn_return = ctk.CTkButton(
                right_box,
                text="Вернуть ключ",
                font=FONT_BOLD,
                width=130,
                height=38,
                corner_radius=19,
                fg_color="#34C759" if is_my_key else "#C7C7CC",
                hover_color="#28A745" if is_my_key else "#C7C7CC",
                state="normal" if is_my_key else "disabled",
                command=lambda k=key_data: self._user_return_key_click(k)
            )
            btn_return.pack(side="left")

    def _user_take_key_click(self, key_data):
        self._save_user_name()
        user_name = self.current_user_name.strip()
        if not user_name:
            messagebox.showwarning("Внимание", "Пожалуйста, укажите ваше имя в поле сверху перед тем, как брать ключ!")
            return

        confirm = messagebox.askyesno(
            "Подтверждение",
            f"Вы уверены, что хотите взять ключ от кабинета №{key_data['id']} ({key_data['name']}) на имя «{user_name}»?"
        )
        if confirm:
            ok, msg = self.storage.take_key(key_data["id"], user_name)
            if ok:
                messagebox.showinfo("Успех", f"Ключ от кабинета №{key_data['id']} выдан вам. Не забудьте вернуть его после занятий!")
                self.refresh_view()
            else:
                messagebox.showerror("Ошибка", msg)

    def _user_return_key_click(self, key_data):
        confirm = messagebox.askyesno(
            "Возврат ключа",
            f"Вернуть ключ от кабинета №{key_data['id']} на вахту / в хранилище?"
        )
        if confirm:
            ok, msg = self.storage.return_key(key_data["id"])
            if ok:
                messagebox.showinfo("Успех", f"Ключ от кабинета №{key_data['id']} успешно возвращен!")
                self.refresh_view()
            else:
                messagebox.showerror("Ошибка", msg)


    # ==========================================
    #             ЭКРАН АДМИНИСТРАТОРА
    # ==========================================
    def _render_admin_view(self):
        stats = self.storage.get_stats()

        # 1. Виджеты статистики (iOS widgets)
        stats_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        stats_frame.pack(fill="x", pady=(0, 15))

        self._create_stat_card(stats_frame, "Всего кабинетов", str(stats["total"]), COLOR_PRIMARY, 0)
        self._create_stat_card(stats_frame, "В наличии (свободно)", str(stats["available"]), COLOR_SUCCESS, 1)
        self._create_stat_card(stats_frame, "На руках (выдано)", str(stats["taken"]), COLOR_WARNING, 2)

        # 2. Панель действий администратора
        action_bar = ctk.CTkFrame(self.main_container, fg_color=COLOR_CARD, corner_radius=16, height=60)
        action_bar.pack(fill="x", pady=(0, 15))
        action_bar.pack_propagate(False)

        ctk.CTkLabel(
            action_bar,
            text="Управление ключами и выдачей",
            font=FONT_BOLD,
            text_color=COLOR_TEXT_DARK
        ).pack(side="left", padx=20)

        # Кнопка "Журнал операций"
        btn_history = ctk.CTkButton(
            action_bar,
            text="📋 Журнал операций",
            font=FONT_BOLD,
            fg_color="#E5E5EA",
            hover_color="#D1D1D6",
            text_color=COLOR_TEXT_DARK,
            corner_radius=18,
            height=36,
            command=self._show_history_window
        )
        btn_history.pack(side="right", padx=(5, 20))

        # Кнопка "Добавить кабинет"
        btn_add = ctk.CTkButton(
            action_bar,
            text="+ Добавить кабинет",
            font=FONT_BOLD,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            corner_radius=18,
            height=36,
            command=self._show_add_key_dialog
        )
        btn_add.pack(side="right", padx=5)

        # 3. Список кабинетов для админа
        self.admin_scroll = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        self.admin_scroll.pack(fill="both", expand=True)

        keys = self.storage.get_keys()
        for k in keys:
            self._create_admin_key_card(k)

    def _create_stat_card(self, parent, title, value, accent_color, col_idx):
        card = ctk.CTkFrame(parent, fg_color=COLOR_CARD, corner_radius=16, height=85)
        card.pack(side="left", fill="both", expand=True, padx=6 if col_idx == 1 else 0)
        card.pack_propagate(False)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(expand=True, pady=10)

        ctk.CTkLabel(inner, text=value, font=(FONT_FAMILY, 26, "bold"), text_color=accent_color).pack()
        ctk.CTkLabel(inner, text=title, font=FONT_SUBTITLE, text_color=COLOR_TEXT_MUTED).pack()

    def _create_admin_key_card(self, key_data):
        card = ctk.CTkFrame(self.admin_scroll, fg_color=COLOR_CARD, corner_radius=16, height=90)
        card.pack(fill="x", pady=5, padx=2)
        card.pack_propagate(False)

        # Номер
        left_box = ctk.CTkFrame(card, fg_color="#F0F4FF", corner_radius=12, width=80, height=65)
        left_box.pack(side="left", padx=15, pady=12)
        left_box.pack_propagate(False)

        ctk.CTkLabel(left_box, text=f"№{key_data['id']}", font=FONT_CARD_TITLE, text_color=COLOR_PRIMARY).pack(expand=True)

        # Описание
        center_box = ctk.CTkFrame(card, fg_color="transparent")
        center_box.pack(side="left", fill="both", expand=True, padx=10, pady=12)

        ctk.CTkLabel(center_box, text=key_data["name"], font=(FONT_FAMILY, 15, "bold"), text_color=COLOR_TEXT_DARK).pack(anchor="w")

        status_str = f"Этаж {key_data['floor']}  •  "
        if key_data["status"] == "available":
            status_str += "В наличии"
            status_color = COLOR_SUCCESS
        else:
            status_str += f"На руках у: {key_data['taken_by']} (с {key_data.get('taken_at', '')})"
            status_color = COLOR_WARNING

        ctk.CTkLabel(center_box, text=status_str, font=FONT_SUBTITLE, text_color=status_color).pack(anchor="w", pady=(3, 0))

        # Действия админа
        right_box = ctk.CTkFrame(card, fg_color="transparent")
        right_box.pack(side="right", padx=15, pady=15)

        if key_data["status"] == "available":
            # Выдать кому-то
            btn_issue = ctk.CTkButton(
                right_box,
                text="Выдать",
                font=FONT_BODY,
                width=90,
                height=34,
                corner_radius=17,
                fg_color=COLOR_PRIMARY,
                hover_color=COLOR_PRIMARY_HOVER,
                command=lambda k=key_data: self._admin_issue_dialog(k)
            )
            btn_issue.pack(side="left", padx=4)
        else:
            # Принять возврат
            btn_accept = ctk.CTkButton(
                right_box,
                text="Принять возврат",
                font=FONT_BODY,
                width=130,
                height=34,
                corner_radius=17,
                fg_color=COLOR_SUCCESS,
                hover_color="#28A745",
                command=lambda k=key_data: self._admin_force_return(k)
            )
            btn_accept.pack(side="left", padx=4)

        # Удалить
        btn_del = ctk.CTkButton(
            right_box,
            text="✕",
            font=FONT_BOLD,
            width=36,
            height=34,
            corner_radius=17,
            fg_color="#F2F2F7",
            hover_color="#FFE5E5",
            text_color=COLOR_DANGER,
            command=lambda k=key_data: self._admin_delete_key(k)
        )
        btn_del.pack(side="left", padx=4)

    def _admin_issue_dialog(self, key_data):
        dialog = ctk.CTkInputDialog(
            text=f"Кому выдать ключ от кабинета №{key_data['id']} ({key_data['name']})?\nВведите ФИО или должность:",
            title="Выдача ключа"
        )
        name = dialog.get_input()
        if name and name.strip():
            ok, msg = self.storage.take_key(key_data["id"], name.strip())
            if ok:
                messagebox.showinfo("Готово", f"Ключ от кабинета №{key_data['id']} выдан: {name.strip()}")
                self.refresh_view()
            else:
                messagebox.showerror("Ошибка", msg)

    def _admin_force_return(self, key_data):
        confirm = messagebox.askyesno(
            "Подтверждение",
            f"Принять ключ от кабинета №{key_data['id']} обратно в хранилище?"
        )
        if confirm:
            self.storage.return_key(key_data["id"])
            self.refresh_view()

    def _admin_delete_key(self, key_data):
        confirm = messagebox.askyesno(
            "Удаление кабинета",
            f"Вы действительно хотите удалить кабинет №{key_data['id']} ({key_data['name']}) из системы?"
        )
        if confirm:
            self.storage.delete_key(key_data["id"])
            self.refresh_view()

    def _show_add_key_dialog(self):
        # Модальное окно добавления кабинета в стиле iOS
        dlg = ctk.CTkToplevel(self)
        dlg.title("Добавить новый кабинет")
        dlg.geometry("450x420")
        dlg.configure(fg_color=COLOR_CARD)
        dlg.resizable(False, False)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="Новый кабинет / ключ", font=FONT_TITLE, text_color=COLOR_PRIMARY).pack(pady=(20, 15))

        # Поле: Номер
        ctk.CTkLabel(dlg, text="Номер кабинета:", font=FONT_BOLD, text_color=COLOR_TEXT_DARK).pack(anchor="w", padx=30)
        ent_num = ctk.CTkEntry(dlg, placeholder_text="например, 405", font=FONT_BODY, corner_radius=10, height=36)
        ent_num.pack(fill="x", padx=30, pady=(4, 12))

        # Поле: Название
        ctk.CTkLabel(dlg, text="Название кабинета:", font=FONT_BOLD, text_color=COLOR_TEXT_DARK).pack(anchor="w", padx=30)
        ent_name = ctk.CTkEntry(dlg, placeholder_text="например, Лаборатория робототехники", font=FONT_BODY, corner_radius=10, height=36)
        ent_name.pack(fill="x", padx=30, pady=(4, 12))

        # Поле: Этаж
        ctk.CTkLabel(dlg, text="Этаж:", font=FONT_BOLD, text_color=COLOR_TEXT_DARK).pack(anchor="w", padx=30)
        ent_floor = ctk.CTkEntry(dlg, placeholder_text="например, 4", font=FONT_BODY, corner_radius=10, height=36)
        ent_floor.pack(fill="x", padx=30, pady=(4, 12))

        # Поле: Заметка
        ctk.CTkLabel(dlg, text="Примечание (оборудование, доступ):", font=FONT_BOLD, text_color=COLOR_TEXT_DARK).pack(anchor="w", padx=30)
        ent_notes = ctk.CTkEntry(dlg, placeholder_text="например, 20 ноутбуков", font=FONT_BODY, corner_radius=10, height=36)
        ent_notes.pack(fill="x", padx=30, pady=(4, 20))

        def on_save():
            num = ent_num.get().strip()
            name = ent_name.get().strip()
            floor = ent_floor.get().strip() or "1"
            notes = ent_notes.get().strip()

            if not num or not name:
                messagebox.showwarning("Ошибка", "Номер и название кабинета обязательны для заполнения!")
                return

            ok, msg = self.storage.add_key(num, name, floor, notes)
            if ok:
                dlg.destroy()
                self.refresh_view()
            else:
                messagebox.showerror("Ошибка", msg)

        btn_save = ctk.CTkButton(
            dlg,
            text="Сохранить",
            font=FONT_BOLD,
            height=40,
            corner_radius=20,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            command=on_save
        )
        btn_save.pack(fill="x", padx=30, pady=10)

    def _show_history_window(self):
        win = ctk.CTkToplevel(self)
        win.title("Журнал операций (История выдачи и возвратов)")
        win.geometry("680x520")
        win.configure(fg_color=COLOR_BG)
        win.grab_set()

        header = ctk.CTkFrame(win, fg_color=COLOR_CARD, corner_radius=0, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(header, text="📋 Журнал истории операций", font=FONT_TITLE, text_color=COLOR_PRIMARY).pack(side="left", padx=20, pady=15)

        scroll = ctk.CTkScrollableFrame(win, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=15)

        history = self.storage.get_history()
        if not history:
            ctk.CTkLabel(scroll, text="История пока пуста", font=FONT_BOLD, text_color=COLOR_TEXT_MUTED).pack(pady=40)
            return

        for item in history:
            row = ctk.CTkFrame(scroll, fg_color=COLOR_CARD, corner_radius=12, height=60)
            row.pack(fill="x", pady=4)
            row.pack_propagate(False)

            # Дата/время
            ctk.CTkLabel(
                row,
                text=item["timestamp"],
                font=(FONT_FAMILY, 12),
                text_color=COLOR_TEXT_MUTED,
                width=130
            ).pack(side="left", padx=10)

            # Действие
            action = item["action"]
            color = COLOR_SUCCESS if "Возврат" in action else COLOR_PRIMARY
            ctk.CTkLabel(
                row,
                text=action,
                font=(FONT_FAMILY, 12, "bold"),
                text_color=color,
                width=140
            ).pack(side="left", padx=5)

            # Детали
            details = f"Каб. №{item['key_id']}  ({item.get('key_name', '')})  •  {item.get('user_name', '')}"
            ctk.CTkLabel(
                row,
                text=details,
                font=(FONT_FAMILY, 13),
                text_color=COLOR_TEXT_DARK
            ).pack(side="left", padx=10)


if __name__ == "__main__":
    app = KeyTrackerApp()
    app.mainloop()
