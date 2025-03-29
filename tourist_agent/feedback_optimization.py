import os
import json
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from typing import Dict, List, Optional
from camel.configs import QwenConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType
from camel.agents import ChatAgent
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# 微服务端点配置 (对应您之前的三个模块)
INTENT_RECOGNITION_URL = "http://localhost:5001/extract_travel_info"
INFO_RETRIEVAL_URL = "http://localhost:5002/get_travel_plan"
HTML_GENERATION_URL = "http://localhost:5003/generate_itinerary_html"

# 数据库路径
FEEDBACK_DB = "storage/feedback_db.json"
OPTIMIZATION_DB = "storage/optimization_db.json"
os.makedirs("storage", exist_ok=True)

class FeedbackOptimizer:
    def __init__(self):
        # 初始化分析Agent
        self.analysis_agent = ChatAgent(
            system_message="""
            你是一个旅游反馈分析专家。请分析用户反馈并生成优化指令：
            1. 识别反馈针对的行程部分（景点/美食/路线/时间安排）
            2. 提取具体修改要求（替换/增加/删除/调整）
            3. 生成优化参数用于重新规划
            
            输出JSON格式：
            {
                "target_aspect": "attractions/food/itinerary",
                "action": "replace/add/remove/adjust",
                "modification_details": {
                    "city": "原城市",
                    "days": "原天数",
                    "changes": {
                        "要移除的景点": [],
                        "要增加的景点类型": [],
                        "要调整的天数分布": {}
                    }
                }
            }
            """,
            model=ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
                model_type="Qwen/Qwen2.5-72B-Instruct",
                api_key=os.getenv("QWEN_API_KEY"),
                url="https://api-inference.modelscope.cn/v1",
                model_config_dict=QwenConfig(temperature=0.2).as_dict(),
            ),
            output_language="Chinese"
        )
        
        # 初始化数据库文件
        for db_file in [FEEDBACK_DB, OPTIMIZATION_DB]:
            if not os.path.exists(db_file):
                with open(db_file, "w", encoding="utf-8") as f:
                    json.dump({"records": []}, f)

    def safe_json_parse(self, json_str: str) -> Dict:
        """安全的JSON解析方法"""
        try:
            # 尝试移除可能的Markdown代码块标记
            json_str = json_str.replace("```json", "").replace("```", "").strip()
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"无效的JSON格式: {str(e)}")

    def analyze_feedback(self, feedback: str, itinerary_data: Dict) -> Dict:
        """分析反馈并生成优化指令"""
        prompt = f"""
        原始行程信息：
        {json.dumps(itinerary_data, indent=2, ensure_ascii=False)}
        
        用户反馈：
        {feedback}
        """
        response = self.analysis_agent.step(prompt)
        try:
            return self.safe_json_parse(response.msgs[0].content)
        except ValueError as e:
            app.logger.error(f"分析反馈时JSON解析失败: {e}\n原始内容: {response.msgs[0].content}")
            raise

    def make_service_request(self, url: str, payload: Dict) -> Dict:
        """安全的微服务请求方法"""
        try:
            response = requests.post(
                url,
                json=payload,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()  # 检查HTTP错误
            return response.json()
        except requests.exceptions.RequestException as e:
            app.logger.error(f"请求微服务失败: {url} - {str(e)}")
            raise ValueError(f"微服务请求失败: {str(e)}")
        except json.JSONDecodeError as e:
            app.logger.error(f"微服务响应JSON解析失败: {response.text}")
            raise ValueError("无效的微服务响应格式")

    def reprocess_itinerary(self, optimization_instruction: Dict) -> Dict:
        """重新触发完整流程生成新行程"""
        # 1. 准备优化后的请求数据
        base_data = optimization_instruction["modification_details"]
        
        # 2. 调用信息检索模块 (替换/增加/删除景点)
        retrieval_response = self.make_service_request(
            INFO_RETRIEVAL_URL,
            {
                "city": base_data["city"],
                "days": base_data["days"],
                "optimization": optimization_instruction
            }
        )
        
        if not retrieval_response.get("status") == "success":
            raise ValueError(f"信息检索失败: {retrieval_response.get('message', '未知错误')}")
        
        # 3. 调用HTML生成模块
        html_response = self.make_service_request(
            HTML_GENERATION_URL,
            {
                "city": base_data["city"],
                "days": base_data["days"],
                "travel_data": retrieval_response["data"]
            }
        )
        
        if not html_response.get("html_content"):
            raise ValueError("HTML生成失败: 缺少html_content字段")
        
        return {
            "new_itinerary": html_response,
            "optimization_applied": optimization_instruction
        }

    def save_optimization_result(self, result: Dict) -> str:
        """保存优化结果并返回文件路径"""
        filename = f"{result['city']}{result['days']}天_优化版_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = os.path.join("storage", filename)
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(result["new_itinerary"]["html_content"])
            
            # 记录到优化数据库
            with open(OPTIMIZATION_DB, "r+", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {"records": []}
                
                data["records"].append({
                    "timestamp": datetime.now().isoformat(),
                    "original_itinerary": result.get("original_itinerary_id"),
                    "optimized_file": filename,
                    "changes_applied": result["optimization_applied"],
                    "feedback": result.get("feedback", "")
                })
                
                f.seek(0)
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.truncate()
            
            return filepath
        except IOError as e:
            app.logger.error(f"文件操作失败: {str(e)}")
            raise ValueError("无法保存优化结果")

# 初始化优化器
optimizer = FeedbackOptimizer()

@app.route('/optimize_itinerary', methods=['POST'])
def optimize_itinerary():
    """
    优化行程端点
    请求格式：
    {
        "original_itinerary_id": "原行程ID",
        "original_html_path": "原HTML文件路径",
        "feedback": "用户反馈文本",
        "user_preferences": {} // 可选额外偏好
    }
    """
    try:
        data = request.get_json()
        if not data or "original_html_path" not in data or "feedback" not in data:
            return jsonify({
                "status": "error",
                "message": "缺少必要参数: original_html_path 和 feedback"
            }), 400
        
        # 1. 加载原始行程数据
        try:
            with open(data["original_html_path"], "r", encoding="utf-8") as f:
                html_content = f.read()
        except IOError as e:
            return jsonify({
                "status": "error",
                "message": f"无法读取原始HTML文件: {str(e)}"
            }), 400
        
        # 2. 分析反馈生成优化指令
        try:
            optimization_instruction = optimizer.analyze_feedback(
                feedback=data["feedback"],
                itinerary_data={
                    "html_content": html_content,
                    "user_preferences": data.get("user_preferences", {})
                }
            )
        except ValueError as e:
            return jsonify({
                "status": "error",
                "message": f"反馈分析失败: {str(e)}"
            }), 400
        
        # 3. 重新触发完整流程
        try:
            optimization_result = optimizer.reprocess_itinerary(optimization_instruction)
            optimization_result.update({
                "original_itinerary_id": data["original_itinerary_id"],
                "city": optimization_instruction["modification_details"]["city"],
                "days": optimization_instruction["modification_details"]["days"],
                "feedback": data["feedback"]
            })
        except ValueError as e:
            return jsonify({
                "status": "error",
                "message": f"行程重新生成失败: {str(e)}"
            }), 500
        
        # 4. 保存优化结果
        try:
            saved_path = optimizer.save_optimization_result(optimization_result)
            return jsonify({
                "status": "success",
                "optimized_file_path": saved_path,
                "changes_applied": optimization_instruction,
                "new_html_url": f"/storage/{os.path.basename(saved_path)}"
            }), 200
        except ValueError as e:
            return jsonify({
                "status": "error",
                "message": f"保存优化结果失败: {str(e)}"
            }), 500

    except Exception as e:
        app.logger.error(f"优化行程时发生未预期错误: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"服务器内部错误: {str(e)}"
        }), 500

# 添加静态文件访问路由
@app.route('/storage/<filename>')
def serve_storage(filename):
    return send_from_directory('storage', filename)

if __name__ == '__main__':
    from gevent import pywsgi
    # 启用更详细的日志记录
    import logging
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)
    
    server = pywsgi.WSGIServer(('0.0.0.0', 5004), app)
    app.logger.info("Feedback optimization service ready on port 5004")
    server.serve_forever()