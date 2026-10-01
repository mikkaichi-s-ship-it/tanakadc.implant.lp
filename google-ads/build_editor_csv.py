"""Google 広告エディタ用の一括入稿ファイルを生成する。

使い方:
    python3 google-ads/build_editor_csv.py https://<LPのURL>/

出力: google-ads/editor-import.tsv
  Google 広告エディタ →「アカウント」→「インポート」→「テキストを貼り付け」または
  「ファイルからインポート」で読み込むと、キャンペーン・広告グループ・キーワード・
  除外キーワード・レスポンシブ検索広告がまとめて作成されます。
"""
import csv
import os
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))

CAMPAIGN = "インプラント_たつの周辺"
DAILY_BUDGET = "2500"
MAX_CPC = "300"

# 広告グループごとの見出し1（固定表示）。検索語句と見出しを一致させる
PINNED_HEADLINE = {
    "地域×インプラント": "たつの市のインプラント相談",
    "インプラント（地域ターゲティングで絞込み）": "たつの市でインプラントなら",
    "悩み・不安（当院の強み）": "持病・服薬中の方もご相談を",
    "指名": "たなか歯科クリニック",
}

MATCH = {"Phrase": "Phrase", "Exact": "Exact", "Broad": "Broad"}


def width(text):
    return sum(2 if unicodedata.east_asian_width(c) in "FWA" else 1 for c in text)


def read_csv(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    if len(sys.argv) != 2 or not sys.argv[1].startswith("https://"):
        sys.exit("使い方: python3 build_editor_csv.py https://<LPのURL>/")
    lp_url = sys.argv[1]

    keywords = read_csv("keywords.csv")
    negatives = read_csv("negative-keywords.csv")
    rsa = read_csv("responsive-search-ads.csv")
    headlines = [r["Text"] for r in rsa if r["Asset type"] == "Headline"]
    descriptions = [r["Text"] for r in rsa if r["Asset type"] == "Description"]
    path1 = next(r["Text"] for r in rsa if r["Asset type"] == "Path1")
    path2 = next(r["Text"] for r in rsa if r["Asset type"] == "Path2")

    cols = (
        ["Campaign", "Campaign Type", "Networks", "Budget", "Budget type",
         "Bid Strategy Type", "Language", "Campaign Status",
         "Ad Group", "Max CPC", "Ad Group Status",
         "Keyword", "Criterion Type", "Status",
         "Ad type", "Final URL", "Path 1", "Path 2"]
        + [f"Headline {i}" for i in range(1, 16)]
        + ["Headline 1 position"]
        + [f"Description {i}" for i in range(1, 5)]
    )
    rows = []

    def row(**kw):
        r = dict.fromkeys(cols, "")
        r.update(kw)
        rows.append(r)

    # キャンペーン（審査・確認のため一時停止で作成。確認後に有効化）
    row(Campaign=CAMPAIGN, **{
        "Campaign Type": "Search", "Networks": "Google search",
        "Budget": DAILY_BUDGET, "Budget type": "Daily",
        "Bid Strategy Type": "Maximize clicks", "Language": "ja",
        "Campaign Status": "Paused"})

    groups = list(dict.fromkeys(k["Ad group"] for k in keywords))
    for g in groups:
        row(Campaign=CAMPAIGN, **{"Ad Group": g, "Max CPC": MAX_CPC,
                                   "Ad Group Status": "Enabled"})
        for k in keywords:
            if k["Ad group"] == g:
                row(Campaign=CAMPAIGN, **{"Ad Group": g, "Keyword": k["Keyword"],
                                           "Criterion Type": MATCH[k["Match type"]],
                                           "Status": "Enabled"})
        # 固定見出しを先頭にし、残りから重複を除いて計15本
        pinned = PINNED_HEADLINE[g]
        hs = [pinned] + [h for h in headlines if h != pinned]
        hs = hs[:15]
        ad = {"Ad Group": g, "Ad type": "Responsive search ad",
              "Final URL": lp_url, "Path 1": path1, "Path 2": path2,
              "Headline 1 position": "1", "Status": "Enabled"}
        for i, h in enumerate(hs, 1):
            ad[f"Headline {i}"] = h
        for i, d in enumerate(descriptions, 1):
            ad[f"Description {i}"] = d
        row(Campaign=CAMPAIGN, **ad)

    for n in negatives:
        row(Campaign=CAMPAIGN, **{"Keyword": n["Negative keyword"],
                                   "Criterion Type": "Campaign Negative Phrase",
                                   "Status": "Enabled"})

    # 文字数チェック（全角=2）
    for r in rows:
        for i in range(1, 16):
            h = r[f"Headline {i}"]
            assert width(h) <= 30, f"見出しが長すぎます: {h}"
        for i in range(1, 5):
            d = r[f"Description {i}"]
            assert width(d) <= 90, f"説明文が長すぎます: {d}"

    out = os.path.join(HERE, "editor-import.tsv")
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    print(f"{out} を出力しました（{len(rows)} 行、最終URL: {lp_url}）")


if __name__ == "__main__":
    main()
