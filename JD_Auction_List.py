#
# 京东夺宝岛已结束拍卖详情抓取一：任务列表
#
# 从京东夺宝岛主页获取已经开始拍卖的商品ID，加入数据库，供抓取拍卖详情的爬虫调用
# 商品的拍卖状态是Javascript渲染的，所以用了Selenium + PhantomJS
from selenium import webdriver
import time, pymysql

# 从数据库中获取已存在的任务列表
def get_old_ids():
    connection = pymysql.connect(host='localhost',
                            user='root',
                            password='mypassword',
                            db='JD',
                            charset='utf8mb4',
                            cursorclass=pymysql.cursors.DictCursor)
    cursor = connection.cursor()
    cursor.execute('select item_id from Auction')
    response = cursor.fetchall()
    results = set()
    for di in response:
        results.add(di['item_id'])
    connection.close()
    return results

# 抓取新的任务列表
def get_new_ids():
    new_ids = {}
    old_ids = get_old_ids()
    driver = webdriver.PhantomJS(executable_path='D:/Program Files/phantomjs/bin/phantomjs.exe')
    # 最多抓取30页，其实同时开始拍卖的商品列表不超过20页
    for i in range(1, 31):
        # url过滤掉一口价的商品，并且按拍卖开始时间排序，这样前面的页都是已开始拍卖的商品，后面的都是等待开拍的商品
        driver.get('http://dbd.jd.com/auctionList.html?t=1&auctionType=5&t=1&sortField=0&limit=40&page=' + str(i))
        # xpath筛选出已开始拍卖和拍卖刚刚结束的商品
        elements = driver.find_elements_by_xpath('//div[@class="lmc"]//li[@class="" or @class="over"]')
        for element in elements:
            # 得到商品ID
            item_id = element.get_attribute('id')[3:]
            # 去掉先前抓取过的
            if item_id not in old_ids:
                new_ids.update({item_id: str(time.localtime().tm_hour)})
        # 中间某一页抓取的不足40，说明这一页是已开始拍卖和等待拍卖的分隔页，抓取到这里就可以结束了
        if len(elements) < 40:
            break
    return new_ids

# 把新获取的商品ID加入数据库
# item_id是商品ID
# 新加入的stats状态都是new，后面要抓取具体商品信息的时候，只选择stats是new的来抓，抓完后改成done
# time1是得到商品ID的时间点，一般拍卖时间不会超过两个小时，所以这个时间点延后两个小时再来抓取具体拍卖信息
def update_db(data):
    connection = pymysql.connect(host='localhost',
                            user='root',
                            password='mypassword',
                            db='JD',
                            charset='utf8mb4',
                            cursorclass=pymysql.cursors.DictCursor)
    cursor = connection.cursor()
    sql = 'insert into Auction (item_id, stats, time1) values (%s, %s, %s)'
    for item_id in data:
        cursor.execute(sql, (item_id, 'new', data[item_id]))
    connection.commit()
    connection.close()
    print('%d new rows inserted.' % len(data))
    return

# 晚上10点前一直运行
while time.localtime().tm_hour < 22:
    print('Start working at %d: %d.' % (time.localtime().tm_hour, time.localtime().tm_min))
    new_ids = get_new_ids()
    update_db(new_ids)
    print('Finish working at %d: %d, sleep for 20 mins.' % (time.localtime().tm_hour, time.localtime().tm_min))
    # 最短的拍卖持续时间是40分钟，程序每运行一次不会超过10分钟，睡眠20-30分钟的话，加起来也不超过40分钟
    time.sleep(1200)
