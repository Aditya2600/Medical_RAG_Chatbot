import json
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
try:
    from langchain_community.vectorstores.faiss import DistanceStrategy
except Exception:
    DistanceStrategy = None
import os
from app.components.embeddings import get_embedding_model

from app.common.logger import get_logger
from app.common.custom_exception import CustomException

from app.config.config import DB_FAISS_PATH, PARENT_DOCS_PATH

logger = get_logger(__name__)

def load_vector_store():
    try:
        embedding_model = get_embedding_model()
        
        if os.path.exists(DB_FAISS_PATH):
            logger.info("Loading existing vectorstore...")
            if DistanceStrategy is not None:
                try:
                    return FAISS.load_local(
                        DB_FAISS_PATH,
                        embedding_model,
                        allow_dangerous_deserialization=True,
                        normalize_L2=True,
                        distance_strategy=DistanceStrategy.COSINE,
                    )
                except TypeError:
                    pass

            try:
                return FAISS.load_local(
                    DB_FAISS_PATH,
                    embedding_model,
                    allow_dangerous_deserialization=True,
                    normalize_L2=True,
                )
            except TypeError:
                return FAISS.load_local(
                    DB_FAISS_PATH,
                    embedding_model,
                    allow_dangerous_deserialization=True,
                )
        else:
            logger.warning("No vector store found..")
    
    except Exception as e:
        error_message = CustomException("Failed to load vectorstore", e)
        logger.error(str(error_message))
        
def save_vector_store(text_chunks):
    try:
        if not text_chunks:
            raise CustomException("No chunks were found..")
        
        logger.info("Generating your new vectorstore")
        
        embedding_model = get_embedding_model()
        
        if DistanceStrategy is not None:
            try:
                db = FAISS.from_documents(
                    text_chunks,
                    embedding_model,
                    normalize_L2=True,
                    distance_strategy=DistanceStrategy.COSINE,
                )
            except TypeError:
                db = FAISS.from_documents(text_chunks, embedding_model)
        else:
            try:
                db = FAISS.from_documents(
                    text_chunks,
                    embedding_model,
                    normalize_L2=True,
                )
            except TypeError:
                db = FAISS.from_documents(text_chunks, embedding_model)
        
        logger.info("Saving vectorstore")
        
        db.save_local(DB_FAISS_PATH)
        
        logger.info("Vectorstore saved sucessfully...")
        
        return db
    
    except Exception as e:
        error_message = CustomException("Failed to create new vectorstore", e)
        logger.error(str(error_message))


def save_parent_docs(parent_docs):
    try:
        if not parent_docs:
            raise CustomException("No parent chunks were found..")

        os.makedirs(DB_FAISS_PATH, exist_ok=True)
        payload = [
            {
                "page_content": doc.page_content,
                "metadata": doc.metadata or {},
            }
            for doc in parent_docs
        ]

        with open(PARENT_DOCS_PATH, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True)

        logger.info("Parent chunks saved successfully.")
        return True

    except Exception as e:
        error_message = CustomException("Failed to save parent chunks", e)
        logger.error(str(error_message))
        return False


def load_parent_docs():
    if not os.path.exists(PARENT_DOCS_PATH):
        logger.warning("No parent doc store found..")
        return {}

    try:
        with open(PARENT_DOCS_PATH, "r", encoding="utf-8") as handle:
            payload = json.load(handle)

        parent_docs = {}
        for item in payload:
            content = item.get("page_content", "")
            metadata = item.get("metadata") or {}
            doc = Document(page_content=content, metadata=metadata)
            parent_id = metadata.get("parent_id")
            if parent_id:
                parent_docs[parent_id] = doc

        logger.info("Loaded %s parent chunks", len(parent_docs))
        return parent_docs
    except Exception as e:
        error_message = CustomException("Failed to load parent chunks", e)
        logger.error(str(error_message))
        return {}
