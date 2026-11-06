
import os

os.environ["TEST_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "clave-exclusiva-para-pruebas"


import pytest
from flask import Flask
from models import db

@pytest.fixture
def app():
    application = Flask(__name__)
    application.config.update(
        TESTING=True,
        SECRET_KEY="solo-para-pruebas",
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    db.init_app(application)
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()
