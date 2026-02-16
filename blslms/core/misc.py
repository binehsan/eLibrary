import requests
def check_isbn(isbn):
    if len(isbn) > 13:
        print('ohno')
    
    API_KEY = "AIzaSyD5RfvtDLR1Kf7J5lBk6mzOwUKy6sPWRw8"

    h = {'Authorization': {API_KEY}}
    #aic
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}&maxResults=1&key={API_KEY}"

    resp = requests.get(url)
    print(resp.json())


check_isbn(input('Enter ISBN: '))