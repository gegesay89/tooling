import os
import zipfile
import pandas as pd
from lxml import etree
import streamlit as st
from collections import defaultdict

UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

st.set_page_config(page_title="OWL Extractor", layout="wide")
st.title('OWL Children and Parents Extractor')

# We'll build a single structure to hold all relevant data
class OwlData:
    def __init__(self):
        # Maps the original 'about' attribute -> mendel_id
        self.about_to_mendel_id = {}
        # Maps each mendel_id -> label
        self.mendel_id_to_label = {}
        # Child -> set of parents (store as sets to handle duplicates)
        self.child_to_parents = defaultdict(set)
        # Parent -> set of children
        self.parent_to_children = defaultdict(set)

# Use cache to avoid re-parsing multiple times if the same file is selected again
@st.cache_data(show_spinner=False)
def parse_owl_file(owl_file_path):
    ns_owl = 'http://www.w3.org/2002/07/owl#'
    ns_rdf = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
    ns_rdfs = 'http://www.w3.org/2000/01/rdf-schema#'

    data = OwlData()
    child_about_to_parents = defaultdict(set)

    # First pass (iterparse) to collect about->mendel_id, label, and immediate subClassOf references
    context = etree.iterparse(owl_file_path, events=('end',), tag=f"{{{ns_owl}}}Class")
    for event, class_element in context:
        about = class_element.get(f"{{{ns_rdf}}}about")
        if about:
            # Extract mendel_id
            mendel_id_elem = class_element.find(f".//{{*}}Mendel_ID")
            if mendel_id_elem is not None and mendel_id_elem.text:
                mendel_id = mendel_id_elem.text.strip()
                data.about_to_mendel_id[about] = mendel_id

                # Extract label
                label_elem = class_element.find(f".//{{{ns_rdfs}}}label")
                label = (label_elem.text.strip() if label_elem is not None and label_elem.text else 'No label')
                data.mendel_id_to_label[mendel_id] = label

                # Collect parent about references from subClassOf
                for subclass_elem in class_element.findall(f"./{{{ns_rdfs}}}subClassOf"):
                    parent_resource = subclass_elem.get(f"{{{ns_rdf}}}resource")
                    if parent_resource:
                        child_about_to_parents[about].add(parent_resource)

        # Clear from memory
        class_element.clear()
        while class_element.getprevious() is not None:
            del class_element.getparent()[0]

    # Second pass: Convert about references to actual mendel_ids
    for child_about, parent_abouts in child_about_to_parents.items():
        child_id = data.about_to_mendel_id.get(child_about)
        if not child_id:
            continue
        for p_about in parent_abouts:
            parent_id = data.about_to_mendel_id.get(p_about)
            if parent_id:
                data.child_to_parents[child_id].add(parent_id)
                data.parent_to_children[parent_id].add(child_id)

    return data

def extract_children(data, root_mendel_id):
    """Recursively find all descendants of a root_mendel_id."""
    visited = set()
    result_ids = set()

    def dfs(m_id):
        if m_id in visited:
            return
        visited.add(m_id)
        for child_id in data.parent_to_children.get(m_id, []):
            if child_id not in result_ids:
                result_ids.add(child_id)
                dfs(child_id)

    dfs(root_mendel_id)

    # Build (mendel_id, label, label::mendel_id) for each child
    children_info = []
    for cid in result_ids:
        lbl = data.mendel_id_to_label.get(cid, 'No label')
        children_info.append((cid, lbl, f"{lbl}::{cid}"))
    return children_info

def extract_parents(data, root_mendel_id):
    """Find all ancestor paths of a root_mendel_id (handling multiple inheritance)."""
    all_paths = []
    visited = set()

    def backtrack(current_id, path):
        if current_id in visited:
            return
        visited.add(current_id)

        parents = data.child_to_parents.get(current_id, [])
        if not parents:
            # Found a root
            all_paths.append(path[:])
        else:
            for p_id in parents:
                path.append(p_id)
                backtrack(p_id, path)
                path.pop()

        visited.remove(current_id)

    backtrack(root_mendel_id, [])

    # Build (mendel_id, label, label::mendel_id, level) for each ancestor in each path
    parent_list = []
    for path in all_paths:
        rev_path = path[::-1]  # reverse so that the top-level parent is first
        for level, mid in enumerate(rev_path):
            lbl = data.mendel_id_to_label.get(mid, 'No label')
            parent_list.append((mid, lbl, f"{lbl}::{mid}", level))

    # Remove duplicates while preserving order
    seen = set()
    unique_parents = []
    for mid, lbl, label_mid, lvl in parent_list:
        if mid not in seen:
            seen.add(mid)
            unique_parents.append((mid, lbl, label_mid, lvl))

    return unique_parents

# -------------------- STREAMLIT APP --------------------
with st.sidebar:
    uploaded_file = st.file_uploader("Upload a ZIP file containing the OWL file", type="zip")
    if uploaded_file is not None:
        with zipfile.ZipFile(uploaded_file, 'r') as z:
            file_extracted = False
            for filename in z.namelist():
                if filename.endswith('.owl'):
                    z.extract(filename, UPLOAD_DIR)
                    st.success(f'OWL file "{filename}" has been uploaded and saved.')
                    file_extracted = True
                    break
            if not file_extracted:
                st.error("No OWL file found in the ZIP archive.")

    saved_files = [f for f in os.listdir(UPLOAD_DIR) if f.endswith('.owl')]
    selected_file = st.selectbox("Select a saved OWL file", saved_files)

st.header("Extract Children from OWL File")
st.subheader("Extract Children")
branch_root_ids_input = st.text_input("Enter Root Mendel ID(s) for Children Extraction (separated by '||')")

if st.button('Extract Children'):
    if branch_root_ids_input and selected_file:
        root_ids = [m.strip() for m in branch_root_ids_input.split('||') if m.strip()]
        owl_file_path = os.path.join(UPLOAD_DIR, selected_file)

        try:
            data = parse_owl_file(owl_file_path)

            # We'll accumulate concept dropdown lines for each root ID
            child_dropdowns = []

            for rid in root_ids:
                children = extract_children(data, rid)
                if children:
                    # Build a DataFrame specifically for this root ID
                    columns = ["Root Mendel ID", "Mendel ID", "Label", "Label::Mendel ID"]
                    child_records = []
                    for child_id, child_label, child_label_mid in children:
                        child_records.append((rid, child_id, child_label, child_label_mid))

                    branch_df = pd.DataFrame(child_records, columns=columns)
                    st.markdown(f"### Extracted Children for: {rid}")
                    st.dataframe(branch_df)

                    csv_data = branch_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        f"Download CSV for {rid}",
                        data=csv_data,
                        file_name=f'extracted_children_{rid}.csv',
                        mime='text/csv'
                    )

                    label_mid_list = branch_df['Label::Mendel ID'].tolist()
                    concept_line = 'Concept Dropdown {' + '||'.join(label_mid_list) + '}'
                    child_dropdowns.append(concept_line)
                else:
                    st.warning(f"No children found for root Mendel ID: {rid}")

            # Show all child dropdown lines, each on its own line
            if child_dropdowns:
                final_child_output = "\n".join(child_dropdowns)
                st.text_area(
                    "Combined Concept Dropdowns for Children",
                    value=final_child_output,
                    height=200
                )
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
        parent_ids = [m.strip() for m in parent_root_ids_input.split('||') if m.strip()]
        owl_file_path = os.path.join(UPLOAD_DIR, selected_file)

        try:
            data = parse_owl_file(owl_file_path)

            parent_dropdowns = []

            for pid in parent_ids:
                results = extract_parents(data, pid)
                if results:
                    columns = ["Root Mendel ID", "Mendel ID", "Label", "Label::Mendel ID", "Level"]
                    parent_records = []
                    for mid, lbl, lbl_mid, lvl in results:
                        parent_records.append((pid, mid, lbl, lbl_mid, lvl))

                    parent_df = pd.DataFrame(parent_records, columns=columns)
                    # Create an indented label column
                    parent_df['Indented Label'] = parent_df.apply(
                        lambda row: ('--' * row['Level']) + '> ' + row['Label'],
                        axis=1
                    )
                    parent_df['Indented Label::Mendel ID'] = (
                        parent_df['Indented Label'] + '::' + parent_df['Mendel ID']
                    )

                    st.markdown(f"### Extracted Parents for: {pid}")
                    display_cols = ["Root Mendel ID", "Mendel ID", "Indented Label", "Label::Mendel ID", "Level"]
                    st.dataframe(parent_df[display_cols])

                    csv_data = parent_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        f"Download CSV for {pid}",
                        data=csv_data,
                        file_name=f'extracted_parents_{pid}.csv',
                        mime='text/csv'
                    )

                    indent_label_mid_list = parent_df['Indented Label::Mendel ID'].tolist()
                    concept_line = 'Concept Dropdown {' + '||'.join(indent_label_mid_list) + '}'
                    parent_dropdowns.append(concept_line)
                else:
                    st.warning(f"No parents found for: {pid}")

            if parent_dropdowns:
                final_parent_output = "\n".join(parent_dropdowns)
                st.text_area(
                    "Combined Concept Dropdowns for Parents",
                    value=final_parent_output,
                    height=200
                )
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
    else:
        st.error("Please enter Mendel ID(s) and select an OWL file.")
