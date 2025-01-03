# ==========================
# Imports
# ==========================

import streamlit as st
import pandas as pd
import numpy as np
import openai
import PyPDF2
import pytesseract
from pdf2image import convert_from_bytes
import io
import json
import zipfile
from PyPDF2 import PdfReader
import os  # For file path operations
import openpyxl

# For authentication
import streamlit_authenticator as stauth  # Make sure to install this package

# For custom footer styling
from htbuilder import HtmlElement, div, hr, p, a, img, styles, br
from htbuilder.units import percent, px

# Set your OpenAI API key
openai.api_key = st.secrets["openai_key"]

def extract_text_from_pdf(pdf_content):
    """
    Extract text from a PDF document. If the PDF is image-based, perform OCR.

    Parameters:
    - pdf_content (bytes): PDF data in bytes.

    Returns:
    - str or None: Extracted text or None if extraction fails.
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_content))
        text = ''
        is_text_based = False

        # Process all pages
        num_pages = len(reader.pages)
        pages = reader.pages[:num_pages]

        # Check if PDF is text-based
        for page in pages:
            page_text = page.extract_text()
            if page_text and page_text.strip():
                is_text_based = True
                text += page_text + '\n'

        if not is_text_based:
            # PDF is image-based; use OCR
            st.info("PDF is image-based. Performing OCR...")
            images = convert_from_bytes(pdf_content)
            text = ''
            for image in images:
                extracted_text = pytesseract.image_to_string(image)
                text += extracted_text + '\n'
            print(text)
            return text
        else:
            print(text)
            return text
    except Exception as e:
        st.error(f"Error extracting text from PDF: {e}")
        return None

# ==========================
# Helper Functions
# ==========================

def extract_sds_fields_with_gpt(text):
    """
    Extract required fields from the text using GPT.

    Parameters:
    - text (str): Text extracted from the SDS PDF.

    Returns:
    - dict: Extracted fields or default values if extraction fails.
    """
    prompt = f"""
You are an assistant that extracts key information from Safety Data Sheets (SDS). Read through the whole document before identifying the fields below. The starting pages may be blank or cover letters, keep reading.

Given the following text extracted from an SDS document, extract and provide the following information in English:

- Chemical Product (think through, might be mentioned anywhere in the file, including the title name. Might be called product name, etc.)
- Manufacturer's Name (think through, could be the logo somewhere, could be mentioned in the address, etc. think and reason)
- Manufacturer's Country (think through, maybe it's in the address, or mentioned elsewhere.)
- Language (identify this field by recognizing the language the SDS is in)
- SDS Revision Date (convert it to MM-DD-YYYY format)
- Product Number (if available)
- Trade Name (name the product is traded by / commonly known name)
- Manufacturer Contact (email address)
- Emergency Phone
- Phone Number
- Fax Number
- Manufacturer Street
- Manufacturer City
- Manufacturer State
- Manufacturer ZIP Code

Provide your findings in valid JSON format. Do not include any markdown formatting, backticks, or the word 'json'. Just return the raw JSON object.

If any of the fields are not available, use an empty string ("") as the value. If the document is not an SDS, use "Not SDS" as the value for the "Parsing Notes" field and leave all other fields empty.

Text:
\"\"\"
{text}
\"\"\"
"""
    try:
        # First, check if the input text is empty or None
        if not text or not text.strip():
            raise ValueError("Input text is empty")

        response = openai.chat.completions.create(
            model="gpt-4o",  
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0,
        )

        # Get the response content and clean it up
        output = response.choices[0].message.content.strip()

        # Remove markdown code block formatting if present
        output = output.replace('```json', '').replace('```', '').strip()

        print(f"Cleaned output: {output}")

        # Ensure the output is valid JSON
        try:
            extracted_fields = json.loads(output)
            print(f"Successfully parsed JSON: {extracted_fields}")
            return extracted_fields

        except json.JSONDecodeError as json_err:
            print(f"JSON Decode Error: {json_err}")
            print(f"Raw output: {output}")
            # Return empty values if JSON parsing fails
            return {}

    except Exception as e:
        print(f"Extraction error: {str(e)}")
        st.error(f"Error extracting fields with GPT: {str(e)}")
        # Return empty values if any error occurs
        return {}

# ==========================
# Footer Functions
# ==========================

def layout(*args):
    style = """
    <style>
      # MainMenu {visibility: hidden;}
      footer {visibility: hidden;}
      .stApp { bottom: 105px; }
    </style>
    """

    style_div = styles(
        position="fixed",
        left=0,
        bottom=0,
        margin=px(0, 0, 0, 0),
        width=percent(100),
        color="black",
        text_align="center",
        height="auto",
        opacity=1
    )

    style_hr = styles(
        display="block",
        margin=px(4, 4, "auto", "auto"),
        border_style="inset",
        border_width=px(1)
    )

    body = p()
    foot = div(
        style=style_div
    )(
        hr(
            style=style_hr
        ),
        body
    )

    st.markdown(style, unsafe_allow_html=True)

    for arg in args:
        if isinstance(arg, str):
            body(arg)
        elif isinstance(arg, HtmlElement):
            body(arg)

    st.markdown(str(foot), unsafe_allow_html=True)

def footer():
    myargs = [
        "© Benchmark Gensuite 2024",
        br(),
        a('benchmarkgensuite.com', href='https://benchmarkgensuite.com/')
    ]
    layout(*myargs)

# ==========================
# Main Functionality
# ==========================

def main():
    st.set_page_config(page_title='SDS Data Extraction Tool', page_icon='bench.png', layout='wide')
    st.sidebar.image('bench.png', width=250)
    # Initialize authentication status in session state if not set
    if 'authentication_status' not in st.session_state:
        st.session_state['authentication_status'] = None

    # Page Header with Logo
    col1, col2, col3 = st.columns([1, 6, 1])
    with col2:
        st.title("SDS Data Extraction Tool")
    with col3:
        st.image('bench.png', width=250)

    # Retrieve credentials from st.secrets
    admin_username = st.secrets["auth"]["admin_username"]
    admin_password = st.secrets["auth"]["admin_password"]
    user_username = st.secrets["auth"]["user_username"]
    user_password = st.secrets["auth"]["user_password"]

    # User Authentication
    names = ['Admin User', 'C&I User']
    usernames = [admin_username, user_username]
    passwords = [admin_password, user_password]

    hashed_passwords_0 = stauth.Hasher.hash(passwords[0])
    hashed_passwords_1 = stauth.Hasher.hash(passwords[1])

    credentials = {
        'usernames': {
            admin_username: {
                'name': 'Admin User',
                'email': 'admin@benchmarkgensuite.com',
                'password': hashed_passwords_0
            },
            user_username: {
                'name': 'User',
                'email': 'user@benchmarkgensuite.com',
                'password': hashed_passwords_1
            }
        }
    }

    authenticator = stauth.Authenticate(credentials, 'some_cookie_name', 'some_signature_key', cookie_expiry_days=30)

    # Update the login call
    authenticator.login('main')

    # Access authentication status from st.session_state
    if st.session_state['authentication_status']:
        authenticator.logout('Logout', 'sidebar')
        st.sidebar.write(f"Welcome *{st.session_state['name']}*")

        # Determine user type
        if st.session_state['username'] == admin_username:
            user_type = 'admin'
        else:
            user_type = 'user'

        # Main app code
        # File uploader for SDS PDFs
        st.write("Upload a ZIP file containing SDS PDF files:")
        uploaded_file = st.file_uploader("", type=["zip"])

        if uploaded_file is not None:
            st.write("Processing the uploaded ZIP file...")
            # Read the ZIP file content
            zip_content = uploaded_file.read()
            with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
                # Get list of PDF files in the ZIP, excluding macOS metadata files
                pdf_files = [
                    file for file in z.namelist()
                    if file.lower().endswith('.pdf')
                    and not '__macosx' in file.lower()
                    and not os.path.basename(file).startswith('._')
                ]

                if not pdf_files:
                    st.error("No PDF files found in the ZIP archive.")
                else:
                    all_extracted_fields = []
                    total_pdfs = len(pdf_files)
                    for idx, pdf_file in enumerate(pdf_files, start=1):
                        st.write(f"Processing {idx} of {total_pdfs}: {os.path.basename(pdf_file)}...")
                        try:
                            # Read each PDF file
                            pdf_content = z.read(pdf_file)
                            # Extract text from the PDF
                            text = extract_text_from_pdf(pdf_content)
                            if text:
                                # Use GPT to extract the required fields
                                extracted_fields = extract_sds_fields_with_gpt(text)
                                # Initialize Parsing Notes
                                parsing_notes = ""
                                # Check if the document is not an SDS
                                if "Not SDS" in extracted_fields.values():
                                    # Set all fields to empty except 'Parsing Notes'
                                    extracted_fields = {key: "" for key in extracted_fields.keys()}
                                    parsing_notes = "Not an SDS"
                                else:
                                    # Identify missing fields
                                    missing_fields = [field for field, value in extracted_fields.items() if value == ""]
                                    if missing_fields:
                                        parsing_notes = "Missing: " + ', '.join(missing_fields)
                                # Add the PDF file name to the extracted fields
                                extracted_fields['Scanned SDS Document File Name'] = os.path.basename(pdf_file)
                                # Add Parsing Notes to the extracted fields
                                extracted_fields['Parsing Notes'] = parsing_notes
                                all_extracted_fields.append(extracted_fields)
                            else:
                                st.error(f"Failed to extract text from {os.path.basename(pdf_file)}.")
                        except Exception as e:
                            st.error(f"Error processing {os.path.basename(pdf_file)}: {e}")
                    if all_extracted_fields:
                        st.write("Extracted fields from all SDS files:")
                        # Convert the list of dictionaries to a DataFrame for display
                        df = pd.DataFrame(all_extracted_fields)
                        # Reorder columns: Move 'Scanned SDS Document File Name' to the first column
                        cols = df.columns.tolist()
                        cols.insert(0, cols.pop(cols.index('Scanned SDS Document File Name')))
                        df = df[cols]
                        # Display the DataFrame
                        st.dataframe(df)
                        # Save DataFrame to an Excel file in memory
                        excel_file = io.BytesIO()
                        df.to_excel(excel_file, index=False, engine='openpyxl')
                        excel_file.seek(0)  # Move the pointer to the beginning of the stream
                        # Create a download button for the Excel file
                        st.download_button(
                            label="Download Extracted Data as Excel",
                            data=excel_file,
                            file_name='extracted_sds_data.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )
                    else:
                        st.error("Failed to extract fields from any SDS files.")

    elif st.session_state['authentication_status'] == False:
        st.error('Username or password is incorrect')
    elif st.session_state['authentication_status'] is None:
        st.warning('Please enter your username and password')
        
    footer()

# Run the main function
if __name__ == "__main__":
    main()
