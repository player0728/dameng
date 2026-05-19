from fastapi import FastAPI
import uvicorn
from pydantic import BaseModel  # 1. 导入 BaseModel
app = FastAPI()
 
# 2. 定义一个类，继承 BaseModel
# 这就像是制定一个“表格”，前端传来的数据必须符合这个表格
class UserInfo(BaseModel):
    username: str
    password: str
    age: int = 18  # 默认18，如果没传就是18
    is_student: bool = True  # 是否是学生
 
# 3. 在接口中使用这个模型
@app.post("/register")
def register(user: UserInfo):  # 核心：参数类型指定为 UserInfo
    # FastAPI 会自动把前端传来的 JSON 塞进 user 变量里
    # 我们可以直接用 user.username 取值
    if user.age < 18:
        return {"message": "未成年人禁止注册", "code": 400}
 
    return {
        "message": "注册成功",
        "用户": user.username,
        "身份": "学生" if user.is_student else "社会人"
    }
 
if __name__=="__main__":
    uvicorn.run(app="main:app",host="127.0.0.1",port=8088)
 
 