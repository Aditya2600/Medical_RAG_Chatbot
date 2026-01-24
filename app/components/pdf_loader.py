import os
import uuid
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.common.logger import get_logger
from app.common.custom_exception import CustomException

from app.config.config import (
    DATA_PATH,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    PARENT_CHUNK_SIZE,
    PARENT_CHUNK_OVERLAP,
)

logger = get_logger(__name__)

def load_pdf_files():
    try:
        if not os.path.exists(DATA_PATH):
            raise CustomException("Data path doesnt exists")
        
        logger.info(f"Loading files from {DATA_PATH}")
        
        loader = DirectoryLoader(DATA_PATH, glob="*.pdf", loader_cls = PyPDFLoader)
        
        documents = loader.load()
        
        if not documents:
            logger.warning("No pdfs were found")
        else:
            logger.info(f"Sucessfully fetched {len(documents)} documents")
            
        return documents
    
    except Exception as e:
        error_message = CustomException("Failed to load", e)
        logger.error(str(error_message))
        return []
    
def create_parent_child_chunks(documents):
    try:
        if not documents:
            raise CustomException("No documents were found")

        logger.info(f"Splitting {len(documents)} documents into parent chunks")

        parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=PARENT_CHUNK_SIZE, chunk_overlap=PARENT_CHUNK_OVERLAP
        )
        child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
        )

        parent_docs = parent_splitter.split_documents(documents)
        child_docs = []

        for parent_index, parent_doc in enumerate(parent_docs):
            parent_id = str(uuid.uuid4())
            parent_metadata = dict(parent_doc.metadata or {})
            parent_metadata.update(
                {
                    "parent_id": parent_id,
                    "parent_index": parent_index,
                    "chunk_type": "parent",
                }
            )
            parent_doc.metadata = parent_metadata

            child_chunks = child_splitter.split_text(parent_doc.page_content)
            for child_index, chunk in enumerate(child_chunks):
                child_metadata = dict(parent_metadata)
                child_metadata.update(
                    {
                        "child_index": child_index,
                        "chunk_type": "child",
                    }
                )
                child_docs.append(
                    Document(page_content=chunk, metadata=child_metadata)
                )

        logger.info(
            "Generated %s parent chunks and %s child chunks",
            len(parent_docs),
            len(child_docs),
        )
        return parent_docs, child_docs

    except Exception as e:
        error_message = CustomException("Failed to generate chunks", e)
        logger.error(str(error_message))
        return [], []


def create_text_chunks(documents):
    try:
        parent_docs, child_docs = create_parent_child_chunks(documents)
        return child_docs
    except Exception as e:
        error_message = CustomException("Failed to generate chunks", e)
        logger.error(str(error_message))
        return []
