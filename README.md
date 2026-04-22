# 💱 Currency Exchange ETL Pipeline

An automated data pipeline that fetches daily currency exchange rates, transforms them, stores them in a PostgreSQL database, and visualizes the data via Metabase. The entire pipeline is orchestrated by Apache Airflow and runs inside Docker containers.

---

## 🏗️ Architecture Overview

```
Frankfurter API
      ↓
  [ Extract ]  → fetch exchange rates (IDR, MYR, SGD vs USD)
      ↓
  [ Transform ] → convert to DataFrame, add timestamp
      ↓
  [ Load ]     → write to PostgreSQL (currency_db)
      ↓
  [ Metabase ] → visualize and explore the data
```

---

## ⚙️ Tech Stack

| Layer             | Tool                                            |
| ----------------- | ----------------------------------------------- |
| 🔁 Orchestration  | Apache Airflow 2.8.1                            |
| 🐍 Scripting      | Python (requests, pandas, psycopg2, SQLAlchemy) |
| 🗄️ Storage        | PostgreSQL 15                                   |
| 📊 Visualization  | Metabase                                        |
| 🐳 Infrastructure | Docker Compose                                  |

---

## 📂 Project Structure

```
currency-exchange/
├── dags/
│   └── currency_exchange.py   # Airflow DAG definition
├── scripts/
│   ├── extract.py             # Fetch data from Frankfurter API
│   ├── transform.py           # Clean and shape the data
│   └── load.py                # Write data to PostgreSQL
├── logs/                      # Airflow task logs
├── .env                       # Database connection secrets
└── docker-compose.yml         # Service definitions
```

---

## 🔄 Pipeline Flow

### 1️⃣ Extract

The `extract.py` script calls the [Frankfurter API](https://frankfurter.dev) to fetch historical exchange rates from 2026-01-01 onward. The base currency is **USD** and the target currencies are **IDR**, **MYR**, and **SGD**.

```python
url = "https://api.frankfurter.dev/v2/rates?from=2026-01-01&quotes=IDR,MYR,SGD,USD&base=USD"
response = requests.get(url)
```

### 2️⃣ Transform

The `transform.py` script converts the raw API response into a pandas DataFrame and appends an `extracted_at` timestamp column to track when the data was collected.

```python
df = pd.DataFrame(data)
df['extracted_at'] = pd.Timestamp.now().date()
```

### 3️⃣ Load

The `load.py` script reads database credentials from the `.env` file, creates a SQLAlchemy engine, and writes the transformed DataFrame into the `currency_data` table in the **currency_db** PostgreSQL database. The table is replaced on each run.

```python
engine = create_engine(f"postgresql://{user}:{password}@{host}:{port}/{db}")
df.to_sql(name="currency_data", con=engine, if_exists="replace", index=False)
```

---

## 🐳 Docker Services

| Service             | Description                                 | Port                 |
| ------------------- | ------------------------------------------- | -------------------- |
| `postgres-airflow`  | Metadata database for Airflow               | internal             |
| `postgres-currency` | Destination database for exchange rate data | 5432(5434 for local) |
| `airflow`           | Scheduler + Webserver                       | 8080                 |
| `metabase`          | BI and visualization tool                   | 3000                 |

---

## 🚀 How to Run

**1. Clone and enter the project folder**

```bash
git clone <repo-url>
cd currency-exchange
```

**2. Set up your environment variables**

Create a `.env` file in the project root with the following values:

```
DB_USER=currency_user
DB_PASS=currency_pass
DB_HOST=postgres-currency
DB_PORT=5432
DB_NAME=currency_db
```

**3. Start all services**

```bash
docker compose up
```

**4. Access the Airflow UI**

Open your browser and go to `http://localhost:8080`

Login credentials:

- Username: `admin`
- Password: `admin`

**5. Trigger the DAG**

Find the `currency_exchange_pipeline` DAG in the Airflow UI and click the ▶️ trigger button to run it manually, or wait for the daily schedule to kick in.

**6. Visualize in Metabase**

Open `http://localhost:3000` and connect Metabase to the `postgres-currency` service to explore the `currency_data` table.

---

## 📅 Schedule

The DAG runs **daily** (`@daily`) and does not backfill historical runs (`catchup=False`). Each run replaces the entire `currency_data` table with the latest fetched data.

---

## 🌐 Data Source

Exchange rate data is provided by [Frankfurter](https://frankfurter.dev), a free and open-source API backed by the European Central Bank.
