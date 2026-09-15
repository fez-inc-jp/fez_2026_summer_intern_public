# 分析に使う公開データ

## 概要

米国テキサス州 Austin のシェアサイクル利用実績。1 行が自転車の貸出 1 回を表し、利用回数や平均利用時間を集計できる

- テーブル: `bigquery-public-data.austin_bikeshare.bikeshare_trips`
- ロケーション: `US`
- 教材で使用する期間: 2023 年 1 月

## 出典

City of Austin の [Austin MetroBike Trips](https://data.austintexas.gov/Transportation-and-Mobility/Austin-MetroBike-Trips/tyfh-5r8s)

上記を BigQuery の公開テーブルを通して用いる

## スキーマ

| 列 | 型 | 内容 |
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
| `duration_minutes` | INTEGER | 利用時間（分） |

## 注意点

- データの収録期間は 2013 年 12 月 12 日〜2024 年 6 月 30 日。教材では、このうち 2023 年 1 月を使用する
- 日別集計は UTC 日付を使う。Austin の現地日付とは異なる
- 利用回数は貸出の回数であり、利用者の人数ではない。料金・売上の情報は含まれない
- 2 分未満の利用や運営スタッフの再配置・保守移動は、提供元の集計対象外
- データの更新により件数や結果が変わる場合がある。市の配布データと BigQuery では収録時期や列名も異なる
- パーティション設定がないため、期間条件や `LIMIT` だけで処理データ量が減るとは限らない
