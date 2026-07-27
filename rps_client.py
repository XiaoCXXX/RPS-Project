"""
石头剪刀布游戏 - 客户端
支持对战、聊天、实时状态显示
"""
import socket
import threading
import sys
import os
import time

# ============ 终端样式 ============
GREEN = '\033[92m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
RED = '\033[91m'
MAGENTA = '\033[95m'
BOLD = '\033[1m'
RESET = '\033[0m'
CLEAR = '\033[2J\033[H'

# Windows 兼容：如果不支持 ANSI，使用 plain
if os.name == 'nt':
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except:
        # 回退到无颜色
        GREEN = YELLOW = CYAN = RED = MAGENTA = BOLD = RESET = ''
        CLEAR = '\n' * 40


def clear_screen():
    """清屏"""
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')


def print_banner():
    """打印游戏标题"""
    banner = f"""
{BOLD}{CYAN}╔══════════════════════════════════╗
║      石头剪刀布 · RPS Arena      ║
╚══════════════════════════════════╝{RESET}
"""
    print(banner)


def print_help():
    """打印帮助信息"""
    print(f'{YELLOW}Commands:{RESET}')
    print(f'  {BOLD}rock{RESET}     - 出石头')
    print(f'  {BOLD}paper{RESET}    - 出布')
    print(f'  {BOLD}scissors{RESET} - 出剪刀')
    print(f'  {BOLD}chat <msg>{RESET} - 发送聊天消息')
    print(f'  {BOLD}/help{RESET}    - 显示帮助')
    print(f'  {BOLD}/quit{RESET}    - 退出游戏')
    print()


# ============ 客户端类 ============
class RPSClient:
    def __init__(self, host='localhost', port=25585):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.port = port
        self.username = ''
        self.running = True
        self.in_game = False
        self.my_turn = False
        self.game_over = False

    def connect(self):
        """连接到服务器"""
        try:
            self.sock.connect((self.host, self.port))
            return True
        except Exception as e:
            print(f'{RED}[!] Connection failed: {e}{RESET}')
            return False

    def send(self, msg):
        """发送消息"""
        try:
            self.sock.sendall((msg + '\n').encode('utf-8'))
        except:
            self.running = False

    def receive_loop(self):
        """后台线程：接收服务器消息"""
        buf = ''
        while self.running:
            try:
                data = self.sock.recv(4096).decode('utf-8')
                if not data:
                    print(f'\n{RED}[!] Disconnected from server.{RESET}')
                    self.running = False
                    break
                buf += data
                while '\n' in buf:
                    line, buf = buf.split('\n', 1)
                    line = line.strip()
                    if line:
                        self.handle_message(line)
            except (ConnectionResetError, BrokenPipeError, OSError):
                print(f'\n{RED}[!] Connection lost.{RESET}')
                self.running = False
                break

    def handle_message(self, msg):
        """处理服务器消息"""
        if msg == 'WELCOME':
            pass  # 连接成功

        elif msg == 'WAITING_FOR_OPPONENT':
            print(f'\n{YELLOW}⏳ 正在等待对手加入...{RESET}')

        elif msg.startswith('OPPONENT_JOINED:'):
            opp = msg[16:]
            self.in_game = True
            print(f'\n{GREEN}⚔️  对手已加入: {BOLD}{opp}{RESET}')

        elif msg.startswith('GAME_INFO:'):
            info = msg[10:]
            print(f'{CYAN}📋 {info}{RESET}')

        elif msg.startswith('ROUND_START:'):
            parts = msg[12:].split(':')
            rnd = parts[0]
            best_of = parts[1]
            print(f'\n{BOLD}{YELLOW}═══ 第 {rnd} 回合 ═══ (Best of {best_of}){RESET}')
            self.game_over = False

        elif msg == 'YOUR_MOVE':
            self.my_turn = True
            print(f'\n{GREEN}{BOLD}🤜 请出拳！(rock / paper / scissors){RESET}')

        elif msg == 'MOVE_RECEIVED':
            self.my_turn = False
            print(f'{CYAN}✓ 出拳已记录，等待对手...{RESET}')

        elif msg.startswith('ROUND_RESULT:'):
            parts = msg[13:].split(':')
            my_move = parts[0]
            opp_move = parts[1]
            outcome = parts[2]

            # 显示结果
            emoji_map = {'rock': '🪨', 'paper': '📄', 'scissors': '✂️'}
            my_emoji = emoji_map.get(my_move, '?')
            opp_emoji = emoji_map.get(opp_move, '?')

            print(f'\n{BOLD}=== 回合结果 ==={RESET}')
            print(f'  你: {my_emoji} {my_move.upper()}')
            print(f'  对手: {opp_emoji} {opp_move.upper()}')

            if outcome == 'win':
                print(f'  {GREEN}{BOLD}🏆 你赢了这一回合！{RESET}')
            elif outcome == 'lose':
                print(f'  {RED}{BOLD}💔 你输了这一回合！{RESET}')
            else:
                print(f'  {YELLOW}{BOLD}🤝 平局！{RESET}')

        elif msg.startswith('SCORE:'):
            parts = msg[6:].split(':')
            my_score = parts[0]
            opp_score = parts[1]
            print(f'{CYAN}📊 比分: {BOLD}{my_score} - {opp_score}{RESET}\n')

        elif msg.startswith('GAME_OVER:'):
            result = msg[10:]
            self.in_game = False
            self.game_over = True
            print(f'\n{"=" * 40}')
            print(f'{BOLD}{YELLOW}        游戏结束！{RESET}')
            print(f'{BOLD}{CYAN}        {result}{RESET}')
            print(f'{"=" * 40}\n')

        elif msg == 'DONE':
            # 比赛彻底结束，可以安全退出了
            pass

        elif msg.startswith('CHAT:'):
            parts = msg[5:].split(':', 1)
            if len(parts) == 2:
                from_name = parts[0]
                text = parts[1]
                print(f'{MAGENTA}[{from_name}] {text}{RESET}')

        elif msg.startswith('ERROR:'):
            print(f'{RED}[!] {msg[6:]}{RESET}')

        elif msg == 'OPPONENT_DISCONNECTED':
            print(f'{RED}[!] 对手已断开连接，游戏结束{RESET}')
            self.in_game = False
            self.game_over = True

    def run(self):
        """主循环"""
        clear_screen()
        print_banner()

        # 获取用户名
        self.username = input(f'{CYAN}请输入你的用户名: {RESET}').strip()
        if not self.username:
            self.username = 'Player'
        print()

        # 连接服务器
        if not self.connect():
            input('按 Enter 退出...')
            return

        # 发送用户名
        self.send(f'NICK:{self.username}')

        # 启动接收线程
        recv_thread = threading.Thread(target=self.receive_loop, daemon=True)
        recv_thread.start()

        # 给接收线程一点时间接收欢迎和等待状态
        time.sleep(0.3)

        print(f'{GREEN}✅ 已连接到服务器！{RESET}')
        print(f'{YELLOW}💡 输入 rock/paper/scissors 出拳 | chat <消息> 聊天 | /help 帮助{RESET}\n')

        # 主输入循环
        self.my_turn = False
        while self.running:
            try:
                cmd = input()
                if not cmd:
                    continue

                if cmd == '/quit':
                    print(f'\n{YELLOW}退出游戏...{RESET}')
                    break

                elif cmd == '/help':
                    print_help()

                elif cmd.startswith('chat '):
                    msg = cmd[5:].strip()
                    if msg:
                        self.send(f'CHAT:{msg}')
                    else:
                        print(f'{YELLOW}用法: chat <消息>{RESET}')

                elif cmd in ('rock', 'paper', 'scissors'):
                    self.send(f'MOVE:{cmd}')

                else:
                    # 尝试当作聊天消息处理（不带 chat 前缀）
                    if cmd.startswith('/'):
                        print(f'{YELLOW}未知命令。输入 /help 查看可用命令{RESET}')
                    else:
                        print(f'{YELLOW}出拳请输入 rock/paper/scissors，聊天请加 chat 前缀{RESET}')

            except (EOFError, KeyboardInterrupt):
                break

        self.running = False
        try:
            self.sock.close()
        except:
            pass


# ============ 启动 ============
if __name__ == '__main__':
    client = RPSClient()
    try:
        client.run()
    except KeyboardInterrupt:
        print(f'\n{YELLOW}游戏结束，再见！{RESET}')
