"""
load_graph.py - Creates a sample CMDB graph in Neo4j
Hard-codes a small graph of Assets, Services, Users, and Locations
"""
import os
from neo4j import GraphDatabase

# Connection settings
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")


class GraphLoader:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def clear_database(self):
        """Clear all nodes and relationships"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("✓ Database cleared")

    def create_constraints(self):
        """Create uniqueness constraints"""
        with self.driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Asset) REQUIRE a.name IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Service) REQUIRE s.name IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.name IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (l:Location) REQUIRE l.name IS UNIQUE",
            ]
            for constraint in constraints:
                session.run(constraint)
            print("✓ Constraints created")

    def load_sample_data(self):
        """Load sample CMDB data"""
        with self.driver.session() as session:
            # Create Locations
            session.run("""
                MERGE (dc1:Location {name: 'Data-Center-1', region: 'US-East', city: 'Virginia'})
                MERGE (dc2:Location {name: 'Data-Center-2', region: 'US-West', city: 'Oregon'})
                MERGE (office:Location {name: 'HQ-Office', region: 'US-East', city: 'New York'})
            """)
            print("✓ Locations created")

            # Create Assets
            session.run("""
                MERGE (db:Asset {name: 'DB-Server', type: 'Database', os: 'Linux', status: 'Running'})
                MERGE (web1:Asset {name: 'Web-Server-1', type: 'Web Server', os: 'Linux', status: 'Running'})
                MERGE (web2:Asset {name: 'Web-Server-2', type: 'Web Server', os: 'Linux', status: 'Running'})
                MERGE (lb:Asset {name: 'Load-Balancer', type: 'Network', os: 'Linux', status: 'Running'})
                MERGE (cache:Asset {name: 'Redis-Cache', type: 'Cache', os: 'Linux', status: 'Running'})
                MERGE (api:Asset {name: 'Web-API', type: 'API Server', os: 'Linux', status: 'Running'})
                MERGE (backup:Asset {name: 'Backup-Server', type: 'Storage', os: 'Linux', status: 'Running'})
            """)
            print("✓ Assets created")

            # Create Services
            session.run("""
                MERGE (payroll:Service {name: 'Payroll-Service', criticality: 'High', sla: '99.9%'})
                MERGE (email:Service {name: 'Email-Service', criticality: 'Medium', sla: '99.5%'})
                MERGE (portal:Service {name: 'Employee-Portal', criticality: 'High', sla: '99.9%'})
            """)
            print("✓ Services created")

            # Create Users
            session.run("""
                MERGE (john:User {name: 'John Smith', role: 'DevOps Engineer', email: 'john@company.com'})
                MERGE (sarah:User {name: 'Sarah Johnson', role: 'Product Owner', email: 'sarah@company.com'})
                MERGE (mike:User {name: 'Mike Davis', role: 'System Admin', email: 'mike@company.com'})
            """)
            print("✓ Users created")

            # Create relationships - Location (run each separately)
            location_rels = [
                ("DB-Server", "Data-Center-1"),
                ("Web-Server-1", "Data-Center-1"),
                ("Web-Server-2", "Data-Center-2"),
                ("Load-Balancer", "Data-Center-1"),
                ("Redis-Cache", "Data-Center-1"),
                ("Web-API", "Data-Center-1"),
                ("Backup-Server", "Data-Center-2"),
            ]
            for asset, location in location_rels:
                session.run("""
                    MATCH (a:Asset {name: $asset})
                    MATCH (l:Location {name: $location})
                    MERGE (a)-[:LOCATED_IN]->(l)
                """, asset=asset, location=location)
            print("✓ Location relationships created")

            # Create dependencies
            dependencies = [
                ("Load-Balancer", "Web-Server-1", "traffic-routing"),
                ("Load-Balancer", "Web-Server-2", "traffic-routing"),
                ("Web-Server-1", "Web-API", "api-calls"),
                ("Web-Server-2", "Web-API", "api-calls"),
                ("Web-API", "DB-Server", "data-storage"),
                ("Web-API", "Redis-Cache", "caching"),
                ("DB-Server", "Backup-Server", "backup"),
            ]
            for source, target, dep_type in dependencies:
                session.run("""
                    MATCH (s:Asset {name: $source})
                    MATCH (t:Asset {name: $target})
                    MERGE (s)-[:DEPENDS_ON {type: $type}]->(t)
                """, source=source, target=target, type=dep_type)
            print("✓ Dependency relationships created")

            # Service to Asset mappings
            service_mappings = [
                ("Employee-Portal", "Load-Balancer"),
                ("Payroll-Service", "Web-API"),
                ("Email-Service", "Web-Server-1"),
            ]
            for service, asset in service_mappings:
                session.run("""
                    MATCH (s:Service {name: $service})
                    MATCH (a:Asset {name: $asset})
                    MERGE (s)-[:RUNS_ON]->(a)
                """, service=service, asset=asset)
            print("✓ Service-to-Asset relationships created")

            # User ownership
            ownership = [
                ("Sarah Johnson", "Payroll-Service"),
                ("John Smith", "Employee-Portal"),
                ("Mike Davis", "Email-Service"),
            ]
            for user, service in ownership:
                session.run("""
                    MATCH (u:User {name: $user})
                    MATCH (s:Service {name: $service})
                    MERGE (u)-[:OWNS]->(s)
                """, user=user, service=service)
            print("✓ User ownership relationships created")

            # User manages Assets
            manages = [
                ("John Smith", "DB-Server"),
                ("Mike Davis", "Load-Balancer"),
            ]
            for user, asset in manages:
                session.run("""
                    MATCH (u:User {name: $user})
                    MATCH (a:Asset {name: $asset})
                    MERGE (u)-[:MANAGES]->(a)
                """, user=user, asset=asset)
            print("✓ User management relationships created")

    def print_stats(self):
        """Print graph statistics"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] as label, count(*) as count
                ORDER BY count DESC
            """)
            print("\n📊 Graph Statistics:")
            for record in result:
                print(f"  {record['label']}: {record['count']}")

            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as relType, count(*) as count
                ORDER BY count DESC
            """)
            print("\n🔗 Relationship Statistics:")
            for record in result:
                print(f"  {record['relType']}: {record['count']}")


def main():
    print("🚀 Loading CMDB Graph into Neo4j...\n")

    loader = GraphLoader(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    try:
        loader.clear_database()
        loader.create_constraints()
        loader.load_sample_data()
        loader.print_stats()
        print("\n✅ Graph loaded successfully!")
    finally:
        loader.close()


if __name__ == "__main__":
    main()
