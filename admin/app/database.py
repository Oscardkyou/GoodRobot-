# Compatibility shim: re-export DB dependency from backup implementation
from backup.admin_backup.app.database import *  # noqa: F401,F403
