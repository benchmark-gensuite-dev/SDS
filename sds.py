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

# For authentication
import streamlit_authenticator as stauth  # Make sure to install this package

# For custom footer styling
from htbuilder import HtmlElement, div, hr, p, a, img, styles
from htbuilder.units import percent, px

# Set your OpenAI API key
openai.api_key = st.secrets["openai_key"]

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
You are an assistant that extracts key information from Safety Data Sheets (SDS).

Given the following text extracted from an SDS document, extract and provide the following information in English:

- Chemical Product
- Manufacturer's Name
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

If any of the fields are not available, use "Not Available" as the value. If the document is not an SDS, use "Not SDS" as value.

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
            model="gpt-4o",  # Using model 'gpt-4o' as per your instruction
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
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
            # Return default values if JSON parsing fails
            return {
                "Chemical Product": "Not Available",
                "Manufacturer's Name": "Not Available",
                "Manufacturer's Country": "Not Available",
                "Language": "Not Available",
                "SDS Revision Date": "Not Available",
                "Product Number": "Not Available",
                "Trade Name": "Not Available",
                "Manufacturer Contact": "Not Available",
                "Emergency Phone": "Not Available",
                "Phone Number": "Not Available",
                "Fax Number": "Not Available",
                "Manufacturer Street": "Not Available",
                "Manufacturer City": "Not Available",
                "Manufacturer State": "Not Available",
                "Manufacturer ZIP Code": "Not Available"
            }

    except Exception as e:
        print(f"Extraction error: {str(e)}")
        st.error(f"Error extracting fields with GPT: {str(e)}")
        # Return default values if any error occurs
        return {
            "Chemical Product": "Not Available",
            "Manufacturer's Name": "Not Available",
            "Manufacturer's Country": "Not Available",
            "Language": "Not Available",
            "SDS Revision Date": "Not Available",
            "Product Number": "Not Available",
            "Trade Name": "Not Available",
            "Manufacturer Contact": "Not Available",
            "Emergency Phone": "Not Available",
            "Phone Number": "Not Available",
            "Fax Number": "Not Available",
            "Manufacturer Street": "Not Available",
            "Manufacturer City": "Not Available",
            "Manufacturer State": "Not Available",
            "Manufacturer ZIP Code": "Not Available"
        }

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

    # Page Header with Logo
    col1, col2, col3 = st.columns([1, 6, 1])
    with col2:
        st.title("SDS Data Extraction Tool")
    with col3:
        st.image('logo.png', width=150)

    # Retrieve credentials from st.secrets
    admin_username = st.secrets["auth"]["admin_username"]
    admin_password = st.secrets["auth"]["admin_password"]
    user_username = st.secrets["auth"]["user_username"]
    user_password = st.secrets["auth"]["user_password"]

    # User Authentication
    names = ['Admin User', 'Regular User']
    usernames = [admin_username, user_username]
    passwords = [admin_password, user_password]

    hashed_passwords = stauth.Hasher(passwords).generate()

    credentials = {
        'usernames': {
            usernames[0]: {
                'name': names[0],
                'email': 'admin@example.com',
                'password': hashed_passwords[0]
            },
            usernames[1]: {
                'name': names[1],
                'email': 'user@example.com',
                'password': hashed_passwords[1]
            }
        }
    }

    authenticator = stauth.Authenticate(credentials, 'sds_extraction_app', 'some_signature_key', cookie_expiry_days=30)

    # Login
    name, authentication_status, username = authenticator.login('Login', 'main')

    if authentication_status:
        authenticator.logout('Logout', 'sidebar')
        st.sidebar.write(f"Welcome *{name}*")

        # Determine user type
        if username == admin_username:
            user_type = 'admin'
        else:
            user_type = 'user'

        # Place your main app code here
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
                                # Add the PDF file name to the extracted fields
                                extracted_fields['Scanned SDS Document File Name'] = os.path.basename(pdf_file)
                                all_extracted_fields.append(extracted_fields)
                            else:
                                st.error(f"Failed to extract text from {os.path.basename(pdf_file)}.")
                        except Exception as e:
                            st.error(f"Error processing {os.path.basename(pdf_file)}: {e}")
                    if all_extracted_fields:
                        st.write("Extracted fields from all SDS files:")
                        # Convert the list of dictionaries to a DataFrame for display
                        df = pd.DataFrame(all_extracted_fields)
                        st.dataframe(df)
                        # Optionally, allow the user to download the extracted data
                        csv = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Download Extracted Data as CSV",
                            data=csv,
                            file_name='extracted_sds_data.csv',
                            mime='text/csv',
                        )
                    else:
                        st.error("Failed to extract fields from any SDS files.")

        # Add the footer at the end of the main content
        footer()

    elif authentication_status == False:
        st.error('Username or password is incorrect')
    elif authentication_status == None:
        st.warning('Please enter your username and password')

# Run the main function
if __name__ == "__main__":
    main()
