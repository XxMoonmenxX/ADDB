import sqlite3
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
import clipboard

DATABASE_NAME = 'parts_inventory.db'


class ImprovedPartsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("учет запчастей")
        self.root.geometry("1400x700")

        self.create_db()
        self.create_widgets()
        self.load_data()
        self.setup_context_menu()

    def create_db(self):
        conn = sqlite3.connect(DATABASE_NAME)
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

    def create_widgets(self):
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

        # Поиск с кнопками буфера
        search_frame = ttk.Frame(self.root)
        search_frame.pack(fill=tk.X, padx=5, pady=5)

        # Кнопки для поля поиска
        ttk.Button(search_frame, text="⌨", command=self.copy_search_text, width=3).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(search_frame, text="📋", command=self.paste_to_search, width=3).pack(side=tk.LEFT, padx=(0, 2))

        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(search_frame, text="Поиск", command=self.search_parts).pack(side=tk.LEFT, padx=2)

        # Горячие клавиши для поля поиска
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
            self.tree.column(col, width=width, anchor=tk.W)

        scroll = ttk.Scrollbar(self.root, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

    def setup_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Копировать", command=self.copy_row)
        self.context_menu.add_command(label="Вставить", command=self.paste_row)
        self.tree.bind("<Button-3>", self.show_context_menu)

        # Обработка горячих клавиш для любой раскладки
        self.root.bind_all("<Control-KeyPress>", self.check_hotkeys)

    def check_hotkeys(self, event):
        keycode = event.keycode
        ctrl = (event.state & 0x4) != 0

        if ctrl:
            if keycode == 54:  # Физическая клавиша C
                self.copy_row()
            elif keycode == 55:  # Физическая клавиша V
                self.paste_row()

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.context_menu.tk_popup(event.x_root, event.y_root)

    def load_data(self, search_term=None):
        self.tree.delete(*self.tree.get_children())
        conn = sqlite3.connect(DATABASE_NAME)
        try:
            cursor = conn.cursor()
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
                self.tree.insert('', tk.END, values=row)
        finally:
            conn.close()

    def add_part(self):
        dialog = AddEditDialog(self.root)
        self.root.wait_window(dialog.top)
        if dialog.values:
            self.save_part(dialog.values)

    def edit_part(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Ошибка", "Выберите запчасть для редактирования")
            return

        part_id = self.tree.item(selected[0], 'values')[0]
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM parts WHERE id = ?', (part_id,))
        part = cursor.fetchone()
        conn.close()

        dialog = AddEditDialog(self.root, part)
        self.root.wait_window(dialog.top)
        if dialog.values:
            self.update_part(part_id, dialog.values)

    def delete_part(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Ошибка", "Выберите запчасть для удаления")
            return

        if messagebox.askyesno("Подтверждение", "Удалить выбранную запчасть?"):
            part_id = self.tree.item(selected[0], 'values')[0]
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM parts WHERE id = ?', (part_id,))
            conn.commit()
            conn.close()
            self.load_data()

    def search_parts(self):
        search_term = self.search_entry.get()
        self.load_data(search_term)

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

    def save_part(self, values):
        conn = sqlite3.connect(DATABASE_NAME)
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO parts (
                    name, part_number, quantity, 
                    price, supplier, description, date_added
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', values)
            conn.commit()
            self.load_data()
            messagebox.showinfo("Успех", "Данные сохранены!")
        except sqlite3.IntegrityError:
            messagebox.showerror("Ошибка", "Артикул должен быть уникальным!")
        finally:
            conn.close()

    def update_part(self, part_id, values):
        conn = sqlite3.connect(DATABASE_NAME)
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