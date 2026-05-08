from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

# --- SUBSISTEMAS ---
class SubsistemaCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None

class SubsistemaResponse(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str]
    estado: str

    class Config:
        from_attributes = True

# --- CARRERAS ---
class CarreraCreate(BaseModel):
    subsistema_id: int
    nombre: str
    area: str
    descripcion: Optional[str] = None
    jefe_id: Optional[int] = None

class CarreraResponse(BaseModel):
    id: int
    subsistema_id: int
    nombre: str
    area: str
    descripcion: Optional[str]
    jefe_id: Optional[int]
    estado: str

    class Config:
        from_attributes = True

# --- INSCRIPCIONES ---
class InscripcionCreate(BaseModel):
    usuario_id: int
    carrera_id: int
    nivel: Optional[str] = None

class InscripcionResponse(BaseModel):
    id: int
    usuario_id: int
    carrera_id: int
    nivel: Optional[str]
    fecha_inscripcion: datetime
    estado: str

    class Config:
        from_attributes = True

# --- USUARIOS ---
class UsuarioCreate(BaseModel):
    nombre: str
    apellido: str
    email: EmailStr
    password: str
    rol: str = "estudiante"
    subsistema_id: Optional[int] = None

    class Config:
        from_attributes = True

class UsuarioResponse(BaseModel):
    id: int
    nombre: str
    apellido: str
    email: str
    rol: str
    subsistema_id: Optional[int]
    estado: str

    class Config:
        from_attributes = True

# --- AUTH ---
class Token(BaseModel):
    access_token: str
    token_type: str
    user: UsuarioResponse

class TokenData(BaseModel):
    username: Optional[str] = None

# --- AVISOS ---
class AvisoCreate(BaseModel):
    titulo: str
    contenido: str

class AvisoResponse(BaseModel):
    id: int
    subsistema_id: int
    autor_id: int
    titulo: str
    contenido: str
    fecha_creacion: datetime

    class Config:
        from_attributes = True

# --- PLANIFICACIONES ---
class PlanificacionCreate(BaseModel):
    modulo_id: int
    tema: str

class PlanificacionResponse(BaseModel):
    id: int
    docente_id: int
    modulo_id: int
    contenido_ia: str
    fecha_generacion: datetime

    class Config:
        from_attributes = True

# --- CERTIFICADOS ---
class CertificadoResponse(BaseModel):
    id: int
    estudiante_id: int
    modulo_id: int
    codigo_qr: str
    fecha_emision: datetime

    class Config:
        from_attributes = True

# --- VOTACIONES (Sistema Electoral CEA) ---
class EleccionCreate(BaseModel):
    nombre: str
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None

class VotoCreate(BaseModel):
    eleccion_id: int
    candidato_id: int

class CandidatoCreate(BaseModel):
    eleccion_id: int
    nombre: str
    sigla: Optional[str] = None
    cargo: Optional[str] = None
    frente: Optional[str] = None
    descripcion: Optional[str] = None
    imagen_base64: Optional[str] = None
    ci_representante: Optional[str] = None

class MesaCreate(BaseModel):
    eleccion_id: int
    cantidad: int

class VotanteCreate(BaseModel):
    ci: str
    nombre: str

class VotanteLoteTexto(BaseModel):
    votantes: list

class AsignarJefeCI(BaseModel):
    ci: str
    eleccion_id: int
