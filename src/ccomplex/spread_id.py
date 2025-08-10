#!/usr/bin/python3

import time
import csv
import os
import random
import numpy as np
# Compatibility workarounds for NumPy 2.0
np.float_ = np.float64
np.Inf = np.inf
import networkx as nx

# Datagather
def getLoads(filename, threshold):
    """
        Funcion para recolectar las cargas de los nodos
    """

    loads = dict()

    try:
        with open(filename, 'r') as file:
            reader = csv.reader(file)
            lines = 0
            for row in reader:
                if lines != 0:
                    loads[row[0]] = [round(float(load), threshold) for load in row[1:]]
                lines += 1

    except Exception as e:
        print(str(e))

    return loads

def getEdges(filename):
    """
        Funcion para recolectar los enlaces del grafo
    """

    edges = list()

    try:
        with open(filename, 'r') as file:
            reader = csv.reader(file)
            lines = 0
            for row in reader:
                if lines >= 3:
                    edges.append({"node_a": row[0], "node_b": row[1], "dist": int(row[2]), "conf": int(row[3])})
                lines += 1

    except Exception as e:
        print(str(e))

    return edges

def getEdges_Config(filename):
    """
        Funcion para recolectar las configuraciones de los enlaces
    """

    confs = dict()

    try:
        with open(filename, 'r') as file:
            reader = csv.reader(file)
            lines = 0
            for row in reader:
                if lines != 0:
                    confs[int(row[0])] = {"coef_r": float(row[1]), "i_max": float(row[2]), "section": row[3]}
                lines += 1

    except Exception as e:
        print(str(e))

    return confs

# Graph
class Link(object):
    """
    Clase para gestionar un enlace del grafo
    """

    # Declaramos tipos de enlace mediante variables estáticas de la clase
    NORMAL = 1
    SWITCH = 0

    # Vamos a definir constantes que son propias del enlace
    VOLTAGE = 415  # Volts
    SWITCH_R = 0.1*0.08  # Ohms

    def __init__(self, node_a, node_b, type_link, state, dist, conf, coef_r, i_max):
        """
        Constructor de la clase Link
        """
        self.node_a = node_a
        self.node_b = node_b
        self.direction = None
        self.type = type_link
        self.state = state
        self.dist = dist
        self.conf = conf

        # Según nos han indicado los enlaces de tipo switch no tienen dist, cap
        if self.type != Link.SWITCH:
            self.capacity = ((i_max * 3.0) * Link.VOLTAGE) / 1000  # kW
            self.coef_R = coef_r  # Ohms/km
        else:
            self.capacity = None
            self.coef_R = None

    @staticmethod
    def ft2meters(fts):
        """
        Funcion de conversion a feet (american unit)
        """
        return (fts) / 3.28084

    @staticmethod
    def meters2ft(meters):
        """
        Funcion de conversion a metros
        """
        return meters * 3.28084

    def getLosses(self, Pin):
        """
        Función para calcular las perdidas de un enlace de forma agnostica
        """
        Loss = 0.0  # kW

        if self.type == Link.SWITCH:
            Loss = Link.getLosses_Switch(Pin)
        else:
            Loss = self.getLosses_Link(Pin)

        return Loss

    @staticmethod
    def getLosses_Switch(P_in):
        """
        Función para calcular las perdidas de inserción por un switch activo dada una Potencia incidente (kW - Kilowatts)
        """
        return (((Link.SWITCH_R) / (Link.VOLTAGE) ** 2) * (P_in * 1000) ** 2) / 1000

    def getLosses_Link(self, P_in):
        """
        Función para calcular las perdidas de un enlace dada una potencia incidente (kW - kilowatts)
        """

        r_eff = self.coef_R * (
            Link.ft2meters(self.dist) / 1000
        )  # El coef_R esta en ohms/km -> la distancia nos venía en fts

        return (((r_eff) / (Link.VOLTAGE) ** 2) * (P_in * 1000) ** 2) / 1000

class Node(object):
    """
        Clase para gestionar un nodo del grafo
    """

    # Declaramos los tipos de nodos mediante variables estáticas de la clase
    NORMAL = 1
    VIRTUAL = 0

    def __init__(self, name, type_node, load=0):
        """
            Constructor de la clase Node
        """
        self.name = name
        self.type = type_node
        self.load = load
        self.neighbors = list()
        self.links = list()
        self.ids = list()
        self.ids_root_count = 0  # Lo usamos solamente para den2neMultiroot.

    def addNeighbor(self, neighbor, type_link, state, dist, conf, coef_r, i_max):
        """
            Funcion para añadir un vecino
        """
        self.neighbors.append(neighbor)
        self.links.append(Link(self.name, neighbor, type_link, state, dist, conf, coef_r, i_max))

    def getActiveID(self):
        """
            Función para obtener el ID activo
        """
        ret_ID = None

        for id in self.ids:
            if id.active is True:
                ret_ID = id
                break

        return ret_ID

    def getIndexID(self, id_to_check):
        """
            Funcion para obtener el indexs de una lista de saltos
        """

        # Aqui no vamos a trabajar con los Objs HLMACs, vamos atrabajar directamente con la lista de chars
        
        ret_index = None

        for id in self.ids:
            if id_to_check == id.hlmac:
                ret_index = self.ids.index(id)
                break
            
        return ret_index

class Graph(object):
    """
        Clase para gestionar el gráfo que representará la red de distribución eléctrica
    """

    def __init__(self, delta, loads, edges, switches, edges_conf, json_path=None, root='150'):
        """
            Constructor de la clase Graph el cual conformará el grafo a partir de los datos procesados.
        """
        self.nodes = dict()
        self.root = root
        self.sw_config = self.buildSwitchConfig(switches)
        self.json_path = json_path
        if self.json_path == None:
            self.buildGraph(delta, loads, edges, switches, edges_conf)
        else:
            self.load_json()

    def buildGraph(self, delta, loads, edges, switches, edges_conf):
        """
            Función para generar el grafo
        """

        # Primero vamos a añadir todos los nodos normales del grafo, ya que los tenemos listados con sus cargas en loads.
        for node in loads:
            self.nodes[node] = Node(node, Node.NORMAL, loads[node][delta])

        # Acto seguido vamos añadir todos los nodos virtuales
        for edge in edges:
            if edge["node_a"] not in self.nodes:
                self.nodes[edge["node_a"]] = Node(edge["node_a"], Node.VIRTUAL, 0)
            elif edge["node_b"] not in self.nodes:
                self.nodes[edge["node_b"]] = Node(edge["node_b"], Node.VIRTUAL, 0)

        for sw_edge in switches:
            if sw_edge["node_a"] not in self.nodes:
                self.nodes[sw_edge["node_a"]] = Node(sw_edge["node_a"], Node.VIRTUAL, 0)
            elif sw_edge["node_b"] not in self.nodes:
                self.nodes[sw_edge["node_b"]] = Node(sw_edge["node_b"], Node.VIRTUAL, 0)

        # A continuación, vamos a añadir a los nodos sus vecinos. Cada enlace es bi-direccional.
        for edge in edges:
            self.nodes[edge["node_a"]].addNeighbor(edge["node_b"], Link.NORMAL, 'closed', edge["dist"], edge["conf"], edges_conf[edge["conf"]]["coef_r"], edges_conf[edge["conf"]]["i_max"])
            self.nodes[edge["node_b"]].addNeighbor(edge["node_a"], Link.NORMAL, 'closed', edge["dist"], edge["conf"], edges_conf[edge["conf"]]["coef_r"], edges_conf[edge["conf"]]["i_max"])

        for sw_edge in switches:
            self.nodes[sw_edge["node_a"]].addNeighbor(sw_edge["node_b"], Link.SWITCH, sw_edge["state"], 0, 0, 0, 0)
            self.nodes[sw_edge["node_b"]].addNeighbor(sw_edge["node_a"], Link.SWITCH, sw_edge["state"], 0, 0, 0, 0)

    def buildSwitchConfig(self, switch):
        """
            Función para procesar la configuración inicial de los enlaces switch
        """

        # Nos creamos una variable auxiliar a devolver
        sw_config = dict()

        for sw_links in switch:
            sw_config[switch.index(sw_links)] = sw_links
            sw_config[switch.index(sw_links)]["pruned"] = False

        return sw_config

    def findSwitchID(self, name):
        """
            Función para buscar el index del enlace Switch dado el nombre de alguno de sus extremos
        """
        index = None

        for key in self.sw_config:
            if self.sw_config[key]['node_a'] == name or self.sw_config[key]['node_b'] == name:
                index = key
                break

        return index

    def getSwitchConfig(self, id):
        """
            Función para obtener el estado de un switch
        """
        return self.sw_config[id]['state']

    def setSwitchConfig(self, id, state, pruned=None):
        """
            Función para establecer el estado de un enlace de tipo switch 
        """

        # Primero vamos a modificarlo en el dict que tenemos en la clase del grafo
        self.sw_config[id]['state'] = state

        # Si se debe a una poda
        if pruned is not None:
            self.sw_config[id]['pruned'] = True

        # Acto seguido, debemos buscar los dos nodos que conforman el enlace y modificar sus Objs links para
        # que la info de estado siga siendo coherente.

        # Node A
        self.nodes[self.sw_config[id]['node_a']].links[self.nodes[self.sw_config[id]['node_a']].neighbors.index(self.sw_config[id]['node_b'])].state = state

        # Node B
        self.nodes[self.sw_config[id]['node_b']].links[self.nodes[self.sw_config[id]['node_b']].neighbors.index(self.sw_config[id]['node_a'])].state = state

        # Estos dos ultimos dos pasos si se va a eleiminar posteriormente uno de los nodos
        # va da igual, ya que el obj link se va a eliminar.. Pero de esta forma, hacemos que el metodo
        # sea robusto ante cualquier tipo de interacción

    def setLinkDirection(self, node_a, node_b, direction):
        """
            Funcion para establecer la dirección de un enlace, es decir, hacia donde irá el flujo de potencia
        """

        # Si la dirección es "up", la potencia va de node_b al node_a

        # Si por el contrario, la dirección es "down", la potencia va de node_a al node_b

        # Node A
        self.nodes[node_a].links[self.nodes[node_a].neighbors.index(node_b)].direction = direction

    def getLinkCapacity(self, node_a, node_b):
        """
            Función para obtener la capacidad del enlace conformado por node_a y node_b 
        """
        ret_cap = None

        # Vamos al nodo A, y miramos el enlace con el vecino node_b

        # Si el enlace es de tipo switch.. no hay capacidad
        if self.nodes[node_a].links[self.nodes[node_a].neighbors.index(node_b)].type == Link.NORMAL:
            ret_cap = self.nodes[node_a].links[self.nodes[node_a].neighbors.index(node_b)].capacity

        return ret_cap

    def removeNode(self, name):
        """
            Funcion para eliminar un nodo del grafo
        """

        # Primero vamos a los vecinos y eleminimos los enlaces con el
        for neighbor in self.nodes[name].neighbors:
            # Obtenemos el index a eliminar (Es necesario para los enlaces por ser objs, no vale hacer un remove)
            index_del = self.nodes[neighbor].neighbors.index(name)

            # Machacamos el nodo a eliminar como vecino, y con el index, eliminamos el enlace con el.
            self.nodes[neighbor].neighbors.remove(name)
            del self.nodes[neighbor].links[index_del]

        # Por último eliminamos el nodo de la lista del grafo
        self.nodes.pop(name)

    def pruneGraph(self):
        """
            Method to automagically prune the graph and set the default status of pruned Switch links

            Returns:
                list: A list of the IDs of the nodes that have been pruned.
        """

        nodes_to_prune = {
            'sweep_1': [],
            'sweep_2': []
        }

        # First sweep
        for node in self.nodes:
            if (
                self.nodes[node].type == Node.VIRTUAL and
                self.nodes[node].name != self.root and
                len(self.nodes[node].links) == 1 and
                self.nodes[node].links[0].type == Link.SWITCH
            ):
                nodes_to_prune['sweep_1'].append(self.nodes[node].name)

        # Lets open the switch links so that they dont consume anything
        for node in nodes_to_prune['sweep_1']:
            self.setSwitchConfig(self.findSwitchID(node), 'open', 'pruned')

        for node in nodes_to_prune['sweep_1']:
            self.removeNode(node)

        # Second sweep
        for node in self.nodes:
            if (
                self.nodes[node].type == Node.VIRTUAL and
                len(self.nodes[node].links) == 1 and
                self.nodes[node].links[0].type == Link.NORMAL
            ):
                nodes_to_prune['sweep_2'].append(self.nodes[node].name)

        for node in nodes_to_prune['sweep_2']:
            self.removeNode(node)

        return nodes_to_prune['sweep_1'] + nodes_to_prune['sweep_2']

# Den2dealg
class HLMAC(object):
    """
        Clase para gestionar las HLMACs asignadas
    """

    def __init__(self, hlmac_parent_addr, name, dependency):
        """
            Constructor de la clase HLMAC 
        """
        [self.hlmac, self.depends_on] = HLMAC.hlmac_assign_address(hlmac_parent_addr, name, dependency)
        self.used = False
        self.active = False

    def getOrigin(self):
        """
            Funcion para conseguir el origen de la HLMAC
        """
        return self.hlmac[-1]

    def getNextHop(self):
        """
            Funcion para conseguir el siguiente salto de la HLMAC
        """
        ret_val = None
        if len(self.hlmac) > 1:
            ret_val = self.hlmac[-2]
        return ret_val

    @staticmethod
    def hlmac_assign_address(hlmac_parent_addr, name, dependency):
        """
            Método para asignar una HLMAC a partir de una addr padre
        """
        new_addr = list()
        new_dependence = list()

        if hlmac_parent_addr is not None:
            # No podemos asignar sin más la lista ya que si no se coparten referencias, y serían mutables entre ellas.
            # Por ello, hay que llamar a copy()
            new_addr = hlmac_parent_addr.hlmac.copy()
            new_dependence = hlmac_parent_addr.depends_on.copy()

        # En caso de que haya una dependencia, la añadimos, si no, unicamente heredamos la de los padres
        if dependency is not None:
            new_dependence.append(dependency)

        new_addr.append(name)

        return [new_addr, new_dependence]

    @staticmethod
    def hlmac_cmp_address(hlmac_a, hlmac_b):
        """
            Funcion para comparar dos addr HLMAC
        """
        return hlmac_a.hlmac == hlmac_b.hlmac

    @staticmethod
    def hlmac_check_loop(hlmac_a, name):
        """
            Función para detectar bucles en una HLMAC a asignar 
        """
        return name in hlmac_a.hlmac

    @staticmethod
    def hlmac_addr_print(addr):
        """
            Funcion para imprimir una HLMAC
        """
        return '.'.join(map(str, addr.hlmac))

    @staticmethod
    def hlmac_deps_print(deps):
        """
            Funcion para imprimir las deps de una  HLMAC
        """
        ret_str = ''

        if len(deps.depends_on) == 0:
            ret_str = '-'
        else:
            ret_str = str(deps.depends_on)

        return ret_str

class Den2ne(object):
    """
    Clase para gestionar la lógica del algoritmo
    """

    # Declaramos tipos de criterio para la decisión entre IDs
    CRITERION_NUM_HOPS = 0
    CRITERION_DISTANCE = 1
    CRITERION_LINKS_LOSSES = 2
    CRITERION_POWER_TO_ZERO = 3
    CRITERION_POWER_TO_ZERO_WITH_LOSSES = 4
    CRITERION_LOW_LINKS_LOSSES = 5

    # Fijamos el número máximo de IDs por nodo
    IDS_MAX = 10

    def __init__(self, graph):
        """
        Constructor de la clase Den2ne
        """
        self.G = graph
        self.global_ids = list()
        self.root = graph.root

    def spread_ids(self):
        """
        Funcion para difundir los IDs entre todos los nodos del grafo
        """

        # Var aux: lista con los nodos que debemos visitar (Va a funcionar como una pila)
        nodes_to_attend = list()

        # Empezamos por el root, como no tiene padre el root, su HLMAC parent addr es None -> No hereda.
        # además, no tiene ninguna dependencia (es decir no tiene ninguno enlace por delante de el de tipo switch)
        self.G.nodes[self.root].ids.append(HLMAC(None, self.root, None))

        # El primero en ser visitado es el root
        nodes_to_attend.append(self.root)

        # Mientras haya nodos a visitar...
        while len(nodes_to_attend) > 0:

            curr_node = self.G.nodes[nodes_to_attend[0]]

            # Iteramos por las posibles IDs disponibles en el nodo
            for i in range(0, len(curr_node.ids)):

                if not curr_node.ids[i].used:

                    # Iteramos por los vecinos del primer nodo a atender
                    for neighbor in curr_node.neighbors:

                        # Vamos a comprobar antes de asignar IDs al vecino, que no hay bucles
                        if HLMAC.hlmac_check_loop(curr_node.ids[i], neighbor):
                            pass
                        elif len(self.G.nodes[neighbor].ids) >= Den2ne.IDS_MAX:
                            pass
                        else:
                            # Si no hay bucles asignamos la ID al vecino

                            # Vamos a comprobar si la relación del nodo con el vecino viene dada por un enlace de tipo switch
                            id_switch_node = self.G.findSwitchID(curr_node.name)
                            id_switch_neighbor = self.G.findSwitchID(neighbor)

                            if id_switch_node == id_switch_neighbor:
                                self.G.nodes[neighbor].ids.append(
                                    HLMAC(curr_node.ids[i], neighbor, id_switch_node)
                                )
                            else:
                                self.G.nodes[neighbor].ids.append(
                                    HLMAC(curr_node.ids[i], neighbor, None)
                                )

                            # Registramos el vecino emn la pila para ser visitado más adelante
                            nodes_to_attend.append(neighbor)

                    # Y tenemos que marcar la HLMAC como que ya ha sido usada
                    self.G.nodes[nodes_to_attend[0]].ids[i].used = True

            # Por último desalojamos al nodo atendido
            nodes_to_attend.pop(0)


# Helper to orient undirected tree from root
def orient_tree(edges, root, all_nodes):
    """Given undirected edge list and root, return list of directed edges away from root"""
    T = nx.DiGraph()
    T.add_nodes_from(all_nodes)
    for u, v in edges:
        T.add_edge(u, v)
        T.add_edge(v, u)
    directed = []
    visited = {root}
    queue = [root]
    while queue:
        n = queue.pop(0)
        for nbr in T.successors(n):
            if nbr not in visited:
                directed.append((n, nbr))
                visited.add(nbr)
                queue.append(nbr)
    return directed

# Alternative Tree Builders

def build_mst_tree(edges, root, all_nodes):
    G = nx.Graph()
    for e in edges:
        G.add_edge(e['node_a'], e['node_b'], weight=e['dist'])
    T = nx.minimum_spanning_tree(G, weight='weight')
    return orient_tree(list(T.edges()), root, all_nodes)


def random_spanning_tree(G):
    H = nx.Graph()
    for u, v in G.edges():
        H.add_edge(u, v, weight=random.random())
    T = nx.minimum_spanning_tree(H, weight='weight')
    return list(T.edges())


def build_pso_tree(edges, root, all_nodes, iterations=15, pop_size=5):
    G = nx.Graph()
    for e in edges:
        G.add_edge(e['node_a'], e['node_b'], dist=e['dist'])
    particles = []
    for _ in range(pop_size):
        tree = random_spanning_tree(G)
        fit = sum(G[u][v]['dist'] for u, v in tree)
        particles.append({'tree': tree, 'pbest': tree, 'pbest_fit': fit})
    gbest = min(particles, key=lambda p: p['pbest_fit'])
    for _ in range(iterations):
        for p in particles:
            common = set(p['tree']).intersection(gbest['pbest'])
            new = list(common)
            while len(new) < len(G.nodes) - 1:
                u, v = random.choice(list(G.edges()))
                if (u, v) not in new and (v, u) not in new:
                    new.append((u, v))
            fit = sum(G[u][v]['dist'] for u, v in new)
            if fit < p['pbest_fit']:
                p['pbest'], p['pbest_fit'] = new, fit
                if fit < gbest['pbest_fit']:
                    gbest = p
            p['tree'] = new
    return orient_tree(gbest['pbest'], root, all_nodes)


def build_ga_tree(edges, root, all_nodes, generations=15, pop_size=5):
    G = nx.Graph()
    for e in edges:
        G.add_edge(e['node_a'], e['node_b'], dist=e['dist'])
    pop = [random_spanning_tree(G) for _ in range(pop_size)]
    for _ in range(generations):
        scored = sorted(pop, key=lambda t: sum(G[u][v]['dist'] for u, v in t))
        survivors = scored[:pop_size//2]
        children = []
        while len(children) < pop_size//2:
            a, b = random.sample(survivors, 2)
            union = set(a).union(b)
            H = nx.Graph(); H.add_nodes_from(G.nodes)
            for u, v in union:
                H.add_edge(u, v, weight=random.random())
            T = nx.minimum_spanning_tree(H, weight='weight')
            children.append(list(T.edges()))
        pop = survivors + children
    best = min(pop, key=lambda t: sum(G[u][v]['dist'] for u, v in t))
    return orient_tree(best, root, all_nodes)


def test_all_topos():
    base = "topo"
    conf_path = "links_config_8.csv"
    out_dir = "results"
    os.makedirs(out_dir, exist_ok=True)
    for fld in sorted(os.listdir(base)):
        if not fld.startswith("topo_"): continue
        n = int(fld.split("_")[1])
        p = os.path.join(base, fld)
        edges = getEdges(os.path.join(p, "links.csv"))
        loads = getLoads(os.path.join(p, "loads.csv"),3)
        confs = getEdges_Config(conf_path)
        all_nodes = list(loads.keys())
        csvf = os.path.join(out_dir, f"topo_{n}.csv")
        with open(csvf,'w',newline='') as f:
            w = csv.writer(f);
            w.writerow(["Run","Root","SpreadIDs(s)","MST(s)","PSO(s)","GA(s)"])
            for run in range(1,11):
                root = random.choice(all_nodes)
                # Spread IDs
                Gg = Graph(0, loads, edges, [], confs, root=root)
                alg = Den2ne(Gg)
                t0=time.time(); alg.spread_ids(); sp=round(time.time()-t0,6)
                # MST
                t0=time.time(); build_mst_tree(edges, root, all_nodes); m=round(time.time()-t0,6)
                # PSO
                t0=time.time(); build_pso_tree(edges, root, all_nodes); p=round(time.time()-t0,6)
                # GA
                t0=time.time(); build_ga_tree(edges, root, all_nodes); g=round(time.time()-t0,6)
                print(f"Topo {n} run{run} Spread:{sp}s MST:{m}s PSO:{p}s GA:{g}s")
                w.writerow([run,root,sp,m,p,g])

if __name__=="__main__": test_all_topos()