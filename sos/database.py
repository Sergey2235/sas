"""
Модуль работы с базой данных SQLite
Реализует все операции CRUD для сущностей системы
"""

import sqlite3
from typing import List, Optional, Tuple
from config import DB_PATH, REQUEST_STATUSES
from models import User, Request, Comment


def get_connection() -> sqlite3.Connection:
    """Создание подключения к БД с поддержкой внешних ключей"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database() -> None:
    """Инициализация структуры базы данных"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Таблица пользователей
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            userID INTEGER PRIMARY KEY AUTOINCREMENT,
            fio TEXT NOT NULL,
            phone TEXT NOT NULL,
            login TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN (
                'Менеджер', 
                'Менеджер по качеству', 
                'Оператор', 
                'Автомеханик', 
                'Заказчик'
            ))
        )
        """)
        
        # Таблица заявок
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Requests (
            requestID INTEGER PRIMARY KEY AUTOINCREMENT,
            startDate TEXT NOT NULL,
            carType TEXT NOT NULL CHECK(carType IN ('Легковая', 'Грузовая', 'Внедорожник')),
            carModel TEXT NOT NULL,
            problemDescryption TEXT NOT NULL,
            requestStatus TEXT DEFAULT 'Новая заявка' 
                CHECK(requestStatus IN ('Новая заявка', 'В процессе ремонта', 'Готова к выдаче')),
            completionDate TEXT,
            repairParts TEXT,
            masterID INTEGER,
            clientID INTEGER NOT NULL,
            FOREIGN KEY (masterID) REFERENCES Users(userID) ON DELETE SET NULL,
            FOREIGN KEY (clientID) REFERENCES Users(userID) ON DELETE CASCADE
        )
        """)
        
        # Таблица комментариев
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Comments (
            commentID INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            masterID INTEGER NOT NULL,
            requestID INTEGER NOT NULL,
            createdDate TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (masterID) REFERENCES Users(userID) ON DELETE CASCADE,
            FOREIGN KEY (requestID) REFERENCES Requests(requestID) ON DELETE CASCADE
        )
        """)
        
        # Индексы для оптимизации поиска
        cur.execute("CREATE INDEX IF NOT EXISTS idx_requests_status ON Requests(requestStatus)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_requests_client ON Requests(clientID)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_requests_master ON Requests(masterID)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_comments_request ON Comments(requestID)")
        
        conn.commit()
    except Exception as exc:
        print(f"[ERROR] Ошибка инициализации БД: {exc}")
        conn.rollback()
    finally:
        conn.close()


def seed_data() -> None:
    """Заполнение БД тестовыми данными из файлов import"""
    conn = get_connection()
    cur = conn.cursor()
    
    users_data = [
        (1, "Белов Александр Давидович", "89210563128", "login1", "pass1", "Менеджер"),
        (2, "Харитонова Мария Павловна", "89535078985", "login2", "pass2", "Автомеханик"),
        (3, "Марков Давид Иванович", "89210673849", "login3", "pass3", "Автомеханик"),
        (4, "Громова Анна Семёновна", "89990563748", "login4", "pass4", "Оператор"),
        (5, "Карташова Мария Данииловна", "89994563847", "login5", "pass5", "Оператор"),
        (6, "Касаткин Егор Львович", "89219567849", "login11", "pass11", "Заказчик"),
        (7, "Ильина Тамара Даниловна", "89219567841", "login12", "pass12", "Заказчик"),
        (8, "Елисеева Юлиана Алексеевна", "89219567842", "login13", "pass13", "Заказчик"),
        (9, "Никифорова Алиса Тимофеевна", "89219567843", "login14", "pass14", "Заказчик"),
        (10, "Васильев Али Евгеньевич", "89219567844", "login15", "pass15", "Автомеханик"),
        # Менеджер по качеству (Модуль 3)
        (11, "Петрова Мария Ивановна", "89123456789", "login16", "pass16", "Менеджер по качеству"),
        (25, "Орлов Максим Станиславович", "89165557788", "q2", "q2", "Менеджер по качеству"),
    ]
    
    requests_data = [
        (1, "2023-06-06", "Легковая", "Hyundai Avante (CN7)", "Отказали тормоза.", "В процессе ремонта", None, "", 2, 7),
        (2, "2023-05-05", "Легковая", "Nissan 180SX", "Отказали тормоза.", "В процессе ремонта", None, "", 3, 8),
        (3, "2022-07-07", "Легковая", "Toyota 2000GT", "В салоне пахнет бензином.", "Готова к выдаче", "2023-01-01", "", 3, 9),
        (4, "2023-08-02", "Грузовая", "Citroen Berlingo (B9)", "Руль плохо крутится.", "Новая заявка", None, "", None, 8),
        (5, "2023-08-02", "Грузовая", "УАЗ 2360", "Руль плохо крутится.", "Новая заявка", None, "", None, 9),
    ]
    
    comments_data = [
        (1, "Очень странно.", 2, 1),
        (2, "Будем разбираться!", 3, 2),
        (3, "Будем разбираться!", 3, 3),
    ]
    
    try:
        cur.executemany(
            "INSERT OR IGNORE INTO Users (userID, fio, phone, login, password, type) VALUES (?, ?, ?, ?, ?, ?)",
            users_data
        )
        cur.executemany(
            "INSERT OR IGNORE INTO Requests (requestID, startDate, carType, carModel, problemDescryption, requestStatus, completionDate, repairParts, masterID, clientID) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            requests_data
        )
        cur.executemany(
            "INSERT OR IGNORE INTO Comments (commentID, message, masterID, requestID) VALUES (?, ?, ?, ?)",
            comments_data
        )
        conn.commit()
    except Exception as exc:
        print(f"[ERROR] Ошибка загрузки данных: {exc}")
        conn.rollback()
    finally:
        conn.close()


def authenticate_user(login: str, password: str) -> Optional[User]:
    """Проверка учётных данных пользователя"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT userID, fio, phone, login, password, type FROM Users WHERE login = ? AND password = ?",
            (login, password)
        )
        row = cur.fetchone()
        if row:
            return User(user_id=row[0], fio=row[1], phone=row[2], login=row[3], password=row[4], user_type=row[5])
        return None
    except Exception as exc:
        print(f"[ERROR] Ошибка авторизации: {exc}")
        return None
    finally:
        conn.close()


def get_all_requests() -> List[Request]:
    """Получение всех заявок с данными пользователей"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
        SELECT r.requestID, r.startDate, r.carType, r.carModel, r.problemDescryption,
               r.requestStatus, r.completionDate, r.repairParts, r.masterID, r.clientID,
               m.fio, c.fio
        FROM Requests r
        LEFT JOIN Users m ON r.masterID = m.userID
        LEFT JOIN Users c ON r.clientID = c.userID
        ORDER BY r.requestID DESC
        """)
        out: List[Request] = []
        for row in cur.fetchall():
            req = Request(
                request_id=row[0],
                start_date=row[1],
                car_type=row[2],
                car_model=row[3],
                problem_descryption=row[4],
                request_status=row[5],
                completion_date=row[6],
                repair_parts=row[7],
                master_id=row[8],
                client_id=row[9],
                master_name=row[10] or "Не назначен",
                client_name=row[11] or "",
            )
            out.append(req)
        return out
    except Exception as exc:
        print(f"[ERROR] Ошибка загрузки заявок: {exc}")
        return []
    finally:
        conn.close()


def get_request_by_id(request_id: int) -> Optional[Tuple]:
    """Получение заявки по ID"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
        SELECT r.startDate, r.carType, r.carModel, r.problemDescryption, r.requestStatus,
               r.completionDate, r.repairParts, m.fio, c.fio
        FROM Requests r
        LEFT JOIN Users m ON r.masterID = m.userID
        LEFT JOIN Users c ON r.clientID = c.userID
        WHERE r.requestID = ?
        """, (request_id,))
        return cur.fetchone()
    except Exception as exc:
        print(f"[ERROR] Ошибка загрузки заявки: {exc}")
        return None
    finally:
        conn.close()


def get_request_status_and_master(request_id: int) -> Optional[Tuple]:
    """Получение статуса, механика и заказчика заявки"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT requestStatus, masterID, clientID FROM Requests WHERE requestID = ?",
            (request_id,),
        )
        return cur.fetchone()
    except Exception as exc:
        print(f"[ERROR] Ошибка загрузки статуса: {exc}")
        return None
    finally:
        conn.close()


def get_comments_for_request(request_id: int) -> List[Tuple]:
    """Получение комментариев к заявке"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
        SELECT c.message, u.fio, c.createdDate
        FROM Comments c
        JOIN Users u ON c.masterID = u.userID
        WHERE c.requestID = ?
        ORDER BY c.createdDate DESC
        """, (request_id,))
        return cur.fetchall()
    except Exception as exc:
        print(f"[ERROR] Ошибка загрузки комментариев: {exc}")
        return []
    finally:
        conn.close()


def get_users_by_type(user_type: str) -> List[Tuple]:
    """Получение пользователей по роли"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT userID, fio FROM Users WHERE type = ? ORDER BY fio", (user_type,))
        return cur.fetchall()
    except Exception as exc:
        print(f"[ERROR] Ошибка загрузки пользователей: {exc}")
        return []
    finally:
        conn.close()


def create_request(start_date: str, car_type: str, car_model: str, 
                   problem_descryption: str, client_id: int, master_id: Optional[int] = None) -> Optional[int]:
    """Создание новой заявки"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
        INSERT INTO Requests (startDate, carType, carModel, problemDescryption, requestStatus, repairParts, masterID, clientID)
        VALUES (?, ?, ?, ?, 'Новая заявка', '', ?, ?)
        """, (start_date, car_type.strip(), car_model.strip(), problem_descryption.strip(), master_id, client_id))
        conn.commit()
        return cur.lastrowid
    except Exception as exc:
        print(f"[ERROR] Ошибка создания заявки: {exc}")
        return None
    finally:
        conn.close()


def update_request_status(request_id: int, new_status: str) -> bool:
    """Обновление статуса заявки"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        from datetime import date
        completion_date = date.today().isoformat() if new_status == "Готова к выдаче" else None
        if completion_date:
            cur.execute(
                "UPDATE Requests SET requestStatus = ?, completionDate = ? WHERE requestID = ?",
                (new_status, completion_date, request_id)
            )
        else:
            cur.execute(
                "UPDATE Requests SET requestStatus = ?, completionDate = NULL WHERE requestID = ?",
                (new_status, request_id)
            )
        conn.commit()
        return cur.rowcount > 0
    except Exception as exc:
        print(f"[ERROR] Ошибка обновления статуса: {exc}")
        return False
    finally:
        conn.close()


def update_request_master(request_id: int, master_id: Optional[int]) -> bool:
    """Назначение механика на заявку"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE Requests SET masterID = ? WHERE requestID = ?", (master_id, request_id))
        conn.commit()
        return cur.rowcount > 0
    except Exception as exc:
        print(f"[ERROR] Ошибка назначения механика: {exc}")
        return False
    finally:
        conn.close()


def add_comment(request_id: int, master_id: int, message: str) -> bool:
    """Добавление комментария к заявке"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO Comments (message, masterID, requestID) VALUES (?, ?, ?)",
            (message.strip(), master_id, request_id)
        )
        conn.commit()
        return True
    except Exception as exc:
        print(f"[ERROR] Ошибка добавления комментария: {exc}")
        return False
    finally:
        conn.close()


def delete_request(request_id: int) -> bool:
    """Удаление заявки (каскадное удаление комментариев)"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM Comments WHERE requestID = ?", (request_id,))
        cur.execute("DELETE FROM Requests WHERE requestID = ?", (request_id,))
        conn.commit()
        return True
    except Exception as exc:
        print(f"[ERROR] Ошибка удаления заявки: {exc}")
        return False
    finally:
        conn.close()


def get_completed_requests_count() -> int:
    """Подсчёт выполненных заявок"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute('SELECT COUNT(*) FROM Requests WHERE requestStatus = "Готова к выдаче"')
        return int(cur.fetchone()[0])
    except Exception as exc:
        print(f"[ERROR] Ошибка подсчёта заявок: {exc}")
        return 0
    finally:
        conn.close()


def get_average_repair_time() -> float:
    """Расчёт среднего времени ремонта в днях"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
        SELECT julianday(completionDate) - julianday(startDate)
        FROM Requests
        WHERE requestStatus = 'Готова к выдаче' AND completionDate IS NOT NULL
        """)
        rows = cur.fetchall()
        if not rows:
            return 0.0
        return round(sum(r[0] for r in rows) / len(rows), 2)
    except Exception as exc:
        print(f"[ERROR] Ошибка расчёта среднего времени: {exc}")
        return 0.0
    finally:
        conn.close()


def backup_database(backup_dir: str = "backup") -> Optional[str]:
    """Создание резервной копии БД (Модуль 2)"""
    import shutil
    import os
    from datetime import datetime
    
    try:
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"AutoService_{timestamp}.bak"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        shutil.copy2(DB_PATH, backup_path)
        print(f"[OK] Резервная копия создана: {backup_path}")
        return backup_path
    except Exception as exc:
        print(f"[ERROR] Ошибка резервного копирования: {exc}")
        return None


def create_user(fio: str, phone: str, login: str, password: str, user_type: str = "Заказчик") -> Optional[int]:
    """Создание нового пользователя в системе"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO Users (fio, phone, login, password, type)
            VALUES (?, ?, ?, ?, ?)
            """,
            (fio.strip(), phone.strip(), login.strip(), password.strip(), user_type.strip()),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError as exc:
        print(f"[ERROR] Ошибка создания пользователя (уникальность логина): {exc}")
        return None
    except Exception as exc:
        print(f"[ERROR] Ошибка создания пользователя: {exc}")
        return None
    finally:
        conn.close()


def update_request_details(
    request_id: int,
    car_model: str,
    problem_descryption: str,
    repair_parts: Optional[str],
) -> bool:
    """Обновление основных полей заявки"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE Requests
            SET carModel = ?, problemDescryption = ?, repairParts = ?
            WHERE requestID = ?
            """,
            (car_model.strip(), problem_descryption.strip(), (repair_parts or "").strip(), request_id),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception as exc:
        print(f"[ERROR] Ошибка обновления заявки: {exc}")
        return False
    finally:
        conn.close()