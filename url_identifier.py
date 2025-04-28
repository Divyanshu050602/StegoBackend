import re

def identify_url_type(url):
    url = url.strip().lower()

    patterns = {
        "Reddit Post": r"(https?://)?(www\.)?reddit\.com/r/[\w\d_]+/comments/[\w\d]+",
        "YouTube Video": r"(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w\-]+",
        "Instagram Post": r"(https?://)?(www\.)?instagram\.com/(p|reel|tv)/[\w\-]+",
    }

    for platform, pattern in patterns.items():
        if re.match(pattern, url):
            return platform

    return "Unknown"

def main():
    print("🔗 Social Media URL Type Identifier")
    print("=" * 40)
    input_url = input("Enter the post URL: ").strip()

    result = identify_url_type(input_url)

    print(f"\n🧭 Detected Type: {result}")

if __name__ == "__main__":
    main()
