import os
import zipfile
import pandas as pd
from lxml import etree
import streamlit as st

# Directory to save the uploaded OWL files
UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

st.set_page_config(page_title="NCIt OWL", layout="wide")
st.title('NCIt OWL Branch Extractor')

def parse_and_find_all_properties(owl_file_path):
   
    parser = etree.XMLParser(remove_blank_text=True, huge_tree=True)
    tree = etree.parse(owl_file_path, parser=parser)
    root = tree.getroot()

    ns_owl = 'http://www.w3.org/2002/07/owl#'
    all_properties = set()

    # Step 1: Gather <owl:AnnotationProperty> -> label
    annotation_prop_label_map = {}
    for annot_node in root.findall(f".//{{{ns_owl}}}AnnotationProperty"):
        about_attr = annot_node.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about")
        if not about_attr:
            continue
        local_name = about_attr.split('#')[-1]  # e.g. 'A10', 'P90'
        label_elem = annot_node.find(f".//{{*}}label")
        if label_elem is not None and label_elem.text:
            annotation_prop_label_map[local_name] = label_elem.text.strip()
        else:
            annotation_prop_label_map[local_name] = local_name

    # Step 2: Collect property tags from <owl:Class>
    for class_node in root.findall(f".//{{{ns_owl}}}Class"):
        for elem in class_node:
            # skip structural tags like subClassOf, label, or nested <owl:Class>
            if '}' in elem.tag:
                tag_local = elem.tag.split('}', 1)[1]
                if tag_local not in ('subClassOf', 'label'):
                    all_properties.add(tag_local)

    return sorted(all_properties), annotation_prop_label_map, root

def extract_children(root, cui_id, selected_props, prop_label_map):
    
    ns_owl = 'http://www.w3.org/2002/07/owl#'
    ns_rdf = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
    ns_rdfs = 'http://www.w3.org/2000/01/rdf-schema#'

    cui_to_node = {}
    parent_to_children = {}
    about_to_cui = {}

    # 1. Build mappings from owl:Class
    for class_node in root.findall(f".//{{{ns_owl}}}Class"):
        about = class_node.get(f"{{{ns_rdf}}}about")
        if not about:
            continue
        cui_elem = class_node.find(f".//{{*}}NHC0")
        if cui_elem is not None and cui_elem.text:
            concept_id_text = cui_elem.text.strip()
            cui_to_node[concept_id_text] = class_node
            about_to_cui[about] = concept_id_text

    # 2. Build parent->children relationships
    for concept_id_text, class_node in cui_to_node.items():
        for subclass_elem in class_node.findall(f"./{{{ns_rdfs}}}subClassOf"):
            parent_resource = subclass_elem.get(f"{{{ns_rdf}}}resource")
            if parent_resource and parent_resource in about_to_cui:
                parent_cui = about_to_cui[parent_resource]
                parent_to_children.setdefault(parent_cui, []).append(concept_id_text)

    # 3. Recursively find all descendants of cui_id
    def get_descendants(cui_id_input, collected):
        children_ids = parent_to_children.get(cui_id_input, [])
        for child_id in children_ids:
            if child_id not in collected:
                collected.add(child_id)
                get_descendants(child_id, collected)
        return collected

    collected_ids = set()
    get_descendants(cui_id, collected_ids)

    results = []
    # For each descendant, retrieve rdfs:label + Galal-selected property codes
    for descendant_cui in collected_ids:
        class_node = cui_to_node.get(descendant_cui)
        if class_node is not None:
            # Attempt to retrieve rdfs:label
            label_elem = class_node.find(f".//{{{ns_rdfs}}}label")
            label_text = label_elem.text.strip() if label_elem is not None and label_elem.text else "No label"

            # Gather the requested properties
            prop_values = {}
            for prop in selected_props:
                found_elems = class_node.findall(f".//{{*}}{prop}")
                if found_elems:
                    joined_text = "; ".join(elem.text.strip() for elem in found_elems if elem.text)
                else:
                    joined_text = ""
                prop_values[prop] = joined_text

            # row_data: [descendant_cui, label_text, propVal1, propVal2, ...]
            row_data = [descendant_cui, label_text]
            for prop in selected_props:
                row_data.append(prop_values[prop])

            results.append(row_data)

    return results

#################################
# Sidebar
#################################
with st.sidebar:
    uploaded_file = st.file_uploader("Upload a ZIP file containing the OWL file", type="zip")
    if uploaded_file is not None:
        with zipfile.ZipFile(uploaded_file, 'r') as z:
            for filename in z.namelist():
                if filename.endswith('.owl'):
                    z.extract(filename, UPLOAD_DIR)
                    st.success(f'OWL file \"{filename}\" has been uploaded and saved.')
                    break
            else:
                st.error("No OWL file found in the ZIP archive.")

    saved_files = [f for f in os.listdir(UPLOAD_DIR) if f.endswith('.owl')]
    selected_file = st.selectbox("Select a saved OWL file", saved_files)

#################################
# Main layout: Extract Children
#################################
st.header("Extract Children from NCIt OWL File")

if selected_file:
    owl_file_path = os.path.join(UPLOAD_DIR, selected_file)
    try:
        # Step 1: parse entire file, gather property codes + their label
        all_props, annotation_prop_label_map, root = parse_and_find_all_properties(owl_file_path)
        
        # Build a display for the multi-select with human-readable label
        display_to_code = {}
        for code in all_props:
            human_label = annotation_prop_label_map.get(code, code)
            display_str = f"{human_label} ({code})"
            display_to_code[display_str] = code
        
        selected_display_props = st.multiselect(
            "Select which properties to include in the output:",
            sorted(display_to_code.keys())
        )
        
        # Convert them back to raw codes
        selected_props = [display_to_code[d] for d in selected_display_props]

    except Exception as e:
        st.error(f"Error parsing/handling the OWL file: {e}")
        selected_props = []
else:
    selected_props = []

cui_input = st.text_input(
    "Enter NCIt concept ID(s) (e.g. C162078), separated by '||'",
    key="extract_children_input"
)

if st.button('Extract Children'):
    if cui_input and selected_file and selected_props:
        cui_list = [c.strip() for c in cui_input.split('||') if c.strip()]
        owl_file_path = os.path.join(UPLOAD_DIR, selected_file)
        try:
            parser = etree.XMLParser(remove_blank_text=True, huge_tree=True)
            tree = etree.parse(owl_file_path, parser=parser)
            root = tree.getroot()

            all_data = []
            for cui in cui_list:
                children_data = extract_children(root, cui, selected_props, annotation_prop_label_map)
                if children_data:
                    # For each row in children_data, prepend the root cui
                    for row in children_data:
                        # row = [descendant_cui, label, propVal1, propVal2, ...]
                        root_cui = cui
                        new_row = [root_cui] + row
                        all_data.append(new_row)
                else:
                    st.warning(f"No children found for concept: {cui}")

            if all_data:
                # First two columns:
                #  - Root NCIt Concept
                #  - Child CUI
                #  - Child Label
                base_cols = ["Root NCIt Concept", "Child NCIt code", "Child Label"]
                
                
                col_labels = []
                for code in selected_props:
                    col_labels.append(annotation_prop_label_map.get(code, code))
                
                final_cols = base_cols + col_labels
                df = pd.DataFrame(all_data, columns=final_cols)
                
                st.write("Extracted Children + Selected Properties:")
                st.dataframe(df)

                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button("Download CSV", data=csv_data, file_name='ncit_children.csv', mime='text/csv')
            else:
                st.warning("No data extracted from the provided NCIt concepts.")

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
    else:
        st.error("Please enter NCIt concept ID(s), select an OWL file, and choose properties.")
