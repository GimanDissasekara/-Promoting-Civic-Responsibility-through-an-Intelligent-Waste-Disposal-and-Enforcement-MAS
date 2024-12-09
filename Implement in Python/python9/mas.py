from mesa import *
from mesa.space import MultiGrid
from mesa.time import RandomActivation
import pygame
import random
import numpy as np


class Municipality(Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.color = (255, 165, 0)  # Orange

class NormalAgent(Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.score = 5
        self.color = (165, 42, 42)  # Brown

    def step(self):
        # Random movement
        self.move()
        
        # Check for garbage disposal
        if self.check_garbage_disposal():
            if random.random() < 0.5:  # 50% chance of improper disposal
                self.improper_disposal()

    def move(self):
        possible_steps = self.model.grid.get_neighborhood(
            self.pos, moore=True, include_center=False
        )
        new_position = random.choice(possible_steps)
        self.model.grid.move_agent(self, new_position)

    def check_garbage_disposal(self):
        cell_contents = self.model.grid.get_cell_list_contents([self.pos])
        return any(isinstance(agent, GarbageItem) for agent in cell_contents)

    def improper_disposal(self):
        # Check if in proper disposal area
        if not self.is_proper_disposal_area():
            self.score -= 1
            if self.score <= 0:
                self.model.schedule.remove(self)
                self.model.grid.remove_agent(self)
                self.model.arrests += 1

    def is_proper_disposal_area(self):
        x, y = self.pos
        return x % 10 == 0 and y % 10 == 0

class ProperDisposer(Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.score = 0
        self.color = (255, 0, 255)  # Magenta

    def step(self):
        # Random movement
        self.move()
        
        # Check and dispose of garbage
        cell_contents = self.model.grid.get_cell_list_contents([self.pos])
        garbage_items = [item for item in cell_contents if isinstance(item, GarbageItem)]
        
        if garbage_items:
            for item in garbage_items:
                self.model.grid.remove_agent(item)
                self.model.schedule.remove(item)
                self.score += 1

    def move(self):
        possible_steps = self.model.grid.get_neighborhood(
            self.pos, moore=True, include_center=False
        )
        new_position = random.choice(possible_steps)
        self.model.grid.move_agent(self, new_position)

class GarbageCollector(Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.target = None
        self.color = (0, 255, 0)  # Green

    def step(self):
        # Find a target if no current target
        if not self.target:
            garbage_items = [agent for agent in self.model.schedule.agents 
                             if isinstance(agent, GarbageItem)]
            if garbage_items:
                self.target = random.choice(garbage_items)

        # Move towards target
        if self.target:
            # Simple movement towards target
            x1, y1 = self.pos
            x2, y2 = self.target.pos
            
            # Move one step closer
            new_x = x1 + (1 if x2 > x1 else -1 if x2 < x1 else 0)
            new_y = y1 + (1 if y2 > y1 else -1 if y2 < y1 else 0)
            
            self.model.grid.move_agent(self, (new_x, new_y))

            # Check if reached target
            if self.pos == self.target.pos:
                self.model.grid.remove_agent(self.target)
                self.model.schedule.remove(self.target)
                self.target = None

class PoliceAgent(Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.color = (255, 255, 0)  # Yellow

    def step(self):
        # Random movement
        possible_steps = self.model.grid.get_neighborhood(
            self.pos, moore=True, include_center=False
        )
        new_position = random.choice(possible_steps)
        self.model.grid.move_agent(self, new_position)

        # Check for agents with low score
        cell_contents = self.model.grid.get_cell_list_contents([self.pos])
        low_score_agents = [
            agent for agent in cell_contents 
            if isinstance(agent, NormalAgent) and agent.score <= 0
        ]

        # Arrest low score agents
        for agent in low_score_agents:
            self.model.grid.remove_agent(agent)
            self.model.schedule.remove(agent)
            self.model.arrests += 1

class Camera(Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.detection_range = 5
        self.color = (255, 255, 255)  # White

    def step(self):
        # Detect illegal disposal within range
        nearby_agents = self.model.grid.get_neighbors(
            self.pos, moore=True, radius=self.detection_range
        )
        illegal_agents = [
            agent for agent in nearby_agents 
            if isinstance(agent, NormalAgent) and agent.score <= 0
        ]
        
        if illegal_agents:
            self.model.blackboard.extend(illegal_agents)

class GarbageItem(Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.color = (165, 42, 42)  # Brown

class WasteManagementModel(Model):
    def __init__(self, width=100, height=100):
        self.grid = MultiGrid(width, height, True)
        self.schedule = RandomActivation(self)
        self.running = True
        self.arrests = 0
        self.blackboard = []
        self.width = width
        self.height = height
        
        # Initialize the current ID tracker
        self.current_id = 0

        # Create Municipality
        municipality = Municipality(self.next_id(), self)
        self.schedule.add(municipality)
        x = random.randint(0, width-1)
        y = random.randint(0, height-1)
        self.grid.place_agent(municipality, (x, y))

        # Create agents
        for _ in range(50):
            agent = NormalAgent(self.next_id(), self)
            self.schedule.add(agent)
            x = random.randint(0, width-1)
            y = random.randint(0, height-1)
            self.grid.place_agent(agent, (x, y))

        for _ in range(10):
            agent = ProperDisposer(self.next_id(), self)
            self.schedule.add(agent)
            x = random.randint(0, width-1)
            y = random.randint(0, height-1)
            self.grid.place_agent(agent, (x, y))

        for _ in range(5):
            agent = GarbageCollector(self.next_id(), self)
            self.schedule.add(agent)
            x = random.randint(0, width-1)
            y = random.randint(0, height-1)
            self.grid.place_agent(agent, (x, y))

        for _ in range(5):
            agent = PoliceAgent(self.next_id(), self)
            self.schedule.add(agent)
            x = random.randint(0, width-1)
            y = random.randint(0, height-1)
            self.grid.place_agent(agent, (x, y))

        for _ in range(10):
            agent = Camera(self.next_id(), self)
            self.schedule.add(agent)
            x = random.randint(0, width-1)
            y = random.randint(0, height-1)
            self.grid.place_agent(agent, (x, y))

        for _ in range(20):
            agent = GarbageItem(self.next_id(), self)
            self.schedule.add(agent)
            x = random.randint(0, width-1)
            y = random.randint(0, height-1)
            self.grid.place_agent(agent, (x, y))

# Pygame Visualization
class WasteManagementVisualization:
    def __init__(self, model, width=800, height=800):
        self.model = model
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Waste Management Simulation")
        self.clock = pygame.time.Clock()
        self.cell_width = width / model.width
        self.cell_height = height / model.height

    def draw(self):
        self.screen.fill((200, 200, 200))  # Light gray background

        # Draw grid lines
        for x in range(0, self.width, int(self.cell_width)):
            pygame.draw.line(self.screen, (100, 100, 100), (x, 0), (x, self.height))
        for y in range(0, self.height, int(self.cell_height)):
            pygame.draw.line(self.screen, (100, 100, 100), (0, y), (self.width, y))

        # Draw agents
        for agent in self.model.schedule.agents:
            x, y = agent.pos
            screen_x = int(x * self.cell_width + self.cell_width / 2)
            screen_y = int(y * self.cell_height + self.cell_height / 2)
            
            pygame.draw.circle(
                self.screen, 
                agent.color, 
                (screen_x, screen_y), 
                int(min(self.cell_width, self.cell_height) / 3)
            )

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            # Run one step of the model
            self.model.step()
            
            # Draw the current state
            self.draw()
            
            # Control simulation speed
            self.clock.tick(5)  # 5 FPS

            # Display number of arrests
            print(f"Arrests: {self.model.arrests}")

        pygame.quit()

# Main execution
if __name__ == "__main__":
    # Create the model
    model = WasteManagementModel()
    
    # Create and run visualization
    visualization = WasteManagementVisualization(model)
    visualization.run()