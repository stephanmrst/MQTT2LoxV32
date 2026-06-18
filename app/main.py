from engine.port import APP_VERSION, create_legacy_app


def create_app():
    return create_legacy_app()


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8099, debug=False)
