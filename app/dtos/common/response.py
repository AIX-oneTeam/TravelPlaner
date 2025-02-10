from fastapi.responses import JSONResponse
from sqlmodel import SQLModel

class N1JSONResponse(JSONResponse):
    # 생성자
    def __init__(self, data=None, message="Success", status_code=200, error_detail=None, **kwargs):
        content = {
            "status": "성공" if status_code < 400 else "에러 발생",
            "message": message
        }
        # 성공일 때는 data를 포함, 에러일 때는 error_detail 포함
        if status_code < 400:
            if isinstance(data, list):
                # 리스트인 경우 각 항목에 대해 SQLModel 체크 후 변환
                content["data"] = [
                    item.model_dump() if isinstance(item, SQLModel) else item 
                    for item in data
                ]
            else:
                # 단일 항목인 경우 기존 로직 유지
                content["data"] = data.model_dump() if isinstance(data, SQLModel) else data
        else:
            content["error_detail"] = error_detail
        # 부모인 JSONResponse생성 및 초기화
        super().__init__(content=content, status_code=status_code, **kwargs)

class SuccessResponse(N1JSONResponse):
    def __init__(self, data=None, message="API 응답 성공", **kwargs):
        super().__init__(data=data, message=message, status_code=200, **kwargs)

# 추가(JSONResponse에 error_detail 인자가 없어서 오류나 명시함)
class ErrorResponse(N1JSONResponse):
    def __init__(self, message="API 응답간 예외가 발생했습니다.", error_detail=None, status_code=400, **kwargs):
        super().__init__(data=None, message=message, error_detail=str(error_detail), status_code=status_code, **kwargs)