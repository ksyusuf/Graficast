from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# api üzerinden gelecek verilerin modeli
class ApiShare(BaseModel):
    comment_id: int
    comment: str
    comment_date: datetime
    writer_name: str
    uni_name: str
    dep_name: Optional[str] = None
    ins_name: Optional[str] = None
    image_template_type: Optional[str] = "instagram-post-square"


# veritabanında tutulacak veriler modeli
class DatabaseShare(BaseModel):
    comment_id: int
    image_template_type: Optional[str] = None
    image_created_date: Optional[datetime] = None
    image_updated_date: Optional[datetime] = None
    is_uploaded_google: bool = False
    uploaded_date_google: Optional[datetime] = None
    last_uploaded_date_google: Optional[datetime] = None
    google_photos_id: Optional[str] = None
    google_product_id: Optional[str] = None
    google_description: Optional[str] = None
    is_shared: bool = False
    shared_date: Optional[datetime] = None
    last_shared_date: Optional[datetime] = None
    error_message: Optional[str] = None
    tags: Optional[List[str]] = []


# veritabanında tutulacak template modeli
class DatabaseTemplate(BaseModel):
    template_type: str
    name: str
    size: str
    description: Optional[str] = None
    template_path: str

