# 更新记录

## v3（2026-09-26）
- 描边预告不再早于句首出现（短间隔时会和上一句的粒子叠在一起）；透明度调淡、加一点深色投影，亮背景也看得到
- 碎成粒子的存活时间随短句按比例缩短；粒子加深色小投影，亮背景也看得到
- 新增自我进化机制：SKILL.md「自我进化」一节、tests/smoke_song.ass、scripts/selftest.py（31 项冒烟测试）、scripts/evolve.py（测试没过就不升版不打包）、CHANGELOG.md

## v2（2026-09-26）
- 模板可以直接 require Yutils（github.com/Youka/Yutils，MIT，skill 自带一份在 scripts/Yutils.lua）
- starter_build.py 加 --yutils：进场第 5 套「描边预告」、退场第 5 套「碎成粒子」，按字的真实形状做效果
- kt_apply.py / mock.lua：在 Aegisub 外也能载入 Yutils；非 Windows 用 Python 按字体文件取字形轮廓
- extras() 改用工作表 L.jobs，不再生成一堆零时长的空行（看得到的特效和 v1 完全一样）
- 文档：cookbook 第 12 节（Yutils 用法和坐标约定）、effect-recipes 新增 L、M、N 三个配方

## v1
- 最初版本：起始模板生成器、Aegisub 外套用模板、libass 截图检查、补缺字、果酱罐范例

## 还没做的想法
- 配方 N「沿轮廓走光」只有写法说明，还没做进 starter_build.py
- 补字（GS 里的字）目前不参与描边预告和碎成粒子，可以改用 glyph() 的绘图来做
- Windows 上 kt_apply.py 直接调用 Yutils 的 GDI 取字形，还没在真的 Windows 上跑过 selftest
- 跨句的累积效果（像果酱罐那样贯穿整首歌）还没有通用的起始代码
