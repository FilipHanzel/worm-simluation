from __future__ import annotations

import random
import sys
from itertools import pairwise, zip_longest
from math import sqrt
from typing import Iterator

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
    __slots__ = "pos", "radius"

    def __init__(self, pos: Vec, radius: int):
        self.pos = pos
        self.radius = radius


class Worm:
    def __init__(self, pos: Vec, n_segments: int, radius: int):
        self.head = Segment(pos, radius)
        self.segments = [self.head]

        self.power = 4.0
        self.drag = 0.04

        self.vel = Vec(0, 0)

        self.base_size = radius
        self.energy = 0.0
        self.eat(1.0)

        self.head_color = "#f7786d"
        self.body_color = "#ffbc85"

    def draw(self, window: pg.Surface) -> None:
        for segment in self.segments:
            pg.draw.circle(window, self.body_color, segment.pos.to_tuple(), segment.radius)  # fmt: skip
        pg.draw.circle(window, self.head_color, self.head.pos.to_tuple(), self.head.radius)  # fmt: skip

    def move(self, acceleration: Vec) -> None:
        self.vel.x += acceleration.x * self.power
        self.vel.y += acceleration.y * self.power

        self.vel.x *= 1.0 - self.drag
        self.vel.y *= 1.0 - self.drag

        self.head.pos.x += self.vel.x
        self.head.pos.y += self.vel.y

        node_overlap = 0.5
        for p, n in pairwise(self.segments):
            dist = distance(p.pos, n.pos)
            clip = dist - (p.radius + n.radius) * (1 - node_overlap)
            if clip > 0:
                n.pos.x += (p.pos.x - n.pos.x) / dist * clip
                n.pos.y += (p.pos.y - n.pos.y) / dist * clip

    @property
    def segment_sizes(self) -> Iterator[float]:
        # Starting from a value slightly higher than 1
        # allows for the head (first node) to change size too.
        i = 1.01
        while True:
            s = i ** (0.15 - i / self.energy)
            i += 1

            yield s

            # The threshold is arbitrary,
            # lower values give longer tail.
            if s < 0.5:
                break

    def eat(self, energy: float) -> None:
        self.energy += energy

        # For now I'm assuming that worm can only grow, so the number
        # of segments returned by generator will never exceed the number
        # of already instantiated segments.
        for segment, size in zip_longest(self.segments, self.segment_sizes):
            if segment is None:
                last = self.segments[-1]
                # It's fine to alter the list here, because when segment is None,
                # it means that we already stopped iterating over it.
                self.segments.append(Segment(last.pos.copy(), size * self.base_size))
            else:
                segment.radius = size * self.base_size

    def update(self, foods: list[Food], dt: float) -> None:
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
            (closest_food.pos.x - self.head.pos.x) / closest_dist * self.power * dt,
            (closest_food.pos.y - self.head.pos.y) / closest_dist * self.power * dt,
        )
        self.move(acceleration)


class Food:
    __slots__ = "pos", "radius"

    def __init__(self, pos: Vec, radius: int):
        self.pos = pos
        self.radius = radius

    # Return false if entity should be removed from simulation
    def update(self, dt: float) -> bool:
        self.radius -= 0.4 * dt
        return self.radius > 0.1

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

        # acc.x = acc.x * self.worm.power * dt
        # acc.y = acc.y * self.worm.power * dt

        # self.worm.move(acc)

        # Automatic movement

        self.worm.update(self.foods, self.update_dt)

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

        if random.random() < 0.04:
            pos = Vec(random.randint(0, WIDTH), random.randint(0, HEIGHT))
            self.foods.append(Food(pos, radius=10))

        for food in self.foods:
            dist = distance(self.worm.head.pos, food.pos)
            if dist < self.worm.head.radius + food.radius:
                self.foods.remove(food)
                self.worm.eat(energy=1.0)
            else:
                if not food.update(self.update_dt):
                    self.foods.remove(food)

    def draw(self, window: pg.Surface) -> None:
        window.fill("#9e7564")

        self.worm.draw(window)
        for food in self.foods:
            food.draw(window)


if __name__ == "__main__":
    WIDTH, HEIGHT = 1600, 900
    WINDOW_SIZE = (WIDTH, HEIGHT)
    TARGET_FPS = 60
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
