import requests
from __init__ import KookBot
import json


class Game(KookBot):
    def __init__(self):
        super(Game, self).__init__()

    def get_game(self, type: str):
        result = self.sessions.get(self.baseUrl + self.api["game_list"], json={
            "type": type
        })
        return json.loads(result.text)["data"]

    def create_game(self, name, **kwargs):
        result = self.sessions.post(self.baseUrl + self.api["game_create"], json={
            "name": name,
            "icon": kwargs.get("icon")
        })
        return json.loads(result.text)["message"]

    def update_game(self, id, **kwargs):
        result = self.sessions.post(self.baseUrl + self.api["game_update"], json={
            "id": id,
            "name": kwargs["name"],
            "icon": kwargs.get("icon")
        })
        return json.loads(result.text)["message"]

    def delete_game(self, id):
        result = self.sessions.post(self.baseUrl + self.api["game_delete"], json={
            "id": id,
        })
        return json.loads(result.text)["message"]

    def set_activity(self, id, data_type, **kwargs):
        result = self.sessions.post(self.baseUrl + self.api["game_activity"], json={
            "id": id,
            "data_type": data_type,
            "software": kwargs.get("software"),
            "singer": kwargs.get("singer"),         # if data_type == 2必须传
            "music_name": kwargs.get("music_name")  # if data_type == 2必须传
        })
        return json.loads(result.text)["message"]

    def delete_activity(self, data_type):
        result = self.sessions.post(self.baseUrl + self.api["game_delete_activity"], json={
            "data_type": data_type,
        })
        return json.loads(result.text)["message"]

    def run(self):
        # print(self.get_game("0"))
        # self.create_game("星穹轨道")  # 创建游戏（游戏名， 图标链接），好像没什么用
        # self.get_game("2")  # 获得游戏列表 好像也没什么用，因为只会返回一点点信息
        # self.update_game(53, name="崩坏：星穹轨道")  # 不知道干嘛的
        self.set_activity(928543, 1)


if __name__ == "__main__":
    Game().run()
