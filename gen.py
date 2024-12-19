import copy
from datetime import datetime, timedelta, time
import random
from tabulate import tabulate

total_buses = int(input())  # Кол-во автобусов
route_duration_min = timedelta(minutes=50)  # Минимальная продолжительность маршрута
route_duration_max = timedelta(minutes=70)  # Максимальная продолжительность маршрута
days_of_week = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]

shift_duration = {0: "A", 1: "B"}  # Тип водителя

# Час пик и нагрузки
peak_hours = [(time(hour=7), time(hour=9)), (time(hour=17), time(hour=19))]

off_peak_load = 0.5
peak_load = 1

population_size = 50
generations = 25
mutation_percent = 0.2
min_individual_size = total_buses * 2
max_individual_size = total_buses * 5


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
    bus_count_peak_hours = int(peak_load * total_buses)  # Округление вниз
    bus_count_off_peak_hours = int(off_peak_load * total_buses)

    start_datetime = datetime.combine(datetime.today(), time(6))  # Начало в 6:00
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


def calculate_drivers_breaks(driver_type, start):
    breaks = []
    if driver_type == "A":
        breaks.append((start + timedelta(hours=4), start + timedelta(hours=5)))
    else:
        current_time = start + timedelta(hours=2, minutes=15)
        while current_time < start + timedelta(hours=12):
            breaks.append((current_time - timedelta(minutes=15), current_time))
            current_time += timedelta(hours=2, minutes=15)

    breaks = [break_ for break_ in breaks
              if break_[0] < datetime.combine(datetime.today(), time(3)) + timedelta(days=1) and
              break_[1] < datetime.combine(datetime.today(), time(3)) + timedelta(days=1)]
    return breaks


def can_get_route(route, breaks):
    for break_ in breaks:
        if not (route.end <= break_[0] or route.start >= break_[1]):
            return False
    return True


def get_driver_week_schedule(schedule, start_route, start_day, driver_id, driver_type, bus_id):
    week_driver_routes = {}
    start_route.take_route(bus_id, driver_id)

    start_day_idx = days_of_week.index(start_day)
    weekends = []
    if driver_type == "A":
        weekends = copy.copy(days_of_week[-2:])
        shift_ending = start_route.start + timedelta(hours=9)
    else:
        shift_ending = start_route.start + timedelta(hours=12)
        work_days = []
        while start_day_idx <= len(days_of_week[1:]):
            work_days.append(days_of_week[start_day_idx])
            start_day_idx += 3
        weekends.extend([i for i in days_of_week if i not in work_days])

    for day, routes in schedule.items():
        if day in weekends:
            continue

        driver_routes = []
        if day == start_day:
            driver_routes.append(start_route)
        breaks = calculate_drivers_breaks(driver_type, start_route.start)
        for route in routes:
            if route.start == start_route.start and route.end == start_route.end and route.is_free:
                driver_routes.append(route)
                route.take_route(bus_id, driver_id)

            elif not route.is_free:
                continue

            if route.start >= shift_ending or route.end >= shift_ending:
                break

            if driver_routes and driver_routes[-1].end <= route.start and can_get_route(route, breaks):
                driver_routes.append(route)
                route.take_route(bus_id=bus_id, driver_id=driver_id)

        if driver_routes:
            week_driver_routes[day] = driver_routes
    return week_driver_routes


def sum_closed_routes(schedule):
    cnt = 0
    for day, routes in schedule.items():
        for route in routes:
            if not route.is_free:
                cnt += 1
    return cnt


def create_schedule(schedule, drivers):
    buses = {}
    for day in days_of_week:
        day_buses = {}
        for i in range(total_buses):
            day_buses[i] = (datetime.combine(datetime.today(), time(hour=6)),
                            datetime.combine(datetime.today(), time(hour=6)))
        buses[day] = day_buses

    for day, routes in schedule.items():
        for route in routes:
            if not route.is_free:
                continue

            for bus_id, shift_time in buses[day].items():
                if not (shift_time[1] <= route.start or shift_time[0] >= route.end):
                    if all(not (st[1] <= route.start or st[0] >= route.end) for st in buses[day].values()):
                        route.is_free = False
                    continue

                if shift_time[1] <= route.start:
                    if drivers:
                        gen = drivers.pop(-1)
                        driver = get_driver_week_schedule(schedule=schedule, driver_id=len(drivers),
                                                          driver_type=shift_duration[gen], bus_id=bus_id,
                                                          start_route=route,
                                                          start_day=day)

                        if list(driver.values()):
                            driver_start = list(driver.values())[0][0].start
                            driver_end = list(driver.values())[0][-1].end
                            buses[day][bus_id] = (driver_start, driver_end)
                            break

    return schedule


def fitness(individual):
    occupied_routes = sum(individual)

    driver_count = individual.count(1)

    penalty = driver_count * 0.1  # Чем больше водителей, тем больше штраф

    return occupied_routes - penalty


def sum_all_routes():
    cnt = 0
    for day, routes in create_bus_schedule().items():
        for _ in routes:
            cnt += 1
    return cnt


all_routes_count = sum_all_routes()

base_schedule = create_bus_schedule()  # Кэшируемое расписание для более быстрого выполнения


def tournament_selection(population, fitnesses):
    i1, i2 = random.sample(range(len(population)), 2)
    return population[i1] if fitnesses[i1] > fitnesses[i2] else population[i2]


def crossover(parent1, parent2):
    point = random.randint(0, min(len(parent1), len(parent2)) - 1)
    child1 = parent1[:point] + parent2[point:]
    child2 = parent2[:point] + parent1[point:]

    return child1, child2


def mutate(individual):
    if random.random() < mutation_percent:
        point = random.randint(0, len(individual) - 1)
        individual[point] = 1 - individual[point]
    return individual


def genetic_algorithm():
    population = initialize_population(population_size)

    for generation in range(generations):
        fitnesses = [fitness(individual) for individual in population]
        print(f"Generation: {generation}, Best fitness: {max(fitnesses)}")

        # Сохранение лучших индивидов
        num_parents = population_size // 2
        new_population = sorted(zip(population, fitnesses), key=lambda x: x[1], reverse=True)[:num_parents]
        new_population = [x[0] for x in new_population]

        # Выбор родителей
        while len(new_population) < population_size:
            parent1 = tournament_selection(population, fitnesses)
            parent2 = tournament_selection(population, fitnesses)
            child1, child2 = crossover(parent1, parent2)
            new_population.append(mutate(child1))
            new_population.append(mutate(child2))

        population = new_population[:population_size]

    best_individual = max(population, key=fitness)
    return best_individual


def initialize_population(size):
    return [generate_individual() for _ in range(size)]


def generate_individual():
    length = random.randint(min_individual_size, max_individual_size)
    return [random.choice([0, 1]) for _ in range(length)]


def display_schedule(bus_schedule):
    table = []
    for day, routes in bus_schedule.items():
        table.append([f"=== {day.upper()} ===", "", "", ""])
        for route in routes:
            table.append([
                f"Водитель: {route.driver_id}",
                f"Начало: {route.start.strftime('%H:%M')}",
                f"Конец: {route.end.strftime('%H:%M')}",
                f"Автобус: {route.bus_id}"
            ])
        table.append(["", "", "", ""])

    print(tabulate(table, headers=["Водитель", "Начало", "Конец", "Автобус"], tablefmt="grid"))


# Запуск ген алгоритма и вывод расписания
bus_schedule = create_bus_schedule()
best_individual = genetic_algorithm()
print(best_individual)
print("Количество водителей:", len(best_individual))
bus_schedule = create_schedule(bus_schedule, best_individual)
display_schedule(bus_schedule)