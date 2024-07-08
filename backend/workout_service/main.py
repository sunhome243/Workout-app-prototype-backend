from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from . import crud, models, schemas, utils
from .database import engine, get_db

app = FastAPI(title="Workout Service")

# CORS middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.post("/sessions/", response_model=schemas.Session)
async def create_session(
    session: schemas.SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_trainer: models.Trainer = Depends(utils.get_current_trainer)
):
    return await crud.create_session(db=db, session=session, trainer_id=current_trainer.trainer_id)

@app.get("/sessions/{session_id}", response_model=schemas.Session)
async def read_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(utils.get_current_user)
):
    session = await crud.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if isinstance(current_user, models.Trainer) and session.trainer_id != current_user.trainer_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")
    return session

@app.get("/sessions/", response_model=List[schemas.Session])
async def read_sessions(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(utils.get_current_user)
):
    if isinstance(current_user, models.Trainer):
        return await crud.get_trainer_sessions(db, trainer_id=current_user.trainer_id, skip=skip, limit=limit)
    else:
        return await crud.get_user_sessions(db, user_id=current_user.user_id, skip=skip, limit=limit)

@app.post("/sessions/{session_id}/workouts/", response_model=schemas.Workout)
async def create_workout(
    session_id: int,
    workout: schemas.WorkoutCreate,
    db: AsyncSession = Depends(get_db),
    current_trainer: models.Trainer = Depends(utils.get_current_trainer)
):
    session = await crud.get_session(db, session_id)
    if not session or session.trainer_id != current_trainer.trainer_id:
        raise HTTPException(status_code=404, detail="Session not found or not authorized")
    return await crud.create_workout(db=db, workout=workout, session_id=session_id)

@app.get("/sessions/{session_id}/workouts/", response_model=List[schemas.Workout])
async def read_workouts(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(utils.get_current_user)
):
    session = await crud.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if isinstance(current_user, models.Trainer) and session.trainer_id != current_trainer.trainer_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")
    return await crud.get_session_workouts(db, session_id=session_id)

@app.put("/sessions/{session_id}", response_model=schemas.Session)
async def update_session(
    session_id: int,
    session_update: schemas.Session,
    db: AsyncSession = Depends(get_db),
    current_trainer: models.Trainer = Depends(utils.get_current_trainer)
):
    session = await crud.get_session(db, session_id)
    if not session or session.trainer_id != current_trainer.trainer_id:
        raise HTTPException(status_code=404, detail="Session not found or not authorized")
    return await crud.update_session(db=db, session_id=session_id, session_update=session_update)

@app.delete("/sessions/{session_id}", response_model=schemas.Session)
async def delete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_trainer: models.Trainer = Depends(utils.get_current_trainer)
):
    session = await crud.get_session(db, session_id)
    if not session or session.trainer_id != current_trainer.trainer_id:
        raise HTTPException(status_code=404, detail="Session not found or not authorized")
    return await crud.delete_session(db=db, session_id=session_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)