
import re
import glob
import json

# 変換ルールの一覧
rules = {
    "Introduction": "はじめに",
    "Acknowledgement": "謝辞",
    "The key words \"MUST\", \"MUST NOT\", \"REQUIRED\", \"SHALL\", \"SHALL NOT\", \"SHOULD\", \"SHOULD NOT\", \"RECOMMENDED\", \"MAY\", and \"OPTIONAL\" in this document are to be interpreted as described in RFC 2119 [RFC2119].": "この文書のキーワード \"MUST\", \"MUST NOT\", \"REQUIRED\", \"SHALL\", \"SHALL NOT\", \"SHOULD\", \"SHOULD NOT\", \"RECOMMENDED\", \"MAY\", および \"OPTIONAL\" はRFC 2119 [RFC2119]に記載されているように解釈されます。"
}

def trans_replace():
    for filename in glob.glob('data/*/rfc*-trans.json'):
        # print(filename)

        with open(filename, 'r') as f:
            obj = json.load(f)

        for paragraph in obj['contents']:

            # 変換ルールに基づく置換
            for text_eng, text_ja in rules.items():
                if paragraph['text'] == text_eng:
                    paragraph['ja'] = text_ja

            # セクション番号が「1.1。」となっている部分の修正
            m = re.match(r'^(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)。(.*)$', paragraph['ja'])
            if m:
                paragraph['ja'] = m[1] + '. ' + m[2]

        with open(filename, 'w') as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    trans_replace()
