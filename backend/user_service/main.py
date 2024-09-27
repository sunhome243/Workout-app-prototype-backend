import logging
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Annotated, Union, Optional, Tuple
from . import crud, models, schemas, utils
from .database import get_db
from . import fcm_token_management
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import auth, db, messaging
from firebase_admin_init import initialize_firebase
from fastapi_utils.tasks import repeat_every
import uuid
import time
import asyncio

initialize_firebase()

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

        # Firebase에서 사용자 정보 조회 및 custom claims 설정
        max_retries = 5
        retry_delay = 1  # seconds
        for attempt in range(max_retries):
            try:
                user_record = auth.get_user(user.uid)
                custom_claims = {'role': user.role}
                auth.set_custom_user_claims(user_record.uid, custom_claims)
                logger.info(f"Custom claims set for user: {user_record.uid}")
                break
            except auth.UserNotFoundError:
                if attempt == max_retries - 1:
                    logger.error(f"User with UID {user.uid} not found in Firebase after {max_retries} attempts")
                    raise HTTPException(status_code=500, detail="User not found in Firebase")
                logger.warning(f"User not found in Firebase, retrying... (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(retry_delay)
        
        return db_user

    except ValueError as ve:
        logger.error(f"ValueError in create_user: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.exception(f"Unexpected error in create_user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")

@router.get("/api/members/me/", response_model=schemas.Member)
async def read_members_me(
    current_user: Annotated[Tuple[Union[models.Member, models.Trainer], str], Depends(utils.get_current_user)],
):
    user, user_type = current_user
    if user_type != 'member':
        raise HTTPException(status_code=403, detail="Access denied")
    return user

@router.get("/api/members/byuid/{uid}", response_model=schemas.Member)
async def read_member_uid(uid: str, db: AsyncSession = Depends(get_db)):
    db_member = await crud.get_member_by_uid(db, uid=uid)
    if db_member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return db_member

@router.get("/api/trainers/byuid/{uid}", response_model=schemas.Trainer)
async def read_trainer_uid(uid: str, db: AsyncSession = Depends(get_db)):
    db_trainer = await crud.get_trainer_by_uid(db, uid=uid)
    if db_trainer is None:
        raise HTTPException(status_code=404, detail="Trainer not found")
    return db_trainer

@router.get("/api/trainers/me/", response_model=schemas.Trainer)
async def read_trainer_me(
    current_user: Annotated[Tuple[Union[models.Member, models.Trainer], str], Depends(utils.get_current_user)],
):
    user, user_type = current_user
    if user_type != 'trainer':
        raise HTTPException(status_code=403, detail="Access denied")
    return user

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
    current_user: Annotated[Tuple[Union[models.Member, models.Trainer], str], Depends(utils.get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    try:
        user, user_type = current_user
        is_trainer = user_type == 'trainer'
        
        logging.info(f"Current user object: {user}")
        logging.info(f"User type: {user_type}")
        logging.info(f"Is trainer: {is_trainer}")
        
        if not hasattr(user, 'uid'):
            logging.error(f"User object does not have 'uid' attribute. User object: {user}")
            raise ValueError("Invalid user object")
        
        logging.info(f"Attempting to create mapping: current_user_uid={user.uid}, other_email={mapping.other_email}, is_trainer={is_trainer}")
        
        db_mapping = await crud.create_trainer_member_mapping_request(
            db, 
            user.uid,
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
    except ValueError as ve:
        logging.error(f"ValueError in request_trainer_member_mapping: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException as http_exc:
        logging.error(f"HTTP exception in request_trainer_member_mapping: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logging.error(f"Unexpected error in request_trainer_member_mapping: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred. Please try again later.")
    
@router.patch("/api/trainer-member-mapping/{mapping_id}/status", response_model=schemas.TrainerMemberMappingResponse)
async def update_trainer_member_mapping_status(
    mapping_id: int,
    status_update: schemas.TrainerMemberMappingUpdate,
    current_user: Annotated[Tuple[Union[models.Member, models.Trainer], str], Depends(utils.get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    user, user_type = current_user
    
    try:
        # Get the mapping using mapping_id
        mapping = await crud.get_trainer_member_mapping_by_id(db, mapping_id)
        
        if not mapping:
            raise HTTPException(status_code=404, detail="Mapping not found")
        
        # Check if the current user is involved in this mapping
        if user.uid not in [mapping.trainer_uid, mapping.member_uid]:
            raise HTTPException(status_code=403, detail="You are not authorized to update this mapping")
        
        # Check if the current user is the requester
        if mapping.requester_uid == user.uid:
            raise HTTPException(status_code=403, detail="You cannot update the status of a mapping you requested")
        
        new_status = schemas.MappingStatus(status_update.new_status)
        
        # Update the status
        updated_mapping = await crud.update_trainer_member_mapping_status(db, mapping_id, new_status)
        
        if not updated_mapping:
            raise HTTPException(status_code=404, detail="Failed to update mapping")
        
        return schemas.TrainerMemberMappingResponse(
            id=updated_mapping.id,
            trainer_uid=updated_mapping.trainer_uid,
            member_uid=updated_mapping.member_uid,
            status=updated_mapping.status,
            remaining_sessions=updated_mapping.remaining_sessions,
            acceptance_date=updated_mapping.acceptance_date
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error updating mapping status: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while updating the mapping status")
    
@router.get("/api/my-mappings/", response_model=List[Union[schemas.MemberMappingInfoWithSessions, schemas.TrainerMappingInfo]])
async def read_my_mappings(
    current_user: Annotated[Tuple[Union[models.Member, models.Trainer], str], Depends(utils.get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    user, user_type = current_user
    is_trainer = user_type == 'trainer'
    mappings = await crud.get_member_mappings(db, user.uid, is_trainer)
    return mappings

@router.delete("/api/trainer-member-mapping/{other_uid}", response_model=schemas.Message)
async def remove_specific_mapping(
    other_uid: str,
    current_user: Annotated[Tuple[Union[models.Member, models.Trainer], str], Depends(utils.get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    user, user_type = current_user
    try:
        is_trainer = user_type == 'trainer'
        removed = await crud.remove_specific_mapping(db, user.uid, other_uid, is_trainer)
    
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
    current_user: Annotated[Tuple[Union[models.Member, models.Trainer], str], Depends(utils.get_current_user)],
):
    user, user_type = current_user
    if user_type != 'member':
        raise HTTPException(status_code=403, detail="Access denied")
    return user

@router.get("/api/trainers/me/", response_model=schemas.Trainer)
async def read_trainer_me(
    current_user: Annotated[Tuple[Union[models.Member, models.Trainer], str], Depends(utils.get_current_user)],
):
    user, user_type = current_user
    if user_type != 'trainer':
        raise HTTPException(status_code=403, detail="Access denied")
    return user


@router.get("/api/trainer/connected-members/{member_uid}", response_model=Optional[schemas.ConnectedMemberInfo])
async def read_specific_connected_member_info(
    member_uid: str,
    current_user: Annotated[Tuple[Union[models.Member, models.Trainer], str], Depends(utils.get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    user, user_type = current_user
    if user_type != 'trainer':
        raise HTTPException(status_code=403, detail="Trainer access required")
    
    member_info = await crud.get_specific_connected_member_info(db, user.uid, member_uid)
    if member_info is None:
        raise HTTPException(status_code=404, detail="Connected member not found")
    return member_info

@router.delete("/api/members/me/", response_model=schemas.Member)
async def delete_members_me(
    current_user: Annotated[Tuple[Union[models.Member, models.Trainer], str], Depends(utils.get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    user, user_type = current_user
    if user_type != 'member':
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        await crud.delete_member(db, user)
        # Also delete the user from Firebase
        auth.delete_user(user.uid)
        return user
    except Exception as e:
        await db.rollback()
        logging.error(f"Error deleting member: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete member: {str(e)}")

@router.delete("/api/trainers/me/", response_model=schemas.Trainer)
async def delete_trainers_me(
    current_user: Annotated[Tuple[Union[models.Member, models.Trainer], str], Depends(utils.get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    user, user_type = current_user
    if user_type != 'trainer':
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        await crud.delete_trainer(db, user)
        # Also delete the user from Firebase
        auth.delete_user(user.uid)
        return user
    except Exception as e:
        await db.rollback()
        logging.error(f"Error deleting trainer: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete trainer: {str(e)}")

@router.post("/api/trainer-member-mapping/request", response_model=schemas.TrainerMemberMappingResponse)
async def request_trainer_member_mapping(
    mapping: schemas.CreateTrainerMemberMapping,
    current_user: Annotated[Tuple[Union[models.Member, models.Trainer], str], Depends(utils.get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    try:
        user, user_type = current_user
        is_trainer = user_type == 'trainer'
        
        logging.info(f"Current user object: {user}")
        logging.info(f"User type: {user_type}")
        logging.info(f"Is trainer: {is_trainer}")
        
        if not hasattr(user, 'uid'):
            logging.error(f"User object does not have 'uid' attribute. User object: {user}")
            raise ValueError("Invalid user object")
        
        logging.info(f"Attempting to create mapping: current_user_uid={user.uid}, other_email={mapping.other_email}, is_trainer={is_trainer}")
        
        db_mapping = await crud.create_trainer_member_mapping_request(
            db, 
            user.uid,
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
    except ValueError as ve:
        logging.error(f"ValueError in request_trainer_member_mapping: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException as http_exc:
        logging.error(f"HTTP exception in request_trainer_member_mapping: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logging.error(f"Unexpected error in request_trainer_member_mapping: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred. Please try again later.")
    
@router.get("/api/trainer-member-mapping/{other_uid}/sessions", response_model=schemas.RemainingSessionsResponse)
async def get_remaining_sessions(
    other_uid: str,
    current_user: Annotated[Tuple[Union[models.Member, models.Trainer], str], Depends(utils.get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    try:
        user, user_type = current_user
        if user_type == 'member':
            trainer_uid, member_uid = other_uid, user.uid
        else:  # trainer
            trainer_uid, member_uid = user.uid, other_uid
        
        logging.info(f"Checking remaining sessions for trainer_uid: {trainer_uid}, member_uid: {member_uid}")
        
        remaining_sessions = await crud.get_remaining_sessions(db, trainer_uid, member_uid)
        if remaining_sessions is None:
            raise HTTPException(status_code=404, detail="Trainer-Member mapping not found")
        return {"remaining_sessions": remaining_sessions}
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error getting remaining sessions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get remaining sessions: {str(e)}")
    
@router.patch("/api/trainer-member-mapping/{other_uid}/update-sessions", response_model=schemas.RemainingSessionsResponse)
async def update_sessions(
    other_uid: str,
    request: schemas.UpdateSessionsRequest,
    current_user: Annotated[Tuple[Union[models.Member, models.Trainer], str], Depends(utils.get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    try:
        user, user_type = current_user
        if user_type != 'trainer':
            raise HTTPException(status_code=403, detail="Only trainers can update sessions")

        new_remaining_sessions = await crud.update_sessions(db, user.uid, other_uid, request.sessions_to_add)
        return {"remaining_sessions": new_remaining_sessions}
    except Exception as e:
        logging.error(f"Error updating sessions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update sessions: {str(e)}")

@router.post("/api/request-more-sessions/{trainer_uid}")
async def request_more_sessions(
    trainer_uid: str,
    request: schemas.RequestMoreSessionsSchema,
    current_user: Annotated[Tuple[Union[models.Member, models.Trainer], str], Depends(utils.get_current_user)],
):
    user, user_type = current_user
    if user_type != 'member':
        raise HTTPException(status_code=403, detail="Only members can request more sessions")

    try:
        # Generate a unique ID for this request
        request_id = str(uuid.uuid4())

        # Store the request in Firebase Realtime Database
        ref = db.reference(f'session_requests/{request_id}')
        ref.set({
            'trainer_uid': trainer_uid,
            'member_uid': user.uid,
            'requested_sessions': request.additional_sessions,
            'status': 'pending',
            'created_at': {'.sv': 'timestamp'}
        })

        # Send a notification to the trainer
        message = messaging.Message(
            notification=messaging.Notification(
                title='New Session Request',
                body=f'A member has requested {request.additional_sessions} more sessions.'
            ),
            data={
                'request_id': request_id,
                'type': 'more_sessions_request'
            },
            token=trainer_fcm_token  # You need to retrieve this token from your database
        )
        messaging.send(message)

        return {"message": "Session request sent successfully", "request_id": request_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to request more sessions: {str(e)}")

@router.patch("/api/members/me", response_model=schemas.Member)
async def update_member_me(
    member_update: schemas.MemberUpdate,
    current_user: Annotated[Tuple[Union[models.Member, models.Trainer], str], Depends(utils.get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    user, user_type = current_user
    if user_type != 'member':
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        updated_member = await crud.update_member(db, user, member_update)
        return updated_member
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while updating member: {str(e)}")

@router.post("/api/fcm-token")
async def add_fcm_token(
    token: str,
    current_user: Annotated[Tuple[Union[models.Member, models.Trainer], str], Depends(utils.get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    user, user_type = current_user
    updated_tokens = await fcm_token_management.add_fcm_token(db, user.uid, token, user_type == 'trainer')
    return {"message": "FCM token added successfully", "tokens": updated_tokens}

@router.delete("/api/fcm-token")
async def remove_fcm_token(
    token: str,
    current_user: Annotated[Tuple[Union[models.Member, models.Trainer], str], Depends(utils.get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    user, user_type = current_user
    updated_tokens = await fcm_token_management.remove_fcm_token(db, user.uid, token, user_type == 'trainer')
    return {"message": "FCM token removed successfully", "tokens": updated_tokens}

@router.put("/api/fcm-token")
async def refresh_fcm_token(
    old_token: str,
    new_token: str,
    current_user: Annotated[Tuple[Union[models.Member, models.Trainer], str], Depends(utils.get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    user, user_type = current_user
    updated_tokens = await fcm_token_management.refresh_fcm_token(db, user.uid, old_token, new_token, user_type == 'trainer')
    return {"message": "FCM token refreshed successfully", "tokens": updated_tokens}

@router.post("/api/update-last-active")
async def update_last_active(
    current_user: Annotated[Tuple[Union[models.Member, models.Trainer], str], Depends(utils.get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    user, user_type = current_user
    await fcm_token_management.update_user_last_active(db, user.uid, user_type == 'trainer')
    return {"message": "Last active timestamp updated successfully"}

@router.get("/api/check-trainer-member-mapping/{trainer_uid}/{member_uid}")
async def check_trainer_member_mapping(
    trainer_uid: str,
    member_uid: str,
    current_user: Annotated[Tuple[Union[models.Member, models.Trainer], str], Depends(utils.get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    user, user_type = current_user
    if user_type != 'trainer' or user.uid != trainer_uid:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        mapping = await crud.get_trainer_member_mapping(db, trainer_uid, member_uid)
        if mapping and mapping.status == schemas.MappingStatus.accepted:
            return {"exists": True}
        return {"exists": False}
    except Exception as e:
        logger.error(f"Error checking trainer-member mapping: {str(e)}")
        raise HTTPException(status_code=500, detail="Error checking trainer-member mapping")

@router.get("/api/trainer/{trainer_uid}/assigned-members", response_model=List[schemas.MemberBasicInfo])
async def get_trainer_assigned_members(
    trainer_uid: str,
    current_user: Annotated[Tuple[Union[models.Member, models.Trainer], str], Depends(utils.get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    user, user_type = current_user
    if user_type != 'trainer' or user.uid != trainer_uid:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        assigned_members = await crud.get_trainer_assigned_members(db, trainer_uid)
        return assigned_members
    except Exception as e:
        logger.error(f"Error fetching assigned members: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching assigned members: {str(e)}")
    
# 비활성 토큰 제거 작업 (백그라운드 태스크로 실행)
@app.on_event("startup")
@repeat_every(seconds=60*60*24)  # 매일 실행
async def remove_inactive_tokens_task():
    async with AsyncSession(get_db()) as db:
        await fcm_token_management.remove_inactive_tokens(db)
        

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)