from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load env variables (pastikan file .env sudah ada)
load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") 

# Inisialisasi Supabase client
supabase: Client = create_client(url, key)

# Buat router khusus untuk Auth
router = APIRouter(tags=["Authentication"])

# Model data yang dikirim oleh user (dari Frontend/Postman)
class UserCredentials(BaseModel):
    email: str
    password: str

@router.post("/signup")
def register_user(user: UserCredentials):
    try:
        response = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password
        })
        return {
            "status": "success", 
            "message": "Registrasi berhasil!", 
            "user_id": response.user.id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal registrasi: {str(e)}")

@router.post("/login")
def login_user(user: UserCredentials):
    try:
        response = supabase.auth.sign_in_with_password({
            "email": user.email,
            "password": user.password
        })
        
        return {
            "status": "success",
            "message": "Login berhasil!",
            "access_token": response.session.access_token,
            "user_id": response.user.id
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Email atau password salah!")