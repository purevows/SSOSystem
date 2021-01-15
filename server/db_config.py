class SSODbPoolConfig:
    host = "192.168.0.0"
    port = 3306
    db = "######"
    user = "######"
    password = "######"
    mincached = 1
    maxcached = 1
    maxshared = 3
    maxconnections = 5
    blocking = True
    maxusage = 100
    setsession = None
    reset = True


class AuthDbPoolConfig:
    host = "######"
    port = 3306
    db = "######"
    user = "######"
    password = "######"
    mincached = 1
    maxcached = 3
    maxshared = 10
    maxconnections = 50
    blocking = True
    maxusage = 100
    setsession = None
    reset = True


class RedisConnectionPool:
    host = "192.168.0.0"
    port = 12500
    password = "######"
    db = 0


'''
    :param mincached:连接池中空闲连接的初始数量
    :param maxcached:连接池中空闲连接的最大数量
    :param maxshared:共享连接的最大数量
    :param maxconnections:创建连接池的最大数量
    :param blocking:超过最大连接数量时候的表现，为True等待连接数量下降，为false直接报错处理
    :param maxusage:单个连接的最大重复使用次数
    :param setsession:optional list of SQL commands that may serve to prepare
        the session, e.g. ["set datestyle to ...", "set time zone ..."]
    :param reset:how connections should be reset when returned to the pool
        (False or None to rollback transcations started with begin(),
        True to always issue a rollback for safety's sake)
    :param host:数据库ip地址
    :param port:数据库端口
    :param db:库名
    :param user:用户名
    :param passwd:密码
    :param charset:字符编码
'''