import os
import sys
import requests


def check_isbn(isbn: str, api_key: str | None = None):
    api_key = api_key or os.getenv('GOOGLE_BOOKS_API_KEY')
    if not api_key:
        raise ValueError('GOOGLE_BOOKS_API_KEY is not set; cannot query Google Books API.')

    if len(isbn) > 13:
        print('ISBN appears too long; still querying API...')

    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}&maxResults=1&key={api_key}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit('Usage: python misc.py <isbn>')
    print(check_isbn(sys.argv[1]))