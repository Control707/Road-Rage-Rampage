import pygame
import math
import Bullet
from health import HealthBar
from pygame import mixer

class Car:
    def __init__(self, x, y, angle=0, length=150, max_steering=1, max_acceleration=450.0):
        self.position = pygame.math.Vector2(x, y)
        self.velocity = pygame.math.Vector2(0.0, 0.0)
        self.angle =  angle 
        self.length = length
        self.max_acceleration = max_acceleration
        self.max_steering = max_steering
        self.brake_deceleration = 200
        self.free_deceleration = 100

        self.acceleration = 0.0
        self.steering = 0.0

        self.deaths = 0
        self.max_health = 100
        self.health = self.max_health
        self.health_bar = HealthBar(self.max_health)
        
        self.shooting_sound = mixer.Sound("sounds/Audio Shoot.wav")
        self.shooting_sound.set_volume(0.5)


        # self.engine_sound = mixer.Sound("Car acceleration sound.mp3")
        # self.engine_sound.set_volume(0.5)


    def draw(self, screen, image_path="images/Death Race Car Sticker Fantasy.png"):

        original_surf = pygame.image.load(image_path).convert_alpha()

        surf = pygame.transform.rotozoom(original_surf, self.angle,0.15)
        rect = pygame.transform.rotozoom(original_surf, 0,0.15).get_rect(center = (self.position.x, self.position.y))
        # pygame.draw.rect(screen, RED, rect, 1)

        # Check if car1 is off screen
        screen_width, screen_height = screen.get_size()
        if self.position.x > screen_width:
            self.position.x = 0
        elif self.position.x < 0:
            self.position.x = screen_width
        if self.position.y > screen_height:
            self.position.y = 0
        elif self.position.y < 0:
            self.position.y = screen_height

        screen.blit(surf, rect)

    def update(self, dt):
       
        self.velocity += (self.acceleration * dt, 0)
        self.velocity.x = max(-self.max_acceleration, min(self.velocity.x, self.max_acceleration))

        if self.steering:
            turning_radius = self.length / math.tan(self.steering)
            angular_velocity = self.velocity.x / turning_radius
        else:
            angular_velocity = 0

        self.position += self.velocity.rotate(-self.angle) * dt
        if self.angle < 360.99 and self.angle > -360.99:
            self.angle += math.degrees(angular_velocity) * dt

        else:
            self.angle = 0

        # if self.acceleration>0:
        #     self.engine_sound.play()
        # else:
        #     self.engine_sound.stop()

    def shoot(self):
        # Calculate the offset of the bullet's initial position
        offset = pygame.math.Vector2(self.length / 2, 0).rotate(-self.angle)
        # Add the offset to the car1's position to get the bullet's initial position
        bullet_position = self.position + offset
        self.shooting_sound.play()
        return Bullet.Bullet(bullet_position, self.angle) 


    def hit(self):
        old_health = self.health_bar.health
        self.health_bar.health -= 10
        if self.health_bar.health < 0:
            self.health_bar.health = 0
        print(f"Car hit! Health: {old_health} -> {self.health_bar.health}")

   
        


    def serialize(self):
        # Convert car data to a format that can be sent over the network
        return {
            'x': self.position.x,
            'y': self.position.y,
            'angle': self.angle,
            'health': self.health
        }

    def deserialize(self, data):
        # Update car data based on received network data
        self.position.x = data['x']
        self.position.y = data['y']
        self.angle = data['angle']
        self.health = data['health']
        self.health_bar.health = self.health