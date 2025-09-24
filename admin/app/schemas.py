# Compatibility shim: re-export Pydantic schemas from backup implementation
from backup.admin_backup.app.schemas import *  # noqa: F401,F403
