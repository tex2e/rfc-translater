
# RFC Translater

### 目的
1. RFCの英語を読むのが辛いので、Google翻訳した文を横に並べたものを読みたい。
[RFCの日本語訳リンク集](https://www.nic.ad.jp/ja/tech/rfc-jp-links.html)では原文と日本語訳が別々のページになっていて、日本語訳が正しいのか判断しにくい問題がある
2. RFCの本文は改行されているので、改行を削除した上でGoogle翻訳に貼り付けないと正しく翻訳されない。改行を削除する煩わしさを解決する

### 流れ
1. RFCのインデックス取得 https://tools.ietf.org/rfc/index (fetch_index)
1. RFCスクレイピング https://tools.ietf.org/html/rfcXXXX (fetch_rfc)
    - WANTS: RFCの有名度 : https://www.google.com/search?q=ietf+rfc1
    - @id="resultStats" => About 13,700 results から抽出して数値の大小を比較する
2. セクション毎に分割 & 改行の除去 (fetch_rfc)
3. Google翻訳で英語を日本語にする (trans_rfc)
4. セクション毎に英文、日本語文を並べて表示するページの生成 (make_html)
5. 有名なRFCやアクセス数の多いページに対しては、翻訳の修正作業などを行う (人手)


### 開発者向け

```
pip3 install selenium
```

```
pip3 install requests lxml
pip3 install beautifulsoup4
pip3 install Mako
pip3 install googletrans
```

```bash
python3 main.py --rfc 123 # RFC 123の翻訳作業を開始してHTMLまで生成する
python3 main.py --rfc 123 --fetch # RFCの取得だけ
python3 main.py --rfc 123 --trans # RFCの翻訳だけ
python3 main.py --rfc 123 --make # HTMLの生成だけ
python3 main.py # 順番に翻訳する
python3 main.py --max 30 # 順番に翻訳し、30個のRFCで終了する
python3 main.py --begin 500 --end 700 # RFC 500〜700 を順番に翻訳する
python3 main.py --trans-mode selenium # 翻訳にseleniumを使用する
python3 main.py --trans-mode googletrans # 翻訳にgoogletransを使用する
```

- fetch_rfc ... data/A000/B00/rfcABCD.json
- trans_rfc ... data/A000/B00/rfcABCD-trans.json
- make_html ... html/rfcABCD.html
