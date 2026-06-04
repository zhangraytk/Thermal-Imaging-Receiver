import csv
import os
from app_config import load_config

APP_CONFIG = load_config()
ROOT = None
LISTBOX = None


def get_pyplot():
    import matplotlib.pyplot as plt
    return plt

def load_csv_curv(path:str):
    with open(path, 'r', newline='') as f:
        rows = [row for row in csv.reader(f) if row]
    labels = [value for value in rows[0][1:] if value != ""]
    x = []
    y = []
    for row in rows[1:]:
        values = [value for value in row if value != ""]
        if not values:
            continue
        x.append(float(values[0]))
        y.append([float(point) for point in values[1:]])
    return x, y, labels

def load_csv_frame(path:str):
    with open(path, 'r', newline='') as f:
        rows = [row for row in csv.reader(f) if row]
    datas = []
    for row in rows[1:]:
        values = [value for value in row[1:] if value != ""]
        datas.append([float(point) for point in values])
    return datas[::-1]

def show_frame(_path):
    try:
        plt = get_pyplot()
        datas = load_csv_frame(_path)
        plt.figure("Tmeperature Frame")
        plt.xlim(0, len(datas[0])-1)
        plt.ylim(0, len(datas)-1)
        plt.imshow(datas, cmap='hot', interpolation='nearest')
        plt.show()
    except Exception as e:
        print(e)

def show_curve(_path):
    try:
        plt = get_pyplot()
        x, y, labels = load_csv_curv(_path)
        print(labels)
        plt.figure()
        plt.grid(True)
        plt.xlim(0, max(x))
        plt.xlabel('Time (s)')
        plt.ylabel('Temperature (°C)')
        plt.plot(x, y, label=labels)
        plt.legend()
        # print(y[-1])
        plt.show()
    except Exception as e:
        print(e)

def list_files():
    # 获取当前目录下的所有文件
    file_list = os.listdir()
    # 在listbox中显示文件列表
    LISTBOX.delete(0, tk.END)
    for file in file_list:
        if file.endswith('.csv'):
            LISTBOX.insert(tk.END, file)

def open_file(event):
    # 获取选中的文件名
    selected_file = LISTBOX.get(tk.ACTIVE)
    # 打开文件
    # print("打开文件：", selected_file)
    if selected_file.startswith('curv'):
        show_curve(selected_file)
    else:
        show_frame(selected_file)

def ask_directory():
    from tkinter import filedialog

    # 弹出对话框让用户选择目录
    directory = filedialog.askdirectory()
    # 如果用户选择了目录，更新文件列表
    if directory:
        os.chdir(directory)
        list_files()

def main():
    global ROOT, LISTBOX
    import tkinter as tk

    APP_CONFIG["data_dir"].mkdir(parents=True, exist_ok=True)

    ROOT = tk.Tk()
    ROOT.title("曲线浏览器")

    LISTBOX = tk.Listbox(ROOT, width=100, height=10)
    LISTBOX.pack()

    # 创建菜单栏
    menu_bar = tk.Menu(ROOT)
    ROOT.config(menu=menu_bar)

    # 创建文件菜单
    file_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="文件", menu=file_menu)

    # 添加选择目录选项
    file_menu.add_command(label="选择目录", command=ask_directory)

    os.chdir(APP_CONFIG["data_dir"])
    list_files()

    # 为listbox添加双击事件
    LISTBOX.bind("<Double-Button-1>", open_file)
    ROOT.mainloop()

if __name__ == '__main__':
    main()
