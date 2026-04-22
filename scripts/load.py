import psycopg2  
from sqlalchemy import create_engine
import extract as e
import transform as t

from dotenv import load_dotenv
import os

load_dotenv('/opt/airflow/.env')
# load_dotenv()``
def load(df):
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASS")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    db = os.getenv("DB_NAME")


    engine = create_engine(f"postgresql://{user}:{password}@{host}:{port}/{db}")
    df.to_sql(name = "currency_data", con=engine, if_exists = 'replace', index=False)

if __name__ == "__main__":
    data = e.extract_currency()
    df = t.transform_currency(data)
    result = load(df)
    print(result)