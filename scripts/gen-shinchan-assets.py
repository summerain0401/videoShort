#!/usr/bin/env python3
"""
gen-shinchan-assets.py — 生成 2.0 野原经济学（蜡笔小新 IP）系列精美角色、道具与背景素材，
并同步更新到 shared/material-library.json。
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "shared"
CHARS_DIR = SHARED / "characters"
PROPS_DIR = SHARED / "props"
BGS_DIR = SHARED / "backgrounds"

CHARS_DIR.mkdir(parents=True, exist_ok=True)
PROPS_DIR.mkdir(parents=True, exist_ok=True)
BGS_DIR.mkdir(parents=True, exist_ok=True)

def get_font(size: int, bold: bool = False):
    font_paths = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Arial Unicode.ttf",
    ]
    for p in font_paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()

# ----------------- 角色绘制辅助函数 -----------------

def create_shinchan(emotion="smile", w=600, h=800):
    """绘制小新角色立绘（蜡笔小新手绘粗线条卡通风格）"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    
    # 皮肤色、衣服颜色
    SKIN = (255, 224, 189, 255)
    RED = (235, 60, 50, 255)
    YELLOW = (255, 215, 0, 255)
    BLACK = (20, 20, 20, 255)
    WHITE = (255, 255, 255, 255)
    BLUSH = (255, 140, 160, 220)
    
    cx, cy = w // 2, h // 2 + 30
    
    # 1. 身体（红上衣）
    d.rounded_rectangle([cx - 110, cy + 80, cx + 110, cy + 240], radius=35, fill=RED, outline=BLACK, width=7)
    
    # 2. 短裤（黄色短裤）
    d.rounded_rectangle([cx - 100, cy + 220, cx + 100, cy + 300], radius=20, fill=YELLOW, outline=BLACK, width=7)
    
    # 3. 双腿与黄色小鞋
    d.rectangle([cx - 70, cy + 290, cx - 25, cy + 335], fill=SKIN, outline=BLACK, width=6)
    d.rectangle([cx + 25, cy + 290, cx + 70, cy + 335], fill=SKIN, outline=BLACK, width=6)
    d.ellipse([cx - 85, cy + 325, cx - 15, cy + 360], fill=YELLOW, outline=BLACK, width=6)
    d.ellipse([cx + 15, cy + 325, cx + 85, cy + 360], fill=YELLOW, outline=BLACK, width=6)
    
    # 4. 手臂
    if emotion == "explaining":
        # 右手上举讲解
        d.line([(cx + 95, cy + 120), (cx + 170, cy + 60)], fill=RED, width=45)
        d.ellipse([cx + 150, cy + 40, cx + 195, cy + 85], fill=SKIN, outline=BLACK, width=6)
        # 左手自然下垂
        d.line([(cx - 95, cy + 120), (cx - 140, cy + 190)], fill=RED, width=45)
        d.ellipse([cx - 165, cy + 180, cx - 120, cy + 225], fill=SKIN, outline=BLACK, width=6)
    elif emotion == "smug":
        # 双手叉腰
        d.line([(cx - 95, cy + 130), (cx - 155, cy + 175), (cx - 95, cy + 210)], fill=RED, width=38)
        d.line([(cx + 95, cy + 130), (cx + 155, cy + 175), (cx + 95, cy + 210)], fill=RED, width=38)
    elif emotion == "thinking":
        # 单手托腮
        d.line([(cx + 95, cy + 130), (cx + 135, cy + 70), (cx + 80, cy + 30)], fill=RED, width=38)
        d.ellipse([cx + 65, cy + 15, cx + 105, cy + 55], fill=SKIN, outline=BLACK, width=6)
        d.line([(cx - 95, cy + 120), (cx - 130, cy + 180)], fill=RED, width=42)
    else:
        # 普通双手自然张开
        d.line([(cx - 95, cy + 120), (cx - 150, cy + 180)], fill=RED, width=42)
        d.ellipse([cx - 170, cy + 170, cx - 125, cy + 215], fill=SKIN, outline=BLACK, width=6)
        d.line([(cx + 95, cy + 120), (cx + 150, cy + 180)], fill=RED, width=42)
        d.ellipse([cx + 125, cy + 170, cx + 170, cy + 215], fill=SKIN, outline=BLACK, width=6)
        
    # 5. 小新特有经典大土豆脸蛋轮廓 (左侧鼓鼓的标志性脸颊)
    head_box = [cx - 170, cy - 170, cx + 160, cy + 100]
    d.ellipse(head_box, fill=SKIN, outline=BLACK, width=8)
    # 左侧突出的萌系肉嘟嘟脸颊
    d.ellipse([cx - 185, cy - 60, cx - 70, cy + 85], fill=SKIN, outline=None)
    d.arc([cx - 185, cy - 60, cx - 70, cy + 85], 90, 270, fill=BLACK, width=8)
    
    # 6. 小新短发（黑色圆弧发际）
    d.pieslice([cx - 165, cy - 170, cx + 155, cy - 10], 180, 360, fill=BLACK)
    
    # 7. 标志性海苔粗眉毛
    d.rounded_rectangle([cx - 130, cy - 85, cx - 35, cy - 50], radius=18, fill=BLACK)
    d.rounded_rectangle([cx + 25, cy - 85, cx + 120, cy - 50], radius=18, fill=BLACK)
    
    # 8. 眼睛
    if emotion in ["smile", "smug"]:
        # 弯弯笑眼
        d.arc([cx - 115, cy - 45, cx - 55, cy + 5], 180, 360, fill=BLACK, width=8)
        d.arc([cx + 40, cy - 45, cx + 100, cy + 5], 180, 360, fill=BLACK, width=8)
    elif emotion == "shocked":
        # 震惊白圆眼 + 小黑点
        d.ellipse([cx - 115, cy - 45, cx - 55, cy + 15], fill=WHITE, outline=BLACK, width=6)
        d.ellipse([cx - 90, cy - 20, cx - 75, cy - 5], fill=BLACK)
        d.ellipse([cx + 40, cy - 45, cx + 100, cy + 15], fill=WHITE, outline=BLACK, width=6)
        d.ellipse([cx + 65, cy - 20, cx + 80, cy - 5], fill=BLACK)
    elif emotion == "thinking":
        # 眼神向右上瞄
        d.ellipse([cx - 110, cy - 40, cx - 60, cy + 10], fill=WHITE, outline=BLACK, width=6)
        d.ellipse([cx - 85, cy - 35, cx - 65, cy - 15], fill=BLACK)
        d.ellipse([cx + 45, cy - 40, cx + 95, cy + 10], fill=WHITE, outline=BLACK, width=6)
        d.ellipse([cx + 70, cy - 35, cx + 90, cy - 15], fill=BLACK)
    else: # explaining, confused
        d.ellipse([cx - 110, cy - 40, cx - 60, cy + 10], fill=WHITE, outline=BLACK, width=6)
        d.ellipse([cx - 92, cy - 22, cx - 72, cy - 2], fill=BLACK)
        d.ellipse([cx + 45, cy - 40, cx + 95, cy + 10], fill=WHITE, outline=BLACK, width=6)
        d.ellipse([cx + 62, cy - 22, cx + 82, cy - 2], fill=BLACK)

    # 9. 腮红
    d.ellipse([cx - 155, cy - 5, cx - 95, cy + 35], fill=BLUSH)
    d.ellipse([cx + 85, cy - 5, cx + 145, cy + 35], fill=BLUSH)
    
    # 10. 嘴巴
    if emotion == "smile":
        d.pieslice([cx - 45, cy + 5, cx + 35, cy + 65], 0, 180, fill=(210, 40, 50, 255), outline=BLACK, width=6)
    elif emotion == "shocked":
        d.ellipse([cx - 30, cy + 10, cx + 25, cy + 70], fill=(180, 20, 30, 255), outline=BLACK, width=6)
    elif emotion == "smug":
        d.arc([cx - 40, cy + 10, cx + 30, cy + 45], 0, 180, fill=BLACK, width=7)
    elif emotion == "explaining":
        d.pieslice([cx - 35, cy + 15, cx + 25, cy + 55], 0, 180, fill=(220, 50, 60, 255), outline=BLACK, width=5)
    else:
        d.line([(cx - 30, cy + 35), (cx + 20, cy + 35)], fill=BLACK, width=7)
        
    return img

def create_misae(emotion="shopping", w=600, h=850):
    """绘制美伢（Misae）立绘：卷发、主妇围裙、生动表情"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    
    SKIN = (255, 226, 195, 255)
    HAIR = (110, 60, 40, 255)
    PINK = (245, 130, 165, 255)
    PURPLE = (160, 110, 190, 255)
    BLACK = (20, 20, 20, 255)
    WHITE = (255, 255, 255, 255)
    
    cx, cy = w // 2, h // 2 + 20
    
    # 身体（粉色上衣+紫色裙子）
    d.rounded_rectangle([cx - 100, cy + 100, cx + 100, cy + 280], radius=30, fill=PINK, outline=BLACK, width=7)
    d.polygon([(cx - 110, cy + 270), (cx + 110, cy + 270), (cx + 140, cy + 380), (cx - 140, cy + 380)], fill=PURPLE, outline=BLACK)
    
    # 头发后部卷发
    d.ellipse([cx - 180, cy - 210, cx + 180, cy + 20], fill=HAIR, outline=BLACK, width=8)
    for ox in [-160, -120, 120, 160]:
        d.ellipse([cx + ox - 40, cy - 80, cx + ox + 40, cy + 40], fill=HAIR, outline=BLACK, width=7)
        
    # 脸型
    d.ellipse([cx - 130, cy - 160, cx + 130, cy + 70], fill=SKIN, outline=BLACK, width=7)
    
    # 头发前部刘海
    d.pieslice([cx - 130, cy - 160, cx + 130, cy - 50], 180, 360, fill=HAIR)
    
    # 眉毛与眼睛
    if emotion == "angry":
        d.line([(cx - 95, cy - 65), (cx - 25, cy - 90)], fill=BLACK, width=7)
        d.line([(cx + 25, cy - 90), (cx + 95, cy - 65)], fill=BLACK, width=7)
        d.arc([cx - 90, cy - 70, cx - 35, cy - 20], 0, 180, fill=BLACK, width=7)
        d.arc([cx + 35, cy - 70, cx + 90, cy - 20], 0, 180, fill=BLACK, width=7)
        # 愤怒咆哮大嘴
        d.ellipse([cx - 50, cy + 5, cx + 50, cy + 75], fill=(200, 30, 40, 255), outline=BLACK, width=7)
    elif emotion == "shocked":
        d.arc([cx - 90, cy - 95, cx - 30, cy - 55], 180, 360, fill=BLACK, width=6)
        d.arc([cx + 30, cy - 95, cx + 90, cy - 55], 180, 360, fill=BLACK, width=6)
        d.ellipse([cx - 85, cy - 55, cx - 35, cy - 5], fill=WHITE, outline=BLACK, width=6)
        d.ellipse([cx - 65, cy - 35, cx - 55, cy - 25], fill=BLACK)
        d.ellipse([cx + 35, cy - 55, cx + 85, cy - 5], fill=WHITE, outline=BLACK, width=6)
        d.ellipse([cx + 55, cy - 35, cx + 65, cy - 25], fill=BLACK)
        d.ellipse([cx - 35, cy + 15, cx + 35, cy + 70], fill=(180, 30, 40, 255), outline=BLACK, width=6)
    else: # shopping / smile / calculating
        d.arc([cx - 90, cy - 85, cx - 30, cy - 55], 180, 360, fill=BLACK, width=6)
        d.arc([cx + 30, cy - 85, cx + 90, cy - 55], 180, 360, fill=BLACK, width=6)
        d.ellipse([cx - 80, cy - 50, cx - 40, cy - 10], fill=BLACK)
        d.ellipse([cx + 40, cy - 50, cx + 80, cy - 10], fill=BLACK)
        d.pieslice([cx - 40, cy + 10, cx + 40, cy + 55], 0, 180, fill=(220, 50, 60, 255), outline=BLACK, width=6)
        
    return img

def create_hiroshi(emotion="tired", w=600, h=880):
    """绘制广志（Hiroshi）立绘：长脸胡茬、西装/衬衫、社畜气质"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    
    SKIN = (255, 224, 192, 255)
    SUIT = (65, 115, 160, 255)
    TIE = (210, 45, 45, 255)
    HAIR = (40, 40, 45, 255)
    BLACK = (20, 20, 20, 255)
    WHITE = (255, 255, 255, 255)
    
    cx, cy = w // 2, h // 2 + 30
    
    # 西装身体
    d.rounded_rectangle([cx - 120, cy + 120, cx + 120, cy + 340], radius=25, fill=SUIT, outline=BLACK, width=7)
    # 白衬衫领与红领带
    d.polygon([(cx - 40, cy + 120), (cx + 40, cy + 120), (cx, cy + 190)], fill=WHITE, outline=BLACK)
    d.polygon([(cx - 15, cy + 140), (cx + 15, cy + 140), (cx + 22, cy + 270), (cx, cy + 300), (cx - 22, cy + 270)], fill=TIE, outline=BLACK)
    
    # 头部：广志标志性方形长脸
    d.rounded_rectangle([cx - 105, cy - 180, cx + 105, cy + 90], radius=45, fill=SKIN, outline=BLACK, width=7)
    # 头发（凌乱分头）
    d.rounded_rectangle([cx - 115, cy - 210, cx + 115, cy - 120], radius=30, fill=HAIR, outline=BLACK, width=6)
    
    # 标志性青色胡茬底色
    d.ellipse([cx - 75, cy + 35, cx + 75, cy + 85], fill=(210, 225, 215, 160))
    
    # 粗浓眉毛
    d.line([(cx - 85, cy - 90), (cx - 25, cy - 90)], fill=BLACK, width=8)
    d.line([(cx + 25, cy - 90), (cx + 85, cy - 90)], fill=BLACK, width=8)
    
    if emotion == "tired":
        # 下垂疲惫眼
        d.line([(cx - 80, cy - 65), (cx - 30, cy - 50)], fill=BLACK, width=6)
        d.line([(cx + 30, cy - 50), (cx + 80, cy - 65)], fill=BLACK, width=6)
        d.line([(cx - 40, cy + 40), (cx + 40, cy + 40)], fill=BLACK, width=6)
    elif emotion == "shocked":
        d.ellipse([cx - 75, cy - 70, cx - 35, cy - 30], fill=WHITE, outline=BLACK, width=5)
        d.ellipse([cx - 60, cy - 55, cx - 50, cy - 45], fill=BLACK)
        d.ellipse([cx + 35, cy - 70, cx + 75, cy - 30], fill=WHITE, outline=BLACK, width=5)
        d.ellipse([cx + 50, cy - 55, cx + 60, cy - 45], fill=BLACK)
        d.ellipse([cx - 30, cy + 20, cx + 30, cy + 65], fill=(160, 30, 30, 255), outline=BLACK, width=6)
    else:
        d.ellipse([cx - 70, cy - 65, cx - 40, cy - 35], fill=BLACK)
        d.ellipse([cx + 40, cy - 65, cx + 70, cy - 35], fill=BLACK)
        d.arc([cx - 40, cy + 15, cx + 40, cy + 50], 0, 180, fill=BLACK, width=6)
        
    return img

def create_shiro(emotion="happy", w=500, h=500):
    """绘制小白（Shiro）：棉花糖卷毛小狗"""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    
    WHITE = (255, 255, 255, 255)
    BLACK = (20, 20, 20, 255)
    BLUE = (60, 140, 240, 255)
    
    cx, cy = w // 2, h // 2
    
    # 身体与耳朵（多个圆弧组合出棉花糖蓬松感）
    d.ellipse([cx - 140, cy - 110, cx + 140, cy + 110], fill=WHITE, outline=BLACK, width=7)
    # 两只耳朵
    d.ellipse([cx - 160, cy - 140, cx - 80, cy - 40], fill=WHITE, outline=BLACK, width=6)
    d.ellipse([cx + 80, cy - 140, cx + 160, cy - 40], fill=WHITE, outline=BLACK, width=6)
    # 蓝色项圈
    d.rounded_rectangle([cx - 80, cy + 85, cx + 80, cy + 115], radius=10, fill=BLUE, outline=BLACK, width=5)
    
    # 黑豆眼与黑鼻子
    d.ellipse([cx - 70, cy - 35, cx - 40, cy - 5], fill=BLACK)
    d.ellipse([cx + 40, cy - 35, cx + 70, cy - 5], fill=BLACK)
    d.ellipse([cx - 20, cy - 5, cx + 20, cy + 25], fill=BLACK)
    
    # 嘴巴
    d.arc([cx - 40, cy + 10, cx, cy + 50], 0, 180, fill=BLACK, width=6)
    d.arc([cx, cy + 10, cx + 40, cy + 50], 0, 180, fill=BLACK, width=6)
    
    return img

# ----------------- 道具绘制 -----------------

def create_prop(name, w=450, h=450):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = w // 2, h // 2
    BLACK = (20, 20, 20, 255)
    
    if name == "巧克比":
        # 绿色六角盒巧克比粉红鳄鱼饼干盒
        GREEN = (60, 185, 100, 255)
        PINK = (255, 130, 170, 255)
        d.polygon([(cx - 110, cy - 140), (cx + 110, cy - 140), (cx + 160, cy), (cx + 110, cy + 140), (cx - 110, cy + 140), (cx - 160, cy)], fill=GREEN, outline=BLACK, width=7)
        # 粉红小恐龙鳄鱼剪影
        d.ellipse([cx - 65, cy - 60, cx + 65, cy + 40], fill=PINK, outline=BLACK, width=5)
        d.text((cx, cy + 85), "CHOCOBI", font=get_font(28, bold=True), fill=(255, 255, 255, 255), anchor="mm")
    elif name == "第二件半价牌":
        # 鲜红爆炸贴纸
        RED = (240, 50, 60, 255)
        YELLOW = (255, 220, 0, 255)
        d.ellipse([cx - 160, cy - 160, cx + 160, cy + 160], fill=RED, outline=YELLOW, width=8)
        d.text((cx, cy - 45), "第 2 件", font=get_font(42, bold=True), fill=(255, 255, 255, 255), anchor="mm")
        d.text((cx, cy + 40), "半 价", font=get_font(60, bold=True), fill=YELLOW, anchor="mm")
    elif name == "工资条":
        WHITE = (255, 255, 255, 255)
        BLUE = (70, 130, 180, 255)
        d.rounded_rectangle([cx - 140, cy - 180, cx + 140, cy + 180], radius=15, fill=WHITE, outline=BLACK, width=6)
        d.rectangle([cx - 140, cy - 180, cx + 140, cy - 110], fill=BLUE)
        d.text((cx, cy - 145), "双叶商事 · 工资单", font=get_font(26, bold=True), fill=WHITE, anchor="mm")
        d.text((cx - 100, cy - 60), "基本薪资: ¥15,000", font=get_font(22), fill=(50, 50, 50, 255))
        d.text((cx - 100, cy - 10), "五险一金: -¥3,300", font=get_font(22), fill=(200, 40, 40, 255))
        d.text((cx - 100, cy + 40), "个人所得税: -¥450", font=get_font(22), fill=(200, 40, 40, 255))
        d.line([(cx - 120, cy + 85), (cx + 120, cy + 85)], fill=BLACK, width=3)
        d.text((cx, cy + 130), "实发: ¥11,250", font=get_font(30, bold=True), fill=(20, 130, 50, 255), anchor="mm")
    else: # 默认钱袋/金币
        GOLD = (255, 200, 40, 255)
        d.ellipse([cx - 140, cy - 100, cx + 140, cy + 150], fill=GOLD, outline=BLACK, width=7)
        d.polygon([(cx - 90, cy - 100), (cx + 90, cy - 100), (cx + 45, cy - 160), (cx - 45, cy - 160)], fill=(230, 170, 30, 255), outline=BLACK, width=6)
        d.text((cx, cy + 20), "¥", font=get_font(90, bold=True), fill=(180, 110, 10, 255), anchor="mm")
    return img

# ----------------- 背景绘制 -----------------

def create_background(name, w=1080, h=1920):
    img = Image.new("RGB", (w, h), (255, 253, 240))
    d = ImageDraw.Draw(img)
    
    if name == "野原家客厅":
        # 暖黄/木质榻榻米色调
        d.rectangle([0, 0, w, h * 0.65], fill=(255, 248, 220)) # 墙面
        d.rectangle([0, h * 0.65, w, h], fill=(225, 205, 160)) # 榻榻米地面
        # 门框线条
        d.line([(0, h * 0.65), (w, h * 0.65)], fill=(120, 80, 50), width=10)
        d.rectangle([100, 250, 450, 800], fill=(240, 235, 210), outline=(130, 90, 60), width=8) # 日式推拉窗
        d.line([(275, 250), (275, 800)], fill=(130, 90, 60), width=6)
    elif name == "春日部超市":
        # 明亮超市货架
        d.rectangle([0, 0, w, h * 0.55], fill=(230, 245, 255))
        d.rectangle([0, h * 0.55, w, h], fill=(240, 240, 245))
        d.line([(0, h * 0.55), (w, h * 0.55)], fill=(100, 150, 200), width=8)
        # 货架与打折标语
        d.rectangle([60, 200, w - 60, 750], fill=(255, 255, 255), outline=(70, 120, 180), width=8)
        d.rectangle([120, 240, w - 120, 360], fill=(255, 70, 80))
        d.text((w // 2, 300), "KASUKABE SUPERMARKET 特卖场", font=get_font(38, bold=True), fill=(255, 255, 255), anchor="mm")
    elif name == "双叶商事办公室":
        d.rectangle([0, 0, w, h * 0.6], fill=(235, 240, 245))
        d.rectangle([0, h * 0.6, w, h], fill=(180, 190, 200))
        d.line([(0, h * 0.6), (w, h * 0.6)], fill=(100, 110, 120), width=8)
        d.rectangle([150, 200, w - 150, 650], fill=(210, 230, 250), outline=(80, 100, 130), width=8)
    else:
        # 春日部小镇街道
        d.rectangle([0, 0, w, h * 0.6], fill=(195, 230, 255)) # 蓝天
        d.rectangle([0, h * 0.6, w, h], fill=(210, 215, 200)) # 街道
        d.line([(0, h * 0.6), (w, h * 0.6)], fill=(120, 130, 120), width=8)
        # 远景小房子剪影
        d.polygon([(100, h * 0.6), (250, h * 0.45), (400, h * 0.6)], fill=(255, 180, 150), outline=(80, 80, 80), width=5)
        d.polygon([(500, h * 0.6), (680, h * 0.48), (860, h * 0.6)], fill=(160, 200, 240), outline=(80, 80, 80), width=5)

    return img

def main():
    print("=== 开始生成 2.0 野原经济学（蜡笔小新 IP）全套核心素材 ===")
    
    # 1. 角色生成
    shinchan_emotions = ["smile", "thinking", "explaining", "smug", "shocked", "confused"]
    for emo in shinchan_emotions:
        im = create_shinchan(emo)
        p = CHARS_DIR / f"char_小新_{emo}.png"
        im.save(p)
        print(f"✓ 角色: {p.name}")
        
    misae_emotions = ["shopping", "angry", "shocked", "calculating", "smile", "crying"]
    for emo in misae_emotions:
        im = create_misae(emo)
        p = CHARS_DIR / f"char_美伢_{emo}.png"
        im.save(p)
        print(f"✓ 角色: {p.name}")
        
    hiroshi_emotions = ["tired", "shocked", "thinking", "smile", "crying"]
    for emo in hiroshi_emotions:
        im = create_hiroshi(emo)
        p = CHARS_DIR / f"char_广志_{emo}.png"
        im.save(p)
        print(f"✓ 角色: {p.name}")
        
    shiro_emotions = ["happy", "wondering", "rolling"]
    for emo in shiro_emotions:
        im = create_shiro(emo)
        p = CHARS_DIR / f"char_小白_{emo}.png"
        im.save(p)
        print(f"✓ 角色: {p.name}")

    # 2. 道具生成
    props = ["巧克比", "第二件半价牌", "工资条", "钱袋"]
    for prop in props:
        im = create_prop(prop)
        p = PROPS_DIR / f"prop_{prop}.png"
        im.save(p)
        print(f"✓ 道具: {p.name}")

    # 3. 背景生成
    bgs = [("野原家客厅", "bg_nohara_living"), ("春日部超市", "bg_kasukabe_market"), 
           ("双叶商事办公室", "bg_office_desk"), ("春日部街道", "bg_kasukabe_street")]
    for name, filename in bgs:
        im = create_background(name)
        p = BGS_DIR / f"{filename}.png"
        im.save(p)
        print(f"✓ 背景: {p.name}")

    # 4. 更新 material-library.json
    lib_path = SHARED / "material-library.json"
    data = {}
    if lib_path.exists():
        try:
            data = json.loads(lib_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
            
    data["version"] = "2.0.0"
    data["lastUpdated"] = "2026-08-27"
    
    # 整合 characters
    chars_list = data.get("characters", [])
    # 移除已有的重复项
    chars_list = [c for c in chars_list if c.get("name") not in ["小新", "美伢", "广志", "小白"]]
    
    for emo in shinchan_emotions:
        chars_list.append({
            "id": f"char_小新_{emo}",
            "type": "character",
            "name": "小新",
            "emotion": emo,
            "action": "standing",
            "filePath": f"shared/characters/char_小新_{emo}.png",
            "status": "active",
            "contentDescription": f"野原新之助（小新），红衣黄裤，{emo}表情",
            "tags": ["角色", "小新", "野原经济学", emo]
        })
    for emo in misae_emotions:
        chars_list.append({
            "id": f"char_美伢_{emo}",
            "type": "character",
            "name": "美伢",
            "emotion": emo,
            "action": "standing",
            "filePath": f"shared/characters/char_美伢_{emo}.png",
            "status": "active",
            "contentDescription": f"野原美伢，主妇造型，{emo}表情",
            "tags": ["角色", "美伢", "野原经济学", emo]
        })
    for emo in hiroshi_emotions:
        chars_list.append({
            "id": f"char_广志_{emo}",
            "type": "character",
            "name": "广志",
            "emotion": emo,
            "action": "standing",
            "filePath": f"shared/characters/char_广志_{emo}.png",
            "status": "active",
            "contentDescription": f"野原广志，西装社职员，{emo}表情",
            "tags": ["角色", "广志", "野原经济学", emo]
        })
    for emo in shiro_emotions:
        chars_list.append({
            "id": f"char_小白_{emo}",
            "type": "character",
            "name": "小白",
            "emotion": emo,
            "action": "standing",
            "filePath": f"shared/characters/char_小白_{emo}.png",
            "status": "active",
            "contentDescription": f"野原小白，白色棉花糖小狗，{emo}表情",
            "tags": ["角色", "小白", "野原经济学", emo]
        })
    data["characters"] = chars_list

    # 整合 backgrounds
    bgs_list = data.get("backgrounds", [])
    bgs_list = [b for b in bgs_list if b.get("name") not in ["野原家客厅", "春日部超市", "双叶商事办公室", "春日部街道"]]
    for name, filename in bgs:
        bgs_list.append({
            "id": filename,
            "type": "background",
            "name": name,
            "filePath": f"shared/backgrounds/{filename}.png",
            "status": "active",
            "contentDescription": f"蜡笔小新经典场景：{name}",
            "tags": ["背景", "蜡笔小新", name]
        })
    data["backgrounds"] = bgs_list

    # 整合 props
    props_list = data.get("props", [])
    props_list = [p for p in props_list if p.get("name") not in ["巧克比", "第二件半价牌", "工资条", "钱袋"]]
    for prop in props:
        props_list.append({
            "id": f"prop_{prop}",
            "type": "prop",
            "name": prop,
            "filePath": f"shared/props/prop_{prop}.png",
            "status": "active",
            "contentDescription": f"蜡笔小新经济学道具：{prop}",
            "tags": ["道具", prop]
        })
    data["props"] = props_list

    lib_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[ok] 素材库索引已更新为 2.0 版本: {lib_path.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
