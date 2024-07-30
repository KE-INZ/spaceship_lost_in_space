# Part 1: Imports and Classes

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from stl import mesh
import numpy as np
import tkinter as tk
import threading
import os.path
import logging
import math

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Anomaly:
    def __init__(self):
        self.background_texture = None

    def add_background(self):
        try:
            self.background_texture = pygame.image.load("textures/background/milky_way.png")
        except pygame.error as e:
            logging.error(f"Error loading background texture: {e}")
            return

        logging.info(f"Background texture loaded: {self.background_texture.get_size()}")

        quad = gluNewQuadric()
        gluQuadricNormals(quad, GLU_SMOOTH)
        gluQuadricTexture(quad, GL_TRUE)

        glEnable(GL_TEXTURE_2D)
        texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        texture_data = pygame.image.tostring(self.background_texture, "RGB", 1)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, self.background_texture.get_width(), self.background_texture.get_height(), 0, GL_RGB, GL_UNSIGNED_BYTE, texture_data)

        glColor3f(1.0, 1.0, 1.0)
        glPushMatrix()
        glRotatef(90, 1, 0, 0)
        gluSphere(quad, 800, 500, 500)
        glPopMatrix()
        glDisable(GL_TEXTURE_2D)

        self.draw_nebula()

    def draw_nebula(self):
        num_particles = 100
        particle_size = 0.57

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glPointSize(particle_size)

        glBegin(GL_POINTS)
        glColor4f(1.0, 1.0, 1.0, 0.5)
        for _ in range(num_particles):
            x = np.random.uniform(-100, 100)
            y = np.random.uniform(-100, 100)
            z = np.random.uniform(-100, 100)
            glVertex3f(x, y, z)
        glEnd()

        glDisable(GL_BLEND)

    @staticmethod
    def draw_stars(stars):
        glDisable(GL_LIGHTING)
        glBegin(GL_POINTS)
        glColor3f(1.0, 1.0, 1.0)
        for star in stars:
            glVertex3f(*star)
        glEnd()
        glEnable(GL_LIGHTING)

class Spaceship:
    def __init__(self):
        self.position = np.zeros(3)
        self.velocity = np.zeros(3)
        self.acceleration = np.zeros(3)
        self.rotation = np.zeros(3)
        self.angular_velocity = np.zeros(3)
        self.max_speed = 0.5
        self.acceleration_rate = 0.05
        self.rotation_rate = 0.4

    def update(self, dt):
        self.velocity += self.acceleration * dt
        self.velocity *= 0.99  # Add friction to limit speed
        self.position += self.velocity * dt
        self.angular_velocity *= 0.95  # Add friction for rotation

        self.rotation += self.angular_velocity * dt
        self.rotation = np.clip(self.rotation, -np.pi / 4, np.pi / 4)

    def apply_thrust(self, thrust_vector):
        self.acceleration = thrust_vector * self.acceleration_rate

    def rotate(self, dx, dy, clockwise=False, counterclockwise=False):
        self.angular_velocity[0] += dy * self.rotation_rate
        self.angular_velocity[1] += dx * self.rotation_rate

        if clockwise:
            self.angular_velocity[2] += self.rotation_rate
        if counterclockwise:
            self.angular_velocity[2] -= self.rotation_rate

        self.rotation[0] += dy * self.rotation_rate
        self.rotation[1] += dx * self.rotation_rate
        self.rotation[0] = np.clip(self.rotation[0], -np.pi / 4, np.pi / 4)

    def move_forward(self):
        thrust_vector = np.array([
            -np.sin(self.rotation[1]) * np.cos(self.rotation[0]),
            np.sin(self.rotation[0]),
            -np.cos(self.rotation[1]) * np.cos(self.rotation[0])
        ])
        self.apply_thrust(thrust_vector)

    def move_backward(self):
        thrust_vector = np.array([
            np.sin(self.rotation[1]) * np.cos(self.rotation[0]),
            -np.sin(self.rotation[0]),
            np.cos(self.rotation[1]) * np.cos(self.rotation[0])
        ])
        self.apply_thrust(thrust_vector)

    def get_camera_position(self):
        return self.position

    def get_camera_target(self):
        x = self.position[0] - np.sin(self.rotation[1]) * np.cos(self.rotation[0])
        y = self.position[1] + np.sin(self.rotation[0])
        z = self.position[2] - np.cos(self.rotation[1]) * np.cos(self.rotation[0])
        return np.array([x, y, z])

class Planet:
    def __init__(self, name, diameter, distance, texture_path, orbital_speed, start_angle, rotation_speed):
        self.name = name
        self.diameter = diameter
        self.distance = distance
        self.texture_path = texture_path
        self.orbital_speed = orbital_speed
        self.angle = start_angle
        self.rotation_speed = rotation_speed
        self.rotation_angle = 0
        self.position = np.array([distance * np.cos(start_angle), 0, distance * np.sin(start_angle)])
        self.texture_id = self.load_texture()

    def update_position(self, dt):
        self.angle += self.orbital_speed * dt
        self.rotation_angle += self.rotation_speed * dt
        angle_rad = np.radians(self.angle)
        self.position = np.array([self.distance * np.cos(angle_rad), 0, self.distance * np.sin(angle_rad)])

    def load_texture(self):
        try:
            texture_surface = pygame.image.load(self.texture_path)
        except pygame.error as e:
            logging.error(f"Error loading texture: {e}")
            return None

        texture_surface = self.scale_texture(texture_surface, 2048)
        texture_data = pygame.image.tostring(texture_surface, 'RGBA', 1)
        width, height = texture_surface.get_rect().size

        logging.info(f"Loading texture: {self.texture_path}")
        logging.info(f"Texture size: {width}x{height}")

        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        try:
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, texture_data)
        except OpenGL.error.GLError as e:
            logging.error(f"OpenGL error loading texture: {e}")
            return None

        glBindTexture(GL_TEXTURE_2D, 0)
        return texture

    @staticmethod
    def scale_texture(texture_surface, max_size):
        width, height = texture_surface.get_rect().size
        if width > max_size or height > max_size:
            scaling_factor = max_size / max(width, height)
            new_width = int(width * scaling_factor)
            new_height = int(height * scaling_factor)
            texture_surface = pygame.transform.smoothscale(texture_surface, (new_width, new_height))
        return texture_surface

    def draw(self):
        glPushMatrix()
        glTranslatef(*self.position)
        glRotatef(np.degrees(self.angle), 0, 1, 0)
        glRotatef(180, 0, 0, 1)
        glRotatef(np.degrees(self.rotation_angle), 0, 1, 0)

        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        quad = gluNewQuadric()
        gluQuadricNormals(quad, GLU_SMOOTH)
        gluQuadricTexture(quad, GL_TRUE)
        glRotatef(90, 1, 0, 0)

        glPushMatrix()
        gluSphere(quad, self.diameter / 2, 32, 32)
        glPopMatrix()

        glMaterialfv(GL_FRONT, GL_AMBIENT_AND_DIFFUSE, (1.0, 1.0, 1.0, 1.0))
        gluSphere(quad, self.diameter / 2, 32, 32)
        glDisable(GL_TEXTURE_2D)

        glPopMatrix()



# Part 2: Helper Functions

def init_opengl(display, sun_position):
    pygame.init()
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption('Spaceship Game')

    glEnable(GL_DEPTH_TEST)
    glEnable(GL_TEXTURE_2D)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

    glMatrixMode(GL_PROJECTION)
    gluPerspective(45, display[0] / display[1], 0.1, 1000.0)
    glMatrixMode(GL_MODELVIEW)

    glTranslatef(0.0, 0.0, -20)

    glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (0.2, 0.2, 0.2, 1.0))
    glLightfv(GL_LIGHT0, GL_POSITION, (*sun_position, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (1.0, 1.0, 0.8, 1.0))
    glLightfv(GL_LIGHT0, GL_SPECULAR, (1.0, 1.0, 1.0, 1.0))

    glLightf(GL_LIGHT0, GL_CONSTANT_ATTENUATION, 1.0)
    glLightf(GL_LIGHT0, GL_LINEAR_ATTENUATION, 0.0)
    glLightf(GL_LIGHT0, GL_QUADRATIC_ATTENUATION, 0.0001)

    glMaterialfv(GL_FRONT, GL_SPECULAR, (0.5, 0.5, 0.5, 1.0))
    glMaterialf(GL_FRONT, GL_SHININESS, 50.0)

    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    glEnable(GL_STENCIL_TEST)

def create_planets():
    planets = []
    planets_data = [
        ("Sun", 2.0, 0, "textures/planeten/sonne/sun.png", 0, 0),
        ("Mercury", 0.4, 10, "textures/planeten/merkur/mercury.png", 0.2, 0.1),
        ("Venus", 0.9, 20, "textures/planeten/venus/venus.png", 0.16, 0.05),
        ("Earth", 1.0, 30, "textures/planeten/erde/earth.jpg", 0.14, 0.03),
        ("Mars", 0.5, 40, "textures/planeten/mars/mars.png", 0.12, 0.02),
        ("Jupiter", 2.0, 50, "textures/planeten/jupiter/jupiter.png", 0.10, 0.015),
        ("Saturn", 1.8, 60, "textures/planeten/saturn/saturn.png", 0.08, 0.01),
        ("Uranus", 1.5, 70, "textures/planeten/uranus/uranus.png", 0.06, 0.005),
        ("Neptune", 1.5, 80, "textures/planeten/neptun/neptune.png", 0.04, 0.003),
        ("Pluto", 0.2, 90, "textures/planeten/pluto/pluto.png", 0.02, 0.001)
    ]

    for name, diameter, distance, texture_path, orbital_speed, rotation_speed in planets_data:
        start_angle = np.random.uniform(0, 2 * np.pi)
        if os.path.exists(texture_path):
            planets.append(Planet(name, diameter, distance, texture_path, orbital_speed, start_angle, rotation_speed))
        else:
            logging.warning(f"Texture file {texture_path} not found.")

    return planets

def update_planets(planets, dt):
    for planet in planets:
        planet.update_position(dt)

def create_stars(num_stars=1000):
    return np.random.rand(num_stars, 3) * 200 - 100

def handle_mouse_events(event, movement, yaw, pitch):
    mouse_sensitivity = 0.4
    if event.type == MOUSEMOTION:
        dx, dy = event.rel
        if dy != 0:  # Vertikale Bewegung
            pitch += dy * mouse_sensitivity  # Invertiere die vertikale Bewegung
            pitch += np.clip(pitch, -89, 89)

        if dx != 0:  # Horizontale Bewegung
            yaw += dx * mouse_sensitivity  # Invertiere die horizontale Bewegung



def handle_keyboard_events(spaceship, keys):
    if keys[K_q]:
        print("Q")
        spaceship.rotate(0, 0, clockwise=True)
    elif keys[K_e]:
        print("E")
        spaceship.rotate(90, 0, counterclockwise=True)
    elif keys[K_w]:
        spaceship.move_forward()
    elif keys[K_s]:
        spaceship.move_backward()

    return keys


def pygame_thread(root, distance_var, speed_var, life_points_var, structure_var, collided_planets_var, spaceship):
    display = (1200, 900)
    sun_position = (0, 0, 0)

    clock = pygame.time.Clock()

    init_opengl(display, sun_position)

    planets = create_planets()

    spaceship_mesh = mesh.Mesh.from_file('models/superman.stl')
    vertices = spaceship_mesh.vectors.reshape(-1, 3)
    normals = spaceship_mesh.normals

    stars = np.random.rand(1000, 3) * 200 - 100

    movement = np.array([100, 0, 0], dtype=float)
    velocity = np.array([0, 0, 0], dtype=float)

    max_speed = 0.5
    acceleration = 0.05
    friction = 0.9
    collision_distance = 1.0

    lasers = []
    laser_speed = 1.0
    laser_length = 0.2  # Set your desired length for the laser
    laser_radius = 0.001  # Set your desired radius for the laser

    mouse_sensitivity = 0.4
    yaw, pitch = 0, 0

    life_points = 1000
    structure_points = 500

    collided_planets = []



    def handle_shield_depletion():
        nonlocal life_points, structure_points
        if life_points <= 0:
            life_points = 0
            if structure_points > 0 and any(
                    np.linalg.norm(planet.position - movement) < planet.diameter / 2 + collision_distance for planet in
                    planets):
                structure_points -= 10  # Reduzieren der Strukturpunkte
                if structure_points <= 0:
                    structure_points = 0



    def add_collided_planet(planet_name):
        if planet_name not in collided_planets:
            collided_planets.append(planet_name)

    def draw_laser(start_pos, direction, length, radius):
        # Normalize direction vector
        length_dir = math.sqrt(direction[0] ** 2 + direction[1] ** 2 + direction[2] ** 2)
        direction = (
            direction[0] / length_dir,
            direction[1] / length_dir,
            direction[2] / length_dir
        )

        # Compute the angles to align the cylinder with the direction
        angle_x = math.atan2(direction[1], direction[2])
        angle_y = math.atan2(direction[0], direction[2])

        glPushMatrix()
        glColor3f(1.0, 0.0, 0.0)  # Red color for laser
        glTranslatef(start_pos[0], start_pos[1], start_pos[2])

        # Rotate around Y-axis to align with direction in the XZ plane
        glRotatef(math.degrees(angle_y), 0, 1, 0)
        # Rotate around X-axis to align with direction in the XY plane
        glRotatef(math.degrees(angle_x), 1, 0, 0)

        # Draw the laser beam as a cylinder
        glPushMatrix()
        glTranslatef(0, 0, -length / 2.0)
        gluCylinder(gluNewQuadric(), radius, radius, length, 16, 16)
        glPopMatrix()

        glPopMatrix()

    def debug_draw_laser(laser):
        start_pos, direction = laser
        print(f"Laser Start: {start_pos}, Direction: {direction}")

        # Optional: Draw a reference line to visualize laser direction
        glColor3f(0.0, 1.0, 0.0)  # Green color for debug line
        glBegin(GL_LINES)
        glVertex3f(start_pos[0], start_pos[1], start_pos[2])
        end_pos = (
            start_pos[0] + direction[0] * 100,  # Extend the line 100 units in direction
            start_pos[1] + direction[1] * 100,
            start_pos[2] + direction[2] * 100
        )
        glVertex3f(end_pos[0], end_pos[1], end_pos[2])
        glEnd()

    def get_laser_start_position(spaceship_position, laser_offset):
        return (
            spaceship_position[0] + laser_offset[0],
            spaceship_position[1] + laser_offset[1],
            spaceship_position[2] + laser_offset[2]
        )

    def calculate_laser_direction(spaceship_direction, offset_angle):
        # Adjust the direction based on the spaceship's current direction and offset angle
        return (
            spaceship_direction[0] * math.cos(offset_angle) - spaceship_direction[1] * math.sin(offset_angle),
            spaceship_direction[0] * math.sin(offset_angle) + spaceship_direction[1] * math.cos(offset_angle),
            spaceship_direction[2]  # Assuming the laser direction is in the same plane
        )

    def render_scene():
        # Zeichne den Hintergrund, Planeten und das Raumschiff
        # draw_background()
        # draw_planets()
        # draw_spaceship()
        pass

        # Zeichne die Laserstrahlen
        glDisable(GL_LIGHTING)  # Lichter deaktivieren, um Laserstrahlen klarer zu sehen
        for laser in lasers:
            start_pos, direction = laser
            draw_laser(start_pos, direction, laser_length, laser_radius)
        glEnable(GL_LIGHTING)  # Lichter wieder aktivieren

    def check_laser_collisions():
        for laser in lasers:
            start_pos, direction = laser
            for planet in planets:
                # Berechne den Abstand zwischen dem Laserstrahl und dem Planeten
                # (Implementiere hier die Kollisionserkennung)
                # Wenn Kollision erkannt:
                print(f"Laser hit {planet.name}")
                lasers.remove(laser)  # Entferne den Laserstrahl, wenn er einen Treffer erzielt hat
                break

    def handle_laser_movement(dt):
        global lasers
        new_lasers = []
        for laser in lasers:
            start_pos, direction = laser
            start_pos += direction * laser_speed * dt
            new_lasers.append([start_pos, direction])
        lasers = new_lasers

    laser_lifetime = 5.0  # Zeit in Sekunden, die ein Laserstrahl aktiv bleibt

    def update_lasers(dt):
        global lasers
        new_lasers = []
        for laser in lasers:
            start_pos, direction = laser
            start_pos += direction * laser_speed * dt
            # Überprüfe, ob der Laserstrahl noch aktiv ist
            if np.linalg.norm(start_pos) < laser_lifetime:
                new_lasers.append([start_pos, direction])
        lasers = new_lasers

    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False

            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False

                if event.type == KEYDOWN:
                    if event.key == K_SPACE:
                        # Position des Raumschiffs als Startposition des Lasers verwenden
                        laser_position = movement.copy()
                        # Berechnung der Blickrichtung und Umkehren
                        laser_direction = np.array([
                            np.sin(np.radians(yaw)) * np.cos(np.radians(pitch)),  # x-Komponente
                            -np.sin(np.radians(pitch)),  # y-Komponente
                            np.cos(np.radians(yaw)) * np.cos(np.radians(pitch))  # z-Komponente
                        ])
                        # Normalisiere den Richtungsvektor
                        laser_direction = laser_direction / np.linalg.norm(laser_direction)
                        lasers.append([laser_position, laser_direction])

            if event.type == MOUSEMOTION:
                handle_mouse_events(event, movement, yaw, pitch)
                dx, dy = event.rel
                yaw -= dx * mouse_sensitivity  # Invertierte Bewegung
                pitch += dy * mouse_sensitivity  # Invertierte Bewegung
                pitch = np.clip(pitch, -89, 89)

        keys = pygame.key.get_pressed()

        # Übergeben Sie das spaceship-Objekt an die handle_keyboard_events-Funktion
        handle_keyboard_events(spaceship, keys)
        # Aktualisiere die Position der Planeten
        update_planets(planets, dt)

        velocity_change = np.array([0, 0, 0], dtype=float)

        if keys[K_s]:
            velocity_change += np.array([
                -np.sin(np.radians(yaw)) * np.cos(np.radians(pitch)),
                np.sin(np.radians(pitch)),
                -np.cos(np.radians(yaw)) * np.cos(np.radians(pitch))
            ])

        if keys[K_w]:
            velocity_change -= np.array([
                -np.sin(np.radians(yaw)) * np.cos(np.radians(pitch)),
                np.sin(np.radians(pitch)),
                -np.cos(np.radians(yaw)) * np.cos(np.radians(pitch))
            ])

        if keys[K_a]:
            velocity_change += np.array([
                np.sin(np.radians(yaw + 90)),
                0,
                np.cos(np.radians(yaw + 90))
            ])

        if keys[K_d]:
            velocity_change += np.array([
                np.sin(np.radians(yaw - 90)),
                0,
                np.cos(np.radians(yaw - 90))
            ])

        if np.linalg.norm(velocity_change) > 0:
            velocity_change = velocity_change / np.linalg.norm(velocity_change) * acceleration

        velocity += velocity_change
        if np.linalg.norm(velocity) > max_speed:
            velocity = velocity / np.linalg.norm(velocity) * max_speed

        movement += velocity
        velocity *= friction

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        camera_distance = 1.05  # näher heranzoomen und Abstand zwischen Kamera und Raumschiff

        glLoadIdentity()
        gluLookAt(
            movement[0] - np.sin(np.radians(yaw)) * np.cos(np.radians(pitch)) * camera_distance,
            # Kameraposition (Augen)
            movement[1] + np.sin(np.radians(pitch)) * camera_distance,  # Kameraposition (Augen)
            movement[2] - np.cos(np.radians(yaw)) * np.cos(np.radians(pitch)) * camera_distance,
            # Kameraposition (Augen)
            movement[0] - np.sin(np.radians(yaw)) * np.cos(np.radians(pitch)),  # Zielpunkt (Mittelpunkt)
            movement[1] + np.sin(np.radians(pitch)),  # Zielpunkt (Mittelpunkt)
            movement[2] - np.cos(np.radians(yaw)) * np.cos(np.radians(pitch)),  # Zielpunkt (Mittelpunkt)
            0, 1, 0  # Up-Vektor (normalerweise die y-Achse)
        )


        glBegin(GL_POINTS)
        for star in stars:
            glVertex3fv(star)
        glEnd()

        glPushMatrix()
        glTranslatef(movement[0], movement[1], movement[2])
        glBegin(GL_TRIANGLES)
        for i in range(len(vertices)):
            glNormal3fv(normals[i // 3])
            glVertex3fv(vertices[i])
        glEnd()
        glPopMatrix()

        anom = Anomaly()  # Instanziierung der Anomalie-Klasse
        # Hinzufügen des Hintergrunds
        anom.add_background()
        anom.draw_stars(stars)

        update_planets(planets, dt)
        for planet in planets:
            planet.draw()

        render_scene()

        for planet in planets:
            distance_to_planet = np.linalg.norm(planet.position - movement)
            if distance_to_planet < planet.diameter / 2 + collision_distance:
                life_points -= 10
                add_collided_planet(planet.name)
                if life_points <= 0:
                    life_points = 0
                elif life_points == 0:
                    structure_points -= 10

        if life_points == 0 and structure_points <= 0:
            print("Game Over")
            running = False

        distance_var.set(f"{np.linalg.norm(movement):.2f} km")
        speed_var.set(f"{np.linalg.norm(velocity):.2f} km/s")
        life_points_var.set(str(life_points))
        structure_var.set(str(structure_points))
        collided_planets_var.set(", ".join(collided_planets))
        root.update_idletasks()

        handle_shield_depletion()

        pygame.display.flip()

    pygame.quit()


def main():
    root = tk.Tk()
    root.title("Spaceship Game Stats")

    distance_var = tk.StringVar()
    speed_var = tk.StringVar()
    life_points_var = tk.StringVar()
    structure_var = tk.StringVar()
    collided_planets_var = tk.StringVar()

    tk.Label(root, text="Entfernung zur Sonne:").grid(row=0, column=0, sticky="w")
    tk.Label(root, textvariable=distance_var).grid(row=0, column=1, sticky="w")

    tk.Label(root, text="Geschwindigkeit:").grid(row=1, column=0, sticky="w")
    tk.Label(root, textvariable=speed_var).grid(row=1, column=1, sticky="w")

    tk.Label(root, text="Schutzschild:").grid(row=2, column=0, sticky="w")
    tk.Label(root, textvariable=life_points_var).grid(row=2, column=1, sticky="w")

    tk.Label(root, text="Raumschiff-Struktur:").grid(row=3, column=0, sticky="w")
    tk.Label(root, textvariable=structure_var).grid(row=3, column=1, sticky="w")

    tk.Label(root, text="Kollidierte Planeten:").grid(row=4, column=0, sticky="w")
    tk.Label(root, textvariable=collided_planets_var).grid(row=4, column=1, sticky="w")

    # Raumschiff erstellen
    spaceship = Spaceship()

    # Übergeben Sie das spaceship-Objekt an die pygame_thread-Funktion
    pygame_thread_args = (root, distance_var, speed_var, life_points_var, structure_var, collided_planets_var, spaceship)
    pygame_thread_instance = threading.Thread(target=pygame_thread, args=pygame_thread_args)
    pygame_thread_instance.start()

    def key_event_loop():
        while True:
            keys = pygame.key.get_pressed()
            handle_keyboard_events(keys)
            pygame.time.delay(10)  # kleine Verzögerung, um die CPU-Auslastung zu reduzieren

    key_thread = threading.Thread(target=key_event_loop)
    key_thread.start()

    root.mainloop()


if __name__ == "__main__":
    main()
