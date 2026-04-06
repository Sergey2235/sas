

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """Модель пользователя системы"""
    user_id: Optional[int] = None
    fio: str = ""
    phone: str = ""
    login: str = ""
    password: str = ""
    user_type: str = ""


@dataclass
class Request:
    """Модель заявки на ремонт"""
    request_id: Optional[int] = None
    start_date: str = ""
    car_type: str = ""
    car_model: str = ""
    problem_descryption: str = ""
    request_status: str = "Новая заявка"
    completion_date: Optional[str] = None
    repair_parts: Optional[str] = None
    master_id: Optional[int] = None
    client_id: Optional[int] = None
    master_name: str = "Не назначен"
    client_name: str = ""

    def __post_init__(self):
        """Автоматическая установка даты создания если не указана"""
        if not self.start_date:
            self.start_date = datetime.now().strftime("%Y-%m-%d")

    def get_repair_duration(self) -> Optional[int]:
        """Расчёт длительности ремонта в днях"""
        if self.start_date and self.completion_date:
            try:
                d1 = datetime.strptime(self.start_date, "%Y-%m-%d")
                d2 = datetime.strptime(self.completion_date, "%Y-%m-%d")
                return (d2 - d1).days
            except ValueError:
                return None
        return None


@dataclass
class Comment:
    """Модель комментария к заявке"""
    comment_id: Optional[int] = None
    message: str = ""
    master_id: Optional[int] = None
    request_id: Optional[int] = None
    created_date: str = ""
    author_name: str = ""

    def __post_init__(self):
        """Автоматическая установка даты создания если не указана"""
        if not self.created_date:
            self.created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")