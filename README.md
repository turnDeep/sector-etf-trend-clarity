# セクターETFトレンドクラリティ分析

このプロジェクトは、複数のセクターETFのトレンドクラリティを計算し、XLKとの相関を考慮した重み付けでランキングを作成するPythonアプリケーションです。

## 特徴

- 複数期間（1ヶ月、2ヶ月、3ヶ月、6ヶ月、12ヶ月）でのトレンド分析
- 対数株価を使用した線形回帰によるトレンドクラリティの計算
- XLK（テクノロジーセクター）との相関を考慮した重み付け
- 22種類の主要セクターETFの分析

## 必要要件

- Python 3.11以上
- VS Code with Dev Containers extension
- Docker

## Dev Containerでの起動方法

1. このリポジトリをクローンまたはダウンロード

```bash
git clone <repository-url>
cd sector-etf-trend-clarity
```

2. VS Codeでフォルダを開く

```bash
code .
```

3. VS Codeで以下のいずれかの方法でDev Containerを起動
   - コマンドパレット（Ctrl/Cmd + Shift + P）で「Dev Containers: Reopen in Container」を選択
   - 左下の緑色のアイコンをクリックして「Reopen in Container」を選択

4. コンテナが起動したら、ターミナルで実行

```bash
python main.py
```

## 分析対象のETF

- **XLK**: Technology Select Sector SPDR Fund
- **XLY**: Consumer Discretionary Select Sector SPDR Fund
- **XLV**: Health Care Select Sector SPDR Fund
- **XLP**: Consumer Staples Select Sector SPDR Fund
- **XLB**: Materials Select Sector SPDR Fund
- **XLU**: Utilities Select Sector SPDR Fund
- **XLI**: Industrial Select Sector SPDR Fund
- **XLC**: Communication Services Select Sector SPDR Fund
- **XLRE**: Real Estate Select Sector SPDR Fund
- **XLF**: Financial Select Sector SPDR Fund
- **XLE**: Energy Select Sector SPDR Fund
- その他11種類のETF

## アルゴリズムの概要

1. **トレンドクラリティの計算**
   - 各ETFの対数株価に対して線形回帰を実行
   - 決定係数（R²）と傾きの符号を掛け合わせた値を計算

2. **重み付けの計算**
   - 各ETFとXLKの月次リターンの相関係数を計算
   - 相関係数の逆数を重みとして使用（XLKとの相関が低いETFほど高い重み）

3. **ランキングの作成**
   - 各期間のトレンドクラリティを合計
   - XLKとの相関による重み付けを適用
   - 重み付きトレンドクラリティでソート

## カスタマイズ

`main.py`の以下の部分を編集することで、分析をカスタマイズできます：

```python
# セクターETFのシンボルリスト
sector_etfs = ["XLK", "XLY", ...]  # 分析対象のETFを追加・削除

# 分析する期間を指定
periods = ['1mo', '2mo', '3mo', '6mo', '12mo']  # 分析期間を変更
```

## トラブルシューティング

- **データ取得エラー**: インターネット接続を確認し、Yahoo Financeのサービスが利用可能か確認してください
- **計算エラー**: 十分な履歴データがあることを確認してください（最低1年分推奨）

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。