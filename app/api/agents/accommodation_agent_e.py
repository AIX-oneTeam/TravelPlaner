from langchain.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain

import os

import os
os.environ["OPENAI_API_KEY"] = "open-ai key"
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)

# 고정 프롬프트 템플릿
prompt = PromptTemplate.from_template(
    """아래 조건에 맞는 숙소를 추천해주세요. 

    지역: {region},
    일정: {date},
    주요 연령대: {age},
    인원 수: {accompanyNumber},
    특이 사항: {specailPoint},
    컨셉: {concept}
    """
)

# 전달 데이터 
prompt_value = prompt.format(
    region="대전",
    date="2025/02/02-2025/02/05",
    age="30대",
    accompanyNumber="성인 3명",
    specailPoint="없음",
    concept="우정여행"
)

# 전달할 프롬프트 출력
print(prompt_value)  

#LLM에 프롬프트 전달
# 프롬프트 템플릿 정의
prompt = ChatPromptTemplate.from_template(
    "너는 여행사 직원이야. {question}에 대해 숙소를 추천해줘. 단, 숙소명, 숙소위치 포함해서 표로 만들어줘, 최근 3개월 이내 후기가 있는 곳으로 최소 10개 추천해줘"
)

chain = LLMChain(llm=llm, prompt=prompt)

question = prompt_value
response = chain.run(question=question)

print(response)