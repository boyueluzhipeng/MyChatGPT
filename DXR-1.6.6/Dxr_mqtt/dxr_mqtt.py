# -*- coding: utf-8 -*-
import copy
import inspect
import json
from multiprocessing import RLock
import os
import sys
import threading
import time
from loguru import logger
from tabulate import tabulate

#  时间输出格式为：2020-01-01 00:00:00
logid = logger.add("run.log", 
           rotation="1 days",
           retention="7 days",
           format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} |{message}",
           enqueue=True,
           catch=True,
           level="DEBUG")
logger.remove(0)
logger.add(sys.stdout, 
           format="{time:YYYY-MM-DD HH:mm:ss} | <blue><bold>{level:<8}</bold></blue> | {message}",
           colorize=True,
           enqueue=True,
           catch=True,
           level="DEBUG")

# 添加错误日志输出到error.log
logger.add("error.log", 
        rotation="1 days",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        enqueue=True,
        catch=True,
        level="ERROR")


def set_log_level(level):
    global logid
    logger.remove(logid)
    # 配置终端输出按照level级别过滤后输出
    my_filter = lambda record: record["level"].name == level
    logid = logger.add("run.log", 
           rotation="1 days",
           retention="7 days",
           format="{time:YYYY-MM-DD HH:mm:ss} {level} {message}",
           colorize=False,
           enqueue=True,
           catch=True,
           level="DEBUG",
           filter=my_filter)

import paho.mqtt.client as mqtt

server_url = '127.0.0.1'
server_port = 1883
callback_dit = {}
publish_dit = []
mqttc = None
rc = -1
isPrintLog = False
client_id = str(int(time.time() * 1000))
topic_list_str_pub = ''
topic_list_str_sub = ''
isReconnect = False
mqtt_thread = None
heart_beat_time = 5
sn = None


def setServerUrl(url='127.0.0.1', port=1883, clientID=str(int(time.time() * 1000))):
    global server_url, server_port, client_id
    server_url = url
    server_port = int(port)
    client_id = clientID


def setSn(serialNumber):
    global sn
    sn = serialNumber


def setHeartBeatTime(heart_time=5):
    global heart_beat_time
    heart_beat_time = heart_time


def setMqttLog(PrintLog=False):
    global isPrintLog
    isPrintLog = PrintLog


class Dxr_url_port:
    pass


def get_cond(topic):
    global callback_dit
    if not isinstance(topic, str):
        topic = topic.topic
    if topic not in callback_dit:
        Dxr_Subscriber(topic, None)
    return callback_dit[topic]['cond']


def on_connect(client, userdata, flags, rrc):
    global rc, isReconnect, mqttc
    rc = rrc
    print("Connected with result code " + str(rc))
    if isReconnect:
        isReconnect = False
        # 获取callback_dit中的所有topic,键
        keys = callback_dit.keys()
        # 重新订阅
        for item in keys:
            client.unsubscribe(item)
            client.subscribe(item, 0)


# 一旦订阅到消息，回调此方法
def on_message(client, obj, msg):
    global callback_dit
    topic = msg.topic
    try:
        threading.Thread(target=callback, args=(topic, msg, client), daemon=True).start()
        # callback(topic, msg, client)
    except Exception as ex:
        print(ex)
        keys = callback_dit.keys()
        topic_arr = topic.split("/")[1:]
        for item in keys:
            item_arr = item.split("/")[1:]
            isThisTopic = True
            if len(item_arr) == len(topic_arr):
                for i in range(len(item_arr)):
                    if item_arr[i] == "+":
                        continue
                    if item_arr[i] != topic_arr[i]:
                        isThisTopic = False
                        break
            if isThisTopic:
                threading.Thread(target=callback, args=(item, msg, client), daemon=True).start()
                # callback(item, msg, topic)
                break


def callback(topic, msg, client):
    global callback_dit
    msg = str(msg.payload.decode("utf-8"))
    if type(msg) is str:
        msg = json.loads(msg)
    if topic not in callback_dit:
        isTongPei = False
        keys = callback_dit.keys()
        for item in keys:
            if "+" in item:
                item_arr = item.split("/")[1:]
                topic_arr = topic.split("/")[1:]
                if item_arr[0] == topic_arr[0]:
                    isTongPei = True
                    break
        if not isTongPei:
            callback_dit[topic] = {'func': None, 'cond': threading.Event(), 'msg': None}
    callback_dit[topic]['msg'] = msg
    cond = get_cond(topic)
    cond.set()
    cond.clear()
    if callback_dit[topic]['func'] is not None:
        func = callback_dit[topic]['func']
        if '+' in topic:
            func(msg, client)
        else:
            func(msg, topic)


# 一旦订阅成功，回调此方法
def on_subscribe(mqttc, obj, mid, granted_qos):
    # print("Subscribed: " + str(mid) + " " + str(granted_qos))
    pass


# 一旦有log，回调此方法
def on_log(mqttc, obj, level, string):
    global isPrintLog
    if isPrintLog:
        print(string)


def on_disconnect(client, userdata, rrc):
    global rc, isReconnect, mqttc
    rc = rrc
    isReconnect = True
    print("Disconnected with result code " + str(rc))


def Mqtt():
    global mqttc, server_url, server_port, client_id, mqtt_thread
    if mqttc is None:
        try:
            # 新建mqtt客户端，默认没有clientid，clean_session=True, transport="tcp"
            mqttc = mqtt.Client(client_id=client_id)
            mqttc.will_set('/topic/' + client_id, '', retain=True)
            mqttc.on_message = on_message
            mqttc.on_connect = on_connect
            mqttc.on_subscribe = on_subscribe
            mqttc.on_disconnect = on_disconnect
            mqttc.on_log = on_log
            # 连接broker，心跳时间为60s
            mqttc.connect(server_url, server_port, heart_beat_time)
            # 订阅该主题，QoS=0
            mqtt_thread = threading.Thread(target=mqttc.loop_forever, daemon=True)
            mqtt_thread.start()
            return mqttc
        except Exception as ex:
            print(ex)
            return None
    else:
        return mqttc


def get_mqtt_status():
    global mqttc
    if mqttc is None:
        return False
    else:
        if mqttc.is_connected():
            return True
        else:
            return False


class Dxr_Subscriber:
    def __init__(self, topic, callback):
        global callback_dit, topic_list_str_pub, topic_list_str_sub, mqttc, sn
        if mqttc is None:
            mqttc = Mqtt()
        if isinstance(topic, str):
            self.topic = topic
        else:
            self.topic = topic.topic
        if sn is not None and sn not in self.topic:
            self.topic = f'/{sn}/client{self.topic}'
        mqttc.subscribe(self.topic)
        self.callback = callback
        if self.topic not in callback_dit:
            cond = threading.Event()
            callback_dit[self.topic] = {'func': self.callback, 'cond': cond, 'msg': None}
        else:
            callback_dit[self.topic]['func'] = self.callback
        topic_list_str_sub = client_id + '_sub:\n'
        for item in callback_dit.keys():
            topic_list_str_sub = '' + topic_list_str_sub + item + '\n'
        if mqttc is not None:
            if mqttc.is_connected():
                mqttc.publish('/topic/' + client_id, retain=True, payload=topic_list_str_pub + topic_list_str_sub)


# 定义一个订阅者类的解释器
class dxr_subscriber:
    def __init__(self, msg):
        global sn
        # 如果msg的类型是str,则将msg赋值给self.topic
        if isinstance(msg, str):
            self.topic = msg
        else:
            self.topic = msg.topic
        self.func = None

    def __call__(self, func):
        # 将函数绑定到解释器上
        self.func = func
        Dxr_Subscriber(self.topic, self.func)


class Dxr_Publisher:
    def __init__(self, topic):
        global publish_dit, topic_list_str_pub, topic_list_str_sub, callback_dit, mqttc, sn
        if mqttc is None:
            mqttc = Mqtt()
        if isinstance(topic, str):
            self.topic = topic
            self.data_type = None
        else:
            self.topic = topic.topic
            self.data_type = topic
        if sn is not None and sn not in self.topic:
            self.topic = f'/{sn}/pc{self.topic}'
        if self.topic not in publish_dit:
            publish_dit.append(self.topic)
        topic_list_str_pub = client_id + '_pub:\n'
        for item in publish_dit:
            topic_list_str_pub = '' + topic_list_str_pub + item + '\n'
        if mqttc is not None:
            if mqttc.is_connected():
                mqttc.publish('/topic/' + client_id, retain=True, payload=topic_list_str_pub + topic_list_str_sub)

    def publish(self, msg):
        global mqttc
        if mqttc is None:
            mqttc = Mqtt()
        try:
            if self.data_type:
                if mqttc is not None:
                    if mqttc.is_connected():
                        # print(f'publish:{self.topic}, msg:{msg.get_json()}')
                        mqttc.publish(self.topic, msg.get_json(), qos=0)
            else:
                if mqttc is not None:
                    if mqttc.is_connected():
                        mqttc.publish(self.topic, json.dumps(msg), qos=0)
        except Exception as ex:
            print(f'publish error: {ex}')

    '''
    使用await_publish来实现消息闭环
    await_publish(msg, timeout, topic)
    {
        msg 为发送的消息
        timeout 不指定的时候，为一直等待设定话题的消息，指定后超时时间中未收到消息，会接收到一个None消息
        topic 为指定闭环消息的话题类型，如果不指定，则默认为原话题类型后追加'_response',可以传递字符串类型的话题，也可以传递消息类型
    }
    '''

    def await_publish(self, msg, timeout=None, topic=None):
        global callback_dit, mqttc
        if mqttc is None:
            mqttc = Mqtt()
        if self.data_type:
            if mqttc is not None:
                if mqttc.is_connected():
                    mqttc.publish(self.topic, msg.get_json(), qos=0)
        else:
            if mqttc is not None:
                if mqttc.is_connected():
                    mqttc.publish(self.topic, json.dumps(msg), qos=0)
        await_topic = None
        if topic is None:
            await_topic = self.topic + '_response'
        else:
            if isinstance(topic, str):
                await_topic = topic
            else:
                await_topic = topic.topic
        if await_topic is None:
            return None
        await_topic = await_topic.replace('pc', 'client')
        cond = get_cond(await_topic)
        if cond is None:
            return None
        if timeout is None:
            cond.wait()
        else:
            cond.wait(timeout)
        return callback_dit[await_topic]['msg']

    def stop_awit_publish(self, topic=None):
        global callback_dit, mqttc
        if topic is None:
            await_topic = self.topic + '_response'
        else:
            if isinstance(topic, str):
                await_topic = topic
            else:
                await_topic = topic.topic
        if await_topic is None:
            return None
        await_topic = await_topic.replace('pc', 'client')
        cond = get_cond(await_topic)
        if cond is None:
            return None
        cond.set()
        cond.clear()

class Dxr_UnSubscriber:
    def __init__(self, topic):
        global callback_dit, mqttc
        if mqttc is None:
            mqttc = Mqtt()
        self.topic = topic
        mqttc.unsubscribe(self.topic)
        callback_dit.pop(self.topic)

# 定义一个猴子补丁，用来替换原来的print函数
def monky_print(*args, **kwargs):
    tmp_args = copy.deepcopy(args)
    # 获取所在文件名和行号
    file_name = inspect.stack()[1].filename
    # 只取文件名
    file_name = os.path.basename(file_name)
    line = inspect.stack()[1].lineno
    # 获取当前的线程名
    thread_name = threading.current_thread().name
    # 获取当前线程数量
    thread_count = threading.active_count()
    isException = False
    # 判断*args是否是错误类型
    for arg in args:
        if isinstance(arg, Exception):
            isException = True
            break
    if isException:
        logger.opt(colors=True).exception(f'<yellow>{file_name}:{line}</yellow>(<blue>{thread_name}:{thread_count}</blue>) {tmp_args}')
    else:
        # for arg in args:
        #     logger.info(arg)
        # # # 将args转换为字符串
        # args = [str(arg) for arg in args]
        # # # 将字符串拼接起来
        # args = " ".join(args)
        # 如果**kwargs中有end参数，则使用end参数的值，否则使用默认值\n
        end = kwargs.get("end", " ")
        # 将end格式添加到args中
        final_str = ''
        for arg in tmp_args:
            try:
                if isinstance(arg, (dict, tuple, list)):
                    # 如果不是list，转换为list
                    if not isinstance(arg, list):
                        arg = list(arg.items())
                    final_str = final_str + '\r\n' + tabulate(arg, maxcolwidths=30, tablefmt='grid', showindex=True, headers='keys') + end
                else:
                    final_str = final_str + str(arg) + end
            except:
                final_str = final_str + str(arg) + end
        logger.opt(colors=True).info(f'<yellow>{file_name}:{line}</yellow>(<blue>{thread_name}:{thread_count}</blue>)\r\n{final_str}')
    
        
# print = monky_print
