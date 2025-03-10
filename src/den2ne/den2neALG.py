#!/usr/bin/python3

from .den2neHLMAC import HLMAC
import os


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

    def flowInertia(self, ids_to_fix=None, n_repetition=None):
        """
        Función para preservar la coherencia en el grafo de los distintos flujos
        """
        if (
            ids_to_fix != None
        ):  # Si no es la primera llamada de flowInertia, entonces cogemos las ids que no se han cambiado para tratar con ellas
            ids_list = ids_to_fix
        else:  # Si es la primera vez que se llama a flowInertia, se ejecuta seleccionando las IDs más grandes
            # Vamos a ordenar la lista de globals ids
            self.global_ids.sort(key=Den2ne.key_sort_by_HLMAC_len, reverse=True)
            ids_list = [
                j
                for j in self.global_ids
                if len(self.global_ids[0].hlmac) == len(j.hlmac)
            ]
        for ids_max_len in ids_list:
            for i in range(len(ids_max_len.hlmac) - 2, 0, -1):

                # Vamos a ver la ID más larga en el camino hacia el root
                nextNode = self.G.nodes[ids_max_len.hlmac[i]]

                # Miramos el index que debería haber
                nextID = nextNode.ids[nextNode.getIndexID(ids_max_len.hlmac[0 : i + 1])]

                if nextID not in self.global_ids:
                    # Sacamos la ID antigua de la lista
                    self.global_ids.remove(nextNode.getActiveID())

                    # Establecemos como activa la nueva ID
                    self.G.nodes[ids_max_len.hlmac[i]].ids[
                        nextNode.ids.index(nextNode.getActiveID())
                    ].active = False
                    self.G.nodes[ids_max_len.hlmac[i]].ids[
                        nextNode.ids.index(nextID)
                    ].active = True

                    # Actualizamos la lista
                    self.global_ids.append(nextID)

                    # Por último, notificamos a nuestros vecinos de la ramas anexas a la rama
                    # principal, para que sean conscientes de la incercia que está ocurriendo
                    # en aras de que entregen su potencia, antes que se recorra el camino principal
                    for neighbor in nextNode.neighbors:

                        # Para que sea un vecino valido no tiene que ser ni el nextHop ni el anterior
                        if (
                            neighbor not in ids_max_len.hlmac
                        ):  # Pongo esto porque si está en la id principal ya lo vamos a revisar más tarde y es tiempo de computo perdido creo yo

                            # En este punto desconocemos la longitud de la rama.. por ello vamos a recorrerla con un while
                            branch_nodes_to_attend = [neighbor]
                            branch_nodes_to_attended = [nextNode.name]

                            while len(branch_nodes_to_attend) > 0:

                                # Hay que visitar todos los vecinos de la rama que no hayan sido visitados
                                curr_node = self.G.nodes[branch_nodes_to_attend[0]]
                                # Bucle de exploración, comprobamos que no hayan sido visitados
                                # Atendemos al nodo en cuestión, si su HLMAC es más corta que el nodo de la rama
                                # principal, hay un problema.. hay que cambiar la HLMAC activa por la HLMAC que siga la incercia del
                                # camino principal
                                # Creo que esto deberíamos hacerlo solo si su anterior paso es el nodo que hemos cambiado
                                # es decir, si en este caso hemos cambiado el 0, solo cambiar los que en su ids tengan un 0
                                if nextID.getOrigin() in curr_node.getActiveID().hlmac:
                                    # Entonces este nodo está utilizando el nodo cuya ids hemos cambiado
                                    # Tenemos que revisar que esta ID esté bien
                                    if len(curr_node.getActiveID().hlmac) <= len(
                                        nextID.hlmac
                                    ) or nextID.hlmac.index(
                                        nextNode.name
                                    ) != curr_node.getActiveID().hlmac.index(
                                        nextNode.name
                                    ):
                                        possible_id = list()
                                        # Con la conectividad alta pueden darse casos que incluyan todos los nodos necesarios, más unos extras que no se corresponden con la id que queremos
                                        # Entonces lo que hacemos es guardar todas las ids que cumplen la condición de los saltos, y cogemos la más pequeña, que es la que tiene los saltos necesarios, sin extras
                                        for id in curr_node.ids:
                                            if all(
                                                hop in id.hlmac for hop in nextID.hlmac
                                            ):
                                                possible_id.append(id)
                                        if possible_id:
                                            possible_id.sort(
                                                key=Den2ne.key_sort_by_HLMAC_len
                                            )  # Cogemos la más pequeña
                                            # Sacamos la ID antigua de la lista
                                            self.global_ids.remove(
                                                curr_node.getActiveID()
                                            )

                                            # Marcamos como activa la nueva ID
                                            self.G.nodes[branch_nodes_to_attend[0]].ids[
                                                curr_node.ids.index(
                                                    curr_node.getActiveID()
                                                )
                                            ].active = False
                                            self.G.nodes[branch_nodes_to_attend[0]].ids[
                                                curr_node.ids.index(possible_id[0])
                                            ].active = True

                                            # Añadidmos la nueva ID a la lista
                                            self.global_ids.append(possible_id[0])
                                            # Si cambiamos la id, añadimos los vecinos a revisar
                                            for neig in curr_node.neighbors:
                                                if neig not in branch_nodes_to_attended:
                                                    branch_nodes_to_attend.append(neig)

                                    # Desalojamos al nodo atendido, y lo marcamos como atendido
                                    branch_nodes_to_attended.append(curr_node.name)
                                    branch_nodes_to_attend.pop(0)
                                else:
                                    # Desalojamos al nodo atendido, y lo marcamos como atendido
                                    branch_nodes_to_attended.append(curr_node.name)
                                    branch_nodes_to_attend.pop(0)
        # Una vez realizado flow inertia revisamos que los ids sean correctos
        # Para evitar bucles infinitos pasamos el parámetro repeticion
        if n_repetition == None or n_repetition <= 10:
            self.IDsCheck(n_repetition)

    def selectBestIDs(self, criterion):
        """
        Función para decidir la mejor ID de en nodo dado un criterio
        """

        # Vamos a elegir la mejor ID para cada nodo
        if Den2ne.CRITERION_NUM_HOPS == criterion:
            self.selectBestID_by_hops()

        elif Den2ne.CRITERION_DISTANCE == criterion:
            self.selectBestID_by_distance()

        elif Den2ne.CRITERION_LINKS_LOSSES == criterion:
            self.selectBestID_by_Links_Losses()

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

    def selectBestID_by_distance(self):
        """
        Función para decidir la mejor ID de un nodo por distancia al root
        """
        for node in self.G.nodes:
            dists = [self.getTotalDistance(id) for id in self.G.nodes[node].ids]

            self.G.nodes[node].ids[dists.index(min(dists))].active = True
            self.global_ids.append(self.G.nodes[node].getActiveID())

        #self.flowInertia()

    def getTotalDistance(self, id):
        """
        Funcion para calcular la distancia total de una HLMAC
        """
        distances = 0
        for i in range(0, len(id.hlmac) - 1):
            distances += (
                self.G.nodes[id.hlmac[i]]
                .links[self.G.nodes[id.hlmac[i]].neighbors.index(id.hlmac[i + 1])]
                .dist
            )

        return distances

    def selectBestID_by_Links_Losses(self):
        """
        Función para decidir la mejor ID de un nodo en función de sus perdidas al root
        """
        for node in self.G.nodes:
            losses = [self.getTotalLinks_Losses(id) for id in self.G.nodes[node].ids]

            self.G.nodes[node].ids[losses.index(min(losses))].active = True
            self.global_ids.append(self.G.nodes[node].getActiveID())

        #self.flowInertia()

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

        #self.flowInertia()

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

        #self.flowInertia()

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

    def IDsCheck(self, n_repetition=0):
        """
        Función que revisa que todas las IDs seleccionadas son coherentes
        y por tanto no se quedará carga en nodos distintos al root
        """
        ids_to_fix = list()
        if n_repetition == None:
            n_repetition = 0
        else:
            n_repetition = n_repetition + 1
        for i in self.global_ids:
            nextHop = i.getNextHop()
            if nextHop != None and self.G.nodes[nextHop].getActiveID().hlmac.index(
                nextHop
            ) > i.hlmac.index(nextHop):
                ids_to_fix.append(i)
        if len(ids_to_fix) != 0:
            self.flowInertia(ids_to_fix, n_repetition)

    def globalBalance(self, withLosses, withCap, withDebugPlot, positions, path):
        """
        Funcion que obtniene el balance global de la red y la dirección de cada enlace (hacia donde va el flujo de potencia)
        """

        # Primero hay que ordenar la lista de global_ids de mayor a menor
        self.global_ids.sort(key=Den2ne.key_sort_by_HLMAC_len, reverse=True)

        # Vamos a estudiar tambien el abs() del movimiento de flujo de Potencia
        abs_flux = 0.0

        # Vamos tambien a prestar atencion a la capacidad
        cap = 0.0

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

            cap = self.G.getLinkCapacity(origin.name, dst.name)


            # Agregamos la carga de origen a destino
            if withLosses and withCap:
                if cap is None or cap >= origin.load:
                    self.G.nodes[dst_index].load += origin.load - origin.links[
                        origin.neighbors.index(dst.name)
                    ].getLosses(origin.load)

                    # Actualizamos el flujo absoluto
                    abs_flux += abs(
                        origin.load
                        - origin.links[origin.neighbors.index(dst.name)].getLosses(
                            origin.load
                        )
                    )

                else:
                    self.G.nodes[dst_index].load += cap - origin.links[
                        origin.neighbors.index(dst.name)
                    ].getLosses(cap)

                    # Actualizamos el flujo absoluto
                    abs_flux += abs(
                        cap
                        - origin.links[origin.neighbors.index(dst.name)].getLosses(cap)
                    )

            elif withLosses:
                self.G.nodes[dst_index].load += origin.load - origin.links[
                    origin.neighbors.index(dst.name)
                ].getLosses(origin.load)

                # Actualizamos el flujo absoluto
                abs_flux += abs(
                    origin.load
                    - origin.links[origin.neighbors.index(dst.name)].getLosses(
                        origin.load
                    )
                )

            elif withCap:
                if cap is None or cap >= origin.load:
                    self.G.nodes[dst_index].load += origin.load

                    # Actualizamos el flujo absoluto
                    abs_flux += abs(origin.load)
                else:
                    self.G.nodes[dst_index].load += cap

                    # Actualizamos el flujo absoluto
                    abs_flux += abs(cap)

            else:
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

    def write_ids_report(self, filename):
        """
        Función que genera un fichero de log con el resultado de las asignaciones de las IDs
        """
        with open(filename, "w") as file:
            for node in self.G.nodes:
                file.write(
                    "-------------------------------------------------------------------------"
                )
                file.write(
                    "-------------------------------------------------------------------------\n"
                )
                file.write(
                    f"| Node: {self.G.nodes[node].name}  | Type: {self.G.nodes[node].type} | Neighbors: {len(self.G.nodes[node].neighbors)} \n"
                )
                file.write(
                    "-------------------------------------------------------------------------"
                )
                file.write(
                    "-------------------------------------------------------------------------\n"
                )
                file.write(
                    "|  Status  |  ID                                                              \n"
                )
                file.write(
                    "-------------------------------------------------------------------------"
                )
                file.write(
                    "-------------------------------------------------------------------------\n"
                )
                for id in self.G.nodes[node].ids:
                    file.write(f"|   {id.used}   |  {HLMAC.hlmac_addr_print(id)} \n")
                file.write(
                    "-------------------------------------------------------------------------"
                )
                file.write(
                    "-------------------------------------------------------------------------\n"
                )
                file.write("\n")

    def write_loads_report(self, filename):
        """
        Función que genera un fichero de log con el resultado de las asignaciones de carga
        """
        with open(filename, "w") as file:
            for node in self.G.nodes:
                file.write(
                    "-------------------------------------------------------------------------"
                )
                file.write(
                    "-------------------------------------------------------------------------\n"
                )
                file.write(
                    f"| Node: {self.G.nodes[node].name}  | Type: {self.G.nodes[node].type} | Neighbors: {len(self.G.nodes[node].neighbors)} | Load: {self.G.nodes[node].load} \n"
                )
                file.write(
                    "-------------------------------------------------------------------------"
                )
                file.write(
                    "-------------------------------------------------------------------------\n"
                )
                file.write(
                    "|    Flag    |  ID                                                              \n"
                )
                file.write(
                    "-------------------------------------------------------------------------"
                )
                file.write(
                    "-------------------------------------------------------------------------\n"
                )
                for id in self.G.nodes[node].ids:
                    file.write(
                        f"|     {int(id.active)}     |  {HLMAC.hlmac_addr_print(id)} \n"
                    )
                file.write(
                    "-------------------------------------------------------------------------"
                )
                file.write(
                    "-------------------------------------------------------------------------\n"
                )
                file.write("\n")

    def write_swConfig_report(self, filename):
        """
        Función que genera un fichero de log con el resultado de la config lógica de la red
        """
        with open(filename, "w") as file:
            for key in self.G.sw_config:
                file.write(
                    "-------------------------------------------------------------------------\n"
                )
                file.write(
                    f'| ID: {key}  | Node A: {self.G.sw_config[key]["node_a"]} | Node B: {self.G.sw_config[key]["node_b"]} | Status: {self.G.sw_config[key]["state"]}                    |\n'
                )
                file.write(
                    "-------------------------------------------------------------------------\n"
                )
                file.write("\n")

    def write_swConfig_CSV(self, filename):
        """
        Función que genera un fichero CSV con el resultado de la config lógica de la red
        """
        with open(filename, "w") as file:
            file.write("ID,Node A,Node B,State\n")
            for key in self.G.sw_config:
                file.write(
                    f'{key},{self.G.sw_config[key]["node_a"]},{self.G.sw_config[key]["node_b"]},{self.G.sw_config[key]["state"]}\n'
                )
