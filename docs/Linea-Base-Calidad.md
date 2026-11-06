# Línea base de calidad

## 1. Situación inicial

Durante la revisión inicial del proyecto no se encontraron pruebas automatizadas ni un pipeline CI/CD configurado en los archivos evaluados.

Tampoco se contaba con una medición inicial de cobertura del código.

## 2. Métricas iniciales

| Métrica | Situación inicial |
|---|---|
| Pruebas automatizadas | No se encontraron |
| Pipeline GitHub Actions | No se encontró |
| Cobertura medida | No disponible |
| Análisis estático | 4 errores detectados con Ruff |
| Bugs y code smells SonarCloud | No medidos |
| Protección de ramas | Sin regla configurada |

La ausencia de una medición inicial de cobertura no significa que la cobertura fuera del 0%.

## 3. Errores identificados

Durante la primera ejecución del análisis estático con Ruff se encontraron cuatro errores en el archivo app.py.

| Código | Cantidad | Descripción |
|---|---|---|
| E402 | 1 | Importación ubicada fuera de la sección correspondiente |
| F821 | 3 | Uso de la función escape sin importar |
| Total | 4 | Errores identificados inicialmente |

## 4. Correcciones realizadas

Se corrigió la ubicación de la importación de Decimal e InvalidOperation.

También se agregó la importación correspondiente de la función escape.

Después de realizar las correcciones se ejecutó nuevamente Ruff y se obtuvo el resultado:

All checks passed!

## 5. Resultado de la comparación

Los errores detectados inicialmente por Ruff disminuyeron de cuatro a cero en los archivos evaluados.

También se incorporaron pruebas automatizadas, medición de cobertura y un pipeline CI/CD para realizar verificaciones de calidad durante las modificaciones del proyecto.

Las métricas de SonarCloud todavía no han sido obtenidas, por lo que no se incluyen valores de bugs, vulnerabilidades o code smells sin una medición real.
