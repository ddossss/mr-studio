[English](README.md) | [한국어](README.ko.md) | 日本語

# MR Studio

YouTube のURL、または自分の音源ファイル → ボーカル除去・キー調整(-5~+5半音) → MRとして書き出し。

## 実行

`run.bat` をダブルクリック → ブラウザでアプリが開く (http://127.0.0.1:7860)

## 機能

手順: ①音源を入れる → ②パート・キーを設定 → ③**プレビュー** → ④**作成（書き出し）**  
音源を入れた後は、パート・キーを変更するたびにプレビューが自動更新されます（新しい曲の初回分離のみ1~2分）。

- **読み込み**: YouTube のURL、または自分の音源ファイル(mp3/wav/flacなど)。ファイルがある場合はファイルが優先されます。
- **残すパート**: メインボーカル / コーラス / ドラム / ベース / ギター / ピアノ / 管楽器 / その他楽器をそれぞれON/OFF。
  - デフォルト = メインボーカルのみOFF → コーラスを含むMR
  - 全てON → 分離せず原曲のキーのみ調整
  - 管楽器（オーケストラ用）: トランペット・ホルン・トロンボーン・サックス・フルートなどを**一括で**分離。トランペットだけを個別に分離するモデルはありません。
    管楽器やその他楽器をOFFにした場合のみ、管楽器分離のステップが追加で実行されます（初回処理+数十秒）。
- **キー調整**: 半音単位で-5~+5（テンポ維持、rubberband使用）
- **作成（書き出し）**: プレビューで確認した設定のままmp3(320k)またはwavで書き出し → `output/`フォルダにも保存

一度分離した曲は`cache/`に保存されるため、パート/キーだけを変えて再作成すれば数秒で完了します。

## 構成

- 分離1段階: Demucs `htdemucs_6s` → ボーカル / ドラム / ベース / ギター / ピアノ / その他
- 分離2段階: Mel-Roformer Karaoke → ボーカルをメインボーカル / コーラスに分離
- (管楽器ON/OFF時) 分離0段階: UVR `17_HP-Wind_Inst` → 管楽器 / それ以外、残りを1・2段階へ
- ミックス(numpy) → キー調整 + リミッター + エンコード(ffmpeg)
- UI: Gradio (v2.0のWeb版も同じアプリをサーバーに載せる方式で拡張可能)

## 制限

- **Amazon Musicは非対応**: DRM保護されたストリームのため抽出不可。購入・所持している音源ファイルを読み込みでご利用ください。
- YouTubeの音源は個人練習用としてのみ使用してください（著作権にご注意）。

## 新しいPCへのインストール

```bat
winget install --id Gyan.FFmpeg --exact
winget install --id yt-dlp.yt-dlp --exact
winget install --id DenoLand.Deno --exact
py -3.13 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

NVIDIA GPU推奨（CPUのみの場合、1曲あたり数分）。初回実行時に分離モデル(~0.9GB)を`models/`へ自動ダウンロード。

## テスト

`.venv\Scripts\python test_app.py` → `OK`

## Made by

[Perch Creative](https://perch-creative.com) — Webサイト制作・ブランディング・ツール開発
