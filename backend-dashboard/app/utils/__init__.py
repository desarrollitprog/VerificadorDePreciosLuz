import html
import logging
import re
import struct
import subprocess
import uuid
import asyncio
import os
from typing import Optional, Tuple

logger = logging.getLogger("uvicorn.error")


def clean_log(text: str) -> str:
    return text.strip() if text else text


def _run_ffmpeg(cmd: list[str], timeout: int = 60) -> tuple[bool, str]:
    """Ejecuta ffmpeg con timeout, retorna (success, stderr)."""
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=timeout)
        if result.returncode == 0:
            return True, ""
        return False, result.stderr.decode(errors="ignore")
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)


def transcode_video(input_path: str, output_path: str, timeout: int = 300) -> tuple[bool, str]:
    """
    Transcodifica video a H.264 720p con audio AAC.
    Retorna (success, error_msg).
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "28",
        "-vf", "scale=-2:720",
        "-c:a", "aac",
        "-b:a", "96k",
        "-movflags", "+faststart",
        output_path
    ]
    return _run_ffmpeg(cmd, timeout)


def _write_file(source_file, dest_path: str) -> None:
    """Escribe el contenido de un archivo subido a disco de forma bloqueante."""
    with open(dest_path, "wb") as buffer:
        import shutil
        shutil.copyfileobj(source_file, buffer)


def generar_thumbnail(video_path: str, output_dir: str) -> Optional[str]:
    """
    Genera un thumbnail (frame a 1s) de un video usando ffmpeg.
    Retorna la URL relativa del thumbnail o None si falla.
    """
    try:
        thumbnail_filename = f"thumb_{uuid.uuid4().hex[:8]}.jpg"
        thumbnail_path = os.path.join(output_dir, thumbnail_filename)
        
        cmd = [
            "ffmpeg", "-y",
            "-ss", "00:00:01",
            "-i", video_path,
            "-vframes", "1",
            "-vf", "scale=320:-1",
            thumbnail_path
        ]
        success, err = _run_ffmpeg(cmd, timeout=30)
        if not success:
            logger.warning("thumbnail_generation_failed", reason=err, path=video_path)
            return None
        
        if not os.path.exists(thumbnail_path):
            logger.warning("thumbnail_generation_failed", reason="no_output_file", path=video_path)
            return None
        
        thumbnail_url = f"/static/banners/{thumbnail_filename}"
        logger.info("thumbnail_generated", video_path=video_path, thumbnail=thumbnail_url)
        return thumbnail_url
    
    except Exception as e:
        logger.warning("thumbnail_generation_error", error=str(e), path=video_path)
        return None


class FileTypeValidator:
    """
    Validador de tipo de archivo basado en magic bytes.
    No requiere dependencias externas.
    """
    
    MAGIC_BYTES = {
        "jpeg": [
            (b"\xFF\xD8\xFF", 0),
        ],
        "png": [
            (b"\x89\x50\x4E\x47\x0D\x0A\x1A\x0A", 0),
        ],
        "gif": [
            (b"\x47\x49\x46\x38\x37\x61", 0),
            (b"\x47\x49\x46\x38\x39\x61", 0),
        ],
        "bmp": [
            (b"\x42\x4D", 0),
        ],
        "webp": [
            (b"RIFF", 0, b"WEBP", 8),
        ],
        "mp4": [
            (b"\x00\x00\x00\x18\x66\x74\x79\x70", 0),
            (b"\x00\x00\x00\x1F\x66\x74\x79\x70", 0),
            (b"\x00\x00\x00\x20\x66\x74\x79\x70", 0),
        ],
        "webm": [
            (b"\x1A\x45\xDF\xA3", 0),
        ],
        "avi": [
            (b"RIFF", 0, b"AVI ", 8),
        ],
    }
    
    MIME_TYPES = {
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "bmp": "image/bmp",
        "webp": "image/webp",
        "mp4": "video/mp4",
        "webm": "video/webm",
        "avi": "video/x-msvideo",
    }
    
    @classmethod
    def detect_type(cls, file_path: str) -> str | None:
        """
        Detecta el tipo de archivo basándose en sus magic bytes.
        Retorna el tipo (jpeg, png, etc.) o None si no se reconoce.
        """
        try:
            with open(file_path, "rb") as f:
                header = f.read(16)
            
            for file_type, patterns in cls.MAGIC_BYTES.items():
                for pattern in patterns:
                    if isinstance(pattern, tuple) and len(pattern) == 2:
                        magic, offset = pattern
                        if len(header) >= offset + len(magic):
                            if header[offset:offset + len(magic)] == magic:
                                return file_type
                    elif isinstance(pattern, tuple) and len(pattern) == 4:
                        magic1, offset1, magic2, offset2 = pattern
                        if len(header) >= max(offset1 + len(magic1), offset2 + len(magic2)):
                            if header[offset1:offset1 + len(magic1)] == magic1 and header[offset2:offset2 + len(magic2)] == magic2:
                                return file_type
            
            return None
        except Exception:
            logger.warning("mime_detection_failed")
            return None
    
    @classmethod
    def validate_file(cls, file_path: str, allowed_types: list[str]) -> tuple[bool, str | None]:
        """
        Valida que el archivo sea de un tipo permitido.
        Retorna (True, mime_type) si es válido, (False, None) si no.
        """
        detected_type = cls.detect_type(file_path)
        if detected_type is None:
            return False, None
        if detected_type not in allowed_types:
            return False, detected_type
        return True, cls.MIME_TYPES.get(detected_type)


def sanitize_html(text: str | None) -> str | None:
    """
    Escapa caracteres HTML para prevenir XSS.
    Útil para campos de texto que se mostrarán en frontend.
    
    Ejemplo:
        sanitize_html("<script>alert('xss')</script>")
        -> "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"
    """
    if text is None:
        return None
    text = str(text)
    text = html.escape(text)
    
    import re
    text = re.sub(r'javascript\s*:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'vbscript\s*:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'data\s*:', '', text, flags=re.IGNORECASE)
    
    return text


def sanitize_filename(text: str | None) -> str | None:
    """
    Sanitiza un nombre de archivo/remitente para almacenamiento seguro.
    Elimina caracteres peligrosos de rutas y solo permite caracteres seguros.
    
    Caracteres permitidos: letras, números, espacios, guiones, guiones bajos, puntos.
    Caracteres eliminados: / \\ : * ? " < > | ..
    """
    if text is None:
        return None
    text = str(text)
    text = text.replace("..", "")
    text = re.sub(r'[/\\:*?"<>|]', '', text)
    text = text.strip()
    return text if text else None


def sanitize_search_query(text: str | None) -> str | None:
    """
    Sanitiza una query de búsqueda.
    Elimina caracteres especiales que podrían causar inyecciones.
    """
    if text is None:
        return None
    text = str(text)
    text = re.sub(r'[^\w\s\-_.@]', '', text)
    text = text.strip()
    return text if text else None
