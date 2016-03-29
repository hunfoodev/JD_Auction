#
# 京东夺宝岛已结束拍卖详情抓取二：具体信息抓取
#
# 还是用Selenium + PhantomJS处理JS页面
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
import pymysql, time

driver = webdriver.PhantomJS(executable_path='D:/Program Files/phantomjs/bin/phantomjs.exe')

# 从数据库中获取任务列表
def get_item_list():
    connection = pymysql.connect(host='localhost',
                        user='root',
                        password='mypassword',
                        db='JD',
                        charset='utf8mb4',
                        cursorclass=pymysql.cursors.DictCursor)
    cursor = connection.cursor()
    t = time.localtime().tm_hour - 2
    # 选择stats为new并且抓取时间为2小时之前的项，避免重复抓取和保证拍卖已结束
    sql = "select item_id from Auction where stats='new' and time1<%s"
    cursor.execute(sql, t)
    response = cursor.fetchall()
    results = set()
    for di in response:
        results.add(di['item_id'])
    connection.close()
    return results

# 对每个商品ID的具体抓取过程
def get_data(item_id):
    url = 'http://dbditem.jd.com/' + item_id
    driver.get(url)
    # item字典储存抓取的信息
    item = {}
    status = 'wait'
    # 确保JS页面已加载和拍卖已结束
    try:
        # auction2意味着拍卖结束
        driver.find_element_by_xpath('//div[@class="auction2"]')
        status = 'over'
    except NoSuchElementException:
        # 页面访问受阻，JS加载不成功，或者拍卖还未结束等等
        print('item_id %s: Auction is not over yet, try again later.' % item_id)
    if status == 'over':
        # 商品名字
        try:
            item_name = driver.find_element_by_xpath('//div[@class="intro_detail"]/div[@class="name"]').get_attribute('title')
        except:
            item_name = 'Null'
        # 商品状态
        try:
            condition_icon = driver.find_element_by_xpath('//h1/i').get_attribute('class')
            d = {'useIcon ui1': '未使用', 'useIcon ui2': '使用过', 'useIcon ui3': '维修过'}
            item_condition = d[condition_icon]
        except:
            item_condition = 'Null'
        # 商品图片链接
        try:
            pic = driver.find_element_by_xpath('//div[@class="jqzoom"]/img').get_attribute('src')
        except:
            pic = 'Null'
        # 商品原价
        try:
            price = driver.find_element_by_xpath('//div[@class="auction2"]//del').text[1:]
        except:
            price = 'Null'
        # 商品热度：围观数
        try:
            hot = driver.find_element_by_xpath('//div[@id="auction2weiguan"]/span').text
        except:
            hot = 'Null'
        # 商品分类
        try:
            category = driver.find_elements_by_xpath('//div[@class="atc_breadcrumb"]/a')[-1].text
        except:
            category = 'Null'
        # 出价次数
        try:
            bid_count = driver.find_element_by_xpath('//span[@id="bidCount"]/em').text
        except:
            bid_count = 'Null'
        # 获拍者和获拍价格
        try:
            bids_info = driver.find_elements_by_xpath('//div[@class="details_sidebar"]//dd')[0].text.split('\n')
            bidder = bids_info[1]
            bid = bids_info[2][1:]
        except:
            bidder = 'Null'
            bid = 'Null'
        item.update({'item_id': item_id, 'category': category, 'item_name': item_name, 'item_condition': item_condition,
                     'price': price, 'hot': hot, 'bid_count': bid_count, 'bidder': bidder, 'bid': bid, 'pic': pic})
    return item

# 更新数据库的任务表和拍卖详情表
def update_db(data1, data2):
    connection = pymysql.connect(host='localhost',
                            user='root',
                            password='mypassword',
                            db='JD',
                            charset='utf8mb4',
                            cursorclass=pymysql.cursors.DictCursor)
    cursor = connection.cursor()
    # 更新已完成的任务列表，stats状态改成done，加个time2表示任务完成的时间点
    sql_a = "update Auction set stats = 'done', time2 = %s where item_id = %s"
    for item_id in data1:
        cursor.execute(sql_a, (str(time.localtime().tm_hour), item_id))
    connection.commit()
    print('%d rows updated.' % len(data1))
    # 更新拍卖详情表
    sql_i = "insert into items (item_id, category, item_name, item_condition, price, hot, bid_count, bidder, bid, pic) " \
            "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    for item in data2:
        cursor.execute(sql_i, (item['item_id'], item['category'], item['item_name'], item['item_condition'], item['price'],
                               item['hot'], item['bid_count'], item['bidder'], item['bid'], item['pic']))
    connection.commit()
    print('%d new items inserted.' % len(data2))
    connection.close()
    return

# 晚上10点前一直运行
while time.localtime().tm_hour < 22:
    print('Start working at %d: %d.' % (time.localtime().tm_hour, time.localtime().tm_min))
    # 已完成的任务集合
    item_list_done = set()
    # items储存item字典
    items = []
    item_list = get_item_list()
    for item_id in item_list:
        item = get_data(item_id)
        # item不为空，即成功获取了拍卖信息
        if item:
            item_list_done.add(item_id)
            items.append(item)
    update_db(item_list_done, items)
    print('Finish working at %d: %d, sleep for 2 hours.' % (time.localtime().tm_hour, time.localtime().tm_min))
    # 只要有商品ID，即使第二天再抓也是可以的，我设的2小时一抓
    time.sleep(7200)
