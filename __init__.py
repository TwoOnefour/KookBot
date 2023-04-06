import datetime
import time
import requests
import json
import zlib
import websockets
import asyncio
import queue
# import urllib

class KookBot:
    def __init__(self):
        """初始化变量"""
        self.sendmessage = None  # 发送给服务器的消息
        self.client_Id = "gxoVp0ey_oU8skDD"  # 机器人id
        self.client_Secret = "ZFrLRGLbQmLsszwq"  # 机器人id
        self.token = "1/MTY1MTg=/L8iqnm2sB07wZDsajv9R4g=="  # 机器人id
        self.headers = {
            "Authorization": "Bot {}".format(self.token), # 请求头拼接token
            "Content-type": "application/json",
        }
        self.baseUrl = "https://www.kookapp.cn"
        self.sessions = requests.Session()  # 持续化session
        self.sessions.headers.update(self.headers)  # 给sessions上header

        self.api = {
            "stream": "/api/v3/asset/create",
            "gateway": "/api/v3/gateway/index",
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
        self.status = {
            "init":{
                "start":0,
                "max":60,
                "slotTimes":0
            },
            "has_get_gateway":{
                "start":0,
                "max":4,
                "slotTimes": 0
            },
            "has_established_to_gateway":{
                "start":0,
                "max":0,
                "slotTimes": 0
            },
            "has_connected":{
                "start":0,
                "max":0,
                "slotTimes": 0
            },
            "time_out":{
                "start":0,
                "max":4,
                "slotTimes":0
            }
        }
        self.status_map = {
            "init":["has_get_gateway"],
            "has_get_gateway":["init", "has_established_to_gateway"],
            "has_established_to_gateway":["has_get_gateway", "has_connected","init"],
            "has_connected":["time_out", "init"],
            "time_out":["has_get_gateway", "has_connected","init"]
        }


    def getgateway(self):  # compress 	query 	integer 	false # zlib.decompress(compressed_data).decode()
        self.targetUrl = "{}{}".format(self.baseUrl, self.api["gateway"])
        self.json = {}
        # self.sessions.get(self.targetUrl, json=self.json)
        # result = self.postmessage("GET")
        # token = result["data"][]
        # dict.get()
        result = self.postmessage("GET")
        if result != -1:
            try:
                return self.postmessage("GET")["data"]["url"]
            except requests.exceptions.ConnectionError:
                return -1
        else:
            if not self.dealerror(url): # 处理失败函数
                continue

    async def waitmessage(self, websocket):
        # await asyncio.sleep(6)
        self.message = await self.getmessage(websocket)
        # time.sleep(6)
        # self.getmessage(websocket)
        if not self.message:
            print("Connection failed. Retry in 3 seconds")
            time.sleep(3)
            self.flag = True
            return False
        # self.sendmessage["sn"] = self.message["sn"]
        # print(self.message)
        self.flag = True
        return True

    async def getmessage(self, websocket):
        # print(await websocket.recv())
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

    async def connectGateway(self, url):
        try:
            async with websockets.connect('wss://ws.kaiheila.cn/gateway') as websocket:
                await self.getmessage(websocket)
                return websocket
        except Exception as e:
            print(e)

    async def dealerror(self, sleepTime): # 处理失败函数
        sleepTime += pow(2, self.slotTimes - 1)
        if sleepTime <= 60:
            self.slotTimes += 1
        # sleepTime = pow(2, self.slotTimes)
        await asyncio.sleep(pow(2, self.slotTimes - 1))

    async def connection(self):
        while True:
            if self.now_status == "init":
                url = self.getgateway()
                if url == -1:
                    await self.dealerror()  # 处理失败函数  如果self.getgateway()函数返回try执行的错误代码-1，如果sleeptime<60，倒退指数+1，（最大为60），然后继续获取gateway
                    continue
                else:
                    self.slotTimes = 0
                    self.now_status = "has_get_gateway"
                    continue
            elif self.now_status == "has_get_gateway":
            firstlogin = False
            url = self.getgateway()
            if url == -1:
                await self.dealerror() # 处理失败函数  如果self.getgateway()函数返回try执行的错误代码-1，如果sleeptime<60，倒退指数+1，（最大为60），然后继续获取gateway
                continue
            else:
                self.slotTimes = 0

            websocket = await self.connectGateway(url) # 链接gateway
            while True:
                # self.getmessage(websocket)
                if not firstlogin:
                    self.looplist.append(self.loop.create_task(self.countdowntime(6)))
                    self.looplist.append(self.loop.create_task(self.waitmessage(websocket)))
                    response = await asyncio.gather(self.looplist[0], self.looplist[1])
                    if not response[0] and not response[1]:
                        break  # 写重连函数，先留空
                    # self.dealmessage(self.sendmessage)
                    if self.message["d"]["code"] == 0:
                        print("{}   Connection established. Hello, KOOK！".format(str(datetime.datetime.now())[0:-7]))
                        firstlogin = True
                        # 登录以后写一个异步函数专门接受信息
                self.looplist.clear()
                self.flag = False
                self.sendmessage = {
                    "s": 2,
                    "sn": 0
                }
                await asyncio.sleep(30)
                self.dealmessage(self.sendmessage)
                # self.looplist.append(self.loop.create_task(self.countdowntime(25)))
                self.looplist.append(self.loop.create_task(websocket.send(json.dumps(self.sendmessage))))
                self.looplist.append(self.loop.create_task(self.waitmessage(websocket)))
                response = await asyncio.gather(self.looplist[0], self.looplist[1])
                # ping
                # self.dealmessage(self.sendmessage)
                # await websocket.send(json.dumps(self.sendmessage))
                if not response[1]:
                    # print()
                    break


    async def countdowntime(self, time):  # 超时计时器
        nowtime = 0
        while not self.flag:
            # if not self.flag:
            nowtime += 1
            await asyncio.sleep(1)
            if nowtime > time:
                return False
        return True

    def connect(self):
        # loop = asyncio.get_event_loop()
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
