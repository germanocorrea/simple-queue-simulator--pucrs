#!/usr/bin/env python
import sys
from enum import Enum
from typing import TypeAlias, TypedDict, Tuple

debug: bool = False


class EventType(Enum):
    ARRIVAL = 0
    EXIT = 1

class Event(TypedDict):
    event_type: EventType
    random_generated: float
    time_to_ocurr: float

type TInterval = tuple[float, float]
type TQueueState = tuple[int, ...] # tamanho da dupla reforçado em runetime depois que inicializa a var

global_time: float = 0
previous_random: float = 42 # seed
max_randoms: int = 100000

state_time: list[float] = []

queue_capacity: int = 0
queue_servers: int = 0
queue_state: TQueueState
queue_status: int = 0
queue_lost: int = 0

scheduler_queue: list[Event] = []

arrival_interval: TInterval = (0, 1)
exit_inteval: TInterval = (0, 1)
initial_time: float = 1

def print_state(label: str = ""):
    if not debug:
        return
    prefix = f"[{label}] " if label else ""
    qs = globals().get("queue_state", ())
    print(f"{prefix}global_time={global_time:.4f} | queue_status={queue_status} | queue_lost={queue_lost} | queue_state={list(qs)}")
    print_scheduler_queue(prefix)

def print_scheduler_queue(indent: str = ""):
    if not debug:
        return
    print(f"{indent}scheduler_queue ({len(scheduler_queue)} items):")
    for i, event in enumerate(scheduler_queue):
        print(f"{indent}  [{i}] type={event['event_type']} random={event['random_generated']:.4f} time_to_ocurr={event['time_to_ocurr']:.4f}")
    if not scheduler_queue:
        print(f"{indent}  (empty)")

def print_new_event(event: Event):
    if not debug:
        return
    if event is None:
        print("  new_event = None")
        return
    print(f"  scheduled_event type={event['event_type']} random={event['random_generated']:.4f} time_to_ocurr={event['time_to_ocurr']:.4f}")

def print_final_report():
    total_time = sum(state_time)
    print("\n======== INPUT INFORMATION ========")
    print(f"Arrival interval: [{arrival_interval[0]:.4f}, {arrival_interval[1]:.4f}]")
    print(f"Exit interval: [{exit_interval[0]:.4f}, {exit_interval[1]:.4f}]")
    print(f"Servers: {queue_servers}")
    print(f"Queue capacity: {queue_capacity}")
    print(f"Max randoms: {max_randoms}")
    print(f"Initial time: {initial_time:.4f}")
    print("\n========== FINAL REPORT ==========")
    print(f"Global simulation time: {global_time:.4f}")
    print(f"Total clients lost: {queue_lost}")
    print("\nQueue state distribution:")
    print(f"  {'State':<6} {'Accum. time':<18} {'Probability':<12} {'%':<10}")
    for i, t in enumerate(state_time):
        prob = (t / total_time) if total_time > 0 else 0
        label = f"{i}*" if i == queue_capacity else str(i)
        print(f"  {label:<6} {t:<18.4f} {prob:<12.6f} {prob*100:<10.2f}")
    print("=" * 32)


def main():
    initialize_queue_state()
    count = max_randoms
    while (count > 0):
        print_state("BEFORE")
        print_scheduler_queue()
        event = scheduler_get_new_event();
        print_new_event(event)
        if (event["event_type"] == EventType.ARRIVAL):
            ARRIVAL(event);
        elif (event["event_type"] == EventType.EXIT):
            EXIT(event);
        print_state("AFTER")
        if debug:
            print()
        count -= 1

    print_final_report()

def initialize_queue_state():
    global queue_state, state_time
    queue_state = (0,) * queue_capacity
    state_time = [0.0] * (queue_capacity + 1)
    scheduler_queue.append({
        "event_type": EventType.ARRIVAL,
        "random_generated": 0,
        "time_to_ocurr": initial_time,
    })

def queue_in():
    global queue_status
    queue_status += 1

def queue_out():
    global queue_status
    queue_status -= 1

def queue_loss():
    global queue_lost
    queue_lost += 1

def new_event(event_type: EventType) -> Event:
    random_generated = get_random_for_type(event_type)
    return {
        "event_type": event_type,
        "random_generated": random_generated,
        "time_to_ocurr": global_time + random_generated,
    }

def get_random_for_type(event_type: EventType) -> float:
    random = random_number()
    interval = get_interval_from_type(event_type)
    return interval[0] + ((interval[1] - interval[0]) * random)

def get_interval_from_type(event_type: EventType) -> TInterval:
    if event_type == EventType.ARRIVAL:
        return arrival_interval
    return exit_interval

def random_number() -> float:
    global previous_random
    M = pow(2, 27)
    a = 545643
    c = 76785897
    previous_random = ((a * previous_random) + c) % M
    return previous_random/M;

def scheduler_get_new_event() -> Event:
    scheduled: Event = None
    scheduled_i: int = -1
    for i in range(len(scheduler_queue)):
        event = scheduler_queue[i]
        if scheduled is None or event["time_to_ocurr"] < scheduled["time_to_ocurr"]:
            scheduled = event
            scheduled_i = i
    if scheduled is not None:
        scheduler_queue.pop(scheduled_i)
    else:
        scheduled = new_event(EventType.ARRIVAL)
    return scheduled

def scheduler_add(event_type: EventType):
    scheduler_queue.append(new_event(event_type))

def accTime(event: Event):
    global global_time
    dt = event["time_to_ocurr"] - global_time
    state_index = min(queue_status, queue_capacity)
    state_time[state_index] += max(dt, 0)
    global_time = event["time_to_ocurr"]

def ARRIVAL(event):
    accTime(event)
    if queue_status < queue_capacity:
        queue_in()
        if queue_status <= queue_servers:
            scheduler_add(EventType.EXIT)
    else:
        queue_loss()
    scheduler_add(EventType.ARRIVAL)

def EXIT(event):
    accTime(event)
    queue_out()
    if queue_status >= queue_servers:
        scheduler_add(EventType.EXIT)

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--debug" in args:
        debug = True
        args.remove("--debug")
    try:
        arrival_interval = (float(args[0]), float(args[1]))
        exit_interval = (float(args[2]), float(args[3]))
        queue_servers = int(args[4])
        queue_capacity = int(args[5])
        if len(args) > 6:
            max_randoms = int(args[6])
        if len(args) > 7:
            initial_time = float(args[7])
    except (IndexError, ValueError):
        print("\n\nUsage: ./simulator.py [arrival_initial_value] [arrival_final_value] [exit_initial_value] [exit_final_value] [servers_number] [queue_capacity] [max_randoms] [initial_time] [--debug]")
        sys.exit(1)
    main()
