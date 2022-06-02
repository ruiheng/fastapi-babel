from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from fastapi_babel import _  # noqa
from fastapi_babel import Babel, BabelConfigs

templates = Jinja2Templates(directory="templates")
configs = BabelConfigs(
    ROOT_DIR=__file__,
    BABEL_DEFAULT_LOCALE="en",
    BABEL_TRANSLATION_DIRECTORY="lang",
)

app = FastAPI()
babel = Babel(app, configs=configs)
babel.install_jinja(templates)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/items/{id}", response_class=HTMLResponse)
async def read_item(request: Request, id: str):
    return templates.TemplateResponse("item.html", {"request": request, "id": id})


if __name__ == "__main__":
    babel.run_cli()
