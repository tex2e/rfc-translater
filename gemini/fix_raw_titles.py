# -*- coding: utf-8 -*-
import json
import os
import sys
import re

def fix_raw_titles(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if 'title' not in data or 'contents' not in data:
            return

        title_text = data['title']['text']
        
        # "RFC 2596 - Use of Language Codes in LDAP" から "Use of Language Codes in LDAP" を抽出
        match_text = re.match(r'RFC \d+ - (.+)', title_text)
        
        targets = [title_text.strip()]
        if match_text:
            targets.append(match_text.group(1).strip())

        updated = False
        for item in data['contents']:
            item_text = item.get('text', '').strip()
            if item_text in targets:
                if item.get('raw') is True:
                    del item['raw']
                    updated = True
                    # タイトルなので ja がない場合は付与を検討するが、
                    # 今回の依頼は "raw": true の削除が主目的
                    if 'ja' not in item and 'ja' in data['title']:
                        # title['ja'] から "RFC XXXX - " を除いた部分を推測
                        match_ja = re.match(r'RFC \d+ - (.+)', data['title']['ja'])
                        if match_ja:
                            item['ja'] = match_ja.group(1).strip()
                        else:
                            item['ja'] = data['title']['ja']

        if updated:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Fixed raw title in {file_path}")

    except Exception as e:
        print(f"Error processing {file_path}: {e}")

if __name__ == "__main__":
    for arg in sys.argv[1:]:
        if os.path.isfile(arg):
            fix_raw_titles(arg)
        elif os.path.isdir(arg):
            for root, dirs, files in os.walk(arg):
                for file in files:
                    if file.endswith('-trans.json'):
                        fix_raw_titles(os.path.join(root, file))
