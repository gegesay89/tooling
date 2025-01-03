import streamlit as st
import duckdb
import requests
import os

# Path for the local DuckDB file
DUCKDB_FILE = "clinvar_data.duckdb"

# Raw file URL for the DuckDB file on GitHub
DUCKDB_URL = "https://raw.githubusercontent.com/gegesay89/tooling/Clinvar/clinvar_data.duckdb"

@st.cache_data
def download_duckdb_from_github():
    """
    Download the DuckDB file from GitHub if it doesn't already exist locally.
    """
    if not os.path.exists(DUCKDB_FILE):
        st.info("Downloading DuckDB file from GitHub. Please wait...")
        response = requests.get(DUCKDB_URL, stream=True)
        response.raise_for_status()  # Raise an error for bad status codes
        with open(DUCKDB_FILE, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        st.success("Download complete!")
    else:
        st.info("DuckDB file already exists locally. Skipping download.")

@st.cache_resource
def get_connection():
    """
    Establish a connection to the DuckDB database file.
    """
    return duckdb.connect(DUCKDB_FILE)

@st.cache_data
def get_columns(table_name="clinvar_data"):
    """
    Retrieve column names from the specified DuckDB table.
    """
    con = get_connection()
    col_info = con.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    columns = [row[1] for row in col_info]
    return columns

def build_search_query(table_name, user_input, limit=500):
    """
    Build a SQL query to search for user_input across all columns in the table.
    """
    valid_columns = get_columns(table_name)
    conditions = []
    for col in valid_columns:
        safe_col = col.replace('"', '""')
        condition = f'CAST("{safe_col}" AS TEXT) ILIKE \'%{user_input}%\''
        conditions.append(condition)

    where_clause = " OR ".join(conditions)
    query = f"""
        SELECT *
        FROM "{table_name}"
        WHERE {where_clause}
        LIMIT {limit}
    """
    return query

def main():
    st.title("Genetic Data Query")

    # Step 1: Download the DuckDB file from GitHub if needed
    download_duckdb_from_github()

    # Step 2: Establish a connection to the database
    con = get_connection()

    st.write("Enter standard names as described in ClinVar; You can search a mutation type, C and P variants, Genes, and more.")

    # Step 3: User Input
    user_input = st.text_input("Search", "")

    if st.button("Search"):
        if user_input.strip():
            query = build_search_query("clinvar_data", user_input)
            st.info(f"Running query:\n```\n{query}\n```")
            try:
                df = con.execute(query).df()
                st.write(f"Found {len(df)} matching rows.")
                st.dataframe(df)
            except Exception as e:
                st.error(f"An error occurred while running the query: {e}")
        else:
            st.warning("Please enter a non-empty search term.")

if __name__ == "__main__":
    main()
