#!/usr/bin/python3

import time
import csv
import os
import random
import copy
import numpy as np
# Compatibility workarounds for NumPy 2.0
np.float_ = np.float64
np.Inf = np.inf
import concurrent.futures
from functools import partial
from tqdm import tqdm


SEED = 42

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
                if lines >= 1:
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
    
    def selectBestIDs(self, criterion):
        """
        Función para decidir la mejor ID de en nodo dado un criterio
        """

        # Vamos a elegir la mejor ID para cada nodo
        if Den2ne.CRITERION_NUM_HOPS == criterion:
            self.selectBestID_by_hops()

        elif Den2ne.CRITERION_POWER_TO_ZERO == criterion:
            self.selectBestID_by_power2zero()

        elif Den2ne.CRITERION_POWER_TO_ZERO_WITH_LOSSES == criterion:
            self.selectBestID_by_power2zero_with_Losses()

        elif Den2ne.CRITERION_LOW_LINKS_LOSSES == criterion:
            self.selectBestID_by_lowLinks_Losses()

        # Por último, vamos a ver el las dependencias con los switchs y activar aquellos que sean necesarios
        dependences = list(
            set(sum([active_ids.depends_on for active_ids in self.global_ids], []))
        )

        for sw in self.G.sw_config:
            if not self.G.sw_config[sw]["pruned"]:
                self.G.setSwitchConfig(sw, "open")

        for deps in dependences:
            self.G.setSwitchConfig(deps, "closed")

    def selectBestID_by_hops(self):
        """
        Función para decidir la mejor ID de un nodo por numero de saltos al root
        """
        for node in self.G.nodes:
            lens = [len(id.hlmac) for id in self.G.nodes[node].ids]

            # La ID con un menor tamaño será la ID con menor numero de saltos al root
            # Por ello, esa será la activa.
            self.G.nodes[node].ids[lens.index(min(lens))].active = True
            self.global_ids.append(self.G.nodes[node].getActiveID())

    def selectBestID_by_lowLinks_Losses(self, alpha=0.5, beta=0.5):
        """
        Función para decidir la mejor ID de un nodo en función de sus perdidas al root
        """
        for node in self.G.nodes:
            ids = self.G.nodes[node].ids
            scores = [ alpha * self.getTotalLinks_Losses(id) + beta * len(id.hlmac) for id in ids]

            # Seleccionar el ID con el menor score
            best_index = scores.index(min(scores))
            ids[best_index].active = True
            self.global_ids.append(self.G.nodes[node].getActiveID())

    def getTotalLinks_Losses(self, id):
        """
        Funcion para calcular las perdidas desde un nodo dado al root
        """

        init_node = self.G.nodes[id.hlmac[len(id.hlmac) - 1]]
        curr_load = init_node.load
        losses = 0
        total_losses = 0

        for i in range(len(id.hlmac) - 1, 0, -1):
            curr_node = self.G.nodes[id.hlmac[i]]

            total_losses += curr_node.links[
                curr_node.neighbors.index(id.hlmac[i - 1])
            ].getLosses(curr_load)
            losses = curr_node.links[
                curr_node.neighbors.index(id.hlmac[i - 1])
            ].getLosses(curr_load)

            curr_load -= losses

        return total_losses

    def selectBestID_by_power2zero(self, alpha=0.5, beta=0.5):
        """
        Función para decidir la mejor ID de un nodo cercanía de potecia a cero, al root
        """
        for node in self.G.nodes:
            ids = self.G.nodes[node].ids
            scores = [  alpha * self.getTotalPower2Zero(id) + beta * len(id.hlmac)  for id in ids ]

            # Seleccionar el ID con el menor score
            best_index = scores.index(min(scores))
            ids[best_index].active = True
            self.global_ids.append(self.G.nodes[node].getActiveID())

    def getTotalPower2Zero(self, id):
        """
        Función para calcular la distancia a zero de la suma de la potencia origen y la destino
        """
        # En caso de que seamos el root
        if len(id.hlmac) == 1:
            return self.G.nodes[id.getOrigin()].load
        else:
            origin_load = self.G.nodes[id.getOrigin()].load
            dst_load = self.G.nodes[id.getNextHop()].load
            return abs(dst_load + origin_load)

    def selectBestID_by_power2zero_with_Losses(self):
        """
        Función para decidir la mejor ID de un nodo cercanía de potecia a cero, al root teniendo en cuenta las perdidas
        """
        for node in self.G.nodes:
            power2zero = [
                self.getTotalPower2Zero_with_Losses(id) for id in self.G.nodes[node].ids
            ]

            self.G.nodes[node].ids[power2zero.index(min(power2zero))].active = True
            self.global_ids.append(self.G.nodes[node].getActiveID())


    def getTotalPower2Zero_with_Losses(self, id):
        """
        Función para calcular la distancia a zero de la suma de la potencia origen y la destino teniendo en cuenta las perdidas
        """

        val = 0

        # En caso de que seamos el root
        if len(id.hlmac) == 1:
            val = self.G.nodes[id.getOrigin()].load
        else:
            # Origen
            origin_load = self.G.nodes[id.getOrigin()].load

            # Destino
            dst_load = self.G.nodes[id.getNextHop()].load

            val = abs(
                dst_load
                + origin_load
                - self.G.nodes[id.getOrigin()]
                .links[
                    self.G.nodes[id.getOrigin()].neighbors.index(
                        self.G.nodes[id.getNextHop()].name
                    )
                ]
                .getLosses(origin_load)
            )

        return val


    def globalBalance(self, withLosses, withCap, withDebugPlot, positions, path):
        """
        Funcion que obtniene el balance global de la red y la dirección de cada enlace (hacia donde va el flujo de potencia)
        """

        # Primero hay que ordenar la lista de global_ids de mayor a menor
        self.global_ids.sort(key=Den2ne.key_sort_by_HLMAC_len, reverse=True)

        # Vamos a estudiar tambien el abs() del movimiento de flujo de Potencia
        abs_flux = 0.0


        # Vamos a llevar la cuenta de las iteraciones
        iteration = 0

        # Vamos a usar una var aux para devolver la potencia
        ret_load = float()

        # Mientras haya IDs != del root -> Vamos a trabajar con listado global como si fuera una pila
        while len(self.global_ids) > 1:

            # Origen
            origin_index = self.global_ids[0].getOrigin()
            origin = self.G.nodes[origin_index]

            # Destino
            dst_index = self.global_ids[0].getNextHop()
            dst = self.G.nodes[dst_index]

            # Establecemos la dirección del flujo de potencia en el enlace
            if origin.load < 0:
                self.G.setLinkDirection(origin.name, dst.name, "down")
                self.G.setLinkDirection(dst.name, origin.name, "up")
            else:
                self.G.setLinkDirection(origin.name, dst.name, "up")
                self.G.setLinkDirection(dst.name, origin.name, "down")


            # Caso ideal
            self.G.nodes[dst_index].load += origin.load

            # Actualizamos el flujo absoluto
            abs_flux += abs(origin.load)

            # Ajustamos a cero el valor de la carga en origen
            self.G.nodes[origin_index].load = 0.0

            # Una vez atendida la ID más larga de la lista, la desalojamos
            self.global_ids.pop(0)

            # Incrementamos el contador de iteraciones
            iteration += 1


        # Devolvemos el balance total
        ret_load = self.G.nodes[self.root].load
        self.G.nodes[self.root].load = 0.0

        return [ret_load, abs_flux]

    def are_enlclosedLoads(self):
        """Funcion para ver si hay cargas encerradas"""
        for node in self.G.nodes:
            if self.G.nodes[node].load != 0:
                if node != self.G.root:
                    return True
        else:
            return False

    @staticmethod
    def key_sort_by_HLMAC_len(id):
        """
        Función para key para ordenar el listado global de IDs en función de la longitud de las HLMACs
        """
        return len(id.hlmac)

    def updateLoads(self, loads, delta):
        """
        Funcion para actualizar las cargas de los nodos del grafo
        """

        # Como solo tenemos las cargas de los nodos normales, vamos a poner a 0 todos y establecer las cargas de los normales
        for node in self.G.nodes:
            if node in loads:
                self.G.nodes[node].load = loads[node][delta]
            else:
                self.G.nodes[node].load = 0

    def clearSelectedIDs(self):
        """
        Función para borrar el flag de active de todas las IDs de cada nodo
        """
        # Limpiamos las IDs globales
        self.global_ids = list()

        # De esta forma podemos volver a tomar una función objetivo
        for node in self.G.nodes:
            for j in range(0, len(self.G.nodes[node].ids)):
                self.G.nodes[node].ids[j].active = False


# Worker function que procesa un único run (topo folder + run_idx + root)
def process_run(base, fld, conf_path, topo_out_dir, run_idx, root, criteria, criteria_names, max_iter, seed):
    """
    Procesa un run para una única topología (fld) y un root dado.
    Crea el CSV de salida: topo_out_dir/run_XX_root_YYY_seed_ZZ.csv
    """
    try:
        # Establecer semilla reproducible para este worker (determinista)
        s = seed + hash(fld) % 100000 + run_idx
        random.seed(s)
        np.random.seed(s)

        # Leer archivos desde disco (evitamos pasar grandes objetos entre procesos)
        p = os.path.join(base, fld)
        edges = getEdges(os.path.join(p, "links.csv"))
        loads = getLoads(os.path.join(p, "loads.csv"), 3)
        confs = getEdges_Config(conf_path)

        # Construir grafo y difundir IDs
        G_root = Graph(0, loads, edges, [], confs, root=root)
        den_root = Den2ne(G_root)
        den_root.spread_ids()  # una vez por root

        # Nombre fichero CSV para este run/root (guardamos seed para trazabilidad)
        csv_fname = os.path.join(
            topo_out_dir,
            f"run_{run_idx:02d}_root_{root}_seed_{seed}.csv"
        )

        with open(csv_fname, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            header = ["Delta"] + criteria_names
            writer.writerow(header)

            num_deltas = len(loads[root])
            for delta in range(num_deltas):
                row_times = [delta]

                # Nota: aquí hacemos una copia profunda del grafo ya etiquetado para cada criterio
                # (podríamos optimizar más, pero así mantenemos el comportamiento original)
                for crit in criteria:
                    Gc = copy.deepcopy(G_root)
                    alg = Den2ne(Gc)
                    alg.updateLoads(loads, delta)

                    t_start = time.time()
                    iter_count = 0
                    while True:
                        alg.clearSelectedIDs()
                        alg.selectBestIDs(crit)
                        alg.globalBalance(
                            withLosses=False,
                            withCap=False,
                            withDebugPlot=False,
                            positions=None,
                            path=None,
                        )
                        iter_count += 1
                        if (not alg.are_enlclosedLoads()) or (iter_count >= max_iter):
                            break
                    t_end = time.time()
                    duration = round(t_end - t_start, 6)
                    row_times.append(duration)

                writer.writerow(row_times)

        return (True, fld, run_idx, root, csv_fname)

    except Exception as e:
        return (False, fld, run_idx, root, str(e))


def test_all_topos(parallel=True, max_workers=None):
    # reproducibilidad para la selección de roots (en hilo principal)
    random.seed(SEED)
    np.random.seed(SEED)

    base = "topo"
    conf_path = "links_config_8.csv"
    out_base = "results_iterative"
    criteria = [
        Den2ne.CRITERION_NUM_HOPS,
        Den2ne.CRITERION_LOW_LINKS_LOSSES,
        Den2ne.CRITERION_POWER_TO_ZERO,
        Den2ne.CRITERION_POWER_TO_ZERO_WITH_LOSSES,
    ]
    criteria_names = ["Hops(s)", "lowLinksLoss(s)", "Power2Zero(s)", "Power2Zero+Links(s)"]
    max_iter = 30

    os.makedirs(out_base, exist_ok=True)

    # Construir lista de tareas (topo folder, run_idx, root, outdir)
    tasks = []
    for fld in sorted(os.listdir(base)):
        if not fld.startswith("topo_"):
            continue

        n = int(fld.split("_")[1])
        p = os.path.join(base, fld)
        loads = getLoads(os.path.join(p, "loads.csv"), 3)
        all_nodes = list(loads.keys())
        all_nodes.sort()  # orden determinista

        topo_out_dir = os.path.join(out_base, fld)
        os.makedirs(topo_out_dir, exist_ok=True)

        # Elegir 10 roots determinísticos (con la semilla ya fijada)
        if len(all_nodes) >= 10:
            chosen_roots = random.sample(all_nodes, k=10)
        else:
            chosen_roots = [random.choice(all_nodes) for _ in range(10)]

        for run_idx, root in enumerate(chosen_roots, start=1):
            tasks.append({
                "base": base,
                "fld": fld,
                "conf_path": conf_path,
                "topo_out_dir": topo_out_dir,
                "run_idx": run_idx,
                "root": root,
                "criteria": criteria,
                "criteria_names": criteria_names,
                "max_iter": max_iter,
                "seed": SEED
            })

    # Ejecutar tareas: secuencial o paralelo
    if not parallel:
        print("[INFO] Ejecutando en modo secuencial")
        # uso tqdm para visualizar progreso en secuencial
        for t in tqdm(tasks, desc="Runs", unit="run"):
            ok, fld, run_idx, root, info = process_run(
                t["base"], t["fld"], t["conf_path"], t["topo_out_dir"],
                t["run_idx"], t["root"], t["criteria"],
                t["criteria_names"], t["max_iter"], t["seed"]
            )
            if ok:
                tqdm.write(f"[OK] {fld} run {run_idx} root {root} -> {info}")
            else:
                tqdm.write(f"[ERR] {fld} run {run_idx} root {root} -> {info}")
    else:
        # Parallel: usar ProcessPoolExecutor
        cpu_count = os.cpu_count() or 2
        if max_workers is None:
            max_workers = max(1, cpu_count - 1)  # deja 1 core libre por seguridad
        else:
            max_workers = min(max_workers, cpu_count)

        print(f"[INFO] Ejecutando en paralelo con max_workers={max_workers}")

        # Usamos map con submit/as_completed y envolvemos con tqdm para progreso
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as exe:
            futures = []
            for t in tasks:
                fut = exe.submit(
                    process_run,
                    t["base"], t["fld"], t["conf_path"], t["topo_out_dir"],
                    t["run_idx"], t["root"], t["criteria"],
                    t["criteria_names"], t["max_iter"], t["seed"]
                )
                futures.append(fut)

            # tqdm sobre as_completed para mostrar progreso a medida que se completan tareas
            for fut in tqdm(concurrent.futures.as_completed(futures),
                            total=len(futures), desc="Runs completed", unit="run"):
                ok, fld, run_idx, root, info = fut.result()
                if ok:
                    tqdm.write(f"[OK] {fld} run {run_idx} root {root} -> {info}")
                else:
                    tqdm.write(f"[ERR] {fld} run {run_idx} root {root} -> {info}")
if __name__ == "__main__":
    # Lanza la función principal en paralelo (o cambialo a parallel=False para debug)
    test_all_topos(parallel=True, max_workers=None)