# ass-kfx-template

**繁體中文** ｜ [简体中文](README.zh-CN.md) ｜ [English](README.en.md)

> 一個給 Claude 用的 skill：把一份普通的 ASS 歌詞，變成動畫插入曲／OP／ED 等級的**卡拉OK特效字幕**。
> Claude 會讀歌詞、看畫面、設計特效、自己套用、自己截圖檢查，最後交給你「模板＋成品＋預覽影片」三件。

| 字落下回彈＋主題圖形（草莓） | 描邊預告（Yutils） | 碎成粒子（Yutils） |
|---|---|---|
| ![落下回彈](docs/images/berry.gif) | ![描邊預告](docs/images/ghost.gif) | ![碎成粒子](docs/images/dust.gif) |

---

## 這是什麼？

先打個比方：

- **ASS 字幕**像是一張「字要放在哪、什麼顏色」的清單。
- **Aegisub 的卡拉OK模板**像是一套「動作劇本」：寫一次「每個字從上面掉下來、落地壓扁彈一下」，它就會幫整首歌每一句、每一個字生出對應的動畫。
- **這個 skill** 則是教 Claude 當一個「會寫動作劇本的特效師」：它知道怎麼寫劇本、怎麼在 Aegisub 外面自己試演、怎麼截圖挑毛病，也記得過去被使用者指正過的地方。

所以你只要丟一份歌詞 `.ass`（最好再給影片），說一句「幫這首歌做特效」，就能拿到可以直接壓進影片的特效字幕。

## 可以做到什麼？

### 1. 真正「設計」過的特效，不是套公式

Claude 會先理解歌曲再動手：

- 讀完整首歌詞，抓出情緒（例如「小事終究會被忘記」）。
- 在每句中間截一張原片，看畫面裡有什麼物件、顏色（例如主角在做草莓果醬）。
- 找出切鏡時間點，把特效的高潮卡在切鏡那一格。
- 想一個把歌詞和畫面連起來的「核心點子」。

skill 裡附了一個完整範例「果醬罐」：果醬就是把草莓存起來，歌詞說小事會忘，那就讓整首歌一句一句把草莓存進罐子裡，罐子從空到滿，最後在切到果醬罐的鏡頭時蓋上紅白格子布、綁蝴蝶結。

### 2. 起始模板一行指令就生成

```bash
python ass-kfx-template/assets/starter_build.py 歌詞.ass 輸出_template.ass --main 日文樣式 --sub 中文樣式 --theme berry --yutils
```

生成的模板已經能跑，內容包括：

| 部分 | 效果 |
|---|---|
| 主行（大字） | 字從上方依序快速落下，落地壓扁再回彈，顏色從閃色褪回本色 |
| 副行（翻譯） | 在主行第一個字落地的同一格，從下方依序彈出 |
| 主題圖形 | 草莓 🍓／花／愛心／星星 四種，**只在進場和退場出現**，不會一直掛在旁邊 |
| 進場動作 | 5 套（從兩側飛入、從下方彈起、從上方砸落、沿上下緣穿過、描邊預告） |
| 退場動作 | 5 套（冒出上浮、中心炸開、沿字頂掃過、加速下墜、碎成粒子） |
| 防重複 | 相鄰兩句不會用同一套；數量、大小、角度再小幅隨機 |
| 短句 | 裝飾動畫按比例壓縮，但不低於一半 |
| 最後一句 | 單獨的收尾：主題圖形沿字頂慢慢滑過，留下一串閃光 |

所有參數（顏色、時間、高度……）都集中在模板第一行的 `C`、`P` 表裡，想改在 Aegisub 裡就能改。

### 3. 用 Yutils 做「照著字形」的特效

加上 `--yutils` 後，模板會在執行時載入 [Yutils](https://github.com/Youka/Yutils)，把字轉成真正的輪廓：

- **描邊預告**：字掉下來之前，落點先亮起一個空心的字形輪廓，字落進去時輪廓淡掉。像在說「這裡馬上會出現一個字」。
- **碎成粒子**：退場時，字照原本的筆畫碎成幾十顆小方塊，從左到右依序起飛、上飄、縮小消失。遠看還是那個字，接著慢慢散掉。很適合講「消逝」「回憶」「星空」的歌。

參考文件裡還寫了「沿輪廓走光」等更多照字形做的配方。

### 4. 不用開 Aegisub 也能套用、截圖

| 工具 | 做什麼 |
|---|---|
| `kt_apply.py` | 直接執行 Aegisub 內建的 `kara-templater.lua`，結果和在 Aegisub 裡按「套用卡拉OK模板」一樣 |
| `render.py` | 用 libass（ffmpeg）把指定時間點截成圖，也能連續截圖、放大局部 |
| `review.py` | 每句在進場、句中、退場各截一張，排成一張總覽圖，一眼看完整首 |

Claude 每做一版都會自己截圖逐張看，確認同步、對齊、在亮暗背景上都看得清楚，發現問題先修再給你看。

### 5. 自動處理缺字

`glyph_check.py` 開工第一步就檢查字體缺哪些字。遇到缺字時，`glyph2ass.py` 可以用本字體的筆畫**拼出**缺的字（例如用「别」「気」的部件拼），或從另一個字體借字，盡量不換字。

### 6. 會自我進化

這個 skill 會隨著每次做歌變強：

1. **記筆記**：每次交付後，使用者的意見會分類寫回 skill 裡。例如使用者說「太素了」，就記進設計經驗；說「這個效果好看」，就存進特效配方庫。
2. **防呆測試**：`selftest.py` 會跑 31 項冒煙測試，每個主題、每一套進退場都實際套用一次，模板器報錯必須是 0，最後再用 libass 截圖。
3. **升版打包**：`evolve.py` 先跑測試，**沒過就拒絕升版、拒絕打包**；過了才會把版本號 +1、寫進 `CHANGELOG.md`，並打包成新的 `.skill`。

## 安裝

### 當作 Claude skill 使用（推薦）

1. 把 `ass-kfx-template/` 這個資料夾壓成 zip，副檔名改成 `.skill`（或直接用 `.zip`）。
2. 在 Claude 的設定裡找到 Skills，上傳這個檔案。
3. 之後對 Claude 說「幫這首插入曲做特效字幕」「做個卡拉OK模板」，它就會自動使用這個 skill。

### 自己在電腦上跑腳本

需要：

- Python 3，加上 `pip install lupa fonttools pillow numpy`
- 帶 libass 的 ffmpeg
- Aegisub（`kt_apply.py` 要用到它的 `automation/autoload/kara-templater.lua`）

> 💡 在 Windows 上請用 **Windows 的 Python** 跑 `kt_apply.py`，字寬測量才會和 Aegisub 完全一致。WSL／Linux 也能跑，但可能差零點幾像素，只適合預覽。

### 用到 Yutils 時

如果要在 Aegisub 裡重新套用有 `--yutils` 的模板，請把 `ass-kfx-template/scripts/Yutils.lua` 複製到下面任一個資料夾（裝過 DependencyControl 的通常已經有，不用再放）：

- `Aegisub 安裝目錄\automation\include\`
- `%APPDATA%\Aegisub\automation\include\`

## 快速上手（手動流程）

```bash
cd ass-kfx-template

# 1. 查缺字
python scripts/glyph_check.py 歌詞.ass

# 2. 生成起始模板
python assets/starter_build.py 歌詞.ass song_template.ass --main 日 --sub 中 --theme berry --yutils

# 3. 套用（模板器報錯必須是 0）
python scripts/kt_apply.py song_template.ass song_fx.ass --aegisub "C:\Program Files\Aegisub"

# 4. 截圖檢查（每句進場／句中／退場）
python scripts/review.py song_fx.ass check --video 原片.mp4 --style 日

# 5. 壓預覽影片
ffmpeg -ss 起 -to 止 -copyts -i 原片.mp4 -vf "subtitles=song_fx.ass" -c:a aac -ss 起 preview.mp4
```

歌詞的寫法有一個規定：**每句開頭只放一個 `{\k1}`，特效欄填 `karaoke`**。`starter_build.py` 會自動幫你改好。

## 檔案結構

```
ass-kfx-template/
├── SKILL.md                  給 Claude 看的操作說明（工作流程、交付規範、自我進化）
├── CHANGELOG.md              每一版改了什麼、還沒做的想法
├── requirements.txt
├── assets/
│   ├── starter_build.py      起始模板生成器（主題、5 套進場、5 套退場）
│   ├── shapes.py             主題圖形素材（草莓、花、愛心、星星……）
│   └── examples/jam_jar/     「果醬罐」完整範例的程式碼（只供閱讀）
├── scripts/
│   ├── kt_apply.py / mock.lua  在 Aegisub 外執行 kara-templater
│   ├── render.py / review.py   libass 截圖、逐句總覽
│   ├── glyph_check.py / glyph2ass.py / fontfind.py   查缺字、字轉繪圖、拼字
│   ├── Yutils.lua            Yutils 函式庫（MIT）
│   ├── selftest.py           冒煙測試
│   └── evolve.py             測試 → 升版 → 打包
├── references/
│   ├── design-lessons.md     使用者真實的修改意見（開工前必讀）
│   ├── showcase-jam-jar.md   目標水準的完整範例解說
│   ├── effect-recipes.md     特效配方庫 A～N（落下回彈、打字機、水墨暈開、碎成粒子……）
│   ├── templater-cookbook.md 模板器技術手冊（含 Yutils 用法）
│   └── missing-glyphs.md     補缺字方法
└── tests/smoke_song.ass      冒煙測試用的歌詞
```

## 限制

- 只保證 **libass**（mpv、ffmpeg 壓制、MPC-HC 的 libass 模式）。VSFilter 不支援包圍盒鎖定的寫法，多層圖形會錯位。
- 「碎成粒子」一句 10 個字大約會多 600 行事件。壓制沒有問題；播放器即時播放吃力時，可以調大 `YP.step` 或調小 `YP.max`。
- Windows 上直接透過 Yutils 用 GDI 取字形的路徑，還沒在真正的 Windows 上跑過 `selftest.py`（見 `CHANGELOG.md`「還沒做的想法」）。

## 授權

MIT © Carinoasd。`scripts/Yutils.lua` 來自 [Youka/Yutils](https://github.com/Youka/Yutils)，同為 MIT 授權，原始版權聲明保留在檔案開頭。
