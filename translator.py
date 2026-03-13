import json
from openai import OpenAI
from config import AppConfig


class Translator:

    def __init__(self, config: AppConfig):
        self.config = config
        self.client = OpenAI(api_key=config.openai_api_key)

    def translate_pair(self, text: str):

        prompt = f"""
次の英語を日本語に翻訳してください。

翻訳ルール:

・直訳しない
・内容を省略しすぎない
・自然な日本語に意訳する
・会話として理解しやすくする
・くどい表現は整理する
・短く要約しすぎない

出力は日本語だけ。

English:
{text}
"""

        resp = self.client.responses.create(
            model=self.config.text_model,
            input=prompt,
        )

        japanese = resp.output_text.strip()

        english = text.strip()

        return english, japanese