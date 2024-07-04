import pygame
import ctypes
import sys

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH, SCREEN_HEIGHT = pygame.display.Info().current_w, pygame.display.Info().current_h
BG_COLOR = (0, 0, 0)
TEXT_COLOR = (173, 216, 230)
FONT_SIZE = 120
LINE_HEIGHT = FONT_SIZE * 1.2
MAX_LINES = int((SCREEN_HEIGHT * 0.66) / LINE_HEIGHT)

# Disable Windows key and Print Screen key
def disable_windows_key():
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    MOD_NOREPEAT = 0x4000
    user32.RegisterHotKey(None, 1, MOD_NOREPEAT, 0x5B)  # 0x5B is the virtual-key code for the left Windows key
    user32.RegisterHotKey(None, 2, MOD_NOREPEAT, 0x5C)  # 0x5C is the virtual-key code for the right Windows key
    user32.RegisterHotKey(None, 3, MOD_NOREPEAT, 0x2C)  # 0x2C is the virtual-key code for Print Screen key

# Enable Windows key and Print Screen key
def enable_windows_key():
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    user32.UnregisterHotKey(None, 1)
    user32.UnregisterHotKey(None, 2)
    user32.UnregisterHotKey(None, 3)

disable_windows_key()

# Set up the display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption('Child Application')
font = pygame.font.Font(None, FONT_SIZE)

# Cursor
class Cursor:
    def __init__(self):
        self.position = [SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2]
        self.visible = True
        self.blink_timer = 0

    def update(self, dt):
        self.blink_timer += dt
        if self.blink_timer >= 500:
            self.visible = not self.visible
            self.blink_timer = 0

    def draw(self, surface):
        if self.visible:
            pygame.draw.rect(surface, TEXT_COLOR, (self.position[0], self.position[1], 10, FONT_SIZE), 2)

    def move(self, dx, dy):
        self.position[0] = max(0, min(self.position[0] + dx, SCREEN_WIDTH - 10))
        self.position[1] = max(0, min(self.position[1] + dy, SCREEN_HEIGHT - FONT_SIZE))

cursor = Cursor()
text_lines = ['']

def draw_text(surface):
    y = SCREEN_HEIGHT // 2
    for line in text_lines:
        text_surface = font.render(line, True, TEXT_COLOR)
        surface.blit(text_surface, (SCREEN_WIDTH // 2, y))
        y += LINE_HEIGHT
        if y > SCREEN_HEIGHT * 0.66:
            text_lines.clear()
            text_lines.append('')
            cursor.position = [SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2]
            break

def handle_keydown(event):
    global running
    if event.key == pygame.K_RETURN:
        cursor.position[0] = SCREEN_WIDTH // 2
        cursor.position[1] += LINE_HEIGHT * 2
        text_lines.append('')
    elif event.key == pygame.K_BACKSPACE:
        if text_lines:
            if text_lines[-1]:
                text_lines[-1] = text_lines[-1][:-1]
            else:
                text_lines.pop()
                cursor.position[1] -= LINE_HEIGHT * 2
                if not text_lines:
                    text_lines.append('')
    elif event.key in (pygame.K_LALT, pygame.K_RALT, pygame.K_TAB, pygame.K_ESCAPE, pygame.K_PRINTSCREEN):
        return
    elif event.key == pygame.K_LCTRL and pygame.key.get_pressed()[pygame.K_q]:
        running = False
    elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
        if event.key == pygame.K_LEFT:
            cursor.move(-font.size(" ")[0], 0)
        elif event.key == pygame.K_RIGHT:
            cursor.move(font.size(" ")[0], 0)
        elif event.key == pygame.K_UP:
            cursor.move(0, -LINE_HEIGHT)
        elif event.key == pygame.K_DOWN:
            cursor.move(0, LINE_HEIGHT)
    else:
        if event.key in range(pygame.K_a, pygame.K_z + 1) or event.key in range(pygame.K_0, pygame.K_9 + 1) or event.unicode.isprintable():
            text_lines[-1] += event.unicode
            cursor.position[0] += font.size(event.unicode)[0]
        else:
            special_keys = {
                pygame.K_F1: "F1", pygame.K_F2: "F2", pygame.K_F3: "F3", pygame.K_F4: "F4", pygame.K_F5: "F5",
                pygame.K_F6: "F6", pygame.K_F7: "F7", pygame.K_F8: "F8", pygame.K_F9: "F9", pygame.K_F10: "F10",
                pygame.K_F11: "F11", pygame.K_F12: "F12", pygame.K_INSERT: "INS", pygame.K_DELETE: "DEL",
                pygame.K_HOME: "HOME", pygame.K_END: "END", pygame.K_PAGEUP: "PGUP", pygame.K_PAGEDOWN: "PGDN"
            }
            if event.key in special_keys:
                text_lines[-1] += special_keys[event.key]
                cursor.position[0] += font.size(special_keys[event.key])[0]

# Main loop
running = True
clock = pygame.time.Clock()

while running:
    dt = clock.tick(30)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            handle_keydown(event)

    cursor.update(dt)

    screen.fill(BG_COLOR)
    draw_text(screen)
    cursor.draw(screen)
    pygame.display.flip()

pygame.quit()
enable_windows_key()
sys.exit()
