"""
石头剪刀布游戏 - 服务器端
支持双人对战匹配、多回合计分、实时聊天
"""
import socket
import threading
import time

# ============ 游戏规则 ============
RULES = {
    'rock': 'scissors',
    'scissors': 'paper',
    'paper': 'rock'
}

def evaluate(move_a, move_b):
    """返回 player_a 的结果: 'win' / 'lose' / 'draw'"""
    if move_a == move_b:
        return 'draw'
    return 'win' if RULES[move_a] == move_b else 'lose'

# ============ 单局比赛 Game ============
class Game:
    def __init__(self, conn_a, name_a, conn_b, name_b, best_of=3):
        self.conns = [conn_a, conn_b]
        self.names = [name_a, name_b]
        self.best_of = best_of          # 几局几胜
        self.max_rounds = best_of * 2 - 1  # 最多进行的局数
        self.scores = [0, 0]
        self.moves = [None, None]
        self.move_events = [threading.Event(), threading.Event()]
        self.running = True
        self.lock = threading.Lock()

    def send(self, player_idx, msg):
        """向指定玩家发送消息"""
        try:
            self.conns[player_idx].sendall((msg + '\n').encode('utf-8'))
        except:
            pass

    def broadcast(self, msg):
        """向双方广播消息"""
        self.send(0, msg)
        self.send(1, msg)

    def set_move(self, player_idx, move):
        """客户端线程调用，设置出拳"""
        with self.lock:
            self.moves[player_idx] = move
        self.move_events[player_idx].set()

    def wait_for_moves(self):
        """等待双方都出拳，返回 (move0, move1)"""
        self.move_events[0].wait()
        self.move_events[1].wait()
        self.move_events[0].clear()
        self.move_events[1].clear()
        with self.lock:
            m0, m1 = self.moves
            self.moves = [None, None]
        return m0, m1

    def run(self):
        """运行比赛主循环"""
        self.send(0, f'OPPONENT_JOINED:{self.names[1]}')
        self.send(1, f'OPPONENT_JOINED:{self.names[0]}')
        self.broadcast(f'GAME_INFO:Best of {self.best_of} | First to {self.best_of // 2 + 1} wins')

        round_num = 1
        while self.running and round_num <= self.max_rounds:
            # 检查是否已有人获胜
            wins_needed = self.best_of // 2 + 1
            if self.scores[0] >= wins_needed or self.scores[1] >= wins_needed:
                break

            # 宣布回合开始
            self.broadcast(f'ROUND_START:{round_num}:{self.best_of}')
            self.send(0, 'YOUR_MOVE')
            self.send(1, 'YOUR_MOVE')

            # 等待双方出拳（由各自的 client thread 调用 set_move）
            m0, m1 = self.wait_for_moves()
            if m0 is None or m1 is None:
                # 有人断线，游戏结束
                break

            # 判定
            result0 = evaluate(m0, m1)  # player0 的结果
            if result0 == 'win':
                self.scores[0] += 1
                result1 = 'lose'
            elif result0 == 'lose':
                self.scores[1] += 1
                result1 = 'win'
            else:
                result1 = 'draw'

            # 发送回合结果
            self.send(0, f'ROUND_RESULT:{m0}:{m1}:{result0}')
            self.send(1, f'ROUND_RESULT:{m1}:{m0}:{result1}')
            self.broadcast(f'SCORE:{self.scores[0]}:{self.scores[1]}')

            round_num += 1

        # 比赛结束
        s0, s1 = self.scores
        if s0 > s1:
            self.broadcast(f'GAME_OVER:{self.names[0]} wins! ({s0}-{s1})')
        elif s1 > s0:
            self.broadcast(f'GAME_OVER:{self.names[1]} wins! ({s1}-{s0})')
        else:
            self.broadcast(f'GAME_OVER:DRAW! ({s0}-{s1})')

        self.running = False
        # 通知双方游戏结束
        self.send(0, 'DONE')
        self.send(1, 'DONE')

    def opponent_disconnected(self, player_idx):
        """对方断线处理"""
        other = 1 - player_idx
        self.send(other, 'OPPONENT_DISCONNECTED')
        self.send(other, 'DONE')
        self.running = False
        # 让 wait_for_moves 不再阻塞
        self.move_events[0].set()
        self.move_events[1].set()


# ============ 全局状态 ============
waiting_player = None  # (connection, name, address)
waiting_lock = threading.Lock()
games = []

def handle_client(conn, addr):
    """处理单个客户端连接"""
    global waiting_player
    name = None
    current_game = None
    player_idx = None

    try:
        # 接收用户名
        data = conn.recv(4096).decode('utf-8').strip()
        if not data.startswith('NICK:'):
            conn.sendall(b'ERROR:First message must be NICK:<name>\n')
            conn.close()
            return
        name = data[5:].strip()
        if not name:
            conn.sendall(b'ERROR:Name cannot be empty\n')
            conn.close()
            return

        print(f'[+] Player "{name}" connected from {addr}')
        conn.sendall(b'WELCOME\n')

        # 尝试匹配对手
        with waiting_lock:
            if waiting_player is None:
                # 没有等待的玩家，成为等待者
                waiting_player = (conn, name, addr)
                conn.sendall(b'WAITING_FOR_OPPONENT\n')
                print(f'[-] Player "{name}" is waiting for an opponent...')
                # 释放锁，等待匹配
            else:
                # 有等待的玩家，配对！
                w_conn, w_name, w_addr = waiting_player
                waiting_player = None  # 清空等待队列
                # 创建游戏
                game = Game(w_conn, w_name, conn, name, best_of=3)
                games.append(game)
                print(f'[!] Match! "{w_name}" vs "{name}"')

                # 在游戏线程中运行
                t = threading.Thread(target=game.run, daemon=True)
                t.start()

                current_game = game
                player_idx = 1  # 当前玩家是 player 1（后连入的）

        # 如果没有立刻匹配，就等待被匹配
        if current_game is None:
            # 循环等待，直到 waiting_player 被清空（表示被匹配）
            while True:
                with waiting_lock:
                    if waiting_player is None or waiting_player[0] is not conn:
                        break
                time.sleep(0.1)

            # 现在应该已被匹配，找到对应的 game
            for g in games:
                if g.conns[0] is conn or g.conns[1] is conn:
                    current_game = g
                    player_idx = 0 if g.conns[0] is conn else 1
                    break

        # 进入游戏消息循环
        if current_game is None:
            conn.sendall(b'ERROR:Failed to join a game\n')
            conn.close()
            return

        buf = ''
        while current_game.running:
            try:
                data = conn.recv(4096).decode('utf-8')
                if not data:
                    break
                buf += data
                while '\n' in buf:
                    line, buf = buf.split('\n', 1)
                    line = line.strip()
                    if not line:
                        continue

                    if line.startswith('MOVE:'):
                        move = line[5:].strip().lower()
                        if move in ('rock', 'paper', 'scissors'):
                            current_game.set_move(player_idx, move)
                            current_game.send(player_idx, 'MOVE_RECEIVED')
                        else:
                            current_game.send(player_idx, 'ERROR:Invalid move. Use rock/paper/scissors')
                    elif line.startswith('CHAT:'):
                        msg = line[5:].strip()
                        if msg:
                            other = 1 - player_idx
                            current_game.send(other, f'CHAT:{current_game.names[player_idx]}:{msg}')
            except (ConnectionResetError, BrokenPipeError, OSError):
                break

    except (ConnectionResetError, BrokenPipeError, OSError) as e:
        print(f'[!] Connection error with {addr}: {e}')
    finally:
        print(f'[-] Player "{name or "unknown"}" disconnected')
        if current_game and current_game.running:
            current_game.opponent_disconnected(player_idx)
        # 清理 waiting 状态
        with waiting_lock:
            if waiting_player and waiting_player[0] is conn:
                waiting_player = None
        try:
            conn.close()
        except:
            pass


# ============ 主程序 ============
def main():
    HOST = 'localhost'
    PORT = 25585

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server.bind((HOST, PORT))
    except socket.error as e:
        print(f'[!] Bind failed: {e}')
        return

    server.listen()
    print(f'[*] RPS Server listening on {HOST}:{PORT}')
    print('[*] Waiting for players...')

    while True:
        conn, addr = server.accept()
        t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        t.start()

if __name__ == '__main__':
    main()
