
# Matriz de Pruebas

## Sistema web de producción frutícola

La matriz de pruebas permite organizar los casos utilizados para comprobar el funcionamiento de diferentes módulos del sistema, incluyendo pruebas unitarias, de integración y de regresión.

| ID | Tipo | Entrada | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|---|---|---|
| CP-01 | Unitaria | Contraseña ClaveSegura123 | La contraseña se valida y almacena como hash | Contraseña validada y hash generado | Aprobada |
| CP-02 | Unitaria | Contraseña otra-clave | La contraseña incorrecta es rechazada | Verificación falsa | Aprobada |
| CP-03 | Unitaria | Árbol A-01 y actividad de riego | Estados activo y pendiente | Estados asignados correctamente | Aprobada |
| CP-04 | Unitaria | Árbol A-02, producción de 12.50 kg y configuración | Relación y valores correctos | Valores comprobados | Aprobada |
| CP-05 | Integración | Actividad vencida hace un día | Crear una alerta vencida | Se creó una alerta vencida | Aprobada |
| CP-06 | Integración | Actividad programada dentro de dos días | Crear una alerta próxima | Se creó una alerta próxima | Aprobada |
| CP-07 | Integración | Actividad lejana y actividad completada | No generar alertas | No se generaron alertas | Aprobada |
| CP-08 | Regresión | Ejecutar dos veces la generación de alertas | Evitar alertas duplicadas | Se conservó una sola alerta | Aprobada |
| CP-09 | Integración | Usuario operador con contraseña Prueba123 | Guardar y recuperar el usuario correctamente | Usuario recuperado y contraseña validada | Aprobada |

## Resultados generales

- Total de pruebas: 9
- Pruebas aprobadas: 9
- Pruebas fallidas: 0
- Herramienta utilizada: pytest
- Cobertura medida: 100% en models.py y servicios_alertas.py
- Cobertura mínima configurada: 60%

Las pruebas se ejecutaron correctamente y permitieron comprobar las funciones seleccionadas del sistema.
