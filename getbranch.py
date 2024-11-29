import os
import zipfile
import pandas as pd
from lxml import etree
import streamlit as st

# Directory to save the uploaded OWL files
UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Streamlit app
st.set_page_config(page_title="OWL Extractor", layout="wide")
st.title('OWL Children and Parents Extractor')

# Function to recursively extract children
def extract_children(root, mendel_id):
    # Namespace URIs
    ns_owl = 'http://www.w3.org/2002/07/owl#'
    ns_rdf = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
    ns_rdfs = 'http://www.w3.org/2000/01/rdf-schema#'

    # Maps to store Mendel IDs and parent-child relationships
    mendel_id_to_node = {}
    parent_to_children = {}

    # Build a mapping from node about attributes to Mendel IDs
    about_to_mendel_id = {}

    # First pass: Build mappings
    for class_node in root.findall(f".//{{{ns_owl}}}Class"):
        # Get the about attribute
        about = class_node.get(f"{{{ns_rdf}}}about")
        if not about:
            continue

        # Find the Mendel_ID element
        mendel_id_elem = class_node.find(f".//{{*}}Mendel_ID")
        if mendel_id_elem is not None and mendel_id_elem.text:
            mendel_id_text = mendel_id_elem.text.strip()
            mendel_id_to_node[mendel_id_text] = class_node
            about_to_mendel_id[about] = mendel_id_text

    # Second pass: Build parent-child relationships
    for class_node in mendel_id_to_node.values():
        mendel_id_elem = class_node.find(f".//{{*}}Mendel_ID")
        if mendel_id_elem is not None and mendel_id_elem.text:
            child_mendel_id = mendel_id_elem.text.strip()

            # Find subClassOf elements
            for subclass_elem in class_node.findall(f"./{{{ns_rdfs}}}subClassOf"):
                parent_resource = subclass_elem.get(f"{{{ns_rdf}}}resource")
                if parent_resource and parent_resource in about_to_mendel_id:
                    parent_mendel_id = about_to_mendel_id[parent_resource]
                    parent_to_children.setdefault(parent_mendel_id, []).append(child_mendel_id)

    # Recursively collect all descendants
    def get_descendants(mendel_id, collected):
        children_ids = parent_to_children.get(mendel_id, [])
        for child_id in children_ids:
            if child_id not in collected:
                collected.add(child_id)
                get_descendants(child_id, collected)
        return collected

    collected_ids = set()
    get_descendants(mendel_id, collected_ids)

    # Collect Mendel_IDs and Labels
    children = []
    for mendel_id in collected_ids:
        class_node = mendel_id_to_node.get(mendel_id)
        if class_node is not None:
            label_elem = class_node.find(f".//{{{ns_rdfs}}}label")
            label_text = label_elem.text.strip() if label_elem is not None and label_elem.text else 'No label'
            children.append((mendel_id, label_text, f"{label_text}::{mendel_id}"))

    return children

# Function to extract parents supporting multiple inheritance
def extract_parents(root, mendel_id):
    # Namespace URIs
    ns_owl = 'http://www.w3.org/2002/07/owl#'
    ns_rdf = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
    ns_rdfs = 'http://www.w3.org/2000/01/rdf-schema#'

    # Maps to store Mendel IDs and child-parent relationships
    mendel_id_to_node = {}
    child_to_parents = {}

    # Build a mapping from node about attributes to Mendel IDs
    about_to_mendel_id = {}

    # First pass: Build mappings
    for class_node in root.findall(f".//{{{ns_owl}}}Class"):
        # Get the about attribute
        about = class_node.get(f"{{{ns_rdf}}}about")
        if not about:
            continue

        # Find the Mendel_ID element
        mendel_id_elem = class_node.find(f".//{{*}}Mendel_ID")
        if mendel_id_elem is not None and mendel_id_elem.text:
            mendel_id_text = mendel_id_elem.text.strip()
            mendel_id_to_node[mendel_id_text] = class_node
            about_to_mendel_id[about] = mendel_id_text

    # Second pass: Build child-parent relationships
    for class_node in mendel_id_to_node.values():
        mendel_id_elem = class_node.find(f".//{{*}}Mendel_ID")
        if mendel_id_elem is not None and mendel_id_elem.text:
            child_mendel_id = mendel_id_elem.text.strip()

            # Find subClassOf elements
            for subclass_elem in class_node.findall(f"./{{{ns_rdfs}}}subClassOf"):
                parent_resource = subclass_elem.get(f"{{{ns_rdf}}}resource")
                if parent_resource and parent_resource in about_to_mendel_id:
                    parent_mendel_id = about_to_mendel_id[parent_resource]
                    child_to_parents.setdefault(child_mendel_id, []).append(parent_mendel_id)

    # Recursively collect all ancestor paths
    def get_ancestor_paths(current_id, current_path, all_paths, visited):
        if current_id in visited:
            return
        visited.add(current_id)
        parents = child_to_parents.get(current_id, [])
        if not parents:
            # Reached a root
            all_paths.append(current_path.copy())
        else:
            for parent_id in parents:
                current_path.append((parent_id))
                get_ancestor_paths(parent_id, current_path, all_paths, visited)
                current_path.pop()
        visited.remove(current_id)

    all_paths = []
    visited = set()
    get_ancestor_paths(mendel_id, [], all_paths, visited)

    # Collect Mendel_IDs, Labels, and Levels
    parents = []
    for path in all_paths:
        # path is a list of Mendel IDs from the child up to a root
        # Reverse it to get from root to child
        path = path[::-1]
        for level, mendel_id in enumerate(path):
            class_node = mendel_id_to_node.get(mendel_id)
            if class_node is not None:
                label_elem = class_node.find(f".//{{{ns_rdfs}}}label")
                label_text = label_elem.text.strip() if label_elem is not None and label_elem.text else 'No label'
                parents.append((mendel_id, label_text, f"{label_text}::{mendel_id}", level))

    # Remove duplicates while preserving order
    seen = set()
    unique_parents = []
    for item in parents:
        if item[0] not in seen:
            seen.add(item[0])
            unique_parents.append(item)

    return unique_parents

# Sidebar for file upload and selection
with st.sidebar:
    uploaded_file = st.file_uploader("Upload a ZIP file containing the OWL file", type="zip")
    if uploaded_file is not None:
        with zipfile.ZipFile(uploaded_file, 'r') as z:
            for filename in z.namelist():
                if filename.endswith('.owl'):
                    z.extract(filename, UPLOAD_DIR)
                    st.success(f'OWL file "{filename}" has been uploaded and saved.')
                    break
            else:
                st.error("No OWL file found in the ZIP archive.")
    
    saved_files = [f for f in os.listdir(UPLOAD_DIR) if f.endswith('.owl')]
    selected_file = st.selectbox("Select a saved OWL file", saved_files)

# Main layout
st.header("Extract Children from OWL File")

st.subheader("Extract Children")
branch_root_ids_input = st.text_input("Enter Root Mendel ID(s) for Children Extraction (separated by '||')")

if st.button('Extract Children'):
    if branch_root_ids_input and selected_file:
        # Parse the input into a list of Mendel IDs
        branch_root_ids = [mid.strip() for mid in branch_root_ids_input.split('||') if mid.strip()]
        owl_file_path = os.path.join(UPLOAD_DIR, selected_file)

        try:
            # Parse the OWL file once
            tree = etree.parse(owl_file_path)
            root = tree.getroot()

            all_branch_data = []
            for branch_root_id in branch_root_ids:
                # Extract the children for each Mendel ID
                branch_data = extract_children(root, branch_root_id)
                if branch_data:
                    # Add the root Mendel ID to each result
                    for data in branch_data:
                        # data is (mendel_id, label, label::mendel_id)
                        all_branch_data.append((branch_root_id, data[0], data[1], data[2]))
                else:
                    st.warning(f"No data extracted for the given Root Mendel ID: {branch_root_id}")
            if all_branch_data:
                branch_df = pd.DataFrame(all_branch_data, columns=["Root Mendel ID", "Mendel ID", "Label", "Label::Mendel ID"])
                st.write("Extracted Children:")
                st.dataframe(branch_df)

                # Option to download the DataFrame as CSV
                csv = branch_df.to_csv(index=False).encode('utf-8')
                st.download_button("Download CSV", data=csv, file_name='extracted_children.csv', mime='text/csv')

                # Prepare the output string in the desired format
                label_mendel_id_list = branch_df['Label::Mendel ID'].tolist()
                output_string = 'Concept Dropdown {' + '||'.join(label_mendel_id_list) + '}'

                # Display in text area
                st.text_area("Editable Output", value=output_string, height=200)
            else:
                st.warning("No data extracted for the given Root Mendel IDs.")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
    else:
        st.error("Please enter Mendel ID(s) and select an OWL file.")

st.header("Extract Parents from OWL File")

st.subheader("Extract Parents")
parent_root_ids_input = st.text_input("Enter Mendel ID(s) for Parents Extraction (separated by '||')")

if st.button('Extract Parents'):
    if parent_root_ids_input and selected_file:
        # Parse the input into a list of Mendel IDs
        parent_root_ids = [mid.strip() for mid in parent_root_ids_input.split('||') if mid.strip()]
        owl_file_path = os.path.join(UPLOAD_DIR, selected_file)

        try:
            # Parse the OWL file once
            tree = etree.parse(owl_file_path)
            root = tree.getroot()

            all_parent_data = []
            for parent_root_id in parent_root_ids:
                # Extract the parents for each Mendel ID
                parent_data = extract_parents(root, parent_root_id)
                if parent_data:
                    # Add the root Mendel ID to each result
                    for data in parent_data:
                        # data is (mendel_id, label, label::mendel_id, level)
                        all_parent_data.append((parent_root_id, data[0], data[1], data[2], data[3]))
                else:
                    st.warning(f"No parents found for the given Mendel ID: {parent_root_id}")
            if all_parent_data:
                parent_df = pd.DataFrame(all_parent_data, columns=["Root Mendel ID", "Mendel ID", "Label", "Label::Mendel ID", "Level"])

                # Create an indented label to represent hierarchy
                parent_df['Indented Label'] = parent_df.apply(
                    lambda row: ('--' * row['Level']) + '> ' + row['Label'], axis=1
                )
                parent_df['Indented Label::Mendel ID'] = parent_df['Indented Label'] + '::' + parent_df['Mendel ID']

                st.write("Extracted Parents (Including Multiple Inheritance):")
                st.dataframe(parent_df[["Root Mendel ID", "Mendel ID", "Indented Label", "Label::Mendel ID", "Level"]])

                # Option to download the DataFrame as CSV
                csv = parent_df.to_csv(index=False).encode('utf-8')
                st.download_button("Download CSV", data=csv, file_name='extracted_parents.csv', mime='text/csv')

                # Prepare the output string in the desired format
                label_mendel_id_list = parent_df['Indented Label::Mendel ID'].tolist()
                output_string = 'Concept Dropdown {' + '||'.join(label_mendel_id_list) + '}'

                # Display in text area
                st.text_area("Editable Output", value=output_string, height=200)
            else:
                st.warning("No parents found for the given Mendel IDs.")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
    else:
        st.error("Please enter Mendel ID(s) and select an OWL file.")
