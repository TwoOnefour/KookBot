import copy
import datetime
import time
import requests
import json
import zlib
import websockets
import asyncio
import queue
import gptapi
import openai
import re
from requests_toolbelt.multipart.encoder import MultipartEncoder

class KookBot:
    def __init__(self):
        """初始化变量"""
        # openai.proxy = {
        #     "http": "http://127.0.0.1:3503",  # 代理
        # }
        self.author_id = None  # 机器人自身聊天id
        self.client_Id = ""  # 机器人id
        self.client_Secret = ""  # 机器人id
        self.token = ""  # 机器人id
        openai.api_key = ""
        self.gpt_user = {}  # gpt当前使用用户
        self.resume_OK = False # 是否resume成功
        self.sn = 0  # sn消息数量
        self.resume = False  # 是否resume
        self.pong = None  # 是否ping成功返回pong
        self.recv_message = False  #  是否连接后第一次启动after_connecting()方法
        self.websocket = None  # websocket对象
        self.send_message = {}  # 发送给服务器的消息
        self.token = "Bot " + self.token
        self.headers = {
            "Authorization": "{}".format(self.token),  # 请求头拼接token
            "Content-type": "application/json",
        }
        self.baseUrl = "https://www.kookapp.cn"
        self.sessions = requests.Session()  # 持续化session
        self.sessions.headers.update(self.headers)  # 给sessions上header
        self.gateway = None  # gateway
        self.api = {
            "stream": "/api/v3/asset/create",
            "gateway": "/api/v3/gateway/index",
            "send_message": "/api/v3/message/create",
            "me": "/api/v3/user/me",
            "asset": "/api/v3/asset/create"
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
        self.help_message = """基本用法：\n@机器人 + {some_message_to_send} 
        \n如果没带任何参数就会返回本消息\nm\t获得一张图片，请在给出该选项后输入对图片的描述\nq\t退出gpt模式\nh\t返回此帮助\nu\t开启上下文模式\ne\t上下文调教模式\neh\t上下文调教模式帮助 """

    def get_my_information(self):
        self.targetUrl = self.baseUrl + self.api["me"]
        self.author_id = self.postmessage("GET")["data"]["id"]

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

    async def connectGateway(self, url):
        try:
            return await websockets.connect(url)
        except Exception as e:
            print(e)

    async def dealerror(self):  # 处理失败函数
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
                    if self.sn == 65535:
                        self.sn = 0
                    self.messageQueue.put(message)
                elif message["s"] == 5:
                    pass                        # 写重连函数，先留空，给嗷呜留着❤
                else:  # s == 6, resume ok
                    self.resume_OK = True                        # 应该不用处理
            except Exception as e:
                print(e)
                await asyncio.sleep(10)   # 等待重连
                self.now_status = "time_out"

    async def deal_message_function(self):  # 处理s==0消息的函数
        while self.message_handler_is_running:
            if self.messageQueue.queue.__len__() == 0:
                await asyncio.sleep(1)
            else:
                message = self.messageQueue.get()

                if message["d"]["type"] == 255 or message["d"]["author_id"] == self.author_id or message["d"]["extra"].get("mention_all"):  # 如果接受到机器人消息或者艾特全员直接跳过
                    continue
                if message["d"]["extra"]["mention"] == ["{}".format(self.author_id)]:
                    if self.gpt_user.get(message["d"]["author_id"]):
                        if self.gpt_user.get(message["d"]["author_id"])[6]:
                            self.json = {
                                "target_id": message["d"]["target_id"],
                                "content": "请不要催，正在等待结果返回",
                                "quote": message["d"]["msg_id"]  # 取最后一条
                            }
                            self.targetUrl = self.baseUrl + self.api["send_message"]
                            while self.now_status != "has_connected":  # 添加等待函数，等待重连
                                await asyncio.sleep(1)
                            self.postmessage("POST")
                            continue
                    # new_message = message["d"]["content"].strip(r"(met)3270025514(met)")
                    # new_message = re.findall(re.compile(r"(.*)\(met\){}\(met\)([\D\w]*)".format(self.author_id), re.M), message["d"]["content"])  # 写上艾特逻辑，并且处理content
                    new_message = message["d"]["content"].replace("(met)", "").replace("{}".format(self.author_id), "")
                    if new_message.strip(" ") != "":  # 如果有消息，直接启动
                        message["d"]["content"] = new_message.strip(" ")
                    else:  # 如果只艾特没消息，直接post消息并continue循环
                        self.json = {
                            "target_id": message["d"]["target_id"],
                            "content": self.help_message,
                            "quote": message["d"]["msg_id"]  # 取最后一条
                        }
                        self.targetUrl = self.baseUrl + self.api["send_message"]
                        while self.now_status != "has_connected":  # 添加等待函数，等待重连
                            await asyncio.sleep(1)
                        self.postmessage("POST")
                        continue
                    # 这里艾特过程初始化启动，改了一下
                    if not self.gpt_user.get(message["d"]["author_id"]):
                        self.gpt_user[message["d"]["author_id"]] = [[], None, [], message["d"]["target_id"], False, [False, []], False, [False, ""]]

                else:
                    continue
                if self.gpt_user.get(message["d"]["author_id"]):
                    if message["d"]["content"].strip(" ") == "q":
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
                    elif message["d"]["content"].strip(" ") == "m":
                        if not self.gpt_user[message["d"]["author_id"]][7][0]:
                            self.json = {
                                "target_id": message["d"]["target_id"],
                                "content": "接下来请你描述一下图片",
                                "quote": message["d"]["msg_id"]
                            }
                            self.targetUrl = self.baseUrl + self.api["send_message"]
                            self.postmessage("POST")
                            self.gpt_user[message["d"]["author_id"]][7][0] = True
                        else:
                            self.gpt_user[message["d"]["author_id"]][0].append(message["d"]["content"].strip(" "))
                        # self.gpt_user[message["d"]["author_id"]][1].cancel()
                        # self.gpt_user.pop(message["d"]["author_id"])

                    elif message["d"]["content"].strip(" ") == "h":
                        self.json = {
                            "target_id": message["d"]["target_id"],
                            "content": self.help_message,
                            "quote": message["d"]["msg_id"]
                        }
                        self.targetUrl = self.baseUrl + self.api["send_message"]
                        self.postmessage("POST")
                        # self.gpt_user.pop(message["d"]["author_id"])
                    elif message["d"]["content"].strip(" ") == "u":
                        if not self.gpt_user[message["d"]["author_id"]][4]:
                            self.json = {
                                "target_id": message["d"]["target_id"],
                                "content": "上下文模式开启",
                                "quote": message["d"]["msg_id"]
                            }
                            self.targetUrl = self.baseUrl + self.api["send_message"]
                            self.postmessage("POST")
                            # self.gpt_user.pop(message["d"]["author_id"])
                            self.gpt_user[message["d"]["author_id"]][4] = True
                        else:
                            self.json = {
                                "target_id": message["d"]["target_id"],
                                "content": "上下文模式关闭",
                                "quote": message["d"]["msg_id"]
                            }
                            self.targetUrl = self.baseUrl + self.api["send_message"]
                            self.postmessage("POST")
                            self.gpt_user[message["d"]["author_id"]][4] = False
                            # self.gpt_user.pop(message["d"]["author_id"])
                    elif message["d"]["content"].strip(" ") == "eh":
                        self.json = {
                            "target_id": message["d"]["target_id"],
                            "content": "此模式使得gpt通过一段长对话输出用户期望的输出，如：\nQ: 无论我说什么，你只需要回答是或者不是。\n"
                                       "A:是。\n"
                                       "Q:1+1=2\n"
                                       "A:是。\n"
                                       "Q:2+2=3\n"
                                       "A:不是。\n"
                                       "Q:2+4=3\n"
                                       "gpt此时通过上下文，则一定返回：”不是。“这个答案。\n"
                                       "你的输入应该为\n"
                                       "Q:some_question.\n"
                                       "A:some_expected_respond.\n"
                                       "同时以类型Q:结尾\n"
                                       "输入纯空格同样视为错误输入，不会记入消息列表，最后，请输入e作为结束标志，会将你的问题和上下文"
                                       "一并发送到gpt获取结果\n"
                                       "在发送以后，调校功能会关闭，恢复到单句对话模式"
                                       "ps:最好一行一个问题，不要分行",
                            "quote": message["d"]["msg_id"]
                        }
                        self.targetUrl = self.baseUrl + self.api["send_message"]
                        self.postmessage("POST")

                    elif self.gpt_user[message["d"]["author_id"]][5][0] and message["d"]["content"].strip(" ") != "e":
                        if message["d"]["content"].strip(" ") == "":
                            continue
                        # re.compile("[QA][:：](.*)\n]")
                        split_message = re.findall(re.compile("[QA][:：](.*)"), message["d"]["content"])  # 正则匹配
                        split_message_type = re.findall(re.compile("([QA])[:：]"), message["d"]["content"])  # 正则匹配每一行的QA类型
                        lines = re.findall(re.compile(r"\n"), message["d"]["content"])  # 匹配一共多少行
                        if split_message:
                            if split_message_type[-1] == "Q":
                                if len(split_message_type) == len(lines) + 1:
                                    for i in range(len(split_message)):
                                        if split_message_type[i].strip(" ") == "Q":  # 如果是question，则拼接json为{"role": "user", "content": some_question}，下面同理
                                            self.gpt_user[message["d"]["author_id"]][5][1].append(
                                                {"role": "user", "content": split_message[i].strip(" ")})
                                        elif split_message_type[i].strip(" ") == "A":
                                            self.gpt_user[message["d"]["author_id"]][5][1].append(
                                                {"role": "assistant", "content": split_message[i].strip(" ")})
                                    # self.gpt_user[message["d"]["author_id"]][2].append(message["d"]["msg_id"])
                                else:
                                    self.json = {
                                        "target_id": message["d"]["target_id"],
                                        "content": "输入错误，请使用Q:和A:开头的形式",
                                        "quote": message["d"]["msg_id"]
                                    }
                                    self.targetUrl = self.baseUrl + self.api["send_message"]
                                    self.postmessage("POST")
                            else:
                                self.json = {
                                    "target_id": message["d"]["target_id"],
                                    "content": "输入错误，请使用Q:类型结尾",
                                    "quote": message["d"]["msg_id"]
                                }
                                self.targetUrl = self.baseUrl + self.api["send_message"]
                                self.postmessage("POST")
                        else:
                            self.json = {
                                "target_id": message["d"]["target_id"],
                                "content": "输入错误",
                                "quote": message["d"]["msg_id"]
                            }
                            self.targetUrl = self.baseUrl + self.api["send_message"]
                            self.postmessage("POST")

                    elif message["d"]["content"].strip(" ") == "e":
                        if not self.gpt_user[message["d"]["author_id"]][5][0]:
                            self.json = {
                                "target_id": message["d"]["target_id"],
                                "content": "上下文调教开启",
                                "quote": message["d"]["msg_id"]
                            }
                            self.targetUrl = self.baseUrl + self.api["send_message"]
                            self.postmessage("POST")
                            self.gpt_user[message["d"]["author_id"]][5][0] = True
                        # self.gpt_user.pop(message["d"]["author_id"])
                        else:
                            self.json = {
                                "target_id": message["d"]["target_id"],
                                "content": "已经成功发送",
                                "quote": message["d"]["msg_id"]
                            }
                            self.targetUrl = self.baseUrl + self.api["send_message"]
                            self.postmessage("POST")
                            self.gpt_user[message["d"]["author_id"]][0] = copy.deepcopy(self.gpt_user[message["d"]["author_id"]][5][1])
                            self.gpt_user[message["d"]["author_id"]][5][1].clear()
                    else:
                        if len(self.gpt_user[message["d"]["author_id"]][0]) > 10:
                            self.json = {
                                "target_id": message["d"]["target_id"],
                                "content": "目前限制为10句话，已经自动退出gpt聊天",
                                "quote": message["d"]["msg_id"]
                            }
                            self.targetUrl = self.baseUrl + self.api["send_message"]
                            self.postmessage("POST")
                            self.gpt_user[message["d"]["author_id"]][1].cancel()
                            self.gpt_user.pop(message["d"]["author_id"])
                            continue
                        # self.gpt_user[message["d"]["author_id"]][2].append(message["d"]["msg_id"])
                        self.gpt_user[message["d"]["author_id"]][0].append({"role": "user", "content": message["d"]["content"]})
                    if not self.gpt_user[message["d"]["author_id"]][1]:
                        # self.gpt_user[message["d"]["author_id"]][0].append(
                            # {"role": "user", "content": message["d"]["content"].strip(" ")})
                        # self.gpt_user[message["d"]["author_id"]][2].append(message["d"]["msg_id"])
                        self.gpt_user[message["d"]["author_id"]][1] = asyncio.get_event_loop().create_task(
                            self.running_gpt(message["d"]["author_id"]))  # 启动\
                    self.gpt_user[message["d"]["author_id"]][2].append(message["d"]["msg_id"])

                # elif "gpt" in message["d"]["content"]:  # 对每一个调用的人创建一个异步函数,传入使用者的姓名
                # else:
                # #     self.gpt_user[message["d"]["author_id"]] = [[], None, [], message["d"]["target_id"], False, [False, []], 0]
                #     self.gpt_user[message["d"]["author_id"]][0].append({"role": "user", "content": message["d"]["content"].strip(" ")})
                #     self.gpt_user[message["d"]["author_id"]][2].append(message["d"]["msg_id"])
                #     self.gpt_user[message["d"]["author_id"]][1] = asyncio.get_event_loop().create_task(self.running_gpt(message["d"]["author_id"]))  # 启动
                    # 创建一个数据结构，格式如下，self.gpt_user[name]
                    # [0]是和gpt的对话消息用于实现上下文，
                    # [1]是该异步函数的对象用于退出,
                    # [2]是消息msg_id的list,用于引用回复当前消息或者上一条消息
                    # [3]是消息频道，用于返回gpt消息时回复该消息所在频道
                    # [4]是是否开启上下文模式
                    # [5]调教模式 结构为[boolean, [json_message]]
                    # [6]是否正在运行
                    # [7]是否生成图片
    async def running_gpt(self, name):
        now = 0
        user_time = 0  # 用于计数用户多久没有发送消息
        while True:
            if now == len(self.gpt_user[name][0]):
                await asyncio.sleep(1)
                user_time += 1
                if user_time >= 120:
                    self.json = {
                        "target_id": self.gpt_user[name][3],
                        "content": "已经2分钟没有输入消息，已自动退出",
                        "quote": self.gpt_user[name][2][-1]
                    }
                    self.targetUrl = self.baseUrl + self.api["send_message"]
                    while self.now_status != "has_connected":
                        await asyncio.sleep(1)
                    self.postmessage("POST")
                    break
            elif self.gpt_user[name][7][0]:  # 图片
                self.gpt_user[name][6] = True
                now = len(self.gpt_user[name][0])
                result = await gptapi.create_image_from_GPT(self.gpt_user[name][0][-1]["content"])
                request_body = MultipartEncoder({
                    "file": ("{}.jpg".format(self.gpt_user[name][0][-1]["content"]), requests.get(result, verify=False).content, 'multipart/form-data')
                })
                headers = {
                    "Authorization": self.token,
                    'Content-Type': request_body.content_type
                }
                result1 = json.loads(requests.post("{}".format(self.baseUrl + self.api["asset"]), headers=headers, data=request_body, verify=False).text)
                self.json = {
                    "target_id": self.gpt_user[name][3],
                    "content": result1["data"]["url"],
                    "quote": self.gpt_user[name][2][-1],
                    "type": 2
                }
                self.targetUrl = self.baseUrl + self.api["send_message"]
                self.postmessage("POST")
                if now == len(self.gpt_user[name][0]):
                    self.gpt_user[name][0].pop(-1)
                    now = len(self.gpt_user[name][0])
                else:
                    self.gpt_user[name][0].pop(now)
                    now = 1 + len(self.gpt_user[name][0])
                self.gpt_user[name][7][0] = False
                self.gpt_user[name][6] = False
            else:
                user_time = 0  # 收到消息重置计数
                now = len(self.gpt_user[name][0]) + 1  # 记录此时的消息数，如果在运行时有消息传进来，那么也会使得下一轮循环的now不等于self.gpt_user[name][0]消息队列中的消息数量
                try:
                    self.gpt_user[name][6] = True  # 判断当前运行状态
                    if not self.gpt_user[name][4]:  # 如果不是上下文
                        if not self.gpt_user[name][5][0]:  # 如果不是调教
                            result = await gptapi.send_to_chatGPT([self.gpt_user[name][0][-1]])  # 如果不是上下文模式或者调教模式，则只发送一条，由于是一条，所以必须要加[]
                            self.json = {
                                "target_id": self.gpt_user[name][3],
                                "content": result,
                                "quote": self.gpt_user[name][2][-1]  # 否则返回最后一条消息
                            }
                        else:  # 如果是调教全发
                            result = await gptapi.send_to_chatGPT(self.gpt_user[name][0])
                            self.json = {
                                "target_id": self.gpt_user[name][3],
                                "content": result,
                                "quote": self.gpt_user[name][2][-2]  # 引用取倒数第二条
                            }
                            self.gpt_user[name][5][0] = False   # 关闭
                    else:
                        result = await gptapi.send_to_chatGPT(self.gpt_user[name][0])
                        self.json = {
                            "target_id": self.gpt_user[name][3],
                            "content": result,
                            "quote": self.gpt_user[name][2][-1]  # 否则返回最后一条消息
                        }
                    self.gpt_user[name][6] = False
                    self.targetUrl = self.baseUrl + self.api["send_message"]
                    while self.now_status != "has_connected":
                        await asyncio.sleep(1)
                    self.postmessage("POST")
                    if now == len(self.gpt_user[name][0]) + 1:  # 如果没有新消息，直接加入结果
                        self.gpt_user[name][0].append({"role": "assistant", "content": result})
                    else:
                        self.gpt_user[name][0].insert(now - 1, {"role": "assistant", "content": result})  # 保证新消息是最后一个,至于为什么是now-1，自己仔细想一下
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
                        await self.websocket.send(json.dumps({
                            "s": 2,
                            "sn": self.sn
                        }))
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
                            self.sn = 0
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
                await self.websocket.send(json.dumps(self.send_message))
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
        if self.token.strip(" ") == "Bot":
            print("请填写机器人token")
            return
        elif openai.api_key.strip(" ") == "":
            print("请填写openai.api_key")
            return
        self.get_my_information()
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
