from datetime import date
from decimal import Decimal
from models import Usuario, Arbol, Actividad, Alerta, Produccion, Configuracion


def test_password_valida():
    usuario = Usuario(nombre="Prueba", correo="prueba@ejemplo.com", rol="operador")
    usuario.establecer_password("ClaveSegura123")
    assert usuario.verificar_password("ClaveSegura123")
    assert usuario.password_hash != "ClaveSegura123"


def test_password_incorrecta():
    usuario = Usuario(nombre="Prueba", correo="prueba@ejemplo.com")
    usuario.establecer_password("ClaveSegura123")
    assert not usuario.verificar_password("otra-clave")


def test_valores_predeterminados(app):
    from models import db
    arbol = Arbol(codigo="A-01", especie="Manzano")
    db.session.add(arbol)
    db.session.commit()
    assert arbol.estado == "activo"
    actividad = Actividad(arbol_id=arbol.id, tipo="Riego", fecha_programada=date.today())
    db.session.add(actividad)
    db.session.commit()
    assert actividad.estado == "pendiente"


def test_produccion_y_configuracion(app):
    from models import db
    arbol = Arbol(codigo="A-02", especie="Pera")
    db.session.add(arbol)
    db.session.flush()
    produccion = Produccion(arbol_id=arbol.id, fecha_cosecha=date.today(), cantidad_kg=Decimal("12.50"), calidad="alta")
    config = Configuracion()
    db.session.add_all([produccion, config])
    db.session.commit()
    assert produccion.arbol.codigo == "A-02"
    assert produccion.cantidad_kg == Decimal("12.50")
    assert config.nombre_unidad == "Unidad de producción frutícola"

