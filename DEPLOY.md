# Streamlit Cloud デプロイ手順

## 1. Streamlit Community Cloud（無料）でデプロイ

1. https://share.streamlit.io にアクセス
2. GitHub アカウントでログイン
3. "New app" → リポジトリ: `kosotanaka/wcup2026` を選択
4. Branch: `claude/sharp-darwin-Czbn1`
5. Main file path: `app/app.py`
6. "Deploy!" をクリック

数分後に `https://share.streamlit.io/kosotanaka/wcup2026/...` のURLが発行されます。
このURLを家族・友人に共有すれば、スマホからも予測入力できます。

## 2. ローカルで起動する場合

```bash
pip install -r requirements.txt
streamlit run app/app.py
```

## 注意
- `data/predictions/` フォルダに参加者の予測データが保存されます
- Streamlit Cloud では再デプロイのたびにデータがリセットされます
- データを永続化する場合は Google Sheets 連携や外部DBが必要です（今後の拡張）
