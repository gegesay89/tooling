import streamlit as st
import pandas as pd
import os
import zipfile
import tempfile


def extract_zip(uploaded_zip):
    """
    Extracts a ZIP file to a temporary directory.

    Args:
        uploaded_zip: Streamlit uploaded file.

    Returns:
        str: Path to the temporary directory containing extracted files.
    """
    temp_dir = tempfile.mkdtemp()
    with zipfile.ZipFile(uploaded_zip, 'r') as z:
        z.extractall(temp_dir)
    return temp_dir


def generate_column_frequency_report(folder_path):
    """
    Generates a frequency report for all CSV files in a folder, summing the non-empty values for each column.

    Args:
        folder_path (str): Path to the folder containing CSV files.

    Returns:
        pd.DataFrame: Frequency report DataFrame.
    """
    results = []

    for file_name in os.listdir(folder_path):
        if file_name.endswith('.csv'):
            file_path = os.path.join(folder_path, file_name)
            try:
                df = pd.read_csv(file_path, encoding='utf-8')
                df.columns = df.columns.str.strip()  # Normalize column headers
                for column in df.columns:
                    non_empty_count = df[column].notna().sum()  # Count non-empty values
                    results.append({
                        'Sheet Name': file_name,
                        'Header Name': column,
                        'Frequency': non_empty_count
                    })
            except Exception as e:
                st.error(f"Error processing {file_name}: {e}")

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

    for file_name in os.listdir(folder_path):
        if file_name.endswith('.csv'):
            file_path = os.path.join(folder_path, file_name)
            try:
                df = pd.read_csv(file_path, encoding='utf-8')
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
                st.error(f"Error processing {file_name}: {e}")

    return pd.DataFrame(results)


def main():
    st.title("The Groundtruth Handler")

    # Tabs for functionalities
    tabs = st.tabs(["MCD (Map, Copy and Download)", "Count Generator", "Unique Frequency Generator"])

    # Tab 1: Map and Copy Data
    with tabs[0]:
        st.header("MCD")
        source_file = st.file_uploader("Upload Source CSV", type="csv")
        target_file = st.file_uploader("Upload Target CSV", type="csv")
        source_mapping_input = st.text_area("Source Columns (one per line)", "")
        target_mapping_input = st.text_area("Target Columns (one per line)", "")

        if st.button("Run Mapping"):
            if source_file and target_file and source_mapping_input and target_mapping_input:
                try:
                    source_df = pd.read_csv(source_file)
                    target_df = pd.read_csv(target_file)
                    source_mapping = [col.strip() for col in source_mapping_input.split("\n")]
                    target_mapping = [col.strip() for col in target_mapping_input.split("\n")]

                    updated_target_df = map_and_copy_data(source_df, target_df, source_mapping, target_mapping)

                    st.dataframe(updated_target_df)
                    st.download_button(
                        label="Download Updated Target CSV",
                        data=updated_target_df.to_csv(index=False),
                        file_name=os.path.basename(target_file.name),
                        mime="text/csv"
                    )
                except Exception as e:
                    st.error(f"An error occurred: {e}")
            else:
                st.error("Please upload both files and provide column mappings.")

    # Tab 2: Column Frequency Report
    with tabs[1]:
        st.header("Count Generator")
        uploaded_zip = st.file_uploader("Upload ZIP File Containing CSVs", type="zip")

        if uploaded_zip and st.button("Generate Column Frequency Report"):
            try:
                folder_path = extract_zip(uploaded_zip)
                frequency_report = generate_column_frequency_report(folder_path)
                st.dataframe(frequency_report)
                st.download_button(
                    label="Download Column Frequency Report",
                    data=frequency_report.to_csv(index=False),
                    file_name="column_frequency_report.csv",
                    mime="text/csv"
                )
            except Exception as e:
                st.error(f"An error occurred: {e}")

    # Tab 3: Detailed Frequency Report
    with tabs[2]:
        st.header("Unique Frequency Generator")
        uploaded_zip = st.file_uploader("Upload ZIP File Containing CSVs (Detailed)", type="zip")

        if uploaded_zip and st.button("Generate Detailed Frequency Report"):
            try:
                folder_path = extract_zip(uploaded_zip)
                detailed_report = generate_frequency_report(folder_path)
                st.dataframe(detailed_report)
                st.download_button(
                    label="Download Detailed Frequency Report",
                    data=detailed_report.to_csv(index=False),
                    file_name="detailed_frequency_report.csv",
                    mime="text/csv"
                )
            except Exception as e:
                st.error(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
