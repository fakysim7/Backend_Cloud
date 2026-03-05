# IaaS Platform на Django

Полнофункциональная платформа Infrastructure as a Service с мультитенантностью, 
квотами ресурсов и интеграцией с KVM через libvirt.

## Архитектура

```
iaas_project/
├── config/                        # Django конфигурация
│   ├── settings/
│   │   ├── base.py                # Базовые настройки
│   │   ├── development.py
│   │   └── production.py
│   ├── celery.py                  # Celery + Beat расписание
│   └── urls.py
├── core/                          # Общие утилиты
│   ├── middleware.py              # TenantMiddleware
│   ├── permissions.py             # IsOrganizationMember/Admin/Owner
│   ├── exceptions.py              # QuotaExceededError + handler
│   └── pagination.py
└── apps/
    ├── accounts/                  # Пользователи, Организации, Роли
    ├── quotas/                    # Квоты ресурсов на организацию
    ├── hypervisors/               # Узлы гипервизора (KVM)
    └── virtual_machines/          # VM: CRUD, жизненный цикл, Celery-задачи
        ├── services/
        │   ├── libvirt_service.py # Интеграция с KVM
        │   └── quota_service.py   # Атомарный контроль квот
        ├── scheduler.py           # Выбор гипервизора (spread/pack)
        └── tasks.py               # Celery: create/delete/start/stop/reboot/sync
```

## Быстрый старт

```bash
# 1. Клонировать и создать .env
cp .env.example .env

# 2. Запустить через Docker Compose
docker-compose up -d

# 3. Применить миграции и создать данные
docker-compose exec api python manage.py migrate
docker-compose exec api python manage.py seed_data
docker-compose exec api python manage.py createsuperuser

# 4. Открыть документацию
open http://localhost:8000/api/docs/
```

## Без Docker

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # настройте DB_* переменные

python manage.py migrate
python manage.py seed_data

# Запустить в разных терминалах:
python manage.py runserver
celery -A config worker -l info
celery -A config beat -l info
```

## API Reference

### Аутентификация

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/api/auth/register/` | Регистрация |
| POST | `/api/auth/token/` | Получить JWT токен |
| POST | `/api/auth/token/refresh/` | Обновить токен |
| GET | `/api/auth/me/` | Текущий пользователь |

### Организации (мультитенантность)

Все запросы к VM и квотам требуют заголовок:
```
X-Organization-Slug: my-org
```

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/organizations/` | Мои организации |
| POST | `/api/organizations/` | Создать организацию |
| GET | `/api/organizations/{id}/members/` | Участники |
| POST | `/api/organizations/{id}/members/invite/` | Пригласить пользователя |
| PATCH | `/api/organizations/{id}/members/{member_id}/` | Изменить роль |
| DELETE | `/api/organizations/{id}/members/{member_id}/` | Удалить участника |

### Виртуальные машины

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/vms/` | Список VM организации |
| POST | `/api/vms/` | Создать VM |
| GET | `/api/vms/{id}/` | Детали VM |
| PATCH | `/api/vms/{id}/` | Обновить имя/описание |
| DELETE | `/api/vms/{id}/` | Удалить VM |
| POST | `/api/vms/{id}/start/` | Запустить |
| POST | `/api/vms/{id}/stop/` | Остановить |
| POST | `/api/vms/{id}/reboot/` | Перезапустить |
| GET | `/api/vms/{id}/status_check/` | Статус из libvirt |

### Квоты

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/quota/` | Текущие квоты и использование |
| PATCH | `/api/quota/` | Изменить лимиты (только admin) |

### Гипервизоры (только superuser)

| Метод | URL | Описание |
|-------|-----|----------|
| GET/POST | `/api/hypervisors/` | CRUD гипервизоров |
| GET | `/api/hypervisors/available/` | Доступные узлы |

## Пример создания VM

```bash
# 1. Получить токен
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"owner1@iaas.local","password":"pass123"}' | jq -r .access)

# 2. Создать VM
curl -X POST http://localhost:8000/api/vms/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Organization-Slug: org-1" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "web-server-01",
    "vcpus": 2,
    "ram_mb": 4096,
    "disk_gb": 50,
    "os_type": "ubuntu-22.04",
    "description": "Веб-сервер"
  }'

# 3. Проверить квоты
curl http://localhost:8000/api/quota/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Organization-Slug: org-1"
```

## Параметры VM

| Параметр | Тип | Мин | Макс | Кратность |
|----------|-----|-----|------|-----------|
| `vcpus` | int | 1 | 64 | — |
| `ram_mb` | int | 512 | 524288 | 512MB |
| `disk_gb` | int | 10 | 10000 | — |

### Доступные ОС (`os_type`)
- `ubuntu-22.04` — Ubuntu 22.04 LTS
- `ubuntu-20.04` — Ubuntu 20.04 LTS  
- `debian-12` — Debian 12
- `centos-9` — CentOS Stream 9
- `rocky-9` — Rocky Linux 9
- `windows-2022` — Windows Server 2022

## Роли в организации

| Роль | Создать VM | Удалить VM | Управлять участниками | Изменять квоты |
|------|-----------|-----------|----------------------|----------------|
| Owner | ✅ | ✅ | ✅ | ❌ (только superuser) |
| Admin | ✅ | ✅ | ✅ | ❌ |
| Member | ✅ | ✅ | ❌ | ❌ |
| Viewer | ❌ | ❌ | ❌ | ❌ |

## Мультитенантность

Реализована через **Shared Database, Shared Schema** с Row-Level Security:

1. `TenantMiddleware` читает `X-Organization-Slug` из заголовка
2. Устанавливает `request.current_organization` и `request.current_role`
3. Все QuerySet в ViewSet фильтруются: `.filter(organization=request.current_organization)`
4. Пользователь физически не может получить ресурсы другой организации

## Контроль квот

- `QuotaService.check_and_allocate()` — атомарная проверка + резервирование через `SELECT FOR UPDATE`
- При ошибке создания VM — квота автоматически возвращается
- Периодическая синхронизация статусов через Celery Beat (каждые 60 сек)

## Запуск тестов

```bash
python manage.py test apps.virtual_machines.tests -v 2
```
