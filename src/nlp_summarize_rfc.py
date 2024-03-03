# ------------------------------------------------------------------------------
# RFCの要約を生成するプログラム
# ------------------------------------------------------------------------------

import re
import os
import json
import datetime
#from pprint import pprint
import openai  # pip install openai
from dotenv import load_dotenv  # pip install python-dotenv
from lxml import etree
from .rfc_utils import RfcUtils
from .rfc_const import RfcXmlElem, RfcFile

# 環境変数の読み込み
load_dotenv()

# APIキーの設定
openai.api_key = os.environ['CHATGPI_API_KEY']

# ChatGPTのモデル名
MODEL35 = "gpt-3.5-turbo"
MODEL4 = "gpt-4-turbo-preview"


def get_rfc_title(rfc_number: int) -> str:
    # 要約対象RFCのタイトルを表示
    input_file = RfcFile.get_filepath_data_trans_json(rfc_number)
    if os.path.exists(input_file):
        # 翻訳済みRFC (json) の読み込み
        ctx = RfcFile.read_json_file(input_file)
        rfc_title = ctx['title']['text']
        return rfc_title
    else:
        return None

# RFCの要約作成
def summarize_rfc(rfc_number: int, model: str, force: bool = False):

    if not model or len(model) == 0:
        model = MODEL35

    rfc_title = get_rfc_title(rfc_number)
    if not rfc_title:
        print('[!] RFC翻訳が未実施です。先に翻訳作業を完了させてください！')
        return False

    # RFC要約済みかの判定
    output_summary_file = RfcFile.get_filepath_data_summary_json(rfc_number)
    if os.path.exists(output_summary_file):
        print(f"[-] RFCの要約結果がすでに存在します！")
        return True

    # TODO: ChatGPT 3.5 は2021/9までの情報しか持っていないため、RFCの発行年月で切り分けたい
    if rfc_number >= 8650:
        prompt = summarize_rfc_by_abstract(rfc_number, rfc_title, model)
    else:
        prompt = summarize_rfc_by_title(rfc_number, rfc_title, model)

    print(f"[+] prompt: \n{prompt}")
    print(f"")
    if force or yes_no_input("[?] 上記の内容でChatGPTに質問します。よろしいですか？"):
        pass
    else:
        return False

    response = openai.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that translates English to Japanese."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    # GPTからの応答の表示
    text = response.choices[0].message.content
    print(f"[+] " + "-" * 80)
    print(f"[+] output: \n{text}")
    print(f"[+] " + "-" * 80)
    print(f"[ ] ")

    if force or yes_no_input(f"上記の内容はRFC {rfc_number}の内容ですか？"):
        pass
    else:
        return False

    # GPTからの要約結果をJSON化
    dt_now = datetime.datetime.now()
    obj = {
        "number": rfc_number,
        "model": model,
        "created_at": dt_now.isoformat(),
        "summary": []
    }
    splitted_texts = re.split(r'\n\n+', text)
    for splitted_text in splitted_texts:
        obj['summary'].append(splitted_text)

    # RFC要約の出力
    RfcFile.write_json_file(output_summary_file, obj)
    return True

# RFC番号でChatGPTに要約してもらう
def summarize_rfc_by_title(rfc_number: int, rfc_title: str, model: str = MODEL35):
    # GPTへ送信するプロンプト作成
    if model.lower().startswith("gpt-4"):
        return f"{rfc_title} についての要約、目的、利用場面、関連するRFCを3〜5行でまとめてください"
    elif model.lower().startswith("gpt-3"):
        return f"{rfc_title} についての要約と目的を3行でまとめてください"
    else:
        return f"{rfc_title} についての要約と目的を3行でまとめてください"

# RFCの概要(Abstract)でChatGPTに要約してもらう
def summarize_rfc_by_abstract(rfc_number: int, rfc_title: str, model: str = MODEL35):
    page = RfcUtils.fetch_url(RfcFile.get_url_rfc_xml(rfc_number))
    page_content = RfcUtils.remove_namespace_from_xml(page.content)
    tree = etree.XML(page_content)

    rfc_abstract = tree.xpath(f'/{RfcXmlElem.RFC}/{RfcXmlElem.FRONT}/{RfcXmlElem.ABSTRACT}//text()')
    if not rfc_abstract or len(rfc_abstract) == 0:
        return False

    rfc_abstract_text = re.sub(r'\s+', ' ', ' '.join(rfc_abstract).strip())

    prompt = ""
    prompt += f"次の【原文】の英語の文章を日本語で要約してください。翻訳するときに以下の条件を満たしてください。\n"
    prompt += f"・出力形式はですます調です。\n"
    prompt += f"・3行以内で要約してください。\n"
    prompt += f"\n"
    prompt += f"【原文】\n"
    prompt += f"{rfc_abstract_text}"
    return prompt

def yes_no_input(question: str):
    while True:
        choice = input(question + " [y/N]: ").lower()
        if choice in ['y', 'ye', 'yes']:
            return True
        elif choice in ['n', 'no']:
            return False
