
翻訳結果をローカルで閲覧するためのnginxコンテナの構築手順です。
RFCの取得・翻訳・HTML生成はコンテナを使いません（[README_ForDeveloper.md](README_ForDeveloper.md) を参照）。

### Podman Composeでの環境構築

```bash
podman compose up -d
# http://localhost:11080/ にアクセス
```

### サーバ再起動時もコンテナを自動起動させる

一般ユーザで以下を実行する

```bash
systemctl --user enable --now podman-restart
```
