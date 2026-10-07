#!/usr/bin/env python
import sys
from enum import Enum
from typing import Any, TypedDict, cast
from dataclasses import dataclass, field
debug: bool = False


class EventType(Enum):
    ARRIVAL = 0
    EXIT = 1
    PASSAGEM = 2

type TInterval = tuple[float, float]
type TQueueState = tuple[int, ...] # tamanho reforçado em runtime depois que inicializa a var

EXTERIOR: str = "exit" # nome reservado no yml para o exterior da rede
EPSILON: float = 1e-9

global_time: float = 0
previous_random: float = 42 # seed
max_randoms: int = 100000
randoms_used: int = 0

@dataclass
class Route:
    destination: "Queue | None" # None = exterior
    probability: float

@dataclass
class Queue:
    name: str = ""
    queue_capacity: int | None = None # None = capacidade infinita
    queue_servers: int = 0
    queue_state: TQueueState = ()
    queue_status: int = 0
    queue_lost: int = 0
    state_time: list[float] = field(default_factory=list)
    arrival_interval: TInterval | None = None # só filas que recebem chegadas externas
    first_arrival: float | None = None
    service_interval: TInterval = (0, 1)
    routes: list[Route] = field(default_factory=list)

class Event(TypedDict):
    event_type: EventType
    random_generated: float
    time_to_ocurr: float
    origin: Queue | None      # filaOrigem  (EXIT e PASSAGEM)
    destination: Queue | None # filaDestino (ARRIVAL e PASSAGEM)

# formato do arquivo yml
class SimulationConfig(TypedDict, total=False):
    max_randoms: int
    seed: float

class QueueConfig(TypedDict, total=False):
    servers: int
    capacity: int | None
    arrival: list[float]
    first_arrival: float
    service: list[float]
    routing: dict[str, float]

class ModelConfig(TypedDict, total=False):
    simulation: SimulationConfig
    queues: dict[str, QueueConfig]

class RandomsExhausted(Exception):
    pass

queues: list[Queue] = []

scheduler_queue: list[Event] = []

def queue_label(q: Queue | None) -> str:
    return q.name if q is not None else EXTERIOR

def print_state(label: str = ""):
    if not debug:
        return
    prefix = f"[{label}] " if label else ""
    print(f"{prefix}global_time={global_time:.4f} | randoms_used={randoms_used}")
    for q in queues:
        print(f"{prefix}{q.name}: status={q.queue_status} | lost={q.queue_lost} | state={list(q.queue_state)}")

def print_scheduler_queue(indent: str = ""):
    if not debug:
        return
    print(f"{indent}scheduler_queue ({len(scheduler_queue)} items):")
    for i, event in enumerate(scheduler_queue):
        print(f"{indent}  [{i}] {format_event(event)}")
    if not scheduler_queue:
        print(f"{indent}  (empty)")

def print_new_event(event: Event):
    if not debug:
        return
    if event is None:
        print("  new_event = None")
        return
    print(f"  scheduled_event {format_event(event)}")

def format_event(event: Event) -> str:
    route = ""
    if event["event_type"] == EventType.ARRIVAL:
        route = f"-> {queue_label(event['destination'])}"
    elif event["event_type"] == EventType.EXIT:
        route = f"{queue_label(event['origin'])} -> {EXTERIOR}"
    elif event["event_type"] == EventType.PASSAGEM:
        route = f"{queue_label(event['origin'])} -> {queue_label(event['destination'])}"
    return f"type={event['event_type']} ({route}) random={event['random_generated']:.4f} time_to_ocurr={event['time_to_ocurr']:.4f}"

def format_capacity(q: Queue) -> str:
    return "infinite" if q.queue_capacity is None else str(q.queue_capacity)

def print_final_report():
    print("\n======== INPUT INFORMATION ========")
    print(f"Max randoms: {max_randoms}")
    print(f"Randoms used: {randoms_used}")
    print(f"Global simulation time: {global_time:.4f}")
    for q in queues:
        total_time = sum(q.state_time)
        print(f"\n========== {q.name} (G/G/{q.queue_servers}/{format_capacity(q)}) ==========")
        if q.arrival_interval is not None and q.first_arrival is not None:
            print(f"Arrival interval: [{q.arrival_interval[0]:.4f}, {q.arrival_interval[1]:.4f}] (first arrival at {q.first_arrival:.4f})")
        print(f"Service interval: [{q.service_interval[0]:.4f}, {q.service_interval[1]:.4f}]")
        routing = ", ".join(f"{queue_label(r.destination)}: {r.probability:.2f}" for r in q.routes) or f"{EXTERIOR}: 1.00"
        print(f"Routing: {routing}")
        print(f"Servers: {q.queue_servers}")
        print(f"Queue capacity: {format_capacity(q)}")
        print(f"Total clients lost: {q.queue_lost}")
        print(f"  {'State':<6} {'Accum. time':<18} {'Probability':<12} {'%':<10}")
        for i, t in enumerate(q.state_time):
            prob = (t / total_time) if total_time > 0 else 0
            label = f"{i}*" if i == q.queue_capacity else str(i)
            print(f"  {label:<6} {t:<18.4f} {prob:<12.6f} {prob*100:<10.2f}")
    print(f"\nTotal clients lost (all queues): {sum(q.queue_lost for q in queues)}")
    print("=" * 32)

def main():
    initialize_queue_state()
    try:
        while randoms_used < max_randoms:
            print_state("BEFORE")
            print_scheduler_queue()
            event = scheduler_get_new_event();
            print_new_event(event)
            if (event["event_type"] == EventType.ARRIVAL):
                ARRIVAL(event);
            elif (event["event_type"] == EventType.EXIT):
                EXIT(event);
            elif (event["event_type"] == EventType.PASSAGEM):
                PASSAGEM(event);
            print_state("AFTER")
            if debug:
                print()
    except RandomsExhausted:
        # o evento que precisava do aleatório 'max_randoms + 1' já teve seu tempo contabilizado
        if debug:
            print("Randoms exhausted, stopping simulation.\n")

    print_final_report()

def initialize_queue_state():
    for q in queues:
        if q.queue_capacity is None:
            q.queue_state = ()
            q.state_time = [0.0] # cresce sob demanda em accTime
        else:
            q.queue_state = (0,) * q.queue_capacity
            q.state_time = [0.0] * (q.queue_capacity + 1)
        if q.arrival_interval is not None and q.first_arrival is not None:
            scheduler_queue.append({
                "event_type": EventType.ARRIVAL,
                "random_generated": 0,
                "time_to_ocurr": q.first_arrival,
                "origin": None,
                "destination": q,
            })

def queue_in(q: Queue):
    q.queue_status += 1

def queue_out(q: Queue):
    q.queue_status -= 1

def queue_loss(q: Queue):
    q.queue_lost += 1

def has_space(q: Queue) -> bool:
    return q.queue_capacity is None or q.queue_status < q.queue_capacity

def new_event(event_type: EventType, origin: Queue | None = None, destination: Queue | None = None) -> Event:
    random_generated = get_random_for_event(event_type, origin, destination)
    return {
        "event_type": event_type,
        "random_generated": random_generated,
        "time_to_ocurr": global_time + random_generated,
        "origin": origin,
        "destination": destination,
    }

def get_random_for_event(event_type: EventType, origin: Queue | None, destination: Queue | None) -> float:
    interval = get_interval_from_event(event_type, origin, destination)
    random = random_number()
    return interval[0] + ((interval[1] - interval[0]) * random)

def get_interval_from_event(event_type: EventType, origin: Queue | None, destination: Queue | None) -> TInterval:
    # chegada usa o intervalo de chegada da fila destino; EXIT e PASSAGEM usam o atendimento da fila origem
    if event_type == EventType.ARRIVAL:
        assert destination is not None and destination.arrival_interval is not None
        return destination.arrival_interval
    assert origin is not None
    return origin.service_interval

def random_number() -> float:
    global previous_random, randoms_used
    if randoms_used >= max_randoms:
        raise RandomsExhausted()
    randoms_used += 1
    M = pow(2, 27)
    a = 545643
    c = 76785897
    previous_random = ((a * previous_random) + c) % M
    return previous_random/M;

def scheduler_get_new_event() -> Event:
    scheduled: Event | None = None
    scheduled_i: int = -1
    for i in range(len(scheduler_queue)):
        event = scheduler_queue[i]
        if scheduled is None or event["time_to_ocurr"] < scheduled["time_to_ocurr"]:
            scheduled = event
            scheduled_i = i
    if scheduled is None:
        raise RuntimeError("scheduler is empty: no queue receives external arrivals")
    scheduler_queue.pop(scheduled_i)
    return scheduled

def scheduler_add(event_type: EventType, origin: Queue | None = None, destination: Queue | None = None):
    scheduler_queue.append(new_event(event_type, origin, destination))

def route(origin: Queue) -> Queue | None:
    """Sorteia o destino de um cliente atendido em 'origin'. None = exterior."""
    # roteamento determinístico (ex.: tandem ou saída direta) não consome aleatório
    if not origin.routes:
        return None
    if len(origin.routes) == 1 and origin.routes[0].probability >= 1 - EPSILON:
        return origin.routes[0].destination

    random = random_number()
    accumulated: float = 0
    for r in origin.routes:
        accumulated += r.probability
        if random < accumulated:
            return r.destination
    return None # o que sobra até 1.0 vai para o exterior

def schedule_service(origin: Queue):
    """Agenda o fim do atendimento de um cliente em 'origin': EXIT ou PASSAGEM, conforme o roteamento."""
    destination = route(origin)
    if destination is None:
        scheduler_add(EventType.EXIT, origin=origin)
    else:
        scheduler_add(EventType.PASSAGEM, origin=origin, destination=destination)

def accTime(event: Event):
    global global_time
    dt = max(event["time_to_ocurr"] - global_time, 0)
    for q in queues:
        if q.queue_capacity is None:
            while len(q.state_time) <= q.queue_status:
                q.state_time.append(0.0)
            state_index = q.queue_status
        else:
            state_index = min(q.queue_status, q.queue_capacity)
        q.state_time[state_index] += dt
    global_time = event["time_to_ocurr"]

def ARRIVAL(event: Event): # chegada externa na fila destino
    accTime(event)
    q = event["destination"]
    assert q is not None
    if has_space(q):
        queue_in(q)
        if q.queue_status <= q.queue_servers:
            schedule_service(q)
    else:
        queue_loss(q)
    scheduler_add(EventType.ARRIVAL, destination=q)

def EXIT(event: Event): # cliente sai da fila origem para o exterior
    accTime(event)
    q = event["origin"]
    assert q is not None
    queue_out(q)
    if q.queue_status >= q.queue_servers:
        schedule_service(q)

def PASSAGEM(event: Event): # cliente passa da fila origem para a fila destino (pode ser a mesma: feedback)
    accTime(event)
    origin = event["origin"]
    destination = event["destination"]
    assert origin is not None and destination is not None

    queue_out(origin)
    if origin.queue_status >= origin.queue_servers:
        schedule_service(origin)

    if has_space(destination):
        queue_in(destination)
        if destination.queue_status <= destination.queue_servers:
            schedule_service(destination)
    else:
        queue_loss(destination)

def parse_interval(value: Any, what: str) -> TInterval:
    if not isinstance(value, list) or len(cast(list[Any], value)) != 2:
        raise ValueError(f"{what} must be a list [min, max]")
    interval: TInterval = (float(value[0]), float(value[1]))
    if interval[0] > interval[1]:
        raise ValueError(f"{what}: min > max")
    return interval

def load_model(path: str):
    global max_randoms, previous_random
    with open(path, encoding="utf-8") as f:
        model = cast(ModelConfig, parse_yml(f.read()))

    simulation: SimulationConfig = model.get("simulation") or {}
    max_randoms = int(simulation.get("max_randoms", max_randoms))
    previous_random = float(simulation.get("seed", previous_random))

    queues_config: dict[str, QueueConfig] = model.get("queues") or {}
    if not queues_config:
        raise ValueError("model has no queues")

    # 1a passada: cria as filas
    by_name: dict[str, Queue] = {}
    for name, cfg in queues_config.items():
        name = str(name)
        if name == EXTERIOR:
            raise ValueError(f"'{EXTERIOR}' is reserved and cannot be a queue name")
        capacity = cfg.get("capacity")
        q = Queue(
            name=name,
            queue_servers=int(cfg["servers"]),
            queue_capacity=None if capacity is None else int(capacity),
            service_interval=parse_interval(cfg.get("service"), f"{name}.service"),
        )
        if q.queue_servers < 1:
            raise ValueError(f"{name}.servers must be >= 1")
        if "arrival" in cfg:
            q.arrival_interval = parse_interval(cfg["arrival"], f"{name}.arrival")
            q.first_arrival = float(cfg.get("first_arrival", 1.0))
        by_name[name] = q
        queues.append(q)

    # 2a passada: liga as filas (filaOrigem -> filaDestino), na ordem em que aparecem no yml
    for name, cfg in queues_config.items():
        origin = by_name[str(name)]
        total: float = 0
        for target, probability in (cfg.get("routing") or {}).items():
            target = str(target)
            if target != EXTERIOR and target not in by_name:
                raise ValueError(f"{name}.routing: unknown queue '{target}'")
            probability = float(probability)
            if probability < 0:
                raise ValueError(f"{name}.routing.{target}: negative probability")
            total += probability
            origin.routes.append(Route(destination=by_name.get(target), probability=probability))
        if total > 1 + EPSILON:
            raise ValueError(f"{name}.routing: probabilities sum to {total:.4f} (> 1)")
        if total < 1 - EPSILON:
            # o restante vai implicitamente para o exterior
            origin.routes.append(Route(destination=None, probability=1 - total))
        # rota única para o exterior é o mesmo que não ter rotas
        if len(origin.routes) == 1 and origin.routes[0].destination is None:
            origin.routes = []

    if not any(q.arrival_interval is not None for q in queues):
        raise ValueError("at least one queue must have 'arrival' (external arrivals)")

# parser mínimo do subconjunto de yml usado nos modelos: mapas aninhados por indentação,
# listas [a, b], números, textos e comentários '#'
def parse_yml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)] # (indentação da chave, mapa)
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        while indent <= stack[-1][0]:
            stack.pop()
        key, sep, value = line.strip().partition(":")
        if not sep:
            raise ValueError(f"invalid yml line: {raw!r}")
        if value.strip():
            stack[-1][1][key] = parse_yml_value(value.strip())
        else:
            stack[-1][1][key] = {}
            stack.append((indent, stack[-1][1][key]))
    return root

def parse_yml_value(value: str) -> Any:
    if value.startswith("[") and value.endswith("]"):
        return [parse_yml_value(v.strip()) for v in value[1:-1].split(",") if v.strip()]
    for kind in (int, float):
        try:
            return kind(value)
        except ValueError:
            pass
    return value.strip("\"'")

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--debug" in args:
        debug = True
        args.remove("--debug")
    try:
        load_model(args[0])
        if len(args) > 1:
            max_randoms = int(args[1])
    except IndexError:
        print("\n\nUsage: ./simulator.py <model.yml> [max_randoms] [--debug]")
        sys.exit(1)
    except (OSError, KeyError, TypeError, ValueError) as e:
        print(f"\n\nInvalid model: {e!r}")
        sys.exit(1)
    main()
