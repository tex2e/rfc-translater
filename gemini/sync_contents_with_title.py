# -*- coding: utf-8 -*-
import json
import os
import sys
import re

def sync_contents(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if 'title' not in data or 'contents' not in data:
            return

        title_text = data['title']['text']
        title_ja = data['title']['ja']

        # "RFC 6087 - Guidelines..." から "Guidelines..." を抽出
        match_text = re.match(r'RFC \d+ - (.+)', title_text)
        match_ja = re.match(r'RFC \d+ - (.+)', title_ja)

        updated = False

        targets = []
        # タイトル全文の一致を確認
        targets.append((title_text.strip(), title_ja.strip()))

        # "RFC XXXX - " を除いた部分の一致を確認
        if match_text and match_ja:
            short_text = match_text.group(1).strip()
            short_ja = match_ja.group(1).strip()
            targets.append((short_text, short_ja))

        for item in data['contents']:
            item_text = item.get('text', '').strip()
            for t_text, t_ja in targets:
                if item_text == t_text:
                    if item.get('ja') != t_ja:
                        item['ja'] = t_ja
                        updated = True
                    break

        if updated:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Synced contents in {file_path}")

    except Exception as e:
        print(f"Error processing {file_path}: {e}")

if __name__ == "__main__":
    for arg in sys.argv[1:]:
        if os.path.isfile(arg):
            sync_contents(arg)
        elif os.path.isdir(arg):
            for root, dirs, files in os.walk(arg):
                for file in files:
                    if file.endswith('-trans.json'):
                        sync_contents(os.path.join(root, file))
