#!/usr/bin/python3

from .node import Node
from .link import Link


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

