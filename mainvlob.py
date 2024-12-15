import copy
from datetime import datetime, timedelta, time
from tabulate import tabulate

# Параметры задачи
total_buses = 8  # Пользователь указывает количество автобусов
route_duration_min = timedelta(minutes=50)  # Минимальное время маршрута (в минутах)
route_duration_max = timedelta(minutes=70)  # Максимальное время маршрута (в минутах)
days_of_week = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]

# Ограничения смен водителей
lunch_duration = 1  # Длительность обеденного перерыва (в часах)
break_duration = 0.25  # Длительность коротких перерывов для типа B (в часах)

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
    bus_count_peak_hours = int(peak_load * total_buses)  # округление вниз
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


def calculate_drivers_breaks(driver_type, start):  # возвращает время начала конца перерыва
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
        # Проверяем на пересечение
        if not (route.end <= break_[0] or route.start >= break_[1]):
            return False  # Пересечение найдено
    return True  # Пересечений нет


def get_driver_week_schedule(schedule, start_route, driver_id, driver_type,
                             bus_id):
    week_driver_routes = {}

    start_route.take_route(bus_id, driver_id)

    start_day = None
    for day, routes in schedule.items():
        if start_day is not None:
            break
        for route in routes:
            if route.start == start_route.start:
                start_day = day
                break
    start_day_idx = days_of_week.index(start_day)
    weekends = []
    if driver_type == "A":
        weekends = copy.copy(days_of_week[-2:])
        shift_ending = start_route.start + timedelta(hours=9)
    else:
        shift_ending = start_route.start + timedelta(hours=12)
        work_days = []
        while start_day_idx <= len(days_of_week[1:]) - 1:
            work_days.append(days_of_week[start_day_idx])
            start_day_idx += 3
        weekends.extend([i for i in days_of_week if i not in work_days])

    for day, routes in schedule.items():
        if day in weekends and driver_type == "A":
            continue

        driver_routes = []
        breaks = calculate_drivers_breaks(driver_type, start_route.start)
        for route in routes:

            if route.start == start_route.start and route.end == start_route.end and route.is_free:
                driver_routes.append(route)
                route.take_route(bus_id, driver_id)

            elif not route.is_free:
                continue

            if route.start >= shift_ending or route.end >= shift_ending:
                break

            if driver_routes:
                if driver_routes[-1].end <= route.start and can_get_route(route, breaks):
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


def create_schedule():
    drivers = []
    days_of_week.insert(0, "фантомный пон")
    buses = {}
    for day in days_of_week:
        day_buses = {}
        for i in range(total_buses):  # Индексы автобуса
            day_buses[i] = (datetime.combine(datetime.today(), time(hour=6)),
                            datetime.combine(datetime.today(), time(hour=6)))
        buses[day] = day_buses

    bus_schedule = create_bus_schedule()
    for day, routes in bus_schedule.items():

        for route in routes:
            if not route.is_free:
                continue

            for bus_id, shift_time in buses[day].items():
                if not (shift_time[1] <= route.start or shift_time[0] >= route.end):
                    if all(not (st[1] <= route.start or st[0] >= route.end) for st in buses[day].values()):
                        route.is_free = False
                    continue
                if shift_time[1] <= route.start:

                    test_schedule = copy.deepcopy(bus_schedule)
                    test_driver = get_driver_week_schedule(schedule=test_schedule, driver_id=len(drivers) + 1,
                                                           driver_type="A", bus_id=bus_id, start_route=route) #для тестов
                    if sum_closed_routes(bus_schedule) == sum_closed_routes(test_schedule):
                        driver = get_driver_week_schedule(schedule=bus_schedule, driver_id=len(drivers) + 1,
                                                          driver_type="B", bus_id=bus_id, start_route=route)
                    else:
                        driver = get_driver_week_schedule(schedule=bus_schedule, driver_id=len(drivers) + 1,
                                                          driver_type="A", bus_id=bus_id, start_route=route)

                    if list(driver.values()):
                        driver_start = list(driver.values())[0][0].start
                        driver_end = list(driver.values())[0][-1].end
                        buses[day][bus_id] = (driver_start, driver_end)
                        drivers.append(driver)
                        break
                else:
                    continue

    return bus_schedule

def display_schedule(bus_schedule):
    table = []
    for day, routes in bus_schedule.items():
        if day == "фантомный пон":
            continue
        table.append([f"=== {day.upper()} ===", "", "", ""])
        for route in routes:
            table.append([
                f"Водитель: {route.driver_id}",
                f"Начало: {route.start.strftime('%H:%M')}",
                f"Конец: {route.end.strftime('%H:%M')}",
                f"Автобус: {route.bus_id}"
            ])
        table.append(["", "", "", ""])  # Пустая строка для разделения дней

    print(tabulate(table, headers=["Водитель", "Начало", "Конец", "Автобус"], tablefmt="grid"))


# Генерация расписания и вывод в виде таблицы
bus_schedule = create_bus_schedule()
display_schedule(create_schedule())


