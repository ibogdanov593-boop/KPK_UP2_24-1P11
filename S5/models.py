from contextlib import asynccontextmanager
from peewee import SqliteDatabase, Model, CharField, BooleanField
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

db = SqliteDatabase('departments.db')

class Department(Model):
    """Модель отделения/факультета)"""
    name = CharField(max_length=100, unique=True, null=False, verbose_name="Название отделения")
    phone = CharField(max_length=20, null=False, default='', verbose_name="Телефон")
    manager = CharField(max_length=100, null=False, default='', verbose_name="Заведующий")
    building = CharField(max_length=50, null=False, default='', verbose_name="Корпус")
    is_active = BooleanField(null=False, default=True, verbose_name="Активно")

    class Meta:
        database = db
        table_name = 'departments'

def init_db():
    """Инициализация БД: создание таблиц"""
    db.connect()
    db.create_tables([Department], safe=True)
    db.close()

# ==================== PYDANTIC СХЕМЫ ====================
class DepartmentCreate(BaseModel):
    name: str = Field(..., max_length=100, description="Название отделения")
    phone: Optional[str] = Field('', max_length=20, description="Телефон")
    manager: Optional[str] = Field('', max_length=100, description="Заведующий")
    building: Optional[str] = Field('', max_length=50, description="Корпус")
    is_active: bool = Field(True, description="Активно")

class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="Название отделения")
    phone: Optional[str] = Field(None, max_length=20, description="Телефон")
    manager: Optional[str] = Field(None, max_length=100, description="Заведующий")
    building: Optional[str] = Field(None, max_length=50, description="Корпус")
    is_active: Optional[bool] = Field(None, description="Активно")

class DepartmentOut(BaseModel):
    id: int
    name: str
    phone: str
    manager: str
    building: str
    is_active: bool

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Запуск сервера Department Service...")
    init_db()
    print("База данных инициализирована")
    yield
    print("Остановка сервера...")
    if not db.is_closed():
        db.close()
    print("Ресурсы освобождены")

app = FastAPI(
    title="Department Service",
    description="Сервис управления отделениями/факультетами СПО",
    version="1.0",
    lifespan=lifespan
)

@app.post("/departments", response_model=DepartmentOut, status_code=201)
def create_department(dept: DepartmentCreate):
    db.connect()
    if Department.select().where(Department.name == dept.name).exists():
        db.close()
        raise HTTPException(400, "Отделение с таким названием уже существует")
    new_dept = Department.create(
        name=dept.name,
        phone=dept.phone or '',
        manager=dept.manager or '',
        building=dept.building or '',
        is_active=dept.is_active
    )
    db.close()
    return new_dept

@app.get("/departments/{dept_id}", response_model=DepartmentOut)
def get_department(dept_id: int):
    db.connect()
    try:
        dept = Department.get_by_id(dept_id)
        return dept
    except Department.DoesNotExist:
        raise HTTPException(404, "Отделение не найдено")
    finally:
        db.close()

@app.get("/departments", response_model=List[DepartmentOut])
def list_departments(
    name: Optional[str] = None,
    manager: Optional[str] = None,
    building: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0
):
    db.connect()
    query = Department.select()
    if name:
        query = query.where(Department.name.contains(name))
    if manager:
        query = query.where(Department.manager.contains(manager))
    if building:
        query = query.where(Department.building.contains(building))
    if is_active is not None:
        query = query.where(Department.is_active == is_active)
    result = list(query.offset(offset).limit(limit))
    db.close()
    return result

@app.put("/departments/{dept_id}", response_model=DepartmentOut)
def update_department(dept_id: int, dept: DepartmentUpdate):
    db.connect()
    if not Department.select().where(Department.id == dept_id).exists():
        db.close()
        raise HTTPException(404, "Отделение не найдено")
    update_data = {}
    if dept.name is not None:
        # Проверка уникальности нового имени
        if Department.select().where((Department.name == dept.name) & (Department.id != dept_id)).exists():
            db.close()
            raise HTTPException(400, "Отделение с таким названием уже существует")
        update_data['name'] = dept.name
    if dept.phone is not None:
        update_data['phone'] = dept.phone
    if dept.manager is not None:
        update_data['manager'] = dept.manager
    if dept.building is not None:
        update_data['building'] = dept.building
    if dept.is_active is not None:
        update_data['is_active'] = dept.is_active
    if update_data:
        Department.update(update_data).where(Department.id == dept_id).execute()
    updated = Department.get_by_id(dept_id)
    db.close()
    return updated

@app.delete("/departments/{dept_id}")
def delete_department(dept_id: int):
    db.connect()
    deleted = Department.delete().where(Department.id == dept_id).execute()
    db.close()
    return {"deleted": bool(deleted)}

@app.get("/")
def root():
    return {
        "service": "Department Service",
        "version": "1.0",
        "endpoints": {
            "POST /departments": "Создать отделение",
            "GET /departments": "Список отделений",
            "GET /departments/{id}": "Получить по ID",
            "PUT /departments/{id}": "Обновить",
            "DELETE /departments/{id}": "Удалить"
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("Запуск сервера Department Service...")
    print("Документация API: http://localhost:8000/docs")
    print("=" * 50)
    uvicorn.run(app, host="127.0.0.1", port=8000)