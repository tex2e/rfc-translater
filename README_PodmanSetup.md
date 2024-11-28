

### Podman Compose実行前の事前準備

非公開情報の設定

```bash
vi ./scraping-app/.env
vi ./.env
```

フォルダとファイルの権限の設定（jenkinsユーザが書き込めるようにするため）

```bash
mkdir ./jenkins/jenkins_home/
chmod 777 ./jenkins/jenkins_home/
chmod 777 ./data ./data/*
chmod 777 ./html
chmod 666 html/*.html
chmod 666 html/*.json
```

### Podman Composeでの環境構築

```bash
podman compose up -d
```
