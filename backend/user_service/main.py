import bcrypt
import logging
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Annotated, Union, Optional, Dict
from . import crud, models, schemas, utils
from .database import get_db
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from datetime import timedelta

app = FastAPI()  # Create the main FastAPI application

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

router = APIRouter()  # Create an APIRouter

ACCESS_TOKEN_EXPIRE_MINUTES = 100

# Login for both trainer + member
@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    member, role = await utils.authenticate_member(db, form_data.username, form_data.password)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = utils.create_access_token(
        data={"sub": str(member.member_id if role == 'member' else member.trainer_id), "type": role},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Member sign up
@router.post("/api/members/", response_model=schemas.Member)
async def create_member(member: schemas.MemberCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_member(db=db, member=member)

# Updating a member
@router.patch("/api/members/me", response_model=schemas.Member)
async def update_member(
    current_member: Annotated[models.Member, Depends(utils.get_current_user)],
    member_update: schemas.MemberUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        updated_member = await crud.update_member(db, current_member, member_update.model_dump())
        if updated_member is None:
            raise HTTPException(status_code=404, detail="Member not found")
        return updated_member
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))



# Trainer sign up
@router.post("/api/trainers/", response_model=schemas.Trainer)
async def create_trainer(trainer: schemas.TrainerCreate, db: AsyncSession = Depends(get_db)): 
    return await crud.create_trainer(db=db, trainer=trainer)

# Updating a trainer
@router.patch("/api/trainers/me", response_model=schemas.Trainer)
async def update_trainer(
    current_trainer: Annotated[models.Trainer, Depends(utils.get_current_user)],
    trainer_update: schemas.TrainerUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        updated_trainer = await crud.update_trainer(db, current_trainer, trainer_update.model_dump())
        if updated_trainer is None:
            raise HTTPException(status_code=404, detail="Member not found")
        return updated_trainer
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Only Admin can use. Get all members
@router.get("/api/members/", response_model=List[schemas.Member])
async def read_members(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(utils.get_db),
    current_member: schemas.Member = Depends(utils.admin_required)
):
    members = await crud.get_members(db, skip=skip, limit=limit)
    return members

# Only Admin can use. Get all trainers
@router.get("/api/trainers/", response_model=List[schemas.Trainer])
async def read_trainers(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(utils.get_db),
    current_member: schemas.Member = Depends(utils.admin_required)
):
    trainers = await crud.get_trainers(db, skip=skip, limit=limit)
    return trainers

# Getting a member with id
@router.get("/api/members/byid/{member_id}", response_model=schemas.Member)
async def read_member(member_id: str, db: AsyncSession = Depends(get_db)):
    db_member = await crud.get_member_by_id(db, member_id=member_id)
    if db_member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return db_member

#Getting a trainer with id
@router.get("/api/trainers/byid/{trainer_id}", response_model=schemas.Trainer)
async def read_trainer(trainer_id: str, db: AsyncSession = Depends(get_db)):
    db_member = await crud.get_trainer_by_id(db, trainer_id=trainer_id)
    if db_member is None:
        raise HTTPException(status_code=404, detail="Trainer not found")
    return db_member

# Getting a member with email
@router.get("/api/members/byemail/{email}", response_model=schemas.Member)
async def read_member_email(email: str, db: AsyncSession = Depends(get_db)):
    db_member = await crud.get_member_by_email(db, email=email)
    if db_member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return db_member

# Getting a trainer with email
@router.get("/api/trainers/byemail/{email}", response_model=schemas.Trainer)
async def read_trainer_email(email: str, db: AsyncSession = Depends(get_db)):
    db_trainer = await crud.get_trainer_by_email(db, email=email)
    if db_trainer is None:
        raise HTTPException(status_code=404, detail="Trainer not found")
    return db_trainer


@router.post("/api/trainer-member-mapping/request", response_model=schemas.TrainerMemberMappingResponse)
async def request_trainer_member_mapping(
    mapping: schemas.CreateTrainerMemberMapping,
    current_user: Union[models.Member, models.Trainer] = Depends(utils.get_current_user),
    db: AsyncSession = Depends(utils.get_db)
):
    try:
        is_trainer = isinstance(current_user, models.Trainer)
        
        logging.info(f"Attempting to create mapping: current_user={current_user}, other_id={mapping.other_id}, is_trainer={is_trainer}")
        
        current_user_id = current_user.trainer_id if is_trainer else current_user.member_id
        
        db_mapping = await crud.create_trainer_member_mapping_request(
            db, 
            current_user_id,
            mapping.other_id,
            is_trainer,
            mapping.initial_sessions
        )
        logging.info(f"Mapping created successfully: {db_mapping}")
        
        return schemas.TrainerMemberMappingResponse(
            id=db_mapping.id,
            trainer_id=db_mapping.trainer_id,
            member_id=db_mapping.member_id,
            status=db_mapping.status,
            remaining_sessions=db_mapping.remaining_sessions
        )
    except ValueError as e:
        logging.error(f"ValueError in request_trainer_member_mapping: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Unexpected error in request_trainer_member_mapping: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create mapping request: {str(e)}")


@router.patch("/api/trainer-member-mapping/{mapping_id}/status", response_model=schemas.TrainerMemberMappingResponse)
async def update_trainer_member_mapping_status(
    mapping_id: int,
    status_update: schemas.TrainerMemberMappingUpdate,
    current_member: Union[models.Member, models.Trainer] = Depends(utils.get_current_user),
    db: AsyncSession = Depends(utils.get_db)
):
    try:
        new_status = schemas.MappingStatus(status_update.new_status)
        current_member_id = current_member.trainer_id if isinstance(current_member, models.Trainer) else current_member.member_id
        db_mapping = await crud.update_trainer_member_mapping_status(db, mapping_id, current_member_id, new_status)
        return schemas.TrainerMemberMappingResponse(
            id=db_mapping.id,
            trainer_id=db_mapping.trainer_id,
            member_id=db_mapping.member_id,
            status=db_mapping.status.value
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid status: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update mapping status: {str(e)}")

@router.get("/api/my-mappings/", response_model=List[Union[schemas.MemberMappingInfo, schemas.TrainerMappingInfo]])
async def read_my_mappings(
    current_member: Union[models.Member, models.Trainer] = Depends(utils.get_current_user),
    db: AsyncSession = Depends(utils.get_db)
):
    is_trainer = isinstance(current_member, models.Trainer)
    member_id = current_member.trainer_id if is_trainer else current_member.member_id
    
    mappings = await crud.get_member_mappings(db, member_id, is_trainer)
    return mappings


@router.delete("/api/trainer-member-mapping/{other_id}", response_model=schemas.Message)
async def remove_specific_mapping(
    other_id: str,
    current_member: Union[models.Member, models.Trainer] = Depends(utils.get_current_user),
    db: AsyncSession = Depends(utils.get_db)
):
    try:
        is_trainer = isinstance(current_member, models.Trainer)
        current_member_id = current_member.trainer_id if is_trainer else current_member.member_id
        
        removed = await crud.remove_specific_mapping(db, current_member_id, other_id, is_trainer)
    
        if removed:
            return {"message": "Successfully removed the trainer-member mapping"}
        else:
            raise HTTPException(status_code=404, detail="No trainer-member mapping found to remove")
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error occurred: {str(e)}")

@router.get("/api/members/me/", response_model=schemas.Member)
async def read_members_me(
    current_member: Annotated[models.Member, Depends(utils.get_current_user)],
):
    return current_member

@router.get("/api/trainers/me/", response_model=schemas.Trainer)
async def read_trainer_me(
    current_trainer: Annotated[models.Trainer, Depends(utils.get_current_user)],
):
    return current_trainer

@router.get("/api/trainer/connected-members/{member_id}", response_model=Optional[schemas.ConnectedMemberInfo])
async def read_specific_connected_member_info(
    member_id: str,
    current_member: models.Trainer = Depends(utils.get_current_user),
    db: AsyncSession = Depends(utils.get_db)
):
    if not isinstance(current_member, models.Trainer):
        raise HTTPException(status_code=403, detail="Trainer access required")
    
    member_info = await crud.get_specific_connected_member_info(db, current_member.trainer_id, member_id)
    if member_info is None:
        raise HTTPException(status_code=404, detail="Connected member not found")
    return member_info

@router.delete("/api/members/me/", response_model=schemas.Member)
async def delete_members_me(
    current_member: Annotated[models.Member, Depends(utils.get_current_user)],
    db: AsyncSession = Depends(utils.get_db)
):
    try:
        # deleting member
        await crud.delete_member(db, current_member)

        return current_member
    except Exception as e:
        await db.rollback()
        logging.error(f"Error deleting member: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete member: {str(e)}")
    
@router.delete("/api/trainers/me/", response_model=schemas.Trainer)
async def delete_trainers_me(
    current_trainer: Annotated[models.Trainer, Depends(utils.get_current_user)],
    db: AsyncSession = Depends(utils.get_db)
):
    try:
        # deleting member
        await crud.delete_trainer(db, current_trainer)

        return current_trainer
    except Exception as e:
        await db.rollback()
        logging.error(f"Error deleting member: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete trainer: {str(e)}")
    
@router.get("/api/check-trainer-member-mapping/{trainer_id}/{member_id}")
async def check_trainer_member_mapping(
    trainer_id: str,
    member_id: str,
    current_member: Union[models.Member, models.Trainer] = Depends(utils.get_current_user),
    db: AsyncSession = Depends(utils.get_db)
):
    try:
        # 현재 사용자가 trainer_id와 일치하는지 확인
        if isinstance(current_member, models.Trainer) and current_member.trainer_id != trainer_id:
            raise HTTPException(status_code=403, detail="Not authorized to check this mapping")
        
        # 매핑 확인
        mapping = await crud.get_trainer_member_mapping(db, trainer_id, member_id)
        
        if mapping:
            logging.info(f"Mapping found: {mapping}")
            logging.info(f"Mapping status: {mapping.status}")
            logging.info(f"Mappingstatus: {schemas.MappingStatus.accepted}")
            exists = (str(mapping.status) == str(schemas.MappingStatus.accepted))
            logging.info(f"Returning exists: {exists}")
            return {"exists": exists}
        else:
            logging.info("No mapping found")
            return {"exists": False}
    except Exception as e:
        logging.error(f"Error in check_trainer_member_mapping: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/api/trainer-member-mapping/{other_id}/sessions", response_model=schemas.RemainingSessionsResponse)
async def get_remaining_sessions(
    other_id: str,
    current_user: Union[models.Member, models.Trainer] = Depends(utils.get_current_user),
    db: AsyncSession = Depends(utils.get_db)
):
    is_trainer = isinstance(current_user, models.Trainer)
    if is_trainer:
        trainer_id, member_id = current_user.trainer_id, other_id
    else:
        trainer_id, member_id = other_id, current_user.member_id
    
    try:
        remaining_sessions = await crud.get_remaining_sessions(db, trainer_id, member_id)
        if remaining_sessions is None:
            raise HTTPException(status_code=404, detail="Trainer-Member mapping not found")
        return {"remaining_sessions": remaining_sessions}
    except Exception as e:
        logging.error(f"Error getting remaining sessions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get remaining sessions: {str(e)}")


@router.patch("/api/trainer-member-mapping/{other_id}/update-sessions", response_model=schemas.RemainingSessionsResponse)
async def update_sessions(
    other_id: str,
    request: schemas.UpdateSessionsRequest,
    current_user: Union[models.Member, models.Trainer] = Depends(utils.get_current_user),
    db: AsyncSession = Depends(utils.get_db)
):
    if not isinstance(current_user, models.Trainer):
        raise HTTPException(status_code=403, detail="Only trainers can update sessions")
    
    try:
        new_remaining_sessions = await crud.update_sessions(db, current_user.trainer_id, other_id, request.sessions_to_add)
        return {"remaining_sessions": new_remaining_sessions}
    except Exception as e:
        logging.error(f"Error updating sessions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update sessions: {str(e)}")


    
app.include_router(router)
