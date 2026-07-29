# 開発・リリース手順

インストール方法や使い方は [README.md](README.md) を参照してください。ここでは開発時のコミット規約とリリースの流れを説明します。

## 名前の構成

意図的に3種類の名前を使い分けています。

| 種類 | 値 | 定義場所 |
|---|---|---|
| PyPI 配布名 | `kanameishi` | `pyproject.toml` の `project.name` |
| import 名 (ディレクトリ) | `kanameishi` | `src/kanameishi/` |
| 起動コマンド | `kaname` | `pyproject.toml` の `[project.scripts]` |

コマンド名だけ短くしています。この差があるため、**`uvx kanameishi` は動きません**。`uvx` は既定でパッケージ名と同名の実行ファイルを探すので、`uvx --from kanameishi kaname` と指定する必要があります (`pipx run` も同様に `--spec` が必要)。`pipx install` / `uv tool install` は影響を受けません。

## バージョンの管理方針

バージョンは **手で編集しません**。`main` にマージされたコミットメッセージから [release-please](https://github.com/googleapis/release-please) が次のバージョンを判定し、以下の3ファイルをまとめて更新します。

| ファイル | 用途 |
|---|---|
| `pyproject.toml` | パッケージのバージョン |
| `src/kanameishi/__init__.py` | `__version__` (アプリ内で参照) |
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
4. **PRをマージする** → タグ `vX.Y.Z` と GitHub Release が作成され、続けて `publish` ジョブが wheel / sdist をビルドして Release と PyPI に配布する

リリースPRは、マージするまで後続のコミットに応じて中身が更新され続けます。「機能を数個まとめてから出す」場合は、マージせず放置しておけばよいです。逆に、`main` にマージした時点ではまだリリースされない点に注意してください。リリースはPRのマージが契機です。

## 配布されるもの

| 配布先 | 内容 |
|---|---|
| PyPI | `kanameishi` パッケージ (`pipx install kanameishi` で入る) |
| GitHub Release | リリースノート (CHANGELOG.md から生成) |
| GitHub Release | `kanameishi-X.Y.Z-py3-none-any.whl` と `kanameishi-X.Y.Z.tar.gz` |
| GitHub Release | Source code (zip / tar.gz) — タグが打たれると GitHub が自動生成 |

`publish` ジョブは1回のビルド成果物を GitHub Release と PyPI の両方に配ります。**PyPI へのアップロードは最後**に実行します。取り消しが効かない操作なので、先に失敗しうる処理を済ませておく順序です。アップロード前に `twine check --strict` でメタデータを検証しています。

リリースノートの見出しは release-please のデフォルトで英語 (`Features` / `Bug Fixes`) です。日本語にしたい場合は `release-please-config.json` に `changelog-sections` を追加して `{"type": "feat", "section": "新機能"}` のように指定します。

## ローカルでビルドを確認する

CI と同じ成果物を手元で作れます。

```bash
python -m pip install build
python -m build
```

`dist/` に wheel と sdist ができます。

> venv を `myenv/` `venv/` `env/` `.venv` 以外の名前でプロジェクト直下に作ると、sdist に venv が丸ごと混入して `AbsoluteLinkError` でビルドが失敗します。hatchling が参照するのは**ルートの `.gitignore` だけ**で、`python -m venv` が venv 内部に生成する `.gitignore` は読まれないためです。その名前をルートの `.gitignore` に追記すれば解消します。

## 初回のみ必要な設定

### 1. リポジトリ設定 (GitHub)

release-please は GitHub Actions からPRを作るため、リポジトリ側で許可が必要です。**これを設定しないとワークフローが `GitHub Actions is not permitted to create or approve pull requests` で失敗します。**

Settings → Actions → General → Workflow permissions:

- **Read and write permissions** を選択
- **Allow GitHub Actions to create and approve pull requests** にチェック

### 2. PyPI の Trusted Publishing 設定

APIトークンは使いません。GitHub Actions の OIDC で認証するため、**PyPI 側に発行元リポジトリを登録**します。トークンを Secrets に置かずに済むので、漏洩リスクのある長期クレデンシャルを持ちません。

`kanameishi` はまだ PyPI に存在しないので、**Pending publisher** として登録します。

1. https://pypi.org/manage/account/publishing/ を開く
2. 「Add a new pending publisher」に以下を入力

| 項目 | 値 |
|---|---|
| PyPI Project Name | `kanameishi` |
| Owner | `yamato3010` |
| Repository name | `kanameishi` |
| Workflow name | `release-please.yml` |
| Environment name | (空欄) |

初回の公開が成功すると PyPI 上にプロジェクトが作られ、pending publisher は通常の publisher に切り替わります。

> より厳しくしたい場合は、GitHub 側に `pypi` という Environment を作って必須レビュアーを設定し、ワークフローの `publish` ジョブに `environment: pypi` を追加、PyPI 側の Environment name にも同じ名前を入れます。公開前に手動承認を挟めるようになりますが、名前が一致しないと失敗するので、必要になってからで構いません。

## 初回リリース後の後片付け

`release-please-config.json` の `bootstrap-sha` は、初回のCHANGELOGに古い履歴を含めないための設定です (`079538f` = 「インストール方法を追記」時点)。初回のリリースPRがマージされた後は参照されなくなるので、削除して構いません。

## トラブルシューティング

**リリースPRが作られない**

- 前回リリース以降のコミットに `feat:` / `fix:` が無い (`docs:` だけでは作られない)
- 上記のリポジトリ設定が済んでいない
- コミットメッセージの型とコロンの間に空白が入っている (`feat :` は認識されません)

**バージョンが `pyproject.toml` だけ更新され `__init__.py` が変わらない**

release-please は `pyproject.toml` の `project.name` (`kanameishi`) をハイフン→アンダースコアに変換して `src/kanameishi/__init__.py` を探します。パッケージ名を変えるときは `src/` 配下のディレクトリ名も合わせてください。ここがずれると**エラーにならず片方だけ更新される**ため、About画面のバージョンが上がらなくなります。

なお起動コマンド名 (`kaname`) は `[project.scripts]` で定義しているだけで、release-please の探索には関係ありません。コマンド名だけを変える場合、`src/` のディレクトリ名は触らないでください。

**PyPI 公開が `invalid-publisher` で失敗する**

PyPI 側の Trusted Publishing 設定と実際の実行内容が一致していません。Owner / Repository name / Workflow name (`release-please.yml`) / Environment name の4つを見比べてください。

よくある原因は**GitHub のリポジトリ名やアカウント名を変更した**ことです。Trusted Publishing の設定はリポジトリ名に紐づいており、GitHub 側のリダイレクトでは救われません。リネームしたら PyPI 側の publisher 設定も更新してください。

**PyPI 公開が `File already exists` で失敗する**

同じバージョンを再アップロードしようとしています。PyPI はバージョン番号の再利用を許しません。`fix:` コミットを積んで次のバージョンとしてリリースし直してください。

**CHANGELOG に `docs:` の変更も載せたい**

`release-please-config.json` の該当パッケージに `changelog-sections` を追加し、`{"type": "docs", "section": "ドキュメント", "hidden": false}` のように指定します。
