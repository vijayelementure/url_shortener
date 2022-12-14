# shortener_app/main.py
from fastapi import FastAPI,HTTPException
import validators
from . import schemas
import secrets
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
from . import models, schemas
from .database import SessionLocal, engine
from . import crud, models, schemas
from .config import get_settings
from starlette.datastructures import URL


app = FastAPI()
models.Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db

    finally:
          db.close()

      


def raise_bad_request(message):
    raise HTTPException(status_code=400, detail = message)


def raise_not_found(request):
    message = f"URL '{request.url}' doesn't exist"
    raise HTTPException(status_code=404, detail=message)
    

    
@app.get("/")
def read_root():
    return "Welcome to the URL shortener API :)"

@app.post("/url", response_model=schemas.URLInfo)
def create_url(url: schemas.URLBase, db: Session = Depends(get_db)):
    if not validators.url(url.target_url):
        raise_bad_request(message="Your provided URL is not valid")
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    key = "".join(secrets.choice(chars) for _ in range(5))
    secret_key = "".join(secrets.choice(chars) for _ in range(8))
    db_url = models.URL(target_url=url.target_url, key=key, secret_key=secret_key)
    db_url = crud.create_db_url(db=db, url=url)
    db.add(db_url)
    db.commit()
    db.refresh(db_url)
    db_url.url = key   
    db_url.admin_url = secret_key
    return get_admin_info(db_url)



@app.get("/{url_key}")
def forward_to_target_url(url_key: str,request: Request,db: Session = Depends(get_db)):
    db_url = (db.query(models.URL).filter(models.URL.key == url_key, models.URL.is_active).first())
    if db_url := crud.get_db_url_by_key(db=db, url_key=url_key):
        return RedirectResponse(db_url.target_url)
    else:
        raise_not_found(request)   





@app.get("/admin/{secret_key}",name="administration info",response_model=schemas.URLInfo,)
def get_url_info(secret_key: str, request: Request, db: Session = Depends(get_db)):
    if db_url := crud.get_db_url_by_secret_key(db, secret_key=secret_key):
        db_url.url = db_url.key
        db_url.admin_url = db_url.secret_key
        return get_admin_info(db_url)
    else:
        raise_not_found(request)



def get_admin_info(db_url: models.URL) -> schemas.URLInfo:
    base_url = URL(get_settings().base_url)
    admin_endpoint = app.url_path_for("administration info", secret_key=db_url.secret_key)
    db_url.url = str(base_url.replace(path=db_url.key))
    db_url.admin_url = str(base_url.replace(path=admin_endpoint))
    return db_url
    


    

    


    



