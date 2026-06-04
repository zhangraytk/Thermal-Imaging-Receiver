import csv
import time
from pathlib import Path

SCALE = 20
ORIG_SURF = None
PIX_ARRAY = None


def get_pygame():
    import pygame
    return pygame


def get_pixel_array():
    global ORIG_SURF, PIX_ARRAY
    if PIX_ARRAY is None:
        pygame = get_pygame()
        ORIG_SURF = pygame.Surface((32, 24))
        PIX_ARRAY = pygame.PixelArray(ORIG_SURF)
    return PIX_ARRAY

def get_colour(value):
    R_colour, G_colour, B_colour = 0, 0, 0
    if 0 <= value < 30:
        R_colour = 0
        G_colour = 0
        B_colour = 20 + (120.0/30.0) * value
    elif 30 <= value < 60:
        R_colour = (120.0 / 30) * (value - 30.0)
        G_colour = 0
        B_colour = 140 - (60.0/30.0) * (value - 30.0)
    elif 60 <= value < 90:
        R_colour = 120 + (135.0/30.0) * (value - 60.0)
        G_colour = 0
        B_colour = 80 - (70.0/30.0) * (value - 60.0)
    elif 90 <= value < 120:
        R_colour = 255
        G_colour = 0 + (60.0/30.0) * (value - 90.0)
        B_colour = 10 - (10.0/30.0) * (value - 90.0)
    elif 120 <= value < 150:
        R_colour = 255
        G_colour = 60 + (175.0/30.0) * (value - 120.0)
        B_colour = 0
    elif 150 <= value <= 180:
        R_colour = 255
        G_colour = 235 + (20.0/30.0) * (value - 150.0)
        B_colour = 0 + 255.0/30.0 * (value - 150.0)
    return R_colour, G_colour, B_colour



def bio_linear_interpolation(dst_x:int, dst_y:int, src_data:list):
    """双线性插值"""  
    def getValue(y, x, _src_data):
        return _src_data[x + (23 - y) * 32]

    src_x = (dst_x*10000 + 5000) // SCALE - 5000
    src_y = (dst_y*10000 + 5000) // SCALE - 5000

    # 找到四个最近邻点的位置
    src_x0 = src_x // 10000
    src_y0 = src_y // 10000
    src_x1 = src_x0+1
    src_y1 = src_y0+1

    # 确保不超出源图像边界
    src_x0 = max(src_x0, 0)
    src_y0 = max(src_y0, 0)
    src_x1 = min(src_x1, 31)
    src_y1 = min(src_y1, 23)

    # 计算分数部分
    frac_x = src_x - src_x0 * 10000
    frac_y = src_y - src_y0 * 10000

    # 获取四个最近邻点的值
    value00 = getValue(src_y0, src_x0, src_data)
    value01 = getValue(src_y0, src_x1, src_data)
    value10 = getValue(src_y1, src_x0, src_data)
    value11 = getValue(src_y1, src_x1, src_data)
    # 沿x轴的线性插值
    v0 = value00 * (10000 - frac_x) + value01 * frac_x
    v1 = value10 * (10000 - frac_x) + value11 * frac_x

    v0 = v0 // 10000
    v1 = v1 // 10000
    # 沿y轴的线性插值
    return (v0 * (10000 - frac_y) + v1 * frac_y) / 10000


def draw_heatmap(matrix, draw_func):
    max_t, min_t, avg_t = matrix[:3]
    max_t += 0.1
    for k, temp in enumerate(matrix[3::]):
        value = 180.0 * (temp - min_t) / (max_t - min_t)
        r, g, b = get_colour(value)
        draw_func(k, (r, g, b))


def draw_heatmap_upsample(matrix):
    pix_array = get_pixel_array()
    max_t, min_t, avg_t = matrix[:3]
    max_t += 0.1
    for k, temp in enumerate(matrix[3::]):
        value = 180.0 * (temp - min_t) / (max_t - min_t)
        r, g, b = get_colour(value)
        x = k % 32
        y = k // 32
        pix_array[x, 23-y] = (r, g, b)
    pygame = get_pygame()
    return pygame.transform.smoothscale(pix_array.make_surface(), (32*SCALE, 24*SCALE))


def save_frame(matrix:list, surf, output_dir=None):
    pygame = get_pygame()
    output_dir = Path(output_dir) if output_dir else Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%m-%d-%H-%M-%S")
    csv_path = output_dir / f"{timestamp}.csv"
    image_path = output_dir / f"{timestamp}.png"
    lines = []
    line = []
    for k, data in enumerate(matrix[3::]):
        if k  %  32 != 0:
            line.append(data)
        elif len(line) > 0:
            lines.insert(0, line)
            line = []
            line.append(data)
        else:
            line.append(data)
    lines.insert(0, line)
    with csv_path.open('w', encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([""] + list(range(len(lines[0]))))
        for k, line in enumerate(lines):
            writer.writerow([k] + line)
    
    cap_rect = pygame.Rect(0, 50, 20*32, 20*24)
    screen_cap = surf.subsurface(cap_rect)
    pygame.image.save(screen_cap, image_path)
    return csv_path, image_path

def save_curv(times:list, points_bytime:list, output_dir=None):
    if not times or not points_bytime:
        return None

    output_dir = Path(output_dir) if output_dir else Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f'curv_{time.strftime("%m-%d-%H-%M-%S")}.csv'
    with csv_path.open('w', encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        header = ["time(s)", "max"]
        header.extend(f"point_{i}" for i in range(len(points_bytime[0]) - 1))
        writer.writerow(header)
        for t, time_stamps in enumerate(points_bytime):
            writer.writerow([f"{times[t]:.3f}"] + time_stamps)
    return csv_path
