from apify_client import ApifyClient

def get_instagram_comments(instagram_url, apify_token):
    # Initialize the ApifyClient with your API token
    client = ApifyClient(apify_token)

    # Prepare input using the correct key 'directUrls'
    run_input = {
        "directUrls": [instagram_url],
        "resultsLimit": 1000,
        "scrollWaitSecs": 3,
        "proxy": {"useApifyProxy": True},
    }

    print("\n🔄 Starting the Instagram comment scraping...")

    # Call the Apify Instagram Comment Scraper actor
    run = client.actor("apify/instagram-comment-scraper").call(run_input=run_input)

    # Fetch results
    comments_list = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        comment = item.get("text")
        if comment:
            comments_list.append(comment)

    return comments_list

def main():
    print("📸 Instagram Comment Scraper with Apify\n" + "=" * 40)
    instagram_url = input("🔗 Enter the public Instagram post URL: ").strip()

    # Replace with your actual Apify API token
    apify_token = "apify_api_j3pf5iuSm0Xcrvi4BHGmwxi5hDlyRi14liqZ"

    try:
        comments = get_instagram_comments(instagram_url, apify_token)

        print("\n💬 Scraped Comments\n" + "-" * 30)
        for comment in comments:
            print(comment)

        print(f"\n✅ Done. {len(comments)} comments stored in memory (list of strings).")

    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()

# apify_api_j3pf5iuSm0Xcrvi4BHGmwxi5hDlyRi14liqZ