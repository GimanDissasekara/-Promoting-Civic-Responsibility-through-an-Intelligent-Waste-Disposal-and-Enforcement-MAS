import random
import pygame
import numpy as np
import logging
from enum import Enum
import time

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
BROWN = (165, 42, 42)
YELLOW = (255, 255, 0)
MAGENTA = (255, 0, 255)
GRAY = (128, 128, 128)

class SimulationState(Enum):
    SETUP = 1
    RUNNING = 2
    STOPPED = 3

class Button:
    def __init__(self, x, y, width, height, text, color, text_color=BLACK):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.text_color = text_color
        self.font = pygame.font.Font(None, 36)

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        text_surface = self.font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

class Agent:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.score = 5

    def move(self, width, height):
        # Random movement
        dx = random.randint(-1, 1)
        dy = random.randint(-1, 1)
        
        new_x = max(0, min(width - 1, self.x + dx))
        new_y = max(0, min(height - 1, self.y + dy))
        
        self.x, self.y = new_x, new_y

class NormalAgent(Agent):
    def __init__(self, x, y):
        super().__init__(x, y, BROWN)
        self.score = 5

    def check_improper_disposal(self, garbage_items, disposal_areas):
        # Check if agent is on a garbage item
        for garbage in garbage_items:
            if self.x == garbage.x and self.y == garbage.y:
                # 50% chance of improper disposal
                if random.random() < 0.5:
                    # Check if not in proper disposal area
                    if not any((self.x == area.x and self.y == area.y) for area in disposal_areas):
                        self.score -= 1
                        return True
        return False

class ProperDisposer(Agent):
    def __init__(self, x, y):
        super().__init__(x, y, MAGENTA)
        self.score = 0

    def collect_garbage(self, garbage_items):
        for garbage in garbage_items[:]:
            if self.x == garbage.x and self.y == garbage.y:
                self.score += 1
                garbage_items.remove(garbage)
                return True
        return False

class PoliceAgent:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def move(self, width, height):
        """Move randomly within the simulation area."""
        self.x = (self.x + random.choice([-1, 0, 1])) % width
        self.y = (self.y + random.choice([-1, 0, 1])) % height

    def check_arrest(self, improper_disposers):
        """Check and arrest any ImproperDisposer agents within the same position."""
        arrests = 0
        for disposer in improper_disposers[:]:
            if disposer.x == self.x and disposer.y == self.y:
                improper_disposers.remove(disposer)
                arrests += 1
        return arrests
    
class ImproperDisposer:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def move(self, width, height):
        """Move randomly within the simulation area."""
        self.x = (self.x + random.choice([-1, 0, 1])) % width
        self.y = (self.y + random.choice([-1, 0, 1])) % height

    def dispose_improperly(self, garbage_items):
        """Dispose garbage improperly, leaving it in the environment."""
        garbage_items.append(GarbageItem(self.x, self.y))

class GarbageCollector(Agent):
    def __init__(self, x, y):
        super().__init__(x, y, GREEN)
        self.target = None

    def find_target(self, garbage_items):
        if not garbage_items:
            return None
        
        # Find closest garbage item
        closest_dist = float('inf')
        closest_garbage = None
        for garbage in garbage_items:
            dist = ((self.x - garbage.x)**2 + (self.y - garbage.y)**2)**0.5
            if dist < closest_dist:
                closest_dist = dist
                closest_garbage = garbage
        return closest_garbage

    def move_to_target(self, target):
        if target:
            dx = np.sign(target.x - self.x)
            dy = np.sign(target.y - self.y)
            self.x += dx
            self.y += dy

class Camera(Agent):
    def __init__(self, x, y):
        super().__init__(x, y, WHITE)
        self.detection_range = 20

    def detect_illegal_disposal(self, normal_agents):
        detected = []
        for agent in normal_agents:
            # Simple distance-based detection
            dist = ((self.x - agent.x)**2 + (self.y - agent.y)**2)**0.5
            if dist <= self.detection_range and agent.score <= 0:
                detected.append(agent)
        return detected

class GarbageItem:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class DisposalArea:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class GarbageSimulation:
    def __init__(self, width=50, height=50):
        # Simulation parameters
        self.width = width
        self.height = height
        
        # Initialize agents and items
        self.normal_agents = []
        self.proper_disposers = []
        self.improper_disposers = []
        self.police_agents = []
        self.garbage_collectors = []
        self.cameras = []
        self.garbage_items = []
        self.disposal_areas = []
        
        # Simulation tracking
        self.arrests = 0
        self.last_arrest_count = 0
        self.last_arrest_time = time.time()
        
        # Logging setup
        self.logger = logging.getLogger('GarbageSimulation')
        self.logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler('simulation_log.txt', mode='w')
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # State tracking
        self.state = SimulationState.SETUP
    
    
    def check_arrest_activity(self):
        current_time = time.time()
        if self.arrests > self.last_arrest_count:
            self.last_arrest_time = current_time
            self.last_arrest_count = self.arrests
        elif current_time - self.last_arrest_time > 30:
            self.state = SimulationState.STOPPED
            self.log_message("Simulation stopped due to inactivity in arrests.")

    def log_message(self, message):
        """Log messages between agents"""
        self.logger.info(message)

    def create_agents(self):
        # Clear existing agents and items
        self.normal_agents.clear()
        self.proper_disposers.clear()
        self.improper_disposers.clear()
        self.police_agents.clear()
        self.garbage_collectors.clear()
        self.cameras.clear()
        self.garbage_items.clear()
        self.disposal_areas.clear()

        # Create normal agents
        for _ in range(50):
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)
            self.normal_agents.append(NormalAgent(x, y))
            
            
        # Create improper disposers
        for _ in range(15):
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)
            self.improper_disposers.append(ImproperDisposer(x, y))
            
        # Create proper disposers
        for _ in range(10):
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)
            self.proper_disposers.append(ProperDisposer(x, y))
        
        # Create police agents
        for _ in range(30):
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)
            self.police_agents.append(PoliceAgent(x, y))
        
        # Create garbage collectors
        for _ in range(50):
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)
            self.garbage_collectors.append(GarbageCollector(x, y))
        
        # Create cameras
        for _ in range(40):
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)
            self.cameras.append(Camera(x, y))
        
        # Create garbage items
        for _ in range(30):
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)
            self.garbage_items.append(GarbageItem(x, y))

        # Create disposal areas
        for x in range(0, self.width, 10):
            for y in range(0, self.height, 10):
                self.disposal_areas.append(DisposalArea(x, y))

        # Log agent creation
        self.log_message(f"Simulation Setup: Created {len(self.normal_agents)} normal agents, "
                         f"{len(self.proper_disposers)} proper disposers, "
                         f"{len(self.police_agents)} police agents, "
                         f"{len(self.garbage_collectors)} garbage collectors, "
                         f"{len(self.cameras)} cameras, and "
                         f"{len(self.garbage_items)} garbage items")

    def step(self):
        if self.state != SimulationState.RUNNING:
            return False
        
        # Move and process improper disposers
        for disposer in self.improper_disposers[:]:
            disposer.move(self.width, self.height)
            disposer.dispose_improperly(self.garbage_items)
            self.log_message(f"Improper Disposal: ImproperDisposer at ({disposer.x}, {disposer.y}) disposed garbage")
        
        # Move and process normal agents
        for agent in self.normal_agents[:]:
            agent.move(self.width, self.height)
            if agent.check_improper_disposal(self.garbage_items, self.disposal_areas):
                self.arrests += 1
                self.log_message(f"Improper Disposal: Agent at ({agent.x}, {agent.y}) penalized")

        # Move and process proper disposers
        for disposer in self.proper_disposers:
            disposer.move(self.width, self.height)
            if disposer.collect_garbage(self.garbage_items):
                self.log_message(f"Garbage Collection: Disposer at ({disposer.x}, {disposer.y}) collected garbage")

        # Move and process police agents
        for police in self.police_agents:
            police.move(self.width, self.height)
            new_arrests = police.check_arrest(self.improper_disposers)
            if new_arrests > 0:
                self.arrests += new_arrests
                self.log_message(f"Arrest: Police agent at ({police.x}, {police.y}) arrested {new_arrests} ImproperDisposers")

        # Move and process garbage collectors
        for collector in self.garbage_collectors:
            collector.move(self.width, self.height)
            target = collector.find_target(self.garbage_items)
            if target:
                collector.move_to_target(target)
                if collector.x == target.x and collector.y == target.y:
                    self.log_message(f"Garbage Removal: Collector at ({collector.x}, {collector.y}) removed garbage")
                    self.garbage_items.remove(target)

        # # Process cameras
        # for camera in self.cameras:
        #     detected = camera.detect_illegal_disposal(self.normal_agents)
        #     if detected:
        #         self.log_message(f"Camera Detection: {len(detected)} illegal disposal agents detected")
        #     self.blackboard.extend(detected)
        
        return True

def main():
    pygame.init()

    SCREEN_WIDTH = 1000
    SCREEN_HEIGHT = 600
    CELL_SIZE = 10

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Garbage Management Simulation")

    simulation = GarbageSimulation(
        width=SCREEN_WIDTH // CELL_SIZE, 
        height=SCREEN_HEIGHT // CELL_SIZE
    )

    setup_button = Button(SCREEN_WIDTH - 200, 50, 180, 50, "Setup", GREEN)
    start_button = Button(SCREEN_WIDTH - 200, 150, 180, 50, "Start", BLUE)

    clock = pygame.time.Clock()

    font = pygame.font.Font(None, 36)

    running = True
    step_count = 0
    auto_step = False

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                if setup_button.is_clicked(pos):
                    simulation.state = SimulationState.SETUP
                    simulation.create_agents()
                    step_count = 0
                    simulation.arrests = 0
                    simulation.last_arrest_time = time.time()
                    auto_step = False
                    
                    

                if start_button.is_clicked(pos):
                    if simulation.state == SimulationState.SETUP or simulation.state == SimulationState.STOPPED:
                        simulation.state = SimulationState.RUNNING
                        auto_step = True

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if simulation.state == SimulationState.RUNNING or simulation.state == SimulationState.STOPPED:
                        if simulation.step():
                            step_count += 1

        if auto_step and simulation.state == SimulationState.RUNNING:
            if simulation.step():
                step_count += 1
            simulation.check_arrest_activity()

        screen.fill(BLACK)

        for area in simulation.disposal_areas:
            pygame.draw.rect(screen, BLACK, 
                (area.x * CELL_SIZE, area.y * CELL_SIZE, CELL_SIZE, CELL_SIZE))

        for item in simulation.garbage_items:
            x, y = item.x * CELL_SIZE, item.y * CELL_SIZE
            triangle_points = [
                (x + CELL_SIZE // 2, y),
                (x, y + CELL_SIZE),
                (x + CELL_SIZE, y + CELL_SIZE)
            ]
            pygame.draw.polygon(screen, BROWN, triangle_points)

        for agent_list, color in [
            (simulation.normal_agents, BROWN),
            (simulation.proper_disposers, MAGENTA),
            (simulation.police_agents, YELLOW),
            (simulation.garbage_collectors, GREEN),
            (simulation.cameras, WHITE)
        ]:
            for agent in agent_list:
                pygame.draw.rect(screen, color, 
                    (agent.x * CELL_SIZE, agent.y * CELL_SIZE, CELL_SIZE, CELL_SIZE))

        setup_button.draw(screen)
        start_button.draw(screen)

        state_text = font.render(f"State: {simulation.state.name}", True, WHITE)
        screen.blit(state_text, (SCREEN_WIDTH - 200, 10))

        arrest_text = font.render(f"Penalties: {simulation.arrests}", True, WHITE)
        screen.blit(arrest_text, (10, 10))

        step_text = font.render(f"Steps: {step_count}", True, WHITE)
        screen.blit(step_text, (10, 50))

        pygame.display.flip()

        clock.tick(10)

    pygame.quit()


if __name__ == "__main__":
    main()