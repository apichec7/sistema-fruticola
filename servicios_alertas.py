
from datetime import date, timedelta
from sqlalchemy import select

from models import db, Actividad, Alerta


def generar_alertas_automaticas():
    hoy = date.today()
    limite = hoy + timedelta(days=3)

    # Actividades pendientes que requieren atención
    actividades = db.session.execute(
        select(Actividad).where(
            Actividad.estado == "pendiente",
            Actividad.fecha_programada <= limite
        )
    ).scalars().all()

    nuevas = 0

    for actividad in actividades:

        # Verificar si ya existe una alerta para la actividad
        alerta_existente = db.session.execute(
            select(Alerta).where(
                Alerta.actividad_id == actividad.id
            )
        ).scalars().first()

        # Evitar duplicados, incluso si fue atendida
        if alerta_existente:
            continue

        if actividad.fecha_programada < hoy:
            tipo = "vencida"
            titulo = "Actividad vencida"
            mensaje = (
                f"La actividad '{actividad.tipo}' del árbol "
                f"{actividad.arbol.codigo} está vencida desde "
                f"{actividad.fecha_programada.strftime('%d/%m/%Y')}."
            )
        else:
            tipo = "proxima"
            titulo = "Actividad próxima"
            mensaje = (
                f"La actividad '{actividad.tipo}' del árbol "
                f"{actividad.arbol.codigo} está programada para "
                f"{actividad.fecha_programada.strftime('%d/%m/%Y')}."
            )

        alerta = Alerta(
            actividad_id=actividad.id,
            arbol_id=actividad.arbol_id,
            titulo=titulo,
            mensaje=mensaje,
            tipo=tipo,
            estado="pendiente"
        )

        db.session.add(alerta)
        nuevas += 1

    if nuevas:
        db.session.commit()

    return nuevas
