import pandas as pd
import extract as e

def transform_currency(data):
    df = pd.DataFrame(data)
    df['extracted_at'] = pd.Timestamp.now().date()
    return df

if __name__ == "__main__":
    currency_data = e.extract_currency()
    transformed_data = transform_currency(currency_data)
    print(transformed_data.head())