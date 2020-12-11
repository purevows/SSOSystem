from app import app
# from flup.server.fcgi import WSGIServer


if __name__ == "__main__":
    # app.run()
    app.run(host="0.0.0.0", port=5000, debug=True)
