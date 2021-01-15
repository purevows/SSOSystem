from dbutils.pooled_db import PooledDB
from db_config import SSODbPoolConfig as SSOConfig
from plugin import logger
import pymysql
import traceback
import uuid


SSODBPool = PooledDB(creator=pymysql, mincached=SSOConfig.mincached, maxcached=SSOConfig.maxcached,
                     maxconnections=SSOConfig.maxconnections, maxusage=SSOConfig.maxusage,
                     maxshared=SSOConfig.maxshared, blocking=SSOConfig.blocking, setsession=SSOConfig.setsession,
                     reset=SSOConfig.reset, user=SSOConfig.user, host=SSOConfig.host, port=SSOConfig.port,
                     password=SSOConfig.password, database=SSOConfig.db)


def create_new_item(list_form_data):
    for form_data in list_form_data:
        ret = check_form_data(form_data)
        if ret != 1:
            return ret
    # noinspection PyBroadException
    try:
        db_conn = SSODBPool.connection()
        db_cursor = db_conn.cursor()
        for form_data in list_form_data:
            db_cursor.execute("insert into sso_site_list(id, site_name, serial_number, url, origins_permission, remark)"
                              " values ('%s', '%s', '%s', '%s', '%s', '%s')" %
                              (str(uuid.uuid1()).replace('-', ''), form_data["site_name"], form_data["serial_number"],
                               form_data["url"], form_data["origins_permission"], form_data["remark"],))
            db_conn.commit()
        db_conn.close()
    except Exception:
        logger.error(traceback.format_exc())
        return traceback.format_exc()
    return 1


def delete_item(form_data):
    # noinspection PyBroadException
    try:
        db_conn = SSODBPool.connection()
        db_cursor = db_conn.cursor()
        db_cursor.execute("delete from sso_site_list where id = '%s'" % form_data["id"])
        db_conn.commit()
        db_conn.close()
    except Exception:
        logger.error(traceback.format_exc())
        return traceback.format_exc()
    return 1


def modify_content(form_data):
    ret = check_form_data(form_data)
    if ret != 1:
        return ret
    # noinspection PyBroadException
    try:
        db_conn = SSODBPool.connection()
        db_cursor = db_conn.cursor()
        db_cursor.execute("update sso_site_list set site_name = '%s', serial_number = '%s', url = '%s',"
                          "origins_permission = '%s',remark = '%s' where id = '%s'" %
                          (form_data["site_name"], form_data["serial_number"], form_data["url"],
                           form_data["origins_permission"], form_data["remark"], form_data["id"]))
        db_conn.commit()
        db_conn.close()
    except Exception:
        logger.error(traceback.format_exc())
        return traceback.format_exc()
    return 1


def query_data():
    db_conn = SSODBPool.connection()
    db_cursor = db_conn.cursor()
    db_cursor.execute("select id, site_name, serial_number, url, origins_permission, remark from sso_site_list")
    data = db_cursor.fetchall()
    ret = []
    for i in data:
        ret.append({"id": i[0], "site_name": i[1], "serial_number": i[2], "url": i[3], "origins_permission": i[4],
                    "remark": i[5]})
    # ('id', 'content', 'department', ...)
    return ret


def check_app_server(app_server):
    db_conn = SSODBPool.connection()
    db_cursor = db_conn.cursor()
    db_cursor.execute("select url from sso_site_list where serial_number = '%s'" % app_server)
    ret = db_cursor.fetchone()
    if ret is None:
        return 0
    else:
        return ret[0]


def origins_list():
    db_conn = SSODBPool.connection()
    db_cursor = db_conn.cursor()
    db_cursor.execute("select url from sso_site_list where origins_permission = 1")
    data = db_cursor.fetchall()
    ret = []
    for i in data:
        ret.append(i[0])
    return ret


def check_form_data(form_data):
    for key, value in form_data.items():
        if key == "site_name":
            if len(value) > 255:
                return "the length of \"site_name\" is out of range"
        elif key == "serial_number":
            if len(value) > 4:
                return "the length of \"serial_number\" is out of range"
        elif key == "url":
            if len(value) > 255:
                return "the length of \"url\" is out of range"
        elif key == "remark":
            if len(value) > 255:
                return "the length of \"remark\" is out of range"
        elif key == "origins_permission":
            if value not in [0, 1]:
                return "the type of \"origins_permission\" is error"
    return 1