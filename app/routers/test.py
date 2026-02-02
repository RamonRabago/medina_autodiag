# app/routers/test.py
from fastapi import APIRouter, Depends
from app.utils.jwt import get_current_user

router = APIRouter(prefix="/test", tags=["Test"])

@router.get("/me")
def me(user = Depends(get_current_user)):
    return {
        "id_usuario": user.id_usuario,
        "email": user.email,
        "rol": user.rol
    }