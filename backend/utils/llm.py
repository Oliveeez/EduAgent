# utils/llm.py

from langchain_core.language_models.llms import LLM
from typing import List, Optional, Any
import requests
import os
import matplotlib.pyplot as plt
import numpy as np
import json
import re


LLM_API_URL = os.environ.get("LLM_API_URL", "https://api.nuwaapi.com/v1/chat/completions")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "sk-M9klOiXTFzzHqaryVg6B36XPIeKKVwNFU2wt4WkBlyqXYUk2")
LLM_MODEL = os.environ.get("LLM_MODEL", "gemini-3-pro-preview-thinking")

class CustomLLM(LLM):
    """自定义LangChain LLM，适配你的API"""
    
    @property
    def _llm_type(self) -> str:
        return "custom"

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        headers = {
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": LLM_MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        try:
            response = requests.post(
                LLM_API_URL,
                headers=headers,
                json=payload,
                timeout=60,
                proxies={"http": None, "https": None}
            )
            response.raise_for_status()
            result = response.json()
            message = result["choices"][0]["message"]
            last = message.get("content", "")
            return last.replace("\n", "<br>")
        except requests.exceptions.Timeout:
            return "请求大模型超时，请稍后重试。"
        except Exception as e:
            return f"请求大模型失败: {str(e)}"
    
    def __call__(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        return self._call(prompt, stop)


def main():
    """
    测试 CustomLLM 类的功能
    """
    print("=" * 80)
    print("🧪 CustomLLM 测试程序")
    print("=" * 80)
    print()
    
    # 显示当前配置
    print("📋 当前配置:")
    print(f"  - API URL: {LLM_API_URL}")
    print(f"  - 模型: {LLM_MODEL}")
    print(f"  - API Key: {LLM_API_KEY[:10]}...{LLM_API_KEY[-4:] if len(LLM_API_KEY) > 14 else ''}")
    print()
    
    # 初始化 LLM
    print("🔧 初始化 CustomLLM...")
    try:
        llm = CustomLLM()
        print("✅ LLM 初始化成功")
        print()
    except Exception as e:
        print(f"❌ LLM 初始化失败: {e}")
        return
    
    # 测试1：简单问答
    print("-" * 80)
    print("📝 测试1：简单问答")
    print("-" * 80)
    test_prompt_1 = "你好！请用一句话介绍你自己。"
    print(f"提示词: {test_prompt_1}")
    print()
    print("调用中...")
    
    try:
        response_1 = llm(test_prompt_1)
        print(f"✅ 响应成功:")
        # 将<br>替换回换行符以便显示
        print(response_1.replace("<br>", "\n"))
        print()
    except Exception as e:
        print(f"❌ 调用失败: {e}")
        print()
    
    # 测试2：结构化输出（JSON）
    print("-" * 80)
    print("📝 测试2：结构化输出（JSON格式）")
    print("-" * 80)
    test_prompt_2 = """请以JSON格式返回以下内容：
{
  "title": "微积分基础",
  "sections": [
    {
      "name": "导数",
      "topics": ["导数定义", "求导法则"]
    },
    {
      "name": "积分",
      "topics": ["不定积分", "定积分"]
    }
  ]
}

只返回JSON，不要包含其他文字。"""
    
    print(f"提示词: {test_prompt_2[:100]}...")
    print()
    print("调用中...")
    
    try:
        response_2 = llm(test_prompt_2)
        print(f"✅ 响应成功:")
        print(response_2.replace("<br>", "\n"))
        print()
        
        # 尝试解析JSON
        try:
            # 移除可能的markdown代码块标记
            json_text = response_2.replace("<br>", "\n")
            json_text = re.sub(r'```json\s*', '', json_text)
            json_text = re.sub(r'```\s*', '', json_text)
            json_text = json_text.strip()
            
            parsed_json = json.loads(json_text)
            print("✅ JSON 解析成功:")
            print(json.dumps(parsed_json, ensure_ascii=False, indent=2))
            print()
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON 解析失败: {e}")
            print("这可能是因为LLM返回了额外的文字说明")
            print()
    except Exception as e:
        print(f"❌ 调用失败: {e}")
        print()
    
    # 测试3：课程大纲生成（模拟实际使用场景）
    print("-" * 80)
    print("📝 测试3：课程大纲生成（模拟实际场景）")
    print("-" * 80)
    test_prompt_3 = """请为"导数的定义"这个知识点生成一个简短的教学大纲。

要求：
1. 包含2-3个要点
2. 每个要点有简要说明
3. 返回JSON格式

示例格式：
{
  "title": "导数的定义",
  "points": [
    {"title": "要点1", "description": "说明"},
    {"title": "要点2", "description": "说明"}
  ]
}"""
    
    print(f"提示词: {test_prompt_3[:100]}...")
    print()
    print("调用中...")
    
    try:
        response_3 = llm(test_prompt_3)
        print(f"✅ 响应成功:")
        print(response_3.replace("<br>", "\n"))
        print()
    except Exception as e:
        print(f"❌ 调用失败: {e}")
        print()
    
    # 测试4：使用 _call 方法
    print("-" * 80)
    print("📝 测试4：直接使用 _call 方法")
    print("-" * 80)
    test_prompt_4 = "1+1等于几？用一句话回答。"
    print(f"提示词: {test_prompt_4}")
    print()
    print("调用中...")
    
    try:
        response_4 = llm._call(test_prompt_4)
        print(f"✅ 响应成功:")
        print(response_4.replace("<br>", "\n"))
        print()
    except Exception as e:
        print(f"❌ 调用失败: {e}")
        print()
    
    # 测试总结
    print("=" * 80)
    print("✅ 测试完成")
    print("=" * 80)
    print()
    print("💡 使用建议:")
    print("  1. 在代码中导入: from utils.llm import CustomLLM")
    print("  2. 初始化: llm = CustomLLM()")
    print("  3. 调用: response = llm('你的提示词')")
    print("  4. 注意: 响应中的换行符会被替换为 <br> 标签")
    print("  5. 如需显示: 使用 response.replace('<br>', '\\n')")
    print()


if __name__ == "__main__":
    main()