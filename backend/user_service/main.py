import logging
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Annotated, Union, Optional
from . import crud, models, schemas, utils
from .database import get_db
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import auth
from firebase_admin_init import initialize_firebase

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log',  # 로그를 파일에 저장
    filemode='a'  # 로그를 추가 모드로 저장
)
logger = logging.getLogger(__name__)

# 콘솔에도 로그 출력
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

router = APIRouter()

@router.post("/api/users/", response_model=schemas.UserCreate)
async def create_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    logger.info(f"Received request to create user: {user}")
    try:
        if user.role == 'member':
            db_user = await crud.create_member(db=db, member=user)
        elif user.role == 'trainer':
            db_user = await crud.create_trainer(db=db, trainer=user)
        else:
            raise ValueError("Invalid user role")

        if db_user is None:
            logger.error("Failed to create user in database")
            raise HTTPException(status_code=500, detail="Failed to create user in database")
        logger.info(f"Successfully created user: {db_user}")
        return db_user
    except ValueError as ve:
        logger.error(f"ValueError in create_user: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.exception(f"Unexpected error in create_user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")

@router.patch("/api/members/me", response_model=schemas.Member)
async def update_member(
    current_member: Annotated[models.Member, Depends(utils.get_current_user)],
    member_update: schemas.MemberUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        update_data = member_update.model_dump(exclude_unset=True)
        updated_member = await crud.update_member(db, current_member, update_data)
        if updated_member is None:
            raise HTTPException(status_code=404, detail="Member not found")
        return updated_member
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/api/trainers/me", response_model=schemas.Trainer)
async def update_trainer(
    current_trainer: Annotated[models.Trainer, Depends(utils.get_current_user)],
    trainer_update: schemas.TrainerUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        updated_trainer = await crud.update_trainer(db, current_trainer, trainer_update.model_dump())
        if updated_trainer is None:
            raise HTTPException(status_code=404, detail="Trainer not found")
        return updated_trainer
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/api/members/", response_model=List[schemas.Member])
async def read_members(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_member: schemas.Member = Depends(utils.admin_required)
):
    members = await crud.get_members(db, skip=skip, limit=limit)
    return members

@router.get("/api/trainers/", response_model=List[schemas.Trainer])
async def read_trainers(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db),
    current_member: schemas.Member = Depends(utils.admin_required)
):
    trainers = await crud.get_trainers(db, skip=skip, limit=limit)
    return trainers

@router.get("/api/members/byemail/{email}", response_model=schemas.Member)
async def read_member_email(email: str, db: AsyncSession = Depends(get_db)):
    db_member = await crud.get_member_by_email(db, email=email)
    if db_member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return db_member

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
    db: AsyncSession = Depends(get_db)
):
    try:
        is_trainer = isinstance(current_user, models.Trainer)
        logging.info(f"Attempting to create mapping: current_user={current_user}, other_email={mapping.other_email}, is_trainer={is_trainer}")
        
        db_mapping = await crud.create_trainer_member_mapping_request(
            db, 
            current_user.uid,
            mapping.other_email,
            is_trainer,
            mapping.initial_sessions
        )
        logging.info(f"Mapping created successfully: {db_mapping}")
        
        return schemas.TrainerMemberMappingResponse(
            id=db_mapping.id,
            trainer_uid=db_mapping.trainer_uid,
            member_uid=db_mapping.member_uid,
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
    current_user: Union[models.Member, models.Trainer] = Depends(utils.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        new_status = schemas.MappingStatus(status_update.new_status)
        db_mapping = await crud.update_trainer_member_mapping_status(db, mapping_id, current_user.uid, new_status)
        return schemas.TrainerMemberMappingResponse(
            id=db_mapping.id,
            trainer_uid=db_mapping.trainer_uid,
            member_uid=db_mapping.member_uid,
            status=db_mapping.status,
            remaining_sessions=db_mapping.remaining_sessions,
            acceptance_date=db_mapping.acceptance_date
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid status: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update mapping status: {str(e)}")

@router.get("/api/my-mappings/", response_model=List[Union[schemas.MemberMappingInfo, schemas.TrainerMappingInfo]])
async def read_my_mappings(
    current_user: Union[models.Member, models.Trainer] = Depends(utils.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    is_trainer = isinstance(current_user, models.Trainer)
    mappings = await crud.get_member_mappings(db, current_user.uid, is_trainer)
    return mappings

@router.delete("/api/trainer-member-mapping/{other_email}", response_model=schemas.Message)
async def remove_specific_mapping(
    other_email: str,
    current_user: Union[models.Member, models.Trainer] = Depends(utils.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        is_trainer = isinstance(current_user, models.Trainer)
        removed = await crud.remove_specific_mapping(db, current_user.uid, other_email, is_trainer)
    
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

@router.get("/api/trainer/connected-members/{member_email}", response_model=Optional[schemas.ConnectedMemberInfo])
async def read_specific_connected_member_info(
    member_email: str,
    current_user: models.Trainer = Depends(utils.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not isinstance(current_user, models.Trainer):
        raise HTTPException(status_code=403, detail="Trainer access required")
    
    member_info = await crud.get_specific_connected_member_info(db, current_user.uid, member_email)
    if member_info is None:
        raise HTTPException(status_code=404, detail="Connected member not found")
    return member_info

@router.delete("/api/members/me/", response_model=schemas.Member)
async def delete_members_me(
    current_member: Annotated[models.Member, Depends(utils.get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    try:
        await crud.delete_member(db, current_member)
        # Also delete the user from Firebase
        auth.delete_user(current_member.uid)
        return current_member
    except Exception as e:
        await db.rollback()
        logging.error(f"Error deleting member: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete member: {str(e)}")
    
@router.delete("/api/trainers/me/", response_model=schemas.Trainer)
async def delete_trainers_me(
    current_trainer: Annotated[models.Trainer, Depends(utils.get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    try:
        await crud.delete_trainer(db, current_trainer)
        # Also delete the user from Firebase
        auth.delete_user(current_trainer.uid)
        return current_trainer
    except Exception as e:
        await db.rollback()
        logging.error(f"Error deleting trainer: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete trainer: {str(e)}")
    
@router.get("/api/check-trainer-member-mapping/{trainer_email}/{member_email}")
async def check_trainer_member_mapping(
    trainer_email: str,
    member_email: str,
    current_user: Union[models.Member, models.Trainer] = Depends(utils.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        trainer = await crud.get_trainer_by_email(db, trainer_email)
        member = await crud.get_member_by_email(db, member_email)
        
        if not trainer or not member:
            raise HTTPException(status_code=404, detail="Trainer or Member not found")
        
        # 현재 사용자가 trainer와 일치하는지 확인
        if isinstance(current_user, models.Trainer) and current_user.uid != trainer.uid:
            raise HTTPException(status_code=403, detail="Not authorized to check this mapping")
        
        # 매핑 확인
        mapping = await crud.get_trainer_member_mapping(db, trainer.uid, member.uid)
        
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

@router.get("/api/trainer-member-mapping/{other_email}/sessions", response_model=schemas.RemainingSessionsResponse)
async def get_remaining_sessions(
    other_email: str,
    current_user: Union[models.Member, models.Trainer] = Depends(utils.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    is_trainer = isinstance(current_user, models.Trainer)
    try:
        if is_trainer:
            member = await crud.get_member_by_email(db, other_email)
            trainer_uid, member_uid = current_user.uid, member.uid
        else:
            trainer = await crud.get_trainer_by_email(db, other_email)
            trainer_uid, member_uid = trainer.uid, current_user.uid
        
        remaining_sessions = await crud.get_remaining_sessions(db, trainer_uid, member_uid)
        if remaining_sessions is None:
            raise HTTPException(status_code=404, detail="Trainer-Member mapping not found")
        return {"remaining_sessions": remaining_sessions}
    except Exception as e:
        logging.error(f"Error getting remaining sessions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get remaining sessions: {str(e)}")

@router.patch("/api/trainer-member-mapping/{member_email}/update-sessions", response_model=schemas.RemainingSessionsResponse)
async def update_sessions(
    member_email: str,
    request: schemas.UpdateSessionsRequest,
    background_tasks: BackgroundTasks,
    current_user: models.Trainer = Depends(utils.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        if not isinstance(current_user, models.Trainer):
            raise HTTPException(status_code=403, detail="Only trainers can update sessions")

        member = await crud.get_member_by_email(db, member_email)
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")

        new_remaining_sessions = await crud.update_sessions(db, current_user.uid, member.uid, request.sessions_to_add)
        return {"remaining_sessions": new_remaining_sessions}
    except Exception as e:
        logging.error(f"Error updating sessions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update sessions: {str(e)}")

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)