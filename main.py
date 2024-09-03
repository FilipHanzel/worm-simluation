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

    def magnitude(self):
        return (self.x * self.x + self.y * self.y) ** 0.5

    @staticmethod
    def normalized(x: float | int, y: float | int) -> Vec:
        magnitute = (x * x + y * y) ** 0.5
        if magnitute == 0:
            return Vec(0, 0)
        return Vec(x / magnitute, y / magnitute)

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
    def __init__(self, pos: Vec, radius: int):

        # Body

        self.head = Segment(pos, radius)
        self.segments = [self.head]

        # Adjustable parameters

        self.base_size = radius

        self.power = 10.0
        self.drag = 0.04
        self.energy_efficiency = 0.99
        self.vision_range = 200

        self.body_thickness = 0.15
        self.body_size_multiplier = 3.0
        self.body_size_function_offset = 0.1
        self.head_color = "#f7786d"
        self.body_color = "#ffbc85"

        # State

        self.acc = Vec(0.0, 0.0)
        self.vel = Vec(0.0, 0.0)
        self.energy = 0.0

        # Initialization

        self.eat(1.0)

    def draw(self, window: pg.Surface) -> None:
        # fmt: off
        for segment in self.segments:
            pg.draw.circle(window, self.body_color, segment.pos.to_tuple(), segment.radius)
        pg.draw.circle(window, self.head_color, self.head.pos.to_tuple(), self.head.radius)

        pg.draw.circle(window, "#ffeeee", self.head.pos.to_tuple(), self.vision_range, 1)
        # fmt: on

    # Return False if entity should be removed from simulation
    def update(self, foods: list[Food], dt: float) -> bool:
        closest_food = None
        closest_dist = float("inf")
        for food in foods:
            dist = distance(self.head.pos, food.pos)

            if dist > self.vision_range:
                continue

            if dist < closest_dist:
                closest_food = food
                closest_dist = dist

        if closest_food is None:
            if random.random() < 0.05:
                self.acc = Vec.normalized(
                    (random.random() * 2 - 1),
                    (random.random() * 2 - 1),
                )
        else:
            self.acc = Vec(
                (closest_food.pos.x - self.head.pos.x) / closest_dist,
                (closest_food.pos.y - self.head.pos.y) / closest_dist,
            )

        self.move(dt)
        return self.energy > 0

    # Return False if entity should be removed from simulation
    def update_manual(self, keys: pg.key.ScancodeWrapper, dt: float) -> bool:
        x, y = 0, 0

        if keys[pg.K_w]:
            y -= 1.0
        if keys[pg.K_s]:
            y += 1.0
        if keys[pg.K_a]:
            x -= 1.0
        if keys[pg.K_d]:
            x += 1.0

        self.acc = Vec.normalized(x, y)
        self.move(dt)
        return self.energy > 0

    def move(self, dt: float) -> None:
        energy_drain = self.acc.magnitude() * (1.0 - self.energy_efficiency) * self.power * dt  # fmt: skip
        if energy_drain > self.energy:
            self.energy = 0.0

        self.burn(energy_drain)

        self.vel.x += self.acc.x * self.power * dt
        self.vel.y += self.acc.y * self.power * dt

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
        # Starting from a value slightly higher than 1.0
        # allows for the head (first node) to change size too,
        # for i == 1.0, head size will always be 1.0.
        i = 1.0 + self.body_size_function_offset

        # Calculate segment/body scale based on stored energy.
        # Adding small number to avoid zero division error,
        # multiplying by arbitrary factor to make body larger.
        scale = (self.energy + 0.001) * self.body_size_multiplier

        # Special case for head (first node) - don't go smaller than 1.0
        s = i ** (self.body_thickness - i / scale)
        s = max(s, 1.0)
        yield s

        while True:
            i += 1.0
            s = i ** (self.body_thickness - i / scale)

            # The threshold is arbitrary,
            # lower values give longer tail.
            if s < 0.5:
                break

            yield s

    def eat(self, energy: float) -> None:
        self.energy += energy

        # Worm can only grow after eating, so the number of segments
        # returned by generator will never exceed the number
        # of already instantiated segments.
        for segment, size in zip_longest(self.segments, self.segment_sizes):
            if segment is None:
                last = self.segments[-1]
                # It's fine to alter the list here, because when segment is None,
                # it means that we already stopped iterating over it.
                self.segments.append(Segment(last.pos.copy(), size * self.base_size))
            else:
                segment.radius = size * self.base_size

    def burn(self, energy: float) -> None:
        self.energy -= energy
        if self.energy < 0.0:
            self.energy = 0.0

        segments = []
        for segment, size in zip(self.segments, self.segment_sizes):
            segment.radius = size * self.base_size
            segments.append(segment)
        self.segments = segments


class Food:
    __slots__ = "pos", "radius"

    def __init__(self, pos: Vec, radius: float):
        self.pos = pos
        self.radius = radius

    # Return False if entity should be removed from simulation
    def update(self, dt: float) -> bool:
        self.radius -= 0.4 * dt
        return self.radius > 0.7

    def draw(self, window: pg.Surface) -> None:
        pg.draw.circle(window, "#bede87", self.pos.to_tuple(), self.radius)


class Virus:
    __slots__ = (
        "pos",
        "vel",
        "acc",
        "radius",
        "lifetime",
        "inactivity_time",
        "active",
        "power",
        "drag",
        "vision_range",
    )

    def __init__(self, pos: Vec, radius: float):
        self.pos = pos
        self.radius = radius

        self.power = 1.0
        self.drag = 0.02
        self.vision_range = 100

        self.acc = Vec(0, 0)
        self.vel = Vec(0, 0)

        self.lifetime = 0.0
        self.inactivity_time = 3.0
        self.active = False

    # Return False if entity should be removed from simulation
    def update(self, worms: list[Worm], dt: float) -> bool:
        self.lifetime += dt

        if not self.active:
            if self.lifetime > self.inactivity_time:
                self.active = True
            return True

        closest_worm = None
        closest_dist = float("inf")
        for worm in worms:
            dist = distance(self.pos, worm.head.pos)

            if dist > self.vision_range:
                continue

            if dist < closest_dist:
                closest_worm = worm
                closest_dist = dist

        if closest_worm is not None:
            self.acc = Vec(
                (closest_worm.head.pos.x - self.pos.x) / closest_dist * self.power * dt,
                (closest_worm.head.pos.y - self.pos.y) / closest_dist * self.power * dt,
            )
            self.move()

        self.radius -= 0.2 * dt
        return self.radius > 0.7

    def draw(self, window: pg.Surface) -> None:
        color = "#e33636" if self.active else "#949494"
        pg.draw.circle(window, color, self.pos.to_tuple(), self.radius)

    def move(self) -> None:
        self.vel.x += self.acc.x
        self.vel.y += self.acc.y

        self.vel.x *= 1.0 - self.drag
        self.vel.y *= 1.0 - self.drag

        self.pos.x += self.vel.x
        self.pos.y += self.vel.y


class Simulation:
    def __init__(self, window_width: int, window_height: int, update_dt: float):
        self.update_dt = update_dt
        self.window_width = window_width
        self.window_height = window_height

        self.manual_control = True

        self.worm = Worm(
            pos=Vec(window_width // 2, window_height // 2),
            radius=10,
        )
        self.foods: list[Food] = []
        self.viruses: list[Virus] = []

        self.font_size = 18
        self.font = pg.font.SysFont("Arial", self.font_size)

    def handle_event(self, event: pg.event.Event) -> None:
        if event.type == pg.KEYDOWN and event.unicode == " ":
            self.manual_control = not self.manual_control

    def update(self, keys: pg.key.ScancodeWrapper) -> None:

        # Movement

        if self.manual_control:
            is_alive = self.worm.update_manual(keys, self.update_dt)
        else:
            is_alive = self.worm.update(self.foods, self.update_dt)

        # Death

        if not is_alive:
            self.worm = Worm(
                pos=Vec(self.window_width // 2, self.window_height // 2),
                radius=10,
            )

        # Simulation boundaries

        if self.worm.head.pos.x < 0:
            self.worm.head.pos.x = 0
        elif self.worm.head.pos.x > self.window_width:
            self.worm.head.pos.x = self.window_width

        if self.worm.head.pos.y < 0:
            self.worm.head.pos.y = 0
        elif self.worm.head.pos.y > self.window_height:
            self.worm.head.pos.y = self.window_height

        # Other entities

        if random.random() < 0.02:
            pos = Vec(
                random.randint(0, self.window_width),
                random.randint(0, self.window_height),
            )
            self.foods.append(Food(pos, radius=10))

        if random.random() < 0.03:
            pos = Vec(
                random.randint(0, self.window_width),
                random.randint(0, self.window_height),
            )
            self.viruses.append(Virus(pos, radius=7))

        for food in self.foods:
            dist = distance(self.worm.head.pos, food.pos)
            if dist < self.worm.head.radius + food.radius:
                self.foods.remove(food)
                self.worm.eat(energy=0.1)
            else:
                if not food.update(self.update_dt):
                    self.foods.remove(food)

        for virus in self.viruses:
            dist = distance(self.worm.head.pos, virus.pos)
            if virus.active and dist < self.worm.head.radius + virus.radius:
                self.viruses.remove(virus)
                self.worm.burn(0.1)
            else:
                if not virus.update([self.worm], self.update_dt):
                    self.viruses.remove(virus)

    def draw(self, window: pg.Surface) -> None:
        window.fill("#9e7564")

        for food in self.foods:
            food.draw(window)

        for virus in self.viruses:
            virus.draw(window)

        self.worm.draw(window)

        window.blit(self.font.render(f"Manual control: {self.manual_control}", True, (255, 255, 255)), (0, self.font_size * 0))  # fmt: skip
        window.blit(self.font.render(f"Energy: {self.worm.energy:.2f}", True, (255, 255, 255)), (0, self.font_size * 1))  # fmt: skip


if __name__ == "__main__":
    WIDTH, HEIGHT = 1600, 900
    TARGET_FPS = 60
    UPDATE_DT = 1.0 / 60.0

    pg.init()
    pg.font.init()

    window = pg.display.set_mode((WIDTH, HEIGHT))
    pg.display.set_caption("Simulation")

    sim = Simulation(WIDTH, HEIGHT, UPDATE_DT)

    clock = pg.time.Clock()
    dt = 0.0

    running = True
    while running:

        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            else:
                sim.handle_event(event)

        dt += clock.tick(TARGET_FPS) / 1000.0
        while dt > UPDATE_DT:
            sim.update(pg.key.get_pressed())
            dt -= UPDATE_DT

        sim.draw(window)

        pg.display.update()

    pg.quit()
    sys.exit()
