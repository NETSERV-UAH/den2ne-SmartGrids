import unittest
from graph.graph import Graph
from den2ne.den2neALG import Den2ne
from dataCollector.dataCollector import DataGatherer

class TestIEEE123(unittest.TestCase):
    
    def setUp(self):
        self.loads = DataGatherer.getLoads("../src/data/loads/loads_v2.csv", 3)
        self.edges = DataGatherer.getEdges("../src/data/links.csv")
        self.edges_conf = DataGatherer.getEdges_Config("../src/data/links_config.csv")
        self.sw_edges = DataGatherer.getSwitches("../src/data/switches.csv")
        self.positions = DataGatherer.getPositions("../src/data/node_positions.csv")
        
        self.G = Graph(0, self.loads, self.edges, self.sw_edges, self.edges_conf, root="150")
        self.G.pruneGraph()
        self.G_den2ne_alg = Den2ne(self.G)
        
    def test_spread_ids(self):
        self.G_den2ne_alg.spread_ids()
        self.assertTrue(len(self.G_den2ne_alg.global_ids) > 0)

    def test_update_loads(self):
        initial_loads = self.G_den2ne_alg.G.nodes["1"].copy()
        self.G_den2ne_alg.updateLoads(self.loads, 1)
        self.assertNotEqual(initial_loads, self.G_den2ne_alg.G.nodes["1"])

    def test_select_best_ids(self):
        self.G_den2ne_alg.selectBestIDs(Den2ne.CRITERION_NUM_HOPS)
        self.assertTrue(len(self.G_den2ne_alg.global_ids) > 0)

    def test_global_balance(self):
        self.G_den2ne_alg.updateLoads(self.loads, 1)
        self.G_den2ne_alg.selectBestIDs(Den2ne.CRITERION_NUM_HOPS)
        balance, flux = self.G_den2ne_alg.globalBalance(withLosses=False, withCap=False, withDebugPlot=False, positions=self.positions, path="results/")
        self.assertIsInstance(balance, (int, float))
        self.assertIsInstance(flux, (int, float))

if __name__ == "__main__":
    unittest.main()