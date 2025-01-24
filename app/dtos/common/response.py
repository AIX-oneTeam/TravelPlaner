from fastapi.responses import JSONResponse
from sqlmodel import SQLModel

class N1JSONResponse(JSONResponse):
    # 생성자
    def __init__(self, data=None, message="Success", status_code=200, **kwargs):
        content = {
            "status": "성공" if status_code < 400 else "에러 발생",
            "message": message,
            # DTO를 추가하는 경우 SQLModel인지 확인 후 model_dump() 호출
            "data": data.model_dump() if isinstance(data, SQLModel) else data,
        }
        # 부모인 JSONResponse생성 및 초기화
        super().__init__(content=content, status_code=status_code, **kwargs)

class SuccessResponse(N1JSONResponse):
    def __init__(self, data=None, message="API 응답 성공", **kwargs):
        super().__init__(data=data, message=message, status_code=200, **kwargs)

class ErrorResponse(N1JSONResponse):
    def __init__(self, message="API 응답간 예외가 발생했습니다.", status_code=400, **kwargs):
        super().__init__(data=None, message=message, status_code=status_code, **kwargs)