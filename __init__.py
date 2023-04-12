import datetime
import time
import requests
import json
import zlib
import websockets
import asyncio
import queue
import gptapi
# import urllib

class KookBot:
    def __init__(self):
        """初始化变量"""
        self.gpt_user = {}
        self.resume_OK = False
        self.sn = 0  # sn消息数量
        self.resume = False  # 是否resume
        self.pong = None  # 是否ping成功返回pong
        self.recv_message = False  #  是否连接后第一次启动after_connecting()方法
        self.websocket = None  # websocket对象
        self.send_message = {}  # 发送给服务器的消息
        self.client_Id = ""  # 机器人id
        self.client_Secret = ""  # 机器人id
        self.token = "1/MTY1MTg=/L8iqnm2sB07wZDsajv9R4g=="  # 机器人id
        self.headers = {
            "Authorization": "Bot {}".format(self.token), # 请求头拼接token
            "Content-type": "application/json",
        }
        self.baseUrl = "https://www.kookapp.cn"
        self.sessions = requests.Session()  # 持续化session
        self.sessions.headers.update(self.headers)  # 给sessions上header
        self.gateway = None  # gateway
        self.api = {
            "stream": "/api/v3/asset/create",
            "gateway": "/api/v3/gateway/index",
            "send_message": "/api/v3/message/create"
        }  # api列表
        self.targetUrl = None  # requests的目标url
        self.json = None  # requests的json
        self.message = None  # 服务器发送的消息
        self.flag = False  # 计时器标志位
        self.loop = asyncio.get_event_loop()  # 事件循环
        self.looplist = []  # 事件循环list
        self.messageQueue = queue.Queue()  # 消息队列
        self.slotTimes = 0  # 倒退指数
        # self.websocket = websockets.WEb
        self.now_status = None
        self.hello = False
        self.message_handler = asyncio.get_event_loop()
        self.message_handler_is_running = False

    def getgateway(self):  # compress 	query 	integer 	false # zlib.decompress(compressed_data).decode()
        self.targetUrl = "{}{}".format(self.baseUrl, self.api["gateway"])
        self.json = {}
        try:
            result = self.postmessage("GET")
        except requests.exceptions.ConnectionError:
            return -1
        if result["code"] != 0:
            print(result["message"])
            return -1
        if result != -1:
            return result["data"]["url"]
        return result

    async def waitmessage(self, websocket):
        self.message = await self.getmessage(websocket)
        if not self.message:
            self.message = json.loads(self.message)
        if not self.message.get("s"):
            print("Connection failed. Retry in 3 seconds")
            time.sleep(3)
            self.flag = True
            return False
        self.flag = True
        return True

    async def getmessage(self, websocket):
        result = await websocket.recv()
        if type(result) == str:
            message = json.loads(result)
        else:
            message = json.loads(zlib.decompress(result).decode())
        self.dealmessage(message)
        return message

    def dealmessage(self, message):
        if message["s"] == 2 or message["s"] == 4:
            print("{}   发出消息：{}".format(str(datetime.datetime.now())[0:-7], message))
            # print("{}收到服务器发来的消息：{}".format(datetime.datetime.now(), message))
        else:
            print("{}   收到服务器发来的消息：{}".format(str(datetime.datetime.now())[0:-7], message))

    async def after_connecting(self):
        while self.now_status == "has_connected":
            message = await self.getmessage(self.websocket)
            # self.dealmessage(message)
            # await self.websocket.recv()
            # message = {"s":3}
            if message["s"] == 5:
                pass   # 写重连函数，先留空，给嗷呜留着❤
            if message["s"] != 3:
                if message["s"] == 0:
                    self.messageQueue.put(message)
            else:
                self.pong = True
        self.recv_message = False

    async def connectGateway(self, url):
        try:
            return await websockets.connect(url)
        except Exception as e:
            print(e)

    async def dealerror(self): # 处理失败函数
        sleepTime = pow(2, self.slotTimes)
        # sleepTime = pow(2, self.slotTimes)
        await asyncio.sleep(sleepTime)


    async def receiving_message(self, websocket):
        while self.now_status != "init" and self.recv_message:
            try:
                message = await self.getmessage(websocket)
                if message["s"] == 3:
                    self.pong = True
                    self.flag = True
                elif message["s"] == 1:
                    self.hello = True
                    self.flag = True
                elif message["s"] == 0:
                    if self.sn >= message["sn"]:  # 在接受到已经处理过的消息的时候选择不处理
                        continue
                    self.sn += 1
                    self.messageQueue.put(message)
                elif message["s"] == 5:
                    pass                        # 写重连函数，先留空，给嗷呜留着❤
                else:  # s == 6, resume ok
                    self.resume_OK = True                        # 应该不用处理
            except Exception as e:
                print(e)
                self.now_status = "time_out"

    async def deal_message_function(self):  # 处理s==0消息的函数
        while self.message_handler_is_running:
            if self.messageQueue.queue.__len__() == 0:
                await asyncio.sleep(1)
            else:
                message = self.messageQueue.get()
                if message["d"]["author_id"] == '369581918':
                    continue
                if self.gpt_user.get(message["d"]["author_id"]):
                    if message["d"]["content"].strip("") == "q":
                        self.json = {
                            "target_id": message["d"]["target_id"],
                            "content": "已退出gpt聊天",
                            "quote": message["d"]["msg_id"]
                        }
                        self.targetUrl = self.baseUrl + self.api["send_message"]
                        self.postmessage("POST")
                        self.gpt_user[message["d"]["author_id"]][1].cancel()
                        self.gpt_user.pop(message["d"]["author_id"])
                        continue
                    elif message["d"]["content"].strip("") == "h":
                        self.json = {
                            "target_id": message["d"]["target_id"],
                            "content": "q    退出gpt模式\nh     返回此帮助\nu    开启上下文模式",
                            "quote": message["d"]["msg_id"]
                        }
                        self.targetUrl = self.baseUrl + self.api["send_message"]
                        self.postmessage("POST")
                        self.gpt_user.pop(message["d"]["author_id"])
                    elif message["d"]["content"].strip("") == "u":
                        self.json = {
                            "target_id": message["d"]["target_id"],
                            "content": "上下文模式开启",
                            "quote": message["d"]["msg_id"]
                        }
                        self.targetUrl = self.baseUrl + self.api["send_message"]
                        self.postmessage("POST")
                        self.gpt_user.pop(message["d"]["author_id"])
                        self.gpt_user[message["d"]["author_id"]][4] = True
                    else:
                        if len(self.gpt_user[message["d"]["author_id"]][0]) > 10:
                            self.json = {
                                "target_id": message["d"]["target_id"],
                                "content": "目前最大上下文限制为10句话，已经自动退出gpt聊天",
                                "quote": message["d"]["msg_id"]
                            }
                            self.targetUrl = self.baseUrl + self.api["send_message"]
                            self.postmessage("POST")
                            self.gpt_user[message["d"]["author_id"]][1].cancel()
                            self.gpt_user.pop(message["d"]["author_id"])
                            continue
                        self.gpt_user[message["d"]["author_id"]][2] = message["d"]["msg_id"]
                        self.gpt_user[message["d"]["author_id"]][0].append({"role": "user", "content": message["d"]["content"]})
                elif "gpt" in message["d"]["content"]:  # 对每一个调用的人创建一个异步函数,传入使用者的姓名
                    self.gpt_user[message["d"]["author_id"]] = [[], asyncio.get_event_loop().create_task(self.running_gpt(message["d"]["author_id"])), message["d"]["msg_id"], message["d"]["target_id"], False]
                    # 创建一个数据结构，格式如下，self.gpt_user[name]
                    # [0]是和gpt的对话消息用于实现上下文，
                    # [1]是该异步函数的对象用于退出,
                    # [2]是消息msg_id,
                    # [3]是消息目标，用于返回gpt消息时回复该消息
                    # [4]是是否开启上下文模式

    async def running_gpt(self, name):
        now = 0
        user_time = 0  # 用于计数用户多久没有发送消息
        self.json = {
            "target_id": self.gpt_user[name][3],
            "content": "你好，我是gpt-3，我能为你做些什么（输入h返回说明）",
            "quote": self.gpt_user[name][2]
        }
        self.targetUrl = self.baseUrl + self.api["send_message"]
        while self.now_status != "has_connected":  # 添加等待函数，等待重连
            await asyncio.sleep(1)
        self.postmessage("POST")
        while True:
            if now == len(self.gpt_user[name][0]):
                await asyncio.sleep(1)
                user_time += 1
                if user_time >= 120:
                    self.json = {
                        "target_id": self.gpt_user[name][3],
                        "content": "已经2分钟没有输入消息，已自动退出",
                        "quote": self.gpt_user[name][2]
                    }
                    self.targetUrl = self.baseUrl + self.api["send_message"]
                    while self.now_status != "has_connected":
                        await asyncio.sleep(1)
                    self.postmessage("POST")
                    break
            else:
                user_time = 0  # 收到消息重置计数
                try:
                    result = await gptapi.send_to_chatGPT(self.gpt_user[name][0])
                    self.json = {
                        "target_id": self.gpt_user[name][3],
                        "content": result,
                        "quote": self.gpt_user[name][2]
                    }
                    self.targetUrl = self.baseUrl + self.api["send_message"]
                    while self.now_status != "has_connected":
                        await asyncio.sleep(1)
                    self.postmessage("POST")
                    if self.gpt_user[name][4]:
                        self.gpt_user[name][0].append({"role": "assistant", "content": result})
                    now += 2
                except Exception as e:
                    print(e)
                    break
        self.gpt_user.pop(name)  # 退出时弹出该用户数据

    async def connection(self):
        self.now_status = "init"
        while True:
            if self.now_status == "has_connected":  # 持续的时间最长，为了减少判断写在第一句
                self.send_message = {
                    "s": 2,
                    "sn": self.sn
                }
                self.dealmessage(self.send_message)
                self.pong = False
                try:
                    await self.websocket.send(json.dumps(self.send_message))
                    self.looplist.append(asyncio.get_event_loop().create_task(self.countdowntime(6)))  # 6秒内收到消息
                    response = await asyncio.gather(self.looplist[0])
                    self.looplist.clear()
                    if not self.pong or not response[0]:
                        self.now_status = "time_out"
                        continue
                    await asyncio.sleep(30)  # 30秒计时器
                except Exception as e:
                    self.now_status = "time_out"
                    print(e)
            elif self.now_status == "init":
                self.gateway = self.getgateway()
                if self.gateway == -1:
                    await self.dealerror()   # 处理失败函数  如果self.getgateway()函数返回try执行的错误代码-1，如果sleeptime<60，倒退指数+1，（最大为60），然后继续获取gateway
                    if self.slotTimes < 6:
                        self.slotTimes += 1
                else:
                    self.slotTimes = 0
                    self.now_status = "has_get_gateway"
            elif self.now_status == "has_get_gateway":
                if self.resume:  # 是否从time_out返回
                    try:
                        response = asyncio.gather(asyncio.get_event_loop().create_task(self.countdowntime(6)))
                        await self.websocket.send({
                            "s": 2,
                            "sn": self.sn
                        })
                        self.dealmessage({
                            "s": 2,
                            "sn": self.sn
                        })
                        if not response[0] or not self.resume_OK:
                            self.slotTimes += 1
                            await asyncio.sleep(self.slotTimes * 8)
                            if self.slotTimes == 3:
                                self.resume = False
                                self.now_status = "init"
                                self.slotTimes = 0
                            continue
                    except Exception as e:
                        self.slotTimes += 1
                        print(e)
                        await asyncio.sleep(self.slotTimes * 8)
                        if self.slotTimes == 3:
                            self.resume = False
                            self.now_status = "init"
                            self.slotTimes = 0
                        continue
                    self.resume_OK = True
                    self.now_status = "has_connected"
                self.recv_message = False
                self.websocket = await self.connectGateway(self.gateway)
                if self.websocket:
                    if not self.recv_message:
                        asyncio.get_event_loop().create_task(self.receiving_message(self.websocket))
                        self.recv_message = True
                    self.slotTimes = 0
                    self.now_status = "has_established_to_gateway"
                else:
                    await self.dealerror()
                    self.slotTimes += 1
                    if self.slotTimes >= 2:
                        self.now_status = "init"
                        self.slotTimes = 0
            elif self.now_status == "has_established_to_gateway":
                self.looplist.append(asyncio.get_event_loop().create_task(self.countdowntime(6)))  # 6秒内收到hello
                # result2 = await self.waitmessage(self.websocket)
                response = await asyncio.gather(self.looplist[0])
                if not response[0] or not self.hello:  # 如果超时
                    self.now_status = "has_get_gateway"
                else:
                    self.now_status = "has_connected"
                    if not self.message_handler_is_running:
                        asyncio.get_event_loop().create_task(self.deal_message_function())
                        self.message_handler_is_running = True
                self.looplist.clear()

            else:  # timeout,重试两次ping,分别间隔2-4秒，如果6秒内收到ping，则返回has_connected
                self.send_message = {
                    "s": 2,
                    "sn": self.sn
                }
                self.websocket.send(json.dumps(self.send_message))
                self.pong = False
                if self.pong:
                    self.now_status = "has_connected"
                    self.slotTimes = 0
                    self.pong = False
                else:
                    await self.dealerror()
                    self.slotTimes += 1
                    if self.slotTimes == 2:
                        self.now_status = "has_get_gateway"
                        self.slotTimes = 0
                        self.resume = True

    async def countdowntime(self, time1):  # 超时计时器
        nowtime = 0
        while not self.flag:
            # if not self.flag:
            nowtime += 1
            await asyncio.sleep(1)
            if nowtime > time1:
                return False
        self.flag = False
        return True

    def connect(self):
        # loop = asyncio.get_event_loop()
        if self.token == "":
            print("请填写机器人token")
            return
        self.loop.run_until_complete(self.connection())
        # return websockets.connect(gateway)
        # self.sessions.get("{}{}".format(self.baseUrl, self.api["gateway"]))

    def playmusic(self):
        # self.targetUrl = "{}{}".format(self.baseUrl, self.api["stream"])
        pass

    def postmessage(self, method):
        if method == "POST":
            result = self.sessions.post(self.targetUrl, json=self.json, verify=False)
        else:
            result = self.sessions.get(self.targetUrl, json=self.json, verify=False)

        if result.text[0] == "{":
            return json.loads(result.text)
        else:
            return -1
