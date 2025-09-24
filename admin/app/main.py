from datetime import datetime

from admin.app import create_app

app = create_app()


@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
