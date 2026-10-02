# crawler 数据层

目标子站：
- 教务处通知：https://jx.zcst.edu.cn （选课/考试/重修）
- 后勤管理处：https://hq.zcst.edu.cn （报修/班车/食堂）
- 学校官网通知：https://www.zcst.edu.cn

约定：
- 抓取间隔 ≥5 秒，只爬公开通知
- 每条数据必须带：标题、正文、发布时间、来源 URL、部门
- 原始 JSON 落 data/raw/，清洗后落 data/clean/（均不入库）
