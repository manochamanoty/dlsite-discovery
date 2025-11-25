from flask import Flask, render_template, send_from_directory

from dlsite_app.config import settings
from dlsite_app.routes.api import api_bp


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(settings.base_dir / "templates"),
        static_folder=str(settings.base_dir / "static"),
    )

    app.register_blueprint(api_bp, url_prefix="/api")
    app.config["JSON_AS_ASCII"] = False

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/images/<path:filename>")
    def images(filename: str):
        return send_from_directory(settings.image_root, filename)

    return app
