# -*- coding: utf-8 -*-
import json
import sys
import os

def update_title(file_path, new_ja_title):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if 'title' in data:
            data['title']['ja'] = new_ja_title
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Successfully updated title in {file_path}")
        else:
            print(f"Error: 'title' object not found in {file_path}")

    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python fix_rfc_title.py <file_path> <new_japanese_title>")
        sys.exit(1)

    file_path_arg = sys.argv[1]
    new_japanese_title_arg = sys.argv[2]

    update_title(file_path_arg, new_japanese_title_arg)
