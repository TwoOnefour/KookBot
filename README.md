# Description
一个kook机器人，websocket链接服务器，但目前连接部分还没有完善。尽管如此，已经接入chatGPT的api，实现kook里使用gpt聊天（又菜又爱玩）
![图片](https://user-images.githubusercontent.com/77989499/230897501-602a39c6-a3f9-4a31-98e5-b5b3aed1baa3.png)
# setup.sh
```angular2html
# setup.sh
#!/bin/bash
#linux自动部署脚本
source /etc/profile
filepath=$(cd "$(dirname "$0")"; pwd)
if [ -d $filepath+"/kookbot" ]; then
cd /root/Kookbot/
git reset --hard FETCH_HEAD
git pull origin main
else
git clone https://github.com/twoonefour/kookbot.git
sed -i '24c\        self.token = ""  # 机器人id' /root/kookbot/__init__.py
sed -i '25c\        openai.api_key = ""' /root/kookbot/__init__.py
fi
python3 main.py >> log 2>&1
```