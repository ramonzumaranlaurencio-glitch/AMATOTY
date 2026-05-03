# Arquitectura Product OS

## Objetivo

Construir una plataforma multiusuario para que personas, empresas y administradores gestionen productos, medios, stock, promociones e historial de automatizaciones.

## Stack recomendado

Para produccion escalable:

- Frontend: Next.js o React con panel privado, rutas protegidas y componentes de tabla/formulario reutilizables.
- Backend: FastAPI o NestJS con modulos por dominio: auth, empresas, productos, medios, promociones, IA, metricas y administracion.
- Base de datos: PostgreSQL con migraciones y, si aplica, Row Level Security por organizacion.
- ORM: SQLAlchemy 2.0 / Prisma, segun el backend elegido.
- Archivos: S3 compatible, Cloudflare R2 o Supabase Storage con URLs firmadas para subida y lectura temporal.
- Cola de tareas: Redis + Celery, RQ, Dramatiq o BullMQ para analisis IA, generacion diaria y publicacion.
- IA: proveedor desacoplado por interfaz, con prompts versionados, salida JSON validada y auditoria de cada generacion.
- Seguridad: contrasenas hasheadas, tokens con expiracion, roles por empresa, logs de auditoria, rate limiting y backups.

La fase 1 implementada en este repo usa Flask + SQLite para avanzar sin romper el sistema actual. La misma separacion de tablas y endpoints permite migrar luego a PostgreSQL/FastAPI.

## Modelos principales

- `platform_users`: usuario, correo, hash de contrasena, tipo de cuenta, estado.
- `platform_organizations`: empresa o perfil personal, propietario, datos comerciales.
- `platform_memberships`: relacion usuario-empresa, rol y permisos.
- `platform_sessions`: tokens bearer con expiracion.
- `platform_password_resets`: recuperacion de contrasena con token temporal.
- `platform_products`: producto, precio, moneda, categoria, stock, prioridad, estado, enlace y metadata.
- `platform_product_media`: imagenes y videos asociados a producto.
- `platform_promotions`: textos, titulos, hashtags, copy social, WhatsApp, ideas y estado de aprobacion.
- `platform_promotion_jobs`: configuracion de generacion diaria por empresa.
- `platform_product_metrics`: vistas, clics, consultas, ventas e ingresos por dia.
- `platform_audit_logs`: acciones sensibles por usuario y empresa.

## Flujo de usuarios

1. Registro como persona natural, empresa o primer administrador.
2. Creacion automatica de organizacion/perfil y membresia `owner`.
3. Inicio de sesion con correo y contrasena.
4. Panel privado con selector de empresa.
5. Creacion, edicion, publicacion o archivo de productos.
6. Carga de imagenes y videos por producto.
7. Generacion de promociones por producto.
8. Revision, aprobacion y posterior automatizacion.

## Interfaz del panel

- Dashboard con productos, publicados, borradores, bajo stock y promociones.
- Inventario con busqueda, filtros por estado/categoria y acciones rapidas.
- Formulario lateral para producto, stock, prioridad, enlaces y medios.
- Promociones con sugerencias, generacion, historial y aprobacion.
- Perfil de empresa para datos comerciales.

## Fases

### Fase 1: Base solida

Implementar autenticacion, organizaciones, roles, CRUD de productos, carga de medios, dashboard y generacion local de promociones. Esta fase ya quedo creada en Flask/SQLite.

### Fase 2: Seguridad y permisos avanzados

Agregar invitaciones de equipo, permisos granulares, cierre de sesiones, rate limiting, validacion de archivos por tamano y politicas de auditoria.

### Fase 3: IA profesional

Conectar proveedor IA real para analizar productos, imagenes, categoria, precio, stock y fecha. Guardar prompt, version, entrada, salida, costo y estado de aprobacion.

### Fase 4: Automatizacion diaria

Ejecutar jobs programados con cola de tareas. Seleccionar productos por prioridad, stock, rotacion, temporada y rendimiento historico. Permitir aprobacion manual o publicacion automatica.

### Fase 5: Escala y publicacion

Migrar a PostgreSQL, almacenamiento externo, CDN, workers separados, observabilidad, backups, administracion global y conectores para redes sociales/WhatsApp.
