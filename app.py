import os

from decimal import Decimal, InvalidOperation
from xml.sax.saxutils import escape
from io import BytesIO
from datetime import datetime
from flask import send_file
from sqlalchemy.orm import joinedload

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from datetime import timedelta
from decimal import Decimal
from sqlalchemy import extract
from pathlib import Path
from datetime import datetime, timezone, date

from dotenv import load_dotenv

from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, session
)

from functools import wraps
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate

from sqlalchemy import text
from sqlalchemy.engine import URL

from models import db, Arbol, Actividad, Alerta, Usuario, Produccion, Configuracion
from servicios_alertas import generar_alertas_automaticas


# ==========================================
# 1. CONFIGURACIÓN DE AGROCONTROL
# ==========================================

load_dotenv(
    dotenv_path=Path(__file__).resolve().parent / ".env"
)

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError(
        "Debes configurar SECRET_KEY en el archivo .env"
    )

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=60)

app.config["SQLALCHEMY_DATABASE_URI"] = URL.create(
    drivername="postgresql+psycopg",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "5432")),
    database=os.getenv("DB_NAME")
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
migrate = Migrate(app, db)
csrf = CSRFProtect(app)



@app.context_processor
def datos_usuario_actual():

    usuario_id = session.get("usuario_id")

    usuario_actual = None

    if usuario_id:
        usuario_actual = db.session.get(
            Usuario, usuario_id
        )

    def obtener_usuario_actual():
        return usuario_actual

    def tiene_rol(*roles):
        return (
            usuario_actual is not None
            and usuario_actual.activo
            and usuario_actual.rol in roles
        )

    return {
        "obtener_usuario_actual": obtener_usuario_actual,
        "tiene_rol": tiene_rol
    }



# ==========================================
# 2. PROTECCIÓN DE RUTAS
# ==========================================

@app.before_request
def verificar_acceso():

    rutas_publicas = {"login", "static"}

    if request.endpoint is None:
        return

    if request.endpoint in rutas_publicas:
        return

    usuario_id = session.get("usuario_id")

    if not usuario_id:
        return redirect(url_for("login"))

    usuario = db.session.get(Usuario, usuario_id)

    if not usuario or not usuario.activo:
        session.clear()

        flash(
            "Debes iniciar sesión para continuar.",
            "warning"
        )

        return redirect(url_for("login"))


# ==========================================
# PERMISOS POR ROL
# ==========================================


def roles_permitidos(*roles):

    def decorador(funcion):

        @wraps(funcion)
        def verificar_permiso(*args, **kwargs):

            usuario_id = session.get("usuario_id")

            if not usuario_id:
                flash(
                    "Debes iniciar sesión.",
                    "warning"
                )
                return redirect(url_for("login"))

            usuario = db.session.get(
                Usuario, usuario_id
            )

            if not usuario or not usuario.activo:
                session.clear()
                return redirect(url_for("login"))

            if usuario.rol not in roles:
                flash(
                    "No tienes permisos para realizar esta acción.",
                    "danger"
                )
                return redirect(url_for("inicio"))

            return funcion(*args, **kwargs)

        return verificar_permiso

    return decorador


# Conservamos este decorador para no modificar
# las rutas existentes de gestión de usuarios.
solo_administrador = roles_permitidos("administrador")




# ==========================================
# 3. INICIO DE SESIÓN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    usuario_id = session.get("usuario_id")

    if usuario_id:
        usuario_actual = db.session.get(
            Usuario, usuario_id
        )

        if usuario_actual and usuario_actual.activo:
            return redirect(url_for("inicio"))

        session.clear()

    if request.method == "POST":

        
        
        nombre = request.form.get(
            "nombre", ""
        ).strip().lower()

        password = request.form.get("password", "")

        usuario = Usuario.query.filter(
            db.func.lower(Usuario.nombre_usuario) == nombre
        ).first()



        if (
            usuario
            and usuario.activo
            and usuario.verificar_password(password)
        ):

            session.clear()
            session["usuario_id"] = usuario.id
            session.permanent = True

            flash(
                "Bienvenido",
                "success"
            )

            return redirect(url_for("inicio"))

        flash(
            "Usuario o contraseña incorrectos.",
            "danger"
        )

    return render_template("login.html")


# ==========================================
# 4. CERRAR SESIÓN
# ==========================================

@app.route("/logout", methods=["POST"])
def logout():

    session.clear()

    flash(
        "Sesión cerrada correctamente.",
        "success"
    )

    return redirect(url_for("login"))



# ==========================================
# DASHBOARD PRINCIPAL
# ==========================================

@app.route("/")
def inicio():

    hoy = date.today()

    # ======================================
    # INDICADORES DE ÁRBOLES Y ACTIVIDADES
    # ======================================

    total_arboles = Arbol.query.filter_by(
        estado="activo"
    ).count()

    actividades_pendientes = Actividad.query.filter_by(
        estado="pendiente"
    ).count()

    actividades_completadas = Actividad.query.filter_by(
        estado="completada"
    ).count()

    actividades_vencidas = Actividad.query.filter(
        Actividad.estado == "pendiente",
        Actividad.fecha_programada < hoy
    ).count()

    proximas_actividades = Actividad.query.filter(
        Actividad.estado == "pendiente",
        Actividad.fecha_programada >= hoy
    ).order_by(
        Actividad.fecha_programada.asc()
    ).limit(5).all()

    # ======================================
    # INDICADORES DE PRODUCCIÓN
    # ======================================

    total_cosechas = Produccion.query.count()

    total_kg = db.session.query(
        db.func.coalesce(
            db.func.sum(Produccion.cantidad_kg),
            0
        )
    ).scalar()

    promedio_kg = (
        total_kg / total_cosechas
        if total_cosechas > 0
        else Decimal("0")
    )

    # ======================================
    # PRODUCCIÓN DE LOS ÚLTIMOS 12 MESES
    # ======================================

    meses = []
    valores_mensuales = []

    primer_mes = date(hoy.year, hoy.month, 1)

    for desplazamiento in range(11, -1, -1):

        numero_mes = (
            primer_mes.year * 12
            + primer_mes.month - 1
            - desplazamiento
        )

        anio = numero_mes // 12
        mes = numero_mes % 12 + 1

        inicio_mes = date(anio, mes, 1)

        if mes == 12:
            fin_mes = date(anio + 1, 1, 1)
        else:
            fin_mes = date(anio, mes + 1, 1)

        cantidad = db.session.query(
            db.func.coalesce(
                db.func.sum(Produccion.cantidad_kg),
                0
            )
        ).filter(
            Produccion.fecha_cosecha >= inicio_mes,
            Produccion.fecha_cosecha < fin_mes
        ).scalar()

        meses.append(
            inicio_mes.strftime("%m/%Y")
        )

        valores_mensuales.append(
            float(cantidad)
        )

    # ======================================
    # PRODUCCIÓN AGRUPADA POR ESPECIE
    # ======================================

    produccion_especies = db.session.query(
        Arbol.especie,
        db.func.sum(
            Produccion.cantidad_kg
        ).label("total")
    ).join(
        Produccion,
        Produccion.arbol_id == Arbol.id
    ).group_by(
        Arbol.especie
    ).order_by(
        db.func.sum(
            Produccion.cantidad_kg
        ).desc()
    ).all()

    especies = [
        registro.especie
        for registro in produccion_especies
    ]

    cantidades_especies = [
        float(registro.total)
        for registro in produccion_especies
    ]

    # ======================================
    # ÚLTIMAS COSECHAS
    # ======================================

    ultimas_cosechas = Produccion.query.order_by(
        Produccion.fecha_cosecha.desc(),
        Produccion.id.desc()
    ).limit(5).all()

    # ======================================
    # MOSTRAR DASHBOARD
    # ======================================

    return render_template(
        "index.html",

        total_arboles=total_arboles,
        actividades_pendientes=actividades_pendientes,
        actividades_completadas=actividades_completadas,
        actividades_vencidas=actividades_vencidas,
        proximas_actividades=proximas_actividades,

        total_cosechas=total_cosechas,
        total_kg=total_kg,
        promedio_kg=promedio_kg,

        meses=meses,
        valores_mensuales=valores_mensuales,

        especies=especies,
        cantidades_especies=cantidades_especies,

        ultimas_cosechas=ultimas_cosechas
    )


# ==========================================
# 6. PROBAR CONEXIÓN POSTGRESQL
# ==========================================

@app.route("/probar-conexion")
def probar_conexion():

    try:
        with db.engine.connect() as conexion:

            resultado = conexion.execute(
                text("SELECT current_database()")
            ).scalar()

        return (
            "Conexión exitosa con PostgreSQL. "
            f"Base de datos: {resultado}"
        )

    except Exception:
        app.logger.exception("Error de conexión")

        return (
            "Error al conectar con PostgreSQL.",
            500
        )


# ==========================================
# 7. LISTAR ÁRBOLES
# ==========================================

@app.route("/arboles")
def listar_arboles():

    arboles = Arbol.query.order_by(
        Arbol.id.desc()
    ).all()

    return render_template(
        "arboles.html",
        arboles=arboles
    )


# ==========================================
# 8. REGISTRAR ÁRBOL
# ==========================================

@app.route("/arboles/nuevo", methods=["GET", "POST"])
@roles_permitidos("administrador", "supervisor")
def nuevo_arbol():

    if request.method == "POST":

        codigo = request.form.get(
            "codigo", ""
        ).strip().upper()

        especie = request.form.get(
            "especie", ""
        ).strip()

        variedad = request.form.get(
            "variedad", ""
        ).strip()

        ubicacion = request.form.get(
            "ubicacion", ""
        ).strip()

        if not codigo or not especie:

            flash(
                "El código y la especie son obligatorios.",
                "danger"
            )

            return redirect(url_for("nuevo_arbol"))

        existente = Arbol.query.filter_by(
            codigo=codigo
        ).first()

        if existente:

            flash(
                "Ya existe un árbol con ese código.",
                "danger"
            )

            return redirect(url_for("nuevo_arbol"))

        arbol = Arbol(
            codigo=codigo,
            especie=especie,
            variedad=variedad,
            ubicacion=ubicacion,
            estado="activo"
        )

        db.session.add(arbol)
        db.session.commit()

        flash(
            "Árbol registrado correctamente.",
            "success"
        )

        return redirect(url_for("listar_arboles"))

    return render_template(
        "form_arbol.html",
        arbol=None
    )


# ==========================================
# 9. EDITAR ÁRBOL
# ==========================================

@app.route("/arboles/editar/<int:id>", methods=["GET", "POST"])
@roles_permitidos("administrador", "supervisor")
def editar_arbol(id):

    arbol = db.get_or_404(Arbol, id)

    if request.method == "POST":

        codigo = request.form.get(
            "codigo", ""
        ).strip().upper()

        especie = request.form.get(
            "especie", ""
        ).strip()

        if not codigo or not especie:

            flash(
                "El código y la especie son obligatorios.",
                "danger"
            )

            return redirect(
                url_for("editar_arbol", id=id)
            )

        existente = Arbol.query.filter_by(
            codigo=codigo
        ).first()

        if existente and existente.id != arbol.id:

            flash(
                "Ese código ya está registrado.",
                "danger"
            )

            return redirect(
                url_for("editar_arbol", id=id)
            )

        arbol.codigo = codigo
        arbol.especie = especie

        arbol.variedad = request.form.get(
            "variedad", ""
        ).strip()

        arbol.ubicacion = request.form.get(
            "ubicacion", ""
        ).strip()

        db.session.commit()

        flash(
            "Árbol actualizado correctamente.",
            "success"
        )

        return redirect(url_for("listar_arboles"))

    return render_template(
        "form_arbol.html",
        arbol=arbol
    )


# ==========================================
# 10. DESACTIVAR ÁRBOL
# ==========================================

@app.route("/arboles/desactivar/<int:id>", methods=["POST"])
@roles_permitidos("administrador")
def desactivar_arbol(id):

    arbol = db.get_or_404(Arbol, id)

    arbol.estado = "inactivo"

    db.session.commit()

    flash(
        "Árbol desactivado correctamente.",
        "warning"
    )

    return redirect(url_for("listar_arboles"))


# ==========================================
# 11. LISTAR ACTIVIDADES
# ==========================================

@app.route("/actividades")
def listar_actividades():

    actividades = Actividad.query.order_by(
        Actividad.fecha_programada.desc()
    ).all()

    return render_template(
        "actividades.html",
        actividades=actividades
    )


# ==========================================
# 12. REGISTRAR ACTIVIDAD
# ==========================================

@app.route("/actividades/nueva", methods=["GET", "POST"])
@roles_permitidos("administrador", "supervisor", "operador")
def nueva_actividad():

    arboles = Arbol.query.filter_by(
        estado="activo"
    ).order_by(
        Arbol.codigo
    ).all()

    if request.method == "POST":

        try:
            arbol_id = int(
                request.form.get("arbol_id", "")
            )

            fecha_programada = date.fromisoformat(
                request.form.get("fecha_programada", "")
            )

        except (ValueError, TypeError):

            flash(
                "Selecciona un árbol y una fecha válida.",
                "danger"
            )

            return redirect(url_for("nueva_actividad"))

        arbol = db.session.get(
            Arbol, arbol_id
        )

        tipo = request.form.get(
            "tipo", ""
        ).strip()

        descripcion = request.form.get(
            "descripcion", ""
        ).strip()

        if not arbol or arbol.estado != "activo" or not tipo:

            flash(
                "Verifica el árbol y el tipo de actividad.",
                "danger"
            )

            return redirect(url_for("nueva_actividad"))

        actividad = Actividad(
            arbol_id=arbol_id,
            tipo=tipo,
            descripcion=descripcion,
            fecha_programada=fecha_programada,
            estado="pendiente"
        )

        db.session.add(actividad)
        db.session.commit()

        flash(
            "Actividad registrada correctamente.",
            "success"
        )

        return redirect(url_for("listar_actividades"))

    return render_template(
        "form_actividad.html",
        arboles=arboles
    )


# ==========================================
# 13. COMPLETAR ACTIVIDAD
# ==========================================

@app.route("/actividades/completar/<int:id>", methods=["POST"])
@roles_permitidos("administrador", "supervisor", "operador")
def completar_actividad(id):

    actividad = db.get_or_404(
        Actividad, id
    )

    if actividad.estado != "completada":

        actividad.estado = "completada"
        actividad.fecha_realizada = date.today()

        db.session.commit()

        flash(
            "Actividad completada correctamente.",
            "success"
        )

    else:

        flash(
            "Esta actividad ya estaba completada.",
            "warning"
        )

    return redirect(url_for("listar_actividades"))


# ==========================================
# 14. LISTAR ALERTAS
# ==========================================

@app.route("/alertas")
def listar_alertas():

    generar_alertas_automaticas()

    pagina = request.args.get(
        "pagina", 1, type=int
    )

    por_pagina = request.args.get(
        "por_pagina", 10, type=int
    )

    if pagina < 1:
        pagina = 1

    if por_pagina not in [10, 20, 50]:
        por_pagina = 10

    estado = request.args.get("estado", "")
    tipo = request.args.get("tipo", "")

    consulta = Alerta.query

    if estado in ["pendiente", "atendida"]:

        consulta = consulta.filter(
            Alerta.estado == estado
        )

    else:
        estado = ""

    if tipo in ["vencida", "proxima"]:

        consulta = consulta.filter(
            Alerta.tipo == tipo
        )

    else:
        tipo = ""

    paginacion = consulta.order_by(
        Alerta.fecha_creacion.desc(),
        Alerta.id.desc()
    ).paginate(
        page=pagina,
        per_page=por_pagina,
        error_out=False
    )

    total_alertas = Alerta.query.count()

    pendientes = Alerta.query.filter_by(
        estado="pendiente"
    ).count()

    atendidas = Alerta.query.filter_by(
        estado="atendida"
    ).count()

    return render_template(
        "alertas.html",
        alertas=paginacion.items,
        paginacion=paginacion,
        total_alertas=total_alertas,
        pendientes=pendientes,
        atendidas=atendidas,
        estado=estado,
        tipo=tipo,
        por_pagina=por_pagina
    )


# ==========================================
# 15. ATENDER ALERTA
# ==========================================

@app.route("/alertas/atender/<int:id>", methods=["POST"])
@roles_permitidos("administrador", "supervisor")
def atender_alerta(id):

    alerta = db.get_or_404(
        Alerta, id
    )

    if alerta.estado != "atendida":

        alerta.estado = "atendida"

        alerta.fecha_atencion = datetime.now(
            timezone.utc
        )

        db.session.commit()

        flash(
            "Alerta marcada como atendida.",
            "success"
        )

    else:

        flash(
            "Esta alerta ya fue atendida.",
            "warning"
        )

    return redirect(url_for("listar_alertas"))


# ==========================================
# 16. HISTORIAL DE ACTIVIDADES
# ==========================================

@app.route("/historial")
def historial_actividades():

    pagina = request.args.get(
        "pagina", 1, type=int
    )

    por_pagina = request.args.get(
        "por_pagina", 10, type=int
    )

    arbol_id = request.args.get(
        "arbol_id", type=int
    )

    estado = request.args.get(
        "estado", ""
    )

    if pagina < 1:
        pagina = 1

    if por_pagina not in [10, 20, 50]:
        por_pagina = 10

    consulta = Actividad.query

    if arbol_id:

        consulta = consulta.filter(
            Actividad.arbol_id == arbol_id
        )

    if estado in ["pendiente", "completada"]:

        consulta = consulta.filter(
            Actividad.estado == estado
        )

    else:
        estado = ""

    paginacion = consulta.order_by(
        Actividad.fecha_programada.desc(),
        Actividad.id.desc()
    ).paginate(
        page=pagina,
        per_page=por_pagina,
        error_out=False
    )

    arboles = Arbol.query.order_by(
        Arbol.codigo.asc()
    ).all()

    total = Actividad.query.count()

    completadas = Actividad.query.filter_by(
        estado="completada"
    ).count()

    pendientes = Actividad.query.filter_by(
        estado="pendiente"
    ).count()

    return render_template(
        "historial.html",
        actividades=paginacion.items,
        paginacion=paginacion,
        arboles=arboles,
        arbol_id=arbol_id,
        estado=estado,
        por_pagina=por_pagina,
        total=total,
        completadas=completadas,
        pendientes=pendientes
    )




# ==========================================
# 18. LISTAR USUARIOS
# ==========================================

@app.route("/usuarios")
@solo_administrador
def listar_usuarios():

    pagina = request.args.get("pagina", 1, type=int)
    por_pagina = request.args.get("por_pagina", 10, type=int)
    buscar = request.args.get("buscar", "").strip()

    if pagina < 1:
        pagina = 1

    if por_pagina not in [10, 20, 50]:
        por_pagina = 10

    consulta = Usuario.query

    if buscar:
        patron = f"%{buscar}%"

        consulta = consulta.filter(
            db.or_(
                Usuario.nombre.ilike(patron),
                Usuario.nombre_usuario.ilike(patron),
                Usuario.correo.ilike(patron)
            )
        )

    paginacion = consulta.order_by(
        Usuario.id.desc()
    ).paginate(
        page=pagina,
        per_page=por_pagina,
        error_out=False
    )

    total = Usuario.query.count()
    activos = Usuario.query.filter_by(activo=True).count()
    inactivos = Usuario.query.filter_by(activo=False).count()

    return render_template(
        "usuarios.html",
        usuarios=paginacion.items,
        paginacion=paginacion,
        total=total,
        activos=activos,
        inactivos=inactivos,
        buscar=buscar,
        por_pagina=por_pagina
    )


# ==========================================
# 19. REGISTRAR USUARIO
# ==========================================

@app.route("/usuarios/nuevo", methods=["GET", "POST"])
@solo_administrador
def nuevo_usuario():

    if request.method == "POST":

        nombre = request.form.get("nombre", "").strip()
        nombre_usuario = request.form.get(
            "nombre_usuario", ""
        ).strip().lower()

        correo = request.form.get(
            "correo", ""
        ).strip().lower()

        password = request.form.get("password", "")
        rol = request.form.get("rol", "")

        if not nombre or not nombre_usuario or not correo:
            flash("Completa los campos obligatorios.", "danger")
            return redirect(url_for("nuevo_usuario"))

        if not nombre_usuario.isascii() or not all(
            c.isalnum() or c == "_" for c in nombre_usuario
        ):
            flash(
                "El usuario solo puede contener letras, números y guion bajo.",
                "danger"
            )
            return redirect(url_for("nuevo_usuario"))

        if len(nombre_usuario) > 50:
            flash("El nombre de usuario es demasiado largo.", "danger")
            return redirect(url_for("nuevo_usuario"))

        if rol not in ["administrador", "supervisor", "operador"]:
            flash("Selecciona un rol válido.", "danger")
            return redirect(url_for("nuevo_usuario"))

        if len(password) < 12:
            flash(
                "La contraseña debe tener al menos 12 caracteres.",
                "danger"
            )
            return redirect(url_for("nuevo_usuario"))

        if Usuario.query.filter(
            db.func.lower(Usuario.nombre_usuario) == nombre_usuario
        ).first():
            flash("Ese nombre de usuario ya existe.", "danger")
            return redirect(url_for("nuevo_usuario"))

        if Usuario.query.filter_by(correo=correo).first():
            flash("Ese correo ya está registrado.", "danger")
            return redirect(url_for("nuevo_usuario"))

        usuario = Usuario(
            nombre=nombre,
            nombre_usuario=nombre_usuario,
            correo=correo,
            rol=rol,
            activo=True
        )

        usuario.establecer_password(password)

        db.session.add(usuario)
        db.session.commit()

        flash("Usuario registrado correctamente.", "success")
        return redirect(url_for("listar_usuarios"))

    return render_template(
        "form_usuario.html",
        usuario=None
    )


# ==========================================
# 20. EDITAR USUARIO
# ==========================================

@app.route("/usuarios/editar/<int:id>", methods=["GET", "POST"])
@solo_administrador
def editar_usuario(id):

    usuario = db.get_or_404(Usuario, id)

    if request.method == "POST":

        nombre = request.form.get("nombre", "").strip()
        nombre_usuario = request.form.get(
            "nombre_usuario", ""
        ).strip().lower()

        correo = request.form.get(
            "correo", ""
        ).strip().lower()

        rol = request.form.get("rol", "")
        password = request.form.get("password", "")

        if not nombre or not nombre_usuario or not correo:
            flash("Completa los campos obligatorios.", "danger")
            return redirect(url_for("editar_usuario", id=id))

        if not nombre_usuario.isascii() or not all(
            c.isalnum() or c == "_" for c in nombre_usuario
        ):
            flash("Nombre de usuario inválido.", "danger")
            return redirect(url_for("editar_usuario", id=id))

        if len(nombre_usuario) > 50:
            flash("El nombre de usuario es demasiado largo.", "danger")
            return redirect(url_for("editar_usuario", id=id))

        if rol not in ["administrador", "supervisor", "operador"]:
            flash("Selecciona un rol válido.", "danger")
            return redirect(url_for("editar_usuario", id=id))

        existente = Usuario.query.filter(
            db.func.lower(Usuario.nombre_usuario) == nombre_usuario,
            Usuario.id != id
        ).first()

        if existente:
            flash("Ese nombre de usuario ya existe.", "danger")
            return redirect(url_for("editar_usuario", id=id))

        correo_existente = Usuario.query.filter(
            Usuario.correo == correo,
            Usuario.id != id
        ).first()

        if correo_existente:
            flash("Ese correo ya está registrado.", "danger")
            return redirect(url_for("editar_usuario", id=id))

        if usuario.id == session.get("usuario_id"):
            if rol != "administrador":
                flash(
                    "No puedes quitarte tu propio rol de administrador.",
                    "danger"
                )
                return redirect(url_for("editar_usuario", id=id))

        if password and len(password) < 12:
            flash(
                "La nueva contraseña debe tener al menos 12 caracteres.",
                "danger"
            )
            return redirect(url_for("editar_usuario", id=id))

        usuario.nombre = nombre
        usuario.nombre_usuario = nombre_usuario
        usuario.correo = correo
        usuario.rol = rol

        if password:
            usuario.establecer_password(password)

        db.session.commit()

        flash("Usuario actualizado correctamente.", "success")
        return redirect(url_for("listar_usuarios"))

    return render_template(
        "form_usuario.html",
        usuario=usuario
    )


# ==========================================
# 21. ACTIVAR O DESACTIVAR USUARIO
# ==========================================

@app.route("/usuarios/estado/<int:id>", methods=["POST"])
@solo_administrador
def cambiar_estado_usuario(id):

    usuario = db.get_or_404(Usuario, id)

    if usuario.id == session.get("usuario_id"):
        flash(
            "No puedes desactivar tu propia cuenta.",
            "danger"
        )
        return redirect(url_for("listar_usuarios"))

    usuario.activo = not usuario.activo

    db.session.commit()

    flash("Estado del usuario actualizado.", "success")

    return redirect(url_for("listar_usuarios"))


# ==========================================
# 22. MÓDULO DE PRODUCCIÓN FRUTÍCOLA
# ==========================================




# ==========================================
# LISTAR PRODUCCIÓN
# ==========================================

@app.route("/produccion")
def listar_produccion():

    pagina = request.args.get("pagina", 1, type=int)
    por_pagina = request.args.get("por_pagina", 10, type=int)
    arbol_id = request.args.get("arbol_id", type=int)

    if pagina < 1:
        pagina = 1

    if por_pagina not in [10, 20, 50]:
        por_pagina = 10

    consulta = Produccion.query

    if arbol_id:
        consulta = consulta.filter(
            Produccion.arbol_id == arbol_id
        )

    paginacion = consulta.order_by(
        Produccion.fecha_cosecha.desc(),
        Produccion.id.desc()
    ).paginate(
        page=pagina,
        per_page=por_pagina,
        error_out=False
    )

    arboles = Arbol.query.order_by(
        Arbol.codigo.asc()
    ).all()

    total_cosechas = Produccion.query.count()

    total_kg = db.session.query(
        db.func.coalesce(
            db.func.sum(Produccion.cantidad_kg), 0
        )
    ).scalar()

    promedio_kg = (
        total_kg / total_cosechas
        if total_cosechas > 0
        else Decimal("0")
    )

    return render_template(
        "produccion.html",
        producciones=paginacion.items,
        paginacion=paginacion,
        arboles=arboles,
        arbol_id=arbol_id,
        por_pagina=por_pagina,
        total_cosechas=total_cosechas,
        total_kg=total_kg,
        promedio_kg=promedio_kg
    )


# ==========================================
# REGISTRAR PRODUCCIÓN
# ==========================================

@app.route("/produccion/nueva", methods=["GET", "POST"])
@roles_permitidos("administrador", "supervisor")
def nueva_produccion():

    arboles = Arbol.query.filter_by(
        estado="activo"
    ).order_by(
        Arbol.codigo.asc()
    ).all()

    if request.method == "POST":

        try:
            arbol_id = int(
                request.form.get("arbol_id", "")
            )

            fecha_cosecha = date.fromisoformat(
                request.form.get("fecha_cosecha", "")
            )

            cantidad_kg = Decimal(
                request.form.get("cantidad_kg", "")
            )

        except (ValueError, TypeError, InvalidOperation):

            flash(
                "Verifica el árbol, la fecha y la cantidad.",
                "danger"
            )

            return redirect(url_for("nueva_produccion"))

        calidad = request.form.get(
            "calidad", ""
        ).strip().lower()

        observaciones = request.form.get(
            "observaciones", ""
        ).strip()

        arbol = db.session.get(Arbol, arbol_id)

        if not arbol or arbol.estado != "activo":

            flash(
                "Debes seleccionar un árbol activo.",
                "danger"
            )

            return redirect(url_for("nueva_produccion"))

        if fecha_cosecha > date.today():

            flash(
                "La fecha de cosecha no puede ser futura.",
                "danger"
            )

            return redirect(url_for("nueva_produccion"))

        if (
            not cantidad_kg.is_finite()
            or cantidad_kg <= 0
            or cantidad_kg > Decimal("99999999.99")
            or cantidad_kg.as_tuple().exponent < -2
        ):

            flash(
                "La cantidad debe ser positiva y tener máximo dos decimales.",
                "danger"
            )

            return redirect(url_for("nueva_produccion"))

        if calidad not in ["buena", "regular", "mala"]:

            flash(
                "Selecciona una calidad válida.",
                "danger"
            )

            return redirect(url_for("nueva_produccion"))

        produccion = Produccion(
            arbol_id=arbol_id,
            responsable_id=session.get("usuario_id"),
            fecha_cosecha=fecha_cosecha,
            cantidad_kg=cantidad_kg,
            calidad=calidad,
            observaciones=observaciones
        )

        db.session.add(produccion)
        db.session.commit()

        flash(
            "Cosecha registrada correctamente.",
            "success"
        )

        return redirect(url_for("listar_produccion"))

    return render_template(
        "form_produccion.html",
        arboles=arboles
    )


# ==========================================
# EDITAR PRODUCCIÓN
# ==========================================

@app.route(
    "/produccion/editar/<int:id>",
    methods=["GET", "POST"]
)
@roles_permitidos("administrador", "supervisor")
def editar_produccion(id):

    produccion = db.get_or_404(Produccion, id)

    arboles = Arbol.query.order_by(
        Arbol.codigo.asc()
    ).all()

    if request.method == "POST":

        try:
            arbol_id = int(
                request.form.get("arbol_id", "")
            )

            fecha_cosecha = date.fromisoformat(
                request.form.get("fecha_cosecha", "")
            )

            cantidad_kg = Decimal(
                request.form.get("cantidad_kg", "")
            )

        except (ValueError, TypeError, InvalidOperation):

            flash(
                "Verifica los datos ingresados.",
                "danger"
            )

            return redirect(
                url_for("editar_produccion", id=id)
            )

        calidad = request.form.get(
            "calidad", ""
        ).strip().lower()

        arbol = db.session.get(Arbol, arbol_id)

        if not arbol:

            flash("El árbol no existe.", "danger")

            return redirect(
                url_for("editar_produccion", id=id)
            )

        if fecha_cosecha > date.today():

            flash(
                "La fecha no puede ser futura.",
                "danger"
            )

            return redirect(
                url_for("editar_produccion", id=id)
            )

        if (
            not cantidad_kg.is_finite()
            or cantidad_kg <= 0
            or cantidad_kg > Decimal("99999999.99")
            or cantidad_kg.as_tuple().exponent < -2
        ):

            flash(
                "Ingresa una cantidad válida con máximo dos decimales.",
                "danger"
            )

            return redirect(
                url_for("editar_produccion", id=id)
            )

        if calidad not in ["buena", "regular", "mala"]:

            flash("Calidad inválida.", "danger")

            return redirect(
                url_for("editar_produccion", id=id)
            )

        produccion.arbol_id = arbol_id
        produccion.fecha_cosecha = fecha_cosecha
        produccion.cantidad_kg = cantidad_kg
        produccion.calidad = calidad
        produccion.observaciones = request.form.get(
            "observaciones", ""
        ).strip()

        db.session.commit()

        flash(
            "Producción actualizada correctamente.",
            "success"
        )

        return redirect(url_for("listar_produccion"))

    return render_template(
        "form_produccion.html",
        produccion=produccion,
        arboles=arboles
    )


# ==========================================
# PASO 24 - REPORTES DE PRODUCCIÓN
# ==========================================

@app.route("/reportes")
def listar_reportes():

    # Obtener filtros
    fecha_inicio = request.args.get(
        "fecha_inicio", ""
    ).strip()

    fecha_fin = request.args.get(
        "fecha_fin", ""
    ).strip()

    arbol_id = request.args.get(
        "arbol_id", type=int
    )

    especie = request.args.get(
        "especie", ""
    ).strip()

    calidad = request.args.get(
        "calidad", ""
    ).strip().lower()

    pagina = max(
        request.args.get("pagina", 1, type=int),
        1
    )

    por_pagina = request.args.get(
        "por_pagina", 10, type=int
    )

    if por_pagina not in [10, 20, 50]:
        por_pagina = 10

    # Consulta inicial
    consulta = Produccion.query.join(
        Arbol,
        Produccion.arbol_id == Arbol.id
    )

    # Filtrar por fechas
    try:
        if fecha_inicio:
            inicio = date.fromisoformat(fecha_inicio)

            consulta = consulta.filter(
                Produccion.fecha_cosecha >= inicio
            )

        if fecha_fin:
            fin = date.fromisoformat(fecha_fin)

            consulta = consulta.filter(
                Produccion.fecha_cosecha <= fin
            )

        if fecha_inicio and fecha_fin and inicio > fin:
            flash(
                "La fecha inicial no puede ser posterior a la final.",
                "warning"
            )
            return redirect(url_for("listar_reportes"))

    except ValueError:
        flash("Las fechas ingresadas no son válidas.", "danger")
        return redirect(url_for("listar_reportes"))

    # Filtrar por árbol
    if arbol_id:
        consulta = consulta.filter(
            Produccion.arbol_id == arbol_id
        )

    # Filtrar por especie
    if especie:
        consulta = consulta.filter(
            Arbol.especie == especie
        )

    # Filtrar por calidad
    if calidad in ["buena", "regular", "mala"]:
        consulta = consulta.filter(
            Produccion.calidad == calidad
        )

    # Estadísticas sobre todos los resultados filtrados
    total_cosechas = consulta.count()

    total_kg = consulta.with_entities(
        db.func.coalesce(
            db.func.sum(Produccion.cantidad_kg),
            0
        )
    ).order_by(None).scalar()

    promedio_kg = (
        total_kg / total_cosechas
        if total_cosechas > 0
        else Decimal("0")
    )

    # Paginación
    paginacion = consulta.order_by(
        Produccion.fecha_cosecha.desc(),
        Produccion.id.desc()
    ).paginate(
        page=pagina,
        per_page=por_pagina,
        error_out=False
    )

    # Opciones de filtros
    arboles = Arbol.query.order_by(
        Arbol.codigo.asc()
    ).all()

    especies = [
        fila[0]
        for fila in db.session.query(
            Arbol.especie
        ).distinct().order_by(
            Arbol.especie.asc()
        ).all()
        if fila[0]
    ]

    return render_template(
        "reportes.html",
        producciones=paginacion.items,
        paginacion=paginacion,
        arboles=arboles,
        especies=especies,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        arbol_id=arbol_id,
        especie=especie,
        calidad=calidad,
        por_pagina=por_pagina,
        total_cosechas=total_cosechas,
        total_kg=total_kg,
        promedio_kg=promedio_kg
    )


# ==========================================
# PASO 24.2 - EXPORTACIÓN DE REPORTES
# ==========================================

def obtener_datos_reporte():

    fecha_inicio = request.args.get(
        "fecha_inicio", ""
    ).strip()

    fecha_fin = request.args.get(
        "fecha_fin", ""
    ).strip()

    arbol_id = request.args.get(
        "arbol_id", type=int
    )

    especie = request.args.get(
        "especie", ""
    ).strip()

    calidad = request.args.get(
        "calidad", ""
    ).strip().lower()

    consulta = Produccion.query.join(
        Arbol,
        Produccion.arbol_id == Arbol.id
    ).options(
        joinedload(Produccion.arbol),
        joinedload(Produccion.responsable)
    )

    if fecha_inicio:
        inicio = date.fromisoformat(fecha_inicio)
        consulta = consulta.filter(
            Produccion.fecha_cosecha >= inicio
        )

    if fecha_fin:
        fin = date.fromisoformat(fecha_fin)
        consulta = consulta.filter(
            Produccion.fecha_cosecha <= fin
        )

    if fecha_inicio and fecha_fin:
        if inicio > fin:
            raise ValueError("Rango de fechas inválido.")

    if arbol_id:
        consulta = consulta.filter(
            Produccion.arbol_id == arbol_id
        )

    if especie:
        consulta = consulta.filter(
            Arbol.especie == especie
        )

    if calidad in ["buena", "regular", "mala"]:
        consulta = consulta.filter(
            Produccion.calidad == calidad
        )

    return consulta.order_by(
        Produccion.fecha_cosecha.desc(),
        Produccion.id.desc()
    ).all()


# ==========================================
# EXPORTAR A EXCEL
# ==========================================

@app.route("/reportes/excel")
@roles_permitidos("administrador", "supervisor")
def exportar_reporte_excel():

    try:
        registros = obtener_datos_reporte()

    except ValueError:
        flash("Verifica las fechas del reporte.", "danger")
        return redirect(url_for("listar_reportes"))

    libro = Workbook()
    hoja = libro.active
    hoja.title = "Producción frutícola"

    verde = "108C6E"
    verde_claro = "E6F4EF"

    hoja.merge_cells("A1:H1")
    hoja["A1"] = "REPORTE DE PRODUCCIÓN"
    hoja["A1"].font = Font(
        bold=True,
        size=16,
        color="FFFFFF"
    )
    hoja["A1"].fill = PatternFill(
        "solid",
        fgColor=verde
    )
    hoja["A1"].alignment = Alignment(
        horizontal="center"
    )

    hoja.merge_cells("A2:H2")
    hoja["A2"] = (
        "Generado: "
        + datetime.now().strftime("%d/%m/%Y %H:%M")
    )
    hoja["A2"].alignment = Alignment(
        horizontal="center"
    )

    encabezados = [
        "No.",
        "Código",
        "Especie",
        "Fecha de cosecha",
        "Cantidad (kg)",
        "Calidad",
        "Responsable",
        "Observaciones"
    ]

    for columna, encabezado in enumerate(
        encabezados, start=1
    ):
        celda = hoja.cell(
            row=4,
            column=columna,
            value=encabezado
        )

        celda.font = Font(
            bold=True,
            color="FFFFFF"
        )

        celda.fill = PatternFill(
            "solid",
            fgColor=verde
        )

        celda.alignment = Alignment(
            horizontal="center"
        )

    total_kg = Decimal("0")

    for numero, registro in enumerate(
        registros, start=1
    ):

        fila = numero + 4
        total_kg += registro.cantidad_kg

        datos = [
            numero,
            registro.arbol.codigo,
            registro.arbol.especie,
            registro.fecha_cosecha,
            float(registro.cantidad_kg),
            registro.calidad.capitalize(),
            (
                registro.responsable.nombre
                if registro.responsable
                else "-"
            ),
            registro.observaciones or ""
        ]

        for columna, valor in enumerate(
            datos, start=1
        ):
            celda = hoja.cell(
                row=fila,
                column=columna,
                value=valor
            )

            if numero % 2 == 0:
                celda.fill = PatternFill(
                    "solid",
                    fgColor=verde_claro
                )

        hoja.cell(
            row=fila,
            column=4
        ).number_format = "DD/MM/YYYY"

        hoja.cell(
            row=fila,
            column=5
        ).number_format = "#,##0.00"

    fila_total = len(registros) + 6

    hoja.cell(
        row=fila_total,
        column=4,
        value="TOTAL KG"
    )

    hoja.cell(
        row=fila_total,
        column=5,
        value=float(total_kg)
    )

    for columna in [4, 5]:
        celda = hoja.cell(
            row=fila_total,
            column=columna
        )
        celda.font = Font(bold=True)
        celda.fill = PatternFill(
            "solid",
            fgColor=verde_claro
        )

    hoja.cell(
        row=fila_total,
        column=5
    ).number_format = "#,##0.00"

    anchos = [8, 18, 22, 20, 18, 15, 25, 45]

    for indice, ancho in enumerate(
        anchos, start=1
    ):
        letra = get_column_letter(indice)
        hoja.column_dimensions[letra].width = ancho

    hoja.freeze_panes = "A5"

    if registros:
        hoja.auto_filter.ref = (
            f"A4:H{len(registros) + 4}"
        )

    archivo = BytesIO()
    libro.save(archivo)
    archivo.seek(0)

    return send_file(
        archivo,
        as_attachment=True,
        download_name="roduccion.xlsx",
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )


# ==========================================
# EXPORTAR A PDF
# ==========================================

@app.route("/reportes/pdf")
@roles_permitidos("administrador", "supervisor")
def exportar_reporte_pdf():

    try:
        registros = obtener_datos_reporte()

    except ValueError:
        flash("Verifica las fechas del reporte.", "danger")
        return redirect(url_for("listar_reportes"))

    archivo = BytesIO()

    documento = SimpleDocTemplate(
        archivo,
        pagesize=landscape(A4),
        rightMargin=25,
        leftMargin=25,
        topMargin=30,
        bottomMargin=30
    )

    estilos = getSampleStyleSheet()

    estilo_titulo = estilos["Title"]
    estilo_titulo.textColor = colors.HexColor(
        "#108C6E"
    )
    estilo_titulo.alignment = TA_CENTER

    estilo_celda = estilos["BodyText"].clone(
        "CeldaReporte"
    )
    estilo_celda.fontSize = 8
    estilo_celda.leading = 10

    contenido = []

    contenido.append(
        Paragraph(
            "REPORTE DE PRODUCCIÓN",
            estilo_titulo
        )
    )

    contenido.append(Spacer(1, 10))

    contenido.append(
        Paragraph(
            "Fecha de generación: "
            + datetime.now().strftime(
                "%d/%m/%Y %H:%M"
            ),
            estilos["Normal"]
        )
    )

    contenido.append(Spacer(1, 12))

    total_kg = sum(
        (r.cantidad_kg for r in registros),
        Decimal("0")
    )

    promedio = (
        total_kg / len(registros)
        if registros
        else Decimal("0")
    )

    contenido.append(
        Paragraph(
            f"Total de cosechas: {len(registros)}"
            f" | Producción total: {total_kg:.2f} kg"
            f" | Promedio: {promedio:.2f} kg",
            estilos["Normal"]
        )
    )

    contenido.append(Spacer(1, 15))

    tabla_datos = [[
        "No.",
        "Árbol",
        "Especie",
        "Fecha",
        "Cantidad",
        "Calidad",
        "Responsable"
    ]]

    from xml.sax.saxutils import escape

    for numero, registro in enumerate(
        registros, start=1
    ):

        responsable = (
            registro.responsable.nombre
            if registro.responsable
            else "-"
        )

        tabla_datos.append([
            str(numero),
            Paragraph(
                escape(registro.arbol.codigo),
                estilo_celda
            ),
            Paragraph(
                escape(registro.arbol.especie),
                estilo_celda
            ),
            registro.fecha_cosecha.strftime(
                "%d/%m/%Y"
            ),
            f"{registro.cantidad_kg:.2f} kg",
            registro.calidad.capitalize(),
            Paragraph(
                escape(responsable),
                estilo_celda
            )
        ])

    if not registros:
        tabla_datos.append([
            "",
            "Sin registros",
            "",
            "",
            "",
            "",
            ""
        ])

    tabla = Table(
        tabla_datos,
        colWidths=[35, 110, 125, 85, 90, 80, 160],
        repeatRows=1,
        hAlign="CENTER"
    )

    tabla.setStyle(TableStyle([
        (
            "BACKGROUND",
            (0, 0),
            (-1, 0),
            colors.HexColor("#108C6E")
        ),
        (
            "TEXTCOLOR",
            (0, 0),
            (-1, 0),
            colors.white
        ),
        (
            "FONTNAME",
            (0, 0),
            (-1, 0),
            "Helvetica-Bold"
        ),
        (
            "FONTSIZE",
            (0, 0),
            (-1, 0),
            9
        ),
        (
            "ALIGN",
            (0, 0),
            (-1, -1),
            "CENTER"
        ),
        (
            "VALIGN",
            (0, 0),
            (-1, -1),
            "MIDDLE"
        ),
        (
            "ROWBACKGROUNDS",
            (0, 1),
            (-1, -1),
            [
                colors.white,
                colors.HexColor("#E6F4EF")
            ]
        ),
        (
            "BOTTOMPADDING",
            (0, 0),
            (-1, -1),
            8
        ),
        (
            "TOPPADDING",
            (0, 0),
            (-1, -1),
            8
        ),
        (
            "LINEBELOW",
            (0, 0),
            (-1, 0),
            1,
            colors.HexColor("#08745A")
        )
    ]))

    contenido.append(tabla)

    documento.build(contenido)

    archivo.seek(0)

    return send_file(
        archivo,
        as_attachment=True,
        download_name="Produccion.pdf",
        mimetype="application/pdf"
    )


# ==========================================
# PASO 24.3 - REPORTES DE ACTIVIDADES
# ==========================================

@app.route("/reportes/actividades")
def reporte_actividades():

    estado = request.args.get("estado", "").strip().lower()
    arbol_id = request.args.get("arbol_id", type=int)

    pagina = max(
        request.args.get("pagina", 1, type=int),
        1
    )

    por_pagina = request.args.get(
        "por_pagina", 10, type=int
    )

    if por_pagina not in [10, 20, 50]:
        por_pagina = 10

    consulta = Actividad.query

    if estado in ["pendiente", "completada"]:
        consulta = consulta.filter(
            Actividad.estado == estado
        )

    if arbol_id:
        consulta = consulta.filter(
            Actividad.arbol_id == arbol_id
        )

    total_actividades = consulta.count()

    pendientes = consulta.filter(
        Actividad.estado == "pendiente"
    ).count()

    completadas = consulta.filter(
        Actividad.estado == "completada"
    ).count()

    vencidas = consulta.filter(
        Actividad.estado == "pendiente",
        Actividad.fecha_programada < date.today()
    ).count()

    paginacion = consulta.order_by(
        Actividad.fecha_programada.desc(),
        Actividad.id.desc()
    ).paginate(
        page=pagina,
        per_page=por_pagina,
        error_out=False
    )

    arboles = Arbol.query.order_by(
        Arbol.codigo.asc()
    ).all()

    return render_template(
        "reporte_actividades.html",
        actividades=paginacion.items,
        paginacion=paginacion,
        arboles=arboles,
        arbol_id=arbol_id,
        estado=estado,
        por_pagina=por_pagina,
        total_actividades=total_actividades,
        pendientes=pendientes,
        completadas=completadas,
        vencidas=vencidas,
        hoy=date.today()
    )


# ==========================================
# PASO 24.3 - REPORTES DE ALERTAS
# ==========================================

@app.route("/reportes/alertas")
def reporte_alertas():

    estado = request.args.get("estado", "").strip().lower()
    tipo = request.args.get("tipo", "").strip().lower()

    pagina = max(
        request.args.get("pagina", 1, type=int),
        1
    )

    por_pagina = request.args.get(
        "por_pagina", 10, type=int
    )

    if por_pagina not in [10, 20, 50]:
        por_pagina = 10

    # Actualizar alertas automáticas
    generar_alertas_automaticas()

    consulta = Alerta.query

    if estado in ["pendiente", "atendida"]:
        consulta = consulta.filter(
            Alerta.estado == estado
        )

    # Los tipos disponibles se obtienen de la BD
    tipos = [
        fila[0]
        for fila in db.session.query(
            Alerta.tipo
        ).distinct().order_by(
            Alerta.tipo.asc()
        ).all()
        if fila[0]
    ]

    if tipo and tipo in tipos:
        consulta = consulta.filter(
            Alerta.tipo == tipo
        )

    total_alertas = consulta.count()

    pendientes = consulta.filter(
        Alerta.estado == "pendiente"
    ).count()

    atendidas = consulta.filter(
        Alerta.estado == "atendida"
    ).count()

    paginacion = consulta.order_by(
        Alerta.fecha_creacion.desc(),
        Alerta.id.desc()
    ).paginate(
        page=pagina,
        per_page=por_pagina,
        error_out=False
    )

    return render_template(
        "reporte_alertas.html",
        alertas=paginacion.items,
        paginacion=paginacion,
        tipos=tipos,
        estado=estado,
        tipo=tipo,
        por_pagina=por_pagina,
        total_alertas=total_alertas,
        pendientes=pendientes,
        atendidas=atendidas
    )


# ==========================================
# PASO 24.4 - EXPORTACIÓN DE ACTIVIDADES
# Y ALERTAS A PDF Y EXCEL
# ==========================================

def obtener_actividades_reporte():

    estado = request.args.get(
        "estado", ""
    ).strip().lower()

    arbol_id = request.args.get(
        "arbol_id", type=int
    )

    consulta = Actividad.query.options(
        joinedload(Actividad.arbol),
        joinedload(Actividad.responsable)
    )

    if estado in ["pendiente", "completada"]:
        consulta = consulta.filter(
            Actividad.estado == estado
        )

    if arbol_id:
        consulta = consulta.filter(
            Actividad.arbol_id == arbol_id
        )

    return consulta.order_by(
        Actividad.fecha_programada.desc(),
        Actividad.id.desc()
    ).all()


def obtener_alertas_reporte():

    estado = request.args.get(
        "estado", ""
    ).strip().lower()

    tipo = request.args.get(
        "tipo", ""
    ).strip().lower()

    consulta = Alerta.query.options(
        joinedload(Alerta.arbol)
    )

    if estado in ["pendiente", "atendida"]:
        consulta = consulta.filter(
            Alerta.estado == estado
        )

    if tipo:
        consulta = consulta.filter(
            Alerta.tipo == tipo
        )

    return consulta.order_by(
        Alerta.fecha_creacion.desc(),
        Alerta.id.desc()
    ).all()


# ==========================================
# FUNCIONES PARA GENERAR ARCHIVOS
# ==========================================

def generar_excel_reporte(titulo, encabezados, filas, nombre):

    libro = Workbook()
    hoja = libro.active
    hoja.title = "Reporte"

    ultima_columna = get_column_letter(len(encabezados))

    hoja.merge_cells(f"A1:{ultima_columna}1")
    titulo_celda = hoja["A1"]
    titulo_celda.value = f"{titulo}"
    titulo_celda.font = Font(
        bold=True,
        size=15,
        color="FFFFFF"
    )
    titulo_celda.fill = PatternFill(
        "solid",
        fgColor="108C6E"
    )
    titulo_celda.alignment = Alignment(
        horizontal="center"
    )

    hoja.merge_cells(f"A2:{ultima_columna}2")
    hoja["A2"] = (
        "Generado: "
        + datetime.now().strftime("%d/%m/%Y %H:%M")
    )

    hoja["A2"].alignment = Alignment(
        horizontal="center"
    )

    for indice, encabezado in enumerate(
        encabezados, start=1
    ):
        celda = hoja.cell(
            row=4,
            column=indice,
            value=encabezado
        )
        celda.font = Font(
            bold=True,
            color="FFFFFF"
        )
        celda.fill = PatternFill(
            "solid",
            fgColor="108C6E"
        )
        celda.alignment = Alignment(
            horizontal="center"
        )

    for numero, datos in enumerate(filas, start=1):

        for columna, valor in enumerate(datos, start=1):

            celda = hoja.cell(
                row=numero + 4,
                column=columna,
                value=valor
            )

            if numero % 2 == 0:
                celda.fill = PatternFill(
                    "solid",
                    fgColor="E6F4EF"
                )

    for columna, encabezado in enumerate(
        encabezados, start=1
    ):
        ancho = max(
            len(str(encabezado)),
            *[
                len(str(fila[columna - 1] or ""))
                for fila in filas
            ]
        ) if filas else len(str(encabezado))

        hoja.column_dimensions[
            get_column_letter(columna)
        ].width = min(max(ancho + 4, 15), 50)

    hoja.freeze_panes = "A5"

    if filas:
        hoja.auto_filter.ref = (
            f"A4:{ultima_columna}{len(filas) + 4}"
        )

    hoja.cell(
        row=len(filas) + 6,
        column=1,
        value=f"Total de registros: {len(filas)}"
    ).font = Font(bold=True)

    archivo = BytesIO()
    libro.save(archivo)
    archivo.seek(0)

    return send_file(
        archivo,
        as_attachment=True,
        download_name=nombre,
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )


def generar_pdf_reporte(titulo, encabezados, filas, nombre):

    archivo = BytesIO()

    documento = SimpleDocTemplate(
        archivo,
        pagesize=landscape(A4),
        leftMargin=25,
        rightMargin=25,
        topMargin=30,
        bottomMargin=30
    )

    estilos = getSampleStyleSheet()

    estilo_celda = estilos["BodyText"].clone(
        "CeldaExportacion"
    )
    estilo_celda.fontSize = 7
    estilo_celda.leading = 9

    contenido = [
        Paragraph(
            escape(f"{titulo}"),
            estilos["Title"]
        ),
        Spacer(1, 10),
        Paragraph(
            "Generado: "
            + datetime.now().strftime("%d/%m/%Y %H:%M"),
            estilos["Normal"]
        ),
        Spacer(1, 8),
        Paragraph(
            f"Total de registros: {len(filas)}",
            estilos["Normal"]
        ),
        Spacer(1, 15)
    ]

    datos = [
        [
            Paragraph(
                escape(str(valor)),
                estilo_celda
            )
            for valor in encabezados
        ]
    ]

    for fila in filas:
        datos.append([
            Paragraph(
                escape(str(valor if valor is not None else "")),
                estilo_celda
            )
            for valor in fila
        ])

    if not filas:
        datos.append([
            Paragraph("Sin registros", estilo_celda)
        ] + [""] * (len(encabezados) - 1))

    from reportlab.platypus import LongTable

    ancho_disponible = landscape(A4)[0] - 50

    tabla = LongTable(
        datos,
        colWidths=[
            ancho_disponible / len(encabezados)
        ] * len(encabezados),
        repeatRows=1
    )

    tabla.setStyle(TableStyle([
        (
            "BACKGROUND",
            (0, 0),
            (-1, 0),
            colors.HexColor("#108C6E")
        ),
        (
            "TEXTCOLOR",
            (0, 0),
            (-1, 0),
            colors.white
        ),
        (
            "FONTNAME",
            (0, 0),
            (-1, 0),
            "Helvetica-Bold"
        ),
        (
            "VALIGN",
            (0, 0),
            (-1, -1),
            "MIDDLE"
        ),
        (
            "ROWBACKGROUNDS",
            (0, 1),
            (-1, -1),
            [
                colors.white,
                colors.HexColor("#E6F4EF")
            ]
        ),
        (
            "TOPPADDING",
            (0, 0),
            (-1, -1),
            7
        ),
        (
            "BOTTOMPADDING",
            (0, 0),
            (-1, -1),
            7
        )
    ]))

    contenido.append(tabla)

    documento.build(contenido)
    archivo.seek(0)

    return send_file(
        archivo,
        as_attachment=True,
        download_name=nombre,
        mimetype="application/pdf"
    )


# ==========================================
# PREPARAR DATOS DE ACTIVIDADES
# ==========================================

def datos_exportacion_actividades():

    registros = obtener_actividades_reporte()
    hoy = date.today()

    encabezados = [
        "No.",
        "Árbol",
        "Actividad",
        "Responsable",
        "Fecha programada",
        "Fecha realizada",
        "Estado"
    ]

    filas = []

    for numero, actividad in enumerate(
        registros, start=1
    ):

        if actividad.estado == "completada":
            estado = "Completada"
        elif (
            actividad.estado == "pendiente"
            and actividad.fecha_programada < hoy
        ):
            estado = "Vencida"
        else:
            estado = actividad.estado.capitalize()

        filas.append([
            numero,
            actividad.arbol.codigo if actividad.arbol else "-",
            actividad.tipo,
            (
                actividad.responsable.nombre
                if actividad.responsable else "-"
            ),
            actividad.fecha_programada.strftime("%d/%m/%Y"),
            (
                actividad.fecha_realizada.strftime("%d/%m/%Y")
                if actividad.fecha_realizada else "-"
            ),
            estado
        ])

    return encabezados, filas


# ==========================================
# PREPARAR DATOS DE ALERTAS
# ==========================================

def datos_exportacion_alertas():

    registros = obtener_alertas_reporte()

    encabezados = [
        "No.",
        "Árbol",
        "Alerta",
        "Mensaje",
        "Tipo",
        "Fecha de creación",
        "Estado"
    ]

    filas = []

    for numero, alerta in enumerate(
        registros, start=1
    ):

        filas.append([
            numero,
            alerta.arbol.codigo if alerta.arbol else "-",
            alerta.titulo,
            alerta.mensaje,
            alerta.tipo.capitalize(),
            (
                alerta.fecha_creacion.strftime("%d/%m/%Y %H:%M")
                if alerta.fecha_creacion else "-"
            ),
            alerta.estado.capitalize()
        ])

    return encabezados, filas


# ==========================================
# RUTAS DE EXPORTACIÓN
# ==========================================

@app.route("/reportes/actividades/excel")
@roles_permitidos("administrador", "supervisor")
def exportar_actividades_excel():

    encabezados, filas = datos_exportacion_actividades()

    return generar_excel_reporte(
        "REPORTE DE ACTIVIDADES",
        encabezados,
        filas,
        "Actividades.xlsx"
    )


@app.route("/reportes/actividades/pdf")
@roles_permitidos("administrador", "supervisor")
def exportar_actividades_pdf():

    encabezados, filas = datos_exportacion_actividades()

    return generar_pdf_reporte(
        "REPORTE DE ACTIVIDADES",
        encabezados,
        filas,
        "Actividades.pdf"
    )


@app.route("/reportes/alertas/excel")
@roles_permitidos("administrador", "supervisor")
def exportar_alertas_excel():

    encabezados, filas = datos_exportacion_alertas()

    return generar_excel_reporte(
        "REPORTE DE ALERTAS",
        encabezados,
        filas,
        "Alertas.xlsx"
    )


@app.route("/reportes/alertas/pdf")
@roles_permitidos("administrador", "supervisor")
def exportar_alertas_pdf():

    encabezados, filas = datos_exportacion_alertas()

    return generar_pdf_reporte(
        "REPORTE DE ALERTAS",
        encabezados,
        filas,
        "Alertas.pdf"
    )


# ==========================================
# PASO 25 - CONFIGURACIÓN DEL SISTEMA
# ==========================================

@app.route("/configuracion", methods=["GET", "POST"])
@roles_permitidos("administrador")
def configuracion_sistema():

    configuracion = db.session.get(Configuracion, 1)

    if request.method == "POST":

        nombre_sistema = request.form.get(
            "nombre_sistema", ""
        ).strip()

        nombre_unidad = request.form.get(
            "nombre_unidad", ""
        ).strip()

        ubicacion = request.form.get(
            "ubicacion", ""
        ).strip()

        responsable = request.form.get(
            "responsable", ""
        ).strip()

        descripcion = request.form.get(
            "descripcion", ""
        ).strip()

        if not nombre_sistema or not nombre_unidad:
            flash(
                "El nombre del sistema y de la unidad son obligatorios.",
                "warning"
            )

            return redirect(
                url_for("configuracion_sistema")
            )

        if len(nombre_sistema) > 100 or len(nombre_unidad) > 150:
            flash(
                "Los nombres superan la longitud permitida.",
                "warning"
            )
            return redirect(url_for("configuracion_sistema"))

        if len(ubicacion) > 200 or len(responsable) > 150:
            flash(
                "La ubicación o el responsable superan la longitud permitida.",
                "warning"
            )
            return redirect(url_for("configuracion_sistema"))

        if configuracion is None:
            configuracion = Configuracion(id=1)
            db.session.add(configuracion)

        configuracion.nombre_sistema = nombre_sistema
        configuracion.nombre_unidad = nombre_unidad
        configuracion.ubicacion = ubicacion
        configuracion.responsable = responsable
        configuracion.descripcion = descripcion

        configuracion.fecha_actualizacion = datetime.now(
            timezone.utc
        )

        db.session.commit()

        flash(
            "La configuración se actualizó correctamente.",
            "success"
        )

        return redirect(
            url_for("configuracion_sistema")
        )

    return render_template(
        "configuracion.html",
        configuracion=configuracion
    )


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
