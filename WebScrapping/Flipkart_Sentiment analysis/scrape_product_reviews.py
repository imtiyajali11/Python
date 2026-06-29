#!/usr/bin/env python3
"""
Scrape reviews and details from individual Flipkart product pages.
Uses product links extracted from search results.
"""
import time
import sys
import csv
import json
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
import pandas as pd

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}

BASE = "https://www.flipkart.com"


def extract_product_details(product_url, retry_limit=3):
    """
    Extract product details and reviews from a Flipkart product page.
    
    Args:
        product_url: Full URL of the product page
        retry_limit: Number of retries on failure
    
    Returns:
        Dictionary with product details and reviews, or None on failure
    """
    retry_count = 0
    
    while retry_count < retry_limit:
        try:
            resp = requests.get(product_url, headers=HEADERS, timeout=20)
            
            if resp.status_code == 429:
                time.sleep(30)
                retry_count += 1
                continue
            
            if resp.status_code != 200:
                time.sleep(5)
                retry_count += 1
                continue
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            product_data = {
                "product_url": product_url,
                "product_name": "N/A",
                "price": "N/A",
                "rating": "N/A",
                "reviews_count": "N/A",
                "description": "N/A",
                "reviews": []
            }
            
            # Extract product name
            name_tag = soup.find("div", class_="B6needP")
            if not name_tag:
                name_tag = soup.find("h1", class_="Nx9bqj")
            if name_tag:
                product_data["product_name"] = name_tag.text.strip()
            
            # Extract price
            price_tag = soup.find("div", class_="_16Jk6d")
            if not price_tag:
                price_tag = soup.find("div", class_="hZ3P6w")
            if price_tag:
                product_data["price"] = price_tag.text.strip()
            
            # Extract rating and review count
            rating_tag = soup.find("div", class_="_3LWZlK")
            if rating_tag:
                product_data["rating"] = rating_tag.text.strip()
            
            review_count_tag = soup.find("span", class_="_1_BvJV")
            if review_count_tag:
                product_data["reviews_count"] = review_count_tag.text.strip()
            
            # Extract description
            desc_tag = soup.find("div", class_="pZY9G0")
            if desc_tag:
                product_data["description"] = desc_tag.text.strip()[:500]
            
            # Extract reviews from the page (initial load)
            # Note: Flipkart loads reviews dynamically, so we'll get limited reviews
            review_containers = soup.find_all("div", class_="t0gRjf")
            
            for idx, review_div in enumerate(review_containers[:10]):  # Limit to 10 visible reviews
                review_item = {}
                
                # Reviewer name
                reviewer_tag = review_div.find("p", class_="MNH9rk")
                review_item["reviewer_name"] = reviewer_tag.text.strip() if reviewer_tag else "N/A"
                
                # Review rating
                rating_elem = review_div.find("div", class_="_3LWZlK")
                review_item["review_rating"] = rating_elem.text.strip() if rating_elem else "N/A"
                
                # Review title
                title_tag = review_div.find("p", class_="z9E0IG")
                review_item["review_title"] = title_tag.text.strip() if title_tag else "N/A"
                
                # Review text
                text_tag = review_div.find("div", class_="ti6qHl")
                review_item["review_text"] = text_tag.text.strip() if text_tag else "N/A"
                
                # Helpful count
                helpful_tag = review_div.find("span", class_="_1ckkH_")
                review_item["helpful_count"] = helpful_tag.text.strip() if helpful_tag else "0"
                
                product_data["reviews"].append(review_item)
            
            return product_data
            
        except requests.exceptions.RequestException as e:
            print(f"  ⚠️  Connection error: {str(e)[:40]}")
            retry_count += 1
            time.sleep(5)
        except Exception as e:
            print(f"  ⚠️  Parse error: {str(e)[:40]}")
            return None
    
    return None


def scrape_reviews_from_links(links_csv="product_links.csv", output_csv="flipkart_products_with_reviews.csv", 
                              max_products=None, delay=1.5):
    """
    Scrape reviews from a list of product links.
    
    Args:
        links_csv: CSV file with product URLs
        output_csv: Output CSV file for products with reviews
        max_products: Limit number of products (None for all)
        delay: Delay between requests in seconds
    """
    # Read product links
    if not Path(links_csv).exists():
        print(f"❌ File not found: {links_csv}")
        return
    
    df_links = pd.read_csv(links_csv)
    links = df_links["product_url"].tolist()
    
    if max_products:
        links = links[:max_products]
    
    print(f"🚀 Scraping {len(links)} products for reviews...\n")
    
    all_products = []
    
    for idx, link in enumerate(links, 1):
        print(f"[{idx}/{len(links)}] Scraping: {link[:60]}...")
        
        product_data = extract_product_details(link)
        
        if product_data:
            all_products.append(product_data)
            print(f"  ✅ Extracted: {product_data['product_name'][:40]}")
            if product_data["reviews"]:
                print(f"  📝 Reviews: {len(product_data['reviews'])}")
        else:
            print(f"  ❌ Failed to extract")
        
        time.sleep(delay)
    
    # Flatten reviews into separate rows
    flattened = []
    for product in all_products:
        if product["reviews"]:
            for review in product["reviews"]:
                flattened.append({
                    "product_url": product["product_url"],
                    "product_name": product["product_name"],
                    "price": product["price"],
                    "rating": product["rating"],
                    "reviews_count": product["reviews_count"],
                    "description": product["description"],
                    "reviewer_name": review.get("reviewer_name", "N/A"),
                    "review_rating": review.get("review_rating", "N/A"),
                    "review_title": review.get("review_title", "N/A"),
                    "review_text": review.get("review_text", "N/A")[:500],
                    "helpful_count": review.get("helpful_count", "0"),
                })
        else:
            # Add product even if no reviews found
            flattened.append({
                "product_url": product["product_url"],
                "product_name": product["product_name"],
                "price": product["price"],
                "rating": product["rating"],
                "reviews_count": product["reviews_count"],
                "description": product["description"],
                "reviewer_name": "N/A",
                "review_rating": "N/A",
                "review_title": "N/A",
                "review_text": "N/A",
                "helpful_count": "0",
            })
    
    # Save to CSV
    df_final = pd.DataFrame(flattened)
    df_final.to_csv(output_csv, index=False, encoding="utf-8")
    
    print(f"\n✅ Scraping complete!")
    print(f"✅ Saved {len(flattened)} rows to {output_csv}")
    print(f"   - Unique products: {len(all_products)}")
    print(f"   - Total reviews: {len(flattened) - len(all_products)}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Scrape reviews from Flipkart product links")
    parser.add_argument("--input", default="product_links.csv", help="Input CSV with product links")
    parser.add_argument("--output", default="flipkart_products_with_reviews.csv", help="Output CSV file")
    parser.add_argument("--max", type=int, default=None, help="Max number of products to scrape")
    parser.add_argument("--delay", type=float, default=1.5, help="Delay between requests (seconds)")
    
    args = parser.parse_args()
    
    scrape_reviews_from_links(
        links_csv=args.input,
        output_csv=args.output,
        max_products=args.max,
        delay=args.delay
    )
