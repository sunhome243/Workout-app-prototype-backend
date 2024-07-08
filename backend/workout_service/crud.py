from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from . import models, schemas
from datetime import datetime

async def create_session(db: AsyncSession, session: schemas.SessionCreate):
    """
    Creates a new session when a trainer starts it.
    Adds a new entry to the SessionIDMap.
    """
    db_session = models.SessionIDMap(
        workout_date=session.workout_date.strftime("%Y-%m-%d"),
        user_id=session.user_id,
        trainer_id=session.trainer_id,
        is_pt=session.is_pt
    )
    db.add(db_session)
    await db.commit()
    await db.refresh(db_session)
    return db_session

async def add_workout_to_session(db: AsyncSession, workout: schemas.SessionDetailCreate, session_id: int):
    """
    Adds a new workout to an existing session.
    Called when a trainer adds a new workout to the ongoing session.
    """
    db_workout = models.Session(
        session_id=session_id,
        workout_key=workout.workout_key,
        set_num=workout.set_num,
        weight=workout.weight,
        reps=workout.reps,
        rest_time=workout.rest_time
    )
    db.add(db_workout)
    await db.commit()
    await db.refresh(db_workout)
    return db_workout

async def get_session(db: AsyncSession, session_id: int):
    """
    Retrieves information about a specific session.
    """
    result = await db.execute(select(models.SessionIDMap).filter(models.SessionIDMap.session_id == session_id))
    return result.scalar_one_or_none()

async def get_session_workouts(db: AsyncSession, session_id: int):
    """
    Retrieves all workouts included in a specific session.
    """
    result = await db.execute(select(models.Session).filter(models.Session.session_id == session_id))
    return result.scalars().all()

async def update_session(db: AsyncSession, session_id: int, session_update: schemas.SessionCreate):
    """
    Updates the basic information of a session.
    """
    db_session = await get_session(db, session_id)
    if db_session:
        update_data = session_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_session, key, value)
        await db.commit()
        await db.refresh(db_session)
    return db_session

async def update_workout(db: AsyncSession, session_id: int, workout_key: int, set_num: int, workout_update: schemas.SessionDetailCreate):
    """
    Updates the details of a specific workout within a session.
    """
    stmt = select(models.Session).filter(
        models.Session.session_id == session_id,
        models.Session.workout_key == workout_key,
        models.Session.set_num == set_num
    )
    result = await db.execute(stmt)
    db_workout = result.scalar_one_or_none()
    if db_workout:
        update_data = workout_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_workout, key, value)
        await db.commit()
        await db.refresh(db_workout)
    return db_workout

async def delete_workout(db: AsyncSession, session_id: int, workout_key: int, set_num: int):
    """
    Deletes a specific workout from a session.
    """
    stmt = select(models.Session).filter(
        models.Session.session_id == session_id,
        models.Session.workout_key == workout_key,
        models.Session.set_num == set_num
    )
    result = await db.execute(stmt)
    db_workout = result.scalar_one_or_none()
    if db_workout:
        await db.delete(db_workout)
        await db.commit()
    return db_workout