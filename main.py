"""
main.py
Main entry point of application that initializes the FastAPI app and includes all endpoints
"""

from fastapi import FastAPI
from routers import login, delete_account, onboarding, drills, session, data_sync_updates, drill_groups

# Initialize FastAPI app and router for endpoints
app = FastAPI()

# Include routers for endpoints in FastAPI app
app.include_router(login.router)
app.include_router(onboarding.router)
app.include_router(delete_account.router)
app.include_router(drills.router)
app.include_router(data_sync_updates.router)
app.include_router(session.router)
app.include_router(drill_groups.router)


# Run FastAPI on local host
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
    # uvicorn main:app --host 0.0.0.0 --port 8000   # in terminal for iphone testing
    