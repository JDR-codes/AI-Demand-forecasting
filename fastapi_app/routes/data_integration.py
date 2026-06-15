from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi_app.services.data_integration.data_integration_service import save_uploaded_file, validate_csv_path
from typing import List

router = APIRouter(prefix="/api/data_integration")


@router.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")
    content = await file.read()
    dest = f"data/{file.filename}"
    path = save_uploaded_file(content, dest)
    return {"message": "uploaded", "path": path}


@router.get("/validate")
def validate(path: str):
    ok = validate_csv_path(path)
    return {"valid": ok}
