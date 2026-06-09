### The Architecture Diagram Code (`architecture.py`)

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.storage import S3
from diagrams.azure.compute import FunctionApps
from diagrams.azure.storage import DataLakeStorage
from diagrams.azure.analytics import Databricks
from diagrams.onprem.analytics import Spark
from diagrams.onprem.analytics import Tableau
from diagrams.onprem.analytics import Powerbi
from diagrams.onprem.network import Internet

# Define the diagram attributes
graph_attr = {
    "fontsize": "15",
    "bgcolor": "white",
    "pad": "0.5"
}

with Diagram("Citi Bike Mobility Analytics Pipeline", show=False, filename="assets/citi_bike_architecture",
             graph_attr=graph_attr):
    # 1. Ingestion Sources
    with Cluster("External Data Sources"):
        historical_s3 = S3("Citi Bike S3 Bucket\n(Historical CSVs)")
        gbfs_api = Internet("GBFS API\n(Real-Time JSON)")

    # 2. Azure Serverless Ingestion
    with Cluster("Azure Serverless"):
        az_function = FunctionApps("Azure Function\n(Timer Trigger)")

    # 3. Azure Data Lake (Medallion Architecture)
    with Cluster("Azure Data Lake Storage Gen2 (Delta Lake)"):
        bronze_layer = DataLakeStorage("Bronze Layer\n(Raw Data)")
        silver_layer = DataLakeStorage("Silver Layer\n(Cleaned/Enriched)")
        gold_layer = DataLakeStorage("Gold Layer\n(Star Schema)")

    # 4. Processing & Machine Learning
    with Cluster("Azure Databricks Workspace"):
        databricks_jobs = Databricks("Workflows (Orchestration)")
        pyspark_etl = Spark("PySpark ETL\n(Data Prep)")
        ml_models = Spark("Spark MLlib & Sklearn\n(Clustering & Forecasting)")

    # 5. Business Intelligence
    with Cluster("Data Visualisation (BI)"):
        tableau = Tableau("Tableau\n(EDA & Spatial Maps)")
        power_bi = Powerbi("Power BI\n(Executive KPIs)")

    # --- Define the Connections (Data Flow) ---

    # Ingestion Flow
    gbfs_api >> Edge(label="Pull Live Status (Minute)") >> az_function
    az_function >> Edge(label="Append JSON") >> bronze_layer
    historical_s3 >> Edge(label="Batch Download") >> bronze_layer

    # ETL Flow (Bronze to Silver to Gold)
    bronze_layer >> Edge(label="Read Raw") >> pyspark_etl
    pyspark_etl >> Edge(label="Clean/Format") >> silver_layer
    silver_layer >> Edge(label="Aggregate") >> pyspark_etl
    pyspark_etl >> Edge(label="Write Fact/Dim Tables") >> gold_layer

    # Machine Learning Flow
    silver_layer >> Edge(label="Feature Engineering") >> ml_models
    ml_models >> Edge(label="Predictive Demand Data") >> gold_layer

    # Visualization Flow
    gold_layer >> Edge(label="Direct Query") >> tableau
    gold_layer >> Edge(label="Direct Query") >> power_bi

    # Orchestration Connections
    databricks_jobs >> Edge(style="dashed", color="gray", label="Schedules") >> pyspark_etl