---
version: 1
title: Austin のシェアサイクル利用実績
description: Austin MetroBike の公開貸出データ
resource: https://data.austintexas.gov/Transportation-and-Mobility/Austin-MetroBike-Trips/tyfh-5r8s
tags: [transportation, bikeshare]
project_id: bigquery-public-data
dataset_id: austin_bikeshare
table_id: bikeshare_trips
---

# Austin のシェアサイクル利用実績

## テーブル

`bigquery-public-data.austin_bikeshare.bikeshare_trips`

このテーブルだけを参照する。他のデータセットや非公開テーブルを使わない

## 粒度と期間

- 1 行は自転車の貸出 1 回
- `trip_id` は貸出の識別子。2026-09-08 の検証では全 2,271,152 行で重複なし
- 確認済みの期間は 2013-12-12〜2024-06-30
- 教材の例題は 2023 年 1 月に固定する
- ロケーションは `US`。パーティション・クラスタリングの設定なし
- 更新される公開テーブルのため、収録期間や件数は変化し得る

## 列

すべて NULL 許容。型は 2026-09-08 の BigQuery メタデータで確認

| 列 | 型 | 意味 |
|---|---|---|
| `trip_id` | STRING | 貸出の識別子 |
| `subscriber_type` | STRING | 会員・利用プランの種類 |
| `bike_id` | STRING | 自転車の識別子 |
| `bike_type` | STRING | 自転車の種類 |
| `start_time` | TIMESTAMP | 貸出開始時刻 |
| `start_station_id` | INTEGER | 貸出場所の識別子 |
| `start_station_name` | STRING | 貸出場所名 |
| `end_station_id` | STRING | 返却場所の識別子 |
| `end_station_name` | STRING | 返却場所名 |
| `duration_minutes` | INTEGER | 利用時間 (分) |

## 集計ルール

- 利用回数は `COUNT(*)` で集計する
- 平均利用時間は `AVG(duration_minutes)`、表示は必要に応じて小数第 2 位まで丸める。利用時間の単位は分
- 日別集計には `DATE(start_time)` を使い、UTC 日付として説明する。現地時間の営業日と同一とは扱わない
- 月別・日別の条件は開始以上・終了未満の半開区間を使う。2023 年 1 月は `start_time >= TIMESTAMP('2023-01-01') AND start_time < TIMESTAMP('2023-02-01')`
- 場所別ランキングは `start_station_name IS NOT NULL` を条件にし、利用回数の降順、同数なら場所名の昇順に並べる
- この表はパーティション化されていない。期間の絞り込みや `LIMIT` がスキャン量を必ず減らすとは説明しない
- `AVG` は NULL を除外する。NULL と 0 を同一視しない
- 貸出場所と返却場所を区別する。ID と名前を取り違えない
- 利用プラン名だけから料金や売上を推定しない
- 元データの公開範囲は全移動を表さない。市の説明では 2 分未満の利用や運営スタッフの再配置・保守移動を除く

## 回答できる質問

- 指定期間の日別・月別の利用回数
- 貸出場所・返却場所別の利用回数ランキング
- 利用プラン・自転車の種類別の利用回数
- 指定期間の平均利用時間

## 回答できない質問

- 売上、料金、利益 (料金の列なし)
- 利用者の氏名・年齢・住所 (利用者情報なし)
- 天気、気温、降水量 (気象データなし)
- 現在の空き自転車数、将来の実績 (リアルタイム情報・未来の実績なし)

## 出典

City of Austin, Texas の [Austin MetroBike Trips](https://data.austintexas.gov/Transportation-and-Mobility/Austin-MetroBike-Trips/tyfh-5r8s) を BigQuery の公開テーブルから利用する。市のデータメタデータのライセンスは Public Domain。原データの条件は [市の利用条件](https://data.austintexas.gov/stories/s/City-of-Austin-Open-Data-Terms-of-Use/ranj-cccq/) を参照する
