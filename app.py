import pyodbc
import pandas as pd
import streamlit as st

# Function to connect to the Azure SQL database
def get_connection():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=clinar.database.windows.net;"  # Your Azure SQL Server name
        "DATABASE=clinvar;"  # Your Azure SQL Database name
        "UID=gegesay89;"  # Your Azure SQL username
        "PWD=Arsenal89;"  # Your Azure SQL password
    )

# Function to query the database
def query_database(query):
    conn = get_connection()
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Streamlit app
def main():
    st.title("ClinVar Variant Database Query")

    # Search functionality
    st.write("Search for genetic variants by specifying the column and value.")
    search_column = st.selectbox(
        "Select a column to search in:",
        [
            "Type",
            "Name",
            "GeneSymbol",
            "ClinicalSignificance",
            "dbSNP",
            "PhenotypeList",
            "Origin",
            "OriginSimple",
            "Assembly",
            "Chromosome",
            "Cytogenetic",
            "c-variant",
            "p-variant",
        ],
    )
    search_value = st.text_input("Enter the value to search for:")

    if st.button("Search"):
        try:
            query = f"SELECT * FROM dbo.variants WHERE {search_column} LIKE '%{search_value}%'"
            results = query_database(query)
            if not results.empty:
                st.write(f"Found {len(results)} matching rows:")
                st.dataframe(results)
            else:
                st.warning("No matching rows found.")
        except Exception as e:
            st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
