import streamlit as st
import duckdb
import requests
import os

# The local filename for the DuckDB file:
DUCKDB_FILE = "clinvar_data.duckdb"

# Direct download link from Google Drive:
DUCKDB_URL = "https://drive.google.com/uc?export=download&id=17jAQY8y9cIvUIjF5E5nStSr_65mno5_D"

@st.cache_data
def download_duckdb():
    """
    Download the .duckdb file from Google Drive if it's not present locally.
    We cache this so it only downloads once per session unless cache is cleared.
    (Returns None, which is fine for @st.cache_data)
    """
    if not os.path.exists(DUCKDB_FILE):
        st.info("Downloading DuckDB file from Google Drive. Please wait...")
        response = requests.get(DUCKDB_URL, stream=True)
        response.raise_for_status()
        with open(DUCKDB_FILE, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        st.success("Download complete!")
    else:
        st.info("DuckDB file already exists locally. Skipping download.")

@st.cache_resource
def get_connection():
    """
    Return a DuckDB connection object (non-serializable).
    Using @st.cache_resource so Streamlit doesn't try to pickle it.
    """
    return duckdb.connect(DUCKDB_FILE)

@st.cache_data
def get_columns(table_name="clinvar_data"):
    """
    Dynamically get a list of columns from the given table using DuckDB's PRAGMA.
    Returns a list of column names (serializable data).
    """
    con = get_connection()
    col_info = con.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    # col_info is like [(0, 'Type', ...), (1, 'Name', ...), ...]
    columns = [row[1] for row in col_info]
    return columns

def build_search_query(table_name, user_input, limit=500):
    """
    Construct a SQL query to search for user_input in ANY column (case-insensitive).
    """
    cols = get_columns(table_name)
    conditions = []
    for col in cols:
        # Cast columns to TEXT and use ILIKE for case-insensitive partial match
        conditions.append(f"CAST({col} as TEXT) ILIKE '%{user_input}%'")
    where_clause = " OR ".join(conditions)
    query = f"""
        SELECT *
        FROM {table_name}
        WHERE {where_clause}
        LIMIT {limit}
    """
    return query

def main():
    st.title("ClinVar DuckDB Search (Fixed)")

    # 1) Download the DuckDB file (if needed)
    download_duckdb()

    # 2) Get a DuckDB connection
    con = get_connection()

    st.write("Enter any text to search across ALL columns in the 'clinvar_data' table.")

    user_input = st.text_input("Search text", "")

    if st.button("Search"):
        if user_input.strip():
            query = build_search_query("clinvar_data", user_input)
            st.info(f"Running query:\n```\n{query}\n```")
            df = con.execute(query).df()
            st.write(f"Found {len(df)} matching rows.")
            st.dataframe(df)
        else:
            st.warning("Please enter a non-empty search term.")

if __name__ == "__main__":
    main()
