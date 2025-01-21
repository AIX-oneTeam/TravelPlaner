import openai
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

# 환경 변수에서 API 키 가져오기
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_travel_recommendations(prompt: str, max_results: int = 4) -> list:
    """
    사용자 프롬프트에 따라 관광지를 추천하는 함수
    Args:
        prompt (str): 사용자 입력 프롬프트
        max_results (int): 추천받을 관광지 개수
    Returns:
        list: 추천 관광지 리스트
    """
    try:
        # ChatCompletion API 호출
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # 사용할 모델 (gpt-4로 변경 가능)
            messages=[
                {"role": "system", "content": "You are a travel assistant. Suggest travel destinations based on user input."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,  # 응답의 창의성을 조정
            max_tokens=200    # 응답 최대 토큰 수
        )
        # 응답에서 추천 텍스트 추출
        recommendations = response["choices"][0]["message"]["content"].strip()
        # 결과를 리스트로 변환하여 반환
        return recommendations.split("\n")[:max_results]
    except Exception as e:
        print(f"Error: {e}")
        return ["추천 실패: 다시 시도해주세요."]
