from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base


class MaterialLibraryGeneration(Base):
    __tablename__ = "material_library_generations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    library_key = Column(String(80), nullable=False, index=True)
    library_name = Column(String(120), nullable=False)
    target_count = Column(Integer, nullable=False, default=100)
    status = Column(String(30), nullable=False, default="sample_pending", index=True)
    progress = Column(Integer, nullable=False, default=0)
    message = Column(String(300), nullable=True)
    error = Column(Text, nullable=True)
    reference_image_path = Column(String(500), nullable=False)
    output_dir = Column(String(500), nullable=False)
    sample_images_json = Column(Text, nullable=True)
    manifest_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
