import streamlit as st
import pandas as pd
from google import genai
import base64
import io
import os
import time

# Streamlit page configuration
st.set_page_config(page_title="PDF Table Extractor", layout="wide")

# Title and description
st.title("PDF Table Extractor")
st.markdown("Upload a PDF file to extract table data and download it as an Excel file.")

# API Key input
# api_key = st.text_input("Enter your Gemini API Key", type="password")

# File uploader for PDF
uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

def extract_table_from_pdf(file, api_key, max_retries=3, min_rows_expected=10):
    try:
        client = genai.Client(api_key=AIzaSyBnTpfIzhT8wGku1feH-Nv5yGVOL3jHGv0)
        temp_file_path = "temp.pdf"
        with open(temp_file_path, "wb") as f:
            f.write(file.read())
        
        my_file = client.files.upload(file=temp_file_path)
        
        for attempt in range(max_retries):
            st.write(f"Attempt {attempt + 1}/{max_retries} to extract table...")
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[my_file, """Extract all table text and give me output in table structure format (markdown table), ignore out-of-table text. Ensure all rows and columns are captured."""]
            )
            
            if response.text and " | " in response.text:
                lines = response.text.split("\n")
                table_rows = [line for line in lines if line.strip().startswith("|")]
                data_rows = len(table_rows) - 1  # Subtract header row
                
                st.write(f"Extracted {data_rows} data rows on attempt {attempt + 1}")
                
                if data_rows >= min_rows_expected:
                    os.remove(temp_file_path)
                    return response.text
            
            st.warning(f"Attempt {attempt + 1} did not extract enough data. Retrying...")
            time.sleep(2)
        
        os.remove(temp_file_path)
        st.error("Failed to extract sufficient table data after maximum retries.")
        return None
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        return None

def parse_table_text(table_text):
    lines = table_text.split("\n")
    headers = []
    data = []
    
    for line in lines:
        if line.strip().startswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if not headers:
                headers = cells  # Set headers from the first valid row
            else:
                # Filter out rows that are just separators or repeats of headers
                if not all(cell in ["", "------", "-", headers[i]] for i, cell in enumerate(cells)):
                    data.append(cells)
    
    df = pd.DataFrame(data, columns=headers)
    return df

def get_excel_download_link(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Table_Data')
    excel_data = output.getvalue()
    
    b64 = base64.b64encode(excel_data).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="extracted_table.xlsx">Download Excel File</a>'
    return href

if uploaded_file is not None and api_key:
    with st.spinner("Extracting table from PDF..."):
        table_text = extract_table_from_pdf(uploaded_file, api_key, max_retries=3, min_rows_expected=10)
        
        if table_text:
            df = parse_table_text(table_text)
            if not df.empty:
                st.subheader("Extracted Table")
                st.dataframe(df, use_container_width=True)
                st.subheader("Download")
                st.markdown(get_excel_download_link(df), unsafe_allow_html=True)
            else:
                st.warning("No valid table data parsed from the response.")
        else:
            st.warning("No table data extracted from the PDF.")
else:
    st.info("Please provide both a valid API key and a PDF file to proceed.")
