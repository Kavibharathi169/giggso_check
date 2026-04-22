from fastapi import FastAPI
from api.routes import checklist

app = FastAPI()

app.include_router(checklist.router)
