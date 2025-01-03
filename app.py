import streamlit as st
import pyodbc
import pandas as pd

# Azure SQL database connection
def get_connection():
    """
    Establish a connection to the Azure SQL database.
    """
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=clinar.database.windows.net;"  # Azure SQL Server name
        "DATABASE=clinvar;"  # Database name
        "UID=gegesay89;"  # Username
        "PWD=Arsenal89;"  # Password
    )

def get_columns(table_name="dbo.variants"):
    """
    Retrieve column names from the specified Azure SQL table.
    """
    conn = get_connection()
    query = f"""
    SELECT COLUMN_NAME 
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = '{table_name.split('.')[-1]}';
    """
    columns = pd.read_sql_query(query, conn)['COLUMN_NAME'].tolist()
    conn.close()
    return columns

def build_search_query(table_name, user_input, limit=500):
    """
    Build a SQL query to search for user_input across all columns in the table.
    """
    valid_columns = get_columns(table_name)
    conditions = []
    for col in valid_columns:
        condition = f"{col} LIKE '%{user_input}%'"
        conditions.append(condition)

    where_clause = " OR ".join(conditions)
    query = f"""
        SELECT TOP {limit} *
        FROM {table_name}
        WHERE {where_clause}
    """
    return query

def query_database(query):
    """
    Execute the given query and return the result as a DataFrame.
    """
    conn = get_connection()
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def main():
    st.title("Genetic Data Query")

    st.write(
        "Enter a keyword to search the `dbo.variants` table. The app will search across all columns and return matching rows."
    )

    # User Input
    user_input = st.text_input("Search for a term:", "")

    if st.button("Search"):
        if user_input.strip():
            st.info("Searching for matches...")
            try:
                # Build and execute the query
                query = build_search_query("dbo.variants", user_input)
                results = query_database(query)
                
                if not results.empty:
                    st.write(f"Found {len(results)} matching rows.")
                    st.dataframe(results)
                else:
                    st.warning("No matching rows found.")
            except Exception as e:
                st.error(f"An error occurred: {e}")
        else:
            st.warning("Please enter a non-empty search term.")

if __name__ == "__main__":
    main()
