import streamlit as st
import pandas as pd
from lxml import etree
import io
import zipfile

def add_new_classes(owl_zip_file, excel_file, output_file_name):
    # Function to add new classes to the ontology
    st.write("Add New Classes to Ontology")
    with st.spinner('Processing...'):
        try:
            with zipfile.ZipFile(owl_zip_file) as z:
                # Find the OWL file inside the zip archive
                owl_filenames = [name for name in z.namelist() if name.endswith('.owl') or name.endswith('.xml')]
                if not owl_filenames:
                    st.error("No OWL file found in the ZIP archive.")
                    return
                # Use the first OWL file found
                owl_filename = owl_filenames[0]
                with z.open(owl_filename) as owl_content:
                    # Create placeholders for progress bar and logs
                    progress_bar = st.progress(0)
                    log_placeholder = st.empty()
                    # Call the processing function
                    output = process_add_new_classes(owl_content, excel_file, progress_bar, log_placeholder)
            st.success('Ontology modification completed.')

            # Provide a download button
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
    logs = []
    # Load the Excel file
    df = pd.read_excel(excel_content)
    
    # Parse the OWL file
    tree = etree.parse(owl_content)
    root = tree.getroot()
    
    # Define XML namespaces to use in XPath queries and element creation
    ns = {
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'owl': 'http://www.w3.org/2002/07/owl#',
        'xml': 'http://www.w3.org/XML/1998/namespace'
    }
    etree.register_namespace('xml', ns['xml'])  # Register the xml namespace for xml:lang
    
    # List of optional properties to add if available
    optional_props = ['Code', 'Synonyms', 'Mendel_ID']

    total_rows = len(df)
    # Initialize log display
    log_text = ''
    log_box = log_placeholder.text_area("Processing Logs", value=log_text, height=200)
    # Iterate through the Excel file rows with progress bar
    for index, row in df.iterrows():
        # Update progress bar
        progress = (index + 1) / total_rows
        progress_bar.progress(progress)
        
        parent_uri = f"http://www.semanticweb.org/amr/ontologies/2018/{row['Parent']}"
        label = str(row['Label']).strip() if pd.notna(row['Label']) and str(row['Label']).strip() != '' else None
        
        # Create a new Class element
        if label:
            new_class = etree.Element('{http://www.semanticweb.org/amr/ontologies/2018/}Class', nsmap=ns)
            new_class.set('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about', f"http://www.co-ode.org/ontologies/ont.owl#{label.replace(' ', '_')}")

            # Add subclass relationship
            subclass_of = etree.SubElement(new_class, '{http://www.w3.org/2000/01/rdf-schema#}subClassOf', nsmap=ns)
            subclass_of.set('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource', parent_uri)

            # Add label
            label_elem = etree.SubElement(new_class, '{http://www.w3.org/2000/01/rdf-schema#}label', {'{http://www.w3.org/XML/1998/namespace}lang': 'en'}, nsmap=ns)
            label_elem.text = label

            # Append properties if they exist and are non-empty
            for prop in optional_props:
                if prop in df.columns:
                    value = str(row[prop]).strip() if pd.notna(row[prop]) and str(row[prop]).strip() != '' else None
                    if value:
                        prop_elem = etree.SubElement(new_class, prop, nsmap=ns)
                        prop_elem.text = value

            # Add UMLS_CUI with the same value as the label
            umls_cui_elem = etree.SubElement(new_class, 'UMLS_CUI', nsmap=ns)
            umls_cui_elem.text = label

            # Append the new class to the root of the document
            root.append(new_class)
            # Log the addition
            log_message = f"Added new class for '{label}' under parent '{row['Parent']}'."
            logs.append(log_message)
            # Update logs display
            log_text = '\n'.join(logs)
            log_placeholder.text_area("Processing Logs", value=log_text, height=200)
        else:
            # Log the skipped entry
            log_message = f"Skipped row {index + 1}: Label is missing."
            logs.append(log_message)
            # Update logs display
            log_text = '\n'.join(logs)
            log_placeholder.text_area("Processing Logs", value=log_text, height=200)
    
    # Write the modified tree to a BytesIO object
    output = io.BytesIO()
    tree.write(output, pretty_print=True, xml_declaration=True, encoding='UTF-8', method="xml")
    output.seek(0)  # Move the cursor to the beginning of the BytesIO object
    return output

def update_codes_in_ontology(owl_zip_file, excel_file, output_file_name):
    # Function to update codes in the ontology
    st.write("Update Codes in Ontology")
    with st.spinner('Processing...'):
        try:
            with zipfile.ZipFile(owl_zip_file) as z:
                # Find the OWL file inside the zip archive
                owl_filenames = [name for name in z.namelist() if name.endswith('.owl') or name.endswith('.xml')]
                if not owl_filenames:
                    st.error("No OWL file found in the ZIP archive.")
                    return
                # Use the first OWL file found
                owl_filename = owl_filenames[0]
                with z.open(owl_filename) as owl_content:
                    # Create placeholders for progress bar and logs
                    progress_bar = st.progress(0)
                    log_placeholder = st.empty()
                    # Call the processing function
                    output = process_update_codes(owl_content, excel_file, progress_bar, log_placeholder)
            st.success('Ontology codes update completed.')

            # Provide a download button
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

    # Load the Excel file
    df = pd.read_excel(excel_content)

    # Keep only the necessary columns
    df = df[['Mendel ID', 'Codes']]

    # Drop rows where 'Mendel ID' is NaN
    df = df.dropna(subset=['Mendel ID'])

    # Remove leading/trailing spaces from column names
    df.columns = df.columns.str.strip()

    # Define a function to convert Mendel IDs to strings without decimal points
    def format_mendel_id(x):
        if pd.isnull(x):
            return ''
        elif isinstance(x, float):
            if x.is_integer():
                return str(int(x))
            else:
                return str(x)
        else:
            return str(x).strip()

    # Apply the function to the 'Mendel ID' column
    df['Mendel ID'] = df['Mendel ID'].apply(format_mendel_id)

    # Replace NaN values with empty strings in 'Codes' column
    df['Codes'] = df['Codes'].fillna('').astype(str).str.strip()

    # Create a dictionary mapping Mendel IDs to lists of codes
    mendel_id_to_codes = df.groupby('Mendel ID')['Codes'].apply(list).to_dict()

    # Parse the OWL file
    tree = etree.parse(owl_content)
    root = tree.getroot()

    # Define the namespaces
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

    # Find all Class elements
    classes = root.xpath('//owl0:Class', namespaces=namespaces)

    total_classes = len(classes)
    # Initialize log display
    log_text = ''
    log_box = log_placeholder.text_area("Processing Logs", value=log_text, height=200)
    # Iterate through the classes with progress bar
    for index, cls in enumerate(classes):
        # Update progress bar
        progress = (index + 1) / total_classes
        progress_bar.progress(progress)

        class_iri = cls.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about')
        label_elems = cls.xpath('.//rdfs:label', namespaces=namespaces)
        class_label = label_elems[0].text if label_elems else 'No label'

        mendel_id_elems = cls.xpath('.//owl0:Mendel_ID', namespaces=namespaces)
        if not mendel_id_elems:
            mendel_id_elems = cls.xpath('.//*[local-name()="Mendel_ID"]')

        if mendel_id_elems:
            mendel_id_elem = mendel_id_elems[0]
            mendel_id = mendel_id_elem.text.strip()

            if mendel_id in mendel_id_to_codes:
                codes_list = mendel_id_to_codes[mendel_id]  # This is a list of codes

                # Get existing Codes
                codes_elems = cls.xpath('.//owl0:Codes', namespaces=namespaces)
                if not codes_elems:
                    codes_elems = cls.xpath('.//*[local-name()="Codes"]')

                if codes_elems:
                    codes_elem = codes_elems[0]
                    existing_codes_text = codes_elem.text or ''
                    existing_codes = [code.strip() for code in existing_codes_text.split('\n') if code.strip()]
                    # Combine existing codes and new codes, avoiding duplicates
                    combined_codes = set(existing_codes) | set(codes_list)
                    # Update the Codes element
                    codes_elem.text = '\n'.join(sorted(combined_codes))
                    log_message = f"Updated codes for Mendel ID {mendel_id}: {combined_codes}"
                else:
                    codes_elem = etree.SubElement(cls, '{%s}Codes' % namespaces['owl0'])
                    combined_codes = set(codes_list)
                    codes_elem.text = '\n'.join(sorted(combined_codes))
                    log_message = f"Added new Codes element for Mendel ID {mendel_id}: {combined_codes}"

                logs.append(log_message)
                # Update logs display
                log_text = '\n'.join(logs)
                log_placeholder.text_area("Processing Logs", value=log_text, height=200)
            else:
                # Mendel ID not found in the Excel file
                continue
        else:
            # No Mendel_ID element found
            continue

    # Write the modified tree to a BytesIO object
    output = io.BytesIO()
    tree.write(output, pretty_print=True, xml_declaration=True, encoding='UTF-8', method="xml")
    output.seek(0)  # Move the cursor to the beginning of the BytesIO object
    return output

def update_synonyms_in_ontology(owl_zip_file, excel_file, output_file_name):
    # Function to update synonyms in the ontology
    st.write("Update Synonyms in Ontology")
    with st.spinner('Processing...'):
        try:
            with zipfile.ZipFile(owl_zip_file) as z:
                # Find the OWL file inside the zip archive
                owl_filenames = [name for name in z.namelist() if name.endswith('.owl') or name.endswith('.xml')]
                if not owl_filenames:
                    st.error("No OWL file found in the ZIP archive.")
                    return
                # Use the first OWL file found
                owl_filename = owl_filenames[0]
                with z.open(owl_filename) as owl_content:
                    # Create placeholders for progress bar and logs
                    progress_bar = st.progress(0)
                    log_placeholder = st.empty()
                    # Call the processing function
                    output = process_update_synonyms(owl_content, excel_file, progress_bar, log_placeholder)
            st.success('Ontology synonyms update completed.')

            # Provide a download button
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

    # Load the Excel file
    df = pd.read_excel(excel_content)

    # Keep only the necessary columns
    df = df[['Mendel ID', 'Synonyms']]

    # Drop rows where 'Mendel ID' is NaN
    df = df.dropna(subset=['Mendel ID'])

    # Remove leading/trailing spaces from column names
    df.columns = df.columns.str.strip()

    # Define a function to convert Mendel IDs to strings without decimal points
    def format_mendel_id(x):
        if pd.isnull(x):
            return ''
        elif isinstance(x, float):
            if x.is_integer():
                return str(int(x))
            else:
                return str(x)
        else:
            return str(x).strip()

    # Apply the function to the 'Mendel ID' column
    df['Mendel ID'] = df['Mendel ID'].apply(format_mendel_id)

    # Replace NaN values with empty strings in 'Synonyms' column
    df['Synonyms'] = df['Synonyms'].fillna('').astype(str).str.strip()

    # Create a dictionary mapping Mendel IDs to lists of synonyms
    mendel_id_to_synonyms = df.groupby('Mendel ID')['Synonyms'].apply(list).to_dict()

    # Parse the OWL file
    tree = etree.parse(owl_content)
    root = tree.getroot()

    # Define the namespaces
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

    # Find all Class elements
    classes = root.xpath('//owl0:Class', namespaces=namespaces)

    total_classes = len(classes)
    # Initialize log display
    log_text = ''
    log_box = log_placeholder.text_area("Processing Logs", value=log_text, height=200)
    # Iterate through the classes with progress bar
    for index, cls in enumerate(classes):
        # Update progress bar
        progress = (index + 1) / total_classes
        progress_bar.progress(progress)

        class_iri = cls.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about')
        label_elems = cls.xpath('.//rdfs:label', namespaces=namespaces)
        class_label = label_elems[0].text if label_elems else 'No label'

        mendel_id_elems = cls.xpath('.//owl0:Mendel_ID', namespaces=namespaces)
        if not mendel_id_elems:
            mendel_id_elems = cls.xpath('.//*[local-name()="Mendel_ID"]')

        if mendel_id_elems:
            mendel_id_elem = mendel_id_elems[0]
            mendel_id = mendel_id_elem.text.strip()

            if mendel_id in mendel_id_to_synonyms:
                synonyms_list = mendel_id_to_synonyms[mendel_id]  # This is a list of synonyms

                # Get existing Synonyms
                synonyms_elems = cls.xpath('.//owl0:Synonyms', namespaces=namespaces)
                if not synonyms_elems:
                    synonyms_elems = cls.xpath('.//*[local-name()="Synonyms"]')

                if synonyms_elems:
                    synonyms_elem = synonyms_elems[0]
                    existing_synonyms_text = synonyms_elem.text or ''
                    existing_synonyms = [synonym.strip() for synonym in existing_synonyms_text.split('\n') if synonym.strip()]
                    # Combine existing synonyms and new synonyms, avoiding duplicates
                    combined_synonyms = set(existing_synonyms) | set(synonyms_list)
                    # Update the Synonyms element
                    synonyms_elem.text = '\n'.join(sorted(combined_synonyms))
                    log_message = f"Updated synonyms for Mendel ID {mendel_id}: {combined_synonyms}"
                else:
                    synonyms_elem = etree.SubElement(cls, '{%s}Synonyms' % namespaces['owl0'])
                    combined_synonyms = set(synonyms_list)
                    synonyms_elem.text = '\n'.join(sorted(combined_synonyms))
                    log_message = f"Added new Synonyms element for Mendel ID {mendel_id}: {combined_synonyms}"

                logs.append(log_message)
                # Update logs display
                log_text = '\n'.join(logs)
                log_placeholder.text_area("Processing Logs", value=log_text, height=200)
            else:
                # Mendel ID not found in the Excel file
                continue
        else:
            # No Mendel_ID element found
            continue

    # Write the modified tree to a BytesIO object
    output = io.BytesIO()
    tree.write(output, pretty_print=True, xml_declaration=True, encoding='UTF-8', method="xml")
    output.seek(0)  # Move the cursor to the beginning of the BytesIO object
    return output

def main():
    st.title("Ontology Concepts Designer (OCD)")

    # Sidebar for function selection
    st.sidebar.title("Options")
    app_mode = st.sidebar.selectbox("Choose the operation", ["Add New Classes", "Update Codes", "Update Synonyms"])

    # Editable output file name
    output_file_name = st.text_input("Enter the name for the output OWL file (including .owl extension)", value="modified.owl")

    if app_mode == "Add New Classes":
        st.write("Upload a ZIP file containing an OWL file and an Excel file to create ontology classes.")
        owl_zip_file = st.file_uploader("Upload ZIP File containing OWL File", type=["zip"])
        excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])

        if owl_zip_file is not None and excel_file is not None:
            if st.button("Create Ontology Classes"):
                add_new_classes(owl_zip_file, excel_file, output_file_name)

    elif app_mode == "Update Codes":
        st.write("Upload a ZIP file containing an OWL file and an Excel file to update codes in the ontology.")
        owl_zip_file = st.file_uploader("Upload ZIP File containing OWL File", type=["zip"])
        excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])

        if owl_zip_file is not None and excel_file is not None:
            if st.button("Update Codes in Ontology"):
                update_codes_in_ontology(owl_zip_file, excel_file, output_file_name)

    elif app_mode == "Update Synonyms":
        st.write("Upload a ZIP file containing an OWL file and an Excel file to update synonyms in the ontology.")
        owl_zip_file = st.file_uploader("Upload ZIP File containing OWL File", type=["zip"])
        excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])

        if owl_zip_file is not None and excel_file is not None:
            if st.button("Update Synonyms in Ontology"):
                update_synonyms_in_ontology(owl_zip_file, excel_file, output_file_name)

if __name__ == "__main__":
    main()
