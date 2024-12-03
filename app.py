import streamlit as st
import pandas as pd
import os
import zipfile
import tempfile


def map_and_copy_data(source_df, target_df, source_mapping, target_mapping):
    """
    Copies data from the source DataFrame to the target DataFrame based on header mappings.

    Args:
        source_df (pd.DataFrame): Source DataFrame.
        target_df (pd.DataFrame): Target DataFrame.
        source_mapping (list): List of source column headers.
        target_mapping (list): List of target column headers.

    Returns:
        pd.DataFrame: Updated target DataFrame.
    """
    if len(source_mapping) != len(target_mapping):
        st.error("Source and target mappings must have the same length.")
        return target_df

    for src_col, tgt_col in zip(source_mapping, target_mapping):
        if src_col in source_df.columns and tgt_col in target_df.columns:
            target_df[tgt_col] = source_df[src_col]
            st.write(f"Copied data from '{src_col}' to '{tgt_col}'")
        elif tgt_col in target_df.columns:
            st.write(f"No data to copy for '{tgt_col}' (preserved as empty).")
        else:
            st.write(f"Column '{tgt_col}' does not exist in the target file.")

    return target_df


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
                df = pd.read_csv(file_path)
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
                df = pd.read_csv(file_path)
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


# Main Streamlit App
def main():
    st.title("Data Management Suite")

    # Tabs for functionalities
    tabs = st.tabs(["Map and Copy Data", "Column Frequency Report", "Detailed Frequency Report"])

    # Tab 1: Map and Copy Data
    with tabs[0]:
        st.header("Map and Copy Data")
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
        st.header("Column Frequency Report")
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
        st.header("Detailed Frequency Report")
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
