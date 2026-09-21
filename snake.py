import pygame
import random
import sys
from collections import deque

pygame.init()

# 화면 설정
WIDTH, HEIGHT = 600, 400
CELL_SIZE = 20
GRID_WIDTH = WIDTH // CELL_SIZE
GRID_HEIGHT = HEIGHT // CELL_SIZE

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("뱀 게임 - 사람 vs AI")
clock = pygame.time.Clock()

# 색상
BLACK = (0, 0, 0)
GREEN = (0, 200, 0)
DARK_GREEN = (0, 120, 0)
BLUE = (60, 140, 255)
DARK_BLUE = (30, 80, 160)
RED = (220, 0, 0)
WHITE = (255, 255, 255)
GRAY = (40, 40, 40)

font = pygame.font.SysFont("malgungothic", 26)
big_font = pygame.font.SysFont("malgungothic", 34)

DIRECTIONS = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def random_food_position(occupied):
    while True:
        pos = (random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
        if pos not in occupied:
            return pos


def draw_cell(pos, color, border_color=None):
    rect = pygame.Rect(pos[0] * CELL_SIZE, pos[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE)
    pygame.draw.rect(screen, color, rect)
    if border_color:
        pygame.draw.rect(screen, border_color, rect, 1)


def show_message(text, y_offset=0, use_big=False):
    f = big_font if use_big else font
    surface = f.render(text, True, WHITE)
    rect = surface.get_rect(center=(WIDTH // 2, HEIGHT // 2 + y_offset))
    screen.blit(surface, rect)


def bfs_next_direction(start, goal, blocked):
    """start에서 goal까지 최단 경로를 찾아 첫 이동 방향을 반환. 경로 없으면 None."""
    queue = deque([start])
    came_from = {start: None}

    while queue:
        current = queue.popleft()
        if current == goal:
            break
        for dx, dy in DIRECTIONS:
            neighbor = (current[0] + dx, current[1] + dy)
            if (
                0 <= neighbor[0] < GRID_WIDTH
                and 0 <= neighbor[1] < GRID_HEIGHT
                and neighbor not in blocked
                and neighbor not in came_from
            ):
                came_from[neighbor] = current
                queue.append(neighbor)

    if goal not in came_from:
        return None

    node = goal
    path = []
    while came_from[node] is not None:
        path.append(node)
        node = came_from[node]
    path.reverse()

    if not path:
        return None

    first_step = path[0]
    return (first_step[0] - start[0], first_step[1] - start[1])


def fallback_direction(start, goal, blocked, current_direction):
    """BFS로 길을 못 찾을 때 안전한 방향 중 사과와 가장 가까워지는 방향 선택."""
    candidates = []
    for dx, dy in DIRECTIONS:
        if (dx, dy) == (-current_direction[0], -current_direction[1]):
            continue  # 자기 목 방향으로 역주행 금지
        new_pos = (start[0] + dx, start[1] + dy)
        if (
            0 <= new_pos[0] < GRID_WIDTH
            and 0 <= new_pos[1] < GRID_HEIGHT
            and new_pos not in blocked
        ):
            dist = abs(new_pos[0] - goal[0]) + abs(new_pos[1] - goal[1])
            candidates.append((dist, (dx, dy)))

    if candidates:
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]

    return current_direction  # 안전한 곳이 없으면 그냥 직진 (죽을 수도 있음)


def ai_choose_direction(ai_snake, ai_direction, food, human_snake):
    head = ai_snake[0]
    blocked = set(ai_snake[:-1]) | set(human_snake[:-1])
    blocked.discard(head)

    direction = bfs_next_direction(head, food, blocked)
    if direction is None:
        direction = fallback_direction(head, food, blocked, ai_direction)
    return direction


def game_loop():
    # 사람 뱀: 왼쪽에서 시작, 오른쪽으로 이동
    human_snake = [(5, GRID_HEIGHT // 2)]
    human_direction = (1, 0)
    human_next_direction = human_direction

    # AI 뱀: 오른쪽에서 시작, 왼쪽으로 이동
    ai_snake = [(GRID_WIDTH - 6, GRID_HEIGHT // 2)]
    ai_direction = (-1, 0)

    food = random_food_position(set(human_snake) | set(ai_snake))

    human_score = 0
    ai_score = 0
    speed = 8

    game_over = False
    result_text = ""

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if game_over:
                    if event.key == pygame.K_r:
                        return game_loop()
                    if event.key == pygame.K_q:
                        pygame.quit()
                        sys.exit()
                else:
                    if event.key in (pygame.K_UP, pygame.K_w) and human_direction != (0, 1):
                        human_next_direction = (0, -1)
                    elif event.key in (pygame.K_DOWN, pygame.K_s) and human_direction != (0, -1):
                        human_next_direction = (0, 1)
                    elif event.key in (pygame.K_LEFT, pygame.K_a) and human_direction != (1, 0):
                        human_next_direction = (-1, 0)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d) and human_direction != (-1, 0):
                        human_next_direction = (1, 0)

        if not game_over:
            human_direction = human_next_direction
            ai_direction = ai_choose_direction(ai_snake, ai_direction, food, human_snake)

            human_new_head = (
                human_snake[0][0] + human_direction[0],
                human_snake[0][1] + human_direction[1],
            )
            ai_new_head = (
                ai_snake[0][0] + ai_direction[0],
                ai_snake[0][1] + ai_direction[1],
            )

            human_eats = human_new_head == food
            ai_eats = ai_new_head == food

            human_dead = False
            ai_dead = False

            # 벽 충돌
            if not (0 <= human_new_head[0] < GRID_WIDTH and 0 <= human_new_head[1] < GRID_HEIGHT):
                human_dead = True
            if not (0 <= ai_new_head[0] < GRID_WIDTH and 0 <= ai_new_head[1] < GRID_HEIGHT):
                ai_dead = True

            # 자기 몸 충돌 (꼬리는 이동하며 비워지므로 제외, 먹었으면 꼬리도 그대로 있음)
            human_body_check = human_snake if human_eats else human_snake[:-1]
            ai_body_check = ai_snake if ai_eats else ai_snake[:-1]

            if not human_dead and human_new_head in human_body_check:
                human_dead = True
            if not ai_dead and ai_new_head in ai_body_check:
                ai_dead = True

            # 상대방 몸 충돌
            if not human_dead and human_new_head in ai_body_check:
                human_dead = True
            if not ai_dead and ai_new_head in human_body_check:
                ai_dead = True

            # 정면충돌 (같은 칸으로 이동)
            if human_new_head == ai_new_head:
                human_dead = True
                ai_dead = True

            if human_dead or ai_dead:
                game_over = True
                if human_dead and ai_dead:
                    result_text = "무승부! 둘 다 충돌했습니다."
                elif human_dead:
                    result_text = "AI 승리! 사람이 충돌했습니다."
                else:
                    result_text = "사람 승리! AI가 충돌했습니다."
            else:
                human_snake.insert(0, human_new_head)
                if human_eats:
                    human_score += 1
                else:
                    human_snake.pop()

                ai_snake.insert(0, ai_new_head)
                if ai_eats:
                    ai_score += 1
                else:
                    ai_snake.pop()

                if human_eats or ai_eats:
                    food = random_food_position(set(human_snake) | set(ai_snake))

        # 그리기
        screen.fill(BLACK)

        for x in range(0, WIDTH, CELL_SIZE):
            pygame.draw.line(screen, GRAY, (x, 0), (x, HEIGHT))
        for y in range(0, HEIGHT, CELL_SIZE):
            pygame.draw.line(screen, GRAY, (0, y), (WIDTH, y))

        draw_cell(food, RED)

        for segment in human_snake:
            draw_cell(segment, GREEN, DARK_GREEN)
        for segment in ai_snake:
            draw_cell(segment, BLUE, DARK_BLUE)

        score_text = f"사람(초록): {human_score}   AI(파랑): {ai_score}"
        score_surface = font.render(score_text, True, WHITE)
        screen.blit(score_surface, (10, 10))

        if game_over:
            show_message(result_text, -20, use_big=True)
            show_message("R: 다시하기   Q: 종료", 20)

        pygame.display.flip()
        clock.tick(speed)


if __name__ == "__main__":
    game_loop()
