import os
import json
import fitz  # PyMuPDF
from PIL import Image
import base64
import requests
from flask import Flask, request, jsonify
from datetime import datetime
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType

app = Flask(__name__)

#os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
# 配置
PDF_UPLOAD_FOLDER = "storage/pdfs"
OPTIMIZED_HTML_FOLDER = "storage/optimized_html"
os.makedirs(PDF_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OPTIMIZED_HTML_FOLDER, exist_ok=True)

# 多模态模型配置 (使用GPT-4o示例)
MULTIMODAL_MODEL = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type="gpt-4o",
    api_key='YOUR_API_KEY',
    #api_base="https://api.openai.com/v1"  # 显式指定API地址
)

class PDFFeedbackProcessor:
    def __init__(self):
        self.feedback_agent = ChatAgent(
            system_message="""
            你是一个旅游攻略优化专家，能够分析PDF文档中的用户标记和反馈。
            你的任务：
            1. 分析用户标记的PDF页面内容
            2. 理解用户的修改意图
            3. 生成具体的优化指令
            
            输入包含：
            - 用户标记的页面图像
            - 用户文字反馈(可选)
            
            输出JSON格式：
            {
                "feedback_type": "景点调整/时间安排/美食推荐/其他",
                "specific_issues": ["具体问题1", "问题2"],
                "optimization_instructions": {
                    "action": "add/remove/modify",
                    "target": "具体景点或项目",
                    "details": "修改细节"
                },
                "confidence": 0-1
            }
            """,
            model=MULTIMODAL_MODEL,
            output_language="Chinese"
        )
    
    def extract_marked_pages(self, pdf_path):
        """提取PDF中被标记的页面为图像"""
        doc = fitz.open(pdf_path)
        marked_pages = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            if self._page_has_annotations(page):
                pix = page.get_pixmap()
                img_path = f"{PDF_UPLOAD_FOLDER}/page_{page_num}.png"
                pix.save(img_path)
                marked_pages.append(img_path)
        
        return marked_pages
    
    def _page_has_annotations(self, page):
        """检查页面是否有用户标记"""
        return len(page.annots()) > 0 or len(page.widgets()) > 0
    
    def process_feedback(self, pdf_path, text_feedback=""):
        """处理PDF反馈并生成优化指令"""
        # 1. 提取标记页面
        marked_pages = self.extract_marked_pages(pdf_path)
        if not marked_pages:
            raise ValueError("PDF中没有找到用户标记")
        
        # 2. 准备多模态输入
        messages = []
        for page_img in marked_pages:
            with open(page_img, "rb") as img_file:
                base64_image = base64.b64encode(img_file.read()).decode('utf-8')
                messages.append({
                    "type": "image_url",
                    "image_url": f"data:image/png;base64,{base64_image}"
                })
        
        if text_feedback:
            messages.append({
                "type": "text",
                "text": f"用户文字反馈: {text_feedback}"
            })
        
        # 3. 调用多模态模型分析
        response = self.feedback_agent.step(messages)
        return json.loads(response.msgs[0].content)

class TravelItineraryOptimizer:
    def __init__(self):
        self.service_endpoints = {
            "info_retrieval": "http://localhost:5002/get_travel_plan",
            "html_generation": "http://localhost:5003/generate_itinerary_html"
        }
    
    def optimize_based_on_feedback(self, original_data, feedback_analysis):
        """基于反馈分析重新生成行程"""
        # 1. 准备优化参数
        optimization_params = {
            "city": original_data["city"],
            "days": original_data["days"],
            "optimization": feedback_analysis
        }
        
        # 2. 调用信息检索服务
        retrieval_response = requests.post(
            self.service_endpoints["info_retrieval"],
            json=optimization_params,
            timeout=30
        ).json()
        
        if retrieval_response.get("status") != "success":
            raise ValueError("信息检索失败")
        
        # 3. 生成新版HTML
        html_response = requests.post(
            self.service_endpoints["html_generation"],
            json={
                "city": original_data["city"],
                "days": original_data["days"],
                "travel_data": retrieval_response["data"]
            },
            timeout=30
        ).json()
        
        return html_response
    
    def save_optimized_version(self, html_content, city, days):
        """保存优化后的HTML版本"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{city}{days}天_优化版_{timestamp}.html"
        filepath = os.path.join(OPTIMIZED_HTML_FOLDER, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        return filepath

# 初始化处理器
pdf_processor = PDFFeedbackProcessor()
itinerary_optimizer = TravelItineraryOptimizer()

@app.route('/optimize_itinerary', methods=['POST'])
def handle_optimization():
    try:
        # 1. 直接接收JSON数据（不再处理文件上传）
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求必须为JSON格式"}), 400

        required_fields = ["city", "days", "original_html_path", "feedback"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"缺少必要字段: {field}"}), 400

        # 2. 模拟PDF标记分析（原多模态处理改为直接解析JSON反馈）
        feedback_analysis = {
            "feedback_type": "用户直接反馈",
            "specific_issues": [data["feedback"]],
            "optimization_instructions": {
                "action": "modify",
                "target": "根据反馈调整",
                "details": data["feedback"]
            },
            "confidence": 0.9
        }

        # 3. 执行优化流程
        new_html = itinerary_optimizer.optimize_based_on_feedback(
            {"city": data["city"], "days": data["days"]},
            feedback_analysis
        )

        # 4. 保存优化结果
        saved_path = itinerary_optimizer.save_optimized_version(
            new_html["html_content"],
            data["city"],
            data["days"]
        )

        return jsonify({
            "status": "success",
            "optimized_path": saved_path,
            "feedback_analysis": feedback_analysis
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_optimized_html/<filename>')
def get_optimized_html(filename):
    return send_from_directory(OPTIMIZED_HTML_FOLDER, filename)

if __name__ == '__main__':
    from gevent import pywsgi
    server = pywsgi.WSGIServer(('0.0.0.0', 5005), app)
    print("Feedback Optimization Service running on port 5005")
    server.serve_forever()