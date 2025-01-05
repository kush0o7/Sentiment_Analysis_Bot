import tweepy
import json

def fetch_tweets(api_key, api_secret, access_token, access_token_secret, query, count=100):
    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
    api = tweepy.API(auth)
    tweets = api.search_tweets(q=query, count=count, lang="en")
    return [tweet.text for tweet in tweets]

if __name__ == "__main__":
    # Test fetching tweets
    tweets = fetch_tweets("your_api_key", "your_api_secret", "your_access_token", "your_access_token_secret", "stock market")
    with open("../data/tweets.json", "w") as f:
        json.dump(tweets, f)
