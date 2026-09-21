import tkinter as tk
import random

WIDTH = 600
HEIGHT = 500

PADDLE_WIDTH = 100
PADDLE_HEIGHT = 15
PADDLE_SPEED = 25

BALL_SIZE = 15
BALL_SPEED = 5

BRICK_ROWS = 5
BRICK_COLS = 8
BRICK_WIDTH = WIDTH // BRICK_COLS
BRICK_HEIGHT = 25
BRICK_COLORS = ["#e74c3c", "#e67e22", "#f1c40f", "#2ecc71", "#3498db"]


class BreakoutGame:
    def __init__(self, root):
        self.root = root
        self.root.title("블럭깨기")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="black", highlightthickness=0)
        self.canvas.pack()

        self.score = 0
        self.lives = 3
        self.running = False
        self.game_over = False

        self.paddle = None
        self.ball = None
        self.bricks = {}

        self.ball_dx = BALL_SPEED
        self.ball_dy = -BALL_SPEED

        self.score_text = self.canvas.create_text(
            60, 15, text="점수: 0", fill="white", font=("맑은 고딕", 12)
        )
        self.lives_text = self.canvas.create_text(
            WIDTH - 60, 15, text="생명: 3", fill="white", font=("맑은 고딕", 12)
        )

        self.setup_level()

        self.root.bind("<Left>", self.move_left)
        self.root.bind("<Right>", self.move_right)
        self.root.bind("<space>", self.toggle_pause_or_start)
        self.root.bind("<Return>", self.restart)

        self.show_message("스페이스바를 눌러 시작하세요", 20)

    def setup_level(self):
        # 패들 생성
        paddle_x = WIDTH / 2 - PADDLE_WIDTH / 2
        paddle_y = HEIGHT - 40
        self.paddle = self.canvas.create_rectangle(
            paddle_x, paddle_y, paddle_x + PADDLE_WIDTH, paddle_y + PADDLE_HEIGHT,
            fill="#ecf0f1", outline=""
        )

        # 공 생성
        ball_x = WIDTH / 2 - BALL_SIZE / 2
        ball_y = paddle_y - BALL_SIZE - 5
        self.ball = self.canvas.create_oval(
            ball_x, ball_y, ball_x + BALL_SIZE, ball_y + BALL_SIZE,
            fill="white", outline=""
        )

        # 벽돌 생성
        self.bricks = {}
        top_offset = 50
        for row in range(BRICK_ROWS):
            for col in range(BRICK_COLS):
                x1 = col * BRICK_WIDTH + 2
                y1 = row * BRICK_HEIGHT + top_offset
                x2 = x1 + BRICK_WIDTH - 4
                y2 = y1 + BRICK_HEIGHT - 4
                brick_id = self.canvas.create_rectangle(
                    x1, y1, x2, y2, fill=BRICK_COLORS[row % len(BRICK_COLORS)], outline=""
                )
                self.bricks[brick_id] = True

    def move_left(self, event=None):
        coords = self.canvas.coords(self.paddle)
        if coords[0] > 0:
            self.canvas.move(self.paddle, -PADDLE_SPEED, 0)

    def move_right(self, event=None):
        coords = self.canvas.coords(self.paddle)
        if coords[2] < WIDTH:
            self.canvas.move(self.paddle, PADDLE_SPEED, 0)

    def toggle_pause_or_start(self, event=None):
        if self.game_over:
            return
        if not self.running:
            self.running = True
            self.canvas.delete("message")
            self.game_loop()

    def restart(self, event=None):
        self.canvas.delete("all")
        self.score = 0
        self.lives = 3
        self.running = False
        self.game_over = False
        self.ball_dx = BALL_SPEED
        self.ball_dy = -BALL_SPEED

        self.score_text = self.canvas.create_text(
            60, 15, text="점수: 0", fill="white", font=("맑은 고딕", 12)
        )
        self.lives_text = self.canvas.create_text(
            WIDTH - 60, 15, text="생명: 3", fill="white", font=("맑은 고딕", 12)
        )

        self.setup_level()
        self.show_message("스페이스바를 눌러 시작하세요", 20)

    def show_message(self, text, size=24):
        self.canvas.delete("message")
        self.canvas.create_text(
            WIDTH / 2, HEIGHT / 2, text=text, fill="yellow",
            font=("맑은 고딕", size, "bold"), tags="message"
        )

    def game_loop(self):
        if not self.running:
            return

        self.move_ball()
        self.check_collisions()

        if not self.bricks:
            self.running = False
            self.show_message("승리했습니다!\n엔터 키로 재시작", 24)
            return

        if self.lives <= 0:
            self.running = False
            self.game_over = True
            self.show_message(f"게임 오버\n최종 점수: {self.score}\n엔터 키로 재시작", 24)
            return

        self.root.after(16, self.game_loop)

    def move_ball(self):
        self.canvas.move(self.ball, self.ball_dx, self.ball_dy)
        ball_coords = self.canvas.coords(self.ball)
        x1, y1, x2, y2 = ball_coords

        # 좌우 벽 충돌
        if x1 <= 0 or x2 >= WIDTH:
            self.ball_dx = -self.ball_dx

        # 천장 충돌
        if y1 <= 0:
            self.ball_dy = -self.ball_dy

        # 바닥에 떨어짐 (생명 감소)
        if y2 >= HEIGHT:
            self.lives -= 1
            self.canvas.itemconfig(self.lives_text, text=f"생명: {self.lives}")
            if self.lives > 0:
                self.reset_ball_and_paddle()

    def reset_ball_and_paddle(self):
        paddle_coords = self.canvas.coords(self.paddle)
        paddle_x = WIDTH / 2 - PADDLE_WIDTH / 2
        self.canvas.coords(
            self.paddle, paddle_x, paddle_coords[1], paddle_x + PADDLE_WIDTH, paddle_coords[3]
        )

        ball_x = WIDTH / 2 - BALL_SIZE / 2
        ball_y = paddle_coords[1] - BALL_SIZE - 5
        self.canvas.coords(self.ball, ball_x, ball_y, ball_x + BALL_SIZE, ball_y + BALL_SIZE)

        self.ball_dx = BALL_SPEED * random.choice([-1, 1])
        self.ball_dy = -BALL_SPEED

    def check_collisions(self):
        ball_coords = self.canvas.coords(self.ball)
        x1, y1, x2, y2 = ball_coords

        # 패들 충돌
        paddle_coords = self.canvas.coords(self.paddle)
        px1, py1, px2, py2 = paddle_coords

        if x2 >= px1 and x1 <= px2 and y2 >= py1 and y1 <= py2 and self.ball_dy > 0:
            # 패들의 어느 위치에 맞았는지에 따라 반사각 조정
            paddle_center = (px1 + px2) / 2
            ball_center = (x1 + x2) / 2
            offset = (ball_center - paddle_center) / (PADDLE_WIDTH / 2)
            self.ball_dx = BALL_SPEED * offset
            self.ball_dy = -abs(self.ball_dy)

        # 벽돌 충돌
        overlapping = self.canvas.find_overlapping(x1, y1, x2, y2)
        for item in overlapping:
            if item in self.bricks:
                self.canvas.delete(item)
                del self.bricks[item]
                self.ball_dy = -self.ball_dy
                self.score += 10
                self.canvas.itemconfig(self.score_text, text=f"점수: {self.score}")
                break


if __name__ == "__main__":
    root = tk.Tk()
    game = BreakoutGame(root)
    root.mainloop()
