# Compatibility shim — re-exports from backend.db.session
from backend.db.session import Base, get_db, init_db, engine, AsyncSessionLocal

__all__ = ["Base", "get_db", "init_db", "engine", "AsyncSessionLocal"]
