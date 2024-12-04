import streamlit as st
import pandas as pd
import os
import zipfile
import tempfile


def extract_zip_nested(uploaded_zip):
    """
    Extracts a ZIP file to a temporary directory, including files in nested folders.

    Args:
        uploaded_zip: Streamlit uploaded file.

    Returns:
        str: Path to the temporary directory containing extracted files.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(uploaded_zip, 'r') as z:
            z.extractall(temp_dir)
        st.success("ZIP file extracted successfully, including nested folders.")
    except Exception as e:
        st.error(f"Failed to extract ZIP file: {e}")
    return temp_dir


def collect_csv_files(folder_path):
    """
    Recursively collects all CSV files in a folder, including nested folders.

    Args:
        folder_path (str): Path to the folder.

    Returns:
        list: List of file paths to CSV files.
    """
    csv_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.csv'):
                csv_files.append(os.path.join(root, file))
    return csv_files


def generate_column_frequency_report(folder_path):
    """
    Generates a frequency report for all CSV files in a folder, summing the non-empty values for each column.

    Args:
        folder_path (str): Path to the folder containing CSV files.

    Returns:
        pd.DataFrame: Frequency report DataFrame.
    """
    results = []
    csv_files = collect_csv_files(folder_path)

    for file_path in csv_files:
        file_name = os.path.basename(file_path)
        st.info(f"Processing file: {file_name}")
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            if df.empty:
                st.warning(f"File '{file_name}' is empty.")
                continue
            df.columns = df.columns.str.strip()  # Normalize column headers
            for column in df.columns:
                non_empty_count = df[column].notna().sum()  # Count non-empty values
                results.append({
                    'Sheet Name': file_name,
                    'Header Name': column,
                    'Frequency': non_empty_count
                })
        except Exception as e:
            st.error(f"Error processing file '{file_name}': {e}")

    return pd.DataFrame(results)


def generate_frequency_report(folder_path):
    """
    Generates a detailed frequency report for all CSV files in a folder.

    Args:
        folder_path (str): Path to the folder containing CSV files.

    Returns:
        pd.DataFrame: Detailed frequency report DataFrame.
    """
    results = []
    csv_files = collect_csv_files(folder_path)

    for file_path in csv_files:
        file_name = os.path.basename(file_path)
        st.info(f"Processing file: {file_name}")
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            if df.empty:
                st.warning(f"File '{file_name}' is empty.")
                continue
            df.columns = df.columns.str.strip()  # Normalize column headers
            for column in df.columns:
                freq = df[column].value_counts().reset_index()
                freq.columns = ['Value', 'Frequency']
                for _, row in freq.iterrows():
                    results.append({
                        'Sheet Name': file_name,
                        'Header Name': column,
                        'Value': row['Value'],
                        'Frequency': row['Frequency']
                    })
        except Exception as e:
            st.error(f"Error processing file '{file_name}': {e}")

    return pd.DataFrame(results)


# Main Streamlit App
def main():
    st.title("The Groundtruth Handler")

    # Tabs for functionalities
    tabs = st.tabs(["Count Generator", "Unique Frequency Generator"])

    # Tab 1: Column Frequency Report
    with tabs[0]:
        st.header("Count Generator")
        uploaded_zip = st.file_uploader("Upload ZIP File Containing CSVs", type="zip")

        if uploaded_zip and st.button("Generate Column Frequency Report"):
            try:
                folder_path = extract_zip_nested(uploaded_zip)
                frequency_report = generate_column_frequency_report(folder_path)
                if not frequency_report.empty:
                    st.dataframe(frequency_report)
                    st.download_button(
                        label="Download Column Frequency Report",
                        data=frequency_report.to_csv(index=False),
                        file_name="column_frequency_report.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("No data found to generate the report.")
            except Exception as e:
                st.error(f"An error occurred: {e}")

    # Tab 2: Detailed Frequency Report
    with tabs[1]:
        st.header("Unique Frequency Generator")
        uploaded_zip = st.file_uploader("Upload ZIP File Containing CSVs (Detailed)", type="zip")

        if uploaded_zip and st.button("Generate Detailed Frequency Report"):
            try:
                folder_path = extract_zip_nested(uploaded_zip)
                detailed_report = generate_frequency_report(folder_path)
                if not detailed_report.empty:
                    st.dataframe(detailed_report)
                    st.download_button(
                        label="Download Detailed Frequency Report",
                        data=detailed_report.to_csv(index=False),
                        file_name="detailed_frequency_report.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("No data found to generate the report.")
            except Exception as e:
                st.error(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
