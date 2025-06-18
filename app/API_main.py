from fastapi import FastAPI
import app.logger
from app.notify_API import router

app = FastAPI()
app.include_router(router)
