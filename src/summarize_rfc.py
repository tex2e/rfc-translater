
import re
import os
import json
import datetime

import openai  # pip install openai
from dotenv import load_dotenv  # pip install python-dotenv

load_dotenv()

# APIキーの設定
openai.api_key = os.environ['CHATGPI_API_KEY']

def summarize_rfc(rfc_number: int):

    # 要約対象RFCのタイトルを表示
    input_dir = 'data/%04d' % (rfc_number // 1000 % 10 * 1000)
    input_file = f'{input_dir}/rfc{rfc_number}-trans.json'
    rfc_title = None
    if os.path.exists(input_file):
        # 翻訳済みRFC (json) の読み込み
        with open(input_file, 'r', encoding="utf-8") as f:
            ctx = json.load(f)
            rfc_title = ctx['title']['text']
    else:
        print('[!] RFC翻訳が未実施です。先に翻訳作業を完了させてください！')
        return False

    # RFC要約済みかの判定
    output_dir = 'data/%04d' % (rfc_number // 1000 % 10 * 1000)
    output_summary_file = f'{output_dir}/rfc{rfc_number}-summary.json'
    if os.path.exists(output_summary_file):
        print(f"[-] RFCの要約結果がすでに存在します！")
        return True

    # GPTへ送信するプロンプト作成
    prompt = f"""{rfc_title} についての要約、利用場面、関連するRFCを3〜5行でまとめてください"""
    print(f"[*] ")
    print(f"[+] prompt: {prompt}")
    print(f"[*] ")
    if yes_no_input("上記の内容でChatGPTに質問します。よろしいですか？"):
        pass
    else:
        return False

    # MODEL = "gpt-3.5-turbo"
    MODEL = "gpt-4-turbo-preview"
    response = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    # GPTからの応答の表示
    text = response.choices[0].message.content
    print(f"[+] " + "-" * 80)
    print(f"[+] output: {text}")
    print(f"[+] " + "-" * 80)
    print(f"[*] ")

    if yes_no_input(f"上記の内容はRFC {rfc_number}の内容ですか？"):
        pass
    else:
        return False

    # GPTからの要約結果をJSON化
    dt_now = datetime.datetime.now()
    obj = {
        "number": rfc_number,
        "model": MODEL,
        "created_at": dt_now.isoformat(),
        "summary": []
    }
    splitted_texts = re.split(r'\n\n+', text)
    for splitted_text in splitted_texts:
        obj['summary'].append(splitted_text)

    # RFC要約の出力
    with open(output_summary_file, 'w', encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

    return True

def yes_no_input(question: str):
    while True:
        choice = input(question + " [y/N]: ").lower()
        if choice in ['y', 'ye', 'yes']:
            return True
        elif choice in ['n', 'no']:
            return False
