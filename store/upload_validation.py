"""Validaciones defensivas para archivos recibidos desde clientes."""

from __future__ import annotations

from pathlib import Path

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}


def _file_extension(upload) -> str:
    return Path(str(getattr(upload, 'name', '') or '')).suffix.lower()


def _validate_size(upload, max_size: int) -> None:
    size = getattr(upload, 'size', None)
    if size is None or size <= 0:
        raise ValidationError('El archivo está vacío o no es válido.')
    if size > max_size:
        raise ValidationError(
            f'El archivo no puede superar los {max_size // (1024 * 1024)} MB.'
        )


def validate_image_upload(upload, *, max_size: int = MAX_UPLOAD_BYTES) -> None:
    """Comprueba tamaño, extensión y contenido real de una imagen."""

    _validate_size(upload, max_size)
    extension = _file_extension(upload)
    content_type = str(getattr(upload, 'content_type', '') or '').lower()

    if extension not in IMAGE_EXTENSIONS:
        raise ValidationError('Solo puedes subir imágenes JPG, PNG, WEBP o GIF.')
    if content_type and not content_type.startswith('image/'):
        raise ValidationError('El tipo de contenido de la imagen no es válido.')

    try:
        upload.seek(0)
        with Image.open(upload) as image:
            width, height = image.size
            if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
                raise ValidationError('Las dimensiones de la imagen no son válidas.')
            image.verify()
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        SyntaxError,
        Image.DecompressionBombError,
    ) as exc:
        raise ValidationError('El archivo no contiene una imagen válida.') from exc
    finally:
        upload.seek(0)


def validate_pdf_upload(upload, *, max_size: int = MAX_UPLOAD_BYTES) -> None:
    """Comprueba que un archivo declarado como PDF tenga la firma esperada."""

    _validate_size(upload, max_size)
    extension = _file_extension(upload)
    content_type = str(getattr(upload, 'content_type', '') or '').lower()
    if extension != '.pdf':
        raise ValidationError('El comprobante PDF debe tener extensión .pdf.')
    if content_type and content_type != 'application/pdf':
        raise ValidationError('El tipo de contenido del PDF no es válido.')

    try:
        upload.seek(0)
        if upload.read(5) != b'%PDF-':
            raise ValidationError('El archivo no contiene un PDF válido.')
    finally:
        upload.seek(0)


def validate_chat_attachment(upload, *, max_size: int = MAX_UPLOAD_BYTES) -> None:
    """Permite únicamente imágenes verificables o PDFs con firma válida."""

    if _file_extension(upload) == '.pdf':
        validate_pdf_upload(upload, max_size=max_size)
        return
    validate_image_upload(upload, max_size=max_size)
