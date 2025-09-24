# Compatibility shim: re-export API router and sub-routers from backup implementation
from backup.admin_backup.app.routers import *  # noqa: F401,F403
