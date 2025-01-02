import streamlit as st
import duckdb
import requests
import os

DUCKDB_FILE = "clinvar_data.duckdb"

DUCKDB_URL = "https://drive.google.com/file/d/1i3wBXtqjrfXYNV11tgibMlVuk62hFUwB/view?usp=sharing"

@st.cache_data
def download_duckdb():
    if not os.path.exists(DUCKDB_FILE):
        st.info("Downloading Clinvar file from Google Drive. Please wait...")
        response = requests.get(DUCKDB_URL, stream=True)
        response.raise_for_status()
        with open(DUCKDB_FILE, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        st.success("Download complete!. Please don't MOVE or EDIT the downloaded file name")
    else:
        st.info("Clinvar file already exists locally. Skipping download.")

@st.cache_resource
def get_connection():
    return duckdb.connect(DUCKDB_FILE)

@st.cache_data
def get_columns(table_name="clinvar_data"):

    con = get_connection()
    col_info = con.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    columns = [row[1] for row in col_info]
    return columns

def build_search_query(table_name, user_input, limit=500):

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

    download_duckdb()

    con = get_connection()

    st.write("Enter standard names as described in Clinvar; You can search a mutation type, C and P variants, Genes, and more.")

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
