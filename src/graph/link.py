#!/usr/bin/python3


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
