import streamlit as st
import duckdb

# Raw file URL for the DuckDB file on GitHub
DUCKDB_URL = "https://raw.githubusercontent.com/gegesay89/tooling/Clinvar/clinvar_data.duckdb"

@st.cache_resource
def get_connection():
    """
    Establish a connection to the DuckDB database file hosted online.
    """
    # Connect to the remote DuckDB file
    return duckdb.connect(f":{DUCKDB_URL}")

@st.cache_data
def get_columns(table_name="clinvar_data"):
    """
    Retrieve column names from the specified DuckDB table.
    Validate that the table exists before querying.
    """
    con = get_connection()
    # Check if the table exists
    tables = con.execute("SHOW TABLES").fetchall()
    table_names = [table[0] for table in tables]

    if table_name not in table_names:
        raise ValueError(f"Table '{table_name}' does not exist in the database.")

    # Retrieve column info
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

    # Step 1: Establish a connection
    try:
        con = get_connection()
    except Exception as e:
        st.error(f"Failed to connect to the DuckDB file: {e}")
        return

    # Step 2: Validate and query the table
    try:
        st.write("Enter standard names as described in ClinVar. You can search a mutation type, C and P variants, Genes, and more.")
        user_input = st.text_input("Search", "")

        if st.button("Search"):
            if user_input.strip():
                query = build_search_query("clinvar_data", user_input)
                st.info(f"Running query:\n```\n{query}\n```")
                df = con.execute(query).df()
                st.write(f"Found {len(df)} matching rows.")
                st.dataframe(df)
            else:
                st.warning("Please enter a non-empty search term.")
    except ValueError as ve:
        st.error(f"Database error: {ve}")
    except Exception as e:
        st.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
