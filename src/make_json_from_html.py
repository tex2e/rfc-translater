
import sys
import re
import json
import codecs
from datetime import datetime, timedelta, timezone
JST = timezone(timedelta(hours=+9), 'JST')
import textwrap
from bs4 import BeautifulSoup
from pprint import pprint

def make_json_from_html(rfc_number):



input_file = 'html/rfc%d.html' % rfc_number
with open(input_file, 'r', encoding="utf-8", newline="\n") as f:
    html_text = f.read()

data = {
    "title": {"text": "", "ja": ""},
    "number": 0,
    "created_at": str(datetime.now(JST)),
    "updated_by": "",
    "contents": []
}

soup = BeautifulSoup(html_text, "html.parser")
# print(html_text)

# 英語タイトル
data['title']['text'] = soup.find('title').text.replace(" 日本語訳", "")
# 日本語タイトル
data['title']['ja'] = soup.find(class_="title_ja").find("strong").text

# RFC番号
m = re.match(r'RFC ?(\d+)', data['title']['text'])
if m:
  data['number'] = int(m[1])

# 更新者
data['updated_by'] = soup.find(class_="updated_by").text.replace("翻訳編集 : ", "")


for row in soup.find_all(class_='row'):
  row_data = {}
  texts = list(row.find_all(class_='text'))
  if len(texts) <= 0:
    continue
  if len(texts) >= 1:
    tag_name = texts[0].name
    row_data['indent'] = 0
    if tag_name == 'p':
      row_data['indent'] = int(texts[0].attrs.get('class')[-1].replace('indent-', ''))

    row_data['text'] = texts[0].text.strip()

    if texts[0].name == 'pre':
      row_data['raw'] = True
      indent_data = texts[0].text.strip("\n")
      dedent_data = textwrap.dedent(indent_data)
      diff = len(indent_data.split("\n")[0]) - len(dedent_data.split("\n")[0])
      row_data['indent'] = diff
      row_data['text'] = dedent_data.strip()
      row_data['ja'] = ""

    if texts[0].name == 'h5':
      row_data['section_title'] = True

    if len(texts) >= 2:
      # print('ja', texts[1].text)
      row_data['ja']   = texts[1].text.strip()

    data['contents'].append(row_data)
  

  # print(texts[0].name)
  # print(texts[0].attrs)

# pprint(data)



output_file = 'data/%d/rfc%d-trans.json' % (rfc_number // 1000 % 10 * 1000, rfc_number)
with open(output_file, 'w', encoding="utf-8", newline="\n") as f:
   json.dump(data, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
  rfc_number = int(sys.argv[1])
  make_json_from_html(rfc_number)
