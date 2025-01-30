import sqlite3
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import clipboard
import os


class ImprovedPartsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Учет запчастей")
        self.root.geometry("1400x700")

        self.current_db = None  # Текущая база данных
        self.create_widgets()
        self.setup_context_menu()

        # При запуске программы предлагаем создать или открыть базу данных
        self.prompt_create_or_open_db()

    def save_part(self, values):
        """Сохраняет запчасть в базу данных"""
        if not self.current_db:
            messagebox.showwarning("Ошибка", "Сначала создайте или откройте базу данных")
            return

        conn = sqlite3.connect(self.current_db)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO parts (name, part_number, quantity, price, supplier, description, date_added)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', values)
            conn.commit()
            messagebox.showinfo("Успех", "Запчасть успешно добавлена")
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка БД", f"Не удалось добавить запчасть: {str(e)}")
        finally:
            conn.close()
        self.load_data()  # Обновляем таблицу после добавления

    def search_parts(self):
        """Поиск запчастей по введенному тексту"""
        search_term = self.search_entry.get().strip()
        if search_term:
            self.load_data(search_term)
        else:
            self.load_data()

    def prompt_create_or_open_db(self):
        """Предлагает пользователю создать новую базу данных или открыть существующую"""
        choice = messagebox.askyesnocancel(
            "База данных",
            "Открыть существующую базу данных? (Нет — создать новую)"
        )
        if choice is None:  # Пользователь нажал "Отмена"
            self.root.destroy()
        elif choice:  # Пользователь выбрал "Открыть"
            self.open_database()
        else:  # Пользователь выбрал "Создать"
            self.save_database_as()

    def create_db(self):
        """Создает новую базу данных, если она не существует"""
        if self.current_db and not os.path.exists(self.current_db):
            conn = sqlite3.connect(self.current_db)
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS parts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        part_number TEXT UNIQUE,
                        quantity INTEGER,
                        price REAL,
                        supplier TEXT,
                        description TEXT,
                        date_added TEXT
                    )
                ''')
                conn.commit()
            except sqlite3.Error as e:
                messagebox.showerror("Ошибка БД", str(e))
            finally:
                conn.close()

    def delete_part(self):
        """Удаляет выбранную запчасть из базы данных"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Ошибка", "Выберите запчасть для удаления")
            return

        part_id = self.tree.item(selected[0], 'values')[0]  # Получаем ID выбранной записи

        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить эту запчасть?"):
            conn = sqlite3.connect(self.current_db)
            cursor = conn.cursor()
            try:
                cursor.execute('DELETE FROM parts WHERE id = ?', (part_id,))
                conn.commit()
                messagebox.showinfo("Успех", "Запчасть успешно удалена")
            except sqlite3.Error as e:
                messagebox.showerror("Ошибка БД", f"Не удалось удалить запчасть: {str(e)}")
            finally:
                conn.close()
            self.load_data()  # Обновляем таблицу после удаления

    def paste_row(self, event=None):
        try:
            pasted_data = (clipboard.paste() or self.root.clipboard_get()).split('\t')

            if len(pasted_data) >= 7:
                # Обработка числовых полей
                pasted_data[2] = int(float(pasted_data[2]))  # quantity
                pasted_data[3] = float(pasted_data[3])  # price

                dialog = AddEditDialog(self.root, pasted_data)
                self.root.wait_window(dialog.top)
                if dialog.values:
                    self.save_part(dialog.values)
                    self.load_data()
        except Exception as e:
            messagebox.showerror("Ошибка вставки", f"Некорректные данные: {str(e)}")

    def copy_search_text(self, event=None):
        text = self.search_entry.get()
        if text:
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                clipboard.copy(text)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось скопировать: {str(e)}")

    def paste_to_search(self, event=None):
        try:
            text = clipboard.paste() or self.root.clipboard_get()
            if text:
                self.search_entry.delete(0, tk.END)
                self.search_entry.insert(0, text)
                self.search_parts()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось вставить: {str(e)}")

    def copy_row(self, event=None):
        selected = self.tree.selection()
        if selected:
            try:
                values = self.tree.item(selected[0], 'values')
                text = '\t'.join(map(str, values))

                self.root.clipboard_clear()
                self.root.clipboard_append(text)
                clipboard.copy(text)
            except Exception as e:
                messagebox.showerror("Ошибка копирования", str(e))

    def edit_part(self):
        """Редактирует выбранную запчасть"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Ошибка", "Выберите запчасть для редактирования")
            return

        part_id = self.tree.item(selected[0], 'values')[0]  # Получаем ID выбранной записи

        conn = sqlite3.connect(self.current_db)
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM parts WHERE id = ?', (part_id,))
            part = cursor.fetchone()
            dialog = AddEditDialog(self.root, part)
            self.root.wait_window(dialog.top)
            if dialog.values:
                self.update_part(part_id, dialog.values)
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка БД", f"Не удалось загрузить данные: {str(e)}")
        finally:
            conn.close()

    def update_part(self, part_id, values):
        """Обновляет запчасть в базе данных"""
        conn = sqlite3.connect(self.current_db)
        try:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE parts SET
                    name = ?,
                    part_number = ?,
                    quantity = ?,
                    price = ?,
                    supplier = ?,
                    description = ?,
                    date_added = ?
                WHERE id = ?
            ''', (*values, part_id))
            conn.commit()
            self.load_data()
            messagebox.showinfo("Успех", "Изменения сохранены")
        except sqlite3.IntegrityError:
            messagebox.showerror("Ошибка", "Артикул должен быть уникальным!")
        finally:
            conn.close()

    def create_widgets(self):
        # Меню
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Открыть", command=self.open_database)
        filemenu.add_command(label="Сохранить как...", command=self.save_database_as)
        menubar.add_cascade(label="Файл", menu=filemenu)
        self.root.config(menu=menubar)

        # Панель инструментов
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        buttons = [
            ("Добавить", self.add_part),
            ("Редактировать", self.edit_part),
            ("Удалить", self.delete_part),
            ("Копировать строку", self.copy_row),
            ("Вставить строку", self.paste_row),
            ("Обновить", self.load_data)
        ]

        for text, command in buttons:
            ttk.Button(toolbar, text=text, command=command).pack(side=tk.LEFT, padx=2)

        # Поиск
        search_frame = ttk.Frame(self.root)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        # Кнопки для поля поиска
        ttk.Button(search_frame, text="⌨", command=self.copy_search_text, width=3).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(search_frame, text="📋", command=self.paste_to_search, width=3).pack(side=tk.LEFT, padx=(0, 2))
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(search_frame, text="Поиск", command=self.search_parts).pack(side=tk.LEFT, padx=2)

        self.search_entry.bind("<Control-c>", lambda e: self.copy_search_text())
        self.search_entry.bind("<Control-v>", lambda e: self.paste_to_search())
        self.search_entry.bind("<Control-C>", lambda e: self.copy_search_text())
        self.search_entry.bind("<Control-V>", lambda e: self.paste_to_search())

        # Таблица
        columns = [
            ('ID', 50),
            ('Название', 150),
            ('Артикул', 100),
            ('Количество', 80),
            ('Цена', 80),
            ('Поставщик', 150),
            ('Описание', 250),
            ('Дата добавления', 120)
        ]

        self.tree = ttk.Treeview(
            self.root,
            columns=[col[0] for col in columns],
            show='headings'
        )

        for col, width in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor=tk.CENTER)

        scroll = ttk.Scrollbar(self.root, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

    def setup_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Копировать", command=self.copy_row)
        self.context_menu.add_command(label="Вставить", command=self.paste_row)
        self.tree.bind("<Button-3>", self.show_context_menu)

        self.root.bind_all("<Control-KeyPress>", self.check_hotkeys)

    def check_hotkeys(self, event):
        keycode = event.keycode
        ctrl = (event.state & 0x4) != 0

        if ctrl:
            if keycode == 54:  # C
                self.copy_row()
            elif keycode == 55:  # V
                self.paste_row()

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.context_menu.tk_popup(event.x_root, event.y_root)

    def load_data(self, search_term=None):
        if not self.current_db:
            messagebox.showwarning("Ошибка", "База данных не выбрана")
            return

        self.tree.delete(*self.tree.get_children())  # Очистить дерево

        conn = sqlite3.connect(self.current_db)
        try:
            cursor = conn.cursor()

            # Проверка существования таблицы parts
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='parts'")
            if not cursor.fetchone():
                messagebox.showwarning("Ошибка", "Таблица 'parts' не найдена в базе данных")
                return

            if search_term:
                cursor.execute('''
                    SELECT * FROM parts 
                    WHERE name LIKE ? 
                    OR part_number LIKE ? 
                    OR description LIKE ?
                 ''', (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))
            else:
                cursor.execute('SELECT * FROM parts')

            for row in cursor.fetchall():
                self.tree.insert('', tk.END, values=row)  # Добавить найденные данные в дерево
        finally:
            conn.close()

    def open_database(self):
        """Открывает выбранную базу данных"""
        file_path = filedialog.askopenfilename(
            filetypes=[("Базы данных", "*.db"), ("Все файлы", "*.*")]
        )
        if file_path:
            try:
                conn = sqlite3.connect(file_path)
                cursor = conn.cursor()

                # Проверка существования таблицы parts
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='parts'")
                if not cursor.fetchone():
                    # Если таблица отсутствует, создаем её
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS parts (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL,
                            part_number TEXT UNIQUE,
                            quantity INTEGER,
                            price REAL,
                            supplier TEXT,
                            description TEXT,
                            date_added TEXT
                        )
                    ''')
                    conn.commit()

                conn.close()
                self.current_db = file_path
                self.load_data()
                messagebox.showinfo("Успех", "База данных успешно загружена")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось открыть базу:\n{str(e)}")

    def save_database_as(self):
        """Создает новую базу данных и сохраняет ее"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("Базы данных", "*.db"), ("Все файлы", "*.*")]
        )
        if file_path:
            try:
                # Создаем пустую базу данных
                conn = sqlite3.connect(file_path)
                cursor = conn.cursor()

                # Создаем таблицу parts
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS parts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        part_number TEXT UNIQUE,
                        quantity INTEGER,
                        price REAL,
                        supplier TEXT,
                        description TEXT,
                        date_added TEXT
                    )
                ''')
                conn.commit()
                conn.close()

                self.current_db = file_path
                self.load_data()
                messagebox.showinfo("Успех", f"Новая база данных создана:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при создании базы:\n{str(e)}")


    def add_part(self):
        """Добавляет новую запчасть"""
        if not self.current_db:
            messagebox.showwarning("Ошибка", "Сначала создайте или откройте базу данных")
            return

        dialog = AddEditDialog(self.root)
        self.root.wait_window(dialog.top)
        if dialog.values:
            self.save_part(dialog.values)


class AddEditDialog:
    def __init__(self, parent, part=None):
        self.top = tk.Toplevel(parent)
        self.top.title("Добавить запчасть" if not part else "Редактировать запчасть")
        self.values = None

        fields = [
            ('Название', 'name'),
            ('Артикул', 'part_number'),
            ('Количество', 'quantity'),
            ('Цена', 'price'),
            ('Поставщик', 'supplier'),
            ('Описание', 'description')
        ]

        self.entries = {}
        for i, (label, field) in enumerate(fields):
            ttk.Label(self.top, text=f"{label}:").grid(row=i, column=0, padx=5, pady=5, sticky=tk.E)
            if field == 'description':
                entry = tk.Text(self.top, height=4, width=30)
            else:
                entry = ttk.Entry(self.top)
            entry.grid(row=i, column=1, padx=5, pady=5, sticky=tk.W + tk.E)
            self.entries[field] = entry

            if part:
                if isinstance(part, (tuple, list)):
                    value_index = i + 1 if field != 'description' else 6
                    value = part[value_index] if len(part) > value_index else ''
                else:
                    value = part.get(field, '')

                if isinstance(entry, ttk.Entry):
                    entry.insert(0, str(value))
                else:
                    entry.insert('1.0', str(value))

        btn_frame = ttk.Frame(self.top)
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=10)

        ttk.Button(btn_frame, text="Сохранить", command=self.save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Отмена", command=self.top.destroy).pack(side=tk.LEFT, padx=5)

    def save(self):
        try:
            description = self.entries['description'].get("1.0", "end-1c") if isinstance(
                self.entries['description'], tk.Text) else self.entries['description'].get()

            values = (
                self.entries['name'].get(),
                self.entries['part_number'].get(),
                int(self.entries['quantity'].get()),
                float(self.entries['price'].get()),
                self.entries['supplier'].get(),
                description,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            self.values = values
            self.top.destroy()
        except ValueError as e:
            messagebox.showerror("Ошибка", f"Некорректные данные: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImprovedPartsApp(root)
    root.mainloop()
