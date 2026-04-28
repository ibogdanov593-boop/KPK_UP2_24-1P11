from contextlib import asynccontextmanager
from peewee import SqliteDatabase, Model, CharField
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

db = SqliteDatabase('departments.db')

class Department(Model):
    """Модель отделения/факультета (без NULL-полей)"""
    name = CharField(max_length=100, unique=True, null=False, verbose_name="Название отделения")
    phone = CharField(max_length=20, null=False, default='', verbose_name="Телефон")
    campus = CharField(max_length=50, null=False, default='', verbose_name="Корпус")

    class Meta:
        database = db
        table_name = 'departments'

def init_db():
    """Инициализация БД"""
    db.connect()
    db.create_tables([Department], safe=True)
    db.close()

class DepartmentCreate(BaseModel):
    name: str = Field(..., max_length=100, description="Название отделения")
    phone: Optional[str] = Field('', max_length=20, description="Телефон")
    campus: Optional[str] = Field('', max_length=50, description="Корпус")

class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="Название отделения")
    phone: Optional[str] = Field(None, max_length=20, description="Телефон")
    campus: Optional[str] = Field(None, max_length=50, description="Корпус")

class DepartmentOut(BaseModel):
    id: int
    name: str
    phone: str
    campus: str

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
        campus=dept.campus or ''
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
def list_departments(name: Optional[str] = None, campus: Optional[str] = None, limit: int = 100, offset: int = 0):
    db.connect()
    query = Department.select()
    if name:
        query = query.where(Department.name.contains(name))
    if campus:
        query = query.where(Department.campus.contains(campus))
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
        if Department.select().where((Department.name == dept.name) & (Department.id != dept_id)).exists():
            db.close()
            raise HTTPException(400, "Отделение с таким названием уже существует")
        update_data['name'] = dept.name
    if dept.phone is not None:
        update_data['phone'] = dept.phone
    if dept.campus is not None:
        update_data['campus'] = dept.campus
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