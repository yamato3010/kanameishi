# TUI強震モニタ

ターミナル上で動作するリアルタイム地震情報モニターアプリケーション。

P2P地震情報 API v2 を利用して、地震情報・津波予報をリアルタイムに表示します。

## 機能

- 🗾 ASCIIアート日本地図上に震源を表示
- 🚨 緊急地震速報〔警報〕の受信時、地図上にP波・S波の到達予想円をアニメーション表示
- ⏱️ 予報区ごとの主要動到達カウントダウン (「あと N 秒」)
- 📊 震度分布をカラーバーチャートで表示
- 📍 震度ごと・都道府県ごとの観測地点名 (市区町村レベル) を一覧表示
- 📋 地震履歴の一覧表示
- 🌊 津波予報の警告表示
- 🔄 WebSocket によるリアルタイム更新
- ⌨️ キーボードショートカットによる操作

## インストール

### PyPI からインストール (推奨)

パッケージ名は `kanameishi`、起動コマンドは `kaname` です。依存関係を専用の仮想環境に隔離したまま、どのディレクトリからでも実行できます。

```bash
# pipx が未導入の場合 (初回のみ)
brew install pipx
pipx ensurepath  # PATH 追加。反映されない場合はターミナルを再起動

pipx install kanameishi
```

`uv` を使っている場合:

```bash
uv tool install kanameishi
```

インストールせず一度だけ試す (コマンド名が違うため `--from` が必要):

```bash
uvx --from kanameishi kaname
```

更新・アンインストール:

```bash
pipx upgrade kanameishi
pipx uninstall kanameishi
```

### Release の wheel を指定する

バージョンを固定したい場合は、[Releases](https://github.com/yamato3010/tui-earthquake-monitor/releases) に添付された wheel を直接指定できます。

```bash
# X.Y.Z は Releases ページで最新のバージョンに置き換えてください
pipx install https://github.com/yamato3010/tui-earthquake-monitor/releases/download/vX.Y.Z/kanameishi-X.Y.Z-py3-none-any.whl
```

### ソースからインストール

```bash
# リポジトリのルートで実行
pipx install .

# 更新する場合 (コードを変更/pull した後)
pipx install . --force
```

### pipx を使わない場合

```bash
pip install --user .
```

### 開発用インストール (editable)

コードを編集しながら動作確認したい場合はこちら。

```bash
pip install -e .
```

## 使い方

```bash
# モジュールとして実行 (editable インストール時など)
python -m kanameishi

# グローバルインストール後はどこからでも実行可能
kaname
```

## キーバインド

| キー | 動作 |
|---|---|
| `Q` | アプリ終了 |
| `R` | データ更新 |
| `↑` `↓` (`K` `J`) | 履歴スクロール |
| `D` | 選択した地震の詳細表示 |
| `?` | このアプリについて (`Esc` で閉じる) |
| `E` | 緊急地震速報のデモ表示 (動作確認用) |

## 緊急地震速報について

- P2P地震情報の code 556 (緊急地震速報〔警報〕) を受信して表示します。警報級 (予想最大震度5弱以上) のみ配信されるため、実際に受信する機会はまれです
- P波 (○) ・S波 (●) の到達予想円は定数速度 (P: 7km/s, S: 4km/s) による近似で、気象庁の走時表とは数秒ずれることがあります
- `E` キーでデモ用のEEWを表示して動作を確認できます
- 環境変数 `KANAME_SANDBOX=1` を設定して起動すると、P2P地震情報の開発サンドボックスAPI (過去データの繰り返し配信) に接続します

## 時刻の扱い

画面に出る時刻・相対表記 (「n分前」) ・カウントダウンはすべて日本標準時 (JST) 基準です。端末のタイムゾーンがJST以外でもずれません。

## データソース

[P2P地震情報](https://www.p2pquake.net/) - 商用・非商用問わず無償利用可能

## ライセンス

MIT
