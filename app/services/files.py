import os
import uuid
from typing import Optional

import fsspec
import s3fs
from fastapi import UploadFile
from sqlalchemy.orm import Session

from ..models import File
from ..settings import (
    FILE_STORAGE_BACKEND,
    FILE_STORAGE_LOCAL_PATH,
    FILE_STORAGE_S3_BUCKET,
    FILE_PUBLIC_BASE_URL,
)


class FileService:
    """Service handling file storage and URL generation."""

    def __init__(self) -> None:
        if FILE_STORAGE_BACKEND == "s3":
            self.fs = s3fs.S3FileSystem()
            self.base = FILE_STORAGE_S3_BUCKET
        else:
            self.fs = fsspec.filesystem("file")
            self.base = FILE_STORAGE_LOCAL_PATH
            self.fs.makedirs(self.base, exist_ok=True)

    def _full_path(self, path: str) -> str:
        if FILE_STORAGE_BACKEND == "s3":
            return f"{self.base}/{path}"
        return os.path.join(self.base, path)

    def upload(self, upload: UploadFile, data: bytes, owner: str, db: Session) -> File:
        ext = os.path.splitext(upload.filename)[1]
        file_id = uuid.uuid4().hex
        path = f"{file_id}{ext}"
        dest = self._full_path(path)
        with self.fs.open(dest, "wb") as f:
            f.write(data)
        file_obj = File(
            id=file_id,
            mime_type=upload.content_type,
            size=len(data),
            name=upload.filename,
            path=path,
            owner=owner,
        )
        db.add(file_obj)
        db.commit()
        db.refresh(file_obj)
        return file_obj

    def get(self, db: Session, file_id: str, owner: str) -> Optional[File]:
        return db.query(File).filter(File.id == file_id, File.owner == owner).first()

    def delete(self, db: Session, file_obj: File) -> None:
        dest = self._full_path(file_obj.path)
        if self.fs.exists(dest):
            self.fs.rm(dest)
        db.delete(file_obj)
        db.commit()

    def public_url(self, path: str) -> str:
        if FILE_STORAGE_BACKEND == "s3":
            return self.fs.url(f"{self.base}/{path}")
        base = FILE_PUBLIC_BASE_URL.rstrip("/") if FILE_PUBLIC_BASE_URL else ""
        if base:
            return f"{base}/{path}"
        return path


file_service = FileService()
