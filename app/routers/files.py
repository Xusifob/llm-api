from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File as FastAPIFile, Security, Response
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import FileOut
from ..settings import FILE_ALLOWED_MIME_TYPES, FILE_MAX_SIZE
from ..services import file_service

bearer_scheme = HTTPBearer()

router = APIRouter(
    prefix="/files",
    tags=["files"],
    dependencies=[Security(bearer_scheme)],
)


def _require_user(request: Request) -> str:
    uid = getattr(request.state, "user_id", None)
    if uid is None:
        raise HTTPException(status_code=401, detail="User API key required")
    return uid


@router.post("/upload", response_model=FileOut, summary="Upload a file")
async def upload_file(
    request: Request,
    upload: UploadFile = FastAPIFile(...),
    db: Session = Depends(get_db),
):
    user_id = _require_user(request)
    if FILE_ALLOWED_MIME_TYPES and upload.content_type not in FILE_ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="File type not allowed")

    data = await upload.read()
    if len(data) > FILE_MAX_SIZE:
        raise HTTPException(status_code=400, detail="File too large")
    return file_service.upload(upload, data, user_id, db)


@router.delete("/{file_id}", status_code=204, summary="Delete a file")
def delete_file(
    file_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = _require_user(request)
    file_obj = file_service.get(db, file_id, user_id)
    if not file_obj:
        raise HTTPException(status_code=404, detail="File not found")
    file_service.delete(db, file_obj)
    return Response(status_code=204)
