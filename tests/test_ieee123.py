import unittest
from graph.graph import Graph
from den2ne.den2neALG import Den2ne
from dataCollector.dataCollector import DataGatherer

class TestIEEE123(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.loads = DataGatherer.getLoads("src/data/loads/loads_v2.csv", 3)
        cls.edges = DataGatherer.getEdges("src/data/ieee123/links.csv")
        cls.edges_conf = DataGatherer.getEdges_Config("src/data/links/links_config.csv")
        cls.sw_edges = DataGatherer.getSwitches("src/data/ieee123/switches.csv")
        cls.positions = DataGatherer.getPositions("src/data/ieee123/node_positions.csv")
        
        cls.G = Graph(0, cls.loads, cls.edges, cls.sw_edges, cls.edges_conf, root="150")
        cls.G.pruneGraph()
        cls.G_den2ne_alg = Den2ne(cls.G)
        cls.G_den2ne_alg.spread_ids()

    def test_a_spread_ids(self):
        global_ids = list()
        for node in self.G_den2ne_alg.G.nodes:
            for id in self.G_den2ne_alg.G.nodes[node].ids:
                global_ids.append(id)            
        self.assertTrue(len(global_ids) > len(self.G_den2ne_alg.G.nodes))

    def test_b_update_loads(self):
        initial_loads = self.G_den2ne_alg.G.nodes["1"].load
        self.G_den2ne_alg.updateLoads(self.loads, 1)
        self.assertNotEqual(initial_loads, self.G_den2ne_alg.G.nodes["1"].load)

    def test_c_select_best_ids(self):
        self.G_den2ne_alg.selectBestIDs(Den2ne.CRITERION_NUM_HOPS)
        self.assertTrue(len(self.G_den2ne_alg.global_ids) > 0)

    def test_d_global_balance(self):
        self.G_den2ne_alg.updateLoads(self.loads, 1)
        self.G_den2ne_alg.clearSelectedIDs()
        self.G_den2ne_alg.selectBestIDs(Den2ne.CRITERION_NUM_HOPS)
        balance, flux = self.G_den2ne_alg.globalBalance(withLosses=False, withCap=False, withDebugPlot=False, positions=self.positions, path="results/")
        self.assertIsInstance(balance, (int, float))
        self.assertIsInstance(flux, (int, float))

if __name__ == "__main__":
    unittest.main()
