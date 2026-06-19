from engine.port import APP_VERSION, create_legacy_app


def create_app():
    app = create_legacy_app()
    app.config["JSON_AS_ASCII"] = False
    if hasattr(app, "json"):
        app.json.ensure_ascii = False
    return app


app = create_app()


@app.after_request
def force_utf8_response(response):
    if response.content_type.startswith("text/html"):
        response.headers["Content-Type"] = "text/html; charset=utf-8"
    elif response.content_type.startswith("text/event-stream"):
        response.headers["Content-Type"] = "text/event-stream; charset=utf-8"
    elif response.content_type.startswith("application/json"):
        response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8099, debug=False)
