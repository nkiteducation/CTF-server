import pathlib
import secrets

import msgspec
import pyzipper
from robyn import Request, Response, Robyn, html
from robyn.templating import JinjaTemplate

BASE_DIR = pathlib.Path(__file__).resolve().parent
ROCKYOU_PATH= BASE_DIR / "rockyou.txt"
SECRET_DIR = BASE_DIR / "secret"
JINJA_TEMPLATE = JinjaTemplate(BASE_DIR / "templates")

SECRET_DIR.mkdir(exist_ok=True)

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
    password = secrets.choice(config.list_passwords)
    zip_path = SECRET_DIR / "flag.zip"

    with pyzipper.AESZipFile(
        zip_path, "w", 
        compression=pyzipper.ZIP_DEFLATED, 
        encryption=pyzipper.WZ_AES
    ) as zf:
        zf.setpassword(password.encode("utf-8"))
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

    return JINJA_TEMPLATE.render_template("index.html", FLAG=config.flag.web)


if __name__ == "__main__":
    app.start(host="0.0.0.0", port=8080)
