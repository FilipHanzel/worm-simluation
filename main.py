from __future__ import annotations

import random
import sys
from itertools import pairwise
from math import sqrt

import pygame as pg


class Vec:
    __slots__ = "x", "y"

    def __init__(self, x: float | int, y: float | int):
        self.x = x
        self.y = y

    def to_tuple(self) -> tuple[float | int, float | int]:
        return (self.x, self.y)

    def copy(self) -> Vec:
        return Vec(self.x, self.y)

    def __repr__(self) -> str:
        return f"Vec(x={self.x}, y={self.y})"


def distance(a: Vec, b: Vec) -> float:
    dx = a.x - b.x
    dy = a.y - b.y
    return sqrt(dx * dx + dy * dy)


class Segment:
    __slots__ = "pos", "vel", "radius"

    def __init__(self, pos: Vec, radius: int):
        self.pos = pos
        self.radius = radius


class Worm:
    def __init__(self, pos: Vec, n_segments: int, radius: int):
        self.head = Segment(pos, radius)

        self.segments = [self.head]
        for idx in range(n_segments):
            segment = Segment(pos.copy(), (n_segments - idx) / n_segments * radius)
            self.segments.append(segment)

        self.power = 0.6
        self.vel = Vec(0, 0)

    def draw(self, window: pg.Surface) -> None:
        for segment in self.segments:
            pg.draw.circle(window, "#ffbc85", segment.pos.to_tuple(), segment.radius)
        pg.draw.circle(window, "#f7786d", self.head.pos.to_tuple(), self.head.radius)

    def move(self, acceleration: Vec) -> None:
        self.vel.x *= 0.9
        self.vel.y *= 0.9

        self.vel.x += acceleration.x * self.power
        self.vel.y += acceleration.y * self.power

        self.head.pos.x += self.vel.x
        self.head.pos.y += self.vel.y

        node_overlap = 0.5
        for p, n in pairwise(self.segments):
            dist = distance(p.pos, n.pos)
            clip = dist - (p.radius + n.radius) * (1 - node_overlap)
            if clip > 0:
                n.pos.x += (p.pos.x - n.pos.x) / dist * clip
                n.pos.y += (p.pos.y - n.pos.y) / dist * clip

    def grow(self) -> None:
        last = self.segments[-1]
        self.segments.append(Segment(last.pos.copy(), 0))

        n = len(self.segments)
        for idx, segment in enumerate(self.segments):
            segment.radius = (n - idx) / n * self.head.radius

    def act(self, foods: list[Food]) -> None:
        closest_food = None
        closest_dist = float("inf")
        for food in foods:
            dist = distance(self.head.pos, food.pos)
            if dist < closest_dist:
                closest_food = food
                closest_dist = dist

        # Do not move if no food in sight
        if closest_food is None:
            return

        acceleration = Vec(
            (closest_food.pos.x - self.head.pos.x) / closest_dist * self.power,
            (closest_food.pos.y - self.head.pos.y) / closest_dist * self.power,
        )
        self.move(acceleration)


class Food:
    __slots__ = "pos", "radius"

    def __init__(self, pos: Vec, radius: int):
        self.pos = pos
        self.radius = radius

    def draw(self, window: pg.Surface) -> None:
        pg.draw.circle(window, "#bede87", self.pos.to_tuple(), self.radius)


class Simulation:
    def __init__(self, window_width: int, window_height: int, update_dt: float):
        self.update_dt = update_dt
        self.window_width = window_width
        self.window_height = window_height

        self.worm = Worm(
            pos=Vec(window_width // 2, window_height // 2),
            n_segments=0,
            radius=10,
        )
        self.foods: list[Food] = []

    def update(self, keys: pg.key.ScancodeWrapper) -> None:

        # Manual controls

        # acc = Vec(0, 0)

        # if keys[pg.K_w]:
        #     acc.y -= 1
        # if keys[pg.K_s]:
        #     acc.y += 1
        # if keys[pg.K_a]:
        #     acc.x -= 1
        # if keys[pg.K_d]:
        #     acc.x += 1

        # if acc.x != 0 and acc.y != 0:
        #     acc.x /= 1.41421356237
        #     acc.y /= 1.41421356237

        # self.worm.move(acc)

        # Automatic movement

        self.worm.act(self.foods)

        # Simulation boundaries

        if self.worm.head.pos.x < 0:
            self.worm.head.pos.x = 0
        elif self.worm.head.pos.x > WIDTH:
            self.worm.head.pos.x = WIDTH

        if self.worm.head.pos.y < 0:
            self.worm.head.pos.y = 0
        elif self.worm.head.pos.y > HEIGHT:
            self.worm.head.pos.y = HEIGHT

        # Food

        if random.random() < 0.02:
            self.foods.append(
                Food(
                    Vec(random.randint(0, WIDTH), random.randint(0, HEIGHT)),
                    radius=10,
                )
            )

        for food in self.foods:
            if (
                distance(self.worm.head.pos, food.pos)
                < self.worm.head.radius + food.radius
            ):
                self.foods.remove(food)
                self.worm.grow()
            else:
                food.radius -= 0.02
                if food.radius <= 0.1:
                    self.foods.remove(food)

    def draw(self, window: pg.Surface) -> None:
        window.fill("#9e7564")

        self.worm.draw(window)
        for food in self.foods:
            food.draw(window)


if __name__ == "__main__":
    WIDTH, HEIGHT = 1600, 900
    WINDOW_SIZE = (WIDTH, HEIGHT)
    TARGET_FPS = 120
    UPDATE_DT = 1.0 / 60.0

    pg.init()

    window = pg.display.set_mode(WINDOW_SIZE)
    pg.display.set_caption("Simulation")

    sim = Simulation(WIDTH, HEIGHT, UPDATE_DT)

    clock = pg.time.Clock()
    dt = 0.0

    running = True
    while running:

        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False

        dt += clock.tick(TARGET_FPS) / 1000.0
        while dt > UPDATE_DT:
            sim.update(pg.key.get_pressed())
            dt -= UPDATE_DT

        sim.draw(window)

        pg.display.update()

    pg.quit()
    sys.exit()
