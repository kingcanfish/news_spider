# -*-coding:utf-8 -*-
import requests
import re
import time
from bs4 import BeautifulSoup
from mysql_helper import MySQL
from lxml import etree

# class MainNews():
#     new_list_url = 'http://news.ncu.edu.cn/ndyw/index.htm'
#     def get_new_list_url():
#         new_list_url = 'http://news.ncu.edu.cn/ndyw/index.htm'
#         response = requests.get(url=new_list_url).text
#         print(response)

# if __name__ == "__main__":
#     a = MainNews()
#     a.get_new_list_url()
#     print("cc")
# new_list_url = 'http://news.ncu.edu.cn/ndyw/index.htm'
# response = requests.get(url = new_list_url).text

class Spider(object):
    headers = {
        'User-Agent': """Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36"""
    }

    db = MySQL('*', '*', '*', '*')

class MainNewsSpider:

    def __init__(self, base_url,flag=True):
        self.session = requests.session()
        self.base_url =base_url
        self.flag =flag
        self.db = MySQL('*', '*', '*', '*t')
    # 南昌大学新闻网南大要闻栏目

    def get_news_list(self):
        if self.flag:
            front_url = 'http://news.ncu.edu.cn/ndyw/'
        else:
            front_url = 'http://news.ncu.edu.cn/kydt/'
        html = self.session.get(self.base_url).text.encode('latin-1').decode()
        soup = BeautifulSoup(html, "html.parser")
        lista = soup.select(".article_list > ul > li > a ")
        news_urls = [front_url+element['href'] for element in lista]
        print(news_urls)
        return news_urls




    def get_content(self, url):
        """
        :param url: 该条新闻的url。
        :return: 返回标题，内容(html源码)，时间。
        """
        dictory = {}
        r = requests.get(url, timeout=10)
        if r.status_code == 404:
            return
        html = r.text.encode('latin-1').decode()
        soup = BeautifulSoup(html, 'lxml')
        try:
            dictory['title'] = soup.select('li[class="show_title"] > font')[0].get_text()
        except Exception:
            return
        if dictory['title'] == '':
            dictory['title'] = soup.select('li[class="show_title"]')[0].get_text()

        time_pattern = re.compile('<span class="dat4">(.*?)</span>')
        dictory['publish_time'] = re.findall(time_pattern, html)[0]
        dictory['publish_time'] = dictory['publish_time'][:4] + '-' + dictory['publish_time'][5:7] + '-' + \
                                  dictory['publish_time'][8:]

        the_li = soup.select('li[id="zoom"]')[0]
        dictory['body'] = list(the_li)
        dictory['body'] = ''.join([str(tag) for tag in dictory['body']]).strip()

        # 很多年以前的图片都是相对路径，将相对路径改为绝对路径

        
        img_pattern = re.compile('(<img.*?src=")(.*?)(".*?>)', re.S)
        print(img_pattern)

        def _add_img_base_url(html):
            if html.group(2)[2] == '/':
                return html.group(1) + "http://news.ncu.edu.cn" + html.group(2)[2:] + html.group(3)
            else:
                return html.group()

        dictory['body'] = re.sub(img_pattern, _add_img_base_url, dictory['body'])
 
        dictory['author'] = soup.select('li[class="show_date"] > span[class="dat1"]')[0].get_text()
        if not dictory['author']:
            dictory['author'] = '佚名'

        time.sleep(0.5)
        return dictory

    def update_main_news_url(self):
        if self.flag:
            main_sql = 'SELECT url FROM comprehensive_main_news WHERE come_from="main_news" ' \
                    'ORDER BY publish_time DESC LIMIT 20'

            save_sql = 'INSERT INTO comprehensive_main_news (title, publish_time, body, author, url, come_from) ' \
                       'VALUES (%(title)s, %(publish_time)s, %(body)s, %(author)s, %(url)s, %(come_from)s)'
        else:
            main_sql = 'SELECT url FROM teaching_science_news WHERE come_from="teaching_news" ' \
                   'ORDER BY publish_time DESC LIMIT 20'
            save_sql = 'INSERT INTO teaching_science_news (title, publish_time, body, author, url, come_from) ' \
                       'VALUES (%(title)s, %(publish_time)s, %(body)s, %(author)s, %(url)s, %(come_from)s)'
            
        name_list = ['url']
        pre_urls = self.db.ExecQuery(main_sql, name_list=name_list)

        pre_url_list = []
        for pre_url in pre_urls:
            pre_url_list.append(pre_url['url'])

        latest_url = pre_url_list[0]

        now_urls = self.get_news_list()
        # print(now_urls)
        # print(pre_url_list)
        newest_url = now_urls[0]
        

        if latest_url == newest_url:
            return
        else:
            for url in now_urls[::-1]:
                if url in pre_url_list:
                    now_urls.remove(url)

            for url in now_urls:
                try:
                    content = self.get_content(url)
                    data = {'title': content['title'],
                            'publish_time': content['publish_time'],
                            'body': content['body'],
                            'author': content['author'],
                            'url': url,
                            'come_from': "main_news"}
                    # print(data)
                    self.db.ExecNonQuery(save_sql, data)
                    print("done1")
                except Exception as e:
                    print(e)


class DeanSiteSpider(Spider):
    """
    爬南大教务处。
    这个之所以写的很麻烦，是因为很多链接点了就直接下载，所以特别处理。
    """

    def save_all(self):

        save_sql = 'INSERT INTO teaching_notice (title, publish_time, body, url, come_from) ' \
                   'VALUES (%(title)s, %(publish_time)s, %(body)s, %(url)s, %(come_from)s)'

        for url, title, publish_time in self.get_departments_notice(get_all=True):
            try:
                content = self.get_content(url, title, publish_time)
                if content is None:
                    continue
                else:
                    self.db.ExecNonQuery(save_sql, {'title': content['title'],
                                                    'publish_time': content['publish_time'],
                                                    'body': content['body'],
                                                    'url': url,
                                                    'come_from': "departments_notice"})
            except Exception:
                continue

        for url, title, publish_time in self.get_teaching_things(get_all=True):
            try:
                content = self.get_content(url, title, publish_time)
                if content is None:
                    continue
                else:
                    self.db.ExecNonQuery(save_sql, {'title': content['title'],
                                                    'publish_time': content['publish_time'],
                                                    'body': content['body'],
                                                    'url': url,
                                                    'come_from': "teaching_things"})
            except Exception:
                continue

    def get_departments_notice(self, get_all=False):
        """
        :param get_all: 若为ture则获取该子菜单所有新闻网址，反之则之获取一页。
        :return: 院系通知模块的新闻网址
        """
        departments_notice_url = 'http://jwc.ncu.edu.cn/yxtz/index.htm'

        if get_all:
            return self._get_all_news(departments_notice_url)
        else:
            return self._get_a_page_news(departments_notice_url)

    def get_teaching_things(self, get_all=False):
        """
        :param get_all: 若为ture则获取该子菜单所有新闻网址，反之则之获取一页。
        :return: 教务通知模块的新闻网址
        """
        teaching_things_url = 'http://jwc.ncu.edu.cn/jwtz/index.htm'

        if get_all:
            return self._get_all_news(teaching_things_url)
        else:
            return self._get_a_page_news(teaching_things_url)

    def get_content(self, url, title, publish_time):
        """
        :param url: 该条新闻的url。
        :return: 返回标题，内容(html源码)，时间。
        """
        dictory = {}
        if url[-3:] != 'htm':
            dictory['url'] = url
            dictory['title'] = title
            mybody = '<p>详情请点击文件地址<a href=%s>' % url + title + "</a></p>"
            dictory['body'] = mybody
            dictory['publish_time'] = publish_time
            return dictory
        r = requests.get(url, headers=self.headers, timeout=10)
        if r.status_code == 404:
            return
        html = r.text.encode('latin-1').decode()
        soup = BeautifulSoup(html, 'lxml')

        dictory['title'] = title

        dictory['publish_time'] = publish_time

        the_li = soup.select('div[class="font"]')[0]
        dictory['body'] = list(the_li)
        dictory['body'] = ''.join([str(tag) for tag in dictory['body']]).strip()

        # 过滤掉尾部以及脚本
        delete_pattern1 = re.compile('<font color="0000ff">.一篇:.*?<a.*?</a>', re.S)
        delete_pattern2 = re.compile('<script src=.*?</script>', re.S)
        dictory['body'] = re.sub(delete_pattern1, '', dictory['body'])
        dictory['body'] = re.sub(delete_pattern2, '', dictory['body'])

        base_url = 'http://jwc.ncu.edu.cn'
        img_pattern = re.compile('<img.*?/>', re.S)
        link_pattern = re.compile('(<a.*?href=")(.*?)(".*?>)', re.S)
        changeline_pattern = re.compile(r'"/n"')

        def _delete_img(html):
            return ''

        def _add_link_base_url(html):
            return html.group(1) + base_url + html.group(2)[2:] + html.group(3)

        def _delete_barrier(html):
            return ""

        dictory['body'] = re.sub(img_pattern, _delete_img, dictory['body'])
        dictory['body'] = re.sub(link_pattern, _add_link_base_url, dictory['body'])
        dictory['body'] = re.sub(changeline_pattern, _delete_barrier, dictory['body'])

        time.sleep(0.5)

        return dictory

    def _get_a_page_news(self, url):
        """
        :param url: 二级页面的网址。
        :return: 该二级页面一页的新闻网址。
        """
        now_base_url = url[:27]
        html = requests.get(url, headers=self.headers).text.encode('latin-1').decode()
        selector = etree.HTML(html)
        suffix_urls = selector.xpath('//div[@class="top-bg"]//dd/a[@onfocus="this.blur()"]/@href')
        titles = selector.xpath('//div[@class="top-bg"]//dd/a[@onfocus="this.blur()"]/text()')
        publish_times = selector.xpath('//div[@class="top-bg"]//span/font/text()')

        publish_times = [publish_time[1:-1] for publish_time in publish_times]

        for pos, suffix_url in enumerate(suffix_urls):
            yield now_base_url + suffix_url, titles[pos], publish_times[pos]

    def _get_all_news(self, url):
        """
        is_first = 是第一页。
        :param url: 二级页面的网址。
        :return: 该二级页面所有的新闻网址。
        """
        is_first = True
        judge_pattern = re.compile('条，分(.*?)页，当前第<font color=red>(.*?)</font>页')

        def _judge_if_last(page_html):
            try:
                last_page, now_page = re.findall(judge_pattern, page_html)[0]
            except Exception as e:
                print(str(e))
                raise ConnectionRefusedError('please review the code or change your ip')
            return last_page == now_page

        def _get_html(page_url):
            page_html = requests.get(page_url, headers=self.headers).text.encode('latin-1').decode()

            return page_html

        count = 0
        while True:
            if is_first:
                yield from self._get_a_page_news(url)

                is_first = False
                html = _get_html(url)
                if _judge_if_last(html):
                    break

                count += 1
                url = url[:32] + str(count) + url[-4:]

            else:
                yield from self._get_a_page_news(url)

                html = _get_html(url)
                if _judge_if_last(html):
                    break

                count += 1
                url = url[:32] + str(count) + url[-4:]

class UpdateDeanSiteSpider:
    def __init__(self):
        self.session = requests.session()
        self.db = MySQL()

    def update_departments_notice(self):
        main_sql = 'SELECT url FROM teaching_notice WHERE come_from="departments_notice" ' \
                   'ORDER BY publish_time DESC LIMIT 20'
        name_list = ['url']
        pre_urls = self.db.ExecQuery(main_sql, name_list=name_list)

        pre_url_list = []
        for pre_url in pre_urls:
            pre_url_list.append(pre_url['url'])

        latest_url = pre_url_list[0]
        url_getter = DeanSiteSpider()
        now_news = list(url_getter.get_departments_notice())
        now_urls = []
        for news in now_news:
            now_urls.append(news[0])
        newest_url = now_urls[0]

        if latest_url == newest_url:
            return
        else:
            for url in now_urls[::-1]:
                if url in pre_url_list:
                    now_news.pop(now_urls.index(url))
            save_sql = 'INSERT INTO teaching_notice (title, publish_time, body, url, come_from) ' \
                       'VALUES (%(title)s, %(publish_time)s, %(body)s, %(url)s, %(come_from)s)'

            for url, title, publish_time in now_news:
                try:
                    content = url_getter.get_content(url, title, publish_time)
                    if content is None:
                        continue
                    else:
                        self.db.ExecNonQuery(save_sql, {'title': content['title'],
                                                        'publish_time': content['publish_time'],
                                                        'body': content['body'],
                                                        'url': url,
                                                        'come_from': "departments_notice"})
                except Exception:
                    continue

    def update_teaching_things(self):
        main_sql = 'SELECT url FROM teaching_notice WHERE come_from="teaching_things" ' \
                   'ORDER BY publish_time DESC LIMIT 20'

        name_list = ['url']
        pre_urls = self.db.ExecQuery(main_sql, name_list=name_list)
        pre_url_list = []
        for pre_url in pre_urls:
            pre_url_list.append(pre_url['url'])

        latest_url = pre_url_list[0]
        url_getter = DeanSiteSpider()
        now_news = list(url_getter.get_teaching_things())

        now_urls = []
        for news in now_news:
            now_urls.append(news[0])
        newest_url = now_urls[0]

        if latest_url == newest_url:
            return
        else:
            for url in now_urls[::-1]:
                if url in pre_url_list:
                    now_news.pop(now_urls.index(url))
            save_sql = 'INSERT INTO teaching_notice (title, publish_time, body, url, come_from) ' \
                       'VALUES (%(title)s, %(publish_time)s, %(body)s, %(url)s, %(come_from)s)'

            for url, title, publish_time in now_news:
                try:
                    content = url_getter.get_content(url, title, publish_time)
                    if content is None:
                        continue
                    else:
                        self.db.ExecNonQuery(save_sql, {'title': content['title'],
                                                        'publish_time': content['publish_time'],
                                                        'body': content['body'],
                                                        'url': url,
                                                        'come_from': "teaching_things"})
                except Exception:
                    continue




if __name__ == "__main__":

    main = MainNewsSpider(base_url = 'http://news.ncu.edu.cn/ndyw/index.htm')
    main.update_main_news_url()
    tech = MainNewsSpider(base_url = 'http://news.ncu.edu.cn/kydt/index.htm',flag=False)
    tech.update_main_news_url()

    bean = UpdateDeanSiteSpider()
    bean.update_departments_notice()
    bean.update_teaching_things()
    print("ok!")
