"""启动入口：python run.py [--port 8001]"""
import argparse

import uvicorn

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="启动多店铺进销存管理工具")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    print("=" * 56)
    print("多店铺进销存管理工具已启动")
    print(f"  使用界面: http://{args.host}:{args.port}/static/index.html")
    print(f"  接口文档: http://{args.host}:{args.port}/docs")
    print("=" * 56)
    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=False)
