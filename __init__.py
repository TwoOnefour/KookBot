import datetime
import time
import requests
import json
import zlib
import websockets
import asyncio
# import urllib

class KookBot:
    def __init__(self):
        self.sendmessage = None
        self.client_Id = "gxoVp0ey_oU8skDD"
        self.client_Secret = "ZFrLRGLbQmLsszwq"
        self.token = "1/MTY1MTg=/L8iqnm2sB07wZDsajv9R4g=="
        self.headers = {
            "Authorization": "Bot {}".format(self.token),
            "Content-type": "application/json",
        }
        self.baseUrl = "https://www.kookapp.cn"
        self.sessions = requests.Session()
        self.sessions.verify = False
        self.sessions.headers.update(self.headers)
        self.api = {
            "stream": "/api/v3/asset/create",
            "gateway": "/api/v3/gateway/index",
        }
        self.targetUrl = None
        self.json = None
        self.message = None
        self.flag = False
        self.loop = asyncio.get_event_loop()
        self.looplist = []

        # self.websocket = websockets.WEb

    def getgateway(self):  # compress 	query 	integer 	false # zlib.decompress(compressed_data).decode()
        self.targetUrl = "{}{}".format(self.baseUrl, self.api["gateway"])
        self.json = {}
        # self.sessions.get(self.targetUrl, json=self.json)
        # result = self.postmessage("GET")
        # token = result["data"][]
        return self.postmessage("GET")["data"]["url"]

    async def waitmessage(self, websocket):
        # await asyncio.sleep(6)
        self.message = await self.getmessage(websocket)
        # time.sleep(6)
        # self.getmessage(websocket)
        if not self.message:
            print("Connection failed. Retry in 3 seconds")
            time.sleep(3)
            return False
        # self.sendmessage["sn"] = self.message["sn"]
        # print(self.message)
        self.flag = True
        return True

    async def getmessage(self, websocket):
        message = json.loads(zlib.decompress(await websocket.recv()).decode())
        self.dealmessage(message)
        return message

    def dealmessage(self, message):
        if message["s"] == 2 or message["s"] == 4:
            print("{}   发出消息：{}".format(str(datetime.datetime.now())[0:-7], message))
            # print("{}收到服务器发来的消息：{}".format(datetime.datetime.now(), message))
        else:
            print("{}   收到服务器发来的消息：{}".format(str(datetime.datetime.now())[0:-7], message))

    async def connection(self):
        while True:
            firstlogin = False
            url = self.getgateway()
            async with websockets.connect(url) as websocket:
                while True:
                    # self.getmessage(websocket)
                    if not firstlogin:
                        self.looplist.append(self.loop.create_task(self.countdowntime(6)))
                        self.looplist.append(self.loop.create_task(self.waitmessage(websocket)))
                        response = await asyncio.gather(self.looplist[0], self.looplist[1])
                        if not response[0] and not response[1]:
                            break # 写重连函数，先留空
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
                    
    async def countdowntime(self, time): # 超时计时器
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
        return json.loads(result.text)
