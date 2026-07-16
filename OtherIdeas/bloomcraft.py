#!/usr/bin/env python3
"""
🌱 BLOOMCRAFT - A Plant Breeding & Raising Game
Grow, care for, and breed plants to discover rare varieties!
"""

import random
import time
import os
import json
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

# ═══════════════════════════════════════════════════════════════
# ANSI Color Codes
# ═══════════════════════════════════════════════════════════════
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BG_GREEN = "\033[42m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"

# ═══════════════════════════════════════════════════════════════
# GENETICS SYSTEM
# ═══════════════════════════════════════════════════════════════

# Alleles: uppercase = dominant, lowercase = recessive
COLOR_GENES = {
    ("R", "R"): "Red",
    ("R", "r"): "Red",
    ("r", "R"): "Red",
    ("r", "r"): "Pink",
    ("B", "B"): "Blue",
    ("B", "b"): "Blue",
    ("b", "B"): "Blue",
    ("b", "b"): "Lavender",
    ("Y", "Y"): "Yellow",
    ("Y", "y"): "Yellow",
    ("y", "Y"): "Yellow",
    ("y", "y"): "Cream",
    ("W", "W"): "White",
    ("W", "w"): "White",
    ("w", "W"): "White",
    ("w", "w"): "Silver",
}

SIZE_GENES = {
    ("T", "T"): "Tall",
    ("T", "t"): "Medium",
    ("t", "T"): "Medium",
    ("t", "t"): "Dwarf",
}

PETAL_GENES = {
    ("P", "P"): "Double",
    ("P", "p"): "Semi-double",
    ("p", "P"): "Semi-double",
    ("p", "p"): "Single",
}

PATTERN_GENES = {
    ("S", "S"): "Striped",
    ("S", "s"): "Spotted",
    ("s", "S"): "Spotted",
    ("s", "s"): "Solid",
}

GLOW_GENES = {
    ("G", "G"): "Radiant",
    ("G", "g"): "Shimmer",
    ("g", "G"): "Shimmer",
    ("g", "g"): "None",
}

SPECIES = {
    "Rose": {"icon": "🌹", "base_grow_time": 5, "water_need": 3},
    "Tulip": {"icon": "🌷", "base_grow_time": 4, "water_need": 2},
    "Sunflower": {"icon": "🌻", "base_grow_time": 6, "water_need": 4},
    "Lily": {"icon": "🪷", "base_grow_time": 5, "water_need": 3},
    "Orchid": {"icon": "🌺", "base_grow_time": 7, "water_need": 2},
    "Daisy": {"icon": "🌼", "base_grow_time": 3, "water_need": 2},
}

GROWTH_STAGES = ["Seed", "Sprout", "Seedling", "Budding", "Blooming", "Mature"]
STAGE_ART = {
    "Seed": [
        "       ",
        "       ",
        "       ",
        "   .   ",
        "  (o)  ",
        "███████",
    ],
    "Sprout": [
        "       ",
        "       ",
        "   |   ",
        "  \\|/  ",
        "   |   ",
        "███████",
    ],
    "Seedling": [
        "       ",
        "   |   ",
        "  /|\\  ",
        " / | \\ ",
        "   |   ",
        "███████",
    ],
    "Budding": [
        "  (@)  ",
        "   |   ",
        "  /|\\  ",
        " / | \\ ",
        "   |   ",
        "███████",
    ],
    "Blooming": [
        " \\|*|/ ",
        " -(*)-  ",
        "  /|\\  ",
        " / | \\ ",
        "   |   ",
        "███████",
    ],
    "Mature": [
        "*\\|*|/*",
        "*-(*)-*",
        " */|\\* ",
        " / | \\ ",
        "   |   ",
        "███████",
    ],
}

# ═══════════════════════════════════════════════════════════════
# PLANT CLASS
# ═══════════════════════════════════════════════════════════════

class Plant:
    _next_id = 1

    def __init__(self, species: str, genes: dict, name: Optional[str] = None, generation: int = 1):
        self.id = Plant._next_id
        Plant._next_id += 1
        self.species = species
        self.genes = genes  # {"color": ("R","r"), "size": ("T","t"), ...}
        self.name = name or f"{species}#{self.id}"
        self.generation = generation
        self.growth_stage = 0  # index into GROWTH_STAGES
        self.health = 100
        self.water_level = 50
        self.happiness = 50
        self.fertilized = False
        self.actions_taken = 0  # tracks "time" passing
        self.times_watered = 0
        self.times_fed = 0
        self.parent_a = None
        self.parent_b = None
        self.is_alive = True
        self.discovered_new = False

    @property
    def stage_name(self):
        return GROWTH_STAGES[self.growth_stage]

    @property
    def is_mature(self):
        return self.growth_stage >= 5

    @property
    def color(self):
        return COLOR_GENES.get(self.genes["color"], "Unknown")

    @property
    def size(self):
        return SIZE_GENES.get(self.genes["size"], "Unknown")

    @property
    def petals(self):
        return PETAL_GENES.get(self.genes["petal"], "Unknown")

    @property
    def pattern(self):
        return PATTERN_GENES.get(self.genes["pattern"], "Unknown")

    @property
    def glow(self):
        return GLOW_GENES.get(self.genes["glow"], "Unknown")

    @property
    def trait_string(self):
        traits = []
        if self.glow != "None":
            traits.append(self.glow)
        if self.pattern != "Solid":
            traits.append(self.pattern)
        traits.append(self.color)
        traits.append(self.size)
        traits.append(f"{self.petals}-petal")
        traits.append(self.species)
        return " ".join(traits)

    @property
    def rarity_score(self):
        score = 0
        # Recessive traits are rarer
        for gene_pair in self.genes.values():
            if gene_pair[0].islower() and gene_pair[1].islower():
                score += 2
            elif gene_pair[0].islower() or gene_pair[1].islower():
                score += 1
        if self.glow != "None":
            score += 3
        if self.pattern != "Solid":
            score += 2
        return score

    @property
    def rarity_label(self):
        s = self.rarity_score
        if s >= 12:
            return f"{C.MAGENTA}★ LEGENDARY ★{C.RESET}"
        elif s >= 9:
            return f"{C.YELLOW}◆ Epic ◆{C.RESET}"
        elif s >= 6:
            return f"{C.BLUE}● Rare ●{C.RESET}"
        elif s >= 3:
            return f"{C.GREEN}○ Uncommon ○{C.RESET}"
        else:
            return f"{C.WHITE}· Common ·{C.RESET}"

    @property
    def color_code(self):
        c = self.color
        if c in ("Red", "Pink"):
            return C.RED
        elif c in ("Blue", "Lavender"):
            return C.BLUE
        elif c in ("Yellow", "Cream"):
            return C.YELLOW
        elif c in ("White", "Silver"):
            return C.WHITE
        return C.GREEN

    def water(self):
        if not self.is_alive:
            return "This plant has withered..."
        self.water_level = min(100, self.water_level + 30)
        self.happiness = min(100, self.happiness + 5)
        self.times_watered += 1
        self._tick()
        return f"💧 You watered {self.name}. Water level: {self.water_level}%"

    def fertilize(self):
        if not self.is_alive:
            return "This plant has withered..."
        if self.fertilized:
            return "Already fertilized! Wait until next growth stage."
        self.fertilized = True
        self.happiness = min(100, self.happiness + 10)
        self.times_fed += 1
        self._tick()
        return f"🧪 You fertilized {self.name}. It looks healthier!"

    def sing_to(self):
        if not self.is_alive:
            return "This plant has withered..."
        self.happiness = min(100, self.happiness + 15)
        self._tick()
        responses = [
            f"🎵 {self.name} seems to sway happily!",
            f"🎵 {self.name} rustles its leaves with joy!",
            f"🎵 {self.name} perks up at the melody!",
            f"🎵 {self.name} glows a little brighter!",
        ]
        return random.choice(responses)

    def prune(self):
        if not self.is_alive:
            return "This plant has withered..."
        self.health = min(100, self.health + 10)
        self._tick()
        return f"✂️ You pruned {self.name}. Health improved!"

    def _tick(self):
        """Simulate time passing with each action."""
        self.actions_taken += 1

        # Water decreases over time
        self.water_level = max(0, self.water_level - 8)
        self.happiness = max(0, self.happiness - 3)

        # Check water stress
        if self.water_level <= 0:
            self.health -= 15
            if self.health <= 0:
                self.is_alive = False
                return

        # Growth check
        grow_time = SPECIES[self.species]["base_grow_time"]
        if self.fertilized:
            grow_time -= 1
        if self.happiness > 70:
            grow_time -= 1
        grow_time = max(2, grow_time)

        if self.actions_taken % grow_time == 0 and self.growth_stage < 5:
            self.growth_stage += 1
            self.fertilized = False  # Reset fertilizer each stage


def create_random_plant(species: Optional[str] = None) -> Plant:
    """Create a plant with random genetics."""
    if species is None:
        species = random.choice(list(SPECIES.keys()))

    color_alleles = random.choice(list(COLOR_GENES.keys()))
    size_alleles = random.choice([("T", "T"), ("T", "t"), ("t", "T"), ("t", "t")])
    petal_alleles = random.choice([("P", "P"), ("P", "p"), ("p", "P"), ("p", "p")])
    pattern_alleles = random.choice([("S", "S"), ("S", "s"), ("s", "S"), ("s", "s")])
    # Glow is very rare in wild plants
    if random.random() < 0.05:
        glow_alleles = random.choice([("G", "g"), ("g", "G")])
    else:
        glow_alleles = ("g", "g")

    genes = {
        "color": color_alleles,
        "size": size_alleles,
        "petal": petal_alleles,
        "pattern": pattern_alleles,
        "glow": glow_alleles,
    }

    return Plant(species, genes)


def breed_plants(parent_a: Plant, parent_b: Plant) -> Plant:
    """Breed two plants using Mendelian genetics."""
    if parent_a.species != parent_b.species:
        # Hybrid - random species from parents
        species = random.choice([parent_a.species, parent_b.species])
    else:
        species = parent_a.species

    child_genes = {}
    for trait in ["color", "size", "petal", "pattern", "glow"]:
        # Each parent contributes one allele
        allele_a = random.choice(parent_a.genes[trait])
        allele_b = random.choice(parent_b.genes[trait])

        # Small mutation chance
        if random.random() < 0.05:
            if trait == "color":
                possible = ["R", "r", "B", "b", "Y", "y", "W", "w"]
                allele_a = random.choice(possible)
            elif trait == "glow":
                allele_a = "G"  # Mutation can introduce glow!

        child_genes[trait] = (allele_a, allele_b)

    child = Plant(species, child_genes, generation=max(parent_a.generation, parent_b.generation) + 1)
    child.parent_a = parent_a.name
    child.parent_b = parent_b.name
    return child


# ═══════════════════════════════════════════════════════════════
# GAME STATE
# ═══════════════════════════════════════════════════════════════

class Game:
    def __init__(self):
        self.garden: list[Plant] = []
        self.archive: list[dict] = []  # Discovered varieties
        self.coins = 50
        self.day = 1
        self.discoveries = set()
        self.achievements = []
        self.total_bred = 0
        self.total_grown = 0

    def get_discovery_key(self, plant: Plant):
        return f"{plant.color}|{plant.size}|{plant.petals}|{plant.pattern}|{plant.glow}|{plant.species}"

    def check_discovery(self, plant: Plant):
        key = self.get_discovery_key(plant)
        if key not in self.discoveries:
            self.discoveries.add(key)
            plant.discovered_new = True
            self.coins += 10
            return True
        return False

    def check_achievements(self):
        new_achievements = []
        checks = [
            (len(self.garden) >= 5, "🌿 Green Thumb - Own 5 plants"),
            (self.total_bred >= 1, "💕 First Love - Breed your first plant"),
            (self.total_bred >= 10, "🧬 Geneticist - Breed 10 plants"),
            (self.total_bred >= 25, "🔬 Mad Scientist - Breed 25 plants"),
            (len(self.discoveries) >= 10, "📚 Botanist - Discover 10 varieties"),
            (len(self.discoveries) >= 25, "🏆 Master Botanist - Discover 25 varieties"),
            (any(p.glow != "None" for p in self.garden), "✨ Bioluminescence - Own a glowing plant"),
            (any(p.rarity_score >= 12 for p in self.garden), "⭐ Legendary Find - Own a legendary plant"),
            (any(p.generation >= 5 for p in self.garden), "👴 Legacy - Reach generation 5"),
            (self.coins >= 200, "💰 Wealthy Gardner - Earn 200 coins"),
        ]
        for condition, achievement in checks:
            if condition and achievement not in self.achievements:
                self.achievements.append(achievement)
                new_achievements.append(achievement)
        return new_achievements


# ═══════════════════════════════════════════════════════════════
# DISPLAY FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(game: Game):
    print(f"\n{C.GREEN}{'═' * 60}{C.RESET}")
    print(f"{C.GREEN}{'═' * 60}{C.RESET}")
    print(f"{C.BOLD}{C.GREEN}   🌱 B L O O M C R A F T 🌱{C.RESET}")
    print(f"{C.GREEN}{'═' * 60}{C.RESET}")
    print(f"  Day: {C.YELLOW}{game.day}{C.RESET} | "
          f"Plants: {C.GREEN}{len(game.garden)}{C.RESET} | "
          f"Coins: {C.YELLOW}{game.coins}🪙{C.RESET} | "
          f"Discoveries: {C.CYAN}{len(game.discoveries)}{C.RESET}")
    print(f"{C.GREEN}{'═' * 60}{C.RESET}")


def print_plant_card(plant: Plant, detailed=False):
    """Display a plant's info in a nice card format."""
    icon = SPECIES[plant.species]["icon"]
    alive_str = "" if plant.is_alive else f" {C.RED}[WITHERED]{C.RESET}"

    print(f"\n  ┌{'─' * 44}┐")
    print(f"  │ {icon} {C.BOLD}{plant.color_code}{plant.name}{C.RESET}{alive_str}")
    print(f"  │ {plant.rarity_label}")
    print(f"  │ {C.DIM}Gen {plant.generation} | {plant.trait_string}{C.RESET}")
    print(f"  │ Stage: {C.CYAN}{plant.stage_name}{C.RESET} ", end="")

    # Progress bar
    progress = plant.growth_stage / 5
    bar_len = 20
    filled = int(bar_len * progress)
    bar = "█" * filled + "░" * (bar_len - filled)
    print(f"[{C.GREEN}{bar}{C.RESET}]")

    if detailed and plant.is_alive:
        # Health bar
        h_color = C.GREEN if plant.health > 50 else (C.YELLOW if plant.health > 25 else C.RED)
        print(f"  │ ❤️  Health:    {h_color}{plant.health:3d}%{C.RESET}")
        # Water bar
        w_color = C.BLUE if plant.water_level > 30 else C.RED
        print(f"  │ 💧 Water:     {w_color}{plant.water_level:3d}%{C.RESET}")
        # Happiness
        hap_color = C.GREEN if plant.happiness > 50 else C.YELLOW
        print(f"  │ 😊 Happiness: {hap_color}{plant.happiness:3d}%{C.RESET}")
        if plant.fertilized:
            print(f"  │ 🧪 {C.GREEN}Fertilized{C.RESET}")
        if plant.parent_a:
            print(f"  │ 👪 Parents: {plant.parent_a} × {plant.parent_b}")

    if detailed:
        # Show ASCII art
        art = STAGE_ART[plant.stage_name]
        print(f"  │")
        for line in art:
            print(f"  │   {plant.color_code}{line}{C.RESET}")

    print(f"  └{'─' * 44}┘")


def print_gene_info(plant: Plant):
    """Show genetic information for a plant."""
    print(f"\n  {C.BOLD}🧬 Genetic Profile: {plant.name}{C.RESET}")
    print(f"  {'─' * 40}")
    genes_display = [
        ("Color", plant.genes["color"], plant.color),
        ("Size", plant.genes["size"], plant.size),
        ("Petals", plant.genes["petal"], plant.petals),
        ("Pattern", plant.genes["pattern"], plant.pattern),
        ("Glow", plant.genes["glow"], plant.glow),
    ]
    for name, alleles, phenotype in genes_display:
        a1, a2 = alleles
        homo = "Homozygous" if a1 == a2 else "Heterozygous"
        print(f"  {name:10s}: [{a1}][{a2}] → {phenotype} ({homo})")


# ═══════════════════════════════════════════════════════════════
# SHOP
# ═══════════════════════════════════════════════════════════════

SHOP_ITEMS = {
    "1": {"name": "Random Seed Pack", "cost": 10, "desc": "A random species seed"},
    "2": {"name": "Rose Seed", "cost": 15, "desc": "A rose seed"},
    "3": {"name": "Tulip Seed", "cost": 12, "desc": "A tulip seed"},
    "4": {"name": "Sunflower Seed", "cost": 15, "desc": "A sunflower seed"},
    "5": {"name": "Lily Seed", "cost": 15, "desc": "A lily seed"},
    "6": {"name": "Orchid Seed", "cost": 20, "desc": "A rare orchid seed"},
    "7": {"name": "Daisy Seed", "cost": 10, "desc": "A daisy seed"},
    "8": {"name": "Mystery Seed", "cost": 30, "desc": "Could be anything... higher rare chance!"},
    "9": {"name": "Bulk Fertilizer (x5)", "cost": 25, "desc": "Fertilize 5 plants instantly"},
}


# ═══════════════════════════════════════════════════════════════
# MAIN GAME LOOP
# ═══════════════════════════════════════════════════════════════

def main():
    game = Game()

    # Give starter plants
    starter1 = create_random_plant("Daisy")
    starter1.name = "Starter Daisy"
    starter2 = create_random_plant("Rose")
    starter2.name = "Starter Rose"
    game.garden.append(starter1)
    game.garden.append(starter2)
    game.check_discovery(starter1)
    game.check_discovery(starter2)

    clear_screen()
    print(f"""
{C.GREEN}{'═' * 60}{C.RESET}
{C.BOLD}{C.GREEN}
    🌱 Welcome to BLOOMCRAFT! 🌱
{C.RESET}
    You've inherited a small garden with two starter plants.
    Your goal: breed and discover as many unique plant
    varieties as possible!

    • Water and care for your plants to help them grow
    • Breed mature plants to create new varieties
    • Discover rare traits through selective breeding
    • Collect coins from discoveries to buy more seeds

    {C.DIM}Tip: Recessive genes (lowercase) create rarer traits!
    Try breeding plants with similar hidden genes.{C.RESET}

{C.GREEN}{'═' * 60}{C.RESET}
""")
    input(f"  {C.CYAN}Press Enter to start your journey...{C.RESET}")

    while True:
        clear_screen()
        print_header(game)

        # Check achievements
        new_achs = game.check_achievements()
        for ach in new_achs:
            print(f"\n  🎉 {C.YELLOW}ACHIEVEMENT UNLOCKED: {ach}{C.RESET}")

        # Main menu
        print(f"""
  {C.BOLD}What would you like to do?{C.RESET}

  {C.GREEN}[1]{C.RESET} 🌿 View Garden
  {C.GREEN}[2]{C.RESET} 💧 Care for a Plant
  {C.GREEN}[3]{C.RESET} 💕 Breed Plants
  {C.GREEN}[4]{C.RESET} 🛒 Seed Shop
  {C.GREEN}[5]{C.RESET} 📖 Collection / Discoveries
  {C.GREEN}[6]{C.RESET} 🏆 Achievements
  {C.GREEN}[7]{C.RESET} 🧬 View Genetics
  {C.GREEN}[8]{C.RESET} 🗑️  Remove a Plant
  {C.GREEN}[9]{C.RESET} ⏭️  Advance Day (water all, time passes)
  {C.GREEN}[0]{C.RESET} 🚪 Quit
""")

        choice = input(f"  {C.CYAN}Choose> {C.RESET}").strip()

        # ─── VIEW GARDEN ───────────────────────────────────
        if choice == "1":
            clear_screen()
            print(f"\n  {C.BOLD}🌿 Your Garden ({len(game.garden)} plants){C.RESET}\n")
            if not game.garden:
                print("  Your garden is empty! Visit the shop to buy seeds.")
            else:
                for plant in game.garden:
                    print_plant_card(plant)
            input(f"\n  {C.DIM}Press Enter to continue...{C.RESET}")

        # ─── CARE FOR PLANT ────────────────────────────────
        elif choice == "2":
            clear_screen()
            print(f"\n  {C.BOLD}💧 Care for a Plant{C.RESET}\n")
            alive_plants = [p for p in game.garden if p.is_alive]
            if not alive_plants:
                print("  No living plants to care for!")
                input(f"\n  {C.DIM}Press Enter to continue...{C.RESET}")
                continue

            for i, p in enumerate(alive_plants, 1):
                icon = SPECIES[p.species]["icon"]
                print(f"  [{i}] {icon} {p.name} - {p.stage_name} (💧{p.water_level}% ❤️{p.health}%)")

            try:
                idx = int(input(f"\n  {C.CYAN}Select plant #> {C.RESET}")) - 1
                plant = alive_plants[idx]
            except (ValueError, IndexError):
                print("  Invalid selection.")
                input(f"\n  {C.DIM}Press Enter to continue...{C.RESET}")
                continue

            print_plant_card(plant, detailed=True)
            print(f"""
  {C.BOLD}Care Actions:{C.RESET}
  [1] 💧 Water
  [2] 🧪 Fertilize
  [3] 🎵 Sing to plant
  [4] ✂️  Prune
  [5] ← Back
""")
            action = input(f"  {C.CYAN}Action> {C.RESET}").strip()
            if action == "1":
                msg = plant.water()
                print(f"\n  {msg}")
            elif action == "2":
                msg = plant.fertilize()
                print(f"\n  {msg}")
            elif action == "3":
                msg = plant.sing_to()
                print(f"\n  {msg}")
            elif action == "4":
                msg = plant.prune()
                print(f"\n  {msg}")

            if plant.growth_stage == 5 and plant.stage_name == "Mature":
                is_new = game.check_discovery(plant)
                if is_new:
                    print(f"\n  🎊 {C.YELLOW}NEW DISCOVERY!{C.RESET} {plant.trait_string}")
                    print(f"  +10 coins! 🪙")
                game.total_grown += 1

            # Check if plant died
            if not plant.is_alive:
                print(f"\n  {C.RED}💀 Oh no! {plant.name} has withered from neglect!{C.RESET}")

            input(f"\n  {C.DIM}Press Enter to continue...{C.RESET}")

        # ─── BREED PLANTS ──────────────────────────────────
        elif choice == "3":
            clear_screen()
            print(f"\n  {C.BOLD}💕 Breed Plants{C.RESET}\n")
            mature_plants = [p for p in game.garden if p.is_mature and p.is_alive]

            if len(mature_plants) < 2:
                print(f"  You need at least 2 mature living plants to breed!")
                print(f"  Currently have: {len(mature_plants)} mature plant(s)")
                input(f"\n  {C.DIM}Press Enter to continue...{C.RESET}")
                continue

            print(f"  {C.DIM}Select two plants to breed:{C.RESET}\n")
            for i, p in enumerate(mature_plants, 1):
                icon = SPECIES[p.species]["icon"]
                print(f"  [{i}] {icon} {p.name} ({p.trait_string})")

            try:
                print()
                idx1 = int(input(f"  {C.CYAN}First parent #> {C.RESET}")) - 1
                idx2 = int(input(f"  {C.CYAN}Second parent #> {C.RESET}")) - 1
                if idx1 == idx2:
                    print("  Can't breed a plant with itself!")
                    input(f"\n  {C.DIM}Press Enter to continue...{C.RESET}")
                    continue
                parent_a = mature_plants[idx1]
                parent_b = mature_plants[idx2]
            except (ValueError, IndexError):
                print("  Invalid selection.")
                input(f"\n  {C.DIM}Press Enter to continue...{C.RESET}")
                continue

            # Breeding animation
            print(f"\n  {C.MAGENTA}Breeding {parent_a.name} × {parent_b.name}...{C.RESET}")
            for i in range(3):
                time.sleep(0.5)
                print(f"  {'💕' * (i + 1)}")

            child = breed_plants(parent_a, parent_b)
            game.garden.append(child)
            game.total_bred += 1

            print(f"\n  {C.GREEN}🌱 A new plant has sprouted!{C.RESET}")
            print_plant_card(child, detailed=True)

            is_new = game.check_discovery(child)
            if is_new:
                print(f"\n  🎊 {C.YELLOW}NEW VARIETY DISCOVERED!{C.RESET}")
                print(f"  +10 coins! 🪙")

            # Name the plant?
            name = input(f"\n  {C.CYAN}Name this plant (Enter to skip)> {C.RESET}").strip()
            if name:
                child.name = name

            input(f"\n  {C.DIM}Press Enter to continue...{C.RESET}")

        # ─── SHOP ─────────────────────────────────────────
        elif choice == "4":
            clear_screen()
            print(f"\n  {C.BOLD}🛒 Seed Shop{C.RESET}")
            print(f"  Your coins: {C.YELLOW}{game.coins}🪙{C.RESET}\n")

            for key, item in SHOP_ITEMS.items():
                affordable = "✓" if game.coins >= item["cost"] else "✗"
                color = C.GREEN if game.coins >= item["cost"] else C.RED
                print(f"  [{key}] {color}{item['name']}{C.RESET} - {item['cost']}🪙")
                print(f"      {C.DIM}{item['desc']}{C.RESET}")

            print(f"\n  [0] ← Back")
            shop_choice = input(f"\n  {C.CYAN}Buy> {C.RESET}").strip()

            if shop_choice in SHOP_ITEMS:
                item = SHOP_ITEMS[shop_choice]
                if game.coins < item["cost"]:
                    print(f"\n  {C.RED}Not enough coins!{C.RESET}")
                else:
                    game.coins -= item["cost"]
                    if shop_choice == "1":
                        new_plant = create_random_plant()
                    elif shop_choice == "2":
                        new_plant = create_random_plant("Rose")
                    elif shop_choice == "3":
                        new_plant = create_random_plant("Tulip")
                    elif shop_choice == "4":
                        new_plant = create_random_plant("Sunflower")
                    elif shop_choice == "5":
                        new_plant = create_random_plant("Lily")
                    elif shop_choice == "6":
                        new_plant = create_random_plant("Orchid")
                    elif shop_choice == "7":
                        new_plant = create_random_plant("Daisy")
                    elif shop_choice == "8":
                        # Mystery seed - higher chance of rare genes
                        new_plant = create_random_plant()
                        # Boost rare alleles
                        for trait in new_plant.genes:
                            if random.random() < 0.4:
                                a, b = new_plant.genes[trait]
                                new_plant.genes[trait] = (a.lower(), b.lower())
                    elif shop_choice == "9":
                        # Bulk fertilizer
                        count = 0
                        for p in game.garden:
                            if p.is_alive and not p.fertilized and count < 5:
                                p.fertilized = True
                                count += 1
                        print(f"\n  🧪 Fertilized {count} plants!")
                        input(f"\n  {C.DIM}Press Enter to continue...{C.RESET}")
                        continue

                    if shop_choice != "9":
                        game.garden.append(new_plant)
                        print(f"\n  {C.GREEN}🌱 You got: {new_plant.trait_string}!{C.RESET}")
                        print_plant_card(new_plant)

                        name = input(f"\n  {C.CYAN}Name this plant (Enter to skip)> {C.RESET}").strip()
                        if name:
                            new_plant.name = name

            input(f"\n  {C.DIM}Press Enter to continue...{C.RESET}")

        # ─── COLLECTION ────────────────────────────────────
        elif choice == "5":
            clear_screen()
            print(f"\n  {C.BOLD}📖 Discovery Collection{C.RESET}")
            print(f"  Varieties discovered: {C.CYAN}{len(game.discoveries)}{C.RESET}\n")

            if not game.discoveries:
                print("  No discoveries yet! Grow and breed plants.")
            else:
                for i, disc in enumerate(sorted(game.discoveries), 1):
                    parts = disc.split("|")
                    color, size, petals, pattern, glow, species = parts
                    display = []
                    if glow != "None":
                        display.append(glow)
                    if pattern != "Solid":
                        display.append(pattern)
                    display.extend([color, size, f"{petals}-petal", species])
                    icon = SPECIES[species]["icon"]
                    print(f"  {i:3d}. {icon} {' '.join(display)}")

            input(f"\n  {C.DIM}Press Enter to continue...{C.RESET}")

        # ─── ACHIEVEMENTS ──────────────────────────────────
        elif choice == "6":
            clear_screen()
            print(f"\n  {C.BOLD}🏆 Achievements{C.RESET}\n")
            if not game.achievements:
                print("  No achievements yet! Keep playing.")
            else:
                for ach in game.achievements:
                    print(f"  ✅ {ach}")

            print(f"\n  {C.DIM}── Stats ──{C.RESET}")
            print(f"  Total plants bred: {game.total_bred}")
            print(f"  Total matured: {game.total_grown}")
            print(f"  Garden size: {len(game.garden)}")
            print(f"  Total coins earned: {game.coins}")

            input(f"\n  {C.DIM}Press Enter to continue...{C.RESET}")

        # ─── GENETICS VIEW ─────────────────────────────────
        elif choice == "7":
            clear_screen()
            print(f"\n  {C.BOLD}🧬 Genetics Lab{C.RESET}\n")
            alive_plants = [p for p in game.garden if p.is_alive]
            if not alive_plants:
                print("  No plants to analyze!")
                input(f"\n  {C.DIM}Press Enter to continue...{C.RESET}")
                continue

            for i, p in enumerate(alive_plants, 1):
                icon = SPECIES[p.species]["icon"]
                print(f"  [{i}] {icon} {p.name}")

            try:
                idx = int(input(f"\n  {C.CYAN}Select plant #> {C.RESET}")) - 1
                plant = alive_plants[idx]
            except (ValueError, IndexError):
                print("  Invalid selection.")
                input(f"\n  {C.DIM}Press Enter to continue...{C.RESET}")
                continue

            print_gene_info(plant)
            print(f"\n  {C.DIM}── Breeding Tips ──{C.RESET}")
            print(f"  • Two lowercase alleles = recessive (rare) trait")
            print(f"  • Breed two heterozygous plants for 25% rare chance")
            print(f"  • Mutations can introduce new alleles (5% chance)")

            input(f"\n  {C.DIM}Press Enter to continue...{C.RESET}")

        # ─── REMOVE PLANT ──────────────────────────────────
        elif choice == "8":
            clear_screen()
            print(f"\n  {C.BOLD}🗑️  Remove a Plant{C.RESET}\n")
            if not game.garden:
                print("  Garden is empty!")
                input(f"\n  {C.DIM}Press Enter to continue...{C.RESET}")
                continue

            for i, p in enumerate(game.garden, 1):
                icon = SPECIES[p.species]["icon"]
                status = "" if p.is_alive else f" {C.RED}[DEAD]{C.RESET}"
                print(f"  [{i}] {icon} {p.name}{status}")

            try:
                idx = int(input(f"\n  {C.CYAN}Remove plant #> {C.RESET}")) - 1
                plant = game.garden[idx]
                confirm = input(f"  Remove {plant.name}? (y/n)> ").strip().lower()
                if confirm == "y":
                    game.garden.pop(idx)
                    game.coins += 2
                    print(f"  Composted {plant.name}. +2 coins for compost. 🪙")
            except (ValueError, IndexError):
                print("  Invalid selection.")

            input(f"\n  {C.DIM}Press Enter to continue...{C.RESET}")

        # ─── ADVANCE DAY ───────────────────────────────────
        elif choice == "9":
            game.day += 1
            print(f"\n  {C.YELLOW}☀️ A new day dawns... (Day {game.day}){C.RESET}\n")
            time.sleep(0.5)

            for plant in game.garden:
                if plant.is_alive:
                    # Auto-water a bit
                    plant.water_level = min(100, plant.water_level + 15)
                    plant._tick()
                    plant._tick()

                    if not plant.is_alive:
                        print(f"  {C.RED}💀 {plant.name} withered!{C.RESET}")
                    elif plant.growth_stage == 5:
                        is_new = game.check_discovery(plant)
                        if is_new:
                            print(f"  🎊 {plant.name} matured! {C.YELLOW}NEW DISCOVERY!{C.RESET} +10🪙")
                            game.total_grown += 1
                        elif plant.actions_taken <= 6:  # Just matured
                            print(f"  🌸 {plant.name} has fully bloomed!")
                            game.total_grown += 1
                    elif GROWTH_STAGES[plant.growth_stage] != "Seed":
                        if random.random() < 0.3:
                            print(f"  🌱 {plant.name} is growing... ({plant.stage_name})")

            # Daily bonus
            game.coins += 5
            print(f"\n  +5 daily coins 🪙")

            input(f"\n  {C.DIM}Press Enter to continue...{C.RESET}")

        # ─── QUIT ─────────────────────────────────────────
        elif choice == "0":
            clear_screen()
            print(f"""
{C.GREEN}{'═' * 60}{C.RESET}

  {C.BOLD}Thanks for playing BLOOMCRAFT!{C.RESET}

  📊 Final Stats:
  • Days played: {game.day}
  • Plants bred: {game.total_bred}
  • Varieties discovered: {len(game.discoveries)}
  • Achievements: {len(game.achievements)}
  • Final coins: {game.coins}

  🌱 Your garden had {len(game.garden)} plants.

{C.GREEN}{'═' * 60}{C.RESET}
""")
            break

        else:
            pass  # Invalid choice, just refresh


if __name__ == "__main__":
    main()
