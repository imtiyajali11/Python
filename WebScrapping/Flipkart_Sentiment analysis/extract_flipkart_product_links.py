#!/usr/bin/env python3
"""Extract Flipkart product page URLs from search results and save to CSV.

Usage:
    python extract_flipkart_product_links.py --query mobiles --pages 5 --output product_links.csv
"""
import argparse
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
import pandas as pd

BASE = "https://www.flipkart.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
}


def extract_product_links(query="mobiles", max_pages=3, delay=2.0, retry_limit=3):
    """
    Extract product links from Flipkart search results.
    
    Args:
        query: Search term (default: "mobiles")
        max_pages: Number of pages to scrape (can be 100-200)
        delay: Delay between requests in seconds (default: 2.0)
        retry_limit: Number of retries on failure (default: 3)
    
    Returns:
        Sorted list of unique product URLs
    """
    links = set()
    product_info = []
    base_url = "https://www.flipkart.com/search"
    consecutive_blocks = 0
    
    print(f"🚀 Scraping Flipkart for '{query}' - up to {max_pages} pages\n")

    for page in range(1, max_pages + 1):
        if consecutive_blocks >= 3:
            print(f"\n⚠️  Blocked 3 times in a row. Stopping scraping.")
            break
            
        params = {"q": query, "page": page}
        retry_count = 0
        
        while retry_count < retry_limit:
            try:
                resp = requests.get(base_url, headers=HEADERS, params=params, timeout=20)
                
                if resp.status_code == 429:
                    print(f"📄 Page {page}: Rate limited, waiting 30s...")
                    time.sleep(30)
                    retry_count += 1
                    consecutive_blocks += 1
                    continue
                    
                if resp.status_code != 200:
                    print(f"📄 Page {page}: Status {resp.status_code} - Retrying...")
                    retry_count += 1
                    consecutive_blocks += 1
                    time.sleep(5)
                    continue
                
                consecutive_blocks = 0
                soup = BeautifulSoup(resp.text, "html.parser")
                
                # Target product cards - find divs containing product links
                product_cards = soup.find_all("div", class_=["_1AtVbE", "_2GkwZy"])
                page_links = 0
                
                if not product_cards:
                    # Fallback: search for any links with product path patterns
                    for a in soup.find_all("a", href=True):
                        href = a.get("href", "").strip()
                        if not href or href.startswith("javascript:"):
                            continue
                        # Extract product links from Flipkart
                        if "/p/" in href:
                            clean_url = href.split("?")[0]
                            full_url = urljoin(BASE, clean_url) if clean_url.startswith("/") else clean_url
                            if full_url.startswith("http"):
                                links.add(full_url)
                                page_links += 1
                else:
                    # Better: extract from product cards
                    for card in product_cards:
                        # Find the main product link
                        a_tag = card.find("a", {"class": "IRpwTa"}) or card.find("a", {"class": "s1Q9rs"})
                        if not a_tag:
                            # Try to find any product link in the card
                            a_tag = card.find("a", href=True)
                        
                        if a_tag and a_tag.get("href"):
                            href = a_tag["href"].strip()
                            if "/p/" in href:
                                clean_url = href.split("?")[0]
                                full_url = urljoin(BASE, clean_url) if clean_url.startswith("/") else clean_url
                                if full_url.startswith("http"):
                                    links.add(full_url)
                                    
                                    # Try to extract product name and price
                                    name_tag = card.find("div", class_="KzDlHZ")
                                    name = name_tag.text.strip() if name_tag else "N/A"
                                    
                                    price_tag = card.find("div", class_=["_30jeq3", "hZ3P6w"])
                                    price = price_tag.text.strip() if price_tag else "N/A"
                                    
                                    product_info.append({
                                        "product_name": name,
                                        "price": price,
                                        "product_url": full_url
                                    })
                                    page_links += 1
                
                print(f"📄 Page {page}: Extracted {page_links} product links (Total: {len(links)})")
                break  # Success, move to next page
                
            except requests.exceptions.RequestException as e:
                print(f"📄 Page {page}: Connection error - {str(e)[:50]}")
                retry_count += 1
                time.sleep(5)
        
        if retry_count >= retry_limit:
            print(f"📄 Page {page}: Failed after {retry_limit} retries, skipping...")
        
        time.sleep(delay)

    print(f"\n✅ Scraping complete! Extracted {len(links)} unique product links")
    return sorted(links), product_info


def save_links(links, product_info, output_path="product_links.csv", info_output_path="product_info.csv"):
    """Save extracted links and product info to CSV files."""
    # Save unique links
    df_links = pd.DataFrame({"product_url": links})
    df_links.to_csv(output_path, index=False, encoding="utf-8")
    print(f"✅ Saved {len(df_links)} unique product links to {output_path}")
    
    # Save product info (name, price, link) - always save even if empty
    df_info = pd.DataFrame(product_info) if product_info else pd.DataFrame(columns=["product_name", "price", "product_url"])
    if len(df_info) > 0:
        df_info = df_info.drop_duplicates(subset=["product_url"])
    df_info.to_csv(info_output_path, index=False, encoding="utf-8")
    print(f"✅ Saved {len(df_info)} product details to {info_output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Flipkart product links from search results")
    parser.add_argument("--query", default="mobiles", help="Search query (default: mobiles)")
    parser.add_argument("--pages", type=int, default=5, help="Number of pages to scrape (default: 5, can go up to 200)")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between requests in seconds (default: 2.0)")
    parser.add_argument("--output", default="product_links.csv", help="Output file for product links")
    parser.add_argument("--info-output", default="product_info.csv", help="Output file for product info (name, price, link)")
    parser.add_argument("--retry", type=int, default=3, help="Retry limit on failure (default: 3)")
    
    args = parser.parse_args()
    
    # Validate pages
    if args.pages > 200:
        print(f"⚠️  Limiting pages to 200 (requested {args.pages})")
        args.pages = 200
    
    # Run scraper
    links, product_info = extract_product_links(
        query=args.query, 
        max_pages=args.pages, 
        delay=args.delay,
        retry_limit=args.retry
    )
    
    # Save results
    save_links(links, product_info, args.output, args.info_output)
