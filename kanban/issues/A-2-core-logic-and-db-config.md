# 任务 A-2: 数据库驱动的配置与核心推送逻辑

- **目标**: 实现数据库驱动的配置加载机制，并完成核心的内容推送功能。这是MVP（最小可行产品）的基石。
- **开发者**: AI Architect
- **估算复杂度**: L
- **子任务**:
    1.  **数据库模块**: 在 `database.py` 中实现数据库表的自动创建（`telegram_settings`, `telegram_subscriptions`）。
    2.  **配置加载**: 实现从 `telegram_settings` 表中加载配置的逻辑。
    3.  **任务调度**: 在 `scheduler.py` 和 `tasks.py` 中，实现一个定时任务。
    4.  **核心推送**: 该定时任务需能：
        - 遍历 `telegram_subscriptions` 表中的所有有效订阅。
        - 根据每条订阅的 `last_resource_x_id`，从 `ResourceX` 表查询新内容。
        - 调用 Telegram API 发送内容。
        - 成功后，更新该订阅的 `last_resource_x_id`。
- **验收标准**:
    1.  在数据库 `telegram_subscriptions` 表中手动插入一条订阅规则。
    2.  在 `ResourceX` 表中插入一条匹配该订阅规则的新内容。
    3.  机器人启动后，能在任务周期内自动将该新内容发送到指定群组。
    4.  `telegram_subscriptions` 表中对应的 `last_resource_x_id` 被正确更新。
- **测试用例**:
    - **TC-1**: 单一群组，单一标签，有新内容，检查是否推送。
    - **TC-2**: 单一群组，单一标签，无新内容，检查是否不推送。
    - **TC-3**: 多个群组，不同标签，各自有新内容，检查是否都正确推送并更新各自进度。
    - **TC-4**: 推送失败（如URL无效），检查 `last_resource_x_id` 是否未更新，并记录错误日志。
- **依赖任务**: A-1