import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from tqdm import tqdm
import random

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
}

def get_product_links(num_products=20, max_pages=5):
    """Scrape product links from Flipkart search"""
    base_url = "https://www.flipkart.com/search?q=mobiles&otracker=search&otracker1=search"
    product_links = []
    page = 1
    
    print(f"🔍 Scraping product links (target: {num_products})...")
    
    while len(product_links) < num_products and page <= max_pages:
        url = f"{base_url}&page={page}"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Blocked on page {page}")
            break
            
        soup = BeautifulSoup(response.text, 'html.parser')
        product_cards = soup.find_all('div', {'data-id': True})
        for card in product_cards:
            link_tag = card.find('a', class_='k7wcnx')
            if not link_tag:
                link_tag = card.find('a', href=lambda x: x and '/p/' in str(x))
            if link_tag:
                full_link = "https://www.flipkart.com" + link_tag['href']
                if full_link not in product_links:
                    product_links.append(full_link)
                    if len(product_links) >= num_products:
                        break
                    
        print(f"📄 Page {page}: {len(product_links)} products found")
        page += 1
        time.sleep(random.uniform(1.5, 3))
    
    # Save products
    df_products = pd.DataFrame(product_links, columns=['product_url'])
    df_products.to_csv('data/products.csv', index=False)
    print(f"✅ Saved {len(product_links)} product links")
    return product_links


def scrape_reviews(product_url, num_reviews=50):
    """Scrape reviews from a single product page"""
    reviews = []
    all_reviews_url = product_url
    
    if '?' in product_url:
        base, params = product_url.split('?', 1)
        if 'page=' not in params:
            sep = '&' if params else ''
            all_reviews_url = f"{base}?{params}{sep}page=1&sort=RELEVANCE"
    else:
        all_reviews_url = f"{product_url}?page=1&sort=RELEVANCE"
    
    print(f"📝 Scraping reviews for: {product_url.split('/')[-1]}")
    
    page = 1
    while len(reviews) < num_reviews:
        if page == 1:
            review_url = all_reviews_url
        else:
            review_url = all_reviews_url.replace('page=1', f'page={page}')
        response = requests.get(review_url, headers=headers)
        
        if response.status_code != 200:
            break
            
        soup = BeautifulSoup(response.text, 'html.parser')
        review_cards = soup.find_all('div', class_='col _2wzgFH K0kLPL')
        if not review_cards:
            review_cards = soup.find_all('div', class_='RZ3QUn._3AT3_6')
        if not review_cards:
            review_cards = soup.find_all('div', attrs={'data-testid': 'review-card'})
        
        for card in review_cards:
            try:
                rating_tag = card.find('div', class_='_3LWZlK')
                if not rating_tag:
                    rating_tag = card.find('div', class_='XQDdHH._1QPb6y')
                rating = rating_tag.text.strip() if rating_tag else 'N/A'
                if rating == 'N/A':
                    continue
                
                title_tag = card.find('p', class_='_2-N8zT')
                if not title_tag:
                    title_tag = card.find('p', class_='z9I68M')
                title = title_tag.text.strip() if title_tag else ''
                
                comment_tag = card.find('div', class_='t-ZTKM')
                if not comment_tag:
                    comment_tag = card.find('div', class_='ZmyHeo')
                comment = comment_tag.text.strip() if comment_tag else ''
                
                reviewer_tag = card.find('p', class_='_2sc7ZR _2V5EHH')
                if not reviewer_tag:
                    reviewer_tag = card.find('p', class_='l9SLGd')
                reviewer = reviewer_tag.text.strip() if reviewer_tag else 'N/A'
                
                reviews.append({
                    'product_url': product_url,
                    'rating': float(rating),
                    'title': title,
                    'comment': comment,
                    'reviewer': reviewer,
                    'review_date': 'N/A'
                })
            except Exception:
                continue
                
        page += 1
        time.sleep(random.uniform(1, 2.5))
        
        if len(reviews) >= num_reviews:
            break
    
    print(f"   → Got {len(reviews)} reviews")
    return reviews