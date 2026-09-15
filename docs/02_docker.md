# 第 2 章: Docker の導入

この章では、第 1 章で作ったアプリを Docker コンテナで動かし、Docker Compose を使った開発環境を作ります。
PC に直接インストールした Python やパッケージでアプリを動かす状態から、アプリの実行環境もコードで再現できる状態へ進みましょう。

- この章でやること
  - Dockerfile からアプリのイメージを作る
  - コンテナを起動し、ポートを通じてアプリへアクセスする
  - Docker Compose に開発時の起動設定をまとめる
  - ホストで編集したコードをコンテナへ反映する
  - コンテナ、プロセス、イメージ、ボリュームの状態を確認する

Dockerfile からイメージを作り、そのイメージからコンテナを起動します。
ブラウザは PC のポートを通じて、コンテナ内で動く FastAPI へアクセスします。

> [!IMPORTANT]
> 第 0 章で起動した完成アプリと、この章で作るアプリは別の Docker Compose プロジェクトとして扱います。
> 完成アプリはプロジェクト名 `public-data-analysis-reference`、URL `http://127.0.0.1:8000` を使います。
> この章ではプロジェクト名を `public-data-analysis-hands-on`、URL を `http://127.0.0.1:8001` とし、両方を起動してもコンテナ名やポートが競合しないようにします。

## 2.1 Docker コンテナでアプリを起動する

はじめに Dockerfile を作り、Docker のコマンドだけでアプリを起動します。
この節を終えると、ソースコードからイメージを作り、そのイメージをコンテナとして実行できるようになります。

### 2.1.1 Docker を起動する

第 0 章でインストールした Colima を起動し、この教材で実装している `hands-on` ディレクトリへ移動します。

```bash
colima start
cd ~/Projects/fez-2026-summer-intern-public/hands-on
docker version
```

`docker version` に `Client` と `Server` の両方が表示されれば、Docker へ接続できています。
すでに Colima が起動している場合も、そのまま次へ進んでください。

### 2.1.2 ビルドへ含めないファイルを指定する

`docker build` は、指定したディレクトリのファイル ([ビルドコンテキスト](https://matsuand.github.io/docs.docker.jp.onthefly/develop/develop-images/dockerfile_best-practices/#%E3%83%93%E3%83%AB%E3%83%89%E3%82%B3%E3%83%B3%E3%83%86%E3%82%AD%E3%82%B9%E3%83%88%E3%81%AE%E7%90%86%E8%A7%A3)といいます) を Docker へ渡します。
その際に不要なファイルを渡さないために、`.dockerignore` を作成しファイルを除外します。

`hands-on/.dockerignore` を作成し、次の内容を記述します。

```dockerignore
# --- Python ---
__pycache__/
*.py[cod]
.venv/
venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# --- 環境変数 ---
.env
.env.*

# --- Git / CI ---
.git/
.gitignore
.github/

# --- Docker ---
Dockerfile
.dockerignore
docker-compose*.yml

# --- IDE / OS ---
.vscode/
.zed/
.idea/
.DS_Store
*.swp

# --- ドキュメント ---
README.md
*.md
!app/knowledge/*.md
!app/knowledge/**/*.md
```

`.gitignore` は Git で管理しないファイルを指定するのに対し、`.dockerignore` は Docker のビルドへ渡さないファイルを指定します。
仮想環境やキャッシュ、環境変数を記録したファイルなどを除外することで、不要なファイルがイメージへコピーされることを防ぎます。
後続の章で追加する `app/knowledge` 内の Markdown はアプリの実行に必要になるため、`!` から始まるパターンで除外対象から戻しています。

### 2.1.3 Dockerfile を作る

`hands-on/Dockerfile` を作成し、次の内容を記述します。

```dockerfile
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.27 /uv /uvx /bin/

COPY . /app

WORKDIR /app
RUN uv sync --frozen --no-cache

CMD ["/app/.venv/bin/fastapi", "run", "app/main.py", "--host", "0.0.0.0"]
```

Dockerfile の命令は上から順に実行され、アプリの実行に必要な環境をイメージへ記録します。

| 命令 | 役割 |
|---|---|
| `FROM` | Python 3.13 が入った軽量なイメージを土台にする |
| 1 つ目の `COPY` | 別のイメージから `uv` と `uvx` をコピーする |
| 2 つ目の `COPY` | ビルドコンテキストのファイルを `/app` へコピーする |
| `WORKDIR` | 以降の命令と起動時の作業ディレクトリを `/app` にする |
| `RUN` | `uv.lock` に記録された依存パッケージをイメージへインストールする |
| `CMD` | コンテナを起動したときに FastAPI を実行する |

`RUN` はイメージを作るときに実行され、結果がイメージへ保存されます。
`CMD` はイメージからコンテナを起動するたびに実行されます。

`--host 0.0.0.0` は、コンテナ内のすべてのネットワークインターフェースで通信を受け付ける指定です。
`fastapi run` は既定でこの値を使いますが、コンテナ外から接続する意図を明示するために書いています。

### 2.1.4 Docker イメージを作る

`hands-on` ディレクトリで次のコマンドを実行します。

```bash
docker build -t public-data-analysis-hands-on-app .
```

`-t` ではイメージを識別する名前を指定します。
ここでは完成アプリのイメージと区別できるように、`public-data-analysis-hands-on-app` とします。
末尾の `.` は、現在の `hands-on` ディレクトリをビルドコンテキストとして使う指定です。

ビルドが完了したら、作成されたイメージを確認します。

```bash
docker image ls public-data-analysis-hands-on-app
```

`public-data-analysis-hands-on-app:latest` という `IMAGE` が 1 行表示されれば、イメージを作成できています。

### 2.1.5 コンテナを起動する

作成したイメージからコンテナを起動します。

```bash
docker run --rm \
  --name public-data-analysis-hands-on-manual \
  -p 127.0.0.1:8001:8000 \
  public-data-analysis-hands-on-app
```

各オプションには次の役割があります。

| オプション | 役割 |
|---|---|
| `--rm` | コンテナの終了後に、停止したコンテナを自動で削除する |
| `--name` | 実行中のコンテナへ識別しやすい名前を付ける |
| `-p 127.0.0.1:8001:8000` | PC の 8001 番ポートをコンテナの 8000 番ポートへ転送する |

`Application startup complete.` と表示されたら、Chrome で [http://127.0.0.1:8001/](http://127.0.0.1:8001/) を開きます (8000 ではないことに注意！)。
第 1 章で作った画面が表示され、履歴の選択やプロンプトの送信ができれば、アプリをコンテナから配信できています。

[http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs) も開き、Swagger UI にチャット API が表示されることを確認します。

確認できたら、コンテナを起動しているターミナルで `Control + C` を押します。
`--rm` を指定したため、停止した `public-data-analysis-hands-on-manual` コンテナは自動で削除されます。

`Dockerfile` と `.dockerignore` の変更をコミットします。

```bash
cd ~/Projects/fez-2026-summer-intern-public/hands-on
git add Dockerfile .dockerignore
git commit -m "chore: Docker イメージを作成"
```

## 2.2 Docker Compose で開発環境を起動する

`docker run` では、コンテナを起動するたびに名前やポートなどのオプションを指定しました。
Docker Compose を使うと、それらの起動設定を YAML ファイルへ記録し、同じ設定で繰り返し起動できます。

この章ではアプリのコンテナだけを定義します。
第 3 章では同じ Compose プロジェクトへ PostgreSQL のコンテナを追加し、複数のコンテナをまとめて起動できるようにします。

### 2.2.1 Compose の設定を書く

`hands-on/docker-compose.yml` を作成し、次の内容を記述します。

```yaml
name: public-data-analysis-hands-on
services:
  app:
    image: public-data-analysis-hands-on-app
    build: .
    command:
      [
        "uv",
        "run",
        "--no-sync",
        "fastapi",
        "dev",
        "app/main.py",
        "--host",
        "0.0.0.0",
      ]
    ports: ["127.0.0.1:8001:8000"]
    volumes:
      - "./:/app"
      - "/app/.venv"
```

設定には次の役割があります。

| 設定 | 役割 |
|---|---|
| `name` | Compose プロジェクト名を完成アプリと区別する |
| `services.app` | `app` という名前でアプリのコンテナを定義する |
| `image` | 第 2.1 節と同じイメージ名を使う |
| `build` | 現在のディレクトリにある Dockerfile からイメージを作る |
| `command` | Dockerfile の `CMD` を開発サーバーの起動コマンドで置き換える |
| `ports` | PC の 8001 番ポートをコンテナの 8000 番ポートへつなぐ |
| `volumes` | PC のコードとコンテナ内の仮想環境をそれぞれマウントする |

Dockerfile では本番環境での実行を想定した `fastapi run` を指定しました。
Compose では、ファイルの変更を検知してアプリを自動で再起動する `fastapi dev` に置き換えます。

1 つ目のボリューム `./:/app` は、PC の `hands-on` ディレクトリをコンテナの `/app` へマウントします。
これにより、VS Code で保存したコードがコンテナからもすぐに見えるようになります。

2 つ目のボリューム `/app/.venv` は、イメージ内にインストールした Python の仮想環境をコンテナ側へ保持します。
PC 上の `.venv` で上書きされないため、PC とコンテナの環境を分離できます。
`--no-sync` は、起動のたびに依存パッケージを同期せず、イメージ内の仮想環境をそのまま使う指定です。

### 2.2.2 Compose の設定を確認する

起動する前に、YAML が Compose の設定として読み込めることを確認します。

```bash
cd ~/Projects/fez-2026-summer-intern-public/hands-on
docker compose config
```

エラーがなく、先頭付近に `name: public-data-analysis-hands-on`、`services` の中に `app` が表示されれば、設定を読み込めています。

### 2.2.3 Compose からアプリを起動する

Dockerfile からイメージを作り直し、Compose に定義したコンテナを起動します。

```bash
docker compose up --build
```

Compose は、`name` とサービス名をもとに `public-data-analysis-hands-on-app-1` というコンテナ名を自動的に付けます。
`reference` にある完成アプリでは、`docker-compose.yml` に`name: public-data-analysis-reference` としているため、コンテナ名が異なり互いを独立して操作できます。

`Application startup complete.` と表示されたら、Chrome で [http://127.0.0.1:8001/](http://127.0.0.1:8001/) を開きます。
第 1 章で作った画面が表示されれば、Compose からもアプリを起動できています。

コンテナはこの後も起動したままにします。以降のコマンドは、VS Code でもう 1 つターミナルを開いて実行してください。

### 2.2.4 コードの変更が自動で読み込まれることを確認する

VS Code で `hands-on/app/main.py` を開き、ファイルの末尾に次のコメントを一時的に追加して保存します。

```python
# Docker Compose の自動読み込みを確認
```

コンテナを起動しているターミナルに、変更の検知とアプリの再起動を示すログが表示されることを確認します。
これは、`./:/app` のマウントを通じて PC 上の変更がコンテナへ伝わり、`fastapi dev` が変更を検知した結果です。

確認できたら、追加したコメントを削除して再び保存します。
一時的な確認コードは残さず、`app/main.py` を変更前の状態へ戻してください。

別のターミナルで Compose の設定をコミットします。

```bash
cd ~/Projects/fez-2026-summer-intern-public/hands-on
git add docker-compose.yml
git commit -m "chore: Docker Compose で開発環境を起動"
```

## 2.3 実行中の状態を確認して終了する

Compose でアプリを起動したまま、Docker が管理しているコンテナ、プロセス、イメージ、ボリュームを確認します。
この節のコマンドは、`hands-on` ディレクトリを開いた 2 つ目のターミナルで実行します。

```bash
cd ~/Projects/fez-2026-summer-intern-public/hands-on
```

### 2.3.1 コンテナとプロセスを確認する

Compose プロジェクトで実行中のコンテナを表示します。

```bash
docker compose ps
```

`public-data-analysis-hands-on-app-1` の状態が `Up` になり、`8001->8000` というポートの対応が表示されることを確認します。

続けて、コンテナ内で実行中のプロセスを表示します。

```bash
docker compose top
```

`fastapi dev app/main.py` を含むプロセスが表示されれば、コンテナ内で開発サーバーが動いています。

### 2.3.2 イメージを確認する

Compose がコンテナの作成に使ったイメージを表示します。

```bash
docker image ls public-data-analysis-hands-on-app
```

第 2.1 節で付けた `public-data-analysis-hands-on-app` という名前のイメージが表示されます。
イメージは実行環境のひな形であり、同じイメージから複数のコンテナを作成できます。

### 2.3.3 コンテナの詳細を見る

先ほど確認した実行中のコンテナの詳細を表示します。

```bash
docker inspect public-data-analysis-hands-on-app-1
```

様々な情報が JSON 形式で出力されます。例えば、`Mounts` の項目を確認してみましょう。
`docker-compose.yml` の `volumes` で設定した 2 つの設定が書かれているはずです。

```yaml
volumes:
  - "./:/app"
  - "/app/.venv"
```

```json
"Mounts": [
    {
        "Type": "bind",
        "Source": "/Users/{example-user}/Projects/fez-2026-summer-intern-public/hands-on",
        "Destination": "/app",
        "Mode": "rw",
        "RW": true,
        "Propagation": "rprivate"
    },
    {
        "Type": "volume",
        "Name": "413ae82d4137a5a2cb84a026649ae7bbb956a862dca99780fdbc2b6968485e8a",
        "Source": "/var/lib/docker/volumes/413ae82d4137a5a2cb84a026649ae7bbb956a862dca99780fdbc2b6968485e8a/_data",
        "Destination": "/app/.venv",
        "Driver": "local",
        "Mode": "z",
        "RW": true,
        "Propagation": ""
    }
],
```

`./:/app` は PC 上の既存ディレクトリをマウントするバインドマウントの設定がされており、
`/app/.venv` は匿名ボリュームとして、コンテナから分離して Python の仮想環境を保持していることがわかります。

### 2.3.4 コンテナ内でコマンドを実行する

`docker compose exec` を使うと、実行中のサービスを指定してコンテナ内でコマンドを実行できます。

```bash
docker compose exec app pwd
docker compose exec app uv run python --version
```

1 つ目のコマンドでは作業ディレクトリの `/app`、2 つ目のコマンドでは `Python 3.13` から始まるバージョンが表示されます。
今後、コンテナ内でアプリ用のコマンドを実行するときも、同じように `app` サービスを指定します。

### 2.3.5 コンテナを終了する

アプリの起動ログを表示しているターミナルで `Control + C` を押します。
コンテナは停止しますが、この時点では Compose が作った停止済みコンテナが残っています。

2 つ目のターミナルで停止状態を確認します。

```bash
docker compose ps --all
```

`public-data-analysis-hands-on-app-1` の状態が `Exited` になっていることを確認します。

## 2.4 全体を確認して変更をコミットする

最後に Compose からアプリをもう一度起動し、同じ開発環境を繰り返し作れることを確認します。

```bash
cd ~/Projects/fez-2026-summer-intern-public/hands-on
docker compose up --build
```

`Application startup complete.` と表示されたら、Chrome で次の内容を確認します。

1. [http://127.0.0.1:8001/](http://127.0.0.1:8001/) に第 1 章で作った画面が表示される
2. サイドバーの履歴を選ぶと URL と結果が切り替わる
3. 「＋ 新規作成」からプロンプトを送信すると、固定の結果が表示される
4. [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs) にチャット API が表示される

確認できたら、起動しているターミナルで `Control + C` を押してコンテナを停止させます。

また、この後作業を続けない場合は Colima も停止しておきます。

```bash
colima stop
```

リポジトリのルートで、変更したファイルとコミットを確認します。

```bash
cd ~/Projects/fez-2026-summer-intern-public
git status
git log --oneline -2
```

`git status` に `nothing to commit, working tree clean` と表示され、この章で作成した次の 2 件のコミットが、新しい順に表示されることを確認します。

```text
chore: Docker Compose で開発環境を起動
chore: Docker イメージを作成
```

変更がコミットされ、動作確認ができればこの章は完了です。
