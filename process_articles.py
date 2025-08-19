import json

def process_articles(input_file, output_file):
    """
    記事が2つ以上ある場合は後半の記事のみを残す
    """
    # ファイルを読み込み
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # データを処理
    for company in data['データ']:
        articles = company.get('四季報記事', [])
        if len(articles) > 1:
            # 記事が2つ以上ある場合は最後の記事のみを残す
            company['四季報記事'] = [articles[-1]]
            print(f"証券コード {company['証券コード']}: {len(articles)}記事 → 1記事に削減")
    
    # 処理結果を保存
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"処理完了: {output_file}")

if __name__ == "__main__":
    input_file = "shikiho_articles_async.json"
    output_file = "shikiho_articles_processed.json"
    process_articles(input_file, output_file) 