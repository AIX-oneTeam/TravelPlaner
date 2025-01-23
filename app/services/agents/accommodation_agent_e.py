from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain.chains import LLMChain
import os

# OpenAI API 키 설정
os.environ["OPENAI_API_KEY"] = "key"  # OpenAI API 키 입력

# GPT-3.5 모델 초기화
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)

# 첫 번째 프롬프트 템플릿 (날짜, 지역 기준 숙소 추천)
first_llm_prompt = ChatPromptTemplate.from_template(
    """You're a travel agent.
    Please recommend accommodation for the following conditions:
    region: {region},
    date: {date},
    type: {prefer}
    
    Please provide 10 accommodation options including the following details:
    1. The name of the accommodation
    2. The location of the accommodation
    3. Only the valid URL of the accommodation on https://www.google.com/travel/search?q={region} (Ensure the URL is a direct link to https://www.google.com/travel/search?q={region} with the correct location)
    
    
    Please chech again this chechlist
    1. Availability for the provided schedule
    2. including {region} in address
    3. url that include {region}.
    4. Please recommend {prefer} type of accommodations first out of all
    """
)

# 첫 번째 질문을 실행하는 체인 생성
first_chain = LLMChain(llm=llm, prompt=first_llm_prompt)

# 두 번째 프롬프트 템플릿 (첫 번째 프롬프트에서 생성된 값을 이용 + 추가 정보)
second_llm_prompt = ChatPromptTemplate.from_template(
    """
    You're a travel agent. Please recommend accommodation using this list: {first_llm_response}.
    Among the list, please check this additional condition: {second_prompt_value} and pick 5 accommodations.
 
    Please let me know 5 accommodations that meet the following criteria:
    1. Name of the accommodation
    2. Location of the accommodation
    3. Reservations must be available for the provided schedule
    4. The reveiw including swimming pool
    5. Only the valid URL of the accommodation on https://www.google.com/travel/search?q=busan (Ensure the URL is a direct link to https://www.google.com/travel/search?q=busan the correct location)
    
    """
)

# 두 번째 질문에 필요한 정보
second_prompt_value = {
    "number": "2 adults",
    "purpose": "vacation trip, swimming pool",
    
}

# 두 번째 체인 실행
async def run_prompts():
    # 첫 번째 프롬프트 실행 시 템플릿의 데이터를 동적으로 넘김
    first_response = await first_chain.arun(region="Busan, KOREA", date="2025/02/02-2025/02/05", prefer="resort")
    
    # print("First Response:", first_response)

    # 두 번째 체인 실행 (첫 번째 응답과 두 번째 프롬프트 정보를 넘겨 실행)
    second_chain = LLMChain(llm=llm, prompt=second_llm_prompt)
    second_response = await second_chain.arun(first_llm_response=first_response, second_prompt_value=second_prompt_value)

    print("Second Response:", second_response)

# 비동기 실행
import asyncio
asyncio.run(run_prompts())
