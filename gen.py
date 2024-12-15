import random
import copy
from datetime import datetime, timedelta, time
from tabulate import tabulate

total_buses = int(input())
route_duration_min = timedelta(minutes=50)
route_duration_max = timedelta(minutes=70)
route_time = (route_duration_min + route_duration_max) / 2
days_of_week = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]

# ограничения смен водителей
shift_duration = {"A": 8, "B": 12}
lunch_duration = 1
break_duration = 0.25

# Часы пик и непик
peak_hours = [(time(hour=7), time(hour=9)), (time(hour=17), time(hour=19))]
off_peak_load = 0.5
peak_load = 1


class Route:
    def __init__(self, start, end):
        self.start = start
        self.end = end
        self.is_free = True
        self.bus_id = None
        self.driver_id = None

    def take_route(self, bus_id, driver_id):
        self.is_free = False
        self.bus_id = bus_id
        self.driver_id = driver_id


def create_bus_schedule():
    bus_count_peak_hours = int(peak_load * total_buses)
    bus_count_off_peak_hours = int(off_peak_load * total_buses)

    start_datetime = datetime.combine(datetime.today(), time(6))
    end_datetime = datetime.combine(datetime.today(), time(3)) + timedelta(days=1)

    peak_start_1 = datetime.combine(start_datetime.date(), peak_hours[0][0])
    peak_end_1 = datetime.combine(start_datetime.date(), peak_hours[0][1])
    peak_start_2 = datetime.combine(start_datetime.date(), peak_hours[1][0])
    peak_end_2 = datetime.combine(start_datetime.date(), peak_hours[1][1])

    interval_in_off_peak_hours = (route_duration_min + route_duration_max) // (2 * bus_count_off_peak_hours)

    bus_schedule = {day: [] for day in days_of_week}
    for day in days_of_week:
        current_time = start_datetime
        day_schedule = []
        active_routes = []
        while current_time < end_datetime:
            current_bus_count = bus_count_off_peak_hours
            interval = interval_in_off_peak_hours

            active_routes = [route for route in active_routes if route.end > current_time]

            if ((peak_start_1 <= current_time < peak_end_1) or (peak_start_2 <= current_time < peak_end_2)) \
                    and day not in days_of_week[-2:]:
                current_bus_count = bus_count_peak_hours
                interval = (route_duration_min + route_duration_max) // (2 * bus_count_peak_hours)

            if len(active_routes) < current_bus_count:
                route = Route(start=current_time, end=current_time + ((route_duration_min + route_duration_max) // 2))
                if route.end <= end_datetime:
                    active_routes.append(route)
                    day_schedule.append(route)

            current_time += interval

        bus_schedule[day] = day_schedule
    return bus_schedule


def calculate_fitness(schedule, num_drivers):
    """
    Функция оценки: максимизация закрытых маршрутов и минимизация количества водителей.
    """
    closed_routes = sum(1 for day in schedule.values() for route in day if not route.is_free)
    fitness = closed_routes - 0.2 * num_drivers  # Уменьшение штрафа за количество водителей
    return max(fitness, 0)  # Фитнес не может быть отрицательным


def assign_drivers(schedule, max_drivers):
    driver_id = 1
    drivers = {}
    for day, routes in schedule.items():
        for route in routes:
            if route.is_free:  # Назначаем водителя только на свободные маршруты
                if driver_id not in drivers:
                    drivers[driver_id] = []
                if len(drivers[driver_id]) < max_drivers:
                    route.driver_id = driver_id
                    route.is_free = False
                    drivers[driver_id].append(route)
                else:
                    driver_id += 1


def mutate_schedule(schedule, num_drivers):
    """
    Мутирует расписание: изменяет состояние маршрутов или количество водителей.
    """
    mutated_schedule = copy.deepcopy(schedule)
    for day, routes in mutated_schedule.items():
        for route in routes:
            if random.random() < 0.1:  # 10% шанс изменения маршрута
                if route.is_free:
                    route.take_route(random.randint(1, total_buses), random.randint(1, num_drivers))
                else:
                    route.is_free = True
                    route.bus_id = None
                    route.driver_id = None

    # Изменение количества водителей с небольшим шансом
    if random.random() < 0.1:  # 10% шанс изменения числа водителей
        num_drivers += random.choice([-1, 1])
        num_drivers = max(1, num_drivers)  # Минимум 1 водитель

    return mutated_schedule, num_drivers


def crossover_schedule(schedule1, schedule2, num_drivers1, num_drivers2):
    """
    Выполняет кроссовер расписаний и количества водителей.
    """
    new_schedule = {}
    for day in days_of_week:
        midpoint = len(schedule1[day]) // 2
        new_schedule[day] = schedule1[day][:midpoint] + schedule2[day][midpoint:]

    # Среднее значение количества водителей
    new_num_drivers = (num_drivers1 + num_drivers2) // 2
    return new_schedule, new_num_drivers


def genetic_algorithm(initial_schedule, generations=100, population_size=50):
    """
    Генетический алгоритм для оптимизации расписания и количества водителей.
    """
    population = [(copy.deepcopy(initial_schedule), random.randint(5, 15)) for _ in range(population_size)]
    best_schedule = None
    best_num_drivers = 0
    best_fitness = float('-inf')

    for _ in range(generations):
        fitness_scores = [calculate_fitness(schedule, num_drivers) for schedule, num_drivers in population]

        # Проверяем и корректируем нулевую сумму фитнесов
        if sum(fitness_scores) == 0:
            fitness_scores = [1 for _ in fitness_scores]  # Устанавливаем минимальные положительные значения

        best_index = fitness_scores.index(max(fitness_scores))
        if fitness_scores[best_index] > best_fitness:
            best_fitness = fitness_scores[best_index]
            best_schedule, best_num_drivers = population[best_index]

        new_population = []
        for _ in range(population_size // 2):
            parent1, parent2 = random.choices(population, weights=fitness_scores, k=2)
            child_schedule, child_num_drivers = crossover_schedule(parent1[0], parent2[0], parent1[1], parent2[1])
            child_schedule, child_num_drivers = mutate_schedule(child_schedule, child_num_drivers)
            new_population.extend([parent1, parent2, (child_schedule, child_num_drivers)])

        population = new_population[:population_size]

    return best_schedule, best_num_drivers


def display_schedule(bus_schedule, num_drivers):
    """
    Вывод расписания и количества водителей.
    """
    table = []
    for day, routes in bus_schedule.items():
        table.append([f"=== {day.upper()} ===", "", "", ""])
        for route in routes:
            table.append([
                f"Водитель: {route.driver_id or 'Свободно'}",
                f"Начало: {route.start.strftime('%H:%M')}",
                f"Конец: {route.end.strftime('%H:%M')}",
                f"Автобус: {route.bus_id or 'Свободно'}"
            ])
        table.append(["", "", "", ""])

    print(tabulate(table, headers=["Водитель", "Начало", "Конец", "Автобус"], tablefmt="grid"))
    print(f"\nОптимальное количество водителей: {num_drivers}")


# Основная программа
initial_schedule = create_bus_schedule()
optimized_schedule, optimal_drivers = genetic_algorithm(initial_schedule)
display_schedule(optimized_schedule, optimal_drivers)