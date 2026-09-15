# 第 4 章: BigQuery から分析データの取得

この章では、第 3 章まで固定値だった分析データを、BigQuery から取得したデータへ置き換えます。
`POST /api/chat` でチャットを作成すると、固定の SQL を BigQuery で実行し、その結果が PostgreSQL に保存される状態へ進みましょう。

- この章でやること
  - Google Cloud コンソールで BigQuery のテーブルと SQL の実行結果を確認する
  - アプリから BigQuery へ接続し、固定の SQL で分析データを取得する
  - 安全に SQL を実行するための制限と単体テストを追加する
  - Swagger UI とブラウザで、取得したデータを確認する
- この章ではやらないこと
  - LLM による SQL、タイトル、要約の生成
  - SQL の実行が失敗したときのエラーハンドリング

章の最後には、BigQuery から取得した分析データを画面に表示し、チャット履歴として再表示できる状態になります。

## 4.1 BigQuery の分析データを確認する

[BigQuery](https://cloud.google.com/bigquery/docs/introduction?hl=ja) は、Google Cloud 上のデータを SQL で分析できるデータウェアハウスです。まずはアプリから接続する前に、Google Cloud コンソールで分析対象と SQL の実行結果を確認します。

### 4.1.1 分析対象のテーブルを確認する

[Google Cloud コンソールの BigQuery](https://console.cloud.google.com/bigquery) を開き、第 0 章で利用した Google アカウントでログインします。画面上部で 第 0 章で作成した自分のプロジェクトを選択してください。

エクスプローラで公開プロジェクト `bigquery-public-data` を検索し、次のテーブルを開きます。クエリの実行と課金には自分のプロジェクトを使い、データの参照には公開プロジェクトを使います。

```text
bigquery-public-data.austin_bikeshare.bikeshare_trips
```

BigQuery では、`プロジェクト ID.データセット ID.テーブル ID` の形式でテーブルを指定します。「スキーマ」タブで、今回利用する列を確認します。

| 列 | 内容 |
|---|---|
| `start_time` | 利用開始日時 (TIMESTAMP) |
| `duration_minutes` | 利用時間 (分、INTEGER) |
| `start_station_name` | 貸出場所の名前 (STRING) |

テーブルの詳細と出典は [利用する公開データ](./data.md) を参照してください。見つからない場合は完全なテーブル名とログイン中のアカウントを確認します。クエリの処理ロケーションは `US` にします。

### 4.1.2 SQL で日ごとの利用回数を集計する

「無題のクエリ」もしくはタブの横にある "＋" ボタンを押し、次の SQL を入力します。

```sql
SELECT
  DATE(start_time) AS `利用日`,
  COUNT(*) AS `利用回数`,
  ROUND(AVG(duration_minutes), 2) AS `平均利用時間_分`
FROM `bigquery-public-data.austin_bikeshare.bikeshare_trips`
WHERE start_time >= TIMESTAMP('2023-01-01')
  AND start_time < TIMESTAMP('2023-01-08')
GROUP BY `利用日`
ORDER BY `利用日`
LIMIT 7;
```

この SQL は、2023 年 1 月 1 日から 1 月 7 日までの利用回数と平均利用時間を、UTC の日付ごとに集計します。1 行を 1 回の利用として `COUNT(*)` で数えます。期間は開始を含み、翌日の 1 月 8 日を含まない条件です。テーブルはパーティション化されていないため、日付条件を付けても処理データ量が必ず減るわけではありません。

クエリエディタに表示される処理データ量を確認してから「実行」を押します。結果に `利用日`、`利用回数`、`平均利用時間_分` の 3 列が表示されれば、分析対象のデータを取得できています。

![BigQuery コンソールで日ごとの利用回数を集計した SQL と実行結果](./assets/04_bigquery/bigquery-daily-trips-result.webp)

## 4.2 アプリから BigQuery へ接続する

ここからは、第 3 章まで作ってきた `hands-on` を変更します。Colima を起動し、ディレクトリへ移動します。

```bash
colima start
cd ~/Projects/fez-2026-summer-intern-public/hands-on
```

### 4.2.1 Google Cloud の認証情報をコンテナへ渡す

第 0 章で実行した `gcloud auth application-default login` は、ライブラリが自動で読み込む認証情報をホストに保存します。これを Application Default Credentials (ADC) と呼びます。ここでは、その認証情報をアプリのコンテナからも読み取れるようにします。

`docker-compose.yml` の `app` サービスにある `volumes` と `environment` を、次のように変更します。

```yaml
    volumes:
      - "./:/app"
      - "/app/.venv"
      - "${HOME}/.config/gcloud:/root/.config/gcloud:ro"
    environment:
      DATABASE_URL: postgresql+psycopg://app:app@db:5432/app
      BIGQUERY_PROJECT_ID: ${BIGQUERY_PROJECT_ID:?自分のプロジェクトIDを.envに設定してください}
      BIGQUERY_LOCATION: ${BIGQUERY_LOCATION:-US}
```

ホストの `~/.config/gcloud` を読み取り専用 (`:ro`) でコンテナへマウントします。読み取り専用にしておけば、コンテナ側の操作でホストの認証情報が書き換わったり壊れたりすることがありません。

また、認証情報そのものはリポジトリへ追加しません。コミットすると、リポジトリを読める人が本人になりすまして Google Cloud のデータへアクセスできるリスクがあります。
`hands-on/.env.example` を作成し、次の内容を記述します。

```dotenv
BIGQUERY_PROJECT_ID=YOUR_PROJECT_ID
BIGQUERY_LOCATION=US
```

`cp .env.example .env` を実行し、`.env` の `YOUR_PROJECT_ID` を第 0 章で作成した自分のプロジェクト ID に置き換えます。`bigquery-public-data` は指定しません。`.env` は Git の管理対象外にし、設定例の `.env.example` だけをコミットします。

Compose が設定を読み込めることを確認し、コンテナを起動します。

```bash
docker compose config
docker compose up
```

設定エラーがなく、`Application startup complete.` と表示されれば起動できています。

コンテナは起動したままにし、VS Code でもう 1 つターミナルを開きます。新しいターミナルで次を実行してください。

```bash
cd ~/Projects/fez-2026-summer-intern-public/hands-on
```

### 4.2.2 BigQuery との接続設定を追加する

Python から BigQuery を利用するため、クライアントライブラリを追加します。

```bash
docker compose exec app uv add google-cloud-bigquery
```

`pyproject.toml` と `uv.lock` が更新され、パッケージがコンテナへインストールされます。

`app/config.py` の `Settings` に、Compose から渡した設定を追加します。

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    bigquery_project_id: str
    bigquery_location: str


settings = Settings()
```

続けて、外部サービスとの通信を置くディレクトリとファイルを作ります。

```bash
mkdir -p app/integrations
touch app/integrations/__init__.py app/integrations/bigquery.py
```

`app/integrations/bigquery.py` に、BigQuery のクライアントを作る処理を記述します。

```python
from datetime import date, datetime, time
from decimal import Decimal
from functools import cache

from google.cloud import bigquery

from app.config import settings
from app.schemas import chat


@cache
def _get_client() -> bigquery.Client:
    return bigquery.Client(
        project=settings.bigquery_project_id,
        location=settings.bigquery_location,
    )
```

`_get_client` は環境変数のプロジェクトとロケーションを使い、ADC で認証します。`@cache` を付けることで、作成したクライアントを再利用します。

### 4.2.3 SQL を安全に実行する

前項で BigQuery のクライアントを作れるようになりましたが、受け取った SQL をそのまま実行すると、誤ってテーブルを変更したり、想定以上のデータを読み取ったりする可能性があります。第 4.1 節では人がクエリエディタの処理データ量を確認してから SQL を実行しましたが、API ではリクエストのたびに同じ確認をコードで行う必要があります。

この項では、実行前の dry run で `SELECT` 以外と、処理データ量が 1 GB を超える SQL を拒否し、本実行にも同じ処理データ量の上限を設定します。これにより、ステートメントの種類と処理データ量を確認した SQL を、上限付きで実行できる状態にします。

この制限は参照先のテーブルを限定しません。第 0 章の前提どおり、機密データへのアクセス権限を持たないアカウントを使用してください。

また、認証や通信などの理由で BigQuery API の呼び出しに失敗する場合があります。アプリのルールによる拒否と外部サービスの失敗では、呼び出し側での扱い方や原因の調べ方が異なるため、別の例外として区別できるようにします。

`app/integrations/bigquery.py` の `@cache` の直前に、処理データ量の上限と例外クラスを追加します。

```python
_BQ_MAX_BYTES = 1_000_000_000  # 1 GB


class BigQueryExecutionError(Exception):
    """BigQuery API の呼び出しに失敗したことを表す例外"""


class QueryNotAllowedError(Exception):
    """許可されないクエリであることを表す例外"""
```

`QueryNotAllowedError` はアプリのルールによる拒否、`BigQueryExecutionError` は BigQuery API との通信や実行の失敗を表します。実際に SDK の例外を `BigQueryExecutionError` へ変換する処理は、次の項で処理全体を組み立てるときに追加します。

`app/integrations/bigquery.py` の末尾に、SQL の確認、本実行、制限を行う処理を追加します。

```python
def _dry_run(client: bigquery.Client, query: str) -> bigquery.QueryJob:
    job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    return client.query(query, job_config=job_config)


def _run_query(client: bigquery.Client, query: str) -> bigquery.QueryJob:
    job_config = bigquery.QueryJobConfig(maximum_bytes_billed=_BQ_MAX_BYTES)
    return client.query(query, job_config=job_config)


def _guard(statement_type: str, total_bytes: int | None) -> None:
    if statement_type != "SELECT":
        raise QueryNotAllowedError(
            f"SELECT 以外は許可されていません (statement_type={statement_type})"
        )
    if total_bytes is not None and total_bytes > _BQ_MAX_BYTES:
        raise QueryNotAllowedError(
            f"スキャン量が上限を超えています ({total_bytes} > {_BQ_MAX_BYTES})"
        )

```

`_dry_run` は SQL を実行せず、SQL のステートメントの種類と処理データ量を確認します。`_guard` は `SELECT` 以外と処理データ量が 1 GB を超える SQL を拒否します。本実行にも `maximum_bytes_billed` を指定し、BigQuery 側にも同じ上限を設定します。

```mermaid
flowchart TD
    SQL["SQL を受け取る"] --> DryRun["dry run でステートメントの種類と処理データ量を確認"]
    DryRun --> Select{"ステートメントは SELECT のみか？"}
    Select -->| No | Reject["QueryNotAllowedError"]
    Select -->| Yes | Bytes{"1 GB 以下か"}
    Bytes -->| No | Reject
    Bytes -->| Yes | Run["上限付きで SQL を実行"]
```

### 4.2.4 取得結果を制限し、JSON で扱える形にする

前項の制限を通過した SQL を実行するときも、BigQuery の結果をそのままアプリへ取り込めるとは限りません。行数が多ければ API のレスポンスや PostgreSQL へ保存するデータが大きくなり、日付や数値の型によっては JSON へ変換できないこともあります。

この項では、BigQuery から取得する行数を最大 1,000 行に制限し、各セルを JSON で扱える型へ変換します。さらに、クライアントの作成から結果の取得までを一つの処理につなぎ、BigQuery API の呼び出しに失敗した場合は前項で定義した例外へ変換します。これにより、呼び出し側は大きさと型が制御された `columns` と `rows` を受け取れるようになります。

`app/integrations/bigquery.py` の `_BQ_MAX_BYTES` の直後に、取得行数の上限を追加します。

```python
_BQ_MAX_BYTES = 1_000_000_000  # 1 GB
_BQ_MAX_ROWS = 1_000
```

`_BQ_MAX_ROWS` は、BigQuery の結果からアプリへ取り込む行数の上限です。第 4.2.3 項で追加した `_BQ_MAX_BYTES` は SQL が読み取るデータ量を制限するもので、取得行数とは役割が異なります。

続けて `app/integrations/bigquery.py` の末尾に、値を変換し、SQL の確認から結果の取得までを行う処理を追加します。

```python
def _convert_to_json_type(value: object) -> chat.Cell:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    return str(value)


def _build_result(
    schema: list[bigquery.SchemaField],
    rows: list[bigquery.Row],
) -> dict:
    columns = [field.name for field in schema]
    rows = [[_convert_to_json_type(value) for value in row.values()] for row in rows]
    return {"columns": columns, "rows": rows}


def get_result(query: str) -> dict:
    try:
        client = _get_client()
        dry_run_job = _dry_run(client, query)
    except Exception as exc:
        raise BigQueryExecutionError(str(exc)) from exc

    _guard(dry_run_job.statement_type, dry_run_job.total_bytes_processed)

    try:
        job = _run_query(client, query)
        result = job.result(max_results=_BQ_MAX_ROWS)
        rows = list(result)
    except Exception as exc:
        raise BigQueryExecutionError(str(exc)) from exc

    return _build_result(result.schema, rows)
```

`get_result` はクライアントを作成して dry run を行い、許可された SQL だけを本実行します。`result` の `max_results` に `_BQ_MAX_ROWS` を指定することで、アプリへ取り込む結果を最大 1,000 行に制限します。

`_guard` は `try` ブロックの外に置きます。これにより、第 4.2.3 項で決めたとおり、アプリのルールに反する SQL は `QueryNotAllowedError`、BigQuery API との通信や実行の失敗は `BigQueryExecutionError` として区別できます。`raise ... from exc` は変換前の例外を原因として残すため、サーバーログから詳しい原因を追跡できます。

`_convert_to_json_type` では、`Decimal` を `float`、日付と時刻を ISO 8601 形式の文字列へ変換し、それ以外は最終手段として `str` へ変換します。`get_result` の戻り値は、第 3 章まで固定値として使っていた `columns` と `rows` と同じ形です。

BigQuery の `BOOL` は、第 1 章で定義した `Cell` にすでに含まれているため、`app/schemas/chat.py` の変更は不要です。

ここまでの変更をコミットします。

```bash
git add .env.example docker-compose.yml pyproject.toml uv.lock app
git commit -m "feat: BigQuery の接続処理を追加"
```

## 4.3 チャットの分析データを BigQuery から取得する

BigQuery との接続処理ができたので、第 3 章で作った固定の表を実際の問い合わせ結果へ置き換えます。タイトル、SQL、要約を作る処理のうち、この章で変更するのは表の取得だけです。

### 4.3.1 固定 SQL で BigQuery から表を取得する

`app/services/analysis.py` を次の内容に置き換えます。

```python
from app.integrations.bigquery import get_result
from app.models import Chat


def _generate_title(prompt: str) -> str:
    return "2023年1月初週の利用状況"


def _generate_sql(prompt: str) -> str:
    return """
    SELECT
      DATE(start_time) AS `利用日`,
      COUNT(*) AS `利用回数`,
      ROUND(AVG(duration_minutes), 2) AS `平均利用時間_分`
    FROM `bigquery-public-data.austin_bikeshare.bikeshare_trips`
    WHERE start_time >= TIMESTAMP('2023-01-01')
      AND start_time < TIMESTAMP('2023-01-08')
    GROUP BY `利用日`
    ORDER BY `利用日`
    LIMIT 7;
    """


def _get_table(sql: str) -> dict:
    return get_result(sql)


def _generate_summary(prompt: str, table: dict) -> str:
    return "この期間は1月6日の利用回数が611回で最も多くなっています。"


def create_chat(prompt: str) -> Chat:
    title = _generate_title(prompt)
    sql = _generate_sql(prompt)
    table = _get_table(sql)
    summary = _generate_summary(prompt, table)

    return Chat(
        title=title,
        prompt=prompt,
        sql=sql,
        result_table=table,
        summary=summary,
    )
```

`_generate_sql` は、第 4.1 節で確認した SQL を固定で返します。`_get_table` は固定の辞書ではなく、`integrations` 層の `get_result` へ SQL を渡します。

この時点では、プロンプトを変えても SQL は変わりません。タイトルと要約も固定値のままなので、後続の章で LLM を使う処理へ置き換えます。

SQL を変更して試す場合も、教材で扱う公開テーブルと 1 GB の上限を守ってください。まずは上記の固定 SQL で章全体を確認します。

### 4.3.2 Swagger UI で取得結果を確認する

ファイルを保存すると FastAPI が再起動します。起動ログにエラーがないことを確認してから、[http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs) を開きます。

`POST /api/chat` の「Try it out」を押し、次のリクエストボディを送信します。

```json
{
  "prompt": "2023年1月1日から7日までの日別の利用回数と平均利用時間を教えて"
}
```

ステータスコードが `201` になり、レスポンスの `result` で次を確認します。

- `columns` に `利用日`、`利用回数`、`平均利用時間_分` が含まれる
- `rows` に BigQuery から取得した日ごとの値が入る
- 日付は文字列、利用回数と平均利用時間は数値になっている

![Swagger UI で BigQuery の集計結果を返した POST API のレスポンス](./assets/04_bigquery/austin-daily-trips-response.webp)

タイトルと要約は表の内容にかかわらず固定値で表示されます。この段階では想定どおりの動作です。

認証エラーが表示された場合は、ホスト側で `gcloud auth application-default login` を実行し、コンテナを起動し直してください。権限エラーの場合は、ログインしている Google アカウントを確認します。

確認できたら、変更をコミットします。

```bash
git add app/services/analysis.py
git commit -m "feat: 分析データを BigQuery から取得"
```

## 4.4 BigQuery 連携を単体テストする

ここまでは、処理の流れを理解するため、実装のたびに手動で動作を確認してきました。しかし、同じ確認を複数人が毎回同じ品質で繰り返すのは難しいため、実際の開発ではコードによるテストも利用します。

このアプリでは、この章以降も確認方法を次のように分けます。

- 手動で確認する
  - 外部サービスへの接続を含む正常系
- 単体テストで確認する
  - 外部接続なしで実行できる処理
  - 手動では再現しにくい異常系

> [!NOTE]
> これは、限られた時間でこのアプリを実装するためのテスト方針であり、すべての開発に当てはまるものではありません。実際の開発では、外部サービスへの接続を含むテストも自動化する場合があります。
>
> また、実装前にテストを書き、そのテストを通すように実装を進める TDD (Test-Driven Development) という手法もあります。AI を用いた開発ではコード変更の量と速さが増えるため、期待する動作をテストで定義し、自動テストをフィードバックとガードレールとして利用する重要性が高まっています。

### 4.4.1 単体テストの方針と実行環境を用意する

BigQuery への接続は、認証、権限、ネットワーク、データの状態に影響されます。そのため、単体テストでは外部接続なしで確認できる処理と、実行してはいけない SQL を止める処理を対象にします。実際の接続は、前の節の Swagger UI で確認します。

pytest を開発用の依存パッケージとして追加します。

```bash
docker compose exec app uv add --dev pytest
```

`pyproject.toml` の末尾に、テストを探す場所を追加します。

```toml
[tool.pytest]
testpaths = ["tests"]
pythonpath = ["."]
```

テスト用のディレクトリとファイルを作ります。

```bash
mkdir -p tests
touch tests/conftest.py tests/test_bigquery.py
```

`app.config` は読み込み時に環境変数を必要とします。外部サービスへ接続しない単体テストでもモジュールを読み込めるように、`tests/conftest.py` にダミー値を設定します。

```python
import os

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
os.environ.setdefault("BIGQUERY_PROJECT_ID", "test-project")
os.environ.setdefault("BIGQUERY_LOCATION", "US")
```

### 4.4.2 値の変換をテストする

`tests/test_bigquery.py` に、BigQuery の値を JSON で扱える形へ変換できることと、`columns` と `rows` を組み立てられることを記述します。

```python
from datetime import date, datetime, time
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from google.cloud.bigquery import Row, SchemaField

from app.integrations import bigquery as bq

disallowed_query_params = pytest.mark.parametrize(
    "statement_type, total_bytes",
    [
        ("SELECT", bq._BQ_MAX_BYTES + 1),
        ("CREATE_TABLE", 1),
        ("DELETE", 1),
    ],
)


def test_convert_to_json_type():
    assert bq._convert_to_json_type(None) is None
    assert type(bq._convert_to_json_type(True)) is bool
    assert type(bq._convert_to_json_type("text")) is str
    assert type(bq._convert_to_json_type(123)) is int
    assert type(bq._convert_to_json_type(123.45)) is float
    assert type(bq._convert_to_json_type(Decimal(100_000))) is float
    assert bq._convert_to_json_type(date(2026, 6, 1)) == "2026-06-01"
    assert (
        bq._convert_to_json_type(datetime(2026, 6, 1, 12, 1, 1))
        == "2026-06-01T12:01:01"
    )
    assert bq._convert_to_json_type(time(12, 1, 1)) == "12:01:01"
    assert type(bq._convert_to_json_type(["a", "b"])) is str
    assert type(bq._convert_to_json_type({"a": 1})) is str

    timestamp = datetime(
        2026,
        6,
        1,
        12,
        1,
        1,
        tzinfo=ZoneInfo(key="Asia/Tokyo"),
    )
    assert bq._convert_to_json_type(timestamp) == "2026-06-01T12:01:01+09:00"


def test_build_result():
    schema = [
        SchemaField("usage_date", "DATE"),
        SchemaField("average_minutes", "NUMERIC"),
    ]
    rows = [
        Row((date(2026, 6, 1), Decimal("36.17")), {"usage_date": 0, "average_minutes": 1}),
        Row((date(2026, 6, 2), Decimal("26.2")), {"usage_date": 0, "average_minutes": 1}),
    ]

    assert bq._build_result(schema, rows) == {
        "columns": ["usage_date", "average_minutes"],
        "rows": [
            ["2026-06-01", 36.17],
            ["2026-06-02", 26.2],
        ],
    }
```

`SchemaField` と `Row` は BigQuery のクライアントライブラリが提供するクラスですが、このテストでは Python の中で作成するため、BigQuery への接続は発生しません。

### 4.4.3 SQL の制限をテストする

`tests/test_bigquery.py` の末尾に、`SELECT` 以外と 1 GB を超える SQL が拒否されることを追加します。

```python
@disallowed_query_params
def test_guard_disallowed_query(statement_type, total_bytes):
    with pytest.raises(bq.QueryNotAllowedError):
        bq._guard(statement_type=statement_type, total_bytes=total_bytes)


def test_not_guard_allowed_query():
    bq._guard(statement_type="SELECT", total_bytes=1)
    bq._guard(statement_type="SELECT", total_bytes=bq._BQ_MAX_BYTES)


@disallowed_query_params
def test_disallowed_query_never_reaches_run_query(
    monkeypatch,
    statement_type,
    total_bytes,
):
    monkeypatch.setattr(bq, "_get_client", lambda: object())
    monkeypatch.setattr(
        bq,
        "_dry_run",
        lambda client, query: SimpleNamespace(
            statement_type=statement_type,
            total_bytes_processed=total_bytes,
        ),
    )

    def _must_not_run(client, query):
        raise AssertionError("許可されていないクエリが実行されました")

    monkeypatch.setattr(bq, "_run_query", _must_not_run)

    with pytest.raises(bq.QueryNotAllowedError):
        bq.get_result("dummy query")
```

外部接続を差し替えたテストでは、BigQuery へ接続する処理を、テストの間だけ偽物へ差し替えています。本物の代わりに決まった値を返す偽物を使う手法をモックと呼びます。第 1 章と第 3 章では固定値を返す実装をモックと呼びましたが、考え方は同じで、ここではテストの中だけ差し替えます。

`monkeypatch` は pytest が用意している仕組みで、テスト関数の引数に書いておくと pytest が渡してくれます。`monkeypatch.setattr` で置き換えた内容はテストが終わると自動で元に戻るため、他のテストへ影響しません。

`_get_client` と `_dry_run` を偽物にすることで、BigQuery へ接続せずに「dry run がこの結果を返したとき」の状況を作れます。`_run_query` は呼ばれたら失敗する関数へ差し替えてあるので、許可しない SQL が本実行まで到達しないことを確認できます。

テストを実行します。

```bash
docker compose exec app uv run pytest
```

`11 passed` と表示されたら、変更をコミットします。

```bash
git add pyproject.toml uv.lock tests
git commit -m "test: BigQuery 連携の単体テストを追加"
```

## 4.5 章全体を確認して変更をコミットする

最後に、更新した依存パッケージを含むイメージを作り直し、最初から起動できることを確認します。Compose の起動ログを表示しているターミナルで `Control + C` を押してから実行してください。

```bash
docker compose rm -fsv
docker compose up --build
```

`Application startup complete.` と表示されたら、次を確認します。

1. `docker compose exec app uv run pytest` ですべてのテストが成功する
2. Swagger UI の `POST /api/chat` から BigQuery の分析データを取得できる
3. [http://127.0.0.1:8001/](http://127.0.0.1:8001/) で作成したチャットの表を表示できる
4. ページを再読み込みしても、保存した表を再表示できる
5. `docker compose ps` で `app` と `db` が起動し、`db` が `healthy` になっている

![ブラウザに表示した BigQuery の日別利用データ](./assets/04_bigquery/austin-daily-trips-app.webp)

確認できたら、Compose の起動ログを表示しているターミナルで `Control + C` を押し、コンテナと Colima を停止します。

```bash
docker compose rm -fsv
docker compose down
colima stop
```

リポジトリのルートで、変更とコミットを確認します。

```bash
cd ~/Projects/fez-2026-summer-intern-public
git status
git log --oneline -3
```

`git status` に `nothing to commit, working tree clean` と表示され、最新の 3 件が次のコミットになっていることを確認します。

```text
test: BigQuery 連携の単体テストを追加
feat: 分析データを BigQuery から取得
feat: BigQuery の接続処理を追加
```

変更がコミットされ、動作確認ができればこの章は完了です。チャットの作成時に BigQuery から分析データを取得し、PostgreSQL へ保存できるようになりました。
