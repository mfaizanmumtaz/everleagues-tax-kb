from langchain_community.document_loaders import PyMuPDFLoader
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
file_path = r"C:\Users\Xeven\Documents\XevenSolutionTasks\everleagues-tax-kb\tests\load_testing\i1040gi.pdf"
loader = PyMuPDFLoader(file_path)

docs = loader.load()
print(docs[59].page_content)


from langchain_community.document_loaders.parsers import LLMImageBlobParser
from langchain_openai import ChatOpenAI

loader = PyMuPDFLoader(
    file_path,
    mode="page",
        extract_tables="markdown",
    images_inner_format="markdown-img",
    images_parser=LLMImageBlobParser(model=ChatOpenAI(model="gpt-4o-mini", max_tokens=1024)),
)
docs = loader.load()
print(docs[59])