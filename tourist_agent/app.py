from flask import Flask, render_template, request, jsonify, send_from_directory
import requests
import os

app = Flask(__name__)

# 服务端点配置
SERVICE_ENDPOINTS = {
    "intent_recognition": "http://localhost:5001/extract_travel_info",
    "info_retrieval": "http://localhost:5002/get_travel_plan",
    "html_generation": "http://localhost:5003/generate_itinerary_html",
    "optimization": "http://localhost:5005/optimize_itinerary"
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/process_query', methods=['POST'])
def process_query():
    try:
        # 1. 调用意图识别服务
        intent_response = requests.post(
            SERVICE_ENDPOINTS["intent_recognition"],
            json={"query": request.json['query']},
            timeout=10
        ).json()
        
        if intent_response.get('error'):
            return jsonify(intent_response), 400
            
        # 2. 如果信息不全，直接返回
        if intent_response['need_more_info']:
            return jsonify(intent_response)
            
        # 3. 调用信息检索服务
        retrieval_response = requests.post(
            SERVICE_ENDPOINTS["info_retrieval"],
            json={"city": intent_response['city'], "days": intent_response['days']},
            timeout=30
        ).json()
        
        if retrieval_response.get('status') != 'success':
            return jsonify(retrieval_response), 400
            
        # 4. 调用HTML生成服务
        html_response = requests.post(
            SERVICE_ENDPOINTS["html_generation"],
            json={"city": intent_response['city'], "days": intent_response['days']},
            timeout=30
        ).json()
        
        return jsonify({
            "status": "success",
            "intent": intent_response,
            "retrieval": retrieval_response,
            "html": html_response
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/optimize', methods=['POST'])
def optimize():
    try:
        data = request.json
        response = requests.post(
            SERVICE_ENDPOINTS["optimization"],
            json=data,
            timeout=30
        ).json()
        return jsonify(response)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)