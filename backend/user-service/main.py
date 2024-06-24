from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .models import MemberBase, MemberCreate, Member, MemberDB

app = FastAPI()

SQLALCHEMY_DATABASE_URL = "postgresql://postgres:itismepassword@db:5432/prototype"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
@app.get ("/")
def just_checking():
    return {"it":"me"}
        
@app.post("/members/", response_model=Member)
def create_member(member: MemberCreate, db: Session = Depends(get_db)):
    db_member = MemberDB(**member.dict())
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)