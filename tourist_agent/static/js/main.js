// 显示不同的功能区域
function showSection(sectionId) {
    document.querySelectorAll('.section').forEach(section => {
        section.style.display = 'none';
    });
    document.getElementById(sectionId).style.display = 'block';
    
    // 更新导航栏活动状态
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // 如果是历史记录部分，加载历史数据
    if (sectionId === 'history-section') {
        loadHistory();
    }
}

// 处理用户查询
function processQuery() {
    const query = document.getElementById('user-query').value.trim();
    if (!query) {
        alert('请输入您的旅游需求');
        return;
    }
    
    // 显示加载状态
    const resultDiv = document.getElementById('query-result');
    resultDiv.style.display = 'block';
    document.getElementById('intent-result').innerHTML = '<p>正在处理您的请求，请稍候...</p>';
    document.getElementById('itinerary-preview').innerHTML = '';
    
    // 发送请求到后端
    fetch('/api/process_query', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: query })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'error') {
            document.getElementById('intent-result').innerHTML = 
                `<div class="alert alert-danger">${data.message}</div>`;
            return;
        }
        
        // 显示意图识别结果
        let intentHtml = '';
        if (data.intent.need_more_info) {
            intentHtml = `
                <div class="alert alert-warning">
                    <p>${data.intent.response}</p>
                    <p>提取到的信息：城市 ${data.intent.city || '未提供'}, 天数 ${data.intent.days || '未提供'}</p>
                </div>
            `;
        } else {
            intentHtml = `
                <div class="alert alert-success">
                    <p>${data.intent.response}</p>
                    <p>目的地：${data.intent.city}, 行程天数：${data.intent.days}天</p>
                </div>
            `;
        }
        document.getElementById('intent-result').innerHTML = intentHtml;
        
        // 如果信息完整，显示行程预览
        if (!data.intent.need_more_info && data.html) {
            document.getElementById('itinerary-preview').innerHTML = data.html.html_content;
            // 保存当前行程数据到全局变量，供下载使用
            window.currentItinerary = {
                city: data.intent.city,
                days: data.intent.days,
                html: data.html.html_content
            };
        }
    })
    .catch(error => {
        document.getElementById('intent-result').innerHTML = 
            `<div class="alert alert-danger">处理请求时出错: ${error.message}</div>`;
    });
}

// 提交优化请求
function submitOptimization() {
    const city = document.getElementById('optimization-city').value.trim();
    const days = document.getElementById('optimization-days').value.trim();
    const feedback = document.getElementById('optimization-feedback').value.trim();
    
    if (!city || !days || !feedback) {
        alert('请填写所有字段');
        return;
    }
    
    // 显示加载状态
    const resultDiv = document.getElementById('optimization-result');
    resultDiv.style.display = 'block';
    document.getElementById('optimized-itinerary').innerHTML = '<p>正在优化您的行程，请稍候...</p>';
    
    // 发送请求到后端
    fetch('/api/optimize', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            city: city,
            days: days,
            feedback: feedback
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'error') {
            document.getElementById('optimized-itinerary').innerHTML = 
                `<div class="alert alert-danger">${data.message}</div>`;
            return;
        }
        
        // 显示优化结果
        document.getElementById('optimized-itinerary').innerHTML = data.html_content;
        // 保存优化后的行程数据到全局变量
        window.optimizedItinerary = {
            path: data.optimized_path,
            html: data.html_content
        };
    })
    .catch(error => {
        document.getElementById('optimized-itinerary').innerHTML = 
            `<div class="alert alert-danger">处理请求时出错: ${error.message}</div>`;
    });
}

// 下载原始行程
function downloadItinerary() {
    if (!window.currentItinerary) {
        alert('没有可下载的行程');
        return;
    }
    
    const blob = new Blob([window.currentItinerary.html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${window.currentItinerary.city}${window.currentItinerary.days}天旅游攻略.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// 下载优化后的行程
function downloadOptimizedItinerary() {
    if (!window.optimizedItinerary) {
        alert('没有可下载的优化行程');
        return;
    }
    
    const blob = new Blob([window.optimizedItinerary.html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = window.optimizedItinerary.path.split('/').pop();
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// 加载历史记录
function loadHistory() {
    // 这里应该是从后端API获取历史记录
    // 示例代码，实际应该从后端获取数据
    document.getElementById('history-list').innerHTML = `
        <tr>
            <td>北京</td>
            <td>3</td>
            <td>2023-10-15 14:30</td>
            <td><button class="btn btn-sm btn-primary">查看</button></td>
        </tr>
        <tr>
            <td>上海</td>
            <td>5</td>
            <td>2023-10-10 10:15</td>
            <td><button class="btn btn-sm btn-primary">查看</button></td>
        </tr>
    `;
}

// 初始化页面
document.addEventListener('DOMContentLoaded', function() {
    showSection('query-section');
});