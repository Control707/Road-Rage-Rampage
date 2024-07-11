import pygame
import math
class Bullet:
    def __init__(self, position, angle):
        self.position = position

        self.angle = angle
        self.speed = 30
        

    def update(self):
        self.position.x += math.cos(math.radians(self.angle)) * self.speed
        self.position.y -= math.sin(math.radians(self.angle)) * self.speed

    def draw(self, screen):

        pygame.draw.circle(screen, '#FF165D', (int(self.position.x), int(self.position.y)), 5)

    def is_out_of_bounds(self, screen_width, screen_height):
        return (self.position.x < 0 or self.position.x > screen_width or
                self.position.y < 0 or self.position.y > screen_height)

    def collides_with(self, car):
        
        
        return (
            math.hypot(
                self.position.x - car.position.x, self.position.y - car.position.y
            )
            < car.length / 2
        )

    def serialize(self):
        # Convert car data to a format that can be sent over the network
        return {
            'x': self.position.x,
            'y': self.position.y,
            'angle': self.angle,
            'speed': self.speed
        }

    @classmethod
    def deserialize(cls, data):
        # Create a new Bullet instance
        bullet = cls(pygame.Vector2(data["x"], data["y"]), data["angle"])

        # Update bullet data based on received network data
        bullet.speed = data["speed"]

        return bullet
