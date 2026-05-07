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

# --- VOTACIONES ---
class EleccionCreate(BaseModel):
    titulo: str
    descripcion: str
    fecha_inicio: datetime
    fecha_fin: datetime

class VotoCreate(BaseModel):
    eleccion_id: int
    candidato_id: int
