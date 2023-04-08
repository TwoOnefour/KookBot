import openai
import os
import time
import json

async def send_to_chatGPT(message):
    openai.api_key = ""
    # openai.api_key = ""

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=message
    )
    # time.sleep(5)
    return completion.choices[0].message["content"]
