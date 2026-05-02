[README.md](https://github.com/user-attachments/files/26875472/README.md)
# Fleet SaaS — Backend GPS

> **SaaS Multi-tenant · REST API · Tiempo Real**
> Django Edition — v1.1 · Abril 2026

Backend para un sistema de gestión de flotas con tracking GPS en tiempo real, construido con Django, Django REST Framework y Django Channels.

---

## Tabla de Contenidos

- [Stack Tecnológico](#-stack-tecnológico)
- [Arquitectura](#-arquitectura)
- [Módulos y Endpoints](#-módulos-y-endpoints)
- [Base de Datos](#-base-de-datos)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Tareas Celery](#-tareas-celery)
- [Seguridad](#-seguridad)
- [Fases de Desarrollo](#-fases-de-desarrollo)
- [KPIs Técnicos](#-kpis-técnicos)
- [Variables de Entorno](#-variables-de-entorno)
- [Instalación](#-instalación)

---

## Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Lenguaje / Runtime | Python 3.12 |
| Framework Web | Django 5.x + Django REST Framework (DRF) |
| Tiempo Real | Django Channels 4.x (WebSockets sobre ASGI) |
| Servidor ASGI | Daphne o Uvicorn |
| Base de Datos | PostgreSQL 16 + TimescaleDB |
| Time-series / GPS | TimescaleDB (extensión Postgres) |
| Cache / Sesiones | Redis 7 (pub/sub + caché de rutas) |
| ORM | Django ORM (nativo) |
| Autenticación | JWT con `djangorestframework-simplejwt` |
| Cola de Tareas | Celery + Redis |
| Scheduler | Celery Beat |
| Almacenamiento | AWS S3 / MinIO via `django-storages` |
| Contenedores | Docker + Docker Compose (dev) / Kubernetes (prod) |
| Testing | pytest + pytest-django + factory_boy |
| Documentación API | drf-spectacular (OpenAPI 3.1 auto-generado) |
| Linting / Formato | Ruff + Black + mypy |

---

## Arquitectura

El sistema sigue una arquitectura orientada a microservicios con separación clara entre:

- **Capa de ingesta GPS** — recibe coordenadas de dispositivos físicos
- **API REST** — gestión de flotas, conductores, reportes
- **WebSockets en tiempo real** — broadcasting de posiciones vía Django Channels
- **Procesamiento asíncrono** — tareas diferidas con Celery + Redis

### Modelo Multi-Tenant

La arquitectura implementa multi-tenancy a nivel de base de datos con `tenant_id` en todas las tablas, reforzado con middleware JWT y Row-Level Security en PostgreSQL.

**Componentes clave:**

- `TenantMiddleware` — resuelve el tenant desde el JWT y lo adjunta al request
- `TenantFilterMixin` — filtra automáticamente cada QuerySet por `tenant_id`
- Row-Level Security (opcional) — aislamiento máximo a nivel de motor PostgreSQL

**Roles del sistema:** `SUPER_ADMIN` · `ORG_ADMIN` · `MANAGER` · `DRIVER` · `VIEWER`

---

## Módulos y Endpoints

### Autenticación (JWT con simplejwt)

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/api/auth/register/` | Registro de organización + admin |
| POST | `/api/auth/login/` | Login → `access_token` + `refresh_token` |
| POST | `/api/auth/token/refresh/` | Renovar access token |
| POST | `/api/auth/logout/` | Blacklist refresh token |
| GET | `/api/auth/me/` | Perfil del usuario autenticado |
| POST | `/api/auth/password/reset/` | Solicitar reset por email |
| POST | `/api/auth/password/confirm/` | Confirmar reset con token |

**Configuración JWT:**
- `ACCESS_TOKEN_LIFETIME` → 15 minutos
- `REFRESH_TOKEN_LIFETIME` → 7 días
- `ROTATE_REFRESH_TOKENS` → `True`
- `BLACKLIST_AFTER_ROTATION` → `True`
- Payload custom: `{ user_id, tenant_id, role, email }`

---

### Vehículos

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/vehicles/` | Listar vehículos del tenant |
| POST | `/api/vehicles/` | Crear vehículo |
| GET | `/api/vehicles/{id}/` | Detalle de vehículo |
| PUT | `/api/vehicles/{id}/` | Actualizar vehículo |
| PATCH | `/api/vehicles/{id}/` | Actualización parcial |
| DELETE | `/api/vehicles/{id}/` | Desactivar vehículo |
| GET | `/api/vehicles/{id}/status/` | Estado actual en tiempo real |

---

### Conductores

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/drivers/` | Listar conductores del tenant |
| POST | `/api/drivers/` | Crear conductor |
| GET | `/api/drivers/{id}/` | Detalle del conductor |
| PUT | `/api/drivers/{id}/` | Actualizar conductor |
| DELETE | `/api/drivers/{id}/` | Desactivar conductor |
| POST | `/api/drivers/{id}/assign/` | Asignar a vehículo |

---

### GPS — Ingesta de Coordenadas

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/api/gps/ingest/` | Endpoint para dispositivos GPS (API Key auth) |
| POST | `/api/gps/ingest/bulk/` | Ingesta masiva (sincronización offline) |

---

### Tracking en Tiempo Real (WebSockets)

**Endpoint:** `wss://api/ws/tracking/`  
**Consumer:** `AsyncJsonWebsocketConsumer`

| Mensajes Cliente → Servidor | Descripción |
|---|---|
| `subscribe_vehicle` | Suscribirse a actualizaciones de un vehículo |
| `unsubscribe_vehicle` | Cancelar suscripción de un vehículo |
| `subscribe_fleet` | Suscribirse a toda la flota del tenant |

| Mensajes Servidor → Cliente | Descripción |
|---|---|
| `vehicle_update` | `lat, lng, speed, heading, timestamp, status` |
| `vehicle_offline` | `vehicle_id, last_seen` |
| `alert_triggered` | `alert_id, vehicle_id, alert_type, message, timestamp` |

---

### Historial de Rutas

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/trips/` | Listar trips del tenant |
| GET | `/api/trips/{id}/` | Detalle de trip |
| GET | `/api/trips/{id}/points/` | Puntos GPS paginados |
| GET | `/api/vehicles/{id}/trips/` | Trips de un vehículo (con filtros) |
| POST | `/api/trips/{id}/export/` | Exportar ruta (GPX / CSV / PDF) |

---

### Analíticas y Reportes

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/analytics/summary/` | Resumen general del tenant |
| GET | `/api/analytics/vehicles/` | Métricas por vehículo |
| GET | `/api/analytics/drivers/` | Métricas por conductor |
| GET | `/api/analytics/usage/` | Actividad diaria/semanal/mensual |
| GET | `/api/analytics/mileage/` | Kilometraje por período y vehículo |
| GET | `/api/analytics/idle-time/` | Tiempo de ralentí por vehículo |
| POST | `/api/reports/generate/` | Generar reporte async (Celery) |
| GET | `/api/reports/{id}/status/` | Estado del reporte |
| GET | `/api/reports/{id}/download/` | URL de descarga (S3 signed URL) |

---

### Alertas

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/alert-rules/` | Listar reglas configuradas |
| POST | `/api/alert-rules/` | Crear regla de alerta |
| PUT | `/api/alert-rules/{id}/` | Actualizar regla |
| DELETE | `/api/alert-rules/{id}/` | Eliminar regla |
| GET | `/api/alert-events/` | Historial de alertas disparadas |
| GET | `/api/alert-events/{id}/` | Detalle de alerta |
| POST | `/api/alert-events/{id}/read/` | Marcar como leída |
| POST | `/api/alert-events/read-all/` | Marcar todas como leídas |

**Tipos de alerta disponibles:**

| Tipo | Descripción |
|---|---|
| `SPEEDING` | Supera velocidad máxima configurada |
| `IDLE_TOO_LONG` | Motor encendido sin movimiento por más de X minutos |
| `GEOFENCE_EXIT` | Sale de zona geográfica definida |
| `GEOFENCE_ENTER` | Entra a zona geográfica |
| `IGNITION_ON` | Encendido fuera de horario permitido |
| `IGNITION_OFF` | Apagado fuera de zona base |
| `NO_SIGNAL` | Sin señal GPS por más de X minutos |

---

### Geofences

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/geofences/` | Listar zonas geográficas |
| POST | `/api/geofences/` | Crear zona |
| PUT | `/api/geofences/{id}/` | Actualizar zona |
| DELETE | `/api/geofences/{id}/` | Eliminar zona |

---

### Organizaciones / Multi-Tenant

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/org/settings/` | Configuración de la organización |
| PUT | `/api/org/settings/` | Actualizar configuración |
| GET | `/api/org/users/` | Listar usuarios de la organización |
| POST | `/api/org/users/invite/` | Invitar usuario (envía email) |
| PUT | `/api/org/users/{id}/role/` | Cambiar rol de usuario |
| DELETE | `/api/org/users/{id}/` | Remover usuario |

---

## 🗄 Base de Datos

### Esquema Principal

| Tabla | Descripción |
|---|---|
| `tenants` | `id, name, slug, plan, config (JSON), created_at` |
| `users` | `id, tenant_id, email, password (hash), role` |
| `outstanding_token` | simplejwt: tokens activos |
| `blacklisted_token` | simplejwt: tokens invalidados |
| `vehicles` | `id, tenant_id, plate, alias, device_id, status, ...` |
| `drivers` | `id, tenant_id, user_id, name, license, ...` |
| `vehicle_drivers` | `vehicle_id, driver_id, assigned_at, unassigned_at` |
| `gps_points` | `id, vehicle_id, lat, lng, speed, timestamp` **(HYPERTABLE)** |
| `trips` | `id, vehicle_id, driver_id, start_time, end_time, ...` |
| `geofences` | `id, tenant_id, name, fence_type, coords (JSON)` |
| `alert_rules` | `id, tenant_id, vehicle_id, type, config (JSON), ...` |
| `alert_events` | `id, rule_id, vehicle_id, triggered_at, data (JSON)` |
| `reports` | `id, tenant_id, report_type, status, file_url` |

### TimescaleDB — `gps_points` (Hypertable)

```sql
-- Registrar como hypertable
SELECT create_hypertable('gps_gpspoint', 'timestamp');
```

- **Chunk interval:** 1 día
- **Índice:** `(vehicle_id, timestamp DESC)`
- **Compresión automática:** datos > 7 días
- **Retención:** datos raw > 90 días son eliminados

### Redis Keys

| Key | Descripción | TTL |
|---|---|---|
| `vehicle:last:{vehicle_id}` | Hash última posición | 30s |
| `alert:cooldown:{rule_id}:{vid}` | Flag cooldown de alerta | `cooldown_minutes` |
| `analytics:cache:{tenant}:{key}` | Caché de analíticas | 5–30 min |

---

## Estructura del Proyecto

```
fleet_backend/
├── config/                       # Configuración global Django
│   ├── settings/
│   │   ├── base.py               # Settings comunes
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py                   # URL raíz + router DRF
│   ├── asgi.py                   # Entry point ASGI (Channels)
│   └── celery.py                 # Configuración Celery
├── apps/
│   ├── tenants/                  # Modelo Tenant, middleware
│   ├── authentication/           # JWT custom, register, login, permisos
│   ├── fleet/                    # Vehículos y conductores
│   ├── gps/                      # Ingesta de coordenadas
│   ├── tracking/                 # WebSocket consumers
│   ├── trips/                    # Historial de rutas
│   ├── analytics/                # Métricas y reportes
│   ├── alerts/                   # Reglas y eventos de alerta
│   └── geofences/                # Zonas geográficas
├── tasks/                        # Tareas Celery
│   ├── gps_tasks.py
│   ├── trip_tasks.py
│   ├── alert_tasks.py
│   ├── report_tasks.py
│   └── analytics_tasks.py
├── shared/
│   ├── mixins.py                 # TenantFilterMixin
│   ├── pagination.py
│   ├── exceptions.py
│   └── utils/
│       ├── geo.py
│       └── redis_client.py
├── tests/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
└── pyproject.toml
```

---

## Tareas Celery

El sistema usa Celery para procesamiento asíncrono y periódico fuera del ciclo request/response.

### Schedule (Celery Beat)

| Tarea | Frecuencia |
|---|---|
| `detect-open-trips` | Cada 5 minutos |
| `aggregate-metrics` | Diario a las 02:00 |
| `cleanup-gps-data` | Domingos a las 03:00 |

### Canales de Notificación de Alertas

- **Email:** Django `send_mail` + `django-anymail` (Resend, SendGrid)
- **Webhook:** `requests.post` con reintentos automáticos de Celery
- **WebSocket:** `channel_layer.group_send` → `fleet_{tenant_id}`

---

## Seguridad

- JWT con `simplejwt` + `token_blacklist` (tokens revocables en logout)
- Tokens rotantes: cada refresh genera nuevo par y blacklistea el anterior
- Rate limiting en login: `django-ratelimit` (5 intentos / 15 min por IP+email)
- Throttling DRF: `AnonRateThrottle` + `UserRateThrottle`
- CORS: `django-cors-headers` con whitelist de dominios por tenant
- Tenant isolation: `TenantFilterMixin` filtra cada QuerySet automáticamente
- Row-Level Security opcional en PostgreSQL
- HTTPS forzado en producción: `SECURE_SSL_REDIRECT = True`
- Headers de seguridad: `SECURE_HSTS_SECONDS`, `X_FRAME_OPTIONS`, `CSP`
- Secrets via variables de entorno con `python-decouple` (nunca en código)
- Logging estructurado con `IP`, `user_id`, `tenant_id` (sin datos sensibles)
- Dispositivos GPS: `DeviceAPIKeyAuthentication` (DRF `BaseAuthentication`)
- `DEBUG = False` obligatorio en producción

---

## Fases de Desarrollo

### Fase 1 — Fundación (Semanas 1–2) X
- Setup Django + DRF + Docker (Postgres, Redis, Celery)
- Configuración multi-entorno (`settings/base`, `development`, `production`)
- Modelo Tenant + `TenantMiddleware`
- Sistema de autenticación JWT completo (simplejwt + blacklist)
- Modelo User custom con `tenant_id` y roles
- CRUD de Vehículos y Conductores (ModelViewSet + DRF)
- `TenantFilterMixin` para aislamiento automático de QuerySets
- Documentación Swagger base (drf-spectacular)
- Tests unitarios de auth (pytest-django)

### Fase 2 — GPS Core (Semanas 3–4) X
- Modelo `GpsPoint` con TimescaleDB (migración con `RunSQL`)
- Endpoint de ingesta GPS (`DeviceAPIKeyAuthentication`)
- Configuración Django Channels + Daphne (ASGI)
- `TrackingConsumer` WebSocket con autenticación JWT
- `RedisChannelLayer` para broadcast de posiciones
- Tarea Celery: `process_gps_point`
- Tests de integración GPS + WebSocket

### Fase 3 — Historial y Analíticas (Semanas 5–6)
- Modelo `Trip` + tarea `detect_open_trips` (Celery Beat)
- Django Signal: inicio de trip en primer punto GPS
- API de historial de rutas con filtros y paginación
- Endpoints de analíticas con ORM `annotate` + raw SQL TimescaleDB
- Caché de analíticas con `django-redis`
- Generación de reportes PDF/Excel async (Celery)
- Exportación de rutas (GPX / CSV)

### Fase 4 — Alertas y Geofences (Semanas 7–8)
- Modelos `AlertRule` y `AlertEvent`
- Tarea Celery `evaluate_alerts` con evaluadores por tipo
- Cooldown de alertas con Redis (TTL)
- Notificaciones por email (`django-anymail` / SMTP)
- Notificaciones por webhook (requests + reintentos Celery)
- Notificaciones WebSocket via Channel Layer
- Modelo `Geofence` + utilidades de detección geométrica

### Fase 5 — Multi-Tenant y Polish (Semanas 9–10)
- Gestión de usuarios: invitaciones por email, cambio de rol
- Throttling avanzado por plan (Free / Pro / Enterprise)
- Logging estructurado (structlog → Loki / CloudWatch)
- Health check endpoint (`/api/health/`) + métricas (`django-prometheus`)
- Documentación API completa (drf-spectacular + Swagger UI + ReDoc)
- Tests end-to-end con pytest
- Pipeline CI/CD (GitHub Actions: lint + tests + build Docker)
- Django Admin panel para gestión interna (Super Admin)

---

## KPIs Técnicos

| KPI | Objetivo |
|---|---|
| Latencia de ingesta GPS | < 150ms (p99) |
| Latencia WebSocket broadcast | < 250ms desde ingesta hasta cliente |
| Tiempo de respuesta API REST | < 400ms (p95) en endpoints estándar |
| Disponibilidad objetivo | 99.9% uptime |
| Cobertura de tests | > 80% en módulos críticos (auth, GPS, alertas) |
| Tiempo máx. generación reporte | < 30 segundos para 30 días de datos |
| Capacidad inicial | 300–500 vehículos concurrentes por instancia |
| Workers Celery recomendados | 4 workers con concurrencia 4 (16 procesos) |

---

## Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto basado en este template:

```env
# Django
DEBUG=True
SECRET_KEY=django-insecure-cambiar-en-produccion
ALLOWED_HOSTS=localhost,127.0.0.1
APP_URL=http://localhost:8000

# Base de Datos
DB_NAME=fleet_db
DB_USER=postgres
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432

# Redis y Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# JWT
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=15
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7

# Email
EMAIL_HOST=smtp.resend.com
EMAIL_PORT=587
EMAIL_HOST_USER=resend
EMAIL_HOST_PASSWORD=<api_key>
DEFAULT_FROM_EMAIL=noreply@tuapp.com

# Storage S3
AWS_STORAGE_BUCKET_NAME=fleet-reports
AWS_S3_REGION_NAME=us-east-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

# GPS Device Auth
GPS_DEVICE_API_KEY_SALT=<random_salt_aqui>
```

---

## Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/fleet-backend.git
cd fleet-backend

# 2. Copiar variables de entorno
cp .env.example .env

# 3. Levantar servicios con Docker Compose
docker compose up -d

# 4. Aplicar migraciones
docker compose exec web python manage.py migrate

# 5. Crear superusuario
docker compose exec web python manage.py createsuperuser

# 6. Ejecutar tests
docker compose exec web pytest
```

La API estará disponible en `http://localhost:8000/api/`  
La documentación Swagger en `http://localhost:8000/api/docs/`

---

*fleet-backend v1.1 — Django Edition · Abril 2026*
