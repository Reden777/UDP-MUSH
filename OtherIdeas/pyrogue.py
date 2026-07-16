#!/usr/bin/env python3
"""
PyRogue - A NetHack-inspired roguelike in Python.
Run in a terminal: python pyrogue.py
Requires: Python 3.7+, a terminal that supports curses (Linux/macOS/WSL)
"""

import curses
import random
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
from enum import Enum, auto
from copy import deepcopy

# === CONSTANTS ===
MAP_WIDTH = 80
MAP_HEIGHT = 40
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 24
VIEWPORT_WIDTH = 80
VIEWPORT_HEIGHT = 18
MSG_HEIGHT = 3
STAT_HEIGHT = 3
MAX_ROOMS = 9
ROOM_MIN_SIZE = 5
ROOM_MAX_SIZE = 12
MAX_MONSTERS_PER_ROOM = 3
MAX_ITEMS_PER_ROOM = 2
FOV_RADIUS = 8
MAX_DUNGEON_LEVEL = 10


# === ENUMS ===
class TileType(Enum):
    WALL = auto()
    FLOOR = auto()
    CORRIDOR = auto()
    DOOR = auto()
    STAIRS_DOWN = auto()
    STAIRS_UP = auto()


class ItemType(Enum):
    WEAPON = auto()
    ARMOR = auto()
    POTION = auto()
    SCROLL = auto()
    FOOD = auto()
    GOLD = auto()
    AMULET = auto()


class MonsterState(Enum):
    SLEEPING = auto()
    WANDERING = auto()
    HUNTING = auto()


# === DATA CLASSES ===
@dataclass
class Tile:
    tile_type: TileType = TileType.WALL
    explored: bool = False
    visible: bool = False
    blocked: bool = True
    block_sight: bool = True

    def __post_init__(self):
        if self.tile_type in (TileType.FLOOR, TileType.CORRIDOR, TileType.DOOR,
                              TileType.STAIRS_DOWN, TileType.STAIRS_UP):
            self.blocked = False
            self.block_sight = False
        if self.tile_type == TileType.DOOR:
            self.block_sight = False


@dataclass
class Rect:
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def center(self) -> Tuple[int, int]:
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    def intersects(self, other: 'Rect') -> bool:
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and
                self.y1 <= other.y2 and self.y2 >= other.y1)


@dataclass
class Item:
    name: str
    item_type: ItemType
    char: str
    color: int = 0
    attack_bonus: int = 0
    defense_bonus: int = 0
    heal_amount: int = 0
    damage_dice: Tuple[int, int] = (1, 4)
    gold_amount: int = 0
    nutrition: int = 0
    description: str = ""
    equipped: bool = False


@dataclass
class Monster:
    name: str
    char: str
    color: int
    x: int = 0
    y: int = 0
    hp: int = 10
    max_hp: int = 10
    attack: int = 2
    defense: int = 0
    xp_value: int = 10
    speed: int = 10
    state: MonsterState = MonsterState.SLEEPING
    move_timer: int = 0
    level: int = 1

    def is_alive(self) -> bool:
        return self.hp > 0


@dataclass
class Player:
    x: int = 0
    y: int = 0
    hp: int = 20
    max_hp: int = 20
    mp: int = 10
    max_mp: int = 10
    attack: int = 5
    defense: int = 2
    level: int = 1
    xp: int = 0
    xp_to_next: int = 20
    gold: int = 0
    nutrition: int = 900
    max_nutrition: int = 1500
    turns: int = 0
    dungeon_level: int = 1
    inventory: List[Item] = field(default_factory=list)
    equipped_weapon: Optional[Item] = None
    equipped_armor: Optional[Item] = None
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10

    @property
    def total_attack(self) -> int:
        bonus = self.equipped_weapon.attack_bonus if self.equipped_weapon else 0
        return self.attack + bonus

    @property
    def total_defense(self) -> int:
        bonus = self.equipped_armor.defense_bonus if self.equipped_armor else 0
        return self.defense + bonus

    def is_alive(self) -> bool:
        return self.hp > 0


# === ITEM DEFINITIONS ===
def get_weapon_pool(dlevel: int) -> List[Item]:
    weapons = [
        Item("dagger", ItemType.WEAPON, ')', attack_bonus=1, damage_dice=(1, 4),
             description="A small but sharp dagger."),
        Item("short sword", ItemType.WEAPON, ')', attack_bonus=3, damage_dice=(1, 6),
             description="A reliable short sword."),
        Item("mace", ItemType.WEAPON, ')', attack_bonus=4, damage_dice=(1, 8),
             description="A heavy iron mace."),
        Item("long sword", ItemType.WEAPON, ')', attack_bonus=5, damage_dice=(2, 6),
             description="A finely crafted long sword."),
        Item("battle axe", ItemType.WEAPON, ')', attack_bonus=7, damage_dice=(2, 8),
             description="A fearsome battle axe."),
        Item("two-handed sword", ItemType.WEAPON, ')', attack_bonus=10, damage_dice=(3, 6),
             description="A massive two-handed sword."),
    ]
    max_idx = min(len(weapons), 2 + dlevel // 2)
    return weapons[:max_idx]


def get_armor_pool(dlevel: int) -> List[Item]:
    armors = [
        Item("leather armor", ItemType.ARMOR, '[', defense_bonus=2,
             description="Basic leather protection."),
        Item("ring mail", ItemType.ARMOR, '[', defense_bonus=3,
             description="Interlocking ring armor."),
        Item("chain mail", ItemType.ARMOR, '[', defense_bonus=5,
             description="Sturdy chain mail armor."),
        Item("plate mail", ItemType.ARMOR, '[', defense_bonus=7,
             description="Heavy plate mail armor."),
        Item("crystal plate mail", ItemType.ARMOR, '[', defense_bonus=10,
             description="Legendary crystal armor."),
    ]
    max_idx = min(len(armors), 1 + dlevel // 2)
    return armors[:max_idx]


def get_potion_pool() -> List[Item]:
    return [
        Item("potion of healing", ItemType.POTION, '!', heal_amount=15,
             description="Restores 15 HP."),
        Item("potion of greater healing", ItemType.POTION, '!', heal_amount=30,
             description="Restores 30 HP."),
        Item("potion of full healing", ItemType.POTION, '!', heal_amount=99,
             description="Fully restores HP."),
    ]


def get_scroll_pool() -> List[Item]:
    return [
        Item("scroll of teleportation", ItemType.SCROLL, '?',
             description="Teleports you randomly."),
        Item("scroll of magic mapping", ItemType.SCROLL, '?',
             description="Reveals the entire level."),
        Item("scroll of enchant weapon", ItemType.SCROLL, '?',
             description="Enhances your weapon."),
    ]


def get_food_pool() -> List[Item]:
    return [
        Item("food ration", ItemType.FOOD, '%', nutrition=800,
             description="A filling meal."),
        Item("apple", ItemType.FOOD, '%', nutrition=200,
             description="A fresh apple."),
    ]


# === MONSTER DEFINITIONS ===
def get_monster_pool(dlevel: int) -> List[dict]:
    monsters = [
        # Level 1-3
        {"name": "rat", "char": "r", "hp": 4, "attack": 1, "defense": 0,
         "xp_value": 5, "speed": 12, "level": 1, "min_dlevel": 1},
        {"name": "bat", "char": "B", "hp": 5, "attack": 2, "defense": 0,
         "xp_value": 7, "speed": 15, "level": 1, "min_dlevel": 1},
        {"name": "kobold", "char": "k", "hp": 8, "attack": 3, "defense": 1,
         "xp_value": 10, "speed": 10, "level": 2, "min_dlevel": 1},
        # Level 3-5
        {"name": "goblin", "char": "g", "hp": 12, "attack": 4, "defense": 2,
         "xp_value": 15, "speed": 10, "level": 3, "min_dlevel": 2},
        {"name": "orc", "char": "o", "hp": 18, "attack": 5, "defense": 3,
         "xp_value": 25, "speed": 8, "level": 4, "min_dlevel": 3},
        {"name": "zombie", "char": "Z", "hp": 22, "attack": 4, "defense": 2,
         "xp_value": 20, "speed": 6, "level": 3, "min_dlevel": 3},
        # Level 5-7
        {"name": "ogre", "char": "O", "hp": 30, "attack": 7, "defense": 4,
         "xp_value": 40, "speed": 7, "level": 5, "min_dlevel": 4},
        {"name": "troll", "char": "T", "hp": 40, "attack": 8, "defense": 5,
         "xp_value": 60, "speed": 8, "level": 6, "min_dlevel": 5},
        {"name": "wraith", "char": "W", "hp": 25, "attack": 9, "defense": 3,
         "xp_value": 50, "speed": 12, "level": 6, "min_dlevel": 5},
        # Level 7-10
        {"name": "dragon", "char": "D", "hp": 60, "attack": 12, "defense": 8,
         "xp_value": 100, "speed": 9, "level": 8, "min_dlevel": 7},
        {"name": "demon", "char": "&", "hp": 50, "attack": 14, "defense": 6,
         "xp_value": 120, "speed": 11, "level": 9, "min_dlevel": 8},
        {"name": "lich", "char": "L", "hp": 45, "attack": 15, "defense": 5,
         "xp_value": 150, "speed": 10, "level": 10, "min_dlevel": 9},
    ]
    return [m for m in monsters if m["min_dlevel"] <= dlevel]


# === DUNGEON GENERATION ===
class DungeonLevel:
    def __init__(self, width: int, height: int, level: int):
        self.width = width
        self.height = height
        self.level = level
        self.tiles: List[List[Tile]] = [[Tile() for _ in range(width)] for _ in range(height)]
        self.rooms: List[Rect] = []
        self.monsters: List[Monster] = []
        self.items: List[Tuple[int, int, Item]] = []
        self.stairs_down: Optional[Tuple[int, int]] = None
        self.stairs_up: Optional[Tuple[int, int]] = None
        self.generate()

    def generate(self):
        for _ in range(30):
            w = random.randint(ROOM_MIN_SIZE, ROOM_MAX_SIZE)
            h = random.randint(ROOM_MIN_SIZE, ROOM_MAX_SIZE)
            x = random.randint(1, self.width - w - 1)
            y = random.randint(1, self.height - h - 1)
            new_room = Rect(x, y, x + w - 1, y + h - 1)

            if any(new_room.intersects(Rect(r.x1 - 1, r.y1 - 1, r.x2 + 1, r.y2 + 1))
                   for r in self.rooms):
                continue

            self._carve_room(new_room)
            if self.rooms:
                self._connect_rooms(self.rooms[-1], new_room)
            self.rooms.append(new_room)

            if len(self.rooms) >= MAX_ROOMS:
                break

        if len(self.rooms) < 2:
            # Ensure at least 2 rooms
            self.tiles = [[Tile() for _ in range(self.width)] for _ in range(self.height)]
            self.rooms = []
            r1 = Rect(2, 2, 12, 10)
            r2 = Rect(20, 5, 30, 12)
            self._carve_room(r1)
            self._carve_room(r2)
            self._connect_rooms(r1, r2)
            self.rooms = [r1, r2]

        # Place stairs
        up_room = self.rooms[0]
        self.stairs_up = up_room.center
        sx, sy = self.stairs_up
        self.tiles[sy][sx].tile_type = TileType.STAIRS_UP

        down_room = self.rooms[-1]
        self.stairs_down = down_room.center
        sx, sy = self.stairs_down
        self.tiles[sy][sx].tile_type = TileType.STAIRS_DOWN

        # Place monsters and items
        self._place_monsters()
        self._place_items()

    def _carve_room(self, room: Rect):
        for y in range(room.y1, room.y2 + 1):
            for x in range(room.x1, room.x2 + 1):
                self.tiles[y][x] = Tile(TileType.FLOOR)

    def _connect_rooms(self, room1: Rect, room2: Rect):
        x1, y1 = room1.center
        x2, y2 = room2.center

        if random.random() < 0.5:
            self._carve_h_tunnel(x1, x2, y1)
            self._carve_v_tunnel(y1, y2, x2)
        else:
            self._carve_v_tunnel(y1, y2, x1)
            self._carve_h_tunnel(x1, x2, y2)

    def _carve_h_tunnel(self, x1: int, x2: int, y: int):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            if 0 <= y < self.height and 0 <= x < self.width:
                if self.tiles[y][x].tile_type == TileType.WALL:
                    self.tiles[y][x] = Tile(TileType.CORRIDOR)

    def _carve_v_tunnel(self, y1: int, y2: int, x: int):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            if 0 <= y < self.height and 0 <= x < self.width:
                if self.tiles[y][x].tile_type == TileType.WALL:
                    self.tiles[y][x] = Tile(TileType.CORRIDOR)

    def _place_monsters(self):
        pool = get_monster_pool(self.level)
        if not pool:
            return

        for room in self.rooms[1:]:  # Skip first room (player start)
            num_monsters = random.randint(0, MAX_MONSTERS_PER_ROOM)
            for _ in range(num_monsters):
                x = random.randint(room.x1 + 1, room.x2 - 1)
                y = random.randint(room.y1 + 1, room.y2 - 1)

                if any(m.x == x and m.y == y for m in self.monsters):
                    continue

                template = random.choice(pool)
                # Scale slightly with depth
                hp_bonus = random.randint(0, self.level)
                monster = Monster(
                    name=template["name"],
                    char=template["char"],
                    color=self._monster_color(template["char"]),
                    x=x, y=y,
                    hp=template["hp"] + hp_bonus,
                    max_hp=template["hp"] + hp_bonus,
                    attack=template["attack"],
                    defense=template["defense"],
                    xp_value=template["xp_value"],
                    speed=template["speed"],
                    level=template["level"],
                    state=random.choice([MonsterState.SLEEPING, MonsterState.WANDERING])
                )
                self.monsters.append(monster)

    def _monster_color(self, char: str) -> int:
        color_map = {
            'r': 3, 'B': 5, 'k': 2, 'g': 2, 'o': 2,
            'Z': 7, 'O': 3, 'T': 2, 'W': 6, 'D': 1,
            '&': 1, 'L': 5
        }
        return color_map.get(char, 7)

    def _place_items(self):
        for room in self.rooms:
            num_items = random.randint(0, MAX_ITEMS_PER_ROOM)
            for _ in range(num_items):
                x = random.randint(room.x1 + 1, room.x2 - 1)
                y = random.randint(room.y1 + 1, room.y2 - 1)

                if any(ix == x and iy == y for ix, iy, _ in self.items):
                    continue

                item = self._random_item()
                self.items.append((x, y, item))

            # Always some gold
            if random.random() < 0.5:
                x = random.randint(room.x1 + 1, room.x2 - 1)
                y = random.randint(room.y1 + 1, room.y2 - 1)
                gold = Item("gold pieces", ItemType.GOLD, '$',
                           gold_amount=random.randint(5, 20 + self.level * 10))
                self.items.append((x, y, gold))

    def _random_item(self) -> Item:
        roll = random.random()
        if roll < 0.25:
            return deepcopy(random.choice(get_weapon_pool(self.level)))
        elif roll < 0.45:
            return deepcopy(random.choice(get_armor_pool(self.level)))
        elif roll < 0.7:
            return deepcopy(random.choice(get_potion_pool()))
        elif roll < 0.85:
            return deepcopy(random.choice(get_scroll_pool()))
        else:
            return deepcopy(random.choice(get_food_pool()))

    def is_blocked(self, x: int, y: int) -> bool:
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return True
        return self.tiles[y][x].blocked

    def get_monster_at(self, x: int, y: int) -> Optional[Monster]:
        for m in self.monsters:
            if m.x == x and m.y == y and m.is_alive():
                return m
        return None


# === FIELD OF VIEW ===
def compute_fov(dungeon: DungeonLevel, px: int, py: int, radius: int):
    # Reset visibility
    for y in range(dungeon.height):
        for x in range(dungeon.width):
            dungeon.tiles[y][x].visible = False

    # Raycasting FOV
    for angle in range(360):
        rad = math.radians(angle)
        dx = math.cos(rad)
        dy = math.sin(rad)

        x, y = float(px), float(py)
        for _ in range(radius):
            ix, iy = int(round(x)), int(round(y))
            if ix < 0 or ix >= dungeon.width or iy < 0 or iy >= dungeon.height:
                break
            dungeon.tiles[iy][ix].visible = True
            dungeon.tiles[iy][ix].explored = True
            if dungeon.tiles[iy][ix].block_sight and (ix != px or iy != py):
                break
            x += dx * 0.5
            y += dy * 0.5


# === GAME CLASS ===
class Game:
    def __init__(self):
        self.player = Player()
        self.dungeons: Dict[int, DungeonLevel] = {}
        self.messages: List[Tuple[str, int]] = []
        self.game_over = False
        self.victory = False
        self.running = True
        self.look_mode = False
        self.look_x = 0
        self.look_y = 0

        # Generate first level
        self._generate_level(1)
        dungeon = self.current_dungeon
        self.player.x, self.player.y = dungeon.stairs_up
        self.message("Welcome to PyRogue! Find the Amulet of Yendor on level 10!", 3)
        self.message("Press '?' for help.", 6)

    @property
    def current_dungeon(self) -> DungeonLevel:
        return self.dungeons[self.player.dungeon_level]

    def _generate_level(self, level: int):
        if level not in self.dungeons:
            self.dungeons[level] = DungeonLevel(MAP_WIDTH, MAP_HEIGHT, level)
            # Place the Amulet on level 10
            if level == MAX_DUNGEON_LEVEL:
                dungeon = self.dungeons[level]
                room = random.choice(dungeon.rooms[1:]) if len(dungeon.rooms) > 1 else dungeon.rooms[0]
                x = random.randint(room.x1 + 1, room.x2 - 1)
                y = random.randint(room.y1 + 1, room.y2 - 1)
                amulet = Item("the Amulet of Yendor", ItemType.AMULET, '"',
                             color=3, description="The legendary Amulet! Ascend to win!")
                dungeon.items.append((x, y, amulet))

    def message(self, text: str, color: int = 7):
        self.messages.append((text, color))
        if len(self.messages) > 100:
            self.messages.pop(0)

    def roll_dice(self, num: int, sides: int) -> int:
        return sum(random.randint(1, sides) for _ in range(num))

    # === PLAYER ACTIONS ===
    def move_player(self, dx: int, dy: int):
        nx, ny = self.player.x + dx, self.player.y + dy
        dungeon = self.current_dungeon

        # Attack monster?
        monster = dungeon.get_monster_at(nx, ny)
        if monster:
            self.attack_monster(monster)
            self._end_turn()
            return

        if not dungeon.is_blocked(nx, ny):
            self.player.x, self.player.y = nx, ny
            self._end_turn()
            # Auto-pickup gold
            self._auto_pickup()
        else:
            self.message("You bump into a wall.", 7)

    def _auto_pickup(self):
        dungeon = self.current_dungeon
        px, py = self.player.x, self.player.y
        to_remove = []
        for i, (ix, iy, item) in enumerate(dungeon.items):
            if ix == px and iy == py and item.item_type == ItemType.GOLD:
                self.player.gold += item.gold_amount
                self.message(f"You pick up {item.gold_amount} gold pieces.", 3)
                to_remove.append(i)
        for i in reversed(to_remove):
            dungeon.items.pop(i)

    def pickup_item(self):
        dungeon = self.current_dungeon
        px, py = self.player.x, self.player.y
        for i, (ix, iy, item) in enumerate(dungeon.items):
            if ix == px and iy == py:
                if item.item_type == ItemType.GOLD:
                    self.player.gold += item.gold_amount
                    self.message(f"You pick up {item.gold_amount} gold pieces.", 3)
                else:
                    if len(self.player.inventory) >= 20:
                        self.message("Your inventory is full!", 1)
                        return
                    self.player.inventory.append(item)
                    self.message(f"You pick up {item.name}.", 6)
                dungeon.items.pop(i)
                self._end_turn()
                return
        self.message("There's nothing here to pick up.", 7)

    def attack_monster(self, monster: Monster):
        # Calculate hit
        hit_roll = random.randint(1, 20) + self.player.level
        if hit_roll >= 10 + monster.defense:
            if self.player.equipped_weapon:
                d_num, d_sides = self.player.equipped_weapon.damage_dice
                damage = self.roll_dice(d_num, d_sides) + self.player.total_attack // 2
            else:
                damage = self.roll_dice(1, 4) + self.player.total_attack // 3
            damage = max(1, damage - monster.defense // 2)
            monster.hp -= damage
            self.message(f"You hit the {monster.name} for {damage} damage!", 2)
            if not monster.is_alive():
                self.message(f"You killed the {monster.name}!", 2)
                self.player.xp += monster.xp_value
                self._check_level_up()
        else:
            self.message(f"You miss the {monster.name}.", 7)
        monster.state = MonsterState.HUNTING

    def _check_level_up(self):
        while self.player.xp >= self.player.xp_to_next:
            self.player.xp -= self.player.xp_to_next
            self.player.level += 1
            self.player.xp_to_next = int(self.player.xp_to_next * 1.5)
            hp_gain = random.randint(3, 8) + self.player.constitution // 5
            self.player.max_hp += hp_gain
            self.player.hp += hp_gain
            self.player.attack += 1
            self.player.defense += 1
            self.message(f"Welcome to level {self.player.level}! You feel stronger!", 3)

    def use_stairs(self, going_down: bool):
        dungeon = self.current_dungeon
        px, py = self.player.x, self.player.y
        tile = dungeon.tiles[py][px].tile_type

        if going_down:
            if tile != TileType.STAIRS_DOWN:
                self.message("There are no stairs going down here.", 7)
                return
            if self.player.dungeon_level >= MAX_DUNGEON_LEVEL:
                self.message("You cannot go deeper!", 1)
                return
            self.player.dungeon_level += 1
            self._generate_level(self.player.dungeon_level)
            new_dungeon = self.current_dungeon
            self.player.x, self.player.y = new_dungeon.stairs_up
            self.message(f"You descend to dungeon level {self.player.dungeon_level}.", 5)
        else:
            if tile != TileType.STAIRS_UP:
                self.message("There are no stairs going up here.", 7)
                return
            if self.player.dungeon_level <= 1:
                # Check for Amulet
                has_amulet = any(i.item_type == ItemType.AMULET for i in self.player.inventory)
                if has_amulet:
                    self.victory = True
                    self.game_over = True
                    self.message("You escape with the Amulet of Yendor! YOU WIN!", 3)
                else:
                    self.message("You can't leave without the Amulet of Yendor!", 3)
                return
            self.player.dungeon_level -= 1
            new_dungeon = self.current_dungeon
            self.player.x, self.player.y = new_dungeon.stairs_down
            self.message(f"You ascend to dungeon level {self.player.dungeon_level}.", 5)

        self._end_turn()

    def use_item(self, item: Item):
        if item.item_type == ItemType.POTION:
            heal = item.heal_amount
            self.player.hp = min(self.player.max_hp, self.player.hp + heal)
            self.message(f"You drink the {item.name}. You feel better! (+{heal} HP)", 2)
            self.player.inventory.remove(item)
            self._end_turn()
        elif item.item_type == ItemType.SCROLL:
            self._use_scroll(item)
            self.player.inventory.remove(item)
            self._end_turn()
        elif item.item_type == ItemType.FOOD:
            self.player.nutrition = min(self.player.max_nutrition,
                                       self.player.nutrition + item.nutrition)
            self.message(f"You eat the {item.name}. Delicious!", 2)
            self.player.inventory.remove(item)
            self._end_turn()
        elif item.item_type == ItemType.WEAPON:
            self._equip_weapon(item)
        elif item.item_type == ItemType.ARMOR:
            self._equip_armor(item)

    def _use_scroll(self, scroll: Item):
        if "teleportation" in scroll.name:
            dungeon = self.current_dungeon
            room = random.choice(dungeon.rooms)
            self.player.x = random.randint(room.x1 + 1, room.x2 - 1)
            self.player.y = random.randint(room.y1 + 1, room.y2 - 1)
            self.message("You feel disoriented... you've been teleported!", 5)
        elif "magic mapping" in scroll.name:
            dungeon = self.current_dungeon
            for y in range(dungeon.height):
                for x in range(dungeon.width):
                    dungeon.tiles[y][x].explored = True
            self.message("A map forms in your mind!", 5)
        elif "enchant weapon" in scroll.name:
            if self.player.equipped_weapon:
                self.player.equipped_weapon.attack_bonus += 2
                self.message(f"Your {self.player.equipped_weapon.name} glows brightly!", 3)
            else:
                self.message("You feel a tingle in your hands.", 7)

    def _equip_weapon(self, item: Item):
        if self.player.equipped_weapon:
            self.player.equipped_weapon.equipped = False
        self.player.equipped_weapon = item
        item.equipped = True
        self.message(f"You wield the {item.name}.", 6)
        self._end_turn()

    def _equip_armor(self, item: Item):
        if self.player.equipped_armor:
            self.player.equipped_armor.equipped = False
        self.player.equipped_armor = item
        item.equipped = True
        self.message(f"You put on the {item.name}.", 6)
        self._end_turn()

    def drop_item(self, item: Item):
        if item.equipped:
            if item == self.player.equipped_weapon:
                self.player.equipped_weapon = None
            elif item == self.player.equipped_armor:
                self.player.equipped_armor = None
            item.equipped = False
        self.player.inventory.remove(item)
        self.current_dungeon.items.append((self.player.x, self.player.y, item))
        self.message(f"You drop the {item.name}.", 7)
        self._end_turn()

    # === MONSTER AI ===
    def _process_monsters(self):
        dungeon = self.current_dungeon
        for monster in dungeon.monsters:
            if not monster.is_alive():
                continue

            # Wake up if player is nearby
            dist = math.sqrt((monster.x - self.player.x) ** 2 +
                           (monster.y - self.player.y) ** 2)
            if dist <= FOV_RADIUS and monster.state == MonsterState.SLEEPING:
                if random.random() < 0.3:
                    monster.state = MonsterState.HUNTING

            if monster.state == MonsterState.SLEEPING:
                continue

            if dist <= 1.5:
                # Melee attack
                self._monster_attack(monster)
            elif monster.state == MonsterState.HUNTING and dist <= FOV_RADIUS + 3:
                self._monster_move_toward_player(monster)
            elif monster.state == MonsterState.WANDERING:
                self._monster_wander(monster)

    def _monster_attack(self, monster: Monster):
        hit_roll = random.randint(1, 20) + monster.level
        if hit_roll >= 8 + self.player.total_defense:
            damage = max(1, monster.attack - self.player.total_defense // 3 +
                        random.randint(-1, 2))
            self.player.hp -= damage
            self.message(f"The {monster.name} hits you for {damage} damage!", 1)
            if not self.player.is_alive():
                self.game_over = True
                self.message(f"You have been killed by the {monster.name}...", 1)
        else:
            self.message(f"The {monster.name} misses you.", 7)

    def _monster_move_toward_player(self, monster: Monster):
        dx = self.player.x - monster.x
        dy = self.player.y - monster.y
        dist = max(abs(dx), abs(dy), 1)
        dx = int(round(dx / dist))
        dy = int(round(dy / dist))

        nx, ny = monster.x + dx, monster.y + dy
        dungeon = self.current_dungeon
        if not dungeon.is_blocked(nx, ny) and not dungeon.get_monster_at(nx, ny):
            if not (nx == self.player.x and ny == self.player.y):
                monster.x, monster.y = nx, ny
        else:
            # Try alternate moves
            for adx, ady in [(dx, 0), (0, dy), (dy, dx), (-dy, -dx)]:
                if adx == 0 and ady == 0:
                    continue
                nx, ny = monster.x + adx, monster.y + ady
                if (not dungeon.is_blocked(nx, ny) and
                    not dungeon.get_monster_at(nx, ny) and
                    not (nx == self.player.x and ny == self.player.y)):
                    monster.x, monster.y = nx, ny
                    break

    def _monster_wander(self, monster: Monster):
        if random.random() < 0.3:
            dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
            nx, ny = monster.x + dx, monster.y + dy
            dungeon = self.current_dungeon
            if (not dungeon.is_blocked(nx, ny) and
                not dungeon.get_monster_at(nx, ny) and
                not (nx == self.player.x and ny == self.player.y)):
                monster.x, monster.y = nx, ny

    def _end_turn(self):
        self.player.turns += 1
        self.player.nutrition -= 1
        if self.player.nutrition <= 0:
            self.player.hp -= 1
            if self.player.turns % 5 == 0:
                self.message("You are starving!", 1)
            if not self.player.is_alive():
                self.game_over = True
                self.message("You starved to death...", 1)
        elif self.player.nutrition < 150:
            if self.player.turns % 10 == 0:
                self.message("You are hungry.", 3)

        # Regeneration
        if self.player.turns % 15 == 0 and self.player.hp < self.player.max_hp:
            self.player.hp += 1

        # Clean dead monsters
        dungeon = self.current_dungeon
        dungeon.monsters = [m for m in dungeon.monsters if m.is_alive()]

        self._process_monsters()

    def wait(self):
        self._end_turn()


# === RENDERING ===
class Renderer:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        curses.start_color()
        curses.use_default_colors()
        # Initialize color pairs
        for i in range(1, 8):
            curses.init_pair(i, i, -1)
        curses.init_pair(8, curses.COLOR_YELLOW, -1)
        curses.init_pair(9, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.curs_set(0)
        self.stdscr.nodelay(False)
        self.stdscr.keypad(True)

    def render(self, game: Game):
        self.stdscr.clear()
        dungeon = game.current_dungeon

        # Compute FOV
        compute_fov(dungeon, game.player.x, game.player.y, FOV_RADIUS)

        # Calculate viewport offset
        cam_x = game.player.x - VIEWPORT_WIDTH // 2
        cam_y = game.player.y - VIEWPORT_HEIGHT // 2
        cam_x = max(0, min(cam_x, dungeon.width - VIEWPORT_WIDTH))
        cam_y = max(0, min(cam_y, dungeon.height - VIEWPORT_HEIGHT))

        # Draw map
        for screen_y in range(VIEWPORT_HEIGHT):
            for screen_x in range(VIEWPORT_WIDTH):
                map_x = screen_x + cam_x
                map_y = screen_y + cam_y

                if map_x >= dungeon.width or map_y >= dungeon.height:
                    continue

                tile = dungeon.tiles[map_y][map_x]
                draw_y = screen_y + MSG_HEIGHT

                if tile.visible:
                    char, color = self._get_tile_char(tile.tile_type, True)
                    self._draw(screen_x, draw_y, char, color)
                elif tile.explored:
                    char, color = self._get_tile_char(tile.tile_type, False)
                    self._draw(screen_x, draw_y, char, curses.color_pair(0) | curses.A_DIM)

        # Draw items
        for ix, iy, item in dungeon.items:
            sx, sy = ix - cam_x, iy - cam_y
            if 0 <= sx < VIEWPORT_WIDTH and 0 <= sy < VIEWPORT_HEIGHT:
                if dungeon.tiles[iy][ix].visible:
                    color = self._item_color(item)
                    self._draw(sx, sy + MSG_HEIGHT, item.char, color)

        # Draw monsters
        for monster in dungeon.monsters:
            if not monster.is_alive():
                continue
            sx, sy = monster.x - cam_x, monster.y - cam_y
            if 0 <= sx < VIEWPORT_WIDTH and 0 <= sy < VIEWPORT_HEIGHT:
                if dungeon.tiles[monster.y][monster.x].visible:
                    self._draw(sx, sy + MSG_HEIGHT, monster.char,
                              curses.color_pair(monster.color) | curses.A_BOLD)

        # Draw player
        sx, sy = game.player.x - cam_x, game.player.y - cam_y
        self._draw(sx, sy + MSG_HEIGHT, '@',
                  curses.color_pair(7) | curses.A_BOLD)

        # Draw messages
        msg_start = max(0, len(game.messages) - MSG_HEIGHT)
        for i, (msg, color) in enumerate(game.messages[msg_start:]):
            if i >= MSG_HEIGHT:
                break
            self._draw_str(0, i, msg[:SCREEN_WIDTH - 1], curses.color_pair(color))

        # Draw status bar
        self._draw_status(game)

        # Look mode cursor
        if game.look_mode:
            lsx, lsy = game.look_x - cam_x, game.look_y - cam_y
            if 0 <= lsx < VIEWPORT_WIDTH and 0 <= lsy < VIEWPORT_HEIGHT:
                self.stdscr.move(lsy + MSG_HEIGHT, lsx)
                curses.curs_set(1)

        self.stdscr.refresh()

    def _draw_status(self, game: Game):
        p = game.player
        y = MSG_HEIGHT + VIEWPORT_HEIGHT

        # HP bar
        hp_pct = p.hp / max(1, p.max_hp)
        hp_color = 2 if hp_pct > 0.6 else (3 if hp_pct > 0.3 else 1)

        status1 = f" @{p.name if hasattr(p, 'name') else 'Hero'} "
        status1 += f"HP:{p.hp}/{p.max_hp} "
        status1 += f"Atk:{p.total_attack} Def:{p.total_defense} "
        status1 += f"Lv:{p.level} XP:{p.xp}/{p.xp_to_next}"
        self._draw_str(0, y, status1[:SCREEN_WIDTH], curses.color_pair(hp_color))

        status2 = f" DLv:{p.dungeon_level} "
        status2 += f"Gold:{p.gold} "
        status2 += f"Turns:{p.turns} "
        nutr_str = "Satiated" if p.nutrition > 1000 else (
            "Normal" if p.nutrition > 300 else (
                "Hungry" if p.nutrition > 150 else "Starving!"))
        status2 += f"[{nutr_str}]"
        if p.equipped_weapon:
            status2 += f" Wpn:{p.equipped_weapon.name}"
        self._draw_str(0, y + 1, status2[:SCREEN_WIDTH], curses.color_pair(7))

    def _draw(self, x: int, y: int, char: str, attr=None):
        try:
            if attr:
                self.stdscr.addch(y, x, char, attr)
            else:
                self.stdscr.addch(y, x, char)
        except curses.error:
            pass

    def _draw_str(self, x: int, y: int, text: str, attr=None):
        try:
            if attr:
                self.stdscr.addstr(y, x, text, attr)
            else:
                self.stdscr.addstr(y, x, text)
        except curses.error:
            pass

    def _get_tile_char(self, tile_type: TileType, visible: bool):
        chars = {
            TileType.WALL: ('#', curses.color_pair(7)),
            TileType.FLOOR: ('.', curses.color_pair(7)),
            TileType.CORRIDOR: ('.', curses.color_pair(7)),
            TileType.DOOR: ('+', curses.color_pair(3)),
            TileType.STAIRS_DOWN: ('>', curses.color_pair(6) | curses.A_BOLD),
            TileType.STAIRS_UP: ('<', curses.color_pair(6) | curses.A_BOLD),
        }
        char, color = chars.get(tile_type, (' ', curses.color_pair(0)))
        if visible:
            return char, color
        return char, curses.color_pair(0) | curses.A_DIM

    def _item_color(self, item: Item) -> int:
        type_colors = {
            ItemType.WEAPON: curses.color_pair(6) | curses.A_BOLD,
            ItemType.ARMOR: curses.color_pair(6),
            ItemType.POTION: curses.color_pair(5) | curses.A_BOLD,
            ItemType.SCROLL: curses.color_pair(7) | curses.A_BOLD,
            ItemType.FOOD: curses.color_pair(3),
            ItemType.GOLD: curses.color_pair(3) | curses.A_BOLD,
            ItemType.AMULET: curses.color_pair(3) | curses.A_BOLD,
        }
        return type_colors.get(item.item_type, curses.color_pair(7))

    def show_inventory(self, game: Game, title: str = "Inventory",
                      allow_select: bool = False) -> Optional[int]:
        """Show inventory screen. Returns selected index or None."""
        self.stdscr.clear()
        self._draw_str(2, 0, f"=== {title} ===", curses.color_pair(3) | curses.A_BOLD)

        if not game.player.inventory:
            self._draw_str(2, 2, "Your inventory is empty.", curses.color_pair(7))
            self._draw_str(2, 4, "Press any key to continue...", curses.color_pair(7))
            self.stdscr.refresh()
            self.stdscr.getch()
            return None

        for i, item in enumerate(game.player.inventory):
            letter = chr(ord('a') + i)
            equipped = " (equipped)" if item.equipped else ""
            line = f" {letter}) {item.char} {item.name}{equipped}"
            color = self._item_color(item)
            self._draw_str(2, i + 2, line, color)

        if allow_select:
            self._draw_str(2, len(game.player.inventory) + 3,
                          "Select item (a-z) or ESC to cancel", curses.color_pair(7))
        else:
            self._draw_str(2, len(game.player.inventory) + 3,
                          "Press any key to continue...", curses.color_pair(7))

        self.stdscr.refresh()

        key = self.stdscr.getch()
        if allow_select and ord('a') <= key <= ord('z'):
            idx = key - ord('a')
            if idx < len(game.player.inventory):
                return idx
        return None

    def show_help(self):
        """Show help screen."""
        self.stdscr.clear()
        help_text = [
            "=== PyRogue Help ===",
            "",
            "Movement:",
            "  hjkl / arrows / numpad - Move (vi-keys supported)",
            "  y u b n - Diagonal movement",
            "  . or 5   - Wait a turn",
            "",
            "Actions:",
            "  g or ,   - Pick up item",
            "  i         - View inventory",
            "  a         - Apply/use item",
            "  d         - Drop item",
            "  e         - Eat food",
            "  w         - Wield weapon",
            "  W         - Wear armor",
            "  >         - Go down stairs",
            "  <         - Go up stairs",
            "  ;         - Look around",
            "",
            "Other:",
            "  ?         - This help screen",
            "  Q         - Quit game",
            "  S         - Save message history",
            "",
            "Goal: Descend to level 10, find the Amulet of",
            "      Yendor, and bring it back to level 1!",
            "",
            "Press any key to continue..."
        ]
        for i, line in enumerate(help_text):
            color = curses.color_pair(3) if i == 0 else curses.color_pair(7)
            self._draw_str(2, i, line, color)
        self.stdscr.refresh()
        self.stdscr.getch()

    def show_look(self, game: Game, x: int, y: int) -> str:
        """Get description at look position."""
        dungeon = game.current_dungeon
        if x < 0 or x >= dungeon.width or y < 0 or y >= dungeon.height:
            return "You see nothing."
        if not dungeon.tiles[y][x].visible:
            if dungeon.tiles[y][x].explored:
                return "You recall seeing this area."
            return "You can't see there."

        # Check for monster
        monster = dungeon.get_monster_at(x, y)
        if monster:
            return f"You see a {monster.name} (HP:{monster.hp}/{monster.max_hp})"

        # Check for items
        for ix, iy, item in dungeon.items:
            if ix == x and iy == y:
                return f"You see {item.name} here."

        # Describe tile
        tile = dungeon.tiles[y][x].tile_type
        descs = {
            TileType.WALL: "A solid wall.",
            TileType.FLOOR: "A stone floor.",
            TileType.CORRIDOR: "A narrow corridor.",
            TileType.STAIRS_DOWN: "Stairs leading down.",
            TileType.STAIRS_UP: "Stairs leading up.",
            TileType.DOOR: "A doorway.",
        }
        return descs.get(tile, "You see nothing special.")

    def show_game_over(self, game: Game):
        """Show game over / victory screen."""
        self.stdscr.clear()
        if game.victory:
            lines = [
                "╔══════════════════════════════════╗",
                "║      *** CONGRATULATIONS ***     ║",
                "║                                  ║",
                "║  You have retrieved the Amulet   ║",
                "║  of Yendor and escaped the       ║",
                "║  dungeon alive!                  ║",
                "║                                  ║",
                "║         *** YOU WIN ***          ║",
                "╚══════════════════════════════════╝",
            ]
            color = curses.color_pair(3) | curses.A_BOLD
        else:
            lines = [
                "╔══════════════════════════════════╗",
                "║        *** GAME OVER ***         ║",
                "║                                  ║",
                "║      You have perished in the    ║",
                "║      depths of the dungeon...    ║",
                "║                                  ║",
                "║          Rest in peace.          ║",
                "╚══════════════════════════════════╝",
            ]
            color = curses.color_pair(1) | curses.A_BOLD

        start_y = 4
        for i, line in enumerate(lines):
            self._draw_str(20, start_y + i, line, color)

        p = game.player
        stats_y = start_y + len(lines) + 2
        self._draw_str(20, stats_y, f"Final Stats:", curses.color_pair(7))
        self._draw_str(20, stats_y + 1,
                      f"  Level: {p.level}  Turns: {p.turns}  Gold: {p.gold}",
                      curses.color_pair(7))
        self._draw_str(20, stats_y + 2,
                      f"  Deepest Level: {p.dungeon_level}",
                      curses.color_pair(7))
        self._draw_str(20, stats_y + 4, "Press any key to exit...",
                      curses.color_pair(7))
        self.stdscr.refresh()
        self.stdscr.getch()


# === MAIN GAME LOOP ===
def main(stdscr):
    renderer = Renderer(stdscr)
    game = Game()

    # Movement keys
    move_keys = {
        ord('h'): (-1, 0), ord('j'): (0, 1),
        ord('k'): (0, -1), ord('l'): (1, 0),
        ord('y'): (-1, -1), ord('u'): (1, -1),
        ord('b'): (-1, 1), ord('n'): (1, 1),
        curses.KEY_LEFT: (-1, 0), curses.KEY_RIGHT: (1, 0),
        curses.KEY_UP: (0, -1), curses.KEY_DOWN: (0, 1),
    }

    while game.running:
        if game.game_over:
            renderer.show_game_over(game)
            break

        renderer.render(game)

        # Handle look mode
        if game.look_mode:
            key = stdscr.getch()
            if key == 27 or key == ord(';') or key == ord('q'):
                game.look_mode = False
                curses.curs_set(0)
                continue
            elif key in move_keys:
                dx, dy = move_keys[key]
                game.look_x += dx
                game.look_y += dy
                desc = renderer.show_look(game, game.look_x, game.look_y)
                game.message(desc, 6)
            continue

        key = stdscr.getch()

        if key in move_keys:
            dx, dy = move_keys[key]
            game.move_player(dx, dy)
        elif key == ord('.') or key == ord('5'):
            game.wait()
            game.message("You wait...", 7)
        elif key == ord('g') or key == ord(','):
            game.pickup_item()
        elif key == ord('i'):
            renderer.show_inventory(game, "Inventory")
        elif key == ord('a'):
            idx = renderer.show_inventory(game, "Apply/Use which item?", True)
            if idx is not None:
                game.use_item(game.player.inventory[idx])
        elif key == ord('d'):
            idx = renderer.show_inventory(game, "Drop which item?", True)
            if idx is not None:
                game.drop_item(game.player.inventory[idx])
        elif key == ord('e'):
            # Quick eat
            food = [i for i in game.player.inventory if i.item_type == ItemType.FOOD]
            if food:
                game.use_item(food[0])
            else:
                game.message("You have nothing to eat!", 1)
        elif key == ord('w'):
            weapons = [(i, item) for i, item in enumerate(game.player.inventory)
                      if item.item_type == ItemType.WEAPON]
            if weapons:
                idx = renderer.show_inventory(game, "Wield which weapon?", True)
                if idx is not None and game.player.inventory[idx].item_type == ItemType.WEAPON:
                    game.use_item(game.player.inventory[idx])
            else:
                game.message("You have no weapons!", 7)
        elif key == ord('W'):
            idx = renderer.show_inventory(game, "Wear which armor?", True)
            if idx is not None and game.player.inventory[idx].item_type == ItemType.ARMOR:
                game.use_item(game.player.inventory[idx])
        elif key == ord('>'):
            game.use_stairs(going_down=True)
        elif key == ord('<'):
            game.use_stairs(going_down=False)
        elif key == ord(';'):
            game.look_mode = True
            game.look_x = game.player.x
            game.look_y = game.player.y
            game.message("Look mode - move cursor, press ; or ESC to exit", 6)
        elif key == ord('?'):
            renderer.show_help()
        elif key == ord('Q'):
            game.message("Really quit? Press Y to confirm.", 1)
            renderer.render(game)
            confirm = stdscr.getch()
            if confirm == ord('Y') or confirm == ord('y'):
                game.running = False
        elif key == 27:  # ESC
            pass


if __name__ == "__main__":
    curses.wrapper(main)
