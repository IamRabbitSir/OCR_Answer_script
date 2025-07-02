import tkinter as tk
from PIL import ImageGrab

class ScreenCapture:
    def __init__(self, prompt):
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
        self.root.bind('<Escape>', self.on_esc_press)
        self.capture_box = None
        self.prompt = prompt
        self.label = tk.Label(self.root, text=prompt, font=("微软雅黑", 24), fg="red", bg="yellow")
        self.label.pack(side=tk.TOP, fill=tk.X)

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
        self.root.destroy()

    def on_esc_press(self, event):
        self.capture_box = None
        self.root.quit()
        self.root.destroy()

    def get_capture_box(self):
        self.root.mainloop()
        return self.capture_box

if __name__ == '__main__':
    region_names = ["标题", "选项A", "选项B", "选项C", "选项D"]
    regions = []
    print("请依次框选5个区域：标题、A、B、C、D。按ESC可随时退出。")
    for name in region_names:
        print(f"请用鼠标框选【{name}】区域，选完后松开鼠标...")
        cap = ScreenCapture(f"请框选：{name}")
        box = cap.get_capture_box()
        if not box:
            print(f"已取消{name}区域选择，程序退出。")
            exit(0)
        print(f"{name}区域坐标: {box}")
        regions.append(box)
    print("\n所有区域已选定，参数如下：")
    for i, name in enumerate(region_names):
        print(f"{name}区域: {regions[i]}")
    print("\n请复制以上5组坐标参数，发给AI助手！") 