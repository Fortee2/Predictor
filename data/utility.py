import requests

class utility:
   
    def call_url_with_symbol(self, url, symbol):
        full_url = url + symbol  # Append the symbol to the URL
        response = requests.get(full_url)  # Send a GET request to the full URL
        return response
    
    def call_url_with_post_symbol(self, url, symbol):
        full_url = url + symbol  # Append the symbol to the URL
        response = requests.post(full_url)  # Send a GET request to the full URL
        return response
