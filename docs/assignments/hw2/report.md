## 一、函数定义

作业2 的函数调用位于合并后的 React 书城 /assistant 页面，与荐书和政策问答共用一个 Agent。统一工具列表还注册了作业3 使用的查书和政策工具。以下列出本作业要求的两项函数定义：

```json
[
  {
    "type": "function",
    "function": {
      "name": "check_inventory",
      "description": "查询电子书城本店的实时库存与售价。当用户询问某本书还有多少本、是否有货、能不能买到、本店卖多少钱，或需要判断库存是否足够时调用。必须先从用户的话里拿到 ISBN 再调用；如果用户只给了书名，不要猜测 ISBN，先向用户索要。",
      "parameters": {
        "type": "object",
        "properties": {
          "isbn": {
            "type": "string",
            "description": "图书的国际标准书号，10 位或 13 位，可带连字符，例如 978-3-00-000000-4 或 9783000000004。"
          }
        },
        "required": [
          "isbn"
        ],
        "additionalProperties": false
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "get_competitor_price",
      "description": "查询其他平台（竞品）对同一本书的报价，用于和本店价格做对比。仅当用户明确要求比价、询问别家卖多少钱时才调用；如果只是问本店库存，不要调用本函数。",
      "parameters": {
        "type": "object",
        "properties": {
          "isbn": {
            "type": "string",
            "description": "图书的 ISBN，与 check_inventory 使用的是同一个值。"
          }
        },
        "required": [
          "isbn"
        ],
        "additionalProperties": false
      }
    }
  }
]
```

## 二、调用解析

统一 ReAct 循环解析模型返回的 tool_calls 中的 id、function.name 和 function.arguments。参数使用 JSON 解析为对象，再由 UnifiedRegistry 根据函数名派发。JSON 无法解析、参数不是对象、缺少 ISBN 或出现未知函数时，会生成结构化错误供后续轮次处理。

每次动作记录模型给出的 Thought、函数名、参数和实际结果；前端在同一条对话中展示 Action、Action Input 与 Observation。

![原书城页面触发两个函数调用](screenshots/inventory-function-calling.png)


## 三、本地执行

check_inventory 携带当前顾客的 JWT 调用 Spring Boot 的书目接口，按 ISBN 读取现有数据库记录。书籍管理页面、订单扣库存和客服查询使用同一个 books 表。get_competitor_price 按课程要求模拟外部报价，返回平台、价格、到货时间和 source=competitor-price-mock。

真实模型查询算法书时，check_inventory 返回30本，回复依据该实时库存。本地库存由原书城 MySQL 管理；竞品价格由课程模拟工具返回。请求和响应保存在 inventory-live.json。

## 四、结果回填

每个执行结果转为 role=tool 消息，tool_call_id 与原调用 id 对应，content 为 JSON 结果。Agent 把 assistant/tool_calls 与 tool 消息追加到上下文，再次请求模型，循环直至模型给出最终答复。前端显示回复，同时保留每一步的函数名、参数和完整 Observation。

本次库存与比价问答由 remote:deepseek-chat 执行，结束状态为 completed。

![统一客服助手根据实时库存和模拟报价生成答复](screenshots/inventory-reply.png)


## 五、异常纠错

工具统一返回 code、message、retryable 和 hint。错误 ISBN 会得到 INVALID_ISBN_FORMAT，模型据此请用户确认；可重试的模拟接口超时返回 UPSTREAM_TIMEOUT，提示原样重试一次。

实际超时用例中，步骤2的 get_competitor_price 返回UPSTREAM_TIMEOUT；模型读取失败 Observation 后在步骤3再次调用并成功。统一循环还限制最大轮次、连续失败和重复动作。

![客服助手依据失败Observation重试比价](screenshots/timeout-self-correction.png)

