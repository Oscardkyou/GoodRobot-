"""
Admin package shim.

This package is a thin compatibility layer that aliases the legacy
implementation located under `backup/admin_backup/app` so that imports like
`from admin.app.auth import ...` continue to work in runtime and tests.
"""
