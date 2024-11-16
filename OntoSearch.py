import streamlit as st
import pandas as pd
from lxml import etree
import logging
import io
import zipfile
import os
import re

def main():
    st.title("Synonym, Mendel ID, or Code Search")

    st.write("""
        This brilliant app allows you to select or upload a ZIP file containing an OWL file and search for:
        - Exact matches of specified phrases within the synonyms. (relaxed search will be available soon)
        - Search by Mendel IDs.
        - Search for codes within the ontology. (Using typical format: Coding system:Code value)
        - Search for code values with relaxed matching. (No need to add the coding system, removes all special characters)
        - **Search for code values with semi-relaxed matching. (Only removes dots from the codes)**
        """)

    # Directory to store ZIP files
    zip_files_directory = 'shared_zip_files'
    os.makedirs(zip_files_directory, exist_ok=True)

    # List existing ZIP files
    existing_zip_files = [f for f in os.listdir(zip_files_directory) if f.endswith('.zip')]

    # File uploader for ZIP file containing OWL file
    st.write("### Select an existing ZIP file or upload a new one")

    # Option to select an existing ZIP file
    if existing_zip_files:
        selected_zip_file = st.selectbox("Select a ZIP file", options=existing_zip_files)
    else:
        st.info("No existing ZIP files found. Please upload a new ZIP file.")
        selected_zip_file = None

    # Option to upload a new ZIP file
    uploaded_zip_file = st.file_uploader("Upload a new ZIP file containing an OWL file", type=["zip"])

    if uploaded_zip_file is not None:
        # Get the original filename and sanitize it
        original_filename = os.path.basename(uploaded_zip_file.name)
        zip_file_name = original_filename
        zip_file_path = os.path.join(zip_files_directory, zip_file_name)

        # Save the uploaded ZIP file
        with open(zip_file_path, 'wb') as f:
            f.write(uploaded_zip_file.getbuffer())

        st.success(f"Uploaded and saved ZIP file: {zip_file_name}")

        selected_zip_file = zip_file_name

        # Update the list of existing ZIP files if not already present
        if zip_file_name not in existing_zip_files:
            existing_zip_files.append(zip_file_name)

    # Radio buttons to select search type
    search_type = st.radio("Select search type", ("Synonym Search", "Mendel ID Lookup", "Code Search", "Relaxed Code Search", "Semi-Relaxed Code Search"))

    # Provide options to input search terms
    st.write("### Provide search values")
    search_input = st.text_input("Enter search terms separated by '||' (optional)")
    search_values_file = st.file_uploader("Upload a CSV file with a single column 'Values' containing search terms (optional)", type=["csv"])

    # Initialize search_values_list
    search_values_list = []

    # Process the uploaded CSV file if provided
    if search_values_file is not None:
        try:
            search_values_df = pd.read_csv(search_values_file)
            if 'Values' not in search_values_df.columns:
                st.error("CSV file must have a single header 'Values'")
                return
            search_values_list = search_values_df['Values'].dropna().astype(str).tolist()
            st.success(f"Loaded {len(search_values_list)} search values from CSV file.")
        except Exception as e:
            st.error(f"Error reading CSV file: {e}")
            return

    # Process the text input if provided
    if search_input.strip():
        input_values = [value.strip() for value in search_input.split('||') if value.strip()]
        search_values_list.extend(input_values)

    # Check if there are any search values
    if not search_values_list:
        st.error("Please enter search terms in the text box or upload a CSV file.")
        return

    # Button to start the search
    if st.button("Search"):

        if selected_zip_file is None:
            st.error("Please select an existing ZIP file or upload a new one.")
            return

        # Set up logging to capture logs in the Streamlit app
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setFormatter(logging.Formatter('%(message)s'))
        logger.handlers = [handler]

        # Join the search values into a single string if needed by the processing functions
        search_values_input = '||'.join(search_values_list) if search_type != "Mendel ID Lookup" else ','.join(search_values_list)

        # Process the selected ZIP file and search for matches
        try:
            # Read the ZIP file from the shared directory
            zip_file_path = os.path.join(zip_files_directory, selected_zip_file)
            with open(zip_file_path, 'rb') as f:
                zip_file_data = f.read()

            if search_type == "Synonym Search":
                results_df = process_zip_file_synonym_search(zip_file_data, search_values_input, logger)
            elif search_type == "Mendel ID Lookup":
                results_df = process_zip_file_mendel_id_lookup(zip_file_data, search_values_input, logger)
            elif search_type == "Code Search":
                results_df = process_zip_file_code_search(zip_file_data, search_values_input, logger)
            elif search_type == "Relaxed Code Search":
                results_df = process_zip_file_code_value_search(zip_file_data, search_values_input, logger)
            else:
                results_df = process_zip_file_code_value_semi_relaxed_search(zip_file_data, search_values_input, logger)

            st.success("Search completed.")

            if not results_df.empty:
                st.write("### Matches Found:")
                st.dataframe(results_df)

                # Download button for the results
                csv_data = results_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Results as CSV",
                    data=csv_data,
                    file_name='search_results.csv',
                    mime='text/csv',
                )
            else:
                st.info("No exact matches found for the provided search input.")

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

        # Display logs
        st.write("### Logs:")
        st.text(log_stream.getvalue())

def process_zip_file_synonym_search(zip_file_data, search_phrases_input, logger):
    # Read the zip file from bytes
    try:
        with zipfile.ZipFile(io.BytesIO(zip_file_data)) as z:
            # Find the OWL file inside the zip archive
            owl_filenames = [name for name in z.namelist() if name.endswith('.owl') or name.endswith('.xml')]
            if not owl_filenames:
                logger.error("No OWL file found in the ZIP archive.")
                raise Exception("No OWL file found in the ZIP archive.")
            owl_filename = owl_filenames[0]
            with z.open(owl_filename) as owl_content:
                # Read the content of the OWL file
                owl_data = owl_content.read()
                # Convert owl_data to a BytesIO object for parsing
                owl_content = io.BytesIO(owl_data)
                # Call the processing function
                results_df = process_owl_file_synonym_search(owl_content, search_phrases_input, logger)
                return results_df
    except zipfile.BadZipFile:
        logger.error("The uploaded file is not a valid ZIP file.")
        raise Exception("The uploaded file is not a valid ZIP file.")
    except Exception as e:
        logger.error(f"An error occurred while processing the ZIP file: {str(e)}")
        raise

def process_zip_file_mendel_id_lookup(zip_file_data, mendel_ids_input, logger):
    # Read the zip file from bytes
    try:
        with zipfile.ZipFile(io.BytesIO(zip_file_data)) as z:
            # Find the OWL file inside the zip archive
            owl_filenames = [name for name in z.namelist() if name.endswith('.owl') or name.endswith('.xml')]
            if not owl_filenames:
                logger.error("No OWL file found in the ZIP archive.")
                raise Exception("No OWL file found in the ZIP archive.")
            owl_filename = owl_filenames[0]
            with z.open(owl_filename) as owl_content:
                # Read the content of the OWL file
                owl_data = owl_content.read()
                # Convert owl_data to a BytesIO object for parsing
                owl_content = io.BytesIO(owl_data)
                # Call the processing function
                results_df = process_owl_file_mendel_id_lookup(owl_content, mendel_ids_input, logger)
                return results_df
    except zipfile.BadZipFile:
        logger.error("The uploaded file is not a valid ZIP file.")
        raise Exception("The uploaded file is not a valid ZIP file.")
    except Exception as e:
        logger.error(f"An error occurred while processing the ZIP file: {str(e)}")
        raise

def process_zip_file_code_search(zip_file_data, codes_input, logger):
    # Read the zip file from bytes
    try:
        with zipfile.ZipFile(io.BytesIO(zip_file_data)) as z:
            # Find the OWL file inside the zip archive
            owl_filenames = [name for name in z.namelist() if name.endswith('.owl') or name.endswith('.xml')]
            if not owl_filenames:
                logger.error("No OWL file found in the ZIP archive.")
                raise Exception("No OWL file found in the ZIP archive.")
            owl_filename = owl_filenames[0]
            with z.open(owl_filename) as owl_content:
                # Read the content of the OWL file
                owl_data = owl_content.read()
                # Convert owl_data to a BytesIO object for parsing
                owl_content = io.BytesIO(owl_data)
                # Call the processing function
                results_df = process_owl_file_code_search(owl_content, codes_input, logger)
                return results_df
    except zipfile.BadZipFile:
        logger.error("The uploaded file is not a valid ZIP file.")
        raise Exception("The uploaded file is not a valid ZIP file.")
    except Exception as e:
        logger.error(f"An error occurred while processing the ZIP file: {str(e)}")
        raise

def process_zip_file_code_value_search(zip_file_data, codes_input, logger):
    # Read the zip file from bytes
    try:
        with zipfile.ZipFile(io.BytesIO(zip_file_data)) as z:
            # Find the OWL file inside the zip archive
            owl_filenames = [name for name in z.namelist() if name.endswith('.owl') or name.endswith('.xml')]
            if not owl_filenames:
                logger.error("No OWL file found in the ZIP archive.")
                raise Exception("No OWL file found in the ZIP archive.")
            owl_filename = owl_filenames[0]
            with z.open(owl_filename) as owl_content:
                # Read the content of the OWL file
                owl_data = owl_content.read()
                # Convert owl_data to a BytesIO object for parsing
                owl_content = io.BytesIO(owl_data)
                # Call the processing function
                results_df = process_owl_file_code_value_search(owl_content, codes_input, logger)
                return results_df
    except zipfile.BadZipFile:
        logger.error("The uploaded file is not a valid ZIP file.")
        raise Exception("The uploaded file is not a valid ZIP file.")
    except Exception as e:
        logger.error(f"An error occurred while processing the ZIP file: {str(e)}")
        raise

def process_zip_file_code_value_semi_relaxed_search(zip_file_data, codes_input, logger):
    # Similar to process_zip_file_code_value_search but uses the semi-relaxed function
    try:
        with zipfile.ZipFile(io.BytesIO(zip_file_data)) as z:
            # Find the OWL file inside the zip archive
            owl_filenames = [name for name in z.namelist() if name.endswith('.owl') or name.endswith('.xml')]
            if not owl_filenames:
                logger.error("No OWL file found in the ZIP archive.")
                raise Exception("No OWL file found in the ZIP archive.")
            owl_filename = owl_filenames[0]
            with z.open(owl_filename) as owl_content:
                # Read the content of the OWL file
                owl_data = owl_content.read()
                # Convert owl_data to a BytesIO object for parsing
                owl_content = io.BytesIO(owl_data)
                # Call the processing function
                results_df = process_owl_file_code_value_semi_relaxed_search(owl_content, codes_input, logger)
                return results_df
    except zipfile.BadZipFile:
        logger.error("The uploaded file is not a valid ZIP file.")
        raise Exception("The uploaded file is not a valid ZIP file.")
    except Exception as e:
        logger.error(f"An error occurred while processing the ZIP file: {str(e)}")
        raise

def process_owl_file_synonym_search(owl_content, search_phrases_input, logger):
    # Split the search phrases and strip whitespace
    search_phrases = [phrase.strip() for phrase in search_phrases_input.split('||') if phrase.strip()]

    # Convert search phrases to lowercase for case-insensitive matching
    # Create a mapping from cleaned phrase to original phrase(s)
    search_phrases_lower = {}
    for phrase in search_phrases:
        cleaned = phrase.lower()
        search_phrases_lower.setdefault(cleaned, []).append(phrase)

    # Parse the OWL file
    logger.info('Parsing the OWL file...')
    try:
        tree = etree.parse(owl_content)
        root = tree.getroot()
        logger.info('OWL file parsed successfully.')
    except Exception as e:
        logger.error(f"Error parsing OWL file: {e}")
        raise

    # Define the namespaces
    namespaces = {
        'owl': 'http://www.w3.org/2002/07/owl#',
        'owl0': 'http://www.w3.org/2002/07/owl#',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'xml': 'http://www.w3.org/XML/1998/namespace',
        'xsd': 'http://www.w3.org/2001/XMLSchema#',
        'www': 'http://www.w3.org/2002/07/',
        'amr': 'http://www.semanticweb.org/amr/ontologies/2018/',
        # Add or adjust namespaces as needed
    }

    # Find all Class elements
    classes = root.xpath('//owl0:Class', namespaces=namespaces)
    total_classes = len(classes)
    logger.info(f'Found {total_classes} classes in the OWL file.')

    # Initialize a list to store results
    results = []

    # Progress bar
    progress_bar = st.progress(0)

    # Iterate over the classes
    logger.info('Searching for matching synonyms...')
    for idx, cls in enumerate(classes):
        # Update progress bar
        progress = (idx + 1) / total_classes
        progress_bar.progress(progress)

        # Get Mendel_ID
        mendel_id = get_mendel_id(cls, namespaces)

        # Get Synonyms
        synonyms = get_synonyms(cls, namespaces)
        if not synonyms:
            continue

        # Convert synonyms to lowercase for case-insensitive matching
        synonyms_lower = set(syn.lower() for syn in synonyms)

        # Perform exact matching using set intersection
        matches = synonyms_lower.intersection(set(search_phrases_lower.keys()))

        if matches:
            # Get the class label
            class_label = get_class_label(cls, namespaces)

            # Retrieve original search phrases that matched
            original_search_terms = []
            for match in matches:
                original_search_terms.extend(search_phrases_lower[match])

            # Append the result
            results.append({
                'Original Search Term': '; '.join(set(original_search_terms)),
                'Mendel_ID': mendel_id,
                'Class_Label': class_label,
                'Synonyms': '; '.join(synonyms),
                'Matched Synonyms': '; '.join({syn for syn in synonyms if syn.lower() in matches})
            })

            # Log the match
            logger.info(f"Exact match found: Mendel_ID: {mendel_id}, Class_Label: {class_label}, Original Search Term: {', '.join(set(original_search_terms))}")

    # Convert results to DataFrame
    results_df = pd.DataFrame(results)
    return results_df

def process_owl_file_mendel_id_lookup(owl_content, mendel_ids_input, logger):
    # Split the Mendel IDs and strip whitespace
    mendel_ids = [mid.strip() for mid in mendel_ids_input.split(',') if mid.strip()]

    # Build a set for faster lookup
    mendel_ids_set = set(mendel_ids)

    # Parse the OWL file
    logger.info('Parsing the OWL file...')
    try:
        tree = etree.parse(owl_content)
        root = tree.getroot()
        logger.info('OWL file parsed successfully.')
    except Exception as e:
        logger.error(f"Error parsing OWL file: {e}")
        raise

    # Define the namespaces
    namespaces = {
        'owl': 'http://www.w3.org/2002/07/owl#',
        'owl0': 'http://www.w3.org/2002/07/owl#',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'xml': 'http://www.w3.org/XML/1998/namespace',
        'xsd': 'http://www.w3.org/2001/XMLSchema#',
        'www': 'http://www.w3.org/2002/07/',
        'amr': 'http://www.semanticweb.org/amr/ontologies/2018/',
        # Add or adjust namespaces as needed
    }

    # Find all Class elements
    classes = root.xpath('//owl0:Class', namespaces=namespaces)
    total_classes = len(classes)
    logger.info(f'Found {total_classes} classes in the OWL file.')

    # Initialize a list to store results
    results = []

    # Progress bar
    progress_bar = st.progress(0)

    # Iterate over the classes
    logger.info('Searching for Mendel IDs...')
    for idx, cls in enumerate(classes):
        # Update progress bar
        progress = (idx + 1) / total_classes
        progress_bar.progress(progress)

        # Get Mendel_ID
        mendel_id = get_mendel_id(cls, namespaces)

        if mendel_id and mendel_id in mendel_ids_set:
            # Get the class label
            class_label = get_class_label(cls, namespaces)

            # Get Synonyms
            synonyms = get_synonyms(cls, namespaces)

            # Append the result
            results.append({
                'Original Search Term': mendel_id,
                'Mendel_ID': mendel_id,
                'Class_Label': class_label,
                'Synonyms': '; '.join(synonyms) if synonyms else ''
            })

            # Log the match
            logger.info(f"Mendel ID found: Mendel_ID: {mendel_id}, Class_Label: {class_label}")

    # Convert results to DataFrame
    results_df = pd.DataFrame(results)
    return results_df

def process_owl_file_code_search(owl_content, codes_input, logger):
    # Split the codes and strip whitespace
    codes = [code.strip() for code in codes_input.split('||') if code.strip()]

    # Convert codes to lowercase for case-insensitive matching
    # Create a mapping from cleaned code to original code(s)
    codes_lower = {}
    for code in codes:
        cleaned = code.lower()
        codes_lower.setdefault(cleaned, []).append(code)

    # Parse the OWL file
    logger.info('Parsing the OWL file...')
    try:
        tree = etree.parse(owl_content)
        root = tree.getroot()
        logger.info('OWL file parsed successfully.')
    except Exception as e:
        logger.error(f"Error parsing OWL file: {e}")
        raise

    # Define the namespaces
    namespaces = {
        'owl': 'http://www.w3.org/2002/07/owl#',
        'owl0': 'http://www.w3.org/2002/07/owl#',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'xml': 'http://www.w3.org/XML/1998/namespace',
        'xsd': 'http://www.w3.org/2001/XMLSchema#',
        'www': 'http://www.w3.org/2002/07/',
        'amr': 'http://www.semanticweb.org/amr/ontologies/2018/',
        # Add or adjust namespaces as needed
    }

    # Find all Class elements
    classes = root.xpath('//owl0:Class', namespaces=namespaces)
    total_classes = len(classes)
    logger.info(f'Found {total_classes} classes in the OWL file.')

    # Initialize a list to store results
    results = []

    # Progress bar
    progress_bar = st.progress(0)

    # Iterate over the classes
    logger.info('Searching for Codes...')
    for idx, cls in enumerate(classes):
        # Update progress bar
        progress = (idx + 1) / total_classes
        progress_bar.progress(progress)

        # Get Mendel_ID
        mendel_id = get_mendel_id(cls, namespaces)

        # Get Codes
        codes_list = get_codes(cls, namespaces)
        if not codes_list:
            continue

        # Convert codes to lowercase for case-insensitive matching
        codes_list_lower = set(code.lower() for code in codes_list)

        # Perform exact matching using set intersection
        matches = codes_list_lower.intersection(set(codes_lower.keys()))

        if matches:
            # Get the class label
            class_label = get_class_label(cls, namespaces)

            # Retrieve original search terms that matched
            original_search_terms = []
            for match in matches:
                original_search_terms.extend(codes_lower[match])

            # Append the result
            results.append({
                'Original Search Term': '; '.join(set(original_search_terms)),
                'Mendel_ID': mendel_id,
                'Class_Label': class_label,
                'Codes': '; '.join(codes_list),
                'Matched Codes': '; '.join({code for code in codes_list if code.lower() in matches})
            })

            # Log the match
            logger.info(f"Code match found: Mendel_ID: {mendel_id}, Class_Label: {class_label}, Original Search Term: {', '.join(set(original_search_terms))}")

    # Convert results to DataFrame
    results_df = pd.DataFrame(results)
    return results_df

def process_owl_file_code_value_search(owl_content, codes_input, logger):
    # Split the codes and strip whitespace
    codes = [code.strip() for code in codes_input.split('||') if code.strip()]

    # Clean up the user input codes: remove spaces, dots, special characters, make lowercase
    def clean_code(code):
        return re.sub(r'[^A-Za-z0-9]', '', code).lower()

    # Create a mapping from cleaned code to original code(s)
    cleaned_to_original = {}
    for code in codes:
        cleaned = clean_code(code)
        cleaned_to_original.setdefault(cleaned, []).append(code)

    codes_cleaned = set(cleaned_to_original.keys())

    # Parse the OWL file
    logger.info('Parsing the OWL file...')
    try:
        tree = etree.parse(owl_content)
        root = tree.getroot()
        logger.info('OWL file parsed successfully.')
    except Exception as e:
        logger.error(f"Error parsing OWL file: {e}")
        raise

    # Define the namespaces
    namespaces = {
        'owl': 'http://www.w3.org/2002/07/owl#',
        'owl0': 'http://www.w3.org/2002/07/owl#',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'xml': 'http://www.w3.org/XML/1998/namespace',
        'xsd': 'http://www.w3.org/2001/XMLSchema#',
        'www': 'http://www.w3.org/2002/07/',
        'amr': 'http://www.semanticweb.org/amr/ontologies/2018/',
        # Add or adjust namespaces as needed
    }

    # Find all Class elements
    classes = root.xpath('//owl0:Class', namespaces=namespaces)
    if not classes:
        classes = root.xpath('//owl:Class', namespaces=namespaces)
    total_classes = len(classes)
    logger.info(f'Found {total_classes} classes in the OWL file.')

    # Initialize a list to store results
    results = []

    # Progress bar
    progress_bar = st.progress(0)

    # Iterate over the classes
    logger.info('Searching for Codes with relaxed matching...')
    for idx, cls in enumerate(classes):
        # Update progress bar
        progress = (idx + 1) / total_classes
        progress_bar.progress(progress)

        # Get Mendel_ID
        mendel_id = get_mendel_id(cls, namespaces)

        # Get Codes
        codes_list = get_codes(cls, namespaces)
        if not codes_list:
            continue

        # Process each code
        matched_codes = []
        original_search_terms = []
        for code_entry in codes_list:
            # Assume code_entry is in format "coding system: code value"
            # Split by ':', take the code value
            parts = code_entry.split(':')
            if len(parts) >= 2:
                code_value = ':'.join(parts[1:]).strip()
            else:
                # If no ':', assume the whole code_entry is the code value
                code_value = code_entry.strip()

            # Clean up code value
            code_value_cleaned = clean_code(code_value)

            # Check if code_value_cleaned matches any of the user input codes
            if code_value_cleaned in codes_cleaned:
                matched_codes.append(code_entry)
                original_search_terms.extend(cleaned_to_original[code_value_cleaned])

        if matched_codes:
            # Get the class label
            class_label = get_class_label(cls, namespaces)

            # Append the result
            results.append({
                'Original Search Term': '; '.join(set(original_search_terms)),
                'Mendel_ID': mendel_id,
                'Class_Label': class_label,
                'Codes': '; '.join(codes_list),
                'Matched Codes': '; '.join(matched_codes)
            })

            # Log the match
            logger.info(f"Code value match found: Mendel_ID: {mendel_id}, Class_Label: {class_label}, Original Search Term: {', '.join(set(original_search_terms))}")

    # Convert results to DataFrame
    results_df = pd.DataFrame(results)
    return results_df

def process_owl_file_code_value_semi_relaxed_search(owl_content, codes_input, logger):
    # Split the codes and strip whitespace
    codes = [code.strip() for code in codes_input.split('||') if code.strip()]

    # Clean up the user input codes: remove dots, make lowercase
    def clean_code(code):
        return code.replace('.', '').lower()

    # Create a mapping from cleaned code to original code(s)
    cleaned_to_original = {}
    for code in codes:
        cleaned = clean_code(code)
        cleaned_to_original.setdefault(cleaned, []).append(code)

    codes_cleaned = set(cleaned_to_original.keys())

    # Parse the OWL file
    logger.info('Parsing the OWL file...')
    try:
        tree = etree.parse(owl_content)
        root = tree.getroot()
        logger.info('OWL file parsed successfully.')
    except Exception as e:
        logger.error(f"Error parsing OWL file: {e}")
        raise

    # Define the namespaces (same as before)
    namespaces = {
        'owl': 'http://www.w3.org/2002/07/owl#',
        'owl0': 'http://www.w3.org/2002/07/owl#',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'xml': 'http://www.w3.org/XML/1998/namespace',
        'xsd': 'http://www.w3.org/2001/XMLSchema#',
        'www': 'http://www.w3.org/2002/07/',
        'amr': 'http://www.semanticweb.org/amr/ontologies/2018/',
        # Add or adjust namespaces as needed
    }

    # Find all Class elements
    classes = root.xpath('//owl0:Class', namespaces=namespaces)
    if not classes:
        classes = root.xpath('//owl:Class', namespaces=namespaces)
    total_classes = len(classes)
    logger.info(f'Found {total_classes} classes in the OWL file.')

    # Initialize a list to store results
    results = []

    # Progress bar
    progress_bar = st.progress(0)

    # Iterate over the classes
    logger.info('Searching for Codes with semi-relaxed matching...')
    for idx, cls in enumerate(classes):
        # Update progress bar
        progress = (idx + 1) / total_classes
        progress_bar.progress(progress)

        # Get Mendel_ID
        mendel_id = get_mendel_id(cls, namespaces)

        # Get Codes
        codes_list = get_codes(cls, namespaces)
        if not codes_list:
            continue

        # Process each code
        matched_codes = []
        original_search_terms = []
        for code_entry in codes_list:
            # Assume code_entry is in format "coding system: code value"
            # Split by ':', take the code value
            parts = code_entry.split(':')
            if len(parts) >= 2:
                code_value = ':'.join(parts[1:]).strip()
            else:
                # If no ':', assume the whole code_entry is the code value
                code_value = code_entry.strip()

            # Clean up code value
            code_value_cleaned = clean_code(code_value)

            # Check if code_value_cleaned matches any of the user input codes
            if code_value_cleaned in codes_cleaned:
                matched_codes.append(code_entry)
                original_search_terms.extend(cleaned_to_original[code_value_cleaned])

        if matched_codes:
            # Get the class label
            class_label = get_class_label(cls, namespaces)

            # Append the result
            results.append({
                'Original Search Term': '; '.join(set(original_search_terms)),
                'Mendel_ID': mendel_id,
                'Class_Label': class_label,
                'Codes': '; '.join(codes_list),
                'Matched Codes': '; '.join(matched_codes)
            })

            # Log the match
            logger.info(f"Code value match found: Mendel_ID: {mendel_id}, Class_Label: {class_label}, Original Search Term: {', '.join(set(original_search_terms))}")

    # Convert results to DataFrame
    results_df = pd.DataFrame(results)
    return results_df

def get_mendel_id(cls, namespaces):
    # Get Mendel_ID
    mendel_id_elems = cls.xpath('.//owl0:Mendel_ID', namespaces=namespaces)
    if not mendel_id_elems:
        mendel_id_elems = cls.xpath('.//*[local-name()="Mendel_ID"]')
    mendel_id = mendel_id_elems[0].text.strip() if mendel_id_elems else None
    return mendel_id

def get_synonyms(cls, namespaces):
    # Get Synonyms
    synonyms_elems = cls.xpath('.//owl0:Synonyms', namespaces=namespaces)
    if not synonyms_elems:
        synonyms_elems = cls.xpath('.//*[local-name()="Synonyms"]')
    if synonyms_elems:
        synonyms_text = synonyms_elems[0].text or ''
        synonyms = [syn.strip() for syn in synonyms_text.replace('\n', ';').split(';') if syn.strip()]
    else:
        synonyms = []
    return synonyms

def get_class_label(cls, namespaces):
    # Get the class label
    label_elems = cls.xpath('.//rdfs:label', namespaces=namespaces)
    if not label_elems:
        label_elems = cls.xpath('.//*[local-name()="label"]')
    class_label = label_elems[0].text.strip() if label_elems else 'No label'
    return class_label

def get_codes(cls, namespaces):
    # Get Codes elements
    codes_elems = cls.xpath('.//owl0:Codes', namespaces=namespaces)
    if not codes_elems:
        codes_elems = cls.xpath('.//owl:Codes', namespaces=namespaces)
    if not codes_elems:
        codes_elems = cls.xpath('.//rdfs:Codes', namespaces=namespaces)
    if not codes_elems:
        codes_elems = cls.xpath('.//*[local-name()="Codes"]')

    codes_list = []
    for code_elem in codes_elems:
        code_text = code_elem.text or ''
        codes = [code.strip() for code in re.split(';|\n', code_text) if code.strip()]
        codes_list.extend(codes)
    return codes_list

if __name__ == '__main__':
    main()
