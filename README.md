# Mobref

## Introduction
Mobref is a powerful framework designed to enhance mobility analysis and optimize territories by integrating various tools. Mobref streamlines complex mobility analyses by seamlessly integrating various data sources and employing advanced algorithms. With an unified interface and very fast processing, it provides a solid foundation for in-depth mobility studies, offering comprehensive solutions for route planning, accessibility analysis, and logistics optimization.


## Key Features

### 1. **Geospatial Data Extraction**
Mobref facilitates the extraction of cartographic data, reconstructs navigable road networks for pedestrians, cars, and bicycles in the form of graphs, incorporating road orientations and speeds. It also extracts points of interest, building footprints, elevation data, and more.

### 2. **Multimodal Network Creation**
- **Data Acquisition and Validation:** Mobref acquires, validates, and processes data from public transportation networks based on operational schedules, aggregating regional data.
- **Multimodal Graph Calculation:** It computes a multimodal graph integrating pedestrian and public transportation data.
- **Impedance Calculation:** Mobref calculates network impedance considering the day of the week and time of day, estimating average waiting times at public transportation stops.

### 3. **Multimodal Travel Time Matrices**
- **Hierarchical Graph Contraction Algorithm:** Mobref utilizes a hierarchical graph contraction algorithm for rapid calculation of shortest paths.
- **Points of Interest Selection:** It allows the selection of various points of interest (POIs) and calculates distances (and associated travel times) from each POI to all other POIs for each mode of transport.

### 4. **Accessibility Analysis**
- **Hierarchical Contraction Hierarchies:** Mobref utilizes transport graph contraction hierarchies to compute aggregated accessibility measures, representing a user's ability to reach specified locations in the city.
- **Nearby Facilities Search:** It identifies the n nearest facilities within a specific radius (or travel time) for all points in the graph within fractions of a second.
- **Isochrone Analysis:** Mobref displays the number of accessible facilities within a given isochrone for each point in the graph.

### 5. **Logistic Routing**
- **Vehicle Routing Problem (VRP):** Mobref addresses the Vehicle Routing Problem, focusing on optimal route planning for a fleet of vehicles engaged in deliveries or services.
- **Efficient Route Calculation:** It aims to find the most efficient routes for vehicles, minimizing total costs while adhering to specific constraints.


## Installation and Data Setup

### Installation:
To install Mobref, follow these steps:

1. Clone the Mobref repository:
    ```bash
    git clone git@github.com:odyssee-co/mobility-referential.git
    ```

2. Install Mobref using pip:
    ```bash
    pip install mobility-referential/
    ```

### Download Necessary Data:
1. Get the French administrative boundaries from [data.gouv.fr](https://www.data.gouv.fr/fr/datasets/decoupage-administratif-communal-francais-issu-d-openstreetmap/). Unzip the file in your data directory.

2. Obtain GTFS data from [transport.data.gouv.fr](https://transport.data.gouv.fr/datasets/reseau-urbain-et-interurbain-dile-de-france-mobilites). Unzip the GTFS data in your data directory. Minimum required GTFS data types are: `stop_times`, `stops`, `routes`, and `trips`, along with either `calendar` or `calendar_dates`.

3. Prepare a file listing the INSEE codes (one per line) of the municipalities you wish to include in the analysis.

## Documentation and Demos

### Documentation:
Detailed documentation for Mobref can be found [here](link_to_documentation).

### Demos:
After editing the `conf-example.yml` file with the correct paths for your system, explore Mobref's capabilities by checking out the examples in the `examples` directory.

## Reporting Bugs
If you encounter any bugs or issues, please help us improve Mobref by reporting them on [GitHub issues](https://github.com/odyssee-co/mobility-referential/issues).

