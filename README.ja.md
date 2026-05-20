# solo-surveillance

<p>
  <img alt="License" src="https://img.shields.io/github/license/tiancheng91/solo-surveillance?style=flat-square">
  <img alt="Python" src="https://img.shields.io/badge/python-%3E%3D3.11-blue?style=flat-square">
  <img alt="Platform" src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey?style=flat-square">
  <img alt="Last Commit" src="https://img.shields.io/github/last-commit/tiancheng91/solo-surveillance?style=flat-square">
  <a href="https://zread.ai/tiancheng91/solo-surveillance"><img alt="zread" src="https://img.shields.io/badge/Ask_Zread-_.svg?style=flat&color=00b0aa&labelColor=000000&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQuOTYxNTYgMS42MDAxSDIuMjQxNTZDMS44ODgxIDEuNjAwMSAxLjYwMTU2IDEuODg2NjQgMS42MDE1NiAyLjI0MDFWNC45NjAxQzEuNjAxNTYgNS4zMTM1NiAxLjg4ODEgNS42MDAxIDIuMjQxNTYgNS42MDAxSDQuOTYxNTZDNS4zMTUwMiA1LjYwMDEgNS42MDE1NiA1LjMxMzU2IDUuNjAxNTYgNC45NjAxVjIuMjQwMUM1LjYwMTU2IDEuODg2NjQgNS4zMTUwMiAxLjYwMDEgNC45NjE1NiAxLjYwMDFaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00Ljk2MTU2IDEwLjM5OTlIMi4yNDE1NkMxLjg4ODEgMTAuMzk5OSAxLjYwMTU2IDEwLjY4NjQgMS42MDE1NiAxMS4wMzk5VjEzLjc1OTlDMS42MDE1NiAxNC4xMTM0IDEuODg4MSAxNC4zOTk5IDIuMjQxNTYgMTQuMzk5OUg0Ljk2MTU2QzUuMzE1MDIgMTQuMzk5OSA1LjYwMTU2IDE0LjExMzQgNS42MDE1NiAxMy43NTk5VjExLjAzOTlDNS42MDE1NiAxMC42ODY0IDUuMzE1MDIgMTAuMzk5OSA0Ljk2MTU2IDEwLjM5OTlaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik0xMy43NTg0IDEuNjAwMUgxMS4wMzg0QzEwLjY4NSAxLjYwMDEgMTAuMzk4NCAxLjg4NjY0IDEwLjM5ODQgMi4yNDAxVjQuOTYwMUMxMC4zOTg0IDUuMzEzNTYgMTAuNjg1IDUuNjAwMSAxMS4wMzg0IDUuNjAwMUgxMy43NTg0QzE0LjExMTkgNS42MDAxIDE0LjM5ODQgNS4zMTM1NiAxNC4zOTg0IDQuOTYwMVYyLjI0MDFDMTQuMzk4NCAxLjg4NjY0IDE0LjExMTkgMS42MDAxIDEzLjc1ODQgMS42MDAxWiIgZmlsbD0iI2ZmZiIvPgo8cGF0aCBkPSJNNCAxMkwxMiA0TDQgMTJaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00IDEyTDEyIDQiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K&logoColor=ffffff"></a>
</p>

> [🇨🇳 中文](README.md) &nbsp; [🇺🇸 English](README.en.md)

セルフホスト型・軽量・完全ローカルの AI 監視 NVR システム。  
RTSP または ONVIF で IP カメラに接続し、モーション検出で AI 推論をトリガー、イベントを記録します — すべてローカル環境で動作し、クラウド依存は一切ありません。

![Web UI スクリーンショット](docs/webui.png)

## 仕組み

solo-surveillance はカメラを常時監視し、記録すべきイベントが発生したかを自動的に判断します。コアとなるのは**3ステージパイプライン**です：

1. **ストリーム取り込み** — RTSP/ONVIF で各カメラに接続、フレームをデコード
2. **モーションゲーティング** — フレーム差分検出で静止画をフィルタリング、実際に動きのあるフレームのみが AI へ
3. **AI 検出** — YOLOv8 人体検出や LLM シーン理解をモーショントリガーで実行

MotionGate がパフォーマンスの基盤です。AI 推論の前に静止フレームをフィルタリングすることで、実際の運用では AI 呼び出しを **90% 以上**削減します。

各カメラは独立した `threading.Thread` で動作し、完全に独立した `RTSPReader`、`MotionGate`、`AIPipeline` インスタンスを持ちます — カメラワーカースレッド間で可変状態は共有されません。

## 機能一覧

| 機能 | 説明 | 設定キー |
|---|---|---|
| マルチカメラ | カメラごとに独立スレッド、独立した設定と実行 | `cameras[]` |
| デュアルプロトコル | `rtsp://` 直接接続または `onvif://` 自動検出 | `stream_url` |
| モーションゲーティング | フレーム差分検出、静止フレームを事前フィルタリング | `motion.*` |
| YOLOv8 人体検出 | YOLO 内蔵、初回実行時にモデルを自動ダウンロード | `detectors.person` |
| LLM ビジョンシーン | Anthropic/OpenAI API による高度なシーン理解 | `detectors.llm_vision` |
| 領域クロッピング | 正規化 ROI 内のみ検出、フル解像度録画を保持 | `region` |
| AI バッチ推論 | マルチフレームサンプリング、最大信頼度でマージ | `ai.frames` |
| イベント録画 | イベントタイプごとにスナップショット (JPEG) とクリップ (MP4) | `recordings.*` |
| タイムライン索引 | CSV ベースのイベントタイムライン（開始時刻、終了時刻、ファイルパス） | 自動管理 |
| Web UI | 内蔵 HTTP サーバー、タイムラインナビゲーション、フィルタリング、再生 | `--http` フラグ |
| Home Assistant | 重要な検出時に REST API イベントをプッシュ | `hass.*` |
| Hook スクリプト | イベント発生時に外部コマンドを実行 | `hooks.*` |
| 自動再接続 | RTSP 切断からの自動復旧、24時間365日運用に対応 | `RTSPReader` 内蔵 |
| 完全ローカル | すべての推論、録画、再生をデバイス上で実行 | — |

## クイックスタート

### 1. インストール

```bash
# 方法 A（推奨）— 自動で仮想環境を分離、手動設定不要
uvx solo-surveillance

# 方法 B — グローバルインストール
pip install solo-surveillance
```

### 2. カメラの設定

```bash
curl -O https://raw.githubusercontent.com/tiancheng91/solo-surveillance/main/config.example.yaml
mv config.example.yaml config.yaml
```

`config.yaml` を編集してカメラ情報を入力：

```yaml
cameras:
  - id: door
    enabled: true
    stream_url: "rtsp://user:password@192.168.1.100:554/stream1"
```

ONVIF 自動検出にも対応：

```yaml
  - id: front_door
    stream_url: "onvif://admin:password@192.168.1.100:80?profile=0"
```

> 完全な設定は `config.example.yaml` を参照（LLM ビジョン、HA 統合、Hook スクリプト等の全オプションを含む）。

### 3. 起動

```bash
solo-surveillance
```

初回起動時に YOLOv8 モデルが自動ダウンロードされます。以下のログが表示されれば正常動作しています：

```
INFO  [cam-door] スレッド開始: door
INFO  [cam-door] RTSP 接続完了
```

### 4. Web UI を開く（オプション）

```bash
solo-surveillance --http 0.0.0.0:8080
```

ブラウザで `http://<デバイスIP>:8080` を開く：

- カメラ・日付・時間帯でイベントをフィルタリング
- サムネイルは遅延読み込み、クリックで拡大表示
- MP4 ビデオクリップの再生に対応
- 右側タイムライン：黄色い部分がイベント発生時間、ドラッグでナビゲーション
- 並び替え：デフォルトは新しい順、クリックで反転

> Web UI はローカルネットワーク再生専用です。動画がクラウドにアップロードされることはありません。

## コマンドラインリファレンス

```bash
solo-surveillance            # 起動（カレントディレクトリの config.yaml を読む）
solo-surveillance -v         # デバッグモード—モーション検出、AI クールダウン等の詳細ログ
solo-surveillance -c /path/to/config.yaml  # カスタム設定パス
solo-surveillance --http :8080     # Web UI 起動（デフォルトポート 8080）
solo-surveillance --http 0.0.0.0:9090  # カスタムアドレス・ポート指定
```

---

## Home Assistant 連携

検出されたイベントを Home Assistant のイベントバスにリアルタイムプッシュし、自動化（照明・アラーム・通知など）に利用できます。Python 標準ライブラリのみ使用、追加依存関係ゼロ。

```yaml
hass:
  enabled: true
  url: "http://homeassistant:8123"
  token: "${HASS_TOKEN}"
```

設定後、各イベント（`camera.motion`、`camera.person`、`camera.feeding` 等）は自動的に HA の `/api/events/{event_type}` に POST されます。

> 詳細な設定は [docs/homeassistant.md](docs/homeassistant.md) を参照。

---

*以下のセクションは上級者向けの詳細設定とシステム設計について説明します。*

---

## 設定

YAML 形式。`defaults` ブロックでグローバルデフォルト値を設定し、`cameras` リストの各カメラで個別に上書きできます。設定値は `${ENV_VAR}` 環境変数置換に対応。

基本構造：

```yaml
defaults:
  motion:         # モーション検出パラメータ
  ai:             # AI 推論パラメータ（フレーム数、クールダウン）
  recordings:     # スナップショット/ビデオクリップ保存
  detectors:      # YOLO / LLM 検出器
  region:         # 検出領域（オプション）

cameras:          # カメラリスト、各カメラで defaults を上書き可

hass:             # オプション：Home Assistant 連携
hooks:            # オプション：外部スクリプト
llm:              # オプション：LLM API 接続設定
```

> 全オプションと詳細コメントは `config.example.yaml` を参照。
> 詳細な設定ガイドとベストプラクティスは [docs/configuration.md](docs/configuration.md) を参照。
> すぐ使えるシナリオ設定例は [docs/scenarios.md](docs/scenarios.md) を参照。

> **ONVIF URL 形式**: `onvif://username:password@host:port?profile=N`
> - `profile`: メディアプロファイルインデックス、デフォルトは 0
> - パスワードの平文保存を避けるため `${ENV_VAR}` に対応：`onvif://admin:${CAM_PASSWORD}@192.168.1.100`

> **ヒント**: カメラアドレスや認証情報の漏洩を防ぐため、`config.yaml` は `.gitignore` に追加することを推奨。

## データフロー

```
RTSP / ONVIF ストリーム ──> MotionGate（フレーム差分ゲーティング）
                            │
                     min_change_ratio ≥ threshold?
                            │いいえ└─ スキップ
                            │はい
                     [AI クールダウンチェック]
                            │
                     collect_frames() マルチフレーム取得
                            │
                     AIPipeline.run_batch() バッチ推論
                            │
                     有意なラベル ≥ threshold?
                            │いいえ└─ スキップ
                            │はい
                     スナップショット/クリップ保存 → timeline.csv 追記
                            │
                     Notifier プッシュ（HA / Hook スクリプト）
```

## 録画とタイムライン

```
data/
  {camera_id}/
    {date}/
      snapshots/
        140530_person.jpg      # イベントスナップショット
      clips/
        140530_person.mp4      # イベントビデオクリップ
      timeline.csv             # 日次イベントインデックス
```

`timeline.csv` 形式：

```
start_time,end_time,event_type,snapshot_path,clip_path
2026-05-07T14:05:30,2026-05-07T14:05:35,person,snapshots/140530_person.jpg,clips/140530_person.mp4
```

同一イベントタイプは 3 秒以内の重複を抑制し、連続録画を防止します。

## Hook スクリプト

Hook スクリプトは `config.yaml` のルートレベルで設定（グローバル—全イベントタイプですべてのスクリプトが実行されます）：

```yaml
# オプション：イベント発生時に実行する外部スクリプト
hooks:
  - command: scripts/event_logger.sh
```

各スクリプトは CLI 引数を受け取ります：

```
--camera-id xiaomi1
--event-type person
--start-time 2026-05-07T14:05:30
--end-time 2026-05-07T14:05:35
--snapshot-path snapshots/140530_person.jpg
--clip-path clips/140530_person.mp4
--labels '{"person": 0.85}'
```

## 検出器の拡張

`PersonYoloDetector`（YOLOv8 人体検出）を内蔵。カスタム検出器の追加手順：

1. `VisionDetector` または `AudioDetector`（`surveillance/detectors/base.py`）を継承
2. 一意の `name` クラス変数を設定
3. `analyze_batch()` を実装し `VisionResult` / `AudioResult` を返す（複数フレームを受け取り、使用方法を決定）
4. `AIPipeline.from_camera_detectors()` に登録

```python
from surveillance.detectors.base import VisionDetector, VisionResult, VisionContext

class FireDetector(VisionDetector):
    name = "fire_detector"

    def analyze_batch(self, frames, ctx: VisionContext | None = None):
        # 火災検出ロジック...
        return VisionResult(labels={"fire": 0.92})
```

## プロジェクト構造

```
solo-surveillance/
├── config.example.yaml              # サンプル設定（全オプション）
├── pyproject.toml                   # パッケージメタデータ、依存関係、CLI エントリポイント
├── surveillance/                    # コアアプリケーションパッケージ
│   ├── __main__.py                  # `python -m surveillance` エントリポイント
│   ├── main.py                      # CLI パーサー、カメラスレッド管理
│   ├── config_loader.py             # YAML 読み込み、deep_merge、${ENV_VAR} 展開
│   ├── stream.py                    # RTSPReader — フレームキャプチャと自動再接続
│   ├── motion.py                    # MotionGate — フレーム差分モーション検出
│   ├── region.py                    # フレームを正規化 ROI にクロッピング
│   ├── vision_burst.py              # マルチフレームサンプリングと結果マージ
│   ├── recordings.py                # スナップショット/クリップ録画とタイムライン CSV
│   ├── onvif.py                     # ONVIF 検出 → RTSP URL 解決
│   ├── http_server.py               # 内蔵 Web UI と API サーバー
│   ├── static/index.html            # シングルページ Web UI
│   └── detectors/
│       ├── base.py                  # 抽象 VisionDetector / AudioDetector
│       ├── person_yolo.py           # YOLOv8 人体検出
│       ├── llm_vision.py            # LLM API シーン分析
│       └── pipeline.py              # AIPipeline — 全検出器を統括
└── docs/                            # ドキュメント
    ├── configuration.md             # 詳細設定ガイドとベストプラクティス
    ├── scenarios.md                 # シナリオ設定例
    └── homeassistant.md             # Home Assistant 連携手順
```

### スレッドモデル

- 有効なカメラごとに独立した `threading.Thread` を作成
- `threading.Event` でシャットダウンを調整（SIGINT / SIGTERM）
- 各スレッドは独立した `RTSPReader`、`MotionGate`、`AIPipeline` を保持（共有状態なし）
- HTTP サーバーはデーモンスレッドで実行、メインフローをブロックしない
- Hook スクリプトはデーモンスレッドで実行（30秒タイムアウト）

## 依存関係

| 依存パッケージ | 用途 | 使用モジュール |
|---|---|---|
| opencv-python-headless | RTSP キャプチャ、画像処理、ビデオエンコード | stream, motion, recordings, llm_vision |
| numpy | フレーム配列演算 | 全体 |
| ultralytics | YOLOv8 推論 | detectors/person_yolo.py |
| PyYAML | 設定ファイル解析 | config_loader.py |
| onvif-zeep | ONVIF デバイス検出と制御 | onvif.py（オプション） |
| anthropic / openai | LLM ビジョン API | detectors/llm_vision.py（オプション） |

Python >= 3.11 が必要。macOS および Linux で動作します。

## ライセンス

MIT
