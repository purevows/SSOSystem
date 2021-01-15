from datetime import timedelta
from logging.handlers import TimedRotatingFileHandler
from functools import wraps
from flask import session, redirect, jsonify
from dbutils.pooled_db import PooledDB
from db_config import AuthDbPoolConfig as AuthConfig
from db_config import RedisConnectionPool as RedisConfig
import redis
import os
import logging
import pymysql
import traceback
import base62


redis_conn_pool = redis.ConnectionPool(host=RedisConfig.host, port=RedisConfig.port, password=RedisConfig.password,
                                       db=RedisConfig.db)
AuthDBPool = PooledDB(creator=pymysql, mincached=AuthConfig.mincached, maxcached=AuthConfig.maxcached,
                      maxconnections=AuthConfig.maxconnections, maxusage=AuthConfig.maxusage,
                      maxshared=AuthConfig.maxshared, blocking=AuthConfig.blocking, setsession=AuthConfig.setsession,
                      reset=AuthConfig.reset, user=AuthConfig.user, host=AuthConfig.host, port=AuthConfig.port,
                      password=AuthConfig.password, database=AuthConfig.db)


class ProductionConfig:
    SECRET_KEY = os.urandom(24)
    SESSION_TYPE = "redis"
    SESSION_REDIS = redis.Redis(host=RedisConfig.host, port=RedisConfig.port, password=RedisConfig.password,
                                db=RedisConfig.db)
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_NAME = "token"
    SESSION_KEY_PREFIX = "SSO:"
    Serial_number = "1000"


class DevelopConfig:
    SECRET_KEY = os.urandom(24)
    SESSION_TYPE = "redis"
    SESSION_REDIS = redis.Redis(host=RedisConfig.host, port=RedisConfig.port, password=RedisConfig.password,
                                db=RedisConfig.db)
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_NAME = "token"
    SESSION_KEY_PREFIX = "SSO:"
    Serial_number = "2000"


def log():
    log_mgr = logging.getLogger(__name__)
    log_mgr.setLevel(logging.INFO)
    if not log_mgr.handlers:
        # file_handler = logging.FileHandler("../serverlog/app.log", encoding="utf-8")
        file_handler = TimedRotatingFileHandler("../serverlog/app.log", when="W6", interval=1, encoding="utf-8")
        formatter = logging.Formatter(fmt="%(asctime)s %(levelname)s %(filename)s %(message)s",
                                      datefmt="%Y/%m/%d %X")
        file_handler.setFormatter(formatter)
        log_mgr.addHandler(file_handler)
    return log_mgr


def login_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if session.get("token") is None:
            return redirect("/login")
        return func(*args, **kwargs)
    return decorated_view


def authority_required(authority="user"):
    def wrapper(func):
        @wraps(func)
        def decorated_view(*args, **kwargs):
            if authority != "user":
                if authority == "综合管理部" and session.get("department") != "综合管理部":
                    return jsonify({"status": 401})
            return func(*args, **kwargs)
        return decorated_view
    return wrapper


def login_attempt_limit(username, method="set"):
    redis_conn = redis.Redis(connection_pool=redis_conn_pool)
    limit_counts = redis_conn.get(username + ":login_attempt_limit")
    if limit_counts is None:
        if method == "get":
            return 0
        redis_conn.set(username + ":login_attempt_limit", 1, ex=600)
        return 1
    if int(limit_counts.decode("utf-8")) >= 5:
        return int(limit_counts.decode("utf-8"))
    elif 0 < int(limit_counts.decode("utf-8")) < 5:
        if method == "get":
            return int(limit_counts.decode("utf-8"))
        redis_conn.set(username + ":login_attempt_limit", int(limit_counts.decode("utf-8")) + 1, ex=600)
        return int(limit_counts.decode("utf-8")) + 1
    else:
        return -1


def set_token(token):
    # noinspection PyBroadException
    try:
        username = token.split(":")[0]
        ticket = token.split(":")[1]
        redis_conn = redis.Redis(connection_pool=redis_conn_pool)
        ret = redis_conn.set(username, ticket, ex=7*24*60*60)  # ex = "seconds"
        if ret is not True:
            return 0
    except Exception:
        logger.error(traceback.format_exc())
        return 0
    return 1


def check_token(token):
    username = token.split(":")[0]
    ticket = token.split(":")[1]
    redis_conn = redis.Redis(connection_pool=redis_conn_pool)
    ret = redis_conn.get(username)
    if ret is None:
        return 0
    if ret.decode("utf-8") != ticket:
        return 0
    return 1


def set_session_expired(token):
    # noinspection PyBroadException
    try:
        ticket = token.split(":")[1]
        redis_conn = redis.Redis(connection_pool=redis_conn_pool)
        ret = redis_conn.expire("SSO:" + ticket, 0)
        if ret == 0:
            logger.info("Session " + ticket + " had been deleted")
        elif ret == 1:
            logger.info("Set session expired:" + ticket)
        else:
            logger.error("Unknown error")
    except Exception:
        logger.error(traceback.format_exc())
        return 0
    return 1


def query_login(username, password):
    # noinspection PyBroadException
    try:
        db_conn = AuthDBPool.connection()
        db_cursor = db_conn.cursor()
        db_cursor.execute("select password, status from org_person where account = '%s'" % username)
        db_result = db_cursor.fetchone()
        if db_result is None:
            ret = 2  # "账号不存在"
        elif db_result[1] != 1:
            ret = 3  # "账号已停用"
        elif password != db_result[0]:
            ret = 2  # "密码错误"
        elif password == db_result[0]:
            ret = 1  # password correct
        else:
            ret = 4
    except Exception:
        logger.error(traceback.format_exc())
        return traceback.format_exc()
    return ret


def query_user_info(token):
    # noinspection PyBroadException
    try:
        username = token.split(":")[0]
        db_conn = AuthDBPool.connection()
        db_cursor = db_conn.cursor()
        db_cursor.execute("select id, name, status from org_person where account = '%s'" % username)
        db_result = db_cursor.fetchone()
        if db_result is None:
            ret = 2  # The account doesn't exist
        elif db_result[2] != 1:
            ret = 3  # The account was blocked
        else:
            db_cursor.execute("select org_id from org_staff where person_id = '%s' and status = 1" % db_result[0])
            org_group = db_cursor.fetchall()
            if len(org_group) == 1:
                org_id = org_group[0][0]
            elif len(org_group) > 1:
                org_id = None
                for org in org_group:
                    if org_id is None:
                        org_id = org[0]
                    for key, value in department_sequence.items():
                        if org[0] == key:
                            if department_sequence[org[0]] < department_sequence[org_id]:
                                org_id = org[0]
            elif len(org_group) < 1:
                ret = 2
                return ret
            db_cursor.execute("select name from org_organization where id = '%s'" % org_id)
            ret = [db_result[1], db_cursor.fetchone()[0], org_id]
    except Exception:
        logger.error(traceback.format_exc())
        return traceback.format_exc()
    return ret


def rc4_init_vector(key):
    state_vector = []
    temporary_vector = []
    for i in range(0, 256):
        state_vector.append(i)
        temporary_vector.append(key[i % len(key)])
    j = 0
    for i in range(0, 256):
        j = (j + state_vector[i] + ord(temporary_vector[i])) % 256
        state_vector[i], state_vector[j] = state_vector[j], state_vector[i]
    return state_vector


def rc4_encrypt(message, key):
    # result = str(base64.b64encode(result.encode("utf-8")), "utf-8")
    result = rc4_process(message, rc4_init_vector(key))
    result = base62.encodebytes(result.encode())
    return result


def rc4_decrypt(message, key):
    # message = bytes.decode(base64.b64decode(message.encode("utf-8")))
    message = base62.decodebytes(message).decode("utf-8")
    result = rc4_process(message, rc4_init_vector(key))
    return result


def rc4_process(message, state_vector):
    result = ""
    i = j = 0
    for element in message:
        i = (i + 1) % 256
        j = (j + state_vector[i]) % 256
        state_vector[i], state_vector[j] = state_vector[j], state_vector[i]
        t = (state_vector[i] + state_vector[j]) % 256
        k = state_vector[t]
        result = result + chr(ord(element) ^ k)
    return result


'''
def sso_type_required(sso_type):
    def decorator(func):
        @functools.wraps(func)
        def check_type(*args, **kwargs):
            pass
'''


flask_config = {
    "production": ProductionConfig,
    "development": DevelopConfig
}
rc4_key = "fengyishuang"

department_sequence = {
    "8e921ad266f2979a0166f2b093af0008": 1,  # 集团公司高管
    "f1ec3e926cfa01ca016d19d500fc4d22": 2,  # 党群工作部
    "8e921ad266f2979a0166f2b09417001b": 3,  # 人力资源部
    "8e921ad266f2979a0166f2b0944d0022": 4,  # 纪检监察审计室
    "8e921ad266f2979a0166f2b0947e0026": 5,  # 综合管理部
    "8e921ad266f2979a0166f2b094cf0031": 6,  # 计划财务部
    "8e921ad266f2979a0166f2b094fd0038": 7,  # 战略与投资发展部
    "8e921ad266f2979a0166f2b09520003d": 8,  # 规划与建设管理部
    "8e921ad266f2979a0166f2b095990050": 9,  # 资产运营部
    "f1ec3e926bf50620016bfeeaa3b065a8": 10,  # 建设公司
    "ff8080816838637301683b0a40a40047": 11,  # 置业公司
    "ff8080816838637301683b0a6ed80049": 12,  # 站场公司
    "ff8080816838637301683b0a9e75004b": 13,  # 开泰公司
    "ff808081690e247901691432259f5e66": 14,  # 副总经济师
    "ff808081690e24790169143272535fd4": 15   # 副总法律顾问
}
logger = log()
