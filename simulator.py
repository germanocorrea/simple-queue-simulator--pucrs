#!/usr/bin/env python
import sys
from enum import Enum
from typing import TypeAlias, TypedDict, Tuple


class TipoEvento(Enum):
    CHEGADA = 0
    SAIDA = 1

class Event(TypedDict):
    event_type: TipoEvento
    random_generated: float
    time_to_ocurr: float

type TInterval = tuple[float, float]
type TQueueState = tuple[int, ...] # tamanho da dupla reforçado em runetime depois que inicializa a var

global_time: float = 0
previous_random: float = 42 # seed
max_randoms: int = 100000

queue_capacity: int = 0
queue_servers: int = 0
queue_state: TQueueState
queue_status: int = 0
queue_lost: int = 0

scheduler_queue: list[Event] = []

arrival_interval: TInterval = (0, 1)
exit_inteval: TInterval = (0, 1)

def print_state(label: str = ""):
    prefix = f"[{label}] " if label else ""
    qs = globals().get("queue_state", ())
    print(f"{prefix}global_time={global_time:.4f} | queue_status={queue_status} | queue_lost={queue_lost} | queue_state={list(qs)} | scheduler_queue={scheduler_queue}")

def print_scheduler_queue():
    print(f"  scheduler_queue (before pop) = {scheduler_queue}")

def print_new_event(event: Event):
    if event is None:
        print("  new_event = None")
        return
    print(f"  scheduled_event type={event['event_type']} random={event['random_generated']:.4f} time_to_ocurr={event['time_to_ocurr']:.4f}")


def main():
    initialize_queue_state()
    count = max_randoms
    while (count > 0):
        print_state("BEFORE")
        print_scheduler_queue()
        evento = scheduler_get_new_event();
        print_new_event(evento)
        if (evento["event_type"] == TipoEvento.CHEGADA):
            chegada(evento);
        elif (evento["event_type"] == TipoEvento.SAIDA):
            saida(evento);
        print_state("AFTER")
        print()
        count -= 1

    # print_distribution()

def initialize_queue_state():
    global queue_state
    queue_state = (0,) * queue_capacity
    scheduler_queue.append(new_event(TipoEvento.CHEGADA))

def fila_in():
    global queue_status
    queue_status += 1

def fila_out():
    global queue_status
    queue_status -= 1

def fila_loss():
    global queue_status, queue_lost
    queue_status -= 1
    queue_lost += 1

def new_event(event_type: TipoEvento) -> Event:
    random_generated = get_random_for_type(event_type)
    return {
        "event_type": event_type,
        "random_generated": random_generated,
        "time_to_ocurr": global_time + random_generated,
    }

def get_random_for_type(event_type: TipoEvento) -> float:
    random = random_number()
    interval = get_interval_from_type(event_type)
    return interval[0] + ((interval[1] - interval[0]) * random)

def get_interval_from_type(event_type: TipoEvento) -> TInterval:
    if event_type == TipoEvento.CHEGADA:
        return arrival_interval
    return exit_interval

def random_number() -> float:
    global previous_random
    M = pow(2, 27)
    a = 545643
    c = 76785897
    previous_random = ((a * previous_random) + c) % M
    return previous_random/M;

# def print_distribution(k, times):
#     for i in range(0,k+1):
#         print(str(i) + ": " + str(times[i]) + " (" + str(times[i]/global_time) + "\%)")

def scheduler_get_new_event() -> Event:
    scheduled: Event = None
    scheduled_i: int = -1
    for i in range(len(scheduler_queue)):
        event = scheduler_queue[i]
        if scheduled is None or event["time_to_ocurr"] < scheduled["time_to_ocurr"]:
            scheduled = event
            scheduled_i = i
    return scheduled

def scheduler_add(event_type: TipoEvento):
    scheduler_queue.append(new_event(event_type))

def accTime(event: Event):
    global global_time
    global_time += event["time_to_ocurr"]

def chegada(evento):
    accTime(evento)
    if queue_status < queue_capacity:
        fila_in()
        if queue_status <= queue_servers:
            scheduler_add(TipoEvento.SAIDA)
    else:
        fila_loss()
    scheduler_add(TipoEvento.CHEGADA)

def saida(evento):
    accTime(evento)
    fila_out()
    if queue_status >= queue_servers:
        scheduler_add(TipoEvento.SAIDA)

if __name__ == "__main__":
    try:
        arrival_interval = (float(sys.argv[1]), float(sys.argv[2]))
        exit_interval = (float(sys.argv[3]), float(sys.argv[4]))
        queue_servers = int(sys.argv[5])
        queue_capacity = int(sys.argv[6])
        if len(sys.argv) > 7:
            max_randoms = int(sys.argv[7])
    except IndexError:
        print("\n\nUsage: ./simulator.py [arrival_initial_value] [arrival_final_value] [exit_initial_value] [exit_final_value] [servers_number] [queue_capacity]")
        sys.exit(1)
    main()
