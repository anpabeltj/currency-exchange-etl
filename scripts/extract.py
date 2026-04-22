import requests




def extract_currency():
    url = "https://api.frankfurter.dev/v2/rates?from=2026-01-01&quotes=IDR,MYR,SGD,USD&base=USD"
    response = requests.get(url)
    return response.json()

if __name__ == "__main__":
    currency_data = extract_currency()

    for item in currency_data:
        print(item['base'], item['date'], item['quote'], item['rate'])
   
