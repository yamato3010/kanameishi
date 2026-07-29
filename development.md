# 開発・リリース手順

インストール方法や使い方は [README.md](README.md) を参照してください。ここでは開発時のコミット規約とリリースの流れを説明します。

## バージョンの管理方針

バージョンは **手で編集しません**。`main` にマージされたコミットメッセージから [release-please](https://github.com/googleapis/release-please) が次のバージョンを判定し、以下の3ファイルをまとめて更新します。

| ファイル | 用途 |
|---|---|
| `pyproject.toml` | パッケージのバージョン |
| `src/earthquake_tui/__init__.py` | `__version__` (アプリ内で参照) |
| `CHANGELOG.md` | 変更履歴 (自動生成) |

`?` キーで開く「このアプリについて」画面は `__version__` を読んでいるため、リリースすると表示も自動で追従します。

現在のバージョンの正は `.release-please-manifest.json` です。ここと上記ファイルがずれると混乱するので、バージョン文字列を直接書き換えないでください。

## コミットメッセージとバージョンの対応

[Conventional Commits](https://www.conventionalcommits.org/ja/v1.0.0/) 形式で書きます。判定はコロンの前の型 (`feat` / `fix` など) だけを見るので、これまで通り絵文字を入れて構いません。

| コミットの型 | 例 | バージョンの動き |
|---|---|---|
| `feat:` | `feat: ✨ 観測地点名を表示` | minor (0.1.0 → 0.2.0) |
| `fix:` | `fix: 🐛 地図の崩れを修正` | patch (0.1.0 → 0.1.1) |
| `feat!:` または本文に `BREAKING CHANGE:` | `feat!: ✨ 設定形式を変更` | major (0.1.0 → 1.0.0) |
| `docs:` `chore:` `refactor:` `test:` `style:` | `docs: 📝 READMEを修正` | 上がらない |

`docs:` や `chore:` だけを積んだ場合、リリースPRは作られません。バージョンを上げたいときは `feat:` か `fix:` を含める必要があります。

> 0.x 系のうちは breaking change で 1.0.0 に上がります。まだ 1.0 を出したくない場合は `release-please-config.json` に `"bump-minor-pre-major": true` を追加すると、breaking change でも minor 止まりになります。

## リリースの流れ

1. `feat:` / `fix:` を含む変更を `main` にマージする
2. `.github/workflows/release-please.yml` が動き、**`chore(main): release X.Y.Z` というPRが自動で作られる**
3. そのPRの差分を確認する (バージョン3ファイル + CHANGELOG.md が想定通りか)
4. **PRをマージする** → タグ `vX.Y.Z` と GitHub Release が自動作成される

リリースPRは、マージするまで後続のコミットに応じて中身が更新され続けます。「機能を数個まとめてから出す」場合は、マージせず放置しておけばよいです。逆に、`main` にマージした時点ではまだリリースされない点に注意してください。リリースはPRのマージが契機です。

リリース後、利用者側の更新手順:

```bash
git pull
pipx install . --force
```

## 初回のみ必要なリポジトリ設定

release-please は GitHub Actions からPRを作るため、リポジトリ側で許可が必要です。**これを設定しないとワークフローが `GitHub Actions is not permitted to create or approve pull requests` で失敗します。**

Settings → Actions → General → Workflow permissions:

- **Read and write permissions** を選択
- **Allow GitHub Actions to create and approve pull requests** にチェック

## 初回リリース後の後片付け

`release-please-config.json` の `bootstrap-sha` は、初回のCHANGELOGに古い履歴を含めないための設定です (`079538f` = 「インストール方法を追記」時点)。初回のリリースPRがマージされた後は参照されなくなるので、削除して構いません。

## トラブルシューティング

**リリースPRが作られない**

- 前回リリース以降のコミットに `feat:` / `fix:` が無い (`docs:` だけでは作られない)
- 上記のリポジトリ設定が済んでいない
- コミットメッセージの型とコロンの間に空白が入っている (`feat :` は認識されません)

**バージョンが `pyproject.toml` だけ更新され `__init__.py` が変わらない**

release-please は `pyproject.toml` の `project.name` (`earthquake-tui`) をハイフン→アンダースコアに変換して `src/earthquake_tui/__init__.py` を探します。パッケージ名を変えるときは `src/` 配下のディレクトリ名も合わせてください。

**CHANGELOG に `docs:` の変更も載せたい**

`release-please-config.json` の該当パッケージに `changelog-sections` を追加し、`{"type": "docs", "section": "ドキュメント", "hidden": false}` のように指定します。
