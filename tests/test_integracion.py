from datetime import date, timedelta
from models import db, Arbol, Actividad, Alerta, Usuario
from servicios_alertas import generar_alertas_automaticas


def agregar_actividad(codigo, fecha, estado="pendiente"):
    arbol = Arbol(codigo=codigo, especie="Manzano")
    db.session.add(arbol)
    db.session.flush()
    actividad = Actividad(arbol_id=arbol.id, tipo="Riego", fecha_programada=fecha, estado=estado)
    db.session.add(actividad)
    db.session.commit()
    return actividad


def test_alerta_actividad_vencida(app):
    actividad = agregar_actividad("V-01", date.today() - timedelta(days=1))
    assert generar_alertas_automaticas() == 1
    alerta = Alerta.query.filter_by(actividad_id=actividad.id).one()
    assert alerta.tipo == "vencida"
    assert "V-01" in alerta.mensaje


def test_alerta_actividad_proxima(app):
    actividad = agregar_actividad("P-01", date.today() + timedelta(days=2))
    assert generar_alertas_automaticas() == 1
    alerta = Alerta.query.filter_by(actividad_id=actividad.id).one()
    assert alerta.tipo == "proxima"
    assert "P-01" in alerta.mensaje


def test_no_alerta_para_actividad_lejana_o_completada(app):
    agregar_actividad("F-01", date.today() + timedelta(days=8))
    agregar_actividad("C-01", date.today(), estado="completada")
    assert generar_alertas_automaticas() == 0
    assert Alerta.query.count() == 0


def test_regresion_no_duplicar_alertas(app):
    agregar_actividad("R-01", date.today())
    assert generar_alertas_automaticas() == 1
    assert generar_alertas_automaticas() == 0
    assert Alerta.query.count() == 1


def test_integracion_usuario_base_de_datos(app):
    usuario = Usuario(nombre="Operador", correo="operador@ejemplo.com", nombre_usuario="operador", rol="operador")
    usuario.establecer_password("Prueba123")
    db.session.add(usuario)
    db.session.commit()
    recuperado = db.session.get(Usuario, usuario.id)
    assert recuperado.verificar_password("Prueba123")
    assert recuperado.rol == "operador"
