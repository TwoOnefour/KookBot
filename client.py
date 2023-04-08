import asyncio
import websockets
import json

IP_ADDR = "127.0.0.1"
IP_PORT = "8888"


# 握手，通过发送hello，接收"123"来进行双方的握手。
async def clientHands(websocket):
    while True:
        await websocket.send("hello")
        break
        # response_str = await websocket.recv()
        # if "123" in response_str:
        #     print("握手成功")
        #     return True


# 向服务器端发送消息
async def clientSend(websocket):
    while True:
        input_text = input("input text: ")
        if input_text == "exit":
            print(f'"exit", bye!')
            await websocket.close(reason="exit")
            return False
        await websocket.send(input_text)
        recv_text = await websocket.recv()
        print(f"{recv_text}")

# 重连函数
async def client_reconnect(websocket):
    msg = await websocket.recv()
    print(msg)
    json_msg = json.loads(msg)
    if json_msg['s']==5:
        gateway = IP_ADDR+IP_PORT
        sn = 0
        print(json_msg["s"])
        #message_queue = []
        #清空本地消息队列
        #关闭连接
        websocket.close()
    

# 进行websocket连接
async def clientRun():
    ipaddress = IP_ADDR + ":" + IP_PORT
    websocket1 = None
    websocket1 = await websockets.connect("ws://" + ipaddress)
        # websocket1 = websocket
    await clientHands(websocket1)
    await client_reconnect(websocket1)

# main function
if __name__ == '__main__':
    print("======client main begin======")
    asyncio.get_event_loop().run_until_complete(clientRun())
