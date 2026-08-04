# 以 skill + CLI 作为分发渠道，skill 为薄壳且与代码同仓库

Agent 生态是新的分发渠道。决定：CLI（`vsum`）是功能本体，skill 是薄壳（命令参考 + 示例 + JSON 输出说明，不复制应用逻辑），随包分发。`vsum skill install` 将包内 `skills/video-summary/` 复制到 `~/.claude/skills/`（复制而非符号链接，避免包升级/换 Python 版本后链接悬空）；更新 = 幂等重跑，卸载时一并移除。

- **Status**: accepted
- **Considered Options**: skill 独立仓库（两仓库版本对齐成本高）；symlink 安装（目标路径随 uv tool 重建而变化，易悬空）
- **Consequences**: 包/仓库/skill 同名 `video-summary`，CLI 命令 `vsum`；用户升级包后需重跑 `vsum skill install` 刷新 skill 副本
