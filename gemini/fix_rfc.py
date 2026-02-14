# -*- coding: utf-8 -*-
import json
import sys
import os

def apply_fix(file_path, english_text, new_japanese_text):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        contents = data.get('contents', [])
        found = False
        for item in contents:
            if item.get('text') == english_text:
                item['ja'] = new_japanese_text
                found = True
                break

        if found:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Successfully updated translation in {file_path}")
        else:
            print(f"Error: English text not found in {file_path}")

    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python fix_rfc.py <file_path> <english_text> <new_japanese_text>")
        sys.exit(1)

    file_path_arg = sys.argv[1]
    english_text_arg = sys.argv[2]
    new_japanese_text_arg = sys.argv[3]

    apply_fix(file_path_arg, english_text_arg, new_japanese_text_arg)
