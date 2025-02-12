#!/usr/bin/python3

import pathlib
from graph.graph import Graph
from den2ne.den2neALG import Den2ne
from dataCollector.dataCollector import DataGatherer

# Vars just for debugging
# Definir los códigos de color
GREEN = "\033[92m"
BLUE = "\033[94m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Definir los anchos de las columnas
delta_width = 3
criteria_width = 3
ideal_case_width = 20
balance_width = 10
flow_width = 10


# Vamos a programar unas pruebas globales sobre la topología IEEE 123
def test_ieee123():

    # Variables
    dirs = ["reports", "csv", "fig"]
    topo_name = "ieee123"
    criteria = [
        Den2ne.CRITERION_NUM_HOPS,
        Den2ne.CRITERION_DISTANCE,
        Den2ne.CRITERION_LINKS_LOSSES,
        Den2ne.CRITERION_POWER_TO_ZERO,
        Den2ne.CRITERION_POWER_TO_ZERO_WITH_LOSSES,
    ]
    out_data = dict()

    # Preparamos los directorios de resultados
    for dir in dirs:
        pathlib.Path("results/" + topo_name + "/" + dir).mkdir(
            parents=True, exist_ok=True
        )

    # Recolectamos los datos
    loads = DataGatherer.getLoads("data/loads/loads_v2.csv", 3)
    edges = DataGatherer.getEdges("data/links.csv")
    edges_conf = DataGatherer.getEdges_Config("data/links_config.csv")
    sw_edges = DataGatherer.getSwitches("data/switches.csv")
    positions = DataGatherer.getPositions("data/node_positions.csv")

    # Creamos la var del grafo para el primer instante
    G = Graph(0, loads, edges, sw_edges, edges_conf, root="150")

    # Podamos los nodos virtuales que estén a modo de ampliación.
    G.pruneGraph()

    # Iniciamos el algoritmo
    G_den2ne_alg = Den2ne(G)

    # Primera fase: difusión de IDs
    G_den2ne_alg.spread_ids()

    # Vamos a iterar por todos los intantes de cargas
    for delta in range(0, len(loads["1"])):

        out_data[delta] = dict()

        # Vamos a iterar por criterio
        for criterion in criteria:

            # Init Loads
            G_den2ne_alg.updateLoads(loads, delta)
            G_den2ne_alg.clearSelectedIDs()
            G_den2ne_alg.selectBestIDs(criterion)

            #  ----------------     Ideal balance      ----------------
            [total_balance_ideal, abs_flux] = G_den2ne_alg.globalBalance(
                withLosses=False,
                withCap=False,
                withDebugPlot=False,
                positions=positions,
                path="results/",
            )
            scenario = "IDEAL"
            message = (
                f"[DEBUG][Delta {delta:<{delta_width}}] "
                f"{GREEN}[Criteria {BOLD}{criterion:>{criteria_width}}{RESET}]{RESET} "
                f"{BLUE}[Scenario {BOLD} {scenario:<{15}}{RESET}] --> "
                f"{RED}[Balance {BOLD}{total_balance_ideal:^{balance_width}.2f}{RESET} kW]{RESET} "
                f"{BLUE}[Flow {BOLD}{abs_flux:^{flow_width}.2f}{RESET} kW]{RESET}"
            )
            # Imprimir el mensaje
            print(message)

            # Genearación de informes
            G_den2ne_alg.write_loads_report(
                f"results/{topo_name}/reports/report_loads_d{delta}_ideal_c{criterion}.txt"
            )

            # Re-Init loads
            G_den2ne_alg.updateLoads(loads, delta)
            G_den2ne_alg.clearSelectedIDs()
            G_den2ne_alg.selectBestIDs(criterion)

            #  ----------------     Withloss balance      ----------------
            [total_balance_with_losses, abs_flux_with_losses] = (
                G_den2ne_alg.globalBalance(
                    withLosses=True,
                    withCap=False,
                    withDebugPlot=False,
                    positions=positions,
                    path="results/",
                )
            )
            scenario = "LOSS"
            message = (
                f"[DEBUG][Delta {delta:<{delta_width}}] "
                f"{GREEN}[Criteria {BOLD}{criterion:>{criteria_width}}{RESET}]{RESET} "
                f"{BLUE}[Scenario {BOLD} {scenario:<{15}}{RESET}] --> "
                f"{RED}[Balance {BOLD}{total_balance_with_losses:^{balance_width}.2f}{RESET} kW]{RESET} "
                f"{BLUE}[Flow {BOLD}{abs_flux_with_losses:^{flow_width}.2f}{RESET} kW]{RESET}"
            )
            # Imprimir el mensaje
            print(message)

            # Genearación de informes
            G_den2ne_alg.write_loads_report(
                f"results/{topo_name}/reports/report_loads_d{delta}_losses_c{criterion}.txt"
            )

            # Re-Init loads
            G_den2ne_alg.updateLoads(loads, delta)
            G_den2ne_alg.clearSelectedIDs()
            G_den2ne_alg.selectBestIDs(criterion)

            #  ----------------     Withloss and Cap balance      ----------------
            [total_balance_with_lossesCap, abs_flux_with_lossesCap] = (
                G_den2ne_alg.globalBalance(
                    withLosses=True,
                    withCap=True,
                    withDebugPlot=False,
                    positions=positions,
                    path="results/",
                )
            )
            scenario = "LOSS_CAP"
            message = (
                f"[DEBUG][Delta {delta:<{delta_width}}] "
                f"{GREEN}[Criteria {BOLD}{criterion:>{criteria_width}}{RESET}]{RESET} "
                f"{BLUE}[Scenario {BOLD} {scenario:<{15}}{RESET}] --> "
                f"{RED}[Balance {BOLD}{total_balance_with_lossesCap:^{balance_width}.2f}{RESET} kW]{RESET} "
                f"{BLUE}[Flow {BOLD}{abs_flux_with_lossesCap:^{flow_width}.2f}{RESET} kW]{RESET}"
            )
            # Imprimir el mensaje
            print(message)

            # ------------------------ Save data --------------------------
            out_data[delta][criterion] = {
                "total_balance_ideal": total_balance_ideal,
                "abs_flux": abs_flux,
                "total_balance_with_losses": total_balance_with_losses,
                "abs_flux_with_losses": abs_flux_with_losses,
                "total_balance_with_lossesCap": total_balance_with_lossesCap,
                "abs_flux_with_lossesCap": abs_flux_with_lossesCap,
            }

            # Genearación de informes
            G_den2ne_alg.write_swConfig_report(
                f"results/{topo_name}/reports/report_swConfig_d{delta}_c{criterion}.txt"
            )

            G_den2ne_alg.write_loads_report(
                f"results/{topo_name}/reports/report_loads_d{delta}_lossesCap_c{criterion}.txt"
            )

            # Generamos la configuración logica
            G_den2ne_alg.write_swConfig_CSV(
                f"results/{topo_name}/csv/swConfig_d{delta}_c{criterion}.csv"
            )

        # Exportamos los datos para un valor de delta
        with open(f"results/{topo_name}/csv/outdata_d{delta}.csv", "w") as file:
            file.write(
                "criterion,power_ideal,abs_ideal,power_wloss,abs_wloss,power_wlossCap,abs_wlossCap\n"
            )
            for criterion in out_data[delta]:
                file.write(
                    f'{criterion},{out_data[delta][criterion]["total_balance_ideal"]},{out_data[delta][criterion]["abs_flux"]},'
                )
                file.write(
                    f'{out_data[delta][criterion]["total_balance_with_losses"]}, {out_data[delta][criterion]["abs_flux_with_losses"]},'
                )
                file.write(
                    f'{out_data[delta][criterion]["total_balance_with_lossesCap"]},{out_data[delta][criterion]["abs_flux_with_lossesCap"]}\n'
                )

    G_den2ne_alg.write_ids_report(f"results/{topo_name}/reports/report_ids.txt")


if __name__ == "__main__":
    test_ieee123()
