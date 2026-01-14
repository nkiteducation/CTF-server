import logging
import mmap
from pathlib import Path
from contextlib import asynccontextmanager
import secrets
import html

from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import HTMLResponse, ORJSONResponse, PlainTextResponse
from pydantic import BaseModel, Field, field_validator
import pyzipper

# Конфигурация логгирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Конфигурация приложения и модели данных ------------------------------

ROCKYOU_PATH = Path("./rockyou.txt")
SECRET_DIR = Path("./secret")
ZIP_FILENAME = "flag.zip"
ZIP_ENTRY_NAME = "flag.txt"


class RuntimeConfig(BaseModel):
    web_flag: str = "None"
    curl_flag: str = "None"
    zip_password_list: list[str] = ROCKYOU_PATH.read_text(encoding="latin-1").split("\n")


# Глобальная в памяти конфигурация (упрощённо)
runtime_config = RuntimeConfig()


class SetConfigPayload(BaseModel):
    zip_flag: str = Field(..., min_length=1, max_length=4096)
    web_flag: str = Field(..., min_length=0, max_length=1024)
    curl_flag: str = Field(..., min_length=0, max_length=1024)

    @field_validator("zip_flag", "web_flag", "curl_flag", mode="after")
    def strip_strings(cls, v):
        if isinstance(v, str):
            return v.strip()
        return cls


# --- Утилиты ---------------------------------------------------------------


def generate_zip_file(
    flag: str,
    password: bytes,
    dest_dir: Path = SECRET_DIR,
    zip_name: str = ZIP_FILENAME,
) -> Path:
    if not isinstance(password, (bytes, bytearray)):
        raise TypeError("password must be bytes")

    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / zip_name

    try:
        with pyzipper.AESZipFile(
            zip_path, "w", compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES
        ) as zf:
            zf.setpassword(password)
            zf.writestr(ZIP_ENTRY_NAME, flag.encode("utf-8"))
    except Exception:
        logger.exception("Failed to generate zip file %s", zip_path)

        try:
            if zip_path.exists():
                zip_path.unlink()
        except Exception:
            logger.exception("Failed to remove incomplete zip file %s", zip_path)
        raise

    logger.info("Created zip file at %s", zip_path)
    return zip_path


# --- FastAPI приложение ----------------------------------------------------

app = FastAPI(default_response_class=ORJSONResponse)


@app.post("/set-config", status_code=status.HTTP_201_CREATED)
def set_config(payload: SetConfigPayload):
    """
    Ожидает JSON:
    {
      "zip_flag": "...",
      "web_flag": "...",
      "curl_flag": "..."
    }

    Создаёт secret/flag.zip зашифрованный случайным паролем (из rockyou.txt),
    сохраняет web/curl флаги возвращает пароль (latin-1 decode).
    """
    password_bytes = secrets.choice(runtime_config.zip_password_list).encode(
        "latin-1", errors="ignore"
    )
    try:
        generate_zip_file(payload.zip_flag, password_bytes)
    except Exception as exc:
        logger.error("Unable to create zip: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create zip archive")

    runtime_config.curl_flag = payload.curl_flag
    runtime_config.web_flag = payload.web_flag

    password_str = password_bytes.decode("latin-1", errors="ignore")

    logger.info(
        "Config updated: web_flag=%s curl_flag=%s",
        bool(runtime_config.web_flag),
        bool(runtime_config.curl_flag),
    )
    return {"zip_password": password_str}


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request):
    ua = (request.headers.get("user-agent") or "").lower()

    if "curl" in ua:
        return PlainTextResponse(f"flag: {runtime_config.curl_flag}\n")

    safe_web_flag = html.escape(runtime_config.web_flag or "")
    html_content = f"""<!DOCTYPE html>
                        <html lang="ru">
                        <head>
                            <meta charset="UTF-8">
                            <title>Page</title>
                            <style>
                                flag {{
                                    display: none;
                                }}
                            </style>
                        </head>
                        <body>
                            <h1>тут будет другой текст</h1>
                            <h6>если я не поленюсь заменить</h6>
                        </body>
                        <flag>FLAG{{{safe_web_flag}}}</flag>
                        </html>
                        """
    return HTMLResponse(html_content)
