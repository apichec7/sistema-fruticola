import os
from unittest.mock import patch

import pytest
from app import app as flask_app
from models import db, Usuario

def test_importar_aplicacion():
    with patch.dict(os.environ, {
        "SECRET_KEY": "clave-exclusiva-pruebas",
        "DB_USER": "usuario_pruebas",
        "DB_PASSWORD": "clave_pruebas",
        "DB_HOST": "localhost",
        "DB_NAME": "base_pruebas",
    }):
        from app import app

        assert app is not None
        assert app.name == "app"


def test_login_get():
    from app import app

    app.config["TESTING"] = True

    cliente = app.test_client()
    respuesta = cliente.get("/login")

    assert respuesta.status_code == 200


def test_logout_sin_sesion():
    from app import app

    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    cliente = app.test_client()
    respuesta = cliente.post("/logout")

    assert respuesta.status_code == 302
    assert "/login" in respuesta.headers["Location"]


@pytest.fixture
def cliente_login():
    assert str(flask_app.config["SQLALCHEMY_DATABASE_URI"]).startswith("sqlite:"), (
        "Las pruebas necesitan SQLite. No se permite usar PostgreSQL."
    )

    flask_app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False
    )

    with flask_app.app_context():
        db.create_all()

        usuario = Usuario(
            nombre="Usuario de Prueba",
            correo="prueba@example.com",
            nombre_usuario="usuario_prueba",
            rol="operador",
            activo=True
        )
        usuario.establecer_password("ClavePrueba123")
        db.session.add(usuario)
        db.session.commit()

        yield flask_app.test_client()

        db.session.remove()
        db.drop_all()


def test_login_correcto(cliente_login):
    respuesta = cliente_login.post("/login", data={
        "nombre": "usuario_prueba",
        "password": "ClavePrueba123"
    })

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].endswith("/")


def test_login_password_incorrecta(cliente_login):
    respuesta = cliente_login.post("/login", data={
        "nombre": "usuario_prueba",
        "password": "Incorrecta"
    })

    assert respuesta.status_code == 200


def test_login_usuario_inexistente(cliente_login):
    respuesta = cliente_login.post("/login", data={
        "nombre": "usuario_no_existe",
        "password": "ClavePrueba123"
    })

    assert respuesta.status_code == 200
