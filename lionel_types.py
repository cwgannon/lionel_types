import pygame
import ctypes
import sys

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH, SCREEN_HEIGHT = pygame.display.Info().current_w, pygame.display.Info().current_h
BG_COLOR = (0, 0, 0)
TEXT_COLOR = (173, 216, 230)
FONT_SIZE = 72

# Disable Windows key
def disable_windows_key():
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    MOD_NOREPEAT = 0x4000
    user32.RegisterHotKey(None, 1, MOD_NOREPEAT, 0x5B)  # 0x5B is the virtual-key code for the left Windows key
    user32.RegisterHotKey(None, 2, MOD_NOREPEAT, 0x5C)  # 0x5C is the virtual-key code for the right Windows key

# Enable Windows key
def enable_windows_key():
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    user32.UnregisterHotKey(None, 1)
    user32.UnregisterHotKey(None, 2)

disable_windows_key()

# Set up the display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption('Child Application')
font = pygame.font.Font(None, FONT_SIZE)

# Cursor
class Cursor:
    def __init__(self):
        self.position = [0, 0]
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

cursor = Cursor()
text_lines = ['']

def draw_text(surface):
    y = 0
    for line in text_lines:
        text_surface = font.render(line, True, TEXT_COLOR)
        surface.blit(text_surface, (0, y))
        y += FONT_SIZE

def handle_keydown(event):
    global running
    if event.key == pygame.K_RETURN:
        cursor.position[0] = 0
        cursor.position[1] += FONT_SIZE
        text_lines.append('')
    elif event.key == pygame.K_BACKSPACE:
        if text_lines:
            if text_lines[-1]:
                text_lines[-1] = text_lines[-1][:-1]
            else:
                text_lines.pop()
                cursor.position[1] -= FONT_SIZE
    elif event.key in (pygame.K_LALT, pygame.K_RALT, pygame.K_TAB, pygame.K_ESCAPE):
        return
    elif event.key == pygame.K_LCTRL and pygame.key.get_pressed()[pygame.K_q]:
        running = False
    else:
        if event.key in range(pygame.K_a, pygame.K_z + 1) or event.key in range(pygame.K_0, pygame.K_9 + 1) or event.unicode.isprintable():
            text_lines[-1] += event.unicode
            cursor.position[0] += font.size(event.unicode)[0]
        else:
            special_keys = {
                pygame.K_F1: "F1", pygame.K_F2: "F2", pygame.K_F3: "F3", pygame.K_F4: "F4", pygame.K_F5: "F5",
                pygame.K_F6: "F6", pygame.K_F7: "F7", pygame.K_F8: "F8", pygame.K_F9: "F9", pygame.K_F10: "F10",
                pygame.K_F11: "F11", pygame.K_F12: "F12", pygame.K_PRINT: "PRTSC", pygame.K_SCROLLLOCK: "SCRLK",
                pygame.K_INSERT: "INS", pygame.K_DELETE: "DEL", pygame.K_HOME: "HOME", pygame.K_END: "END",
                pygame.K_PAGEUP: "PGUP", pygame.K_PAGEDOWN: "PGDN", pygame.K_UP: "UP", pygame.K_DOWN: "DOWN",
                pygame.K_LEFT: "LEFT", pygame.K_RIGHT: "RIGHT"
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
