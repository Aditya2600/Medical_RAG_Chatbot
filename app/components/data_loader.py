from app.components.pdf_loader import load_pdf_files, create_parent_child_chunks
from app.components.vector_store import save_parent_docs, save_vector_store
from app.common.logger import get_logger
from app.common.custom_exception import CustomException

logger = get_logger(__name__)


def process_and_store_pdfs() -> None:
    """Load PDFs, chunk them into parent/child docs, and persist the vectorstore + parent docs."""
    try:
        logger.info("Building vectorstore from PDFs...")

        documents = load_pdf_files()
        if not documents:
            raise CustomException("No PDF documents found to index", None)

        parent_docs, child_docs = create_parent_child_chunks(documents)

        save_vector_store(child_docs)
        save_parent_docs(parent_docs)

        logger.info("Vectorstore created successfully")

    except Exception as e:
        err = e if isinstance(e, CustomException) else CustomException("Failed to create vectorstore", e)
        logger.error(str(err))
        raise err


if __name__ == "__main__":
    process_and_store_pdfs()