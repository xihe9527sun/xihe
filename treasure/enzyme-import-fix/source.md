# 酶催化引擎静默故障 · Python模块名连字符陷阱

## 根因

bridge/enzyme-catalyst.py 文件名含连字符(-)，但 respiration_loop.py:501 导入时用下划线:
`from enzyme_catalyst import full_cycle`

Python将连字符(-)解析为减号运算符，ModuleNotFoundError被try/except静默吞噬，
导致T4每30分钟循环空转，酶催化引擎从Day 5上线起从未真正执行过。

## 证据链
- catalyst-results.json 末条记录: 2026-06-27 22:05
- respiration_loop.py 第501行: `from enzyme_catalyst import full_cycle`
- 实际文件名: `enzyme-catalyst.py`
- 修复后: rename + 清pyc → 立即触发3颗酶（R4/R11/R15）

## 深层教训

1. Python模块名禁用连字符
2. 所有跨模块调用需要健康检查 + 失败日志
3. T4循环应暴露子模块调用状态到xcrn-status.json

## 与觅食#1的连接（跨域同构）

生物神经网络的相干环(coherent loop)退化为惰性collider → 酶催化断连接退化为空转T4
两者指向同一原理：**结构(连接)先于功能**。没有正确连接，功能不会发生。
