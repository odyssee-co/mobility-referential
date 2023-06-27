import osmium

# Convert the .osm file to .osm.pbf format using osmium
class OSMToPBFHandler(osmium.SimpleHandler):
    def __init__(self, writer):
        super(OSMToPBFHandler, self).__init__()
        self.writer = writer

    def node(self, n):
        self.writer.add_node(n)

    def way(self, w):
        self.writer.add_way(w)

    def relation(self, r):
        self.writer.add_relation(r)

def xml_to_pbf(graph_input, graph_output):
    writer = osmium.SimpleWriter(graph_output)
    handler = OSMToPBFHandler(writer)
    handler.apply_file(graph_input)
    writer.close()
