# Sistema web de producción frutícola — SQA

Sistema académico desarrollado en PG2 con Flask, PostgreSQL, SQLAlchemy, Bootstrap y Jinja. Se añadió una base de pruebas automatizadas y GitHub Actions.

## Instalación
1. Crear entorno virtual: `py -m venv .venv`.
2. Activar: `.\.venv\Scripts\Activate.ps1`.
3. Instalar: `python -m pip install -r requirements-dev.txt`.
4. Configurar `.env` local con `SECRET_KEY`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`.
5. Ejecutar: `python app.py`.

## Calidad
- Pruebas: `python -m pytest --cov --cov-branch --cov-report=term-missing --cov-fail-under=60`
- Linter: `python -m ruff check app.py models.py servicios_alertas.py tests/`
- Pipeline: `.github/workflows/ci.yml` (build, test, analyze, report).
- Cobertura medida: modelos y servicio de alertas; no toda la aplicación.

## Documentación
Consultar `docs/` para plan SQA, matriz, línea base, reporte de mejora y manual técnico.

## Estado
Pendiente de validar la primera ejecución en GitHub Actions y completar SonarCloud, protección de rama y evidencias de antes/después. No se publican credenciales ni `.env`.
