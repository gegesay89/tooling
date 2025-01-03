import pandas as pd
import streamlit as st
from sqlalchemy import create_engine

# Create a connection engine using SQLAlchemy
def get_connection():
    server = "clinar.database.windows.net"
    database = "clinvar"
    username = "gegesay89"
    password = "Arsenal89"
    driver = "ODBC Driver 17 for SQL Server"
    connection_string = f"mssql+pyodbc://{username}:{password}@{server}/{database}?driver={driver}"
    return create_engine(connection_string)

# Get the list of tables in the database
def get_tables():
    engine = get_connection()
    with engine.connect() as connection:
        query = """
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        """
        tables = pd.read_sql(query, connection)
        return tables['TABLE_NAME'].tolist()

# Query the database
def query_database(query):
    engine = get_connection()
    with engine.connect() as connection:
        return pd.read_sql(query, connection)

# Streamlit app
def main():
    st.title("ClinVar Variant Database Query")

    st.write("Search across all columns in a selected table. Enter a value to retrieve matching rows.")

    # Fetch available tables
    tables = get_tables()
    if not tables:
        st.error("No tables found in the database.")
        return

    # Select table
    selected_table = st.selectbox("Select a table to search:", tables)

    # Search functionality
    user_input = st.text_input("Search for a term:", "")

    if st.button("Search"):
        if user_input.strip():
            try:
                # Build the search query
                query = f"""
                    SELECT TOP 500 *
                    FROM {selected_table}
                    WHERE CONCAT_WS(' ', Type, Name, GeneSymbol, ClinicalSignificance, dbSNP, PhenotypeList, Origin, OriginSimple, Assembly, Chromosome, Cytogenetic, c_variant, p_variant) LIKE '%{user_input}%'
                """
                st.info(f"Running query:\n```\n{query}\n```")
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
