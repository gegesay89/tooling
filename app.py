import pandas as pd
import streamlit as st
from sqlalchemy import create_engine

# Cache database connection
@st.cache_resource
def get_connection():
    server = "clinar.database.windows.net"
    database = "clinvar"
    username = "gegesay89"
    password = "Arsenal89"
    driver = "ODBC Driver 17 for SQL Server"
    connection_string = f"mssql+pyodbc://{username}:{password}@{server}/{database}?driver={driver}"
    return create_engine(connection_string)

# Cache table metadata
@st.cache_data
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

# Pagination for large results
def paginate_dataframe(df, page_size=10):
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
                # Build the query
                query = f"""
                    SELECT *
                    FROM {selected_table}
                    WHERE CONCAT_WS(' ', Type, Name, GeneSymbol, ClinicalSignificance, dbSNP, PhenotypeList, Origin, OriginSimple, Assembly, Chromosome, Cytogenetic, [c-variant], [p-variant]) LIKE '%{user_input}%'
                """
                st.info("Running query, please wait...")
                results = query_database(query)

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
