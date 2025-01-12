from dotenv import load_dotenv
import os
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_huggingface import HuggingFaceEndpoint
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA

load_dotenv()

# 데이터 로드
with open('lodging_data.txt', 'r', encoding='UTF-8') as f:
    lodging_data = [line.strip() for line in f.readlines()]

# 임베딩 모델 로드
embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
lodging_store = FAISS.from_texts(lodging_data, embeddings)

# 저장된 벡터 데이터 확인
query = "서울 조용한 숙소"
results = lodging_store.similarity_search(query, k=2)
print("검색 결과", [result.page_content for result in results])

huggingface_api_Key = os.getenv('API_KEY')

# LLM 모델 로드
llm = HuggingFaceEndpoint(
    repo_id="tiiuae/falcon-7b-instruct",
    huggingfacehub_api_token=huggingface_api_Key,
    model_kwargs={"temperature": 0.7, "max_length": 256},
)

# 프롬프트 템플릿 정의
template = """
당신은 여행과 숙소에 대한 전문가 에이전트입니다. 사용자가 입력한 장소에 가장 적합한 숙소를 추천해주세요.
질문: {query}
답변:
"""

prompt = PromptTemplate(template=template, input_variables=["query"])

# RAG 체인 생성
rag_chain = RetrievalQA.from_chain_type(
    chain_type="llm",
    llm=llm,
    vector_store=lodging_store,
    prompt_template=prompt,
)

# 테스트 질의
query = "서울 조용한 숙소 추천"
response = rag_chain.run(query)
print("테스트 결과", response)
# app = FastAPI()

# @app.get("/", response_class=HTMLResponse)
# async def read_root():
#     return "index.html"


# @app.post("/", response_class=HTMLResponse)
# async def root(query: str = Form(...)):
#     response = rag_chain.run(query)
#     return HTMLResponse(content=response, status_code=200)


