from flask import Flask, request, session, jsonify, render_template, redirect
from flask_session import Session
from flask_cors import cross_origin
from plugin import flask_config, logger, query_login, query_user_info, check_token, set_token, login_attempt_limit
from plugin import set_session_expired, rc4_encrypt, rc4_decrypt, rc4_key, login_required, authority_required
from ssoplugin import create_new_item, modify_content, delete_item, query_data, check_app_server, origins_list
import datetime
import json


web_type = "development"  # development or production
app = Flask(__name__)
app.config.from_object(flask_config[web_type])
Session(app)


@app.route("/login", methods=["GET", "POST"])
@cross_origin(methods=["POST"], origins=origins_list(), supports_credentials=1)
def sso_login():
    if request.method == "GET":
        app_server = request.args.get("AppServer", None)
        srv_path = request.args.get("srv_path", "")
        if app_server is None:
            return "Hello World!"
        app_server = check_app_server(app_server)
        if app_server == 0:
            return "Hello World!"
        if session.get("token") is not None:
            return redirect(app_server + "/" + srv_path + "?token=" + session.get("token"))
        return render_template("login.html", app_server=app_server, srv_path=srv_path)
    elif request.method == "POST":
        token = request.headers.get("Token")
        if token is not None:
            # the header contains token
            token = rc4_decrypt(token, rc4_key)
            redis_ret = check_token(token)
            session.clear()
            if redis_ret == 1:
                # Token is valid
                ret = query_user_info(token)
                if ret == 2:
                    return jsonify({"status": 200, "retCode": 2})  # The account doesn't exist
                elif ret == 3:
                    return jsonify({"status": 200, "retCode": 3})  # The account was blocked
                else:
                    logger.info("Login success:" + token.split(":")[0])
                    return jsonify({"status": 200, "retCode": 1, "name": ret[0], "department": ret[1],
                                    "department_id": ret[2], "username": token.split(":")[0]})
                    # Matched correct token
            else:
                set_session_expired(token)
                return jsonify({"status": 200, "retCode": 4})  # No match, login needed
        else:
            # the header doesn't contains token
            form_data = json.loads(request.get_data().decode("utf-8"))
            if "username" not in form_data or "password" not in form_data:
                return jsonify({"status": 200, "retCode": 5})  # No match, need login
            username = form_data["username"]
            password = form_data["password"]
            if session.get("token") is not None:
                # maybe from cross_origin
                token = rc4_decrypt(session.get("token"), rc4_key)
                if token.split(":")[0] == username:
                    redis_ret = check_token(token)
                    if redis_ret == 1:
                        logger.info("Send token to cross_origin:" + username)
                        return jsonify({"status": 200, "retCode": 1, "token": session.get("token")})
            limit_counts = login_attempt_limit(username, method="get")
            if limit_counts >= 5:
                logger.info("Too many login attempts:" + username)
                return jsonify({"status": 200, "retCode": 6})
            ret = query_login(username, password)
            logger.info("Attempt Login:" + username)
            if ret == 2:
                limit_counts = login_attempt_limit(username)
                if limit_counts == -1:
                    logger.error("Internal Server Error")
                    return jsonify({"status": 200, "retCode": 4})
                logger.info("Login fail: wrong account or password, current limit times=" + str(limit_counts))
                return jsonify({"status": 200, "retCode": 2, "limit_counts": limit_counts})
                # Wrong username or password
            elif ret == 3:
                logger.info("Login fail: the account was blocked")
                return jsonify({"status": 200, "retCode": 3})  # The account was blocked
            elif ret == 1:
                token = username + ":" + session.sid
                redis_ret = set_token(token)
                token = rc4_encrypt(token, rc4_key)
                if redis_ret != 1:
                    return jsonify({"status": 200, "retCode": 7})  # Server Error
                session["token"] = token
                logger.info("Create token:" + username)
                return jsonify({"status": 200, "retCode": 1, "token": token})
                # Login success, create token
            else:
                return jsonify({"status": 200, "retCode": 4})


@app.route("/setting", methods=["GET"])
@login_required
def list_item():
    # if session.get("token") is None:
    #     return redirect("/login")
    if session.get("name") is None or session.get("department") is None:
        ret = query_user_info(rc4_decrypt(session.get("token"), rc4_key))
        if ret == 2:
            return "The account doesn't exist"
        elif ret == 3:
            return "The account was blocked"
        else:
            session["name"] = ret[0]
            session["department"] = ret[1]
    if request.args.get("token") is not None:
        return redirect("setting")
    current_user = session.get("name")
    current_department = session.get("department")
    current_time = datetime.date.today().isoformat()
    get_item_list = query_data()
    logger.info("User " + current_user + " loads the item list of " + current_time)
    return render_template("/configuration.html", current_time=current_time, item_list=get_item_list,
                           current_user=current_user, current_department=current_department)


@app.route("/add_site")
@login_required
@authority_required("综合管理部")
def add_content_page():
    # if session.get("name") is None:
    #     return redirect("/login")
    current_time = datetime.date.today().isoformat()
    current_user = session.get("name")
    current_department = session.get("department")
    return render_template("/add_site.html", current_time=current_time, current_user=current_user,
                           current_department=current_department)


@app.route("/modify", methods=["POST"])
@login_required
@authority_required("综合管理部")
def modify():
    # if session.get("name") is None:
    #     abort(400)
    form_data = json.loads(request.get_data().decode("utf-8"))
    form_data["site_name"] = form_data["site_name"].replace("\n", "")
    form_data["serial_number"] = form_data["serial_number"].replace("\n", "")
    form_data["url"] = form_data["url"].replace("\n", "")
    form_data["remark"] = form_data["remark"].replace("\n", "")
    form_data["site_name"] = form_data["site_name"].replace("\t", "")
    form_data["serial_number"] = form_data["serial_number"].replace("\t", "")
    form_data["url"] = form_data["url"].replace("\t", "")
    form_data["remark"] = form_data["remark"].replace("\t", "")
    # form_data["site_name"] = form_data["site_name"].replace(" ", "")
    form_data["serial_number"] = form_data["serial_number"].replace(" ", "")
    form_data["url"] = form_data["url"].replace(" ", "")
    ret = modify_content(form_data)
    if ret == 1:
        logger.info("User " + session.get("name") + " submit modified items")
        return jsonify({"status": 200, "message": "success"})
    else:
        return jsonify({"status": 400, "message": ret})


@app.route("/del_item", methods=["POST"])
@login_required
@authority_required("综合管理部")
def del_item():
    # if session.get("name") is None:
    #     abort(400)
    form_data = json.loads(request.get_data().decode("utf-8"))
    ret = delete_item(form_data)
    if ret == 1:
        logger.info("User " + session.get("name") + " delete items")
        return jsonify({"status": 200, "message": "success"})
    else:
        return jsonify({"status": 400, "message": ret})


@app.route("/add_new_site", methods=["POST"])
@login_required
@authority_required("综合管理部")
def add_new_content():
    # if session.get("name") is None:
    #     abort(400)
    list_form_data = json.loads(request.get_data().decode("utf-8"))
    for form_data in list_form_data:
        form_data["site_name"] = form_data["site_name"].replace("\n", "")
        form_data["serial_number"] = form_data["serial_number"].replace("\n", "")
        form_data["url"] = form_data["url"].replace("\n", "")
        form_data["remark"] = form_data["remark"].replace("\n", "")
        form_data["site_name"] = form_data["site_name"].replace("\t", "")
        form_data["serial_number"] = form_data["serial_number"].replace("\t", "")
        form_data["url"] = form_data["url"].replace("\t", "")
        form_data["remark"] = form_data["remark"].replace("\t", "")
        # form_data["site_name"] = form_data["site_name"].replace(" ", "")
        form_data["serial_number"] = form_data["serial_number"].replace(" ", "")
        form_data["url"] = form_data["url"].replace(" ", "")
    ret = create_new_item(list_form_data)
    if ret == 1:
        logger.info("User " + session.get("name") + " add new items")
        return jsonify({"status": 200, "message": "success", "url": "/setting"})
    else:
        return jsonify({"status": 400, "message": ret})


@app.route("/logout", methods=["GET"])
def sso_logout():
    app_server = request.args.get("AppServer")
    if app_server is None:
        return "Hello World!"
    app_server = check_app_server(app_server)
    if app_server is None:
        return "Hello World!"
    if session.get("token") is not None:
        session.clear()
    return redirect(app_server)


@app.route("/clear_session", methods=["GET"])
def clear_session():
    return redirect("/logout?AppServer=" + flask_config[web_type].Serial_number)


if __name__ == '__main__':
    app.run()
