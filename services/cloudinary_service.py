import os

import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, UploadFile


ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


def _ensure_cloudinary_configured() -> None:
    cloudinary_url = os.getenv("CLOUDINARY_URL")

    if not cloudinary_url:
        raise HTTPException(
            status_code=500,
            detail="Cloudinary is not configured",
        )

    cloudinary.config(secure=True)


def validate_product_image(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only JPEG, PNG, and WEBP images are allowed",
        )


def upload_product_image(file: UploadFile, product_id: int) -> str:
    _ensure_cloudinary_configured()
    validate_product_image(file)

    upload_result = cloudinary.uploader.upload(
        file.file,
        folder="online-shop/products",
        public_id=f"product-{product_id}",
        overwrite=True,
        resource_type="image",
    )

    secure_url = upload_result.get("secure_url")

    if not isinstance(secure_url, str):
        raise HTTPException(
            status_code=500,
            detail="Cloudinary upload failed",
        )

    return secure_url