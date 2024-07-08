import pygame
class HealthBar:
    def __init__(self, max_health):
        self.max_health = max_health
        self.health = max_health

    def draw(self, screen, x, y):
        pygame.draw.rect(screen, (0, 255, 0), (x, y, 100, 10))
        pygame.draw.rect(screen, '#FF165D', (x, y, 100 * (self.health / self.max_health), 10))