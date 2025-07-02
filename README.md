![733428e181c7e0bf86cde02c98e99311](https://github.com/user-attachments/assets/f05b0a90-663c-47e6-917a-2edc0d526816)
有一些答题微信小程序，总是答不过对方，辅助脚本。轻松拿捏对方！（其实脚本有时还答不过对方玩家）非百分之百，但几乎也有80%的正确率。
这是一个python脚本，运行后会有5秒的默认框选的案例（这是初始值），可以选否进行自定义框选，固定模式（5个框，分别是问题、选项A、选项B、选项C、选项D）
原理是通过OCR识别这5个框选的内容，识别文字，传给阿里云AI大模型进行判断，然后接受参数给予正确的选项进行辅助答题。

阿里云API Key自行配置（好像要费用，使用量不多也就几毛，充个10块够用了）
ORC我用的是开源的tesseract-ORC，优点免费快捷，缺点识别精度不高（目前识别的BUG有部分原因） 换别的反应会有点慢，答题时间有限
https://digi.bib.uni-mannheim.de/tesseract/        下载exe版本安装，安装的时候别全选全部语音，否则慢死你！！！！！

自行修改代码部分：
# 设置阿里云API Key
dashscope.api_key = "XXXXXXXXXXXXXXXX"

# 设置Tesseract路径（请根据您的安装路径修改）
pytesseract.pytesseract.tesseract_cmd = r'D:\software\tesseract\tesseract.exe'

然后就可以运行了
