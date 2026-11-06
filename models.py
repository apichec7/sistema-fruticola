
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone, date

db = SQLAlchemy()


# ==========================================
# 1. MODELO DE USUARIOS
# ==========================================

class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(
        db.String(30),
        nullable=False,
        default="operador"
    )
    activo = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )
    nombre_usuario = db.Column(
        db.String(50),
        unique=True,
        nullable=True
    )

    def establecer_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def verificar_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)


# ==========================================
# 2. MODELO DE ÁRBOLES
# ==========================================

class Arbol(db.Model):
    __tablename__ = "arboles"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(
        db.String(30),
        unique=True,
        nullable=False
    )
    especie = db.Column(db.String(80), nullable=False)
    variedad = db.Column(db.String(80))
    ubicacion = db.Column(db.String(150))
    fecha_siembra = db.Column(db.Date)
    estado = db.Column(
        db.String(30),
        default="activo",
        nullable=False
    )
    observaciones = db.Column(db.Text)


# ==========================================
# 3. MODELO DE ACTIVIDADES
# ==========================================

class Actividad(db.Model):
    __tablename__ = "actividades"

    id = db.Column(db.Integer, primary_key=True)

    arbol_id = db.Column(
        db.Integer,
        db.ForeignKey("arboles.id"),
        nullable=False
    )

    responsable_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True
    )

    tipo = db.Column(db.String(60), nullable=False)
    descripcion = db.Column(db.Text)
    fecha_programada = db.Column(db.Date, nullable=False)
    fecha_realizada = db.Column(db.Date)
    estado = db.Column(
        db.String(30),
        default="pendiente",
        nullable=False
    )

    arbol = db.relationship(
        "Arbol",
        backref="actividades"
    )

    responsable = db.relationship(
        "Usuario",
        backref="actividades"
    )


# ==========================================
# 4. MODELO DE ALERTAS
# ==========================================

class Alerta(db.Model):
    __tablename__ = "alertas"

    id = db.Column(db.Integer, primary_key=True)

    actividad_id = db.Column(
        db.Integer,
        db.ForeignKey("actividades.id"),
        nullable=True
    )

    arbol_id = db.Column(
        db.Integer,
        db.ForeignKey("arboles.id"),
        nullable=True
    )

    titulo = db.Column(db.String(150), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    tipo = db.Column(
        db.String(40),
        default="actividad"
    )
    estado = db.Column(
        db.String(30),
        default="pendiente",
        nullable=False
    )

    fecha_creacion = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    fecha_atencion = db.Column(
        db.DateTime(timezone=True)
    )

    actividad = db.relationship(
        "Actividad",
        backref="alertas"
    )

    arbol = db.relationship(
        "Arbol",
        backref="alertas"
    )


# ==========================================
# 5. MODELO DE PRODUCCIÓN FRUTÍCOLA
# ==========================================

class Produccion(db.Model):
    __tablename__ = "producciones"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    arbol_id = db.Column(
        db.Integer,
        db.ForeignKey("arboles.id"),
        nullable=False
    )

    responsable_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True
    )

    fecha_cosecha = db.Column(
        db.Date,
        nullable=False
    )

    cantidad_kg = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    calidad = db.Column(
        db.String(30),
        nullable=False
    )

    observaciones = db.Column(
        db.Text,
        nullable=True
    )

    fecha_registro = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    arbol = db.relationship(
        "Arbol",
        backref="producciones"
    )

    responsable = db.relationship(
        "Usuario",
        backref="producciones"
    )


# ==========================================
# CONFIGURACIÓN DEL SISTEMA
# ==========================================

class Configuracion(db.Model):

    __tablename__ = "configuraciones"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    nombre_sistema = db.Column(
        db.String(100),
        nullable=False,
        default="AgroControl"
    )

    nombre_unidad = db.Column(
        db.String(150),
        nullable=False,
        default="Unidad de producción frutícola"
    )

    ubicacion = db.Column(
        db.String(200),
        nullable=True
    )

    responsable = db.Column(
        db.String(150),
        nullable=True
    )

    descripcion = db.Column(
        db.Text,
        nullable=True
    )

    fecha_actualizacion = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
