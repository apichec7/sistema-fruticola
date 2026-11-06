
from getpass import getpass

from app import app
from models import db, Usuario


with app.app_context():

    correo = input("Correo del administrador: ").strip().lower()
    nombre = input("Nombre del administrador: ").strip()
    password = getpass("Contraseña: ")
    confirmacion = getpass("Confirmar contraseña: ")

    if not correo or not nombre:
        print("El nombre y correo son obligatorios.")

    elif len(password) < 12:
        print("La contraseña debe tener al menos 12 caracteres.")

    elif password != confirmacion:
        print("Las contraseñas no coinciden.")

    elif Usuario.query.filter_by(correo=correo).first():
        print("Ya existe un usuario con ese correo.")

    else:
        administrador = Usuario(
            nombre=nombre,
            correo=correo,
            rol="administrador",
            activo=True
        )

        administrador.establecer_password(password)

        db.session.add(administrador)
        db.session.commit()

        print("Administrador creado correctamente.")
