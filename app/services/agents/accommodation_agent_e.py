from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain.chains import LLMChain
import os

os.environ["OPENAI_API_KEY"] = "my-key"  
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

# 첫 번째 프롬프트 템플릿 (날짜, 지역 기준 숙소 추천)
first_llm_prompt = ChatPromptTemplate.from_template(
    """
    You're a travel agent.
    Please recommend accommodation for the following conditions:
   {first_prompt_value}
        
    Please provide 10 accommodation options including the following details:
    1. The name of the accommodation
    2. The address of the accommodation
    
    Please check again this chechlist
    1. Available for the provided schedule
    2. including {region_value} in address
    3. url that include {region_value}.
    """
)

first_prompt_value = {
    "region": "Daegu, KOREA",
    "date": "2025/02/02-2025/02/05",
}
region_value = first_prompt_value["region"]


# 두 번째 프롬프트 템플릿 (첫 번째 프롬프트에서 생성된 값을 이용 + 추가 정보)
second_llm_prompt = ChatPromptTemplate.from_template(
    """
    You're a travel agent. Please pick accommodation using this list: {first_llm_response}.
    Among the list, please check this additional condition: {second_prompt_value} and pick 5 accommodations.
 
    Please pick 5 accommodation options including the following details:
    1. The name of the accommodation
    2. The address of the accommodation
    
    checklist : 
    1. Only the valid URL of the accommodation on https://www.google.com/travel/search?q={region_value}  (Ensure the URL is a direct link to https://www.google.com/travel/search?q=busan the correct location) 
    2. Is it open now
    """
)

# 두 번째 질문에 필요한 정보
second_prompt_value = {
    "number": "2 adults",
    "purpose": "vacation trip"
}

# 답변 생성
async def run_prompts():
    # 첫 번째 체인 실행
    first_chain = LLMChain(llm=llm, prompt=first_llm_prompt)
    first_response = await first_chain.arun(first_prompt_value=first_prompt_value, region_value=region_value)
    
    # 두 번째 체인 실행 
    second_chain = LLMChain(llm=llm, prompt=second_llm_prompt)
    second_response = await second_chain.arun(first_llm_response=first_response, second_prompt_value=second_prompt_value,region_value=region_value )

    print("Second Response:", second_response)

# 비동기 실행
import asyncio
asyncio.run(run_prompts())
