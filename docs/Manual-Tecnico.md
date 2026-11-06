# Manual técnico del pipeline

## Arquitectura
Push o pull request → build (instala dependencias y compila Python) → test (pytest y cobertura mínima de 60 %) y analyze (Ruff) → report (resumen y fallo si alguna etapa no aprueba).

## Instalación local
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest --cov --cov-branch --cov-report=term-missing --cov-fail-under=60
python -m ruff check app.py models.py servicios_alertas.py tests/
```

## Mantenimiento
Agregar casos en `tests/`, actualizar la matriz, revisar resultados en Actions y corregir fallos antes de fusionar un pull request. La cobertura actual se mide sobre `models.py` y `servicios_alertas.py`; no representa la cobertura total de `app.py`.

## Protección de main
En GitHub → Settings → Rules → Rulesets, crear una regla para `main`, exigir pull request y la comprobación del workflow una vez que exista una ejecución correcta. Algunas opciones dependen del plan y visibilidad del repositorio.

## SonarCloud
Crear el proyecto en SonarCloud, configurar `sonar.projectKey`, `sonar.organization` y `SONAR_TOKEN` en secretos de GitHub; después agregar su análisis al workflow y comprobar el quality gate real. Esta integración aún no está terminada.
