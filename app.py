import streamlit as st
import pandas as pd
import os


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

def main():
    st.title("V1=>V2 Mapper")

    # File upload
    st.header("Upload CSV Files")
    source_file = st.file_uploader("Upload Source CSV", type="csv")
    target_file = st.file_uploader("Upload Target CSV", type="csv")

    # Input for column mappings
    st.header("Column Mappings")
    source_mapping_input = st.text_area("Source Columns", "")
    target_mapping_input = st.text_area("Target Columns", "")

    if st.button("Map and Copy Data"):
        if source_file and target_file and source_mapping_input and target_mapping_input:
            try:
                # Load the CSV files
                source_df = pd.read_csv(source_file)
                target_df = pd.read_csv(target_file)

                # Parse the column mappings
                source_mapping = [col.strip() for col in source_mapping_input.split("\n")]
                target_mapping = [col.strip() for col in target_mapping_input.split("\n")]

                # Perform the mapping and copying
                updated_target_df = map_and_copy_data(source_df, target_df, source_mapping, target_mapping)

                # Display the result and provide a download link
                st.header("Updated Target DataFrame")
                st.dataframe(updated_target_df)

               # Extract the target file name
                target_file_name = os.path.basename(target_file.name)

                # Download link for the updated target file
                st.download_button(
                    label="Download Updated Target CSV",
                    data=updated_target_df.to_csv(index=False),
                    file_name=target_file_name,
                    mime="text/csv"
                )
            except Exception as e:
                st.error(f"An error occurred: {e}")
        else:
            st.error("Please upload both files and provide column mappings.")

if __name__ == "__main__":
    main()
