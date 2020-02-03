import pymysql
from datetime import date

class MySQL(object):

    def __init__(self, host, user, pwd, db):
        self.host = host
        self.user = user
        self.pwd = pwd
        self.db = db

    def __GetConnect(self):
        if not self.db:
            raise(NameError, "没有设置数据库信息")
        self.conn = pymysql.connect(
            host=self.host, user=self.user, password=self.pwd, database=self.db, charset="utf8")
        cur = self.conn.cursor()
        if not cur:
            raise(NameError, "连接数据库失败")
        else:
            return cur

    def ExecQuery(self, sql, params=None, name_list=None):
        cur = self.__GetConnect()
        cur.execute(sql, params)
        reslist = cur.fetchall()
        # 查询完毕后必须关闭连接
        self.conn.close()
        result = list()
        if not name_list is None:
            for row in reslist:
                i = 0
                dic = dict()
                for name in name_list:
                    if isinstance(row[i], date):
                        dic[name] = row[i].strftime('%Y-%m-%d')
                    else:
                        dic[name] = row[i]
                    i = i + 1
                result.append(dic)
        else:
            for row in reslist:
                dic = dict()
                for i in range(reslist.rowcount):
                    dic[i] = row[i]
                result.append(dic)
        return result

    def ExecNonQuery(self, sql, params=None):
        cur = self.__GetConnect()
        cur.execute(sql, params)
        self.conn.commit()
        self.conn.close()
