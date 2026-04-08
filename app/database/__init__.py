# app/database/__init__.py
# Camada de acesso ao banco de dados
# Usa SQLite local via SQLAlchemy

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from config import DB_PATH

# ─── Conexão ──────────────────────────────────────────────────
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ─── Modelo da tabela ─────────────────────────────────────────
class Analise(Base):
    __tablename__ = "analises"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    criado_em       = Column(DateTime, default=datetime.now)
    titulo          = Column(String(200), nullable=False)
    documentos      = Column(Text, nullable=False)
    marcadores      = Column(Text, nullable=True)
    lacunas         = Column(Text, nullable=True)
    veredito        = Column(String(20), nullable=True)
    relatorio       = Column(Text, nullable=True)
    nivel_evidencia = Column(Integer, nullable=True)

# ─── Criar tabela se não existir ──────────────────────────────
def init_db():
    Base.metadata.create_all(engine)

# ─── Sessão de banco para uso nos agentes ─────────────────────
def get_session():
    return SessionLocal()