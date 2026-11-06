# Plan de Aseguramiento de Calidad

## Propósito
Verificar automáticamente la calidad del sistema web de producción frutícola desarrollado en PG2.

## Alcance
Se evaluarán modelos, contraseñas, reglas de generación de alertas, persistencia de datos y análisis estático. El sistema existente conserva Flask, PostgreSQL y las plantillas Bootstrap. Las pruebas aisladas usan SQLite temporal para no alterar datos reales.

## Estándares y criterios
Se toman como referencia buenas prácticas de pruebas automatizadas y las características de mantenibilidad, seguridad y fiabilidad de ISO/IEC 25010. El criterio de aceptación es que las pruebas pasen, la cobertura medida de `models.py` y `servicios_alertas.py` sea al menos 60 %, y Ruff no encuentre errores de las reglas configuradas.

## Actividades y herramientas
- GitHub y GitHub Actions: control de versiones y automatización.
- pytest y pytest-cov: pruebas y cobertura.
- Ruff: análisis estático.
- SonarCloud: integración opcional hasta completar su configuración real.
- Pull requests: revisión de cambios y validación del pipeline.

## Métricas
Casos ejecutados, casos aprobados, porcentaje de cobertura del alcance definido, incidencias del linter y estado del pipeline.

## Riesgos
- Dependencias incompatibles: instalar en Python 3.11 y revisar los errores.
- Falla de cobertura: ampliar pruebas relevantes, sin reducir artificialmente el umbral.
- Credenciales expuestas: excluir `.env` y usar secretos de GitHub.
- Diferencias SQLite/PostgreSQL: validar manualmente el sistema real antes de desplegar.
