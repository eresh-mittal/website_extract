from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict
import asyncio

from llama_index.core import Document, VectorStoreIndex
from llama_index.core import Settings
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.llms.huggingface import HuggingFaceLLM
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

app = FastAPI(title="Web Content Q&A API using LlamaIndex")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class URLInput(BaseModel):
    urls: List[HttpUrl]


class QuestionInput(BaseModel):
    question: str
    urls: List[str]


async def initialize_llama_index():

    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-m3",
                                       cache_folder="./hf_cache")

    llm = HuggingFaceLLM(
        model_name="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        tokenizer_name="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        context_window=2048,
        max_new_tokens=512
    )

    Settings.llm = llm
    Settings.embed_model = embed_model
    Settings.node_parser = SimpleNodeParser.from_defaults(
        chunk_size=512, chunk_overlap=50
    )


loop = asyncio.get_event_loop()
loop.create_task(initialize_llama_index())

url_documents: Dict[str, Document] = {}
url_indices: Dict[str, VectorStoreIndex] = {}


def extract_text_from_url(url: str) -> str:
    """Extract text content from a URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for script in soup(["script", "style"]):
            script.extract()

        text = soup.get_text()

        lines = (line.strip() for line in text.splitlines())

        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))

        text = "\n".join(chunk for chunk in chunks if chunk)

        text = re.sub(r"\s+", " ", text).strip()

        return text
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to extract content from {url}: {str(e)}"
        )


@app.post("/extract-content")
def extract_content(input_data: URLInput):
    """Extract content from provided URLs and store it as LlamaIndex Documents."""
    result = {}

    for url in input_data.urls:
        url_str = str(url)
        extracted_text = extract_text_from_url(url_str)

        document = Document(text=extracted_text, metadata={"source": url_str})

        url_documents[url_str] = document

        index = VectorStoreIndex.from_documents([document])
        url_indices[url_str] = index

        result[url_str] = len(extracted_text)

    return {
        "message": "Content extracted and indexed successfully",
        "character_counts": result,
    }


@app.post("/ask-question")
def ask_question(input_data: QuestionInput):
    """Answer a question using LlamaIndex RAG pipeline."""
    for url in input_data.urls:
        if url not in url_indices:
            raise HTTPException(
                status_code=400,
                detail=f"No indexed content found for URL: {url}. Please extract content first.",
            )

    question = input_data.question.strip()

    try:
        if len(input_data.urls) == 1:
            url = input_data.urls[0]
            query_engine = url_indices[url].as_query_engine(similarity_top_k=3)
            response = query_engine.query(question)
            
            # Check if retrieved nodes have sufficient relevance scores
            retrieved_nodes = response.source_nodes
            print(retrieved_nodes, (node.score < 0.5 for node in retrieved_nodes))
            if not retrieved_nodes or all(node.score < 0.5 for node in retrieved_nodes):
                return {"answer": "I couldn't find relevant information to answer this question in the provided content."}
            
            answer = str(response)
        else:
            all_responses = []
            for url in input_data.urls:
                query_engine = url_indices[url].as_query_engine(similarity_top_k=2)
                response = query_engine.query(question)
                retrieved_nodes = response.source_nodes
                if not retrieved_nodes or all(node.score < 0.7 for node in retrieved_nodes):
                    response=""
                all_responses.append(str(response))

            answer = " ".join(all_responses)
    
            if len(answer.strip()) == 0:
                return {"answer": "I couldn't find relevant information to answer this question in the provided content."}

        return {"answer": answer}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying index: {str(e)}")


@app.get("/get-urls")
def get_urls():
    """Get a list of URLs that have content extracted and indexed."""
    return {"urls": list(url_indices.keys())}

@app.get("/")
def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"}