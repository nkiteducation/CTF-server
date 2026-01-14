import pathlib
import secrets

import msgspec
import pyzipper
from robyn import Request, Response, Robyn, html

ROCKYOU_PATH = pathlib.Path("./rockyou.txt")
SECRET_DIR = pathlib.Path("./secret")  


class Flag(msgspec.Struct):
    zip: str = "None"
    web: str = "None"
    curl: str = "None"


class Config(msgspec.Struct):
    flag: Flag
    list_passwords: list[str]

    @classmethod
    def load_config(cls) -> Config:
        if ROCKYOU_PATH.exists():
            passwords = ROCKYOU_PATH.read_text(encoding="latin-1").splitlines()
        else:
            passwords = ["default_pass"]

        return cls(flag=Flag(), list_passwords=passwords)


config = Config.load_config()


def generate_zip_file(flag_content: str) -> str:
    SECRET_DIR.mkdir(exist_ok=True)
    password = secrets.choice(config.list_passwords)
    zip_path = SECRET_DIR / "flag.zip"

    with pyzipper.AESZipFile(
        zip_path, "w", 
        compression=pyzipper.ZIP_DEFLATED, 
        encryption=pyzipper.WZ_AES
    ) as zf:
        zf.setpassword(password.encode("utf-8")) # Более универсально
        zf.writestr("flag.txt", flag_content.encode("utf-8"))

    return password


app = Robyn(__file__)

@app.post("/set-config")
async def set_config(request: Request):
    config.flag = msgspec.json.decode(request.body, type=Flag)
    password = generate_zip_file(config.flag.zip)

    return {"zip_password": password}


@app.get("/")
async def index(request: Request):
    ua_raw = request.headers.get("user-agent")
    ua = ua_raw.lower() if ua_raw else ""

    if "curl" in ua:
        return Response(
            status_code=200,
            headers={"Content-Type": "text/plain; charset=utf-8"},
            description=f"flag: {config.flag.curl}\n",
        )

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
                        <flag>FLAG{{{config.flag.web}}}</flag>
                        </html>"""

    return html(html_content)


if __name__ == "__main__":
    app.start(host="0.0.0.0", port=8080)
