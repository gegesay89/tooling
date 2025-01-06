import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

# Cache database connection
@st.cache_resource
def get_connection():
    """
    Create and cache a database connection using SQLAlchemy.
    """
    server = "clinar.database.windows.net"
    database = "clinvar"
    username = "gegesay89"
    password = "Arsenal89"
    driver = "ODBC Driver 17 for SQL Server"
    connection_string = f"mssql+pyodbc://{username}:{password}@{server}/{database}?driver={driver}"
    return create_engine(connection_string)

# Query the database
def query_database(query, params=None):
    """
    Execute a database query with optional parameters.
    """
    engine = get_connection()
    with engine.connect() as connection:
        try:
            # Use parameterized queries for safety
            return pd.read_sql(query, connection, params=params)
        except Exception as e:
            connection.rollback()  # Roll back any invalid transactions
            raise e

# Pagination for large results
def paginate_dataframe(df, page_size=100):
    """
    Paginate a DataFrame for better display in Streamlit.
    """
    total_pages = (len(df) + page_size - 1) // page_size
    page = st.number_input(
        "Page number",
        min_value=1,
        max_value=total_pages,
        value=1,
        step=1,
        format="%d"
    )
    start = (page - 1) * page_size
    end = start + page_size
    return df.iloc[start:end]

# Streamlit App
def main():
    st.title("GENIEVAR")

    st.write("Enter standard names as described in ClinVar; You can search a mutation type, C and P variants, Genes, and more.")

    # Fixed table name
    table_name = "variants"

    # Search functionality
    user_input = st.text_input("Enter search term:", "")

    if st.button("Search"):
        if user_input.strip():
            try:
                # Build the parameterized query
                query = text(f"""
                    SELECT *
                    FROM {table_name}
                    WHERE Type LIKE :user_input
                       OR Name LIKE :user_input
                       OR GeneSymbol LIKE :user_input
                       OR ClinicalSignificance LIKE :user_input
                       OR dbSNP LIKE :user_input
                       OR PhenotypeList LIKE :user_input
                       OR Origin LIKE :user_input
                       OR OriginSimple LIKE :user_input
                       OR Assembly LIKE :user_input
                       OR Chromosome LIKE :user_input
                       OR Cytogenetic LIKE :user_input
                       OR [c-variant] LIKE :user_input
                       OR [p-variant] LIKE :user_input;
                """)
                # Pass parameters for safer queries
                params = {"user_input": f"%{user_input}%"}
                st.info("Running query, please wait...")
                results = query_database(query, params)

                if not results.empty:
                    st.write(f"Found {len(results)} matching rows.")
                    # Paginate results
                    paginated_results = paginate_dataframe(results)
                    st.dataframe(paginated_results)
                else:
                    st.warning("No matching rows found.")
            except Exception as e:
                st.error(f"An error occurred: {e}")
        else:
            st.warning("Please enter a search term.")

if __name__ == "__main__":
    main()
