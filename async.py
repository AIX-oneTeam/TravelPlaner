import asyncio

def normal_function():
    return "나는 일반 함수!"

async def coroutine_function():
    return "나는 코루틴!"

print(normal_function())   # 나는 일반 함수!
# print(coroutine_function())  # <coroutine object coroutine_function at 0x0000016FAE0FF1C0>
result = asyncio.run(coroutine_function())
print(result)
print(result)