import pygame
import pygame_gui
import serial
import serial.tools.list_ports
import sys
import threading
import queue
import time
from app_config import load_config
from frame_parser import FrameParseError, parse_frame_packet
from utils import *

pygame.init()
pygame.font.init()
pygame.mouse.set_visible(False)
FONT = pygame.font.Font(None, 25)  # 使用默认字体，大小为72
SERIAL = serial.Serial()
SERIAL.timeout = 2
FRAME_QUEUE = queue.Queue(2)
ERROR_QUEUE = queue.Queue(5)
IMG_BUFFER = None
REC = False
IDENTIFY_BUFFER = b""
ALIVE = True
SCALE = 20
REC_INTERVAL = 0.25
MAX_REC_TIME = 3600 * 5

DISPLAY_MODE = "SCALED"
SURF_IMG = pygame.Surface((32*SCALE, 24*SCALE))
REC_LAST_TIME = time.time()
TIME_REC_LIST = []
POINTS_REC_LIST = []
REC_BEGIN_TIME = time.time()
APP_CONFIG = load_config(create_data_dir=True)
DATA_DIR = APP_CONFIG["data_dir"]
BAUDRATE = int(APP_CONFIG["baudrate"])
REC_INTERVAL = float(APP_CONFIG["record_interval"])


class Serial_Manager():
    def __init__(self):
        self.ports = []
        self.names = []
    
    def scan_ports(self):
        options = serial.tools.list_ports.comports()
        if sys.platform == "darwin":
            options = sorted(options, key=lambda item: (not item.device.startswith("/dev/cu."), item.device))
        ports = [i.device for i in options]
        names = [f"{i.description} ({i.device})" for i in options]
        self.ports = ports
        self.names = names
        return ports, names

def get_serial_msg(port):
        if SERIAL.in_waiting:
            print(SERIAL.read())

class myUIDropDownMenu(pygame_gui.elements.UIDropDownMenu):
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self.listed = False 
        self.serial_manager = Serial_Manager()
        self.dic_ports = {}
    
    def process_event(self, event: pygame.event.Event):
        consumed_event = False
        if event.type == 32868:
            if event.ui_object_id in ["drop_down_menu.#expand_button", "drop_down_menu.#selected_option"]:
                if self.current_state != self.menu_states['expanded']:
                    self.update_ports()

        if self.is_enabled:
            consumed_event = self.current_state.process_event(event)
        return consumed_event
    
    def set_disconnected(self):
        self.selected_option = self.options_list[0]

    def update_ports(self):
        self.dic_ports = {}
        ports, names = self.serial_manager.scan_ports()
        if self.selected_option[0] not in names:
            self.selected_option = self.options_list[0]
        
        for i in list(self.options_list):
            if i[0] not in ["断开连接"]:
                self.remove_options([i[0]])
        
        for port, name in zip(ports, names):
            self.dic_ports[name] = port
            self.add_options([name])

def thread_serial():
    global IDENTIFY_BUFFER, ALIVE, SERIAL
    while ALIVE:
        if not SERIAL.is_open:
            time.sleep(0.05)
            continue

        try:
            IDENTIFY_BUFFER = SERIAL.read_until(b"END")
        except Exception as e:
            IDENTIFY_BUFFER = b""
            put_queue_latest(ERROR_QUEUE, e)
            continue

        try:
            frame = parse_frame_packet(IDENTIFY_BUFFER)
        except FrameParseError:
            continue
        put_queue_latest(FRAME_QUEUE, frame)


def put_queue_latest(target_queue, value):
    try:
        target_queue.put_nowait(value)
    except queue.Full:
        try:
            target_queue.get_nowait()
        except queue.Empty:
            pass
        target_queue.put_nowait(value)


def drain_latest_frame():
    frame = None
    while True:
        try:
            frame = FRAME_QUEUE.get_nowait()
        except queue.Empty:
            return frame


def drain_latest_error():
    error = None
    while True:
        try:
            error = ERROR_QUEUE.get_nowait()
        except queue.Empty:
            return error

def draw_func(surf, k, color):
    y = k  // 32
    x = k  %  32
    pygame.draw.rect(surf, color, (x*SCALE, (23-y)*SCALE+50, SCALE, SCALE))

def draw_func2(surf:pygame.Surface, img_buffer:pygame.Surface):
    surf.blit(img_buffer, (0, 0))


def render(surf:pygame.Surface, ):
    if IMG_BUFFER:
        if DISPLAY_MODE == "ORIGINAL":
            draw_heatmap(IMG_BUFFER, lambda k, c: draw_func(surf, k, c))
        else:
        # draw_heatmap_upsample(IMG_BUFFER, lambda s: draw_func2(surf, s))
            sur = draw_heatmap_upsample(IMG_BUFFER)
            surf.blit(sur, (0, 50))

def get_temp(pos):
    mx, my = pos
    x = mx//SCALE
    x = x if x < 31 else 31
    x = x if x > 0 else 0
    y = -(my-50)//SCALE+24
    y = y if y < 23 else 23
    y = y if y > 0 else 0
    k = y*32+x
    tmp = IMG_BUFFER[k+3] if IMG_BUFFER else None
    return x, y, k, tmp

def draw_temp_cross(surf:pygame.Surface, pos, temp):
    x, y = pos
    x_diff = 5 if x < 570 else -45
    y_diff = 5 if y < 500 else -15

    pygame.draw.line(surf, (255, 255, 255), (x-10, y), (x+10, y), 2)
    pygame.draw.line(surf, (255, 255, 255), (x, y-10), (x, y+10), 2)
    pygame.draw.line(surf, (0, 0, 0), (x-3, y), (x+3, y), 2)
    pygame.draw.line(surf, (0, 0, 0), (x, y-3), (x, y+3), 2)
    if 530 > y > 50 and x < 640:
        if isinstance(temp, float):
            text_surf = FONT.render(f"{temp:.2f}", True, (255, 255, 255), (0,0,0))
            surf.blit(text_surf, (x+x_diff, y+y_diff))
        # text_surf = FONT.render(f"{temp:.2f}℃", True, (255, 255, 255), (0,0,0))
        # surf.blit(text_surf, (x+50, y+50))

def change_mode():
    global DISPLAY_MODE
    DISPLAY_MODE = "SCALED" if DISPLAY_MODE == "ORIGINAL" else "ORIGINAL"


def format_serial_error(error):
    message = str(error)
    if sys.platform.startswith("linux") and "Permission" in message:
        message += "，请确认当前用户有 dialout 权限"
    return message


def stop_recording():
    global REC, TIME_REC_LIST, POINTS_REC_LIST
    REC = False
    path = save_curv(TIME_REC_LIST, POINTS_REC_LIST, DATA_DIR)
    TIME_REC_LIST = []
    POINTS_REC_LIST = []
    return path


def rec_trigger():
    global REC, TIME_REC_LIST, POINTS_REC_LIST, REC_BEGIN_TIME, REC_LAST_TIME
    if not SERIAL.is_open:
        return None
    if not REC:
        TIME_REC_LIST = []
        POINTS_REC_LIST = []
        REC = True
        REC_BEGIN_TIME = REC_LAST_TIME = time.time()
        return None
    return stop_recording()

def rec_loop(temps:list):
    global REC, TIME_REC_LIST, POINTS_REC_LIST, REC_LAST_TIME
    if REC:
        now = time.time()
        if now - REC_LAST_TIME > REC_INTERVAL:
            TIME_REC_LIST.append(now - REC_BEGIN_TIME)
            REC_LAST_TIME = now
        # for temp in temps:
            POINTS_REC_LIST.append(temps.copy())
            

def main():
    global ALIVE, IMG_BUFFER
    mouse_pos = (0,0)
    test_points = []
    test_temps = []
    msg = "热成像监视器"
    window_surface = pygame.display.set_mode((640, 530), pygame.RESIZABLE)
    max_temp, min_temp, avg_temp = 0, 0, 0
    background = pygame.Surface((640, 530))
    background.fill(pygame.Color('#000000'))
    manager = pygame_gui.UIManager((640, 530))
    manager.set_locale('zh')
    # hello_list = pygame_gui.elements.UIDropDownMenu(["1","2","3"], "1", pygame.Rect((350, 275), (100, 50)),manager)
    port_list = myUIDropDownMenu(["断开连接"], "断开连接", 
                                 pygame.Rect((0, 0), (200, 50)),
                                 manager, 
                                 anchors={  'left': 'left',
                                            'top': 'top',}) 
    
    button_layout_rect = pygame.Rect((0, 0), (100, 50))
    button_layout_rect.topleft = (200, 0)
    button_save = pygame_gui.elements.UIButton(relative_rect=button_layout_rect, 
                                               text='保存温度帧', 
                                               manager=manager,
                                               anchors={    'left': 'left',
                                                            'top': 'top',})
    
    button_layout_rect2 = pygame.Rect((0, 0), (150, 50))
    button_layout_rect2.topright = (0, 0)
    button_scale = pygame_gui.elements.UIButton(relative_rect=button_layout_rect2, 
                                            text='双线性插值：开', 
                                            manager=manager,
                                            anchors={    'right': 'right',
                                                        'top': 'top',})
    button_layout_rect3 = pygame.Rect((0, 0), (80, 50))
    button_layout_rect3.topright = (-150, 0)
    button_rec = pygame_gui.elements.UIButton(relative_rect=button_layout_rect3, 
                                            text='录制曲线', 
                                            manager=manager,
                                            anchors={   'right': 'right',
                                                        'top': 'top',})
    clock = pygame.time.Clock()
    is_running = True
    threading.Thread(target=thread_serial, daemon=True).start()

    while is_running:
        test_temps.clear()
        time_delta = clock.tick(60)/1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                is_running = False
                ALIVE = False
                if REC:
                    stop_recording()
            elif event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
                test_points.clear()
                if REC:
                    saved_path = stop_recording()
                    button_rec.set_text('录制曲线')
                    msg = f'录制完成：{saved_path.name}' if saved_path else '录制已结束，无数据'
                if event.text == "断开连接":
                    if SERIAL.is_open:
                        SERIAL.close()
                    IMG_BUFFER = None
                    msg = f"{msg}，已断开连接" if msg else "已断开连接"
                    manager.process_events(event)
                    continue
                try:
                    if SERIAL.is_open:
                        SERIAL.close()
                    SERIAL.port = port_list.dic_ports[event.text]
                    SERIAL.baudrate = BAUDRATE
                    SERIAL.open()
                    msg = f"已连接 {SERIAL.port}"
                except Exception as e:
                    SERIAL.close()
                    port_list.set_disconnected()
                    msg = format_serial_error(e)
            elif event.type == pygame_gui.UI_BUTTON_PRESSED:
                if event.ui_element == button_save:
                    if IMG_BUFFER is not None:
                        csv_path, image_path = save_frame(IMG_BUFFER, window_surface, DATA_DIR)
                        msg = f"已保存 {csv_path.name} / {image_path.name}"
                    else:
                        msg = '未连接串口'
                elif event.ui_element == button_scale:
                    change_mode()
                    if DISPLAY_MODE == "SCALED":
                        button_scale.set_text('双线性插值：开')
                    else:
                        button_scale.set_text('双线性插值：关')
                elif event.ui_element == button_rec:
                    if len(test_points) == 0:
                        msg = '请先选择测温点'
                    else:
                        saved_path = rec_trigger()
                        if REC:
                            button_rec.set_text('结束录制')
                            msg = '曲线录制中'
                        else:
                            button_rec.set_text('录制曲线')
                            msg = f'录制完成：{saved_path.name}' if saved_path else '录制已结束，无数据'
            elif event.type == pygame.MOUSEMOTION:
                mouse_pos = event.pos
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if SERIAL.is_open and not REC:
                    if event.button == 1:
                        x, y = event.pos
                        if 530 > y > 50 and x < 640:
                            test_points.append(event.pos)
                    elif  event.button == 3:
                        if len(test_points) > 0:
                            test_points.pop()
                elif not SERIAL.is_open:
                    msg = '未连接串口'
                elif REC:
                    msg = '曲线录制中,结束后可添加测温点'
            manager.process_events(event)

        manager.update(time_delta)
        latest_frame = drain_latest_frame()
        if latest_frame is not None:
            IMG_BUFFER = latest_frame

        serial_error = drain_latest_error()
        if serial_error is not None:
            SERIAL.close()
            port_list.set_disconnected()
            msg = format_serial_error(serial_error)
            if REC:
                saved_path = stop_recording()
                button_rec.set_text('录制曲线')
                if saved_path:
                    msg += f"，曲线已保存：{saved_path.name}"

        window_surface.blit(background, (0, 0))
        
        render(window_surface)
        draw_temp_cross(window_surface, mouse_pos, get_temp(mouse_pos)[-1])
        
        if IMG_BUFFER:
            max_temp, min_temp, avg_temp = IMG_BUFFER[:3]
            pygame.display.set_caption(f'MAX: {max_temp:.2f}, MIN: {min_temp:.2f}, AVG: {avg_temp:.2f}, k: {get_temp(mouse_pos)[-2]} {msg}')
        else:
            pygame.display.set_caption(msg)
        
        test_temps.append(max_temp)
        for i in test_points:
            temp = get_temp(i)[-1]
            draw_temp_cross(window_surface, i, temp)
            test_temps.append(temp)

        rec_loop(test_temps)
        manager.draw_ui(window_surface)
        draw_temp_cross(window_surface, mouse_pos, get_temp(mouse_pos)[-1])
        draw_temp_cross(window_surface, mouse_pos, get_temp(mouse_pos)[-1])

        pygame.display.update()

if __name__ == '__main__':
    main()
