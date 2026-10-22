// 珠科百事通 · 初赛作品介绍 PPT 生成器（三个风格版本）
// 用法：node ppt/gen.js
const PptxGenJS = require('pptxgenjs');

const FONT = 'Microsoft YaHei';

// 三套配色
const palettes = {
  zcst: {  // 版本A：珠科官网红
    label: '珠科官网红',
    primary: 'B7354B', dark: '9E2438', light: 'DA2E48', gold: 'F6C344',
    coverBg: '9E2438', bg: 'FDF6F6', card: 'FFFFFF',
    text: '2D2A2A', muted: '8A7A7A', accent: 'B7354B',
  },
  tech: {  // 版本B：科技蓝
    label: '科技蓝',
    primary: '1E2761', dark: '16213E', light: '065A82', gold: 'F6C344',
    coverBg: '1E2761', bg: 'F4F7FC', card: 'FFFFFF',
    text: '2D3436', muted: '7A8A9A', accent: '00CEC9',
  },
  clean: { // 版本C：简约现代
    label: '简约现代',
    primary: '028090', dark: '21295C', light: '00A896', gold: 'F6C344',
    coverBg: '21295C', bg: 'F7FAFA', card: 'FFFFFF',
    text: '333333', muted: '90999B', accent: '02C39A',
  },
};

function buildDeck(p, outFile) {
  const pptx = new PptxGenJS();
  pptx.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5
  const W = 13.33, H = 7.5;

  // 通用：标题 + 小标记（圆形莲花意象）
  function header(s, title, sub) {
    s.background = { color: p.bg };
    s.addText(title, { x: 0.6, y: 0.45, w: 11.0, h: 0.9, fontSize: 30, bold: true, color: p.dark, fontFace: FONT });
    if (sub) s.addText(sub, { x: 0.62, y: 1.25, w: 11.0, h: 0.4, fontSize: 13, color: p.muted, fontFace: FONT });
  }
  // 数字卡片
  function statCard(s, x, y, w, num, label, color) {
    s.addShape(pptx.ShapeType.roundRect, { x, y, w, h: 1.7, fill: { color: p.card }, line: { color: 'EFE6E6', width: 0.75 }, rectRadius: 0.08 });
    s.addText(num, { x, y: y + 0.2, w, h: 0.75, fontSize: 34, bold: true, color: color || p.primary, fontFace: FONT, align: 'center' });
    s.addText(label, { x, y: y + 0.98, w, h: 0.5, fontSize: 13, color: p.muted, fontFace: FONT, align: 'center' });
  }

  // ===== P1 封面 =====
  let s = pptx.addSlide();
  s.background = { color: p.coverBg };
  // 顶部莲花意象：圆形光环
  s.addShape(pptx.ShapeType.ellipse, { x: W / 2 - 1.1, y: 0.9, w: 2.2, h: 2.2, fill: { color: p.coverBg }, line: { color: p.gold, width: 2 } });
  s.addText('珠科', { x: W / 2 - 1.1, y: 1.5, w: 2.2, h: 1.0, fontSize: 40, bold: true, color: 'FFFFFF', fontFace: FONT, align: 'center', valign: 'middle' });
  s.addText('珠科百事通', { x: 1.0, y: 3.15, w: W - 2, h: 1.2, fontSize: 60, bold: true, color: 'FFFFFF', fontFace: FONT, align: 'center' });
  s.addText('校务生活 RAG 智能问答平台', { x: 1.0, y: 4.35, w: W - 2, h: 0.6, fontSize: 24, color: 'FFFFFF', fontFace: FONT, align: 'center' });
  s.addText('一句话问 · 3 秒答 · 答案必带官方出处', { x: 1.0, y: 5.05, w: W - 2, h: 0.5, fontSize: 17, color: p.gold, fontFace: FONT, align: 'center' });
  s.addText('RAGGO 队 ｜ 方向 05：RAG 知识库问答 ｜ 珠海科技学院', { x: 1.0, y: 6.55, w: W - 2, h: 0.4, fontSize: 13, color: 'F3D9D9', fontFace: FONT, align: 'center' });

  // ===== P2 场景背景 =====
  s = pptx.addSlide();
  header(s, '3.1 万在校生，校务信息散落在 4 个官网');
  statCard(s, 0.6, 2.0, 2.85, '3.1 万', '在校生');
  statCard(s, 3.65, 2.0, 2.85, '4 个', '部门官网');
  statCard(s, 6.7, 2.0, 2.85, '254 篇', '官方通知');
  statCard(s, 9.75, 2.0, 2.85, '6 类', '高频场景');
  s.addText('选课规则、报修电话、校巴时刻、奖助政策、考试报名、学籍事务……学生想查一件事，往往要在教务处、后勤处、招生办、图书馆多个官网间反复翻找，信息分散、时效难辨、真假难分。', { x: 0.6, y: 4.15, w: 12.1, h: 1.4, fontSize: 16, color: p.text, fontFace: FONT, lineSpacingMultiple: 1.4, valign: 'middle' });

  // ===== P3 解决方案 =====
  s = pptx.addSlide();
  header(s, '一句话问，3 秒答，答案必带官方出处');
  const steps3 = [
    { t: '01 提问', d: '自然语言输入校务问题' },
    { t: '02 检索', d: '双路召回 254 篇官方通知' },
    { t: '03 生成', d: '大模型生成带出处回答' },
  ];
  steps3.forEach((it, i) => {
    const x = 0.6 + i * 4.2;
    s.addShape(pptx.ShapeType.roundRect, { x, y: 2.3, w: 3.6, h: 2.4, fill: { color: p.card }, line: { color: 'EFE6E6', width: 0.75 }, rectRadius: 0.08 });
    s.addShape(pptx.ShapeType.ellipse, { x: x + 0.3, y: 2.55, w: 0.7, h: 0.7, fill: { color: p.primary } });
    s.addText(String(i + 1), { x: x + 0.3, y: 2.55, w: 0.7, h: 0.7, fontSize: 20, bold: true, color: 'FFFFFF', fontFace: FONT, align: 'center', valign: 'middle' });
    s.addText(it.t, { x: x + 1.15, y: 2.62, w: 2.3, h: 0.55, fontSize: 20, bold: true, color: p.dark, fontFace: FONT, valign: 'middle' });
    s.addText(it.d, { x: x + 0.3, y: 3.55, w: 3.0, h: 0.9, fontSize: 14, color: p.muted, fontFace: FONT, lineSpacingMultiple: 1.3 });
    if (i < 2) s.addText('→', { x: x + 3.55, y: 2.9, w: 0.6, h: 0.6, fontSize: 28, color: p.primary, fontFace: FONT, align: 'center' });
  });
  s.addText('基于 RAG（检索增强生成），回答直接引用官方通知原文，杜绝大模型「一本正经胡说八道」。', { x: 0.6, y: 5.15, w: 12.1, h: 0.8, fontSize: 15, color: p.text, fontFace: FONT });

  // ===== P4 产品展示 =====
  s = pptx.addSlide();
  header(s, '四端一体的校务问答');
  const feats = [
    { t: 'Web 门户', d: '首页概览、智能问答、通知速览、关于，珠科红官网风' },
    { t: '智能问答', d: '对话式提问，打字机回复，来源引用卡片' },
    { t: '通知速览', d: '254 篇通知，部门/栏目筛选，时效状态标签' },
    { t: '微信小程序', d: '学生端搜索提问，随时随地问校务' },
  ];
  feats.forEach((it, i) => {
    const x = 0.6 + (i % 2) * 6.2, y = 2.1 + Math.floor(i / 2) * 2.2;
    s.addShape(pptx.ShapeType.roundRect, { x, y, w: 5.9, h: 1.9, fill: { color: p.card }, line: { color: 'EFE6E6', width: 0.75 }, rectRadius: 0.08 });
    s.addShape(pptx.ShapeType.ellipse, { x: x + 0.3, y: y + 0.35, w: 0.6, h: 0.6, fill: { color: p.light } });
    s.addText(it.t.slice(0, 1), { x: x + 0.3, y: y + 0.35, w: 0.6, h: 0.6, fontSize: 16, bold: true, color: 'FFFFFF', fontFace: FONT, align: 'center', valign: 'middle' });
    s.addText(it.t, { x: x + 1.1, y: y + 0.3, w: 4.5, h: 0.5, fontSize: 18, bold: true, color: p.dark, fontFace: FONT });
    s.addText(it.d, { x: x + 1.1, y: y + 0.85, w: 4.6, h: 0.85, fontSize: 13, color: p.muted, fontFace: FONT, lineSpacingMultiple: 1.3 });
  });

  // ===== P5 功能架构 =====
  s = pptx.addSlide();
  header(s, '七步 RAG 检索链路', '数据层 → 检索层 → 生成层');
  const arch = [
    { t: '数据采集', g: 'data' }, { t: '清洗入库', g: 'data' }, { t: '混合检索', g: 'retr' },
    { t: 'RRF 融合', g: 'retr' }, { t: '重排序', g: 'retr' }, { t: '时效降权', g: 'retr' }, { t: 'LLM 生成', g: 'gen' },
  ];
  const gcolor = { data: p.primary, retr: p.light, gen: p.gold };
  arch.forEach((it, i) => {
    const x = 0.5 + i * 1.78;
    s.addShape(pptx.ShapeType.roundRect, { x, y: 2.6, w: 1.6, h: 1.5, fill: { color: p.card }, line: { color: gcolor[it.g], width: 1.5 }, rectRadius: 0.1 });
    s.addShape(pptx.ShapeType.rect, { x, y: 2.6, w: 1.6, h: 0.12, fill: { color: gcolor[it.g] } });
    s.addText(it.t, { x, y: 2.95, w: 1.6, h: 0.9, fontSize: 14, bold: true, color: p.dark, fontFace: FONT, align: 'center', valign: 'middle' });
    if (i < 6) s.addText('→', { x: x + 1.5, y: 2.95, w: 0.4, h: 0.5, fontSize: 18, color: p.muted, fontFace: FONT, align: 'center' });
  });
  const legend = [['数据层', p.primary], ['检索层', p.light], ['生成层', p.gold]];
  legend.forEach((lg, i) => {
    const x = 3.3 + i * 2.6;
    s.addShape(pptx.ShapeType.ellipse, { x, y: 4.8, w: 0.3, h: 0.3, fill: { color: lg[1] } });
    s.addText(lg[0], { x: x + 0.45, y: 4.72, w: 1.6, h: 0.4, fontSize: 13, color: p.muted, fontFace: FONT });
  });
  s.addText('FTS5 关键词 + bge-m3 语义向量双路召回，RRF 融合后 bge-reranker 精排，时效降权让过时通知下沉，最终由华为云 MaaS 大模型生成带出处回答。', { x: 0.6, y: 5.5, w: 12.1, h: 0.9, fontSize: 14, color: p.text, fontFace: FONT, lineSpacingMultiple: 1.35 });

  // ===== P6 核心亮点 =====
  s = pptx.addSlide();
  header(s, '五个差异化亮点');
  const highs = [
    { t: '真实数据', d: '254 篇官方通知，爬虫直采教务处/后勤处/招生办' },
    { t: '双路混合检索', d: 'FTS5 关键词 + bge-m3 语义向量，RRF 融合' },
    { t: '时效降权', d: '过时通知自动下沉，优先返回当前有效信息' },
    { t: '答案必带出处', d: '每条回答附来源链接，可一键查看官方原文' },
    { t: '评测驱动', d: '100 问真实学生评测集，Hit Rate 87%' },
  ];
  highs.forEach((it, i) => {
    const y = 2.0 + i * 1.0;
    s.addShape(pptx.ShapeType.ellipse, { x: 0.7, y: y + 0.1, w: 0.55, h: 0.55, fill: { color: p.primary } });
    s.addText(String(i + 1), { x: 0.7, y: y + 0.1, w: 0.55, h: 0.55, fontSize: 16, bold: true, color: 'FFFFFF', fontFace: FONT, align: 'center', valign: 'middle' });
    s.addText(it.t, { x: 1.5, y: y, w: 3.4, h: 0.5, fontSize: 18, bold: true, color: p.dark, fontFace: FONT });
    s.addText(it.d, { x: 5.1, y: y, w: 7.5, h: 0.6, fontSize: 14, color: p.text, fontFace: FONT, valign: 'middle' });
  });

  // ===== P7 评测数据 =====
  s = pptx.addSlide();
  header(s, '100 问评测：Hit Rate 87%');
  const metrics = [
    { n: '87.1%', l: 'Hit Rate 命中率' },
    { n: '0.84', l: 'MRR 平均倒数排名' },
    { n: '90%', l: '拒答成功率' },
    { n: '254', l: '收录官方通知' },
  ];
  metrics.forEach((m, i) => {
    const x = 0.6 + i * 3.1;
    s.addShape(pptx.ShapeType.roundRect, { x, y: 2.2, w: 2.9, h: 2.4, fill: { color: p.card }, line: { color: 'EFE6E6', width: 0.75 }, rectRadius: 0.08 });
    s.addText(m.n, { x, y: 2.6, w: 2.9, h: 0.9, fontSize: 44, bold: true, color: p.primary, fontFace: FONT, align: 'center' });
    s.addText(m.l, { x, y: 3.7, w: 2.9, h: 0.5, fontSize: 13, color: p.muted, fontFace: FONT, align: 'center' });
  });
  s.addText('基于内部 100 问真实学生评测集，Hit Rate = 答案来源命中期望文档的比例。', { x: 0.6, y: 5.1, w: 12.1, h: 0.5, fontSize: 13, color: p.muted, fontFace: FONT });

  // ===== P8 码道应用 =====
  s = pptx.addSlide();
  header(s, '华为云码道 CodeArts 全流程驱动');
  const codearts = [
    { t: '环境搭建', d: '依赖安装、建库、服务启动脚本生成' },
    { t: '代码生成', d: '爬虫、检索、FastAPI 接口、前端门户' },
    { t: '调试排错', d: '检索排序、拒答判定、引用校验排错' },
    { t: '文档生成', d: '方案书、分工书、README、评测报告' },
  ];
  codearts.forEach((it, i) => {
    const x = 0.6 + (i % 2) * 6.2, y = 2.1 + Math.floor(i / 2) * 2.0;
    s.addShape(pptx.ShapeType.roundRect, { x, y, w: 5.9, h: 1.7, fill: { color: p.card }, line: { color: 'EFE6E6', width: 0.75 }, rectRadius: 0.08 });
    s.addShape(pptx.ShapeType.ellipse, { x: x + 0.3, y: y + 0.4, w: 0.6, h: 0.6, fill: { color: p.accent } });
    s.addText('码', { x: x + 0.3, y: y + 0.4, w: 0.6, h: 0.6, fontSize: 15, bold: true, color: 'FFFFFF', fontFace: FONT, align: 'center', valign: 'middle' });
    s.addText(it.t, { x: x + 1.1, y: y + 0.25, w: 4.5, h: 0.5, fontSize: 18, bold: true, color: p.dark, fontFace: FONT });
    s.addText(it.d, { x: x + 1.1, y: y + 0.8, w: 4.6, h: 0.7, fontSize: 13, color: p.muted, fontFace: FONT, lineSpacingMultiple: 1.3 });
  });
  s.addText('码道贯穿开发全流程，Prompt 设计、代码生成、重构、排错均有完整记录，随作品提交 codearts_proof 证明材料。', { x: 0.6, y: 6.15, w: 12.1, h: 0.6, fontSize: 14, color: p.text, fontFace: FONT });

  // ===== P9 团队与技术栈 =====
  s = pptx.addSlide();
  header(s, '团队与技术栈');
  // 团队
  s.addText('团队', { x: 0.6, y: 2.0, w: 2.0, h: 0.5, fontSize: 20, bold: true, color: p.dark, fontFace: FONT });
  const team = ['ZY（队长）', 'ZC', 'HJQ'];
  team.forEach((t, i) => {
    const x = 0.6 + i * 1.8;
    s.addShape(pptx.ShapeType.ellipse, { x, y: 2.7, w: 1.3, h: 1.3, fill: { color: p.light } });
    s.addText(t.split('（')[0], { x, y: 2.7, w: 1.3, h: 1.3, fontSize: 24, bold: true, color: 'FFFFFF', fontFace: FONT, align: 'center', valign: 'middle' });
    s.addText(t, { x: x - 0.25, y: 4.15, w: 1.8, h: 0.4, fontSize: 14, bold: true, color: p.dark, fontFace: FONT, align: 'center' });
  });
  // 技术栈
  s.addText('技术栈', { x: 6.6, y: 2.0, w: 2.0, h: 0.5, fontSize: 20, bold: true, color: p.dark, fontFace: FONT });
  const stack = ['Python', 'FastAPI', 'SQLite FTS5', 'bge-m3', 'bge-reranker', '华为云 MaaS'];
  stack.forEach((t, i) => {
    const x = 6.6 + (i % 3) * 2.1, y = 2.7 + Math.floor(i / 3) * 1.1;
    s.addShape(pptx.ShapeType.roundRect, { x, y, w: 1.9, h: 0.8, fill: { color: p.card }, line: { color: 'EFE6E6', width: 0.75 }, rectRadius: 0.15 });
    s.addText(t, { x, y, w: 1.9, h: 0.8, fontSize: 13, bold: true, color: p.text, fontFace: FONT, align: 'center', valign: 'middle' });
  });

  // ===== P10 结尾 =====
  s = pptx.addSlide();
  s.background = { color: p.coverBg };
  s.addText('感谢观看', { x: 1.0, y: 2.3, w: W - 2, h: 1.1, fontSize: 48, bold: true, color: 'FFFFFF', fontFace: FONT, align: 'center' });
  s.addText('珠科百事通 · 校务生活 RAG 智能问答平台', { x: 1.0, y: 3.6, w: W - 2, h: 0.5, fontSize: 18, color: 'F3D9D9', fontFace: FONT, align: 'center' });
  s.addText('在线体验：https://ikjivc5w-8000.devbridge-s2.hwtunnel.com/', { x: 1.0, y: 4.7, w: W - 2, h: 0.5, fontSize: 16, color: p.gold, fontFace: FONT, align: 'center' });
  s.addText('GitCode：https://gitcode.com/ZSIOM/zhike-baishitong', { x: 1.0, y: 5.3, w: W - 2, h: 0.5, fontSize: 16, color: p.gold, fontFace: FONT, align: 'center' });

  pptx.writeFile({ fileName: outFile }).then(() => console.log('生成完成:', outFile));
}

Object.keys(palettes).forEach((k) => {
  buildDeck(palettes[k], `ppt/珠科百事通_作品介绍_${palettes[k].label}.pptx`);
});
