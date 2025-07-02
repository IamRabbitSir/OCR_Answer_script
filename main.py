# 使用 Tesseract OCR 进行文字识别
import pytesseract

import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageGrab, ImageEnhance, ImageFilter
import pyautogui
import threading
import time
import re
import dashscope
from dashscope import Generation
import keyboard

# 设置阿里云API Key
dashscope.api_key = "XXXXXXXXXXXXXXXXXXXXX"

# 设置Tesseract路径（请根据您的安装路径修改）
pytesseract.pytesseract.tesseract_cmd = r'D:\software\tesseract\tesseract.exe'

class ScreenCapture:
    def __init__(self):
        self.start_x = 0
        self.start_y = 0
        self.end_x = 0
        self.end_y = 0
        self.rect = None
        self.root = tk.Tk()
        self.root.attributes('-alpha', 0.3)
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.config(cursor="cross")
        self.canvas = tk.Canvas(self.root, cursor="cross", bg='grey')
        self.canvas.pack(fill=tk.BOTH, expand=tk.YES)
        self.canvas.bind('<Button-1>', self.on_mouse_down)
        self.canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_up)
        self.root.bind('<Escape>', self.on_esc_press)  # 新增ESC退出
        self.capture_box = None

    def on_mouse_down(self, event):
        self.start_x = float(self.canvas.canvasx(event.x))
        self.start_y = float(self.canvas.canvasy(event.y))
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=2)

    def on_mouse_drag(self, event):
        cur_x = float(self.canvas.canvasx(event.x))
        cur_y = float(self.canvas.canvasy(event.y))
        if self.rect is not None:
            self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_mouse_up(self, event):
        self.end_x = float(self.canvas.canvasx(event.x))
        self.end_y = float(self.canvas.canvasy(event.y))
        self.capture_box = (
            int(min(self.start_x, self.end_x)),
            int(min(self.start_y, self.end_y)),
            int(max(self.start_x, self.end_x)),
            int(max(self.start_y, self.end_y))
        )
        self.root.quit()
        self.root.destroy()  # 确保窗口销毁

    def on_esc_press(self, event):
        self.capture_box = None
        self.root.quit()
        self.root.destroy()

    def get_capture_box(self):
        self.root.mainloop()
        return self.capture_box


def preprocess_image(img, for_option=False):
    """图像预处理，适应小区域，提高OCR识别率。for_option=True时用于选项区域。"""
    if img.mode != 'RGB':
        img = img.convert('RGB')
    width, height = img.size
    img = img.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
    img = img.convert('L')
    if for_option:
        # 选项区域参数更温和
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.3)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.0)
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.2)
        # 二值化
        img = img.point(lambda x: 0 if x < 180 else 255, '1')
    else:
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.1)
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.5)
        img = img.filter(ImageFilter.MedianFilter(size=3))
    return img


def extract_qa_structure(text):
    """提取问题和选项结构"""
    # print(f"🔍 开始提取QA结构...")
    
    # 简单分割文本行
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    # print(f"🔍 分割后行数: {len(lines)}")
    # print(f"🔍 分割后内容: {lines}")
    
    if len(lines) < 2:
        # print(f"❌ 文本行数不足，无法提取QA结构")
        return "", []
    
    # 查找问题结束位置
    question_end = -1
    for i, line in enumerate(lines):
        # 检查是否包含问题结束标记
        if any(marker in line for marker in ['？', '?', '：', ':', '》', '。']):
            question_end = i
            # print(f"🔍 在第{i+1}行找到问题结束标记: '{line}'")
            break
    
    # 如果没有找到明确的结束标记，使用默认分割
    if question_end == -1:
        if len(lines) >= 3:
            question_end = 1  # 前2行作为问题
            # print(f"🔍 未找到结束标记，使用默认分割：前2行作为问题")
        else:
            question_end = 0  # 第1行作为问题
            # print(f"🔍 未找到结束标记，使用默认分割：第1行作为问题")
    
    # 提取问题
    question_lines = lines[:question_end + 1]
    question = " ".join(question_lines)
    # print(f"🔍 提取的问题: '{question}'")
    
    # 提取选项
    option_lines = lines[question_end + 1:]
    # print(f"🔍 原始选项行: {option_lines}")
    
    # 清理和验证选项
    cleaned_options = []
    for i, opt in enumerate(option_lines):
        opt = opt.strip()
        if opt and len(opt) > 1:  # 排除空行和太短的内容
            cleaned_options.append(opt)
            # print(f"🔍 选项{i+1}: '{opt}'")
    
    # 只取前4个选项
    options = cleaned_options[:4]
    # print(f"🔍 最终选项数量: {len(options)}")
    
    return question, options


def format_qa_for_ai(question, options):
    """将问题和选项格式化为AI输入格式"""
    formatted_text = f"问题：{question}\n"
    for i, option in enumerate(options):
        formatted_text += f"{chr(65+i)}. {option}\n"
    return formatted_text


def extract_answer_only(ai_text, options=None):
    """从AI响应中提取答案部分，并加上选项文字"""
    # 查找答案模式
    import re
    
    # 匹配 "答案：X" 或 "答案: X" 格式
    answer_pattern = re.compile(r'答案[：:]\s*([A-D])', re.IGNORECASE)
    match = answer_pattern.search(ai_text)
    
    if match:
        answer = match.group(1).upper()
        if options and len(options) >= ord(answer) - ord('A') + 1:
            option_text = options[ord(answer) - ord('A')]
            return f"答案：{answer}. {option_text}"
        else:
            return f"答案：{answer}"
    
    # 如果没有找到标准格式，尝试提取单个字母
    letter_pattern = re.compile(r'\b([A-D])\b', re.IGNORECASE)
    match = letter_pattern.search(ai_text)
    
    if match:
        answer = match.group(1).upper()
        if options and len(options) >= ord(answer) - ord('A') + 1:
            option_text = options[ord(answer) - ord('A')]
            return f"答案：{answer}. {option_text}"
        else:
            return f"答案：{answer}"
    
    # 如果都没找到，返回原始文本的前50个字符
    return ai_text[:50] + "..." if len(ai_text) > 50 else ai_text


def analyze_confidence(question, options):
    """分析问题的复杂度和AI回答的置信度"""
    # 简单的置信度分析
    confidence_factors = []
    
    # 检查问题长度
    if len(question) > 50:
        confidence_factors.append("问题较长，可能存在复杂逻辑")
    
    # 检查选项相似度
    option_lengths = [len(opt) for opt in options]
    if max(option_lengths) - min(option_lengths) > 20:
        confidence_factors.append("选项长度差异较大")
    
    # 检查是否包含专业术语
    professional_terms = ['经济', '政治', '历史', '科学', '技术', '法律', '医学']
    if any(term in question for term in professional_terms):
        confidence_factors.append("包含专业术语")
    
    # 根据因素数量判断置信度
    if len(confidence_factors) == 0:
        return "高", "问题相对简单，AI回答可信度较高"
    elif len(confidence_factors) == 1:
        return "中", f"注意：{confidence_factors[0]}"
    else:
        return "低", f"注意：问题较复杂，建议人工验证。因素：{', '.join(confidence_factors)}"


def ask_ai_for_answer(question, options):
    """调用阿里云百联模型获取AI推荐答案"""
    try:
        # 格式化输入
        formatted_qa = format_qa_for_ai(question, options)
        
        # 构建提示词 - 增强准确性
        prompt = f"""请仔细分析以下问题和选项，选择最准确的答案：\n\n{formatted_qa}\n\n请基于以下原则选择答案：
1. 仔细理解问题的核心含义
2. 分析每个选项的准确性
3. 选择最符合题目要求的选项
4. 如果不确定，请选择最合理的选项

请直接给出最优选项的字母（A、B、C或D），不要包含理由说明。格式如下：\n答案：X\n\n请确保答案准确。"""

        # 调用阿里云百联模型
        response = Generation.call(
            model='qwen-turbo',  # 使用通义千问模型
            prompt=prompt,
            max_tokens=500,
            temperature=0.3,
            top_p=0.8
        )
        
        # 解析响应 - 使用JSON方式提取text内容
        response_str = str(response)
        import json
        try:
            response_dict = json.loads(response_str)
            if 'output' in response_dict and 'text' in response_dict['output']:
                ai_text = response_dict['output']['text'].strip()
                # 提取答案部分，并加上选项文字
                return extract_answer_only(ai_text, options)
        except json.JSONDecodeError:
            pass
        
        # 如果JSON解析失败，直接返回字符串
        return f"无法解析AI响应: {response_str[:100]}..."
        
    except Exception as e:
        return f"AI调用异常: {str(e)}"


def ocr_loop(box, interval=1.0):
    print(f"已选定区域：{box}，开始实时识别...")
    print("💡 提示：按 Z 键立即重新识别当前区域")
    print("💡 提示：按 X 键暂停/恢复识别")
    print("💡 提示：按 Ctrl+C 退出程序")
    
    last_text = None
    last_qa = None
    last_question = None  # 添加上次问题记录
    force_retry = False
    is_paused = False  # 添加暂停状态标志
    
    # 注册热键
    def on_z_press():
        nonlocal force_retry
        force_retry = True
        if is_paused:
            print("\n🔄 手动触发重新识别（暂停状态下）...")
        else:
            print("\n🔄 手动触发重新识别...")
        # 手动触发时重置问题记录，确保能重新显示
        nonlocal last_question
        last_question = None
    
    def on_x_press():
        nonlocal is_paused
        is_paused = not is_paused
        if is_paused:
            print("\n⏸️  识别已暂停，按 X 键恢复识别，或按 Z 键手动识别")
        else:
            print("\n▶️  识别已恢复")
    
    keyboard.on_press_key('z', lambda _: on_z_press())
    keyboard.on_press_key('x', lambda _: on_x_press())
    
    try:
        while True:
            # 检查是否暂停（但允许手动触发识别）
            if is_paused and not force_retry:
                time.sleep(0.1)  # 暂停时减少CPU使用
                continue
            
            # 截图
            img = ImageGrab.grab(bbox=box)
            
            # 图像预处理
            processed_img = preprocess_image(img)
            
            # 用Tesseract识别
            text = ""
            try:
                # 保存预处理后的图片用于调试
                processed_img.save('debug_processed.png')
                
                # 使用单一OCR配置，减少调试输出
                try:
                    text = pytesseract.image_to_string(processed_img, lang='chi_sim', config='--psm 6')
                    text = text.strip()
                    
                    if text and len(text) > 2:
                        print(f"✅ OCR识别成功")
                    else:
                        print("❌ OCR识别结果为空或过短")
                        
                except Exception as e:
                    print(f"❌ OCR识别异常: {e}")
                    text = ""
                
                if not text or len(text) <= 2:
                    print("⚠️  OCR识别失败")
                    
            except Exception as e:
                print(f"OCR识别异常: {e}")
                text = ""
            
            # 检查是否需要重新识别（文本变化或手动触发）
            if (text and text != last_text) or force_retry:
                if force_retry:
                    force_retry = False
                    print("\n--- 手动重新识别结果 ---")
                else:
                    print("\n--- OCR识别结果 ---")
                print(text)
                print("------------------")
                
                # 提取问题和选项结构
                # print(f"\n🔍 原始文本分析:")
                # print(f"原始文本行数: {len(text.split(chr(10)))}")
                # print(f"原始文本: {repr(text)}")
                
                question, options = extract_qa_structure(text)
                
                # 检查是否是新问题
                is_new_question = question != last_question
                
                if is_new_question or force_retry:
                    print(f"\n🔍 提取结果:")
                    print(f"提取到的问题: '{question}'")
                    print(f"提取到的选项数量: {len(options)}")
                    print(f"选项内容:")
                    for i, opt in enumerate(options):
                        print(f"  选项{i+1}: '{opt}'")
                else:
                    print(f"\n⏭️  问题相同，跳过输出: '{question[:30]}...'")
                
                # 识别到问题+2个以上选项就调用AI
                if question and len(options) >= 2:
                    # 只有新问题或手动触发时才显示详细信息和调用AI
                    if is_new_question or force_retry:
                        print(f"\n问题: {question}")
                        print("选项:")
                        for i, opt in enumerate(options):
                            print(f"  {chr(65+i)}. {opt}")
                        
                        # 显示选项完整性提示
                        if len(options) < 4:
                            print(f"⚠️  选项不完整（{len(options)}/4），但仍进行AI分析")
                        
                        # 分析置信度
                        confidence_level, confidence_msg = analyze_confidence(question, options)
                        
                        # 调用AI分析
                        print("\n🤖 AI分析中...")
                        ai_response = ask_ai_for_answer(question, options)
                        print(f"\n🎯 AI推荐答案:")
                        print(ai_response)
                        print(f"\n📊 置信度评估: {confidence_level}")
                        print(f"💡 {confidence_msg}")
                        print("=" * 50)
                        
                        last_qa = (question, options)
                    else:
                        print(f"⏭️  AI分析已跳过（相同问题）")
                else:
                    if is_new_question or force_retry:
                        print("⚠️  无法识别完整的问题和选项结构，跳过AI分析")
                        print(f"问题为空: {not question}")
                        print(f"选项不足: {len(options) < 2}")
                
                # 更新记录
                last_text = text
                if question:  # 只有在成功提取到问题时才更新
                    last_question = question
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n主程序已退出。")
    finally:
        # 清理热键监听
        keyboard.unhook_all()


def realtime_ocr(interval=1.0):
    cap = ScreenCapture()
    box = cap.get_capture_box()
    if not box:
        print("未选定区域，程序退出。"); return
    # 启动新线程做OCR
    t = threading.Thread(target=ocr_loop, args=(box, interval), daemon=True)
    t.start()
    # 主线程保持运行，等待Ctrl+C退出
    try:
        while t.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n主程序已退出。")


def ocr_single(img, for_option=False, debug_save_path=None):
    """使用Tesseract识别图片，返回文本。可指定是否为选项区域，并保存预处理后图片。"""
    processed_img = preprocess_image(img, for_option=for_option)
    if debug_save_path:
        processed_img.save(debug_save_path)
    # 选项区域优先用psm 7
    config = '--psm 7' if for_option else '--psm 6'
    try:
        text = pytesseract.image_to_string(processed_img, lang='chi_sim', config=config)
        text = text.strip()
        if not text and for_option:
            # 选项区域识别失败时再用psm 6试一次
            text = pytesseract.image_to_string(processed_img, lang='chi_sim', config='--psm 6').strip()
        return text
    except Exception as e:
        print(f"OCR识别异常: {e}")
        return ""


def test_tesseract():
    """测试Tesseract OCR功能"""
    print("🧪 测试Tesseract OCR功能...")
    
    # 检查Tesseract版本
    try:
        version = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract版本: {version}")
    except Exception as e:
        print(f"❌ 无法获取Tesseract版本: {e}")
        return False
    
    # 检查语言包
    try:
        langs = pytesseract.get_languages()
        print(f"✅ 可用语言包: {langs}")
        if 'chi_sim' not in langs:
            print("❌ 缺少中文简体语言包 (chi_sim)")
            return False
    except Exception as e:
        print(f"❌ 无法获取语言包列表: {e}")
        return False
    
    # 测试简单识别
    try:
        # 创建一个简单的测试图片
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGB', (200, 50), color='white')
        draw = ImageDraw.Draw(img)
        # 尝试绘制中文文字（如果有字体的话）
        try:
            # 尝试使用系统字体
            font = ImageFont.truetype("simhei.ttf", 20)
            draw.text((10, 10), "测试", fill='black', font=font)
        except:
            # 如果没有中文字体，使用默认字体
            draw.text((10, 10), "Test", fill='black')
        
        text = pytesseract.image_to_string(img, lang='chi_sim', config='--psm 6')
        print(f"✅ 测试识别结果: '{text.strip()}'")
        return True
    except Exception as e:
        print(f"❌ 测试识别失败: {e}")
        return False


def select_5_regions():
    regions = []
    region_names = ["标题", "选项A", "选项B", "选项C", "选项D"]
    for name in region_names:
        print(f"请用鼠标框选【{name}】区域，选完后松开鼠标...")
        cap = ScreenCapture()
        box = cap.get_capture_box()
        if not box:
            print(f"已取消{name}区域选择，程序安全退出。")
            return None
        regions.append(box)
    print("5个区域已全部选定！")
    return regions


class AnswerPopup:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI推荐答案")
        self.root.attributes('-topmost', True)
        self.root.geometry("350x110+100+100")
        self.root.resizable(False, False)
        # 快捷键说明
        self.tips = tk.Label(self.root, text="快捷键：Z=手动识别  X=暂停/恢复  Ctrl+C=退出", font=("微软雅黑", 10), fg="gray")
        self.tips.pack(side=tk.TOP, fill=tk.X, pady=(5,0))
        self.label = tk.Label(self.root, text="", font=("微软雅黑", 18), fg="green")
        self.label.pack(expand=True, fill=tk.BOTH)
        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        self.root.withdraw()  # 初始隐藏
        self.visible = False
    def show_answer(self, answer_text):
        self.label.config(text=answer_text)
        if not self.visible:
            self.root.deiconify()
            self.visible = True
        self.root.update()
    def hide(self):
        self.root.withdraw()
        self.visible = False
    def destroy(self):
        self.root.destroy()


def auto_click_option(ai_response, regions):
    match = re.search(r'答案[：: ]*([A-D])', ai_response)
    if not match:
        return
    answer = match.group(1).upper()
    idx = ord(answer) - ord('A') + 1
    if idx < 1 or idx > 4:
        return
    left, top, right, bottom = regions[idx]
    x = (left + right) // 2
    y = (top + bottom) // 2
    pyautogui.moveTo(x, y, duration=0.1)
    pyautogui.click()


def ocr_loop_structured(regions, interval=1.0):
    print(f"已选定5个区域，开始实时识别...")
    print("💡 提示：按 Z 键立即重新识别所有区域")
    print("💡 提示：按 X 键暂停/恢复识别")
    print("💡 提示：按 Ctrl+C 退出程序")
    
    last_question = None
    force_retry = False
    is_paused = False
    same_question_count = 0  # 新增：相同问题计数
    region_save_names = ["title.png", "a.png", "b.png", "c.png", "d.png"]
    region_proc_names = ["title_proc.png", "a_proc.png", "b_proc.png", "c_proc.png", "d_proc.png"]
    popup = AnswerPopup()
    
    def on_z_press():
        nonlocal force_retry
        force_retry = True
        print("\n🔄 手动触发重新识别...")
        nonlocal last_question
        last_question = None
    
    def on_x_press():
        nonlocal is_paused
        is_paused = not is_paused
        if is_paused:
            print("\n⏸️  识别已暂停，按 X 键恢复识别，或按 Z 键手动识别")
        else:
            print("\n▶️  识别已恢复")
    
    keyboard.on_press_key('z', lambda _: on_z_press())
    keyboard.on_press_key('x', lambda _: on_x_press())
    
    try:
        while True:
            if is_paused and not force_retry:
                time.sleep(0.1)
                continue
            
            # 依次识别5个区域，并保存原图和预处理图
            imgs = [ImageGrab.grab(bbox=box) for box in regions]
            for i, img in enumerate(imgs):
                img.save(region_save_names[i])
            texts = []
            for i, img in enumerate(imgs):
                is_option = (i > 0)
                text = ocr_single(img, for_option=is_option, debug_save_path=region_proc_names[i])
                if not text.strip():
                    print(f"⚠️  区域{region_save_names[i]}识别为空，请检查截图区域是否正确，或调试图片查看！")
                texts.append(text)
            title, optA, optB, optC, optD = [t.strip() for t in texts]
            
            # 结构化输出
            question = title
            options = [optA, optB, optC, optD]
            
            # 判断是否为新问题
            is_new_question = question != last_question
            if is_new_question or force_retry:
                same_question_count = 0
                print("\n--- 结构化OCR识别结果 ---")
                print(f"问题: {question}")
                print(f"A. {optA}")
                print(f"B. {optB}")
                print(f"C. {optC}")
                print(f"D. {optD}")
            else:
                same_question_count += 1
                print(f"\n⏭️  问题相同，跳过输出: '{question[:30]}...'（已连续{same_question_count}次）")
                if same_question_count == 5:
                    # 自动点击选项B和选项C
                    for idx in [2, 3]:  # 2=选项B, 3=选项C
                        left, top, right, bottom = regions[idx]
                        x = (left + right) // 2
                        y = (top + bottom) // 2
                        print(f"⚠️  连续5次相同问题，自动点击选项{chr(65+idx-1)}")
                        pyautogui.moveTo(x, y, duration=0.1)
                        pyautogui.click()
                        time.sleep(0.2)  # 两次点击间隔
                    same_question_count = 0
                    time.sleep(1)  # 新增：点击后延迟1秒再进行下一轮OCR
            
            # 只要有2个及以上选项就调用AI
            valid_options = [opt for opt in options if opt]
            if question and len(valid_options) >= 2:
                if is_new_question or force_retry:
                    # 分析置信度
                    confidence_level, confidence_msg = analyze_confidence(question, options)
                    print("\n🤖 AI分析中...")
                    ai_response = ask_ai_for_answer(question, options)
                    print(f"\n🎯 AI推荐答案:")
                    print(ai_response)
                    print(f"\n📊 置信度评估: {confidence_level}")
                    print(f"💡 {confidence_msg}")
                    print("=" * 50)
                    # 新增：弹窗显示答案
                    popup.show_answer(ai_response)
                    # 新增：自动点击选项
                    auto_click_option(ai_response, regions)
            else:
                if is_new_question or force_retry:
                    print("⚠️  无法识别完整的问题和选项结构，跳过AI分析")
                    print(f"问题为空: {not question}")
                    print(f"选项不足: {len(valid_options) < 2}")
            
            last_question = question
            force_retry = False
            try:
                popup.root.update()
            except Exception:
                pass
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n主程序已退出。")
    finally:
        keyboard.unhook_all()
        try:
            popup.destroy()
        except Exception:
            pass


def show_default_regions_and_confirm(default_regions):
    # 1. 显示全屏蒙版和5个高亮框
    root = tk.Tk()
    root.attributes('-alpha', 0.3)
    root.attributes('-fullscreen', True)
    root.attributes('-topmost', True)
    root.config(cursor="arrow")
    canvas = tk.Canvas(root, bg='grey')
    canvas.pack(fill=tk.BOTH, expand=tk.YES)
    colors = ['red', 'blue', 'green', 'orange', 'purple']
    region_names = ["标题", "选项A", "选项B", "选项C", "选项D"]
    for i, box in enumerate(default_regions):
        canvas.create_rectangle(box[0], box[1], box[2], box[3], outline=colors[i], width=4)
        canvas.create_text((box[0]+box[2])//2, box[1]-20, text=region_names[i], fill=colors[i], font=("微软雅黑", 18, "bold"))
    root.after(5000, root.destroy)  # 5秒后自动销毁
    root.mainloop()

    # 2. 弹出选择弹窗
    confirm = tk.Tk()
    confirm.title("区域选择")
    confirm.geometry("400x180+600+300")
    confirm.attributes('-topmost', True)
    label = tk.Label(confirm, text="是否使用默认区域？", font=("微软雅黑", 20), fg="black")
    label.pack(pady=20)
    result = [None]
    def use_default():
        result[0] = True
        confirm.destroy()
    def manual():
        result[0] = False
        confirm.destroy()
    def on_close():
        confirm.destroy()
        exit(0)
    confirm.protocol("WM_DELETE_WINDOW", on_close)
    btn1 = tk.Button(confirm, text="是（推荐）", font=("微软雅黑", 16), width=10, command=use_default)
    btn1.pack(side=tk.LEFT, padx=40, pady=20)
    btn2 = tk.Button(confirm, text="否，手动框选", font=("微软雅黑", 16), width=12, command=manual)
    btn2.pack(side=tk.RIGHT, padx=40, pady=20)
    confirm.mainloop()
    return result[0]


if __name__ == '__main__':
    if test_tesseract():
        print("\n🎉 Tesseract测试通过，开始主程序...")
        print("\n📋 快捷键说明：")
        print("  Z 键 - 立即重新识别所有区域（暂停时也可使用）")
        print("  X 键 - 暂停/恢复识别")
        print("  Ctrl+C - 退出程序")
        print("\n⚠️  重要提醒：")
        print("  AI回答仅供参考，请结合自己的知识判断答案的正确性")
        print("  对于重要考试或决策，建议进行人工验证")
        # 默认区域参数
        default_regions = [
            (121, 407, 466, 484),
            (158, 490, 428, 540),
            (161, 555, 422, 610),
            (161, 623, 421, 676),
            (160, 692, 423, 744)
        ]
        use_default = show_default_regions_and_confirm(default_regions)
        if use_default:
            regions = default_regions
            print("已选择默认区域！")
        else:
            print("请依次框选5个区域：标题、A、B、C、D")
            regions = select_5_regions()
            if regions is None:
                print("区域选择被取消，程序已安全退出。")
                exit(0)
        ocr_loop_structured(regions, interval=0.5)
    else:
        print("\n❌ Tesseract测试失败，请检查安装配置")
        print("💡 建议：")
        print("1. 确保Tesseract已正确安装")
        print("2. 确保中文语言包已安装")
        print("3. 检查路径配置是否正确") 