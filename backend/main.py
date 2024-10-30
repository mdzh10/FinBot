from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from controllers.authentication_controller import router as auth_router
from controllers.dashboard_controller import router as dashboard_router
from controllers.transaction_controller import router as txn_router
from controllers.account_controller import router as acc_router
from controllers.receipt_controller import router as receipt_router
from controllers.visualization_controller import router as report_router # type: ignore
from config.db.database import database, create_tables

app = FastAPI()
# Add the CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # List of allowed origins
    allow_credentials=True,       # Allow credentials such as cookies or HTTP auth
    allow_methods=["*"],          # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],          # Allow all headers (can also be restricted if necessary)
)

# Include authentication router
app.include_router(auth_router, prefix="/auth")
app.include_router(dashboard_router, prefix="/dashboard")
app.include_router(txn_router, prefix="/transaction")
app.include_router(acc_router, prefix="/account")
app.include_router(receipt_router, prefix="/receipt")
app.include_router(report_router, prefix="/report")

@app.on_event("startup")
async def startup():
    await database.connect()
    create_tables()  # Ensure this function is called to create tables

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.get("/")
async def root():
    return {"message": "Successfully connected to Supabase!"}
