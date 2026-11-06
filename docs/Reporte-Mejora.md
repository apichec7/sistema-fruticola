# Reporte de mejora

## 1. Cambios implementados

Se implementaron pruebas automatizadas utilizando pytest, medicion de cobertura con pytest-cov y analisis estatico mediante Ruff.

Tambien se configuro un pipeline CI/CD en GitHub Actions con cuatro etapas: build, test, analyze y report.

Se agregaron controles de calidad para verificar automaticamente las pruebas y el analisis estatico antes de integrar cambios al proyecto.

## 2. Correccion de errores

Durante el analisis inicial con Ruff se encontraron cuatro errores en el archivo app.py.

- Un error E402 relacionado con una importacion ubicada fuera de la seccion correspondiente.
- Tres errores F821 relacionados con el uso de la funcion escape sin haberla importado.

Se corrigieron las importaciones correspondientes y se ejecuto nuevamente Ruff.

Resultado final: All checks passed!

## 3. Metricas obtenidas

| Metrica | Resultado |
|---|---|
| Pruebas automatizadas | 9 |
| Pruebas aprobadas | 9 |
| Pruebas fallidas | 0 |
| Cobertura de models.py y servicios_alertas.py | 100% |
| Cobertura minima requerida | 60% |
| Errores iniciales de Ruff | 4 |
| Errores finales de Ruff | 0 |
| Etapas del pipeline | 4 |
| Etapas aprobadas | 4 |

La cobertura del 100% corresponde solamente a los archivos models.py y servicios_alertas.py, no a toda la aplicacion.

## 4. Comparativa antes y despues

| Indicador | Antes | Despues |
|---|---|---|
| Errores Ruff | 4 | 0 |
| Pruebas automatizadas | Sin suite SQA documentada | 9 aprobadas |
| Cobertura | Sin medicion inicial | 100% en los modulos evaluados |
| Pipeline CI/CD | No configurado | Cuatro etapas funcionando |
| Quality Gates | No configurados | Configurados y verificados |
| Proteccion de main | Sin regla configurada | Pull Request y aprobacion requeridos |

## 5. Verificacion del pipeline

Se comprobo el funcionamiento del pipeline mediante GitHub Actions.

Durante una prueba se agrego temporalmente un caso de prueba incorrecto para verificar que el pipeline detectara el fallo.

El resultado mostro que las etapas test y report fallaron, impidiendo que la ejecucion se considerara correcta.

Posteriormente se elimino la prueba temporal y se ejecuto nuevamente el pipeline, obteniendo resultados satisfactorios en las cuatro etapas.

## 6. Proteccion de ramas

Se configuro una regla de proteccion para la rama main.

La regla solicita utilizar Pull Requests, contar con una aprobacion y completar las verificaciones obligatorias antes de integrar cambios.

Se creo un Pull Request desde feature/sqa-pipeline hacia main y se comprobo que GitHub bloqueaba la integracion mientras no se cumpliera con la aprobacion requerida.

## 7. Resultados y conclusiones

La implementacion de las pruebas automatizadas, el analisis estatico y el pipeline CI/CD permitio establecer controles para detectar errores durante las modificaciones del sistema.

Se corrigieron los cuatro errores identificados inicialmente por Ruff y las nueve pruebas automatizadas finalizaron correctamente.

Tambien se incorporaron verificaciones automaticas y proteccion de ramas para reducir el riesgo de integrar cambios sin las revisiones correspondientes.

Estos resultados representan una mejora en los procesos de aseguramiento de calidad del proyecto.

## 8. Analisis adicional

No se cuenta todavia con metricas verificadas de bugs, vulnerabilidades o code smells provenientes de SonarCloud. Estas metricas requieren configurar y ejecutar dicha herramienta o un analizador equivalente.
