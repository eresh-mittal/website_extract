import streamlit as st
import requests
from typing import List
import os
import logging

# logging.basicConfig(level=logging.INFO, filename="py_log.log", filemode="w")

st.set_page_config(
    page_title="Web Content Q&A Tool",
    page_icon="🔍",
    layout="wide"
)

API_URL = os.getenv("API_URL", "http://localhost:8000")
# logging.info(API_URL)

if 'urls' not in st.session_state:
    st.session_state.urls = []


st.title("Web Content Q&A Tool")
st.markdown("""
This tool allows you to:
1. Enter one or more URLs to extract content
2. Ask questions about the content from those URLs
3. Get answers based solely on the extracted information
""")


def extract_content(urls: List[str]):
    try:
        response = requests.post(
            f"{API_URL}/extract-content",
            json={"urls": urls}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error extracting content: {str(e)}")
        return None


def ask_question(question: str, urls: List[str]):
    try:
        response = requests.post(
            f"{API_URL}/ask-question",
            json={"question": question, "urls": urls}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error asking question: {str(e)}")
        return None


def get_stored_urls():
    try:
        response = requests.get(f"{API_URL}/get-urls")
        logging.info(response)
        response.raise_for_status()
        return response.json().get("urls", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching stored URLs: {str(e)}")
        return []


with st.sidebar:
    st.header("Add URLs to Analyze")
    

    url_input = st.text_input("Enter a URL (include http:// or https://)", key="url_input")
    

    if st.button("Add URL"):
        if url_input and url_input.startswith(("http://", "https://")):
            if url_input not in st.session_state.urls:
                st.session_state.urls.append(url_input)
                st.success(f"Added: {url_input}")
            else:
                st.warning("This URL is already in your list")
        else:
            st.error("Please enter a valid URL (including http:// or https://)")

    if st.session_state.urls:
        st.subheader("Your URLs:")
        for i, url in enumerate(st.session_state.urls):
            st.write(f"{i+1}. {url}")
        
        if st.button("Process All URLs"):
            with st.spinner("Extracting content from URLs..."):
                result = extract_content(st.session_state.urls)
                if result:
                    st.success("Content extracted successfully!")
                    st.write(f"Extracted content from {len(result['character_counts'])} URLs")
        
        if st.button("Clear All URLs"):
            st.session_state.urls = []
            st.info("URL list cleared")

st.header("Ask a Question")

stored_urls = get_stored_urls()

if not stored_urls:
    st.info("No content has been extracted yet. Please add URLs in the sidebar and process them.")
else:
    st.success(f"Content extracted from {len(stored_urls)} URLs")

    st.subheader("Select URLs to query")
    selected_urls = []
    
    for url in stored_urls:
        if st.checkbox(url, value=True, key=f"check_{url}"):
            selected_urls.append(url)
    print(stored_urls)

    question = st.text_input("Enter your question about the content:", key="question_input")
    
    if st.button("Submit Question") and question and selected_urls:
        with st.spinner("Finding answer..."):
            result = ask_question(question, selected_urls)
            
            if result and "answer" in result:
                st.subheader("Answer:")
                st.write(result["answer"])
            else:
                st.error("Failed to get an answer. Please try again.")
    elif not selected_urls and st.session_state.get("question_input"):
        st.warning("Please select at least one URL to query")
