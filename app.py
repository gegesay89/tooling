import os
import zipfile
import pandas as pd
from lxml import etree
import io
import streamlit as st
import re

# Directory to save the uploaded OWL files
UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

st.set_page_config(page_title="OCD", layout="wide")
st.title("Ontology Concepts Designer (OCD)")

# This constant determines how often (in # of rows) we update the UI elements
UPDATE_INTERVAL = 100  

########################################
# Part 1: Add New Classes
########################################
def add_new_classes(owl_zip_file, excel_file, output_file_name):
    st.write("Add New Classes to Ontology")
    with st.spinner('Processing...'):
        try:
            with zipfile.ZipFile(owl_zip_file) as z:
                owl_filenames = [name for name in z.namelist() if name.endswith('.owl') or name.endswith('.xml')]
                if not owl_filenames:
                    st.error("No OWL file found in the ZIP archive.")
                    return
                owl_filename = owl_filenames[0]
                with z.open(owl_filename) as owl_content:
                    progress_bar = st.progress(0)
                    log_placeholder = st.empty()
                    output = process_add_new_classes(owl_content, excel_file, progress_bar, log_placeholder)
            st.success('Ontology modification completed.')
            st.download_button(
                label="Download Modified OWL File",
                data=output,
                file_name=output_file_name,
                mime='application/rdf+xml'
            )
        except zipfile.BadZipFile:
            st.error("The uploaded file is not a valid ZIP file.")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

def process_add_new_classes(owl_content, excel_content, progress_bar, log_placeholder):
    # A helper function to remove/replace any special characters in the label, 
    # leaving only letters, numbers, and underscores.
    def sanitize_label(raw_label):
        # Remove all non-alphanumeric or underscore characters
        sanitized = re.sub(r'[^a-zA-Z0-9_]+', '', raw_label)
        return sanitized

    logs = []
    df = pd.read_excel(excel_content)
    
    # Parse OWL
    tree = etree.parse(owl_content)
    root = tree.getroot()
    
    ns = {
        'owl': 'http://www.w3.org/2002/07/owl#',
        'owl0': 'http://www.w3.org/2002/07/owl#',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'www': 'http://www.w3.org/2002/07/',
        'xml': 'http://www.w3.org/XML/1998/namespace',
        'xsd': 'http://www.w3.org/2001/XMLSchema#',
        'amr': 'http://www.semanticweb.org/amr/ontologies/2018/'
    }
    etree.register_namespace('xml', ns['xml'])
    
    optional_props = ['Code', 'Synonyms', 'Mendel_ID']

    total_rows = len(df)
    log_text = ''
    log_placeholder.text_area("Processing Logs", value=log_text, height=200)

    for index, row in df.iterrows():
        # Update progress bar periodically for performance
        if index % UPDATE_INTERVAL == 0 or index == total_rows - 1:
            progress_bar.progress((index + 1) / total_rows)

        parent_uri = f"http://www.semanticweb.org/amr/ontologies/2018/{row['Parent']}"
        label_raw = row.get('Label', None)
        label = str(label_raw).strip() if pd.notna(label_raw) and str(label_raw).strip() != '' else None

        # Check if label has newline => warn
        if label and ("\n" in label or "\r" in label):
            st.warning(f"Row {index+1}: Label '{label}' contains newline(s). This might cause issues.")

        if label:
            # Sanitize the label for IRI
            sanitized_label = sanitize_label(label)

            new_class = etree.Element('{http://www.semanticweb.org/amr/ontologies/2018/}Class', nsmap=ns)
            # Use only the sanitized label in the IRI
            new_class.set('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about',
                          f"http://www.co-ode.org/ontologies/ont.owl#{sanitized_label}")

            subclass_of = etree.SubElement(new_class, '{http://www.w3.org/2000/01/rdf-schema#}subClassOf', nsmap=ns)
            subclass_of.set('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource', parent_uri)

            label_elem = etree.SubElement(new_class,
                                          '{http://www.w3.org/2000/01/rdf-schema#}label',
                                          {'{http://www.w3.org/XML/1998/namespace}lang': 'en'},
                                          nsmap=ns)
            label_elem.text = label

            # Add optional props
            for prop in optional_props:
                if prop in df.columns:
                    value_raw = row.get(prop, None)
                    value_str = str(value_raw).strip() if pd.notna(value_raw) and str(value_raw).strip() != '' else None
                    if value_str:
                        prop_elem = etree.SubElement(new_class, prop, nsmap=ns)
                        prop_elem.text = value_str

            # Add UMLS_CUI same as label
            umls_cui_elem = etree.SubElement(new_class, 'UMLS_CUI', nsmap=ns)
            umls_cui_elem.text = label

            root.append(new_class)

            log_message = f"Added new class for '{label}' (IRI: #{sanitized_label}) under parent '{row['Parent']}'."
            logs.append(log_message)
        else:
            log_message = f"Skipped row {index + 1}: Label is missing."
            logs.append(log_message)

        # Periodically (or at end) update the log text area with the last X lines
        if index % UPDATE_INTERVAL == 0 or index == total_rows - 1:
            log_text = '\n'.join(logs[-200:])
            log_placeholder.text_area("Processing Logs", value=log_text, height=200)
    
    output = io.BytesIO()
    tree.write(output, pretty_print=True, xml_declaration=True, encoding='UTF-8', method="xml")
    output.seek(0)
    return output

########################################
# Part 2: Update Codes
########################################
def update_codes_in_ontology(owl_zip_file, excel_file, output_file_name):
    st.write("Update Codes in Ontology")
    with st.spinner('Processing...'):
        try:
            with zipfile.ZipFile(owl_zip_file) as z:
                owl_filenames = [name for name in z.namelist() if name.endswith('.owl') or name.endswith('.xml')]
                if not owl_filenames:
                    st.error("No OWL file found in the ZIP archive.")
                    return
                owl_filename = owl_filenames[0]
                with z.open(owl_filename) as owl_content:
                    progress_bar = st.progress(0)
                    log_placeholder = st.empty()
                    output = process_update_codes(owl_content, excel_file, progress_bar, log_placeholder)
            st.success('Ontology codes update completed.')
            st.download_button(
                label="Download Modified OWL File",
                data=output,
                file_name=output_file_name,
                mime='application/rdf+xml'
            )
        except zipfile.BadZipFile:
            st.error("The uploaded file is not a valid ZIP file.")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

def process_update_codes(owl_content, excel_content, progress_bar, log_placeholder):
    logs = []
    df = pd.read_excel(excel_content)
    df = df[['Mendel ID', 'Codes']]
    df = df.dropna(subset=['Mendel ID'])
    df.columns = df.columns.str.strip()

    def format_mendel_id(x):
        if pd.isnull(x):
            return ''
        elif isinstance(x, float):
            return str(int(x)) if x.is_integer() else str(x)
        else:
            return str(x).strip()

    df['Mendel ID'] = df['Mendel ID'].apply(format_mendel_id)
    df['Codes'] = df['Codes'].fillna('').astype(str).str.strip()

    mendel_id_to_codes = df.groupby('Mendel ID')['Codes'].apply(list).to_dict()

    tree = etree.parse(owl_content)
    root = tree.getroot()

    namespaces = {
        'owl': 'http://www.w3.org/2002/07/owl#',
        'owl0': 'http://www.w3.org/2002/07/owl#',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'www': 'http://www.w3.org/2002/07/',
        'xml': 'http://www.w3.org/XML/1998/namespace',
        'xsd': 'http://www.w3.org/2001/XMLSchema#',
        'amr': 'http://www.semanticweb.org/amr/ontologies/2018/',
    }
    classes = root.xpath('//owl0:Class', namespaces=namespaces)

    total_classes = len(classes)
    log_text = ''
    log_placeholder.text_area("Processing Logs", value=log_text, height=200)

    for index, cls in enumerate(classes):
        # Update progress bar periodically
        if index % UPDATE_INTERVAL == 0 or index == total_classes - 1:
            progress_bar.progress((index + 1) / total_classes)

        mendel_id_elems = cls.xpath('.//owl0:Mendel_ID', namespaces=namespaces)
        if not mendel_id_elems:
            # fallback
            mendel_id_elems = cls.xpath('.//*[local-name()="Mendel_ID"]')

        if mendel_id_elems:
            mendel_id = mendel_id_elems[0].text.strip()
            if mendel_id in mendel_id_to_codes:
                codes_list = mendel_id_to_codes[mendel_id]
                codes_elems = cls.xpath('.//owl0:Codes', namespaces=namespaces)
                if not codes_elems:
                    codes_elems = cls.xpath('.//*[local-name()="Codes"]')

                if codes_elems:
                    codes_elem = codes_elems[0]
                    existing_codes_text = codes_elem.text or ''
                    existing_codes = [code.strip() for code in existing_codes_text.split('\n') if code.strip()]
                    combined_codes = set(existing_codes) | set(codes_list)
                    codes_elem.text = '\n'.join(sorted(combined_codes))
                    log_message = f"Updated codes for Mendel ID {mendel_id}: {combined_codes}"
                else:
                    codes_elem = etree.SubElement(cls, '{%s}Codes' % namespaces['owl0'])
                    combined_codes = set(codes_list)
                    codes_elem.text = '\n'.join(sorted(combined_codes))
                    log_message = f"Added new Codes element for Mendel ID {mendel_id}: {combined_codes}"

                logs.append(log_message)

        # Periodically (or at end) update the log text area
        if index % UPDATE_INTERVAL == 0 or index == total_classes - 1:
            log_text = '\n'.join(logs[-200:])
            log_placeholder.text_area("Processing Logs", value=log_text, height=200)

    output = io.BytesIO()
    tree.write(output, pretty_print=True, xml_declaration=True, encoding='UTF-8', method="xml")
    output.seek(0)
    return output

########################################
# Part 3: Update Synonyms
########################################
def update_synonyms_in_ontology(owl_zip_file, excel_file, output_file_name):
    st.write("Update Synonyms in Ontology")
    with st.spinner('Processing...'):
        try:
            with zipfile.ZipFile(owl_zip_file) as z:
                owl_filenames = [name for name in z.namelist() if name.endswith('.owl') or name.endswith('.xml')]
                if not owl_filenames:
                    st.error("No OWL file found in the ZIP archive.")
                    return
                owl_filename = owl_filenames[0]
                with z.open(owl_filename) as owl_content:
                    progress_bar = st.progress(0)
                    log_placeholder = st.empty()
                    output = process_update_synonyms(owl_content, excel_file, progress_bar, log_placeholder)
            st.success('Ontology synonyms update completed.')
            st.download_button(
                label="Download Modified OWL File",
                data=output,
                file_name=output_file_name,
                mime='application/rdf+xml'
            )
        except zipfile.BadZipFile:
            st.error("The uploaded file is not a valid ZIP file.")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

def process_update_synonyms(owl_content, excel_content, progress_bar, log_placeholder):
    logs = []

    df = pd.read_excel(excel_content)
    df = df[['Mendel ID', 'Synonyms']]
    df = df.dropna(subset=['Mendel ID'])
    df.columns = df.columns.str.strip()

    def format_mendel_id(x):
        if pd.isnull(x):
            return ''
        elif isinstance(x, float):
            return str(int(x)) if x.is_integer() else str(x)
        else:
            return str(x).strip()

    df['Mendel ID'] = df['Mendel ID'].apply(format_mendel_id)
    df['Synonyms'] = df['Synonyms'].fillna('').astype(str).str.strip()

    mendel_id_to_synonyms = df.groupby('Mendel ID')['Synonyms'].apply(list).to_dict()

    tree = etree.parse(owl_content)
    root = tree.getroot()

    namespaces = {
        'owl': 'http://www.w3.org/2002/07/owl#',
        'owl0': 'http://www.w3.org/2002/07/owl#',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'www': 'http://www.w3.org/2002/07/',
        'xml': 'http://www.w3.org/XML/1998/namespace',
        'xsd': 'http://www.w3.org/2001/XMLSchema#',
        'amr': 'http://www.semanticweb.org/amr/ontologies/2018/',
    }

    classes = root.xpath('//owl0:Class', namespaces=namespaces)

    total_classes = len(classes)
    log_text = ''
    log_placeholder.text_area("Processing Logs", value=log_text, height=200)

    for index, cls in enumerate(classes):
        # Update progress bar periodically
        if index % UPDATE_INTERVAL == 0 or index == total_classes - 1:
            progress_bar.progress((index + 1) / total_classes)

        mendel_id_elems = cls.xpath('.//owl0:Mendel_ID', namespaces=namespaces)
        if not mendel_id_elems:
            mendel_id_elems = cls.xpath('.//*[local-name()="Mendel_ID"]')

        if mendel_id_elems:
            mendel_id_val = mendel_id_elems[0].text.strip()
            if mendel_id_val in mendel_id_to_synonyms:
                synonyms_list = mendel_id_to_synonyms[mendel_id_val]
                synonyms_elems = cls.xpath('.//owl0:Synonyms', namespaces=namespaces)
                if not synonyms_elems:
                    synonyms_elems = cls.xpath('.//*[local-name()="Synonyms"]')

                if synonyms_elems:
                    synonyms_elem = synonyms_elems[0]
                    existing_synonyms_text = synonyms_elem.text or ''
                    existing_synonyms = [syn.strip() for syn in existing_synonyms_text.split('\n') if syn.strip()]
                    combined_synonyms = set(existing_synonyms) | set(synonyms_list)
                    synonyms_elem.text = '\n'.join(sorted(combined_synonyms))
                    log_message = f"Updated synonyms for Mendel ID {mendel_id_val}: {combined_synonyms}"
                else:
                    synonyms_elem = etree.SubElement(cls, '{%s}Synonyms' % namespaces['owl0'])
                    combined_synonyms = set(synonyms_list)
                    synonyms_elem.text = '\n'.join(sorted(combined_synonyms))
                    log_message = f"Added new Synonyms element for Mendel ID {mendel_id_val}: {combined_synonyms}"

                logs.append(log_message)

        # Periodically (or at end) update the text area
        if index % UPDATE_INTERVAL == 0 or index == total_classes - 1:
            log_text = '\n'.join(logs[-200:])
            log_placeholder.text_area("Processing Logs", value=log_text, height=200)

    output = io.BytesIO()
    tree.write(output, pretty_print=True, xml_declaration=True, encoding='UTF-8', method="xml")
    output.seek(0)
    return output

########################################
# Part 4: Remove Codes or Synonyms
########################################
def remove_codes_in_ontology(owl_zip_file, excel_file, output_file_name):
    st.write("Remove Codes in Ontology")
    with st.spinner('Processing...'):
        try:
            with zipfile.ZipFile(owl_zip_file) as z:
                owl_filenames = [name for name in z.namelist() if name.endswith('.owl') or name.endswith('.xml')]
                if not owl_filenames:
                    st.error("No OWL file found in the ZIP archive.")
                    return
                owl_filename = owl_filenames[0]
                with z.open(owl_filename) as owl_content:
                    progress_bar = st.progress(0)
                    log_placeholder = st.empty()
                    output = process_remove_codes(owl_content, excel_file, progress_bar, log_placeholder)
            st.success('Ontology codes removal completed.')
            st.download_button(
                label="Download Modified OWL File",
                data=output,
                file_name=output_file_name,
                mime='application/rdf+xml'
            )
        except zipfile.BadZipFile:
            st.error("The uploaded file is not a valid ZIP file.")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

def process_remove_codes(owl_content, excel_content, progress_bar, log_placeholder):
    logs = []

    df = pd.read_excel(excel_content)
    df = df[['Mendel ID', 'Codes']]
    df = df.dropna(subset=['Mendel ID'])
    df.columns = df.columns.str.strip()

    def format_mendel_id(x):
        if pd.isnull(x):
            return ''
        elif isinstance(x, float):
            return str(int(x)) if x.is_integer() else str(x)
        else:
            return str(x).strip()

    df['Mendel ID'] = df['Mendel ID'].apply(format_mendel_id)
    df['Codes'] = df['Codes'].fillna('').astype(str).str.strip()

    mendel_id_to_remove_codes = df.groupby('Mendel ID')['Codes'].apply(lambda col: set(col.str.strip())).to_dict()

    tree = etree.parse(owl_content)
    root = tree.getroot()

    namespaces = {
        'owl': 'http://www.w3.org/2002/07/owl#',
        'owl0': 'http://www.w3.org/2002/07/owl#',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'www': 'http://www.w3.org/2002/07/',
        'xml': 'http://www.w3.org/XML/1998/namespace',
        'xsd': 'http://www.w3.org/2001/XMLSchema#',
        'amr': 'http://www.semanticweb.org/amr/ontologies/2018/',
    }

    classes = root.xpath('//owl0:Class', namespaces=namespaces)
    total_classes = len(classes)
    log_text = ''
    log_placeholder.text_area("Processing Logs", value=log_text, height=200, key="remove_codes_log_unique")

    for index, cls in enumerate(classes):
        if index % UPDATE_INTERVAL == 0 or index == total_classes - 1:
            progress_bar.progress((index + 1) / total_classes)

        mendel_id_elems = cls.xpath('.//owl0:Mendel_ID', namespaces=namespaces)
        if not mendel_id_elems:
            mendel_id_elems = cls.xpath('.//*[local-name()="Mendel_ID"]')

        if mendel_id_elems:
            mendel_id_val = mendel_id_elems[0].text.strip()
            if mendel_id_val in mendel_id_to_remove_codes:
                remove_set = mendel_id_to_remove_codes[mendel_id_val]

                codes_elems = cls.xpath('.//owl0:Codes', namespaces=namespaces)
                if not codes_elems:
                    codes_elems = cls.xpath('.//*[local-name()="Codes"]')

                if codes_elems:
                    codes_elem = codes_elems[0]
                    existing_codes_text = codes_elem.text or ''
                    existing_codes = [c.strip() for c in existing_codes_text.split('\n') if c.strip()]

                    updated_codes = [code for code in existing_codes if code not in remove_set]

                    if updated_codes:
                        codes_elem.text = '\n'.join(sorted(set(updated_codes)))
                    else:
                        codes_elem.text = ''

                    log_message = f"Removed codes {remove_set} for Mendel ID {mendel_id_val}. Remaining: {updated_codes}"
                    logs.append(log_message)

        if index % UPDATE_INTERVAL == 0 or index == total_classes - 1:
            log_text = '\n'.join(logs[-200:])
            log_placeholder.text_area("Processing Logs", value=log_text, height=200, key=f"remove_codes_log_{index}")

    output = io.BytesIO()
    tree.write(output, pretty_print=True, xml_declaration=True, encoding='UTF-8', method="xml")
    output.seek(0)
    return output

def remove_synonyms_in_ontology(owl_zip_file, excel_file, output_file_name):
    st.write("Remove Synonyms in Ontology")
    with st.spinner('Processing...'):
        try:
            with zipfile.ZipFile(owl_zip_file) as z:
                owl_filenames = [name for name in z.namelist() if name.endswith('.owl') or name.endswith('.xml')]
                if not owl_filenames:
                    st.error("No OWL file found in the ZIP archive.")
                    return
                owl_filename = owl_filenames[0]
                with z.open(owl_filename) as owl_content:
                    progress_bar = st.progress(0)
                    log_placeholder = st.empty()
                    output = process_remove_synonyms(owl_content, excel_file, progress_bar, log_placeholder)
            st.success('Ontology synonyms removal completed.')
            st.download_button(
                label="Download Modified OWL File",
                data=output,
                file_name=output_file_name,
                mime='application/rdf+xml'
            )
        except zipfile.BadZipFile:
            st.error("The uploaded file is not a valid ZIP file.")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

def process_remove_synonyms(owl_content, excel_content, progress_bar, log_placeholder):
    logs = []

    df = pd.read_excel(excel_content)
    # The sheet has columns: Mendel ID and Synonyms (to remove)
    df = df[['Mendel ID', 'Synonyms']]
    df = df.dropna(subset=['Mendel ID'])
    df.columns = df.columns.str.strip()

    def format_mendel_id(x):
        if pd.isnull(x):
            return ''
        elif isinstance(x, float):
            return str(int(x)) if x.is_integer() else str(x)
        else:
            return str(x).strip()

    df['Mendel ID'] = df['Mendel ID'].apply(format_mendel_id)
    df['Synonyms'] = df['Synonyms'].fillna('').astype(str).str.strip()

    # Build a dictionary: mendel_id -> set of synonyms to remove
    mendel_id_to_remove_syns = df.groupby('Mendel ID')['Synonyms'].apply(lambda col: set(col.str.strip())).to_dict()

    tree = etree.parse(owl_content)
    root = tree.getroot()

    namespaces = {
        'owl': 'http://www.w3.org/2002/07/owl#',
        'owl0': 'http://www.w3.org/2002/07/owl#',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'www': 'http://www.w3.org/2002/07/',
        'xml': 'http://www.w3.org/XML/1998/namespace',
        'xsd': 'http://www.w3.org/2001/XMLSchema#',
        'amr': 'http://www.semanticweb.org/amr/ontologies/2018/',
    }

    classes = root.xpath('//owl0:Class', namespaces=namespaces)
    total_classes = len(classes)
    log_text = ''
    log_placeholder.text_area("Processing Logs", value=log_text, height=200)

    for index, cls in enumerate(classes):
        # Update progress bar periodically
        if index % UPDATE_INTERVAL == 0 or index == total_classes - 1:
            progress_bar.progress((index + 1) / total_classes)

        mendel_id_elems = cls.xpath('.//owl0:Mendel_ID', namespaces=namespaces)
        if not mendel_id_elems:
            mendel_id_elems = cls.xpath('.//*[local-name()="Mendel_ID"]')

        if mendel_id_elems:
            mendel_id_val = mendel_id_elems[0].text.strip()
            if mendel_id_val in mendel_id_to_remove_syns:
                remove_set = mendel_id_to_remove_syns[mendel_id_val]

                # Find existing <Synonyms>
                syn_elems = cls.xpath('.//owl0:Synonyms', namespaces=namespaces)
                if not syn_elems:
                    syn_elems = cls.xpath('.//*[local-name()="Synonyms"]')

                if syn_elems:
                    synonyms_elem = syn_elems[0]
                    existing_syns_text = synonyms_elem.text or ''
                    existing_syns = [s.strip() for s in existing_syns_text.split('\n') if s.strip()]

                    updated_syns = [syn for syn in existing_syns if syn not in remove_set]
                    if updated_syns:
                        synonyms_elem.text = '\n'.join(sorted(set(updated_syns)))
                    else:
                        synonyms_elem.text = ''

                    log_message = f"Removed synonyms {remove_set} for Mendel ID {mendel_id_val}. Remaining: {updated_syns}"
                    logs.append(log_message)

        # Periodically (or at end) update the text area
        if index % UPDATE_INTERVAL == 0 or index == total_classes - 1:
            log_text = '\n'.join(logs[-200:])
            log_placeholder.text_area("Processing Logs", value=log_text, height=200)

    output = io.BytesIO()
    tree.write(output, pretty_print=True, xml_declaration=True, encoding='UTF-8', method="xml")
    output.seek(0)
    return output

########################################
# Main
########################################
def main():
    st.sidebar.title("Actions")
    app_mode = st.sidebar.selectbox(
        "Choose the operation",
        [
            "Add New Classes",
            "Update Codes",
            "Update Synonyms",
            "Remove Codes",
            "Remove Synonyms"
        ]
    )

    # Editable output file name based on uploaded file
    owl_zip_file = st.file_uploader("Upload ZIP File containing OWL File", type=["zip"], key="owl_zip_file")
    if owl_zip_file:
        base_name = os.path.splitext(owl_zip_file.name)[0]
        output_file_name = f"{base_name}_updated.owl"
    else:
        output_file_name = "modified.owl"

    st.text_input(
        "Enter the name for the output OWL file (plwase keep the extenison)",
        value=output_file_name
    )

    if app_mode == "Add New Classes":
        st.write("Upload a .xlsx file that has following columns:")
        st.write("* MUST have: Label, Parent.")
        st.write("* Optional: Synonyms, Codes, Mendel_ID.")
        excel_file = st.file_uploader("", type=["xlsx"], key="add_classes_excel")

        if owl_zip_file and excel_file:
            if st.button("Create Concepts"):
                add_new_classes(owl_zip_file, excel_file, output_file_name)

    elif app_mode == "Update Codes":
        st.write("Upload a .xlsx file that has following columns:")
        st.write("* Mendel ID, Codes.")
        excel_file = st.file_uploader("", type=["xlsx"], key="update_codes_excel")

        if owl_zip_file and excel_file:
            if st.button("Update Codes"):
                update_codes_in_ontology(owl_zip_file, excel_file, output_file_name)

    elif app_mode == "Update Synonyms":
        st.write("Upload a .xlsx file that has following columns:")
        st.write("* Mendel ID, Synonyms.")
        excel_file = st.file_uploader("", type=["xlsx"], key="update_synonyms_excel")

        if owl_zip_file and excel_file:
            if st.button("Update Synonyms"):
                update_synonyms_in_ontology(owl_zip_file, excel_file, output_file_name)

    elif app_mode == "Remove Codes":
        st.write("Upload a .xlsx file that has following columns:")
        st.write("* Mendel ID, Codes.")
        excel_file = st.file_uploader("", type=["xlsx"], key="remove_codes_excel")

        if owl_zip_file and excel_file:
            if st.button("Remove Codes"):
                remove_codes_in_ontology(owl_zip_file, excel_file, output_file_name)

    elif app_mode == "Remove Synonyms":
        st.write("Upload a .xlsx file that has following columns:")
        st.write("* Mendel ID, Synonyms.")
        excel_file = st.file_uploader("", type=["xlsx"], key="remove_synonyms_excel")

        if owl_zip_file and excel_file:
            if st.button("Remove Synonyms"):
                remove_synonyms_in_ontology(owl_zip_file, excel_file, output_file_name)

if __name__ == "__main__":
    main()
