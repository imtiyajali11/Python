from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from transformers import pipeline
import pandas as pd
import numpy as np

def analyze_sentiment(df):
    # VADER
    analyzer = SentimentIntensityAnalyzer()
    df['vader_score'] = df['comment'].apply(lambda x: analyzer.polarity_scores(str(x))['compound'])
    df['vader_sentiment'] = df['vader_score'].apply(lambda x: 'Positive' if x > 0.05 else 'Negative' if x < -0.05 else 'Neutral')
    
    # RoBERTa
    sentiment_pipeline = pipeline("sentiment-analysis", model="siebert/sentiment-roberta-large-english")
    def get_roberta_sentiment(text):
        result = sentiment_pipeline(text[:512])[0]
        return result['score'] if result['label'] == 'POSITIVE' else -result['score']
    
    print("🤖 Running RoBERTa (this may take time)...")
    df['roberta_score'] = df['comment'].apply(get_roberta_sentiment)
    df['roberta_sentiment'] = df['roberta_score'].apply(lambda x: 'Positive' if x > 0 else 'Negative')
    
    return df


def compare_models(df):
    comparison = df.groupby('rating').agg({
        'vader_score': 'mean',
        'roberta_score': 'mean',
        'vader_sentiment': lambda x: x.value_counts().to_dict(),
        'roberta_sentiment': lambda x: x.value_counts().to_dict()
    })
    print("📊 Model Comparison:")
    print(comparison)
    return comparison