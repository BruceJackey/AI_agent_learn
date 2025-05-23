# Tourist_Helper_Agent
目的核心目标是实现一个智能化的旅游出行规划助手：用户只需输入目的地和天数，系统即可自动生成详细的旅游行程，包括每日活动安排、餐饮推荐、景点信息等。系统还支持根据用户反馈动态调整行程，支持在线阅览和编辑，同时提供多种格式（Markdown，HTML 或 PDF）的导出，方便用户保存或分享。这不仅提升了行程规划的效率，也能为用户带来更为便捷和专业的旅游体验。

![整体架构](https://github.com/BruceJackey/AI_agent_learn/blob/main/tourist_agent/1.png)
## 用户意图识别模块
该模块主要用于收集用户想要去哪，去几天的需求。我们可以通过一个合适的system prompt来实现。
##旅游信息检索模块
在该模块中，用户和信息收集Agent进行多轮往复的对话，直到Agent认为能够通过用户的表达和上下文提取出用户的目标出行城市和出行天数等关键信息，并将信息传递到下一个模块。
![用户意图识别模块](https://github.com/BruceJackey/AI_agent_learn/blob/main/tourist_agent/2.png)
## 攻略生成模块

### 验证数据是否存在：

如果数据库中存在对应的城市和天数的旅游数据，（即缓存命中），则直接加载复用数据。

如果数据库中没有查询到对应的信息，则调用Tool Calling中的搜索工具（Google Search 或 DuckDuckGo）进行实时的信息检索（检索的内容包括著名景点，当地美食，天气情况等数据，可以根据需要自由添加）
![攻略生成模块](https://github.com/BruceJackey/AI_agent_learn/blob/main/tourist_agent/3.png)
### 攻略初稿生成：

接下来，攻略生成Agent会结合上述检索到的基础数据，按预先定义的默认格式生成 HTML 格式的详细行程攻略，包含每日的活动安排和推荐内容。
### 格式转换：

将生成的 HTML 导出为 PDF 格式，并在前端提供在线预览，方便用户进行下载/转发/保存/修改。
## 反馈优化模块
### 收集用户反馈：

用户可以在前端预览中对生成的攻略初稿中的任意部分和内容进行评价，支持手动标记圈画需要优化的部分，这意味着我们接受反馈的形式是多模态的（图像理解+文字评述）。
使用反馈优化Agent进行意图理解并迭代式地调整攻略：

### 反馈优化Agent分析用户反馈并理解具体修改需求；

基于用户反馈，结合多模态能力和工具调用生成新内容并迭代式优化。

### 输出最终攻略版本：

根据用户确认的最终行程生成 PDF 文档。

将优化后的行程存入数据库以供未来复用。
## 简易的UI界面
![UI界面](https://github.com/BruceJackey/AI_agent_learn/blob/main/tourist_agent/4.png)
