
import tkinter as tk
from database import init_database, seed_data
from ui import LoginForm


if __name__ == "__main__":
    # Инициализация базы данных
    init_database()
    seed_data()
    
    # Запуск приложения
    root = tk.Tk()
    LoginForm(root)
    root.mainloop()