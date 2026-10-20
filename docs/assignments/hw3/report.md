## 一、政策向量化

书城的退换货与会员政策存放在 python-assistant/data/policy.txt，包含5章25条课程模拟政策。加载时清除排版分隔线，保留版本、章节和条款信息；按条款分块，超长内容按句子拆分，窗口420字符、重叠60字符，每块保留标题和编号。

本次清洗后共3480字符，产生26个分块。使用 sentence-transformers:BAAI/bge-small-zh-v1.5 在本地生成512维稠密向量并做L2归一化。文档和查询使用同一编码器，分块及全部向量保存在 policy-vectors.json。

## 二、政策检索

RAG 参照课程 Simple RAG 示例：逐块计算 Embedding，保存为内存向量列表，对查询向量逐项计算余弦相似度，再取 Top-K。query_store_policy 默认返回前三条、过滤低于0.55的结果，结果含条款正文、章节、块编号和分数。模型据这些观测回答政策问题，并引用条款。

索引缓存指纹包含政策文本、分块参数和编码器名称。语料或参数变化后重建索引；没有达到阈值的条款时返回 POLICY_NOT_COVERED，避免将弱相关内容直接作为依据。

## 三、ReAct循环

导购位于原书城 /guide 页面，与库存客服共用同一 Python 服务。每轮将用户问题和此前记录传给模型，解析 Thought、Action 与 Action Input，实际执行工具后写入 Observation，再进行下一轮。模型输出 Final Answer 时结束；同时限制步数、连续错误次数和重复动作。

模型生成在 Observation 标记处停止；观测由程序执行工具后提供。完整步骤同源返回给前端并写入日志。

## 四、工具路由

search_book_catalog 通过当前顾客的 JWT 读取现有书城目录，按标题、分类、作者和简介匹配需求，价格和现货条件可以传入过滤。query_store_policy 调用共享政策向量库。用户同时问荐书和退货时，模型先选择查书工具，取得结果后再检索政策。

![导购读取原书城中的微服务书目](screenshots/react-bookstore.png)


## 五、执行链路

实际用户提问为“我想买一本关于微服务的书，另外如果我买了不喜欢，拆了塑封还能退吗？”。本次使用 remote:deepseek-chat，共3轮，结束状态为completed。以下摘录实际 Thought 和参数，并将观测内容按书名或条款号作摘要；原始完整结果见 react-case.json 和运行日志。

```text
Thought: 用户问了两个问题：一是想买微服务相关的书，二是询问拆了塑封能否退货。我需要先查书目，再查政策。按顺序先查书。
Action: search_book_catalog
Action Input: {"query": "微服务"}
Observation 摘要: {"source": "bookstore-api", "count": 2, "titles": ["微服务架构设计模式", "微服务设计"]}

Thought: 用户问了两个问题：一是想买微服务相关的书，二是询问拆了塑封能否退货。我已经查到了微服务相关的书目，现在需要查政策来回答退货问题。
Action: query_store_policy
Action Input: {"question": "拆了塑封还能退吗"}
Observation 摘要: {"source": "policy-rag", "count": 3, "clauses": ["第六条【塑封与拆封规则】", "第八条【不支持退换的商品】", "第二十条【已拆封退货权益】"]}
```

![模型继续检索政策并取得第六条等条款](screenshots/react-policy.png)


最终答复同时推荐数据库中的微服务图书，并依据第六条说明一般拆封退货规则，补充质量问题和会员权益例外。

![原书城页面显示实际导购答复](screenshots/react-reply.png)

