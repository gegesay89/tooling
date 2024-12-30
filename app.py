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
                owl_filenames = [
                    name for name in z.namelist()
                    if name.endswith('.owl') or name.endswith('.xml')
                ]
                if not owl_filenames:
                    st.error("No OWL file found in the ZIP archive.")
                    return
                owl_filename = owl_filenames[0]
                with z.open(owl_filename) as owl_content:
                    progress_bar = st.progress(0)
                    log_placeholder = st.empty()
                    output = process_add_new_classes(
                        owl_content,
                        excel_file,
                        progress_bar,
                        log_placeholder
                    )
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
    def sanitize_label(raw_label):
        return re.sub(r'[^a-zA-Z0-9_]+', '', raw_label)

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

    for index, row in df.iterrows():
        # Progress bar update
        if index % UPDATE_INTERVAL == 0 or index == total_rows - 1:
            progress_bar.progress((index + 1) / total_rows)

        parent_uri = f"http://www.semanticweb.org/amr/ontologies/2018/{row.get('Parent','')}"
        label_raw = row.get('Label', '')
        label = str(label_raw).strip() if pd.notna(label_raw) else None

        # Warn if the label has newlines
        if label and ("\n" in label or "\r" in label):
            st.warning(f"Row {index+1}: Label '{label}' contains newline(s). This might cause issues.")

        if label:
            sanitized_label = sanitize_label(label)
            new_class = etree.Element(
                '{http://www.semanticweb.org/amr/ontologies/2018/}Class',
                nsmap=ns
            )
            new_class.set(
                '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about',
                f"http://www.co-ode.org/ontologies/ont.owl#{sanitized_label}"
            )

            subclass_of = etree.SubElement(
                new_class,
                '{http://www.w3.org/2000/01/rdf-schema#}subClassOf',
                nsmap=ns
            )
            subclass_of.set(
                '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource',
                parent_uri
            )

            label_elem = etree.SubElement(
                new_class,
                '{http://www.w3.org/2000/01/rdf-schema#}label',
                {'{http://www.w3.org/XML/1998/namespace}lang': 'en'},
                nsmap=ns
            )
            label_elem.text = label

            # Add optional props
            for prop in optional_props:
                if prop in df.columns:
                    value_raw = row.get(prop, '')
                    value_str = str(value_raw).strip() if pd.notna(value_raw) else None
                    if value_str:
                        prop_elem = etree.SubElement(new_class, prop, nsmap=ns)
                        prop_elem.text = value_str

            # Add UMLS_CUI
            umls_cui_elem = etree.SubElement(new_class, 'UMLS_CUI', nsmap=ns)
            umls_cui_elem.text = label

            root.append(new_class)
            logs.append(
                f"Added new class '{label}' (# {sanitized_label}) under parent '{row.get('Parent','')}'."
            )
        else:
            logs.append(f"Skipped row {index + 1}: Label is missing.")

    # After the loop, show the logs in a single text_area
    log_text = '\n'.join(logs)
    log_placeholder.text_area(
        "Add New Classes Logs",
        value=log_text,
        height=300,
        key="process_add_new_classes_log_final"
    )

    output = io.BytesIO()
    tree.write(output, pretty_print=True, xml_declaration=True, encoding='UTF-8')
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
                owl_filenames = [
                    name for name in z.namelist()
                    if name.endswith('.owl') or name.endswith('.xml')
                ]
                if not owl_filenames:
                    st.error("No OWL file found in the ZIP archive.")
                    return
                owl_filename = owl_filenames[0]
                with z.open(owl_filename) as owl_content:
                    progress_bar = st.progress(0)
                    log_placeholder = st.empty()
                    output = process_update_codes(
                        owl_content,
                        excel_file,
                        progress_bar,
                        log_placeholder
                    )
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
    for index, cls in enumerate(classes):
        if index % UPDATE_INTERVAL == 0 or index == total_classes - 1:
            progress_bar.progress((index + 1) / total_classes)

        mendel_id_elems = cls.xpath('.//owl0:Mendel_ID', namespaces=namespaces)
        if not mendel_id_elems:
            mendel_id_elems = cls.xpath('.//*[local-name()="Mendel_ID"]')

        if mendel_id_elems:
            mendel_id = (mendel_id_elems[0].text or '').strip()
            if mendel_id in mendel_id_to_codes:
                codes_list = mendel_id_to_codes[mendel_id]
                codes_elems = cls.xpath('.//owl0:Codes', namespaces=namespaces)
                if not codes_elems:
                    codes_elems = cls.xpath('.//*[local-name()="Codes"]')

                if codes_elems:
                    codes_elem = codes_elems[0]
                    existing_codes_text = codes_elem.text or ''
                    existing_codes = [c.strip() for c in existing_codes_text.split('\n') if c.strip()]
                    combined = set(existing_codes) | set(codes_list)
                    codes_elem.text = '\n'.join(sorted(combined))
                    logs.append(f"Updated codes for Mendel ID {mendel_id}: {combined}")
                else:
                    new_codes_elem = etree.SubElement(cls, '{%s}Codes' % namespaces['owl0'])
                    combined = set(codes_list)
                    new_codes_elem.text = '\n'.join(sorted(combined))
                    logs.append(f"Added codes for Mendel ID {mendel_id}: {combined}")

    log_text = '\n'.join(logs)
    log_placeholder.text_area(
        "Update Codes Logs",
        value=log_text,
        height=300,
        key="process_update_codes_log_final"
    )

    output = io.BytesIO()
    tree.write(output, pretty_print=True, xml_declaration=True, encoding='UTF-8')
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
                owl_filenames = [
                    name for name in z.namelist()
                    if name.endswith('.owl') or name.endswith('.xml')
                ]
                if not owl_filenames:
                    st.error("No OWL file found in the ZIP archive.")
                    return
                owl_filename = owl_filenames[0]
                with z.open(owl_filename) as owl_content:
                    progress_bar = st.progress(0)
                    log_placeholder = st.empty()
                    output = process_update_synonyms(
                        owl_content,
                        excel_file,
                        progress_bar,
                        log_placeholder
                    )
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

    mendel_id_to_syns = df.groupby('Mendel ID')['Synonyms'].apply(list).to_dict()

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
    for index, cls in enumerate(classes):
        if index % UPDATE_INTERVAL == 0 or index == total_classes - 1:
            progress_bar.progress((index + 1) / total_classes)

        mendel_id_elems = cls.xpath('.//owl0:Mendel_ID', namespaces=namespaces)
        if not mendel_id_elems:
            mendel_id_elems = cls.xpath('.//*[local-name()="Mendel_ID"]')

        if mendel_id_elems:
            mendel_id_val = (mendel_id_elems[0].text or '').strip()
            if mendel_id_val in mendel_id_to_syns:
                synonyms_list = mendel_id_to_syns[mendel_id_val]
                syn_elems = cls.xpath('.//owl0:Synonyms', namespaces=namespaces)
                if not syn_elems:
                    syn_elems = cls.xpath('.//*[local-name()="Synonyms"]')

                if syn_elems:
                    synonyms_elem = syn_elems[0]
                    existing_syn_text = synonyms_elem.text or ''
                    existing_syns = [s.strip() for s in existing_syn_text.split('\n') if s.strip()]
                    combined = set(existing_syns) | set(synonyms_list)
                    synonyms_elem.text = '\n'.join(sorted(combined))
                    logs.append(f"Updated synonyms for Mendel ID {mendel_id_val}: {combined}")
                else:
                    new_syn_elem = etree.SubElement(cls, '{%s}Synonyms' % namespaces['owl0'])
                    combined = set(synonyms_list)
                    new_syn_elem.text = '\n'.join(sorted(combined))
                    logs.append(f"Added synonyms for Mendel ID {mendel_id_val}: {combined}")

    log_text = '\n'.join(logs)
    log_placeholder.text_area(
        "Update Synonyms Logs",
        value=log_text,
        height=300,
        key="process_update_synonyms_log_final"
    )

    output = io.BytesIO()
    tree.write(output, pretty_print=True, xml_declaration=True, encoding='UTF-8')
    output.seek(0)
    return output

########################################
# Part 4: Remove Codes
########################################
def remove_codes_in_ontology(owl_zip_file, excel_file, output_file_name):
    st.write("Remove Codes in Ontology")
    with st.spinner('Processing...'):
        try:
            with zipfile.ZipFile(owl_zip_file) as z:
                owl_filenames = [
                    name for name in z.namelist()
                    if name.endswith('.owl') or name.endswith('.xml')
                ]
                if not owl_filenames:
                    st.error("No OWL file found in the ZIP archive.")
                    return
                owl_filename = owl_filenames[0]
                with z.open(owl_filename) as owl_content:
                    progress_bar = st.progress(0)
                    log_placeholder = st.empty()
                    output = process_remove_codes(
                        owl_content,
                        excel_file,
                        progress_bar,
                        log_placeholder
                    )
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

    mendel_id_to_remove = df.groupby('Mendel ID')['Codes'].apply(lambda c: set(c.str.strip())).to_dict()

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
        'amr': 'http://www.semanticweb.org/amr/ontologies/2018/',
    }
    classes = root.xpath('//owl0:Class', namespaces=ns)

    total_classes = len(classes)
    for index, cls in enumerate(classes):
        if index % UPDATE_INTERVAL == 0 or index == total_classes - 1:
            progress_bar.progress((index + 1) / total_classes)

        mendel_id_elems = cls.xpath('.//owl0:Mendel_ID', namespaces=ns)
        if not mendel_id_elems:
            mendel_id_elems = cls.xpath('.//*[local-name()="Mendel_ID"]')

        if mendel_id_elems:
            mendel_id_val = (mendel_id_elems[0].text or '').strip()
            if mendel_id_val in mendel_id_to_remove:
                remove_set = mendel_id_to_remove[mendel_id_val]
                codes_elems = cls.xpath('.//owl0:Codes', namespaces=ns)
                if not codes_elems:
                    codes_elems = cls.xpath('.//*[local-name()="Codes"]')

                for c_elem in codes_elems:
                    existing_text = c_elem.text or ''
                    existing_codes = [c.strip() for c in existing_text.split('\n') if c.strip()]
                    updated = [code for code in existing_codes if code not in remove_set]
                    if updated:
                        c_elem.text = '\n'.join(sorted(set(updated)))
                    else:
                        c_elem.text = ''
                logs.append(
                    f"Removed codes {remove_set} for Mendel ID {mendel_id_val}."
                )

    log_text = '\n'.join(logs)
    log_placeholder.text_area(
        "Remove Codes Logs",
        value=log_text,
        height=300,
        key="process_remove_codes_log_final"
    )

    output = io.BytesIO()
    tree.write(output, pretty_print=True, xml_declaration=True, encoding='UTF-8')
    output.seek(0)
    return output

########################################
# Part 5: Remove Synonyms
########################################
def remove_synonyms_in_ontology(owl_zip_file, excel_file, output_file_name):
    st.write("Remove Synonyms in Ontology")
    with st.spinner('Processing...'):
        try:
            with zipfile.ZipFile(owl_zip_file) as z:
                owl_filenames = [
                    name for name in z.namelist()
                    if name.endswith('.owl') or name.endswith('.xml')
                ]
                if not owl_filenames:
                    st.error("No OWL file found in the ZIP archive.")
                    return
                owl_filename = owl_filenames[0]
                with z.open(owl_filename) as owl_content:
                    progress_bar = st.progress(0)
                    log_placeholder = st.empty()
                    output = process_remove_synonyms(
                        owl_content,
                        excel_file,
                        progress_bar,
                        log_placeholder
                    )
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

    mendel_id_to_remove_syns = df.groupby('Mendel ID')['Synonyms'].apply(lambda col: set(col.str.strip())).to_dict()

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
        'amr': 'http://www.semanticweb.org/amr/ontologies/2018/',
    }
    classes = root.xpath('//owl0:Class', namespaces=ns)

    total_classes = len(classes)
    for index, cls in enumerate(classes):
        if index % UPDATE_INTERVAL == 0 or index == total_classes - 1:
            progress_bar.progress((index + 1) / total_classes)

        mendel_id_elems = cls.xpath('.//owl0:Mendel_ID', namespaces=ns)
        if not mendel_id_elems:
            mendel_id_elems = cls.xpath('.//*[local-name()="Mendel_ID"]')

        if mendel_id_elems:
            mendel_id_val = (mendel_id_elems[0].text or '').strip()
            if mendel_id_val in mendel_id_to_remove_syns:
                remove_set = mendel_id_to_remove_syns[mendel_id_val]
                syn_elems = cls.xpath('.//owl0:Synonyms', namespaces=ns)
                if not syn_elems:
                    syn_elems = cls.xpath('.//*[local-name()="Synonyms"]')

                for s_elem in syn_elems:
                    existing_text = s_elem.text or ''
                    existing_syns = [s.strip() for s in existing_text.split('\n') if s.strip()]
                    updated = [syn for syn in existing_syns if syn not in remove_set]
                    if updated:
                        s_elem.text = '\n'.join(sorted(set(updated)))
                    else:
                        s_elem.text = ''
                logs.append(
                    f"Removed synonyms {remove_set} for Mendel ID {mendel_id_val}."
                )

    log_text = '\n'.join(logs)
    log_placeholder.text_area(
        "Remove Synonyms Logs",
        value=log_text,
        height=300,
        key="process_remove_synonyms_log_final"
    )

    output = io.BytesIO()
    tree.write(output, pretty_print=True, xml_declaration=True, encoding='UTF-8')
    output.seek(0)
    return output

########################################
# Part 6: All in One (Add → Add Codes → Add Synonyms → Remove Synonyms → Remove Codes)
########################################
def all_in_one_operations(owl_zip_file, excel_file, output_file_name):
    """
    Reads a single Excel file that has two sheets:
    1) 'AddConcepts': used by process_add_new_classes
        - Must have at least: 'Label' and 'Parent'
        - Optionally: 'Synonyms', 'Codes', 'Mendel_ID'
    2) 'MassUpdates': used for the rest of the updates/removals
        - Columns: 'Mendel ID', 'Codes to Add', 'Codes to Remove', 'Synonyms to Add', 'Synonyms to Remove'

    Performs all operations in order on one OWL file in memory:
      1) Add new classes
      2) Update (Add) codes
      3) Update (Add) synonyms
      4) Remove synonyms
      5) Remove codes
    """

    st.write("Performing operations in sequence:")
    st.write("1) Add New Classes")
    st.write("2) Add Codes")
    st.write("3) Add Synonyms")
    st.write("4) Remove Synonyms")
    st.write("5) Remove Codes")

    try:
        # Read the Excel as bytes into memory
        xls_data = excel_file.read()
        excel_file_io = io.BytesIO(xls_data)

        with zipfile.ZipFile(owl_zip_file) as z:
            owl_filenames = [
                name for name in z.namelist()
                if name.endswith('.owl') or name.endswith('.xml')
            ]
            if not owl_filenames:
                st.error("No OWL file found in the ZIP archive.")
                return
            owl_filename = owl_filenames[0]

            # Parse the Excel file
            xls = pd.ExcelFile(excel_file_io)
            df_add_concepts = xls.parse("AddConcepts")
            df_mass = xls.parse("MassUpdates")

            # 1) Convert df_add_concepts to BytesIO for process_add_new_classes
            add_concepts_io = io.BytesIO()
            with pd.ExcelWriter(add_concepts_io, engine='openpyxl') as writer:
                df_add_concepts.to_excel(writer, index=False)
            add_concepts_io.seek(0)

            # Start with the original OWL for the first operation
            with z.open(owl_filename) as initial_owl_content:
                progress_bar = st.progress(0)
                log_placeholder = st.empty()
                modified_owl = process_add_new_classes(
                    owl_content=initial_owl_content,
                    excel_content=add_concepts_io,
                    progress_bar=progress_bar,
                    log_placeholder=log_placeholder
                )

            # 2) Add Codes
            add_codes_df = df_mass[["Mendel ID", "Codes to Add"]].rename(
                columns={"Codes to Add": "Codes"}
            ).dropna(subset=["Mendel ID"])
            add_codes_io = io.BytesIO()
            with pd.ExcelWriter(add_codes_io, engine='openpyxl') as writer:
                add_codes_df.to_excel(writer, index=False)
            add_codes_io.seek(0)

            progress_bar = st.progress(0)
            log_placeholder = st.empty()
            modified_owl = process_update_codes(
                owl_content=modified_owl,
                excel_content=add_codes_io,
                progress_bar=progress_bar,
                log_placeholder=log_placeholder
            )

            # 3) Add Synonyms
            add_syn_df = df_mass[["Mendel ID", "Synonyms to Add"]].rename(
                columns={"Synonyms to Add": "Synonyms"}
            ).dropna(subset=["Mendel ID"])
            add_syn_io = io.BytesIO()
            with pd.ExcelWriter(add_syn_io, engine='openpyxl') as writer:
                add_syn_df.to_excel(writer, index=False)
            add_syn_io.seek(0)

            progress_bar = st.progress(0)
            log_placeholder = st.empty()
            modified_owl = process_update_synonyms(
                owl_content=modified_owl,
                excel_content=add_syn_io,
                progress_bar=progress_bar,
                log_placeholder=log_placeholder
            )

            # 4) Remove Synonyms
            remove_syn_df = df_mass[["Mendel ID", "Synonyms to Remove"]].rename(
                columns={"Synonyms to Remove": "Synonyms"}
            ).dropna(subset=["Mendel ID"])
            remove_syn_io = io.BytesIO()
            with pd.ExcelWriter(remove_syn_io, engine='openpyxl') as writer:
                remove_syn_df.to_excel(writer, index=False)
            remove_syn_io.seek(0)

            progress_bar = st.progress(0)
            log_placeholder = st.empty()
            modified_owl = process_remove_synonyms(
                owl_content=modified_owl,
                excel_content=remove_syn_io,
                progress_bar=progress_bar,
                log_placeholder=log_placeholder
            )

            # 5) Remove Codes
            remove_codes_df = df_mass[["Mendel ID", "Codes to Remove"]].rename(
                columns={"Codes to Remove": "Codes"}
            ).dropna(subset=["Mendel ID"])
            remove_codes_io = io.BytesIO()
            with pd.ExcelWriter(remove_codes_io, engine='openpyxl') as writer:
                remove_codes_df.to_excel(writer, index=False)
            remove_codes_io.seek(0)

            progress_bar = st.progress(0)
            log_placeholder = st.empty()
            modified_owl = process_remove_codes(
                owl_content=modified_owl,
                excel_content=remove_codes_io,
                progress_bar=progress_bar,
                log_placeholder=log_placeholder
            )

            st.success("All operations completed successfully.")
            st.download_button(
                label="Download Final Modified OWL File",
                data=modified_owl,
                file_name=output_file_name,
                mime='application/rdf+xml'
            )

    except zipfile.BadZipFile:
        st.error("The uploaded file is not a valid ZIP file.")
    except KeyError as ke:
        st.error(f"Missing required sheet or column in Excel: {str(ke)}")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

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
            "Remove Synonyms",
            "All in One (Add + Update + Remove)"
        ]
    )

    owl_zip_file = st.file_uploader(
        "Upload ZIP File containing OWL File",
        type=["zip"],
        key="owl_zip_file"
    )
    if owl_zip_file:
        base_name = os.path.splitext(owl_zip_file.name)[0]
        output_file_name = f"{base_name}_updated.owl"
    else:
        output_file_name = "modified.owl"

    st.text_input(
        "Enter the name for the output OWL file (including .owl extension)",
        value=output_file_name
    )

    if app_mode == "Add New Classes":
        st.write("Upload a .xlsx file that has the following columns:")
        st.write("• MUST have: Label, Parent")
        st.write("• Optional: Synonyms, Codes, Mendel_ID")
        excel_file = st.file_uploader("Upload Excel File for new classes", type=["xlsx"], key="add_classes_excel")

        if owl_zip_file and excel_file and st.button("Create Concepts"):
            add_new_classes(owl_zip_file, excel_file, output_file_name)

    elif app_mode == "Update Codes":
        st.write("Upload a .xlsx file that has the following columns:")
        st.write("• Mendel ID, Codes")
        excel_file = st.file_uploader("Upload Excel File for code updates", type=["xlsx"], key="update_codes_excel")

        if owl_zip_file and excel_file and st.button("Update Codes"):
            update_codes_in_ontology(owl_zip_file, excel_file, output_file_name)

    elif app_mode == "Update Synonyms":
        st.write("Upload a .xlsx file that has the following columns:")
        st.write("• Mendel ID, Synonyms")
        excel_file = st.file_uploader("Upload Excel File for synonym updates", type=["xlsx"], key="update_synonyms_excel")

        if owl_zip_file and excel_file and st.button("Update Synonyms"):
            update_synonyms_in_ontology(owl_zip_file, excel_file, output_file_name)

    elif app_mode == "Remove Codes":
        st.write("Upload a .xlsx file that has the following columns:")
        st.write("• Mendel ID, Codes")
        excel_file = st.file_uploader("Upload Excel File for codes removal", type=["xlsx"], key="remove_codes_excel")

        if owl_zip_file and excel_file and st.button("Remove Codes"):
            remove_codes_in_ontology(owl_zip_file, excel_file, output_file_name)

    elif app_mode == "Remove Synonyms":
        st.write("Upload a .xlsx file that has the following columns:")
        st.write("• Mendel ID, Synonyms")
        excel_file = st.file_uploader("Upload Excel File for synonyms removal", type=["xlsx"], key="remove_synonyms_excel")

        if owl_zip_file and excel_file and st.button("Remove Synonyms"):
            remove_synonyms_in_ontology(owl_zip_file, excel_file, output_file_name)

    elif app_mode == "All in One (Add + Update + Remove)":
        st.write("Upload a .xlsx file that has 2 sheets:")
        st.write("1) 'AddConcepts' for new classes (Label, Parent, optional Synonyms, Codes, Mendel_ID)")
        st.write("2) 'MassUpdates' for adding/removing codes/synonyms (Mendel ID, Codes to Add, Codes to Remove, Synonyms to Add, Synonyms to Remove)")
        excel_file = st.file_uploader("Upload Excel File with Both Sheets", type=["xlsx"], key="combined_excel")

        if owl_zip_file and excel_file and st.button("Process All in One"):
            all_in_one_operations(owl_zip_file, excel_file, output_file_name)

if __name__ == "__main__":
    main()
