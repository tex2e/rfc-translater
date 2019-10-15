
# RFC Translater

### 目的
1. RFCの英語を読むのが辛いので、Google翻訳した文を横に並べたものを読みたい。
[RFCの日本語訳リンク集](https://www.nic.ad.jp/ja/tech/rfc-jp-links.html)では原文と日本語訳が別々のページになっていて、日本語訳が正しいのか判断がしにくい
2. RFCの本文は改行されているので、改行を削除した上でGoogle翻訳に貼り付けないと正しく翻訳されない。改行を削除する煩わしさを解決する

### 流れ
1. RFCスクレイピング (https://tools.ietf.org/html/rfcXXXX)
2. セクション毎に分割 & 改行の除去
3. Google翻訳で英語を日本語にする
4. セクション毎に英文、日本語文を並べて表示するページの生成

```
pip install requests lxml
pip install googletrans
pip install hyper
```


```python
python fetch_rfc.py 1
python trans_rfc.py 1
```
